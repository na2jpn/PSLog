from rule_view_verified_remaining71 import apply as apply_remaining_view
"""Fukuoka 2026: attached regulation is authoritative for the local code list."""
from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parents[1]
city='4007:久留米 4008:大牟田 4009:直方 4010:飯塚 4011:田川 4012:柳川 4015:八女 4016:筑後 4017:大川 4018:行橋 4019:豊前 4020:中間 4022:小郡 4023:春日 4024:筑紫野 4025:大野城 4026:宗像 4027:太宰府 4029:古賀 4030:福津 4031:うきは 4032:宮若 4033:嘉麻 4034:朝倉 4035:みやま 4036:糸島 4037:那珂川'
county='40001:朝倉 40004:遠賀 40005:糟屋 40006:嘉穂 40007:鞍手 40009:田川 40011:築上 40012:三井 40014:三潴 40015:京都 40018:八女'
ward='400101:福岡市東区 400102:福岡市博多区 400103:福岡市中央区 400104:福岡市南区 400105:福岡市西区 400106:福岡市城南区 400107:福岡市早良区 402101:北九州市門司区 402102:北九州市若松区 402103:北九州市戸畑区 402104:北九州市小倉北区 402105:北九州市小倉南区 402106:北九州市八幡東区 402107:北九州市八幡西区'
groups={k:dict(x.split(':') for x in text.split()) for k,text in [('city',city),('county',county),('ward',ward)]};inside=[c for g in groups.values() for c in g];assert [len(g) for g in groups.values()]==[27,11,14]
areas=json.loads((root/'config/db/contest/jarl_area_2026.json').read_text());outside=[v['code'] for v in areas['areas'] if v['code']!='40']
r=json.loads((root/'config/rules/all_chiba_2026.txt').read_text());e=r['event'];r.update(id='fukuoka',name='福岡コンテスト',sort_name='ふくおか',organizer='JARL福岡県支部',url='');r['points']=dict(cw=1,phone=1,digital=0);r['conditions']=[dict(when=dict(field='area',op='in',value=','.join(inside)),points=3)]
L=['1.9','3.5','7'];H=['14','21','28'];A=L+H;VU=['50','144','430'];AB=A+VU
bands=dict(L=L,H=H,A=A,VU=VU,AB=AB);phone=['SSB','AM','FM']
e.pop('band_choices',None);e['windows']=[dict(start='2026-09-12 21:00',end='2026-09-13 00:00',bands=AB),dict(start='2026-09-13 06:00',end='2026-09-13 15:00',bands=AB)]
e['exchange']=dict(kind='numbered_region',codes=inside+outside,same_sent_region=True)
e['power_by_operation']=dict(stationary=100,portable=50)
e['entrant']=dict(station_types=[],guest_policy='allowed');e['duplicate_fields']=['call','band','mode_family'];e['prefer']='first'
e['required_flags']=['国内局として1種目のみ提出し、県内外はコールエリアでなく実運用地で判断した','指定周波数・免許範囲を守り、RS(T)と実際のナンバーの交換が完全である','申告した移動有無と最大電力が全運用の実態に合っている','地方規約にない運用条件はJARLコンテスト規程に従い、クロスバンド・クロスモード・レピータ交信を含めていない','運用者区分と同時送信・移動範囲等の共通規程を確認した']
e['normalization']=dict(bands={b+'MHZ':b for b in AB},modes={'USB':'SSB','LSB':'SSB'},mode_families={});e['normalization']['bands'].update({'1.8':'1.9','1.8MHZ':'1.9'})
e['band_modes']={b:['CW','SSB','AM']+(['FM'] if b not in AB[:5] else []) for b in AB}
cats=[]
for marker,label,sent in [('F','県内',inside),('X','県外',outside)]:
 for group,bs in bands.items():
  for mode,title,modes in [('C','電信',['CW']),('P','電話',phone),('CP','電信電話',['CW']+phone)]:
   code=group+marker+mode
   cats.append(dict(id=code,name=label+' SO '+group+' '+title,bands=bs,modes=modes,max_power=100,min_bands=1,max_bands=len(bs),min_calls=1,operator='SO',required_flags=['クラブ局を含め全運用を一人で行った'],sent_codes=sent))
for code,label,sent in [('MOCP','県内',inside),('MXCP','県外',outside)]:
 cats.append(dict(id=code,name=label+' MO AB 電信電話',bands=AB,modes=['CW']+phone,max_power=100,min_bands=1,max_bands=len(AB),min_calls=1,operator='MO',required_flags=['全運用者のコールを運用者一覧に記入した'],sent_codes=sent,operators_in_comments=True,operator_list_format='calls'))
assert len(cats)==32
e['categories']=cats
e['submission']=dict(formats=['JARL R1.0'],zone='JST',contest='第20回福岡コンテスト',instructions='2026年・添付規約正本の32種目。県外同士も1点と地域マルチ、福岡最低交信条件なし。移動なし100W／移動50W以内（SO/MO共通）。1種目だけ提出。クラブ局の一人運用はSO。MO全員のコールを備考（意見）欄へ。電子JARL R1.0をメール本文へ貼付、添付不可。宛先jf6twp@jarl.com。締切2026-09-24、郵送は同日消印有効・手書きのみ。電子時分の独自締切は設けません。自動送信しません。')
e['rule_view']={'participants': '日本国内のアマチュア局。県内・県外の区分は実際の運用場所によります。クラブ局を1人で運用した場合はシングルオペ。', 'power': '移動しない局は100W以内、移動する局は50W以内。', 'movement': '移動局は50W以内。県内・県外の区分は実際に運用する場所で決まります。', 'call_method': '県内局：電話 CQ 福岡コンテスト／電信 CQ FO TEST\n県外局：電話 CQ 福岡コンテストこちらは県外局／電信 CQ FOX TEST', 'counterparts': '福岡県内局との交信は3点、県外局との交信も1点。県外局同士の交信も得点対象です。', 'frequency': '1.8～430MHz帯（WARCバンドを除く）。JARL制定のコンテスト周波数に従います。', 'exchange': '県内局：RS(T)＋市郡区ナンバー。県外局：RS(T)＋JARL制定の都府県・地域等ナンバー。', 'repeat': '同一局との同一バンドの交信は電信・電話それぞれ1交信ずつ有効。バンドが異なればそれぞれ有効。'};
apply_remaining_view(r)
(root/'config/rules/fukuoka_2026.txt').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
source=root/'docs/contest-research/sources/fukuoka_2026.pdf';db=dict(id='fukuoka_numbers',year=2026,organizer=r['organizer'],source='利用者添付2026-20th-fukuoka-contest-regulations.pdf',source_file=source.name,sha256=hashlib.sha256(source.read_bytes()).hexdigest(),groups=groups,outside=[v for v in areas['areas'] if v['code']!='40'])
(root/'config/db/contest/fukuoka_2026.json').write_text(json.dumps(db,ensure_ascii=False,indent=2)+'\n')
print('Fukuoka: 32 categories, 52 official local numbers, explicit power by operation')
