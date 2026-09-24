"""Apply officially reviewed, presentation-only facts for contest entries 16–86."""
from __future__ import annotations
import json
from pathlib import Path

DATA=Path(__file__).with_name('contest_rule_view_verified_remaining71.json')

def apply(rule):
    item=json.loads(DATA.read_text(encoding='utf-8')).get(rule.get('id'))
    if item and rule.get('year')==item['year']:
        rule.setdefault('event',{})['rule_view']=dict(item['rule_view'])
        if 'url' in item:rule['url']=item['url']
    return rule

if __name__=='__main__':
    from sys import path
    root=Path(__file__).resolve().parent.parent
    path.insert(0,str(root))
    from contest_rules import loads,dumps
    for file in sorted((root/'config/rules').glob('*.txt')):
        before=loads(file.read_text(encoding='utf-8-sig'))
        after=apply(before)
        if after != loads(file.read_text(encoding='utf-8-sig')):
            file.write_text(dumps(after)+'\n',encoding='utf-8')
