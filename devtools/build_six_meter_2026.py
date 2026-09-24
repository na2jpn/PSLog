"""Offline generator from archived JARL code lists; never fetches or edits user logs."""
from rule_view_verified_15 import apply as apply_rule_view
from pathlib import Path
import json,re,hashlib
from copy import deepcopy
root=Path(__file__).resolve().parents[1]
src=root/'docs/contest-research/sources/6d_number_snapshot_20260914'
rows=[];removed=[];counts={}
for name,kind,lengths in [('jcc-list.txt','city',[4,6]),('jcg-list.txt','county',[5]),('ku-list.txt','ward',[6])]:
 current=[]
 for line in (src/name).read_bytes().decode('cp932').splitlines():
  m=re.match(r'^\s*([*※]?)\s*([0-9]{4,6})\s+(.+)$',line)
  if not m or len(m[2]) not in lengths:continue
  row=dict(code=m[2],label=m[3].strip(),kind=kind,source=name)
  (removed if m[1] else current).append(row)
 counts[kind]=len(current);rows.extend(current)
assert counts==dict(city=815,county=379,ward=171),counts
assert len({x['code'] for x in rows})==len(rows)
parents={x['code'][:4] for x in rows if x['kind']=='ward'}
assert len(parents)==20
for row in rows:row['contest_usable']=row['code'] not in parents
assert {r['code'] for r in rows if r['source']=='ku-list.txt' and r['code'].startswith('1802')}=={'180207','180208','180209'}
meta=dict(year=2026,contest_date='2026-07-04',retrieved='2026-09-14',organizer='JARL',source_versions={'jcc':'2019-05-01','jcg':'2018-10-01','ward':'2024-01-01','history':'2024-01-01'},note='2026大会用スナップショット。取得日と原典更新日を区別。rireki.xlsの最新変更が浜松2024であること、現存815市379郡171区と照合。政令市20親番号は区番号を使うため大会番号から除く。所在地補助用PHP原本は変更しない。',sources=[dict(file=p.name,url='https://www.jarl.org/Japanese/A_Shiryo/A-2_jcc-jcg/'+p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(src.iterdir())],counts=counts,rows=rows,retired=removed)
(root/'config/db/contest/jarl_municipal_2026.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
low=['50','144','430','1200'];high=['2400','5600','10100','10400','24000','47000','77000','135000','248000'];bands=low+high
r=json.loads((root/'config/rules/all_ja_2026.txt').read_text());r.update(id='six_meter_and_down',name='6m AND DOWNコンテスト',year=2026,url='https://www.jarl.org/Japanese/1_Tanoshimo/1-1_Contest/6d_rules.html',sort_name='しっくすめーたーあんどだうん')
phone=['SSB','FM','AM','DV'];allm=['CW']+phone
so=['運用に関わる全作業を一人で行い、同時に複数波を送信していない','運用場所を変更していない、又は移動SOの許可範囲（各番号体系で開始時マルチ内、常置場所との往来なし）のみで変更した']
mo=['日本国内の同一運用地（直径500m以内）で運用し、途中で運用地を変更していない','同一バンドで複数波を同時送信せず、全運用者を提出書類に記載する']
cats=[]
def add(ident,label,bs,modes,power=None,op='SO',qualification=None):
 c=dict(id=ident,name=label,bands=bs,modes=modes,max_power=power,min_bands=1,max_bands=len(bs),min_calls=1,required_flags=deepcopy(so if op=='SO' else mo),operator=op)
 if ident.startswith('X') and ident!='XMJ':c['required_mode_families']=['phone']
 if qualification:c['qualification']=qualification
 cats.append(c);return c
add('PA','電話 SO オールバンド',bands,phone,20)
c=add('PN','電話 SO ニューカマー',bands,phone,20,qualification=dict(license_since='2023-07-04',license_until='2026-07-04'));c['required_flags'].append('初めて開局した個人局で、入力日は再免許日でなく最初の局免許年月日である')
add('PD','電話 SO D-STAR',bands,['DV'],20)
add('PMA','電話 MO オールバンド',bands,phone,20,'MO')
for prefix,label,modes in [('C','電信',['CW']),('X','電信電話',allm)]:
 add(prefix+'A',label+' SO オールバンド',bands,modes)
 for b in low+['2400','5600']:add(prefix+b,label+' SO '+b+'MHz',[b],modes)
 add(prefix+'10G',label+' SO 10.1GHz以上',high[2:],modes)
 c=add(prefix+'S',label+' SO シルバー',bands,modes,qualification=dict(min_age=70));c['required_flags'].append('年齢は実際の運用者の運用時年齢である')
 add(prefix+'P',label+' SO QRP',bands,modes,5)
 add(prefix+'MA',label+' MO オールバンド',bands,modes,None,'MO')
c=add('XMJ','電信電話 MO ジュニア',bands,allm,None,'MO',dict(operators_max_age=18));c['required_flags'].append('全実運用者を年齢付きで入力した（成人の交信担当者を省略していない）')
assert len(cats)==27 and len({c['id'] for c in cats})==27
regions=[x['code'] for x in json.loads((root/'config/db/contest/jarl_area_2026.json').read_text())['areas']]
codes=sorted(x['code'] for x in rows if x['contest_usable'])
# Hokkaido mapping is intentionally not guessed from prefix 01.
parents_map={c:('48' if c=='10007' else c[:2]) for c in codes if not c.startswith('01')}
e=dict(timezone='JST',windows=[dict(start='2026-07-04 21:00',end='2026-07-05 15:00',bands=bands)],categories=cats,required_flags=[
'日本国内局同士の交信であり、相手番号は実際の受信記録である',
'指定周波数・免許範囲を確認し、クロスバンド・電信電話間クロスモード・レピータ交信を含めていない',
'DVと記録した交信はD-STARのデジタル音声かつシンプレックスである（該当なしを含む）',
'低域の送信地域番号と高域の市郡区番号は同じアンテナ所在地を表すことを確認した（北海道の地域区分を含む）',
'参加種目の最大使用電力、各交信の電力文字、1コール1種目、記念局の参加条件、リモート・セルフスポット等の共通規約を確認した',
'終了後の受信内容の補完は行わず、訂正は運用中のメモによる誤記・書式訂正の範囲である'],duplicate_fields=['call','band'],prefer='first',special='none',exchange=dict(kind='jarl_band_power',same_sent_region=True,profiles=[dict(id='region',bands=low,codes=regions,code_lengths=[2,3],m_threshold=20,points=1),dict(id='municipal',bands=high,codes=codes,code_lengths=[4,5,6],m_threshold=20,points=2)],parent_regions=parents_map),normalization=dict(bands={},modes={'D-STAR':'DV','DSTAR':'DV','USB':'SSB','LSB':'SSB'},mode_families={'DV':'phone'}),submission=dict(formats=['JARL R1.0','JARL R2.1'],zone='JST',contest='第56回6m AND DOWNコンテスト',required_fields=['email'],instructions='2026年規約・SWL除外27種目。締切2026-07-15。PN/CS/XSはPSLogではR2.1。移動時は運用地、ゲストSOは運用者コールを記載。DVはD-STARのみ。明示チェックログは交信情報で指定。自動送信しません。'))
for b in bands:e['normalization']['bands'][b+'MHZ']=b
for g,b in [('1.2','1200'),('2.4','2400'),('5.6','5600'),('10.1','10100'),('10.4','10400'),('24','24000'),('47','47000'),('77','77000'),('135','135000'),('248','248000')]:
 for suffix in ('G','GHZ'):e['normalization']['bands'][g+suffix]=b
r['event']=e
apply_rule_view(r)
(root/'config/rules/six_meter_and_down_2026.txt').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('JCC/JCG/ward',counts,'contest codes',len(codes),'categories',len(cats))
