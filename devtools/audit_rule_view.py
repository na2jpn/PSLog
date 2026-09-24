"""Audit display-only contest rule facts.

This is a developer aid.  Rule-view text must come from official/source material
and must not be inferred from submission-blocking confirmations.
"""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
FIELDS=('participants','power','movement','call_method','counterparts','frequency','restrictions','exchange','repeat')


def main():
    rows=[]
    for path in sorted((ROOT/'config'/'rules').glob('*.txt')):
        try:rule=json.loads(path.read_text(encoding='utf-8-sig'))
        except Exception:continue
        view=(rule.get('event',{}) or {}).get('rule_view',{}) or {}
        missing=[field for field in FIELDS if not str(view.get(field,'')).strip()]
        rows.append((rule.get('id',path.stem),rule.get('name',''),missing))
    complete=sum(not missing for _,_,missing in rows)
    print(f'contest rules: {len(rows)} / complete explicit rule_view: {complete}')
    for ident,name,missing in rows:
        if missing:print(f'{ident}\t{name}\tmissing: {", ".join(missing)}')

if __name__=='__main__':main()
