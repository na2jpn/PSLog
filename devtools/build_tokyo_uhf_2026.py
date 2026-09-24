from rule_view_verified_remaining71 import apply as apply_remaining_view
"""Tokyo UHF 20260826 edition: explicit 10GHz subbands and young categories."""
from pathlib import Path
from copy import deepcopy
import json,hashlib
root=Path(__file__).resolve().parents[1]
r=json.loads((root/'config/rules/tokyo_cw_2026.txt').read_text());e=r['event']
six=json.loads((root/'config/rules/six_meter_and_down_2026.txt').read_text());bands=six['event']['windows'][0]['bands'][2:]
inside=next(c for c in e['categories'] if c['id']=='2CA')['sent_codes'];outside=next(c for c in e['categories'] if c['id']=='1CA')['sent_codes']
url='https://jarltokyo.com/_media/contest/contest_rules_uhf_ver20260826.pdf'
r.update(id='tokyo_uhf',name='東京UHFコンテスト',sort_name='とうきょうゆーえいちえふ',url=url)
e['windows']=[dict(start='2026-11-23 09:00',end='2026-11-23 15:00',bands=bands)]
e['required_flags']=['国内の個人局として本人だけで運用し、社団局等・ゲスト・マルチオペではない','同一人の別コール運用・同時2波・クロスバンドを行わず、1種目だけ提出する','電波型式は自局の許可範囲で、430はJARLコンテスト帯・1200以上はバンドプランに従い、A2A/F2Aの使用区分も確認した','移動局の運用地変更は開始時のマルチ内の許可範囲だけである','大会独自の番号を実際に交換し、未受信情報の補完をしていない']
e.pop('band_modes',None);e['normalization']=deepcopy(six['event']['normalization']);e['normalization']['bands'].update({'10GHZ':'10G'});e['normalization']['mode_families'].update({'C4FM':'phone','DMR':'phone','FREEDV':'phone'})
e['band_choices']={'10G':['10100','10400']}
cats=[]
for prefix,label,codes in [('1','都内',inside),('2','都外',outside)]:
 for suffix,bs in [('A',bands),('430',['430']),('1200',['1200']),('2400',['2400']),('5600',['5600']),('10G',['10100','10400'])]:
  cats.append(dict(id=prefix+'X'+suffix,name=label+' 一般 '+('全帯' if suffix=='A' else suffix+'MHz' if suffix!='10G' else '10GHz'),bands=bs,modes=['*'],max_power=None,min_bands=1,max_bands=len(bs),min_calls=1,operator='SO',required_flags=[],sent_codes=codes))
 for suffix,bs in [('A',['430','1200']),('430',['430']),('1200',['1200'])]:
  cats.append(dict(id=prefix+'Y'+suffix,name=label+' ヤング '+('全帯' if suffix=='A' else suffix+'MHz'),bands=bs,modes=['*'],max_power=None,min_bands=1,max_bands=len(bs),min_calls=1,operator='SO',required_flags=['ヤングで参加する全運用履歴を含め、1200MHzを超える運用を行っていない'],sent_codes=codes,qualification=dict(max_age=18,age_output='comments'),operation_bands=['430','1200'],fallback_category=prefix+'X'+suffix))
e['categories']=cats;assert len(cats)==18
e['submission']=dict(formats=['JARL R1.0'],zone='JST',contest='東京UHFコンテスト',instructions='2026年・20260826版、18種目。都内1／都外2。10Gは10.1/10.4GHzを別バンドで集計。不明な10Gは交信情報補完で選択。ヤングは18歳以下・430/1200のみ、年齢を意見に記載。締切2026-12-07必着、専用Web又は郵送。自動提出しません。')
apply_remaining_view(r)
(root/'config/rules/tokyo_uhf_2026.txt').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
db=json.loads((root/'config/db/contest/tokyo_cw_2026.json').read_text());db.update(id='tokyo_uhf_numbers',source=url,sha256=hashlib.sha256((root/'docs/contest-research/sources/tokyo_uhf_2026.pdf').read_bytes()).hexdigest())
(root/'config/db/contest/tokyo_uhf_2026.json').write_text(json.dumps(db,ensure_ascii=False,indent=2)+'\n')
print('Tokyo UHF: 18 categories, 10GHz choices, young age in comments')
