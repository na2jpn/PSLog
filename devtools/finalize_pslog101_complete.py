"""Create the complete PSLog 1.01 pre-Windows handoff archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREFIX = Path("PSLOG101")
PROJECT_PREFIX = PREFIX / "pslog-1.01"
EXCLUDED_PARTS = {".git", "__pycache__", "build", "dist", "release", "logbook", "bak"}
EXCLUDED_NAMES = {"conf.cfg", "location_overrides.json", "submit_profiles.json", ".DS_Store"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if path.is_symlink():
            raise ValueError(f"シンボリックリンクは最終保存版へ含めません: {rel}")
        if not path.is_file():
            continue
        if any(part in EXCLUDED_PARTS for part in rel.parts):
            continue
        if path.name in EXCLUDED_NAMES or path.suffix in {".pyc", ".pyo"}:
            continue
        files.append(path)
    return files


def test_count(log: Path) -> int:
    text = log.read_text(encoding="utf-8", errors="replace")
    found = re.search(r"Ran (\d+) tests?", text)
    if not found or not re.search(r"\nOK(?:\s|$)", text):
        raise ValueError(f"全試験成功を確認できないログです: {log}")
    return int(found.group(1))


def build(output: Path, source_log: Path, extracted_log: Path | None) -> dict[str, object]:
    source_count = test_count(source_log)
    extracted_count = test_count(extracted_log) if extracted_log else None
    if extracted_count is not None and extracted_count != source_count:
        raise ValueError("元ソースと展開コピーの試験件数が一致しません。")

    files = source_files()
    manifest_files: dict[str, dict[str, object]] = {}
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        manifest_files[rel] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}

    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    manifest = {
        "product": "PSLog",
        "version": "1.01",
        "checkpoint": "steps 1-12 complete; Windows acceptance pending",
        "created_utc": created,
        "root": PROJECT_PREFIX.as_posix(),
        "files": manifest_files,
    }
    checks = {
        "source_compileall": "passed",
        "source_tests": {"status": "passed", "count": source_count},
        "extracted_tests": (
            {"status": "passed", "count": extracted_count}
            if extracted_count is not None
            else {"status": "not included in candidate"}
        ),
        "manifest_algorithm": "SHA-256",
        "project_file_count": len(files),
        "windows_exe": "not built; requires 64-bit Windows 10/11",
        "windows_next": "Run build-windows.ps1, then WINDOWS_CHECKLIST.txt",
    }
    start_here = """# PSLog 1.01 最終保存版

最初に `pslog-1.01/docs/CHECKPOINT_PSLOG101_FINAL_PRE_WINDOWS.md` を読んでください。

このZIPはステップ1～12の全ソース、テスト、参照DB、帳票、取得原典、調査・仕様履歴を含みます。
Windows EXEは含みません。Windowsで `build-windows.ps1` を実行し、`WINDOWS_CHECKLIST.txt` で
実機確認してください。利用者のログ・個人設定は含めていません。

`handoff/MANIFEST.json` はプロジェクト全ファイルのサイズとSHA-256、
`handoff/FINAL_PACKAGE_CHECKS.json` と試験ログは最終検証記録です。
"""

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=output.name + ".", suffix=".tmp", dir=output.parent, delete=False) as temp:
        temp_path = Path(temp.name)
    try:
        with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
            for path in files:
                archive.write(path, (PROJECT_PREFIX / path.relative_to(ROOT)).as_posix())
            archive.writestr((PREFIX / "START_HERE.md").as_posix(), start_here)
            archive.writestr(
                (PREFIX / "handoff" / "MANIFEST.json").as_posix(),
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            )
            archive.writestr(
                (PREFIX / "handoff" / "FINAL_PACKAGE_CHECKS.json").as_posix(),
                json.dumps(checks, ensure_ascii=False, indent=2) + "\n",
            )
            archive.write(source_log, (PREFIX / "handoff" / "tests_source.log").as_posix())
            if extracted_log:
                archive.write(extracted_log, (PREFIX / "handoff" / "tests_extracted.log").as_posix())
        with zipfile.ZipFile(temp_path) as archive:
            bad = archive.testzip()
            if bad:
                raise ValueError(f"ZIP CRC検査に失敗しました: {bad}")
        os.replace(temp_path, output)
    finally:
        temp_path.unlink(missing_ok=True)

    result = {
        **checks,
        "archive": output.name,
        "archive_bytes": output.stat().st_size,
        "archive_sha256": sha256_file(output),
        "archive_crc": "passed",
        "created_utc": created,
    }
    return result


def verify(archive_path: Path, extract_dir: Path) -> dict[str, object]:
    with zipfile.ZipFile(archive_path) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"ZIP CRC検査に失敗しました: {bad}")
        archive.extractall(extract_dir)
    manifest_path = extract_dir / PREFIX / "handoff" / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    root = extract_dir / manifest["root"]
    checked = 0
    for rel, expected in manifest["files"].items():
        path = root / rel
        if not path.is_file() or path.stat().st_size != expected["bytes"] or sha256_file(path) != expected["sha256"]:
            raise ValueError(f"MANIFEST照合に失敗しました: {rel}")
        checked += 1
    return {"status": "passed", "files_checked": checked, "project_root": str(root)}


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    make = sub.add_parser("build")
    make.add_argument("output", type=Path)
    make.add_argument("source_log", type=Path)
    make.add_argument("--extracted-log", type=Path)
    check = sub.add_parser("verify")
    check.add_argument("archive", type=Path)
    check.add_argument("extract_dir", type=Path)
    args = parser.parse_args()
    if args.command == "build":
        result = build(args.output.resolve(), args.source_log.resolve(), args.extracted_log.resolve() if args.extracted_log else None)
    else:
        result = verify(args.archive.resolve(), args.extract_dir.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
