"""Display-only 2026 rule facts verified for the first 15 contest review entries.

Apply after building a contest rule and before serializing it. The overlay
never changes categories, score conditions, confirmation flags or submission
validation; those remain owned by the existing builder.
"""
from __future__ import annotations
import json
from pathlib import Path

DATA=Path(__file__).with_name('contest_rule_view_verified_15.json')

def apply(rule):
    entries=json.loads(DATA.read_text(encoding='utf-8'))
    item=entries.get(rule.get('id'))
    if item and rule.get('year')==item['year']:
        rule['url']=item['url']
        rule.setdefault('event',{})['rule_view']=dict(item['rule_view'])
    return rule
