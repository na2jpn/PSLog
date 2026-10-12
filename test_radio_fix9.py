import unittest
from pathlib import Path


class RadioFix9Tests(unittest.TestCase):
    def test_setupc_runs_from_its_install_directory(self):
        source=Path('radio_control.py').read_text(encoding='utf-8')
        self.assertIn("info.lpDirectory=str(directory) if directory else None",source)
        self.assertIn("$toolDir = Split-Path -Parent $tool",source)
        self.assertIn("Set-Location -LiteralPath $toolDir",source)
        self.assertIn("directory=str(Path(tool).resolve().parent)",source)

    def test_setupc_list_uses_tool_directory(self):
        source=Path('radio_control.py').read_text(encoding='utf-8')
        self.assertIn("_run([path,'list'],timeout=timeout,cwd=str(Path(path).resolve().parent))",source)


if __name__=='__main__':
    unittest.main()
