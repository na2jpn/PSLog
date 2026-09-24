from rule_view_verified_remaining71 import apply as apply_remaining_view
"""Standard Okayama CW/Phone/RTTY event, not the FT8/FT4 event."""
from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parents[1]
r=json.loads((root/'config/rules/all_chiba_2026.txt').read_text());e=r['event'];r.update(id='all_okayama',name='オール岡山コンテスト',sort_name='おーるおかやま',organizer='JARL岡山県支部',url='https://www.jarl.com/okayama/oy-test-rule-2026.html');r['points']=dict(cw=1,phone=1,digital=1);r['conditions']=[]
db=json.loads((root/'config/db/contest/jarl_municipal_2026.json').read_text());local=[x for x in db['rows'] if x['code'].startswith('31') and x['contest_usable']];inside=[x['code'] for x in local];area=json.loads((root/'config/db/contest/jarl_area_2026.json').read_text());outside=[x['code'] for x in area['areas'] if x['code']!='31']
L=['1.9','3.5','7'];H=['14','21','28'];V=['50','144','430','1200','2400'];bands=L+H+V
assert '310101' in inside and '3101' not in inside
e.pop('band_choices',None);e['windows']=[dict(start='2026-09-20 09:00',end='2026-09-20 21:00',bands=bands)]
e['exchange']=dict(kind='numbered_region',codes=inside+outside,same_sent_region=True)
e['entrant']=dict(station_types=['individual','club','special'],guest_policy='allowed',checklog_only_types=['special'])
e['newcomer_claim']=dict(name='ニューカマー記念品',license_since='2023-09-20',license_until='2026-09-20',operators=['SO'],station_types=['individual','club'])
e['duplicate_fields']=['call','band'];e['prefer']='first'
e['normalization']=dict(bands={b+'MHZ':b for b in bands},modes={'USB':'SSB','LSB':'SSB'},mode_families={});e['normalization']['bands'].update({'1.8':'1.9','1.8MHZ':'1.9','1.2G':'1200','1.2GHZ':'1200','2.4G':'2400','2.4GHZ':'2400'})
e['band_modes']={b:['CW','SSB','AM','RTTY']+(['FM'] if b not in bands[:5] else []) for b in bands}
e['required_flags']=['国内局で県内外は実運用地で判断し、県外局の得点相手は岡山県内のみである','電信・電話・RTTY及びL/H/Vはそれぞれ独立した部門として提出する','個人局を複数人で運用した場合はMO、社団局を一人で運用した場合はSOとした','市・区・郡を跨ぐ場所変更をしていない（県外でも同じ県なら移動可とはしない）','クロスバンド・クロスモード・レピータ交信、MOの同一バンド2波同時発射を含めない','指定周波数・免許範囲を守り、コール・RS(T)・番号を交信時に完全交換し、ネット等で事後補記していない','表示は申告得点であり、相手ログとのクロスチェック成立や審査結果を保証するものではない']
cats=[]
for region,label,sent in [('O','県内',inside),('X','県外',outside)]:
 for g,bs in [('L',L),('H',H),('V',V)]:
  for op in ['S','M']:
   for m,title,modes in [('C','電信',['CW']),('P','電話',['SSB','AM','FM']),('D','RTTY',['RTTY'])]:
    for qrp in [False,True]:
     code=g+region+'-'+op+m+('P' if qrp else '')
     c=dict(id=code,name=label+' '+g+' '+('SO' if op=='S' else 'MO')+' '+title+(' QRP' if qrp else ''),bands=bs,modes=modes,max_power=5 if qrp else None,min_bands=1,max_bands=len(bs),min_calls=1,operator='SO' if op=='S' else 'MO',required_flags=[],sent_codes=sent)
     if region=='X':c['eligible']=dict(field='area',op='in',value=','.join(inside))
     cats.append(c)
assert len(cats)==72
e['categories']=cats
e['submission']=dict(formats=['JARL R1.0'],zone='JST',allowed_zones=['JST','UTC'],row_scope='category',contest='第39回オール岡山コンテスト',required_fields=[],instructions='2026年・通常版72種目。CW/電話/RTTY・L/H/V・QRPを個別提出し、FT8版とは混同しません。今回はJARL R1.0出力、受付側の版別互換性は未検証。JST又はUTCを選択し受付画面と一致させてください。特別コール局は全体チェックログを明示選択。新人賞はSOのみ、初開局3年以内・再開局不可の任意申告。締切2026-09-30必着、時分は独自指定しません。公式規約の提出リンクから送信し、再提出は最後のものが受付。oy-test@ja4czm.comは問い合わせ先でメール提出先ではありません。自動提出しません。')
apply_remaining_view(r)
(root/'config/rules/all_okayama_2026.txt').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
source=root/'docs/contest-research/sources/all_okayama_2026.html'
result=dict(id='all_okayama_numbers',year=2026,organizer=r['organizer'],source=r['url'],sha256=hashlib.sha256(source.read_bytes()).hexdigest(),municipal_source_versions=db['source_versions'],inside=local,outside=[x for x in area['areas'] if x['code']!='31'],submission_page='http://contest.jj4kme.mydns.jp/uploadLog.html?20260531_092548_7091',submission_fetch='2026-09-14 web取得502、実パーサー未確認')
(root/'config/db/contest/all_okayama_2026.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('All Okayama: 72 categories;',len(inside),'municipal codes')
