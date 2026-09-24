"""Validation helpers for official PSLog Windows update packages.

This module is deliberately standard-library only so both PSLog and the small
PSLogUpdater helper can perform the same validation independently.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, BadZipFile
import hashlib
import json
import re
import stat

from storage import StorageError

MANIFEST_PATH = 'PSLog/meta/PSLOG_UPDATE_INFO.json'
LEGACY_MANIFEST_PATH = 'PSLog/PSLOG_UPDATE_INFO.json'
FORMAT_NAME = 'PSLog update package'
FORMAT_VERSION = 1
MAX_FILES = 30000
MAX_UNCOMPRESSED = 2 * 1024 * 1024 * 1024

# Runtime user data at the application root.  An update package must never
# contain these locations.  Bundled defaults live under _internal/config and
# are application files, not user data.
PRESERVED_ROOTS = ('config', 'logbook', 'logbook_flr', 'bak', 'output')

# Ver1.043 and later keep system metadata below meta/, helper executables below
# exec/, and application documentation below docs/.  docs/ is intentionally
# allowed to be empty; the directory entry itself is part of the package.
REQUIRED_MANAGED_ROOTS = (
    'pslog.exe',
    'exec',
    '_internal',
    'meta',
    'docs',
)

# Ver1.042 had exec/ but still placed the metadata and text documents at the
# application root.  Keep this exact tuple readable so a one-time bridge ZIP
# can be consumed by an already installed 1.042 updater.
LEGACY_MANAGED_ROOTS_1042 = (
    'pslog.exe',
    'exec',
    '_internal',
    'USER_GUIDE.txt',
    'SAVE_LOCATION.md',
    'WINDOWS_CHECKLIST.txt',
    'BUILD_INFO.json',
    'PSLOG_UPDATE_INFO.json',
)

# Ver1.041 additionally used a root-level PSLogUpdater.exe.
LEGACY_MANAGED_ROOTS_1041 = (
    'pslog.exe',
    'PSLogUpdater.exe',
    '_internal',
    'USER_GUIDE.txt',
    'SAVE_LOCATION.md',
    'WINDOWS_CHECKLIST.txt',
    'BUILD_INFO.json',
    'PSLOG_UPDATE_INFO.json',
)
SUPPORTED_MANAGED_ROOTS = (
    REQUIRED_MANAGED_ROOTS,
    LEGACY_MANAGED_ROOTS_1042,
    LEGACY_MANAGED_ROOTS_1041,
)


@dataclass(frozen=True)
class UpdateInfo:
    path: Path
    version: str
    packaged_utc: str
    files: dict[str, str]
    managed_roots: tuple[str, ...]
    manifest_logical: str


UPDATE_UPGRADE = 'upgrade'
UPDATE_REINSTALL = 'reinstall'
UPDATE_SAME = 'same'
UPDATE_DOWNGRADE = 'downgrade'


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def installation_matches(info: UpdateInfo, data_root) -> bool:
    """Return True only when the installed managed payload matches this package.

    User data outside the package manifest is intentionally ignored.  Empty managed
    directories such as docs/ are still checked, so reinstall can repair a missing
    distribution directory even when it contains no files.
    """
    root = Path(data_root).resolve()
    if not root.is_dir():
        return False
    for managed in info.managed_roots:
        path = root / Path(*managed.split('/'))
        if managed == 'PSLOG_UPDATE_INFO.json':
            # Legacy package manifests are not included in info.files, but the
            # installed legacy layout still needs this managed file to count as
            # an exact match.
            if not path.is_file():
                return False
            continue
        if not path.exists():
            return False
    for logical, expected in info.files.items():
        path = root / Path(*logical.split('/'))
        if not path.is_file():
            return False
        try:
            if _file_sha256(path) != expected:
                return False
        except OSError:
            return False
    return True


def classify_update(info: UpdateInfo, current_version: str, data_root=None) -> str:
    """Classify candidate as upgrade/reinstall/same/downgrade.

    Same-version packages are considered a repair reinstall only when at least
    one managed installed file/directory differs from the selected package.
    """
    candidate = version_number(info.version)
    current = version_number(current_version)
    if candidate > current:
        return UPDATE_UPGRADE
    if candidate < current:
        return UPDATE_DOWNGRADE
    if data_root is None:
        return UPDATE_SAME
    return UPDATE_SAME if installation_matches(info, data_root) else UPDATE_REINSTALL


def version_number(value: str) -> Decimal:
    """Return the numeric PSLog version.

    PSLog uses compact decimal releases such as 1.04, 1.041, 1.042, 1.043 and
    1.05.  They are intentionally compared as decimal numbers, not semantic-
    version components.
    """
    text = str(value).strip()
    if not re.fullmatch(r'\d+\.\d+', text):
        raise ValueError('PSLogのバージョン表記が不正です: ' + text)
    try:
        return Decimal(text)
    except InvalidOperation as e:
        raise ValueError('PSLogのバージョン表記が不正です: ' + text) from e


def is_newer(candidate: str, current: str) -> bool:
    return version_number(candidate) > version_number(current)


def _safe_member(info):
    name = info.filename
    if '\\' in name:
        raise StorageError('更新ZIP内にWindows区切り文字を使った不正なパスがあります。')
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise StorageError('更新ZIP内に不正なパスがあります。')
    if path.parts[0] != 'PSLog':
        raise StorageError('PSLog更新ZIPではないファイルが含まれています: ' + name)
    # Reject Unix symlink entries even though normal Windows packages do not
    # use them.  This keeps extraction rules deterministic on every platform.
    mode = (info.external_attr >> 16) & 0xFFFF
    if mode and stat.S_ISLNK(mode):
        raise StorageError('更新ZIPにシンボリックリンクは使用できません。')
    return path


def _logical(name: str) -> str:
    path = PurePosixPath(name)
    return PurePosixPath(*path.parts[1:]).as_posix()


def _root_present(root: str, hashes: dict[str, str], directories: set[str]) -> bool:
    if root in hashes or root in directories:
        return True
    prefix = root.rstrip('/') + '/'
    return any(name.startswith(prefix) for name in hashes) or any(name.startswith(prefix) for name in directories)


def inspect_update(path, current_version: str | None = None, require_newer: bool = False) -> UpdateInfo:
    path = Path(path).resolve()
    if not path.is_file():
        raise StorageError('更新ZIPが見つかりません。')
    try:
        with ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_FILES:
                raise StorageError('更新ZIP内のファイル数が多すぎます。')
            if sum(i.file_size for i in infos) > MAX_UNCOMPRESSED:
                raise StorageError('更新ZIPの展開後サイズが大きすぎます。')
            if archive.testzip() is not None:
                raise StorageError('更新ZIPの検証に失敗しました。')
            seen = set()
            file_infos = {}
            directories = set()
            for info in infos:
                member = _safe_member(info)
                name = member.as_posix()
                if name in seen:
                    raise StorageError('更新ZIP内に同名ファイルが重複しています: ' + name)
                seen.add(name)
                if info.flag_bits & 0x1:
                    raise StorageError('暗号化ZIPには対応していません。')
                if info.is_dir():
                    logical = _logical(name)
                    if logical:
                        directories.add(logical.rstrip('/'))
                else:
                    file_infos[name] = info

            manifest_paths = [p for p in (MANIFEST_PATH, LEGACY_MANIFEST_PATH) if p in file_infos]
            if not manifest_paths:
                raise StorageError('PSLog更新情報がありません。正式なWindows版ZIPを選択してください。')
            if len(manifest_paths) != 1:
                raise StorageError('PSLog更新情報が重複しています。')
            manifest_path = manifest_paths[0]
            try:
                manifest = json.loads(archive.read(manifest_path).decode('utf-8'))
            except (ValueError, UnicodeError) as e:
                raise StorageError('PSLog更新情報を読み込めません。') from e
            if not isinstance(manifest, dict) or manifest.get('format') != FORMAT_NAME:
                raise StorageError('PSLog更新情報の形式が不正です。')
            if manifest.get('format_version') != FORMAT_VERSION:
                raise StorageError('未対応のPSLog更新形式です。')
            if manifest.get('product') != 'PSLog':
                raise StorageError('PSLog用ではない更新ZIPです。')
            version = str(manifest.get('version', '')).strip()
            try:
                version_number(version)
            except ValueError as e:
                raise StorageError(str(e)) from e
            managed = manifest.get('managed_roots')
            if not isinstance(managed, list) or any(not isinstance(x, str) for x in managed):
                raise StorageError('更新対象情報が不正です。')
            managed_tuple = tuple(managed)
            if managed_tuple not in SUPPORTED_MANAGED_ROOTS:
                raise StorageError('このPSLogでは扱えない更新対象構成です。')

            # New-layout packages must use the metadata directory.  Legacy
            # tuples intentionally retain the old root manifest for 1.041/1.042.
            if managed_tuple == REQUIRED_MANAGED_ROOTS and manifest_path != MANIFEST_PATH:
                raise StorageError('現行形式のPSLog更新情報の場所が不正です。')
            if managed_tuple != REQUIRED_MANAGED_ROOTS and manifest_path != LEGACY_MANIFEST_PATH:
                raise StorageError('旧形式のPSLog更新情報の場所が不正です。')

            hashes = manifest.get('files')
            if not isinstance(hashes, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in hashes.items()):
                raise StorageError('更新ファイル一覧が不正です。')

            actual_logical = {_logical(name) for name in file_infos if name != manifest_path}
            if set(hashes) != actual_logical:
                raise StorageError('更新ZIPのファイル一覧と更新情報が一致しません。')
            for logical, expected in hashes.items():
                if not re.fullmatch(r'[0-9a-f]{64}', expected):
                    raise StorageError('更新ファイルの検証情報が不正です: ' + logical)
                p = PurePosixPath(logical)
                if p.is_absolute() or '..' in p.parts or not p.parts:
                    raise StorageError('更新ファイルのパスが不正です: ' + logical)
                if p.parts[0].casefold() in {x.casefold() for x in PRESERVED_ROOTS}:
                    raise StorageError('更新ZIPに利用者データ領域が含まれています: ' + logical)
                member = 'PSLog/' + p.as_posix()
                digest = hashlib.sha256(archive.read(member)).hexdigest()
                if digest != expected:
                    raise StorageError('更新ZIPの内容が更新情報と一致しません: ' + logical)

            for root in managed_tuple:
                # The legacy manifest is itself one of the old managed roots;
                # the current manifest lives inside managed root meta/.
                if root == 'PSLOG_UPDATE_INFO.json':
                    continue
                if not _root_present(root, hashes, directories):
                    kind = 'フォルダー' if root in {'_internal', 'exec', 'meta', 'docs'} else 'ファイル'
                    raise StorageError(f'更新ZIPに必要な{kind}がありません: ' + root)
            packaged = str(manifest.get('packaged_utc', ''))
    except (BadZipFile, OSError) as e:
        raise StorageError('更新ZIPを読み込めません: ' + str(e)) from e

    if current_version is not None and require_newer and not is_newer(version, current_version):
        if version_number(version) == version_number(current_version):
            raise StorageError(f'選択したZIPは現在と同じ Ver{version} です。新しいバージョンを選択してください。')
        raise StorageError(f'Ver{current_version} から Ver{version} へ戻すことはできません。新しいバージョンを選択してください。')
    return UpdateInfo(path, version, packaged, hashes, managed_tuple, _logical(manifest_path))
