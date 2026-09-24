"""Portable data location independent of the launch working directory."""
from pathlib import Path
import sys

def data_directory(override=None):
    if override is not None:return Path(override).resolve()
    return (Path(sys.executable).resolve().parent if getattr(sys,'frozen',False)
            else Path(__file__).resolve().parent)

def open_folder(parent,folder):
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtCore import QUrl
    from PySide6.QtWidgets import QMessageBox
    folder=Path(folder).resolve()
    try:
        folder.mkdir(parents=True,exist_ok=True)
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder))):
            raise OSError('フォルダーを表示するアプリを起動できませんでした。')
    except OSError as e:
        QMessageBox.warning(parent,'フォルダーを開けません',f'場所: {folder}\n\n{e}\n\n保存先の存在とアクセス権を確認してください。')
        return False
    return True
