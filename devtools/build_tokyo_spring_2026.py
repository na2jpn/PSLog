from rule_view_verified_remaining71 import apply as apply_remaining_view
"""2026 spring contest based on the user-designated 2024-03-31 regulation.
No proposed 2027 changes. Do not overwrite the newer CW/UHF definitions.
"""
from pathlib import Path
from copy import deepcopy
import json,hashlib
root=Path(__file__).resolve().parents[1]
r=json.loads((root/'config/rules/tokyo_cw_2026.txt').read_text());e=r['event'];bands=['21','28','50','144']
inside=next(c for c in e['categories'] if c['id']=='2CA')['sent_codes'];outside=next(c for c in e['categories'] if c['id']=='1CA')['sent_codes']
url='https://jarltokyo.com/_media/contest/contest_rules_ver20240331.pdf'
r.update(id='tokyo',name='東京コンテスト',sort_name='とうきょう',url=url)
e['windows']=[dict(start='2026-05-03 09:00',end='2026-05-03 15:00',bands=bands)]
e['required_flags']=['2026年開催に2024-03-31改定規約を適用し、2027年変更予告を適用しない','国内個人局の本人運用で、社団等・ゲスト・MOでなく、同一人の別コール運用・同時2波をしていない','指定周波数と免許範囲を守り、クロスバンド交信を含めていない','移動SOの場所変更は開始時マルチ内の許可範囲のみである','実際の交換番号を使い、事後に未受信情報を補完していない']
phone=['SSB','AM','FM','DV','C4FM','DMR','FREEDV'];e['normalization']=dict(bands={b+'MHZ':b for b in bands},modes={'USB':'SSB','LSB':'SSB','DSTAR':'DV','D-STAR':'DV'},mode_families={m:'phone' for m in phone})
e['band_modes']={b:['CW']+[m for m in phone if b!='21' or m!='FM'] for b in bands}
cats=[]
for prefix,label,codes in [('1','都内',inside),('2','都外',outside)]:
 for mode,mlabel in [('C','電信'),('X','電信電話'),('Y','ヤング電信電話')]:
  for suffix,bs in [('A',bands)]+[(b,[b]) for b in bands]:
   c=dict(id=prefix+mode+suffix,name=label+' '+mlabel+' '+('全帯' if suffix=='A' else suffix+'MHz'),bands=bs,modes=['CW'] if mode=='C' else ['CW']+phone,max_power=None,min_bands=1,max_bands=len(bs),min_calls=1,operator='SO',required_flags=[],sent_codes=codes)
   if mode!='C':c['required_mode_families']=['phone']
   if mode=='Y':c.update(qualification=dict(max_age=18,age_output='comments'),fallback_category=prefix+'X'+suffix)
   cats.append(c)
e['categories']=cats;assert len(cats)==30
e['submission']=dict(formats=['JARL R1.0'],zone='JST',contest='東京コンテスト',instructions='2026年用・原典改定2024-03-31。30種目、都内1／都外2。ヤング年齢は意見に記載。2026-05-17締切の過去ログ再現用。開催当時のメール受付は閉鎖済みで現行提出先として案内しません。2027予告は未適用。自動提出しません。')
apply_remaining_view(r)
(root/'config/rules/tokyo_2026.txt').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
db=json.loads((root/'config/db/contest/tokyo_cw_2026.json').read_text());db.update(id='tokyo_numbers',year=2026,version='20240331',source=url,sha256=hashlib.sha256((root/'docs/contest-research/sources/tokyo_rules_20240331_for_2026.pdf').read_bytes()).hexdigest())
(root/'config/db/contest/tokyo_2026.json').write_text(json.dumps(db,ensure_ascii=False,indent=2)+'\n')
print('Tokyo spring: 30 categories, 2026 event / 20240331 source, no 2027 changes')
