from rule_view_verified_remaining71 import apply as apply_remaining_view
"""Tokyo CW 2026: dedicated, zero-preserving municipal numbers, not JCC."""
from pathlib import Path
from copy import deepcopy
import hashlib,json
root=Path(__file__).resolve().parents[1]
city_text='002:八王子市 003:立川市 004:武蔵野市 005:三鷹市 006:青梅市 007:府中市 008:昭島市 009:調布市 010:町田市 011:小金井市 012:小平市 013:日野市 014:東村山市 015:国分寺市 016:国立市 019:福生市 020:狛江市 021:東大和市 022:清瀬市 023:東久留米市 024:武蔵村山市 025:多摩市 026:稲城市 028:羽村市 029:あきる野市 030:西東京市'
ward_text='101:千代田区 102:中央区 103:港区 104:新宿区 105:文京区 106:台東区 107:墨田区 108:江東区 109:品川区 110:目黒区 111:大田区 112:世田谷区 113:渋谷区 114:中野区 115:杉並区 116:豊島区 117:北区 118:荒川区 119:板橋区 120:練馬区 121:足立区 122:葛飾区 123:江戸川区'
town_text='201:瑞穂町 202:日の出町 203:檜原村 204:奥多摩町'
island_text='401:大島町 402:利島村 403:新島村 404:神津島村 411:三宅村 412:御蔵島村 421:八丈町 422:青ヶ島村 431:小笠原村'
outside_text='01:北海道 02:青森県 03:岩手県 04:秋田県 05:山形県 06:宮城県 07:福島県 08:新潟県 09:長野県 11:神奈川県 12:千葉県 13:埼玉県 14:茨城県 15:栃木県 16:群馬県 17:山梨県 18:静岡県 19:岐阜県 20:愛知県 21:三重県 22:京都府 23:滋賀県 24:奈良県 25:大阪府 26:和歌山県 27:兵庫県 28:富山県 29:福井県 30:石川県 31:岡山県 32:島根県 33:山口県 34:鳥取県 35:広島県 36:香川県 37:徳島県 38:愛媛県 39:高知県 40:福岡県 41:佐賀県 42:長崎県 43:熊本県 44:大分県 45:宮崎県 46:鹿児島県 47:沖縄県'
groups={name:dict(pair.split(':') for pair in text.split()) for name,text in [('city',city_text),('ward',ward_text),('town',town_text),('island',island_text),('outside',outside_text)]}
inside=[c for name,g in groups.items() if name!='outside' for c in g];outside=list(groups['outside']);codes=inside+outside
assert [len(groups[x]) for x in groups]==[26,23,4,9,46] and len(set(codes))==108
url='https://jarltokyo.com/_media/contest/contest_rules_cw_ver20260826.pdf'
source=root/'docs/contest-research/sources/tokyo_cw_2026.pdf'
db=dict(id='tokyo_cw_numbers',year=2026,version='20260826',organizer='JARL東京都支部',source=url,sha256=hashlib.sha256(source.read_bytes()).hexdigest(),groups=groups)
(root/'config/db/contest/tokyo_cw_2026.json').write_text(json.dumps(db,ensure_ascii=False,indent=2)+'\n')
r=json.loads((root/'config/rules/xpo_2026.txt').read_text());e=r['event'];bands=['3.5','7','14','21','28','50','144','430']
r.update(id='tokyo_cw',name='東京CWコンテスト',organizer='JARL東京都支部',sort_name='とうきょうしーだぶりゅー',url=url)
r['conditions']=[dict(when=dict(field='area',op='in',value=','.join(inside)),points=2)]
e['windows']=[dict(start='2026-10-25 06:00',end='2026-10-25 12:00',bands=bands)]
e['exchange']=dict(kind='numbered_region',codes=codes,same_sent_region=True)
e['entrant']=dict(station_types=['individual'],guest_policy='forbidden')
e['required_flags']=['国内の個人局として本人だけで運用した（社団局・特別局・ゲスト・マルチオペでない）','同一人の別コール運用を行わず、1種目のみ提出する','指定周波数・A1A電信で運用し、A2A/F2A・クロスバンド・同時2波を含めていない','常置場所から離れた移動局の場所変更は開始時と同じマルチの範囲内である','受信番号は大会独自の番号を実際に交換した記録である']
cats=[]
for prefix,label,sent_codes in [('1','都外',outside),('2','都内',inside)]:
 for suffix,bs in [('A',bands)]+[({'3.5':'35'}.get(b,b),[b]) for b in bands]:
  cats.append(dict(id=prefix+'C'+suffix,name=label+' 電信 '+('全帯' if suffix=='A' else bs[0]+'MHz'),bands=bs,modes=['CW'],max_power=None,min_bands=1,max_bands=len(bs),min_calls=1,operator='SO',required_flags=[],sent_codes=sent_codes))
e['categories']=cats;assert len(cats)==18
e['normalization']=dict(bands={b+'MHZ':b for b in bands},modes={},mode_families={})
e['band_modes']={b:['CW'] for b in bands}
def group(name,n=None):return dict(codes=list(groups[name]),min_count=n or len(groups[name]))
e['awards']=[dict(id='all_cities',name='全市賞',groups=[group('city')]),dict(id='all_wards',name='全区賞',groups=[group('ward')]),dict(id='towns_island',name='全郡・島賞',groups=[group('town'),group('island',1)])]
e['submission']=dict(formats=['JARL R1.0'],zone='JST',contest='東京CWコンテスト',instructions='2026年・20260826版、個人局18種目。独自番号：都内2点・都外1点。社団局等は相手としては得点対象ですが、自局の提出は不可。各行に得点・マルチを出力します。希望する大会内アワードだけ申請文を追加。締切2026-11-09必着、専用Web受付又は郵送。自動送信しません。')
apply_remaining_view(r)
(root/'config/rules/tokyo_cw_2026.txt').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('Tokyo CW: 108 codes, 18 categories, three optional awards')
