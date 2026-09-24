from rule_view_verified_remaining71 import apply as apply_remaining_view
"""All Chiba 2026 from archived official PDF and confirmed user clarifications."""
from pathlib import Path
from copy import deepcopy
import json,hashlib
root=Path(__file__).resolve().parents[1]
r=json.loads((root/'config/rules/tokyo_uhf_2026.txt').read_text());e=r['event']
municipal=json.loads((root/'config/db/contest/jarl_municipal_2026.json').read_text())
local=[v for v in municipal['rows'] if v['code'].startswith('12') and v['contest_usable']]
inside=[v['code'] for v in local];area=json.loads((root/'config/db/contest/jarl_area_2026.json').read_text());outside=[v['code'] for v in area['areas'] if v['code']!='12']
assert '120101' in inside and '1201' not in inside and '12' not in outside
bands=['1.9','3.5','7','14','21','28','50','144','430','1200','2400','5600','10100','10400','24000','47000','77000','135000','248000'];normal=bands[:11];qrp=bands[:9];upper=bands[10:]
phone=['SSB','AM','FM','DV','C4FM','DMR','FREEDV'];mixed=['CW']+phone
url='http://jarl-chiba.info/2026test/2026info.pdf'
r.update(id='all_chiba',name='オール千葉コンテスト',sort_name='おーるちば',organizer='JARL千葉県支部',url=url)
r['points']=dict(cw=2,phone=1,digital=0)
r['conditions']=[dict(when={'all':[dict(field='area',op='in',value=','.join(inside)),{'any':[dict(field='mode',op='eq',value='CW'),dict(field='mode',op='starts',value='CW ')]}]},points=3),dict(when=dict(field='area',op='in',value=','.join(inside)),points=2)]
e['windows']=[dict(start='2026-10-18 12:00',end='2026-10-18 18:00',bands=bands)]
e.pop('awards',None);e['exchange']=dict(kind='numbered_region',codes=inside+outside,same_sent_region=True)
e['entrant']=dict(station_types=['individual','club'],guest_policy='allowed')
e['duplicate_fields']=['call','band','mode_family'];e['prefer']='first'
e['required_flags']=['国内局として1部門のみ提出し、県内外は実運用地で判断した','指定周波数・免許範囲を守り、電話のデジタルは音声のみ（RTTY・FT8等を含めない）','番号変更を伴う移動、クロスバンド・クロスモード・レピータ・セルフスポットを行っていない','SO同時2波以上、MO複数地点・同一バンド同時2波以上を行っていない','実際に交換した番号を使用し、千葉市は区番号まで確認した']
e['normalization']['bands'].update({b+'MHZ':b for b in bands});e['normalization']['bands'].update({'1.8':'1.9','1.8MHZ':'1.9'})
e['normalization']['modes']={'USB':'SSB','LSB':'SSB','DSTAR':'DV','D-STAR':'DV'};e['normalization']['mode_families']={m:'phone' for m in phone}
e['band_modes']={b:[m for m in mixed if m!='FM' or b not in bands[:5]] for b in bands}
cats=[]
specs=[('CW','CW',normal,['CW']),('PHONE','電話',normal,phone),('MIX','MIX',normal,mixed),('19','1.9',['1.9'],mixed),('35','3.5',['3.5'],mixed),('7CW','7CW',['7'],['CW']),('7PHONE','7電話',['7'],phone),('7','7',['7'],mixed)]+[(b,b,[b],mixed) for b in ['14','21','28','50','144','430','1200']]+[('2400UP','2400UP',upper,mixed),('JUNIOR','ジュニア',normal,mixed),('NEWCOMER','ニューカマー',bands,mixed),('QRP_CW','QRP CW',qrp,['CW']),('QRP','QRP',qrp,mixed),('CLUB','社団',bands,mixed)]
for prefix,label,sent in [('C','県内',inside),('X','県外',outside)]:
 for ident,code,bs,modes in specs:
  club=ident=='CLUB';flags=['全運用者の姓名・無線従事者資格を運用者一覧へ記載した'] if club else ['個人局で全運用を一人で行った（個人局MOではない）']
  c=dict(id=prefix+'-'+ident,submission_code=prefix+'-'+code,name=label+' '+code,bands=bs,modes=modes,max_power=5 if ident.startswith('QRP') else None,min_bands=1,max_bands=len(bs),min_calls=1,required_flags=flags,sent_codes=sent,station_types=['club' if club else 'individual'])
  if club:c['operators_in_comments']=True
  else:c['operator']='SO'
  if prefix=='X':c['eligible']=dict(field='area',op='in',value=','.join(inside))
  if ident=='JUNIOR':c['qualification']=dict(max_age=18,age_output='comments')
  if ident=='NEWCOMER':c['qualification']=dict(license_since='2023-10-18',license_until='2026-10-18',license_output='comments');c['required_flags'].append('今回が初めての個人局開設であり、再開局・再免許の日付ではない')
  cats.append(c)
assert len(cats)==42
e['categories']=cats
e['submission']=dict(formats=['JARL R1.0'],zone='JST',contest='第41回オール千葉コンテスト',required_fields=['opplace'],club_entry=dict(prefix='12-',station_types=['individual']),instructions='2026年・42種目、1部門のみ。公式の日本語種目コードを保持します。ジュニア年齢・ニューカマー初回局免許年月日・社団全運用者の姓名と資格は意見欄。メール本文又は添付でサマリーとログを1本に連結、chiba-test@jarl-chiba.info。件名はコール-参加部門（再提出時は-再提出）。再提出には自動返信なし。電子締切2026-11-08 23:59送出、紙は同日消印有効・全記入手書き。県内登録クラブ対抗は12-xx-xxの所属個人局のみ。自動提出しません。')
apply_remaining_view(r)
(root/'config/rules/all_chiba_2026.txt').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
db=dict(id='all_chiba_numbers',year=2026,organizer=r['organizer'],source=url,sha256=hashlib.sha256((root/'docs/contest-research/sources/all_chiba_2026.pdf').read_bytes()).hexdigest(),municipal_source_versions=municipal['source_versions'],inside=local,outside=[v for v in area['areas'] if v['code']!='12'])
(root/'config/db/contest/all_chiba_2026.json').write_text(json.dumps(db,ensure_ascii=False,indent=2)+'\n')
print('All Chiba: 42 categories;',len(inside),'local codes;',len(outside),'outside codes')
