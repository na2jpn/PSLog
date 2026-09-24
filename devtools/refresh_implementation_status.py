"""Refresh current contest implementation status documentation.

The research notes intentionally retain investigation-time wording such as
"not implemented".  This tool inserts a current-status banner generated from
PSLOG101_CURRENT_AUDIT.json and produces docs/IMPLEMENTATION_STATUS.md so those
historical statements cannot be mistaken for the current implementation state.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs/contest-research/PSLOG101_CURRENT_AUDIT.json"
STATUS_DOC = ROOT / "docs/IMPLEMENTATION_STATUS.md"
START = "<!-- CURRENT_IMPLEMENTATION_STATUS_START -->"
END = "<!-- CURRENT_IMPLEMENTATION_STATUS_END -->"


def clean_runtime(value: str) -> str:
    """Return the runtime path without prose appended after a Japanese colon."""
    return value.split("：", 1)[0].strip()


def runtime_paths(c: dict) -> list[str]:
    values = c.get("runtime_definitions")
    if values:
        return [str(v).strip() for v in values]
    value = clean_runtime(c.get("runtime_definition", ""))
    return [value] if value else []


def label(c: dict) -> str:
    no = c.get("no")
    prefix = f"No.{no} " if no is not None else ""
    return f"{prefix}{c['name']} (`{c['id']}`, {c['year']})"


def banner(contests: list[dict], tests: int) -> str:
    lines = [
        START,
        "> **現在の実装状態（Ver1.02 文書整理 / 2026-09-16）: 実装済み**",
        ">",
    ]
    for c in contests:
        runtimes = runtime_paths(c)
        lines.append(f"> - {label(c)}")
        if runtimes:
            lines.append(">   - 実行定義: " + " / ".join(f"`{runtime}`" for runtime in runtimes))
        gate = c.get("implementation_gate", "").strip()
        if gate:
            lines.append(f">   - 現行監査: {gate}")
    lines.extend([
        f"> - PSLOG101最終監査: **定義済み87 / 未定義0、全体回帰{tests}件合格**。",
        "> - Ver1.01正本はWindows上の全unittestがOKになった状態で受領済み。大会ごとのWindows実機操作・EXE・主催者受付確認は、監査記載どおり別確認です。",
        ">",
        "> **この下に残る「未実装」「未検証」「本体未対応」等は、調査・設計開始時点の履歴です。現在状態の判定には使用しません。**",
        "> 現在状態はこの欄と [`docs/IMPLEMENTATION_STATUS.md`](../IMPLEMENTATION_STATUS.md)、および現行コード・回帰テストを優先してください。",
        END,
        "",
    ])
    return "\n".join(lines)


def update_note(path: Path, contests: list[dict], tests: int) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(
        rf"{re.escape(START)}.*?{re.escape(END)}",
        "",
        text,
        flags=re.S,
    )
    # Obsolete current-tracker references are actively misleading. Historical
    # descriptions remain otherwise untouched.
    text = text.replace(
        "`docs/CONTEST_IMPLEMENTATION_TRACKER.json`",
        "`docs/contest-research/PSLOG101_CURRENT_AUDIT.json`",
    )
    lines = text.splitlines()
    if lines and lines[0].startswith("# "):
        heading = lines[0].rstrip()
        body = "\n".join(lines[1:]).lstrip("\n")
        text = heading + "\n\n" + banner(contests, tests).rstrip() + "\n" + body
    else:
        body = text.lstrip("\n")
        text = banner(contests, tests).rstrip() + "\n" + body
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def make_status_doc(audit: dict) -> str:
    contests = audit["contests"]
    rows = []
    for c in contests:
        no = "—" if c.get("no") is None else str(c["no"])
        runtimes = runtime_paths(c)
        runtime = "<br>".join(f"`{v}`" for v in runtimes)
        note = c.get("implementation_note", "")
        gate = c.get("implementation_gate", "").replace("|", "\\|")
        rows.append(f"|{no}|`{c['id']}`|{c['name']}|**実装済み**|{runtime}|{gate}|`{note}`|")
    return "\n".join([
        "# PSLog Ver1.03 — 現在の実装状況",
        "",
        "更新: **2026-09-16**（Ver1.02 文書整理の開始時点）",
        "",
        "この文書は、調査メモに残る過去の「未実装」表記と現在の実装状態を混同しないための入口です。",
        "現行状態を判断するときは **コード＋回帰テスト → この一覧 → 個別調査メモの現在状態欄 → 調査履歴** の順で参照します。",
        "",
        "## 現在の結論",
        "",
        f"- 管理項目: **{audit['defined']} / {audit['defined']} 実装定義済み**、未定義 **{audit['undefined']}**。",
        f"- PSLOG101最終監査時の全体回帰: **{audit['tests']}件合格**（Qt offscreen）。",
        "- Ver1.01正本は、利用者側Windowsで全unittestが **OK** になった状態のソースを基準としている。",
        "- 大会ごとのWindows実機操作、EXEでの確認、主催者受付・実提出受理は、各項目の監査欄どおり別確認。",
        "- 個別調査メモ本文中の「未実装」「未検証」「本体未対応」「ルール未作成」は調査時点の履歴で、現状を表さない。",
        "- 紙提出の完全再現など、意図的に現版の対象外とした機能は『大会そのものが未実装』とは区別する。",
        "",
        "## 状態の読み方",
        "",
        "**実装済み**は、その管理項目に実行定義が存在し、現行監査で未定義扱いではないことを示します。",
        "『主催者受付未検証』『Windows実機未検証』等は、実装の有無ではなく外部・実機での最終確認状態です。",
        "規約に明記されない条件を勝手に補完しない方針もそのまま維持します。",
        "",
        "## 管理項目一覧",
        "",
        "|No.|ID|大会|現在状態|実行定義|実装・確認メモ|調査メモ|",
        "|---:|---|---|---|---|---|---|",
        *rows,
        "",
        "## 元データ",
        "",
        "- `docs/contest-research/PSLOG101_CURRENT_AUDIT.json` — 87項目の機械可読な最終監査。",
        "- `docs/contest-research/PSLOG101_CURRENT_AUDIT.md` — 方針再確認と全体試験の説明。",
        "- `docs/CONTEST_RESEARCH_ALL.md` — 調査履歴を含む累積資料。本文中の古い状態表記より本書を優先。",
        "",
        "この一覧は `python devtools/refresh_implementation_status.py` で監査JSONから再生成できます。",
        "",
    ])


def main() -> None:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    if audit.get("undefined") != 0:
        raise SystemExit("Audit contains undefined implementation items; refusing to mark all as implemented.")
    grouped: dict[str, list[dict]] = defaultdict(list)
    for c in audit["contests"]:
        note = c.get("implementation_note")
        if not note:
            raise SystemExit(f"Missing implementation_note: {c.get('id')}")
        grouped[note].append(c)
        for runtime in runtime_paths(c):
            if not (ROOT / runtime).exists():
                raise SystemExit(f"Runtime definition missing for {c.get('id')}: {runtime}")
    for note, contests in grouped.items():
        path = ROOT / note
        if not path.exists():
            raise SystemExit(f"Implementation note missing: {note}")
        update_note(path, contests, audit["tests"])
    STATUS_DOC.write_text(make_status_doc(audit), encoding="utf-8")
    print(f"updated {len(grouped)} research notes for {len(audit['contests'])} implementation items")
    print(f"wrote {STATUS_DOC.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
