"""One-time development generator for the reviewed ALL JA 2026 category table.
Do not run over user-edited installed rules. This targets the source checkout.
"""
from rule_view_verified_15 import apply as apply_rule_view
from pathlib import Path
import json
from copy import deepcopy
root=Path(__file__).resolve().parents[1]
p=root/'config/rules/all_ja_2026.txt';r=json.loads(p.read_text())
base=deepcopy(next(c for c in r['event']['categories'] if c['id']=='CM2M'))
two={c['id']:deepcopy(c) for c in r['event']['categories'] if c['id'] in ('CM2M','CM2H','XM2M','XM2H')}
bands=['1.9','3.5','7','14','21','28','50'];phone_bands=[b for b in bands if b!='14'];phone=['SSB','USB','LSB','AM','FM'];code=dict(zip(bands,['19','35','7','14','21','28','50']))
so=['運用に関わる全作業を一人で行い、同時に複数波を送信していない','運用場所を変更していない、又は移動SOの許可範囲（開始時地域内、常置場所との往来なし）のみで変更した']
mo=['日本国内の同一運用地（直径500m以内）で運用し、途中で運用地を変更していない','同一バンドで複数波を同時送信せず、全運用者を提出書類に記載する']
def cat(ident,name,bs,modes,operator='SO',power=None,low=None):
 c=dict(id=ident,name=name,bands=bs,modes=modes,max_power=power,min_bands=1,max_bands=len(bs),min_calls=1,operator=operator,required_flags=deepcopy(so if operator=='SO' else mo))
 if low is not None:c['min_power_exclusive']=low
 return c
cats=[]
# Step 1: normal phone SO/MO, and CW/mixed SO/MO power classes.
for ident,name,bs,op in [('PA','電話 SO 全帯',phone_bands,'SO')]+[('P'+code[b],'電話 SO '+b+'MHz',[b],'SO') for b in phone_bands]+[('PMA','電話 MO 全帯',phone_bands,'MO')]:
 c=cat(ident,name,bs,phone,op,20 if '50' in bs else 10);c['power_by_band']={b:20 if b=='50' else 10 for b in bs};cats.append(c)
for mode in ('C','X'):
 modes=['CW'] if mode=='C' else ['CW']+phone;label='電信' if mode=='C' else '電信電話'
 for prefix,bs in [('A',bands)]+[(code[b],[b]) for b in bands]:
  for power,maxp,low in [('H',None,100),('M',100,5),('P',5,None)]:
   c=cat(mode+prefix+power,label+' SO '+('全帯' if prefix=='A' else bs[0]+'MHz')+' '+power,bs,modes,power=maxp,low=low)
   if mode=='X':c['required_mode_families']=['phone']
   cats.append(c)
 for power,maxp,low in [('H',None,100),('M',100,5)]:
  c=cat(mode+'MA'+power,label+' MO 全帯 '+power,bands,modes,'MO',maxp,low)
  if mode=='X':c['required_mode_families']=['phone']
  cats.append(c)
  c=two[mode+'M2'+power];c['required_flags']=mo+['送信は同時に最大2波、異なるバンドで行い、系列1・2を確認した'];cats.append(c)
assert len(cats)==64
# Step 2: special entrant qualifications.
c=cat('PN','電話 SO ニューカマー',phone_bands,phone,power=20);c['power_by_band']={b:20 if b=='50' else 10 for b in phone_bands};c['qualification']=dict(license_since='2023-04-25',license_until='2026-04-25');c['required_flags']+=['初めて開局した個人局で、入力日は再免許日でなく最初の局免許年月日である'];cats.append(c)
for mode in ('C','X'):
 c=cat(mode+'S',('電信' if mode=='C' else '電信電話')+' SO シルバー',bands,['CW'] if mode=='C' else ['CW']+phone);c['qualification']=dict(min_age=70);c['required_flags']+=['年齢は申請者でなく実際の運用者の運用時年齢である']
 if mode=='X':c['required_mode_families']=['phone']
 cats.append(c)
c=cat('XMJ','電信電話 MO ジュニア',bands,['CW']+phone,'MO');c['qualification']=dict(operators_max_age=18);c['required_flags']+=['全ての実運用者を年齢付きで入力した（成人の交信担当者を省略していない）'];cats.append(c)
assert len(cats)==68 and len({c['id'] for c in cats})==68
r['name']='ALL JAコンテスト';r['event']['categories']=cats
r['event']['band_modes']={b:['CW','SSB','USB','LSB','AM']+(['FM'] if b in ('28','50') else []) for b in bands}
r['event']['required_flags']=[s for s in r['event']['required_flags'] if not s.startswith('日本国内の同一運用地') and not s.startswith('全運用者を提出書類')]
r['event']['required_flags']+=['日本国内で運用し、1部門1種目・同一人の別コール提出に関する条件を確認した']
r['event']['submission']['required_fields']=['email']
r['event']['submission']['instructions']='2026年規約。SWLを除く68種目。R2.1推奨、PN/CS/XSは資格情報の出力のためPSLogではR2.1を使用します。2波種目の系列は物理リグ番号ではなく1/2で入力。締切2026-05-06。移動運用時は運用地も記載してください。自動送信しません。'
apply_rule_view(r)
p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('normal + 2TX: 64; qualified categories: 4; total:',len(cats))
