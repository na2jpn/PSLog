from rule_view_verified_remaining71 import apply as apply_remaining_view
"""2026 XPO; no 2025 commemorative bonus. Do not overwrite installed user rules."""
from pathlib import Path
from copy import deepcopy
import json
root=Path(__file__).resolve().parents[1]
r=json.loads((root/'config/rules/six_meter_and_down_2026.txt').read_text());e=r['event']
hf=['1.9','3.5','7','14','21','28'];upper=['2400','5600','10G'];bands=hf+['50','144','430','1200']+upper
r.update(id='xpo',name='XPO記念コンテスト',organizer='JARL関西地方本部',sort_name='えっくすぴーおーきねん',url='https://www.eonet.ne.jp/~ja3-test/kiyaku/xpokinen_2026kiyaku.htm')
regions=e['exchange']['profiles'][0]['codes']
e['exchange']=dict(kind='numbered_region',codes=regions,same_sent_region=True)
e['windows']=[dict(start='2026-09-21 06:00',end='2026-09-21 18:00',bands=bands)]
e['entrant']=dict(station_types=[],guest_policy='mo_only')
e['required_flags']=['国内局同士の完全交信であり、番号は実際に交換した都府県地域番号である','CWはA1A、電話はSSB/AM/FMのみで指定周波数・免許範囲を守った（デジタル音声・A2A/F2Aは対象外）','1コール1種目・ゲストと補助者のMO扱い・同時送信制限を確認した','クロスバンド・レピータ交信・セルフスポットを含めず、リモート設備の同一所在地条件を守った','終了後に未受信情報を調べて番号やコールを補完していない（紙ログ電子化を除く）']
so=['全運用を一人で行い、ゲスト・補助者を伴っていない','運用地は同一場所、又はコンテスト目的で移動したSOの開始時マルチ内のみで変更した']
mo=['全運用者・補助者を提出書類に記載し、同一運用地（直径500m以内）を変更していない']
cats=[]
for p,label,modes in [('C','電信',['CW']),('F','混合',['CW','SSB','AM','FM'])]:
 for suffix,name,bs,minimum,op in [('A','全帯',bands,2,'SO'),('H','HF',hf,2,'SO')]+[({'1.9':'19','3.5':'35'}.get(b,b),b+'MHz',[b],1,'SO') for b in hf+['50','144','430','1200']]+[('2400','2400MHz以上',upper,1,'SO'),('C','全帯',bands,1,'MO')]:
  c=dict(id=p+suffix,name=f'{label} {op} {name}',bands=bs,modes=modes,max_power=None,min_bands=minimum,max_bands=len(bs),min_calls=1,required_flags=deepcopy(so if op=='SO' else mo),operator=op)
  if p=='F':c['required_mode_families']=['phone']
  if suffix=='A':c['excluded_band_subsets']=[hf,upper]
  cats.append(c)
assert len(cats)==28
e['categories']=cats
aliases={b+'MHZ':b for b in bands if b!='10G'}
aliases.update({'1.8':'1.9','1.8MHZ':'1.9','1.2G':'1200','1.2GHZ':'1200','2.4G':'2400','2.4GHZ':'2400','5.6G':'5600','5.6GHZ':'5600','10GHZ':'10G','10.1G':'10G','10.1GHZ':'10G','10.4G':'10G','10.4GHZ':'10G','10100':'10G','10400':'10G','10100MHZ':'10G','10400MHZ':'10G'})
e['normalization']=dict(bands=aliases,modes={'USB':'SSB','LSB':'SSB'},mode_families={})
e['band_modes']={b:['CW','SSB','AM']+(['FM'] if b not in ['1.9','3.5','7','14','21'] else []) for b in bands}
e['submission']=dict(formats=['JARL R1.0','JARL R2.1'],zone='JST',contest='第56回XPO記念コンテスト',required_fields=['email'],instructions='2026年規約・28種目。記念局も1点。全期間の交信を残して参加種目のみ採点。10.1/10.4GHzは10GHzへ統合。ゲスト・補助者を伴う運用はMO。締切2026-10-05、電子23:59まで。電子ログはメール本文、添付不可。共同企画の追加ログは不要です。自動送信しません。')
e['rule_view']={'participants': '日本国内のアマチュア局。電信はCW（A1A）、電話はSSB・AM・FM。ゲストや補助者が運用に関わる場合はマルチオペ。', 'power': '2026年規約に大会独自の一律送信出力上限は記載されていません。免許条件を確認してください。', 'movement': 'コンテスト中の運用場所は原則1か所（直径500mの範囲内）。コンテストのため常置場所を離れたシングルオペのみ、開始時のマルチプライヤー内で場所変更可。移動局はコール末尾に /数字または/JD1を付けます。', 'call_method': '電信：CQ XPO TEST\n電話：CQ XPOコンテスト', 'counterparts': '日本国内のアマチュア局同士の完全な交信。記念局（8J・8K・8N等）も一般局と同じ扱いです。', 'frequency': '1.9～10GHz帯（3.8・10・18・24MHz帯を除く）。1.9～430MHz帯は規約の電波型式別周波数表を参照。1200MHz以上は総務省告示の使用区別に従います。10.1GHzと10.4GHzは同一の10GHz帯として扱います。', 'restrictions': 'クロスバンド交信、同一オペレーターの2波以上の同時発射、マルチオペの同一バンド2波以上の同時発射を禁止。レピーターやインターネット等経由の交信は得点・マルチに計上不可（規約のリモート運用例外あり）。セルフスポットやその依頼は禁止。リモート設備の所在地条件とコンテスト終了後のログ修正制限は公式規約を確認してください。', 'exchange': 'RS(T) ＋ JARL制定の都府県・地域等のナンバー。', 'repeat': '同一局との同一バンド内の再交信は、電波型式が異なっても得点になりません。バンドが異なれば別に計上できます。'};
apply_remaining_view(r)
(root/'config/rules/xpo_2026.txt').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('XPO: 28 categories, numeric region, grouped 10GHz, all-band composition constraints')
