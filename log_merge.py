"""Safe same-year PSLog log-file consolidation.

The checker is deliberately read-only.  Execution is only possible with the
exact snapshots produced by a successful check, so a changed file always
requires another check before destructive work can start.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import os
import uuid

from storage import (Snapshot, StorageError, InvalidLog, parse, duplicate_key,
                     operation_lock, replace_bytes)
from search import file_identity


@dataclass(frozen=True)
class MergePlan:
    target: Path
    source: Path
    target_snapshot: Snapshot
    source_snapshot: Snapshot
    target_year: str
    target_call: str
    source_call: str
    target_records: int
    source_records: int
    duplicate_skipped: int
    added_records: int
    merged_records: int
    output: bytes
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class MergeResult:
    target: Path
    removed_source: Path
    target_backup: Path
    source_backup: Path
    added_records: int
    duplicate_skipped: int
    merged_records: int


def _inside_logbook(repo, path):
    path = Path(path).resolve()
    book = repo.book.resolve()
    if path.parent != book:
        raise StorageError('logbook直下のPSLogログファイルを選択してください。')
    if not path.exists() or not path.is_file():
        raise StorageError('選択したログファイルが見つかりません。')
    if path.is_symlink():
        raise StorageError('リンクされたログファイルは統合できません。')
    return path


def _identity(path):
    value = file_identity(path)
    if not value:
        raise StorageError(
            f'{Path(path).name}: PSLogのログファイル名ではありません。'
            '（例: 2026_JH1HST_.txt / 2026_JH1HST-1_.txt）'
        )
    return value


def _base_call(call):
    return call.split('/', 1)[0].upper()


def _read_checked(path, snap, year):
    try:
        log = parse(snap.data or b'')
    except InvalidLog as e:
        raise StorageError(f'{path.name}: {e}') from e
    if log.issues:
        sample = '\n'.join(f'  {x.line}行: {x.reason}' for x in log.issues[:8])
        more = f'\n  ほか {len(log.issues)-8}件' if len(log.issues) > 8 else ''
        raise StorageError(f'{path.name}: 解釈できない行があります。\n{sample}{more}')
    # Header / separator notices cannot be assigned a safe position after a
    # chronological sort.  Refuse rather than silently dropping or moving them.
    if log.notices:
        sample = '\n'.join(f'  {x.line}行: {x.reason}' for x in log.notices[:8])
        more = f'\n  ほか {len(log.notices)-8}件' if len(log.notices) > 8 else ''
        raise StorageError(
            f'{path.name}: 見出し・区切り行があります。自動統合では位置を保持できないため実行しません。\n'
            f'{sample}{more}'
        )
    wrong = [(line, q.date) for line, q in log.records if not q.date.startswith(year + '-')]
    if wrong:
        sample = ', '.join(f'{line}行={date}' for line, date in wrong[:8])
        more = f' ほか{len(wrong)-8}件' if len(wrong) > 8 else ''
        raise StorageError(
            f'{path.name}: ファイル年 {year} と異なるQSOがあります（{sample}{more}）。'
            ' 年を修正してから再度チェックしてください。'
        )
    return log


def _raw_body(raw):
    return raw.rstrip('\r\n')


def check(repo, target, source):
    """Read and fully validate two logs, returning an immutable merge plan."""
    target = _inside_logbook(repo, target)
    source = _inside_logbook(repo, source)
    if target == source:
        raise StorageError('統合先と統合元に同じファイルは指定できません。')

    target_year, target_call, _target_suffix = _identity(target)
    source_year, source_call, _source_suffix = _identity(source)
    if target_year != source_year:
        raise StorageError(f'同じ年のログだけ統合できます（{target_year} と {source_year}）。')
    if _base_call(target_call) != _base_call(source_call):
        raise StorageError(
            '同じ自局コールサイン系統のログだけ統合できます。'
            f'（統合先 {target_call} / 統合元 {source_call}）'
        )

    target_snapshot = Snapshot.read(target)
    source_snapshot = Snapshot.read(source)
    target_log = _read_checked(target, target_snapshot, target_year)
    source_log = _read_checked(source, source_snapshot, source_year)
    if not source_log.records:
        raise StorageError('統合元に交信記録がありません。')

    # Keep every target row exactly once in its existing multiplicity.  For the
    # source, the first occurrence of a duplicate key wins and any key already
    # present in the target is skipped.  This is the requested "target wins"
    # rule without rewriting/removing duplicates already present in the target.
    seen = {duplicate_key(q) for _, q in target_log.records}
    rows = []
    sequence = 0
    for line, q in target_log.records:
        rows.append((q.date, q.time, sequence, _raw_body(target_log.lines[line-1].raw)))
        sequence += 1
    skipped = 0
    added = 0
    for line, q in source_log.records:
        key = duplicate_key(q)
        if key in seen:
            skipped += 1
            continue
        seen.add(key)
        rows.append((q.date, q.time, sequence, _raw_body(source_log.lines[line-1].raw)))
        sequence += 1
        added += 1

    rows.sort(key=lambda x: (x[0], x[1], x[2]))
    newline = target_log.newline or '\r\n'
    text = ''.join(raw + newline for _date, _time, _seq, raw in rows)
    output = (b'\xef\xbb\xbf' if target_log.bom else b'') + text.encode('utf-8')
    verified = parse(output)
    if verified.issues or len(verified.records) != len(rows):
        raise StorageError('統合後データの自己検査に失敗しました。原本は変更していません。')

    warnings = []
    target_blank = sum(1 for item in target_log.lines if not item.qso and not item.raw.strip())
    source_blank = sum(1 for item in source_log.lines if not item.qso and not item.raw.strip())
    if target_blank or source_blank:
        warnings.append(f'空行 {target_blank + source_blank}行は統合後の並べ替えで除去されます。')
    if target_log.bom != source_log.bom:
        warnings.append('BOM有無が異なります。統合先ファイルの文字コード表現を維持します。')
    if target_log.newline != source_log.newline:
        warnings.append('改行コードが異なります。統合先ファイルの改行コードを使用します。')

    return MergePlan(
        target, source, target_snapshot, source_snapshot,
        target_year, target_call, source_call,
        len(target_log.records), len(source_log.records), skipped, added,
        len(rows), output, tuple(warnings)
    )


def _backup(directory, path, data, stamp):
    if data is None:
        raise StorageError(f'{path.name}: バックアップする原本がありません。')
    if directory.is_symlink():
        raise StorageError('logbook_bakフォルダーがリンクです。安全のため統合を中止します。')
    directory.mkdir(parents=True, exist_ok=True)
    name = f'{path.name}.{stamp}-{uuid.uuid4().hex[:8]}.bak'
    dest = directory / name
    with dest.open('xb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    if dest.read_bytes() != data:
        dest.unlink(missing_ok=True)
        raise StorageError(f'{path.name}: 統合前バックアップの照合に失敗しました。')
    return dest


def execute(repo, plan):
    """Execute a previously checked plan.  Re-check snapshots before writes."""
    if not isinstance(plan, MergePlan):
        raise StorageError('先に「ファイルチェック」を実行してください。')
    target = _inside_logbook(repo, plan.target)
    source = _inside_logbook(repo, plan.source)
    backup_dir = repo.bak / 'logbook_bak'
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')

    with operation_lock(repo.book):
        # A selection or file change after the checker invalidates execution.
        plan.target_snapshot.check(target)
        plan.source_snapshot.check(source)

        target_backup = _backup(backup_dir, target, plan.target_snapshot.data, stamp)
        source_backup = _backup(backup_dir, source, plan.source_snapshot.data, stamp)

        # Recheck after potentially slow backup writes, then atomically replace
        # the target.  If a crash occurs before source deletion, both logs remain
        # and a re-run simply reports all source rows as duplicates.
        plan.target_snapshot.check(target)
        plan.source_snapshot.check(source)
        replace_bytes(target, plan.output, plan.target_snapshot)
        after = Snapshot.read(target)
        parsed = parse(after.data or b'')
        if parsed.issues or len(parsed.records) != plan.merged_records:
            raise StorageError(
                '統合先の保存後検査に失敗しました。統合元は削除していません。'
                f' バックアップ: {backup_dir}'
            )

        # Do not delete a source that changed since the check.
        plan.source_snapshot.check(source)
        source.unlink()
        repo.started.add(target)
        repo.changed.add(target)

    return MergeResult(
        target, source, target_backup, source_backup,
        plan.added_records, plan.duplicate_skipped, plan.merged_records
    )
