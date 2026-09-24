"""Offline generator from the reviewed 2026 ACAG memo and JARL code snapshot."""
from rule_view_verified_15 import apply as apply_rule_view
from pathlib import Path
from copy import deepcopy
import json
root=Path(__file__).resolve().parents[1]
r=json.loads((root/'config/rules/all_ja_2026.txt').read_text())
fd=json.loads((root/'config/rules/field_day_2026.txt').read_text())
e=r['event'];bands=fd['event']['windows'][0]['bands'];vhf=['50','144','430'];high=bands[bands.index('10100'):]
r.update(id='all_ja_cg',name='全市全郡コンテスト',sort_name='ぜんしぜんぐん',url='https://www.jarl.org/Japanese/1_Tanoshimo/1-1_Contest/acag_rules.html')
e['windows']=[dict(start='2026-10-10 21:00',end='2026-10-11 21:00',bands=bands)]
cats=e['categories']
for c in cats:
 if c['id'] in ('PA','PN','PMA'):c['bands']=[b for b in bands if b!='14']
 elif len(c['bands'])>1:c['bands']=deepcopy(bands)
 c['max_bands']=len(c['bands'])
 if c.get('power_by_band'):c['power_by_band']={b:20 if b in vhf else 10 for b in c['bands']}
 if c['id']=='PN':c['qualification'].update(license_since='2023-10-10',license_until='2026-10-10')
 c['required_flags']=[s.replace('開始時地域内','開始時市郡区内') for s in c['required_flags']]
for p in ('C','X'):
 base=next(c for c in cats if c['id']==p+'S')
 for b in ['144','430','1200','2400','5600','10G']:
  c=deepcopy(base);c.pop('qualification');c['required_flags']=[f for f in c['required_flags'] if not f.startswith('年齢は')]
  c.update(id=p+b,name=('電信' if p=='C' else '電信電話')+' SO '+('10.1GHz以上' if b=='10G' else b+'MHz'),bands=high if b=='10G' else [b],max_bands=len(high) if b=='10G' else 1)
  cats.append(c)
assert len(cats)==80 and len({c['id'] for c in cats})==80
codes=fd['event']['exchange']['profiles'][2]['codes']
e['exchange']=dict(kind='jarl_band_power',same_sent_region=True,same_sent_region_across_profiles=True,profiles=[dict(id=ident,bands=bs,codes=codes,code_lengths=[4,5,6],m_threshold=t,points=1) for ident,bs,t in [('municipal10',[b for b in bands if b not in vhf],10),('municipal20',vhf,20)]])
e['normalization']=deepcopy(fd['event']['normalization']);e['normalization']['bands'].update({'1.8':'1.9','1.8MHZ':'1.9'})
e['band_modes']=deepcopy(fd['event']['band_modes'])
e['required_flags'].append('送信番号は同じ運用市郡区の番号であり、政令市は市番号でなく区番号を使用した')
e['submission'].update(contest='第47回全市全郡コンテスト',instructions='2026年規約・SWL除外80種目。締切2026-10-21必着。市郡区番号＋出力文字。PN/CS/XSはPSLogではR2.1。2波種目のみ系列1/2を記載。種目外の交信も提出に残します。申告得点であり主催者審査前です。')
apply_rule_view(r)
(root/'config/rules/all_ja_cg_2026.txt').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('ACAG: 80 categories, municipal number profiles, four two-wave categories')
