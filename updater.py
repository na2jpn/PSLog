"""PSLogUpdater helper.

Built as PSLogUpdater.exe.  It is not a standalone installer: PSLog creates a
one-time session file, copies this helper to a temporary folder, then exits.
The helper waits for PSLog to stop, validates the official update ZIP again,
replaces application files only, and starts the new pslog.exe.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import ctypes
import json
import os
import hashlib
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from zipfile import ZipFile

from update_package import (
    inspect_update, classify_update, UPDATE_UPGRADE, UPDATE_REINSTALL,
    UPDATE_SAME, UPDATE_DOWNGRADE,
)
from update_state import remove_lock,read_lock

SESSION_FORMAT = 'PSLog update session'
SESSION_VERSION = 1


def _message(title, text, error=False):
    if sys.platform == 'win32':
        flags = 0x10 if error else 0x40  # MB_ICONERROR / MB_ICONINFORMATION
        ctypes.windll.user32.MessageBoxW(None, str(text), str(title), flags)
    else:
        stream = sys.stderr if error else sys.stdout
        print(f'{title}: {text}', file=stream)


def _load_session(path, token):
    path = Path(path).resolve()
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError, UnicodeError) as e:
        raise RuntimeError('更新セッション情報を読み込めません。') from e
    if not isinstance(data, dict) or data.get('format') != SESSION_FORMAT or data.get('format_version') != SESSION_VERSION:
        raise RuntimeError('更新セッション情報が不正です。')
    if not token or data.get('token') != token:
        raise RuntimeError('更新セッションを確認できません。PSLogからやり直してください。')
    for key in ('package', 'target', 'current_version', 'pid'):
        if key not in data:
            raise RuntimeError('更新セッション情報が不足しています。')
    return path, data


def _wait_for_pid(pid, timeout=120):
    pid = int(pid)
    if pid <= 0:
        return
    if sys.platform != 'win32':
        # Used only by tests/source diagnostics.  Production updater is Windows.
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                os.kill(pid, 0)
            except OSError:
                return
            time.sleep(0.1)
        raise RuntimeError('PSLogの終了を確認できませんでした。')
    SYNCHRONIZE = 0x00100000
    WAIT_OBJECT_0 = 0
    WAIT_TIMEOUT = 0x102
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
    if not handle:
        return  # already exited
    try:
        result = kernel32.WaitForSingleObject(handle, int(timeout * 1000))
        if result == WAIT_TIMEOUT:
            raise RuntimeError('PSLogの終了を確認できませんでした。更新を中止しました。')
        if result != WAIT_OBJECT_0:
            raise RuntimeError('PSLogの終了待ちに失敗しました。')
    finally:
        kernel32.CloseHandle(handle)


def _remove(path):
    path = Path(path)
    if not path.exists() and not path.is_symlink():
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_tree(info, root, label='更新ファイル'):
    root = Path(root)
    for logical, expected in info.files.items():
        path = root / Path(*logical.split('/'))
        if not path.is_file():
            raise RuntimeError(f'{label}が不足しています: {logical}')
        actual = _file_sha256(path)
        if actual != expected:
            raise RuntimeError(f'{label}の整合性確認に失敗しました: {logical}')


def _extract_verified(info, destination):
    destination = Path(destination)
    app = destination / 'PSLog'
    with ZipFile(info.path) as archive:
        for member in archive.infolist():
            # inspect_update already rejects unsafe members.  Preserve explicit
            # directory entries too because docs/ may intentionally be empty.
            logical = Path(*member.filename.split('/')[1:])
            target = app / logical
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as src, target.open('wb') as dst:
                shutil.copyfileobj(src, dst)
    _verify_tree(info, app, '展開した更新ファイル')
    return app


def _runtime_self_check(target, timeout=45):
    exe = Path(target) / 'pslog.exe'
    if not exe.is_file():
        raise RuntimeError('更新後のpslog.exeがありません。')
    try:
        completed = subprocess.run(
            [str(exe), '--update-self-check'],
            cwd=str(target),
            timeout=timeout,
            check=False,
            close_fds=True,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        raise RuntimeError('更新後のPSLog自己診断を実行できませんでした。') from e
    if completed.returncode != 0:
        raise RuntimeError(
            '更新後のPSLog自己診断に失敗しました。'
            f' (終了コード {completed.returncode})'
        )


def _apply_staged(staged, target, managed_roots, verify_installed=None):
    target = Path(target).resolve()
    if not target.is_dir():
        raise RuntimeError('PSLog本体フォルダーが見つかりません。')
    if not (target / 'pslog.exe').is_file():
        raise RuntimeError('更新先にpslog.exeがありません。')
    # Keep the rollback tree on the same volume as PSLog so moving the large
    # _internal directory is a fast rename instead of a full cross-volume copy.
    backup = target.parent / ('.PSLogUpdateRollback-' + uuid.uuid4().hex)
    backup.mkdir(parents=True, exist_ok=False)
    moved_old = []
    installed = []
    try:
        for root in managed_roots:
            old = target / root
            if old.exists() or old.is_symlink():
                saved = backup / root
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(old), str(saved))
                moved_old.append((saved, old))
        for root in managed_roots:
            src = staged / root
            if not src.exists():
                raise RuntimeError('更新用ファイルが不足しています: ' + root)
            dst = target / root
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            installed.append(dst)
        if not (target / 'pslog.exe').is_file() or not (target / '_internal').is_dir():
            raise RuntimeError('更新後のPSLog本体を確認できません。')
        if verify_installed is not None:
            verify_installed(target)
    except BaseException as original:
        restore_errors=[]
        for p in reversed(installed):
            try:_remove(p)
            except OSError as e:restore_errors.append(str(e))
        for saved, old in reversed(moved_old):
            try:
                old.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(saved), str(old))
            except OSError as e:
                restore_errors.append(str(e))
        if restore_errors:
            try:(backup/'.PSLOG_KEEP_ROLLBACK').write_text('Automatic rollback failed; preserve this directory.',encoding='utf-8')
            except OSError:pass
            raise RuntimeError(str(original)+'\n\n更新前状態への自動復旧にも失敗しました。\n復旧用フォルダーを削除せず確認してください:\n'+str(backup)) from original
        shutil.rmtree(backup, ignore_errors=True)
        raise
    shutil.rmtree(backup, ignore_errors=True)


def perform(session_path, token):
    session_file, session = _load_session(session_path, token)
    package = Path(session['package']).resolve()
    target = Path(session['target']).resolve()
    current = str(session['current_version'])
    _wait_for_pid(session['pid'])
    try:
        # Validate again only after the old PSLog has fully exited.  If the ZIP
        # changed after the in-app confirmation, no application file is touched.
        info = inspect_update(package)
        requested_mode = str(session.get('mode') or 'upgrade')
        if requested_mode not in (UPDATE_UPGRADE, UPDATE_REINSTALL):
            raise RuntimeError('更新モードを確認できません。PSLogからやり直してください。')
        relation = classify_update(info, current, target)
        if relation == UPDATE_DOWNGRADE:
            raise RuntimeError(f'Ver{current} から Ver{info.version} へ戻すことはできません。')
        if requested_mode == UPDATE_UPGRADE and relation != UPDATE_UPGRADE:
            if relation == UPDATE_SAME:
                raise RuntimeError('選択したZIPは現在インストールされている内容と同じです。')
            raise RuntimeError('通常アップデートとして扱えない更新パッケージです。PSLogからやり直してください。')
        if requested_mode == UPDATE_REINSTALL and relation != UPDATE_REINSTALL:
            if relation == UPDATE_SAME:
                raise RuntimeError('選択したZIPは現在インストールされている内容と同じです。再インストールは不要です。')
            raise RuntimeError('修復・再インストールとして扱えない更新パッケージです。PSLogからやり直してください。')
        # Stage beside the installation so directory swaps stay on one volume.
        with tempfile.TemporaryDirectory(prefix='.PSLogUpdateStage-', dir=str(target.parent)) as temp:
            staged = _extract_verified(info, temp)
            if not (staged / info.manifest_logical).is_file():
                raise RuntimeError('展開した更新情報を確認できません。')
            def verify_installed(root):
                _verify_tree(info, root, '更新後のPSLogファイル')
                _runtime_self_check(root)
            _apply_staged(staged, target, info.managed_roots, verify_installed)
    except BaseException:
        # The old application has already exited.  If validation failed or the
        # transactional swap rolled back, clear the update gate before bringing
        # the usable old PSLog back up.
        remove_lock(target,session.get('token') or token)
        old_exe=target/'pslog.exe'
        if old_exe.is_file():
            try:subprocess.Popen([str(old_exe)],cwd=str(target),close_fds=True)
            except OSError:pass
        raise
    try:
        session_file.unlink(missing_ok=True)
    except OSError:
        pass
    return info.version,target,str(session.get('token') or token),requested_mode


def _completion_wait(version,seconds=10,mode='upgrade'):
    action = '修復・再インストール' if mode == UPDATE_REINSTALL else 'バージョンアップ'
    text=(f'PSLog Ver{version} の{action}が完了しました。\n\n'
          'OKで今すぐ起動します。\n'
          f'操作しなくても約{seconds}秒後に自動的に起動します。')
    if sys.platform=='win32':
        try:
            fn=ctypes.windll.user32.MessageBoxTimeoutW
            fn.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_uint,ctypes.c_ushort,ctypes.c_uint]
            fn.restype=ctypes.c_int
            fn(None,text,'PSLog Updater',0x40,0,int(seconds*1000))
            return
        except Exception:
            pass
    _message('PSLog Updater',text)


def _launch_updated_pslog(target,token):
    exe=Path(target)/'pslog.exe'
    if not exe.is_file():raise RuntimeError('更新後のpslog.exeがありません。')
    subprocess.Popen([str(exe),'--update-launch-token',str(token)],cwd=str(target),close_fds=True)



def _wait_for_launch_ack(target,token,timeout=45):
    deadline=time.time()+timeout
    while time.time()<deadline:
        data=read_lock(target)
        if not data or data.get('token')!=str(token):return
        time.sleep(0.1)
    remove_lock(target,token)
    raise RuntimeError('新しいPSLogの起動完了を確認できませんでした。')

def _schedule_self_delete():
    if sys.platform != 'win32' or not getattr(sys, 'frozen', False):
        return
    try:
        MOVEFILE_DELAY_UNTIL_REBOOT = 0x4
        ctypes.windll.kernel32.MoveFileExW(str(Path(sys.executable)), None, MOVEFILE_DELAY_UNTIL_REBOOT)
    except Exception:
        pass


def main(argv=None):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--session')
    parser.add_argument('--token')
    args, _ = parser.parse_known_args(argv)
    if not args.session or not args.token:
        _message('PSLog Updater',
                 'このプログラムはPSLogから自動的に起動される更新用プログラムです。\n\n'
                 '直接実行することはできません。\nPSLogの「バージョンアップ」機能から実行してください。')
        return 2
    target=None
    try:
        version,target,launch_token,mode = perform(args.session, args.token)
        _completion_wait(version,10,mode)
        _launch_updated_pslog(target,launch_token)
        _wait_for_launch_ack(target,launch_token)
    except Exception as e:
        if target is not None:
            try:remove_lock(target,args.token)
            except Exception:pass
        _message('PSLog Updater - 更新失敗',
                 str(e) + '\n\nPSLogのプログラム更新を完了できませんでした。\n利用者データは更新対象にしていません。', True)
        return 1
    _schedule_self_delete()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
