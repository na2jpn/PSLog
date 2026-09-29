"""Validation helpers for official PSLog Windows update packages.

Ver1.15 adds a forward-looking manifest at ``meta/versionup.json``.  It can
name arbitrary application-managed root EXEs/folders while protected user-data
roots remain forbidden.  The legacy ``PSLOG_UPDATE_INFO.json`` reader remains
for updates from older PSLog releases and for the Ver1.15 transition package.

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

# Ver1.15+ manifest.  Normal Ver1.15 Windows packages intentionally also carry
# the old manifest so Ver1.14 can install the transition release.  Ver1.15 and
# later prefer this new file when it is present.
VERSIONUP_PATH = 'PSLog/meta/versionup.json'
VERSIONUP_FORMAT_NAME = 'PSLog versionup package'
VERSIONUP_FORMAT_VERSION = 1

MAX_FILES = 30000
MAX_UNCOMPRESSED = 2 * 1024 * 1024 * 1024

# Runtime user data at the application root.  No update manifest may manage,
# replace or remove these locations.  Bundled defaults below _internal/config
# are application files and are intentionally not affected by this rule.
PRESERVED_ROOTS = ('config', 'logbook', 'logbook_flr', 'bak', 'output')
_PRESERVED_CASEFOLD = {x.casefold() for x in PRESERVED_ROOTS}

# Historical fixed layout used by the legacy manifest.  Keep these tuples
# readable because already-installed old updaters know exactly these layouts.
REQUIRED_MANAGED_ROOTS = (
    'pslog.exe',
    'exec',
    '_internal',
    'meta',
    'docs',
)
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
    remove_roots: tuple[str, ...] = ()
    manifest_kind: str = 'legacy'


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
    """Return True only when the installed managed payload matches this package."""
    root = Path(data_root).resolve()
    if not root.is_dir():
        return False
    manifest_path = root / Path(*info.manifest_logical.split('/'))
    if not manifest_path.is_file():
        return False
    for managed in info.managed_roots:
        path = root / Path(*managed.split('/'))
        if managed == 'PSLOG_UPDATE_INFO.json':
            if not path.is_file():
                return False
            continue
        if not path.exists():
            return False
    for removed in info.remove_roots:
        path = root / Path(*removed.split('/'))
        if path.exists() or path.is_symlink():
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
    mode = (info.external_attr >> 16) & 0xFFFF
    if mode and stat.S_ISLNK(mode):
        raise StorageError('更新ZIPにシンボリックリンクは使用できません。')
    return path


def _logical(name: str) -> str:
    path = PurePosixPath(name)
    return PurePosixPath(*path.parts[1:]).as_posix()


def _root_present(root: str, hashes: dict[str, str], directories: set[str], extra_files=()) -> bool:
    if root in hashes or root in directories or root in extra_files:
        return True
    prefix = root.rstrip('/') + '/'
    return (any(name.startswith(prefix) for name in hashes)
            or any(name.startswith(prefix) for name in directories)
            or any(name.startswith(prefix) for name in extra_files))


def _validate_hashes(archive, hashes, file_infos):
    if not isinstance(hashes, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in hashes.items()):
        raise StorageError('更新ファイル一覧が不正です。')
    for logical, expected in hashes.items():
        if not re.fullmatch(r'[0-9a-f]{64}', expected):
            raise StorageError('更新ファイルの検証情報が不正です: ' + logical)
        p = PurePosixPath(logical)
        if p.is_absolute() or '..' in p.parts or not p.parts:
            raise StorageError('更新ファイルのパスが不正です: ' + logical)
        if p.parts[0].casefold() in _PRESERVED_CASEFOLD:
            raise StorageError('更新ZIPに利用者データ領域が含まれています: ' + logical)
        member = 'PSLog/' + p.as_posix()
        if member not in file_infos:
            raise StorageError('更新ZIPのファイル一覧と更新情報が一致しません。')
        digest = hashlib.sha256(archive.read(member)).hexdigest()
        if digest != expected:
            raise StorageError('更新ZIPの内容が更新情報と一致しません: ' + logical)


def _validate_new_root_name(root: str, hashes: dict[str, str], directories: set[str]):
    p = PurePosixPath(root)
    if p.is_absolute() or '..' in p.parts or len(p.parts) != 1 or not root:
        raise StorageError('更新対象ルートが不正です: ' + str(root))
    if root.casefold() in _PRESERVED_CASEFOLD:
        raise StorageError('利用者データ領域を更新対象にはできません: ' + root)
    # The distribution root remains intentionally clean: direct files are EXEs;
    # all non-EXE content belongs inside folders such as meta/, exec/, dll/, etc.
    if root in hashes and not root.casefold().endswith('.exe'):
        raise StorageError('PSLogルート直下の更新ファイルはEXEだけ使用できます: ' + root)
    if root not in hashes and root not in directories:
        prefix = root + '/'
        if not any(x.startswith(prefix) for x in hashes) and not any(x.startswith(prefix) for x in directories):
            raise StorageError('更新対象ルートが更新ZIPにありません: ' + root)


def _inspect_versionup(archive, path, file_infos, directories):
    try:
        manifest = json.loads(archive.read(VERSIONUP_PATH).decode('utf-8'))
    except (ValueError, UnicodeError) as e:
        raise StorageError('versionup情報を読み込めません。') from e
    if not isinstance(manifest, dict) or manifest.get('format') != VERSIONUP_FORMAT_NAME:
        raise StorageError('versionup情報の形式が不正です。')
    if manifest.get('format_version') != VERSIONUP_FORMAT_VERSION:
        raise StorageError('未対応のversionup形式です。')
    if manifest.get('product') != 'PSLog':
        raise StorageError('PSLog用ではない更新ZIPです。')
    version = str(manifest.get('version', '')).strip()
    try:
        version_number(version)
    except ValueError as e:
        raise StorageError(str(e)) from e

    managed = manifest.get('managed_roots')
    removed = manifest.get('remove_roots', [])
    if (not isinstance(managed, list) or not managed or any(not isinstance(x, str) or not x for x in managed)
            or len(set(x.casefold() for x in managed)) != len(managed)):
        raise StorageError('versionupの更新対象情報が不正です。')
    if (not isinstance(removed, list) or any(not isinstance(x, str) or not x for x in removed)
            or len(set(x.casefold() for x in removed)) != len(removed)):
        raise StorageError('versionupの削除対象情報が不正です。')
    managed_tuple = tuple(managed)
    removed_tuple = tuple(removed)
    if 'pslog.exe' not in {x.casefold() for x in managed_tuple}:
        raise StorageError('versionupにはpslog.exeの更新指定が必要です。')
    if {x.casefold() for x in managed_tuple} & {x.casefold() for x in removed_tuple}:
        raise StorageError('同じルートを更新対象と削除対象の両方には指定できません。')

    hashes = manifest.get('files')
    _validate_hashes(archive, hashes, file_infos)

    # versionup.json itself and the optional legacy transition manifest are
    # metadata, not ordinary payload entries listed in the v2 file hash map.
    excluded = {VERSIONUP_PATH, MANIFEST_PATH, LEGACY_MANIFEST_PATH}
    actual_logical = {_logical(name) for name in file_infos if name not in excluded}
    if set(hashes) != actual_logical:
        raise StorageError('更新ZIPのファイル一覧とversionup情報が一致しません。')

    for root in managed_tuple:
        _validate_new_root_name(root, hashes, directories)
    for root in removed_tuple:
        p = PurePosixPath(root)
        if p.is_absolute() or '..' in p.parts or len(p.parts) != 1 or not root:
            raise StorageError('削除対象ルートが不正です: ' + str(root))
        if root.casefold() in _PRESERVED_CASEFOLD:
            raise StorageError('利用者データ領域を削除対象にはできません: ' + root)
        if root.casefold() == 'pslog.exe':
            raise StorageError('pslog.exeを削除対象にはできません。')

    allowed = {x.casefold() for x in managed_tuple}
    for logical in hashes:
        first = PurePosixPath(logical).parts[0]
        if first.casefold() not in allowed:
            raise StorageError('versionupの更新対象外ファイルが含まれています: ' + logical)

    # If a compatibility legacy manifest is present, at least require it to
    # identify the same product/version.  Older PSLog versions will validate its
    # own full hash list independently.
    if MANIFEST_PATH in file_infos:
        try:
            legacy = json.loads(archive.read(MANIFEST_PATH).decode('utf-8'))
        except (ValueError, UnicodeError) as e:
            raise StorageError('互換更新情報を読み込めません。') from e
        if legacy.get('product') != 'PSLog' or str(legacy.get('version','')).strip() != version:
            raise StorageError('versionup情報と互換更新情報のバージョンが一致しません。')

    packaged = str(manifest.get('packaged_utc', ''))
    return UpdateInfo(Path(path).resolve(), version, packaged, hashes, managed_tuple,
                      _logical(VERSIONUP_PATH), removed_tuple, 'versionup')


def _inspect_legacy(archive, path, file_infos, directories):
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
    if managed_tuple == REQUIRED_MANAGED_ROOTS and manifest_path != MANIFEST_PATH:
        raise StorageError('現行形式のPSLog更新情報の場所が不正です。')
    if managed_tuple != REQUIRED_MANAGED_ROOTS and manifest_path != LEGACY_MANIFEST_PATH:
        raise StorageError('旧形式のPSLog更新情報の場所が不正です。')

    hashes = manifest.get('files')
    _validate_hashes(archive, hashes, file_infos)
    actual_logical = {_logical(name) for name in file_infos if name != manifest_path}
    if set(hashes) != actual_logical:
        raise StorageError('更新ZIPのファイル一覧と更新情報が一致しません。')

    for root in managed_tuple:
        if root == 'PSLOG_UPDATE_INFO.json':
            continue
        if not _root_present(root, hashes, directories):
            kind = 'フォルダー' if root in {'_internal', 'exec', 'meta', 'docs'} else 'ファイル'
            raise StorageError(f'更新ZIPに必要な{kind}がありません: ' + root)
    packaged = str(manifest.get('packaged_utc', ''))
    return UpdateInfo(Path(path).resolve(), version, packaged, hashes, managed_tuple,
                      _logical(manifest_path), (), 'legacy')


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

            if VERSIONUP_PATH in file_infos:
                info = _inspect_versionup(archive, path, file_infos, directories)
            else:
                info = _inspect_legacy(archive, path, file_infos, directories)
    except (BadZipFile, OSError) as e:
        raise StorageError('更新ZIPを読み込めません: ' + str(e)) from e

    if current_version is not None and require_newer and not is_newer(info.version, current_version):
        if version_number(info.version) == version_number(current_version):
            raise StorageError(f'選択したZIPは現在と同じ Ver{info.version} です。新しいバージョンを選択してください。')
        raise StorageError(f'Ver{current_version} から Ver{info.version} へ戻すことはできません。新しいバージョンを選択してください。')
    return info
