from rule_view_verified_remaining71 import apply as apply_remaining_view
"""All Osaka 2026: archived PDF/HTML plus confirmed F19 and location clarification."""
from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parents[1]
r=json.loads((root/'config/rules/all_chiba_2026.txt').read_text());e=r['event']
municipal=json.loads((root/'config/db/contest/jarl_municipal_2026.json').read_text());local=[v for v in municipal['rows'] if v['code'].startswith('25') and v['contest_usable']];inside=[v['code'] for v in local]
areas=json.loads((root/'config/db/contest/jarl_area_2026.json').read_text());outside=[v['code'] for v in areas['areas'] if v['code']!='25'];bands=['1.9','3.5','7','14','21','28','50','144','430','1200','2400']
url='https://ja3ujr.sakura.ne.jp/jarlosaka/contest/kiyaku2026.html'
r.update(id='all_osaka',name='オール大阪コンテスト',sort_name='おーるおおさか',organizer='JARL大阪府支部',url=url);r['conditions']=[];r['points']=dict(cw=1,phone=1,digital=1)
e.pop('band_choices',None);e['windows']=[dict(start='2026-11-01 06:00',end='2026-11-01 18:00',bands=bands)]
e['exchange']=dict(kind='tagged_region',codes=inside+outside,local_codes=inside,same_sent_region=True,tag_points=dict(Y=2,X=4),operator_tag='Y',special_tag='X',special_calls={'JA3YRL':inside,'JK3ZKX':['2506']},young_below=20,reference_date='2026-11-01')
e['entrant']=dict(station_types=[],guest_policy='allowed');e['duplicate_fields']=['call','band'];e['prefer']='first'
e['required_flags']=['国内局で、府内外は今回の提出部門の実運用地で判断した','電信・電話・RTTY・SSTVを独立提出し、同一部門へ複数種目を提出していない','同一部門内で運用場所を変更せず、MO複数地点・個人局同時2波以上を行っていない','規約指定周波数と免許範囲を守り、クロスバンド・クロスモード・レピータ交信を含めていない','Y/Xは実際に交換した文字で、Y送信は各交信の実担当者による該当である']
e['operating_locations']=dict(groups=dict(cw='電信',phone='電話',digital='デジタル'),matches=dict(digital=['cw','phone']))
e['normalization']=dict(bands={b+'MHZ':b for b in bands},modes={'USB':'SSB','LSB':'SSB'},mode_families={})
e['normalization']['bands'].update({'1.8':'1.9','1.8MHZ':'1.9','1.2G':'1200','1.2GHZ':'1200','2.4G':'2400','2.4GHZ':'2400'})
e['band_modes']={b:['CW','SSB','AM','RTTY','SSTV']+(['FM'] if b not in bands[:5] else []) for b in bands}
cats=[]
for tail,label,sent in [('-O','府内',inside),('','府外',outside)]:
 for prefix,modes,group,start,end in [('C',['CW'],'cw','06:00','11:30'),('F',['SSB','AM','FM'],'phone','12:30','18:00')]:
  spec=[('M',bands,'SO')]+[({'1.9':'19','3.5':'35'}.get(b,b),[b],'SO') for b in bands]+[('A',bands,'MO')]
  if tail:spec.append(('YLM',bands,'SO'))
  for suffix,bs,op in spec:
   ident=prefix+suffix+tail;public=prefix+'Y/LM-O' if suffix=='YLM' else ident
   c=dict(id=ident,submission_code=public,name=label+' '+('電信 ' if prefix=='C' else '電話 ')+public,bands=bs,modes=modes,max_power=None,min_bands=1,max_bands=len(bs),min_calls=1,operator=op,required_flags=['全運用者のコールサイン・氏名・無線従事者資格を運用者一覧に記載した'] if op=='MO' else ['全運用を一人で行った'],sent_codes=sent,location_group=group,scoring_windows=[dict(start='2026-11-01 '+start,end='2026-11-01 '+end)])
   if not tail:c['eligible']=dict(field='area',op='in',value=','.join(inside))
   if op=='MO':c['operators_in_comments']=True
   if suffix=='YLM':c['qualification']=dict(yl_or_younger_than=20,reference_date='2026-11-01')
   cats.append(c)
 for mode in ['RTTY','SSTV']:
  ident=mode+tail;c=dict(id=ident,name=label+' '+mode+' 全帯',bands=bands,modes=[mode],max_power=None,min_bands=1,max_bands=len(bands),min_calls=1,mo_operators_in_comments=True,required_flags=['デジタル運用時は、実際の電信又は電話の運用地と同じ場所であることを確認した','MOの場合は全運用者のコールサイン・氏名・無線従事者資格を意見欄にも記載した'],sent_codes=sent,location_group='digital')
  if not tail:c['eligible']=dict(field='area',op='in',value=','.join(inside))
  cats.append(c)
assert len(cats)==58
e['categories']=cats
e['submission']=dict(formats=['JARL R1.0'],zone='JST',contest='第33回オール大阪コンテスト',required_fields=[],instructions='2026年・58種目。電話1.9MHzのF19/F19-OはHTML表と利用者確認に基づき有効。CW/電話/RTTY/SSTVは別提出。R1.0出力（Ver2の案内からR2.1受理を推定しません）。MOは全OPコール・氏名・資格を意見欄へ。YLは性別、若年は生年月日を意見欄へ。メール本文へサマリーとログを貼付、添付不可。件名はコール＋種目コード。2026宛先allosaka-33@jr3yrl.net、毎年変更。締切2026-11-16 23:59、郵送同日消印有効。自動送信しません。')
apply_remaining_view(r)
(root/'config/rules/all_osaka_2026.txt').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
db=dict(id='all_osaka_numbers',year=2026,organizer=r['organizer'],source=url,sources=[dict(file=n,sha256=hashlib.sha256((root/'docs/contest-research/sources'/n).read_bytes()).hexdigest()) for n in ['all_osaka_2026.pdf','all_osaka_2026.html']],municipal_source_versions=municipal['source_versions'],inside=local,outside=[v for v in areas['areas'] if v['code']!='25'],special_calls=e['exchange']['special_calls'])
(root/'config/db/contest/all_osaka_2026.json').write_text(json.dumps(db,ensure_ascii=False,indent=2)+'\n')
print('Osaka: 58 categories;',len(inside),'local codes')
