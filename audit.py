"""Read-only audit and annual import plan: python audit.py source --call JH1HST."""
import argparse
import json
from pathlib import Path
from dataclasses import asdict
from storage import Repository, import_plan, VERSION

def main():
    p=argparse.ArgumentParser(description='PSLog読み取り検査。原本への書き込みは行いません。')
    p.add_argument('source');p.add_argument('--call',required=True);p.add_argument('--suffix',default='')
    p.add_argument('--root',default='data');p.add_argument('--report',required=True)
    a=p.parse_args()
    log,plans=import_plan(Repository(a.root),a.source,a.call,a.suffix)
    report={'version':VERSION,'source':str(Path(a.source).resolve()),'lines':len(log.lines),
        'records':len(log.records),'issues':[asdict(x) for x in log.issues],
        'notices':[asdict(x) for x in log.notices],
        'warning':'振り分けは指定自局の仮計画です。区切り行の/JD1等は人が確認してください。実際の取り込みは行っていません。',
        'annual_plan':[{'file':p.name,'add':len(v['records']),'skip':v['skipped']} for p,v in plans.items()]}
    with Path(a.report).open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
    print(f"{len(log.records)}交信を読取、問題{len(log.issues)}行。レポート: {a.report}")

if __name__=='__main__':main()
