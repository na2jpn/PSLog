"""Reviewed FD 2026: 42 non-SWL categories, scoring windows and two-wave series."""
from rule_view_verified_15 import apply as apply_rule_view
from pathlib import Path
from copy import deepcopy
import json
root=Path(__file__).resolve().parents[1];r=json.loads((root/'config/rules/six_meter_and_down_2026.txt').read_text());e=r['event']
hf=['1.9','3.5','7','14','21','28'];bands=hf+e['windows'][0]['bands'];low20=['50','144','430'];low10=hf+['1200'];high=e['exchange']['profiles'][1]['bands']
region=e['exchange']['profiles'][0]['codes'];municipal=e['exchange']['profiles'][1]['codes']
r.update(id='field_day',name='フィールドデーコンテスト',sort_name='ふぃーるどでー',url='https://www.jarl.org/Japanese/1_Tanoshimo/1-1_Contest/fd_rules.html')
e['windows']=[dict(start='2026-08-01 21:00',end='2026-08-02 15:00',bands=bands)]
e['station_factor']='jarl_fd'
so=deepcopy(next(c for c in e['categories'] if c['id']=='CA')['required_flags'])
mo=deepcopy(next(c for c in e['categories'] if c['id']=='CMA')['required_flags'])
cats=[]
def add(ident,name,bs,modes,power=50,op='SO'):
 c=dict(id=ident,name=name,bands=bs,modes=modes,max_power=power,min_bands=1,max_bands=len(bs),min_calls=1,required_flags=deepcopy(so if op=='SO' else mo),operator=op)
 if ident.startswith('X') and ident!='XMJ':c['required_mode_families']=['phone']
 cats.append(c);return c
phone=['SSB','AM','FM'];phone_bands=[b for b in bands if b!='14']
for ident,name,op in [('PA','電話 SO オールバンド','SO'),('PN','電話 SO ニューカマー','SO'),('PMA','電話 MO オールバンド','MO')]:
 c=add(ident,name,phone_bands,phone,20,op);c['power_by_band']={b:20 if b in low20 else 10 for b in phone_bands}
 if ident=='PN':
  c['qualification']=dict(license_since='2023-08-01',license_until='2026-08-01');c['required_flags'].append('初めて開局した個人局で、入力日は再免許日でなく最初の局免許年月日である')
allja=json.loads((root/'config/rules/all_ja_2026.txt').read_text())
two=deepcopy(next(c for c in allja['event']['categories'] if c['id']=='CM2M')['timing'])
for prefix,label,modes in [('C','電信',['CW']),('X','電信電話',['CW']+phone)]:
 add(prefix+'A',label+' SO オールバンド',bands,modes)
 for b in hf+['50','144','430','1200','2400','5600']:
  code={'1.9':'19','3.5':'35'}.get(b,b);add(prefix+code,label+' SO '+b+'MHz',[b],modes)
 add(prefix+'10G',label+' SO 10.1GHz以上',high[2:],modes)
 c=add(prefix+'S',label+' SO シルバー',bands,modes);c['qualification']=dict(min_age=70);c['required_flags'].append('年齢は実際の運用者の運用時年齢である')
 add(prefix+'P',label+' SO QRP',bands,modes,5)
 c=add(prefix+'AR',label+' SO オールバンドモーニング',bands,modes);c['scoring_windows']=[dict(start='2026-08-02 06:00',end='2026-08-02 12:00')]
 add(prefix+'MA',label+' MO オールバンド',bands,modes,50,'MO')
 c=add(prefix+'M2',label+' MO 2波',bands,modes,50,'MO');c['timing']=deepcopy(two);c['required_flags'].append('送信は同時に最大2波、異なるバンドで行い、系列1・2を確認した')
c=add('XMJ','電信電話 MO ジュニア',bands,['CW']+phone,50,'MO');c['qualification']=dict(operators_max_age=18);c['required_flags'].append('全実運用者を年齢付きで入力した（成人の交信担当者を省略していない）')
assert len(cats)==42 and len({c['id'] for c in cats})==42
e['categories']=cats
e['required_flags']=[f for f in e['required_flags'] if not f.startswith('DVと記録')]
e['required_flags'].append('FDの局種を途中で変更せず、移動局は移動先表記を送出・記録し、全体50W以下で運用した')
e['exchange']['profiles']=[dict(id=i,bands=b,codes=c,code_lengths=l,m_threshold=t,points=1,power_letters=['M','L','P']) for i,b,c,l,t in [('region10',low10,region,[2,3],10),('region20',low20,region,[2,3],20),('municipal',high,municipal,[4,5,6],10)]]
e['normalization']['modes']={'USB':'SSB','LSB':'SSB'};e['normalization']['mode_families']={}
for b in hf:e['normalization']['bands'][b+'MHZ']=b
e['band_modes']={b:['CW','SSB','AM']+(['FM'] if b not in ['1.9','3.5','7','14','21'] else []) for b in bands}
e['submission'].update(jarl_tx=True,contest='第69回フィールドデーコンテスト',instructions='2026年規約。SWLを除く42種目。CAR/XARは日曜06:00～12:00のみ採点。CM2/XM2は送信系列1/2を入力。PN/CS/XSはPSLogではR2.1を使用。FD局種A/B/ホームを選択。Aでは具体運用地と電池・発電機等の供給源を記載。移動Bも運用地必須。締切2026-08-12。自動送信しません。')
apply_rule_view(r)
(root/'config/rules/field_day_2026.txt').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('FD 42 categories: 3 phone, 19 CW, 20 mixed; morning 2, two-wave 2')
