from rule_view_verified_remaining71 import apply as apply_remaining_view
"""Reviewed 2026 AI contest. Offline development generator, not an updater."""
from pathlib import Path
from copy import deepcopy
import json
root=Path(__file__).resolve().parents[1]
r=json.loads((root/'config/rules/xpo_2026.txt').read_text());e=r['event']
fd=json.loads((root/'config/rules/field_day_2026.txt').read_text())
bands=fd['event']['windows'][0]['bands'];hf=bands[:6];low=hf[:3];high=hf[3:];vu=bands[6:];ghz=bands[bands.index('1200'):]
r.update(id='ai_chikyu',name='愛・地球博記念コンテスト',sort_name='あいちきゅうはくきねん',organizer='JARL東海地方本部',url='https://www.tokai-jarl.jp/tkitest/regulation/21st-ai.html')
e['windows']=[dict(start='2026-09-22 21:00',end='2026-09-23 00:00',bands=bands),dict(start='2026-09-23 06:00',end='2026-09-23 12:00',bands=bands)]
e['normalization']=deepcopy(fd['event']['normalization']);e['normalization']['modes'].update({'DSTAR':'DV','D-STAR':'DV'});e['normalization']['mode_families']={'DV':'phone'}
e['mode_groups']={'CW':'cw','SSB':'phone','AM':'phone','FM':'phone','DV':'dstar'};e['duplicate_fields']=['call','band','mode_group']
e['mode_confirmations']={'DV':'DV／D-STARの交信はD-STAR方式のデジタル音声かつシンプレックスであり、C4FM・DMR・レピータではない'}
# General confirmation checkboxes are deliberately kept empty here.  The
# 2026 official rule does not state several generic prohibitions that older
# PSLog data had inferred (repeater/cross-band/remote/self-spot etc.).  Such
# facts belong in read-only rule_view data when the official source supports
# them, not in submission-blocking confirmation flags.
e['required_flags']=[]
e['rule_view']={
 'participants':'日本国内の陸上で運用するアマチュア局およびSWL。',
 'power':'電話部門は20W以下（HF帯は10W以下）。QRP種目は5W以下。モリゾー＆キッコロ種目は20W以下（HF帯は10W以下）。',
 'movement':'コンテスト中の運用場所変更は禁止。ただし、コンテスト参加の目的で常置場所を離れ移動運用するシングルオペに限り、運用開始時のマルチプライヤー内での場所変更を認める。移動運用局は運用場所を市区町村名まで明記する。',
 'call_method':'電話：CQ AIコンテスト（またはCQ 愛コンテスト）\n電信：CQ AI TEST',
 'counterparts':'管外局同士の交信も有効な全国型コンテスト。',
 'frequency':'JARLコンテスト使用周波数帯、および1200MHz以上の各アマチュアバンド。1200MHz以上は総務省告示の「アマチュア業務に使用する電波の型式及び周波数の使用区別」による。',
 'restrictions':'D-STARの交信はDVモード（デジタル音声通信）かつシンプレックス。モリゾー＆キッコロ種目は2波以上の電波の同時発射を禁止。運用場所変更の条件は「移動運用」欄を参照。',
 'exchange':'RS(T) + 自局の運用場所を示す都府県支庁ナンバー。',
 'repeat':'同一バンドの同一局は、電信・電話（FM/SSB等）・電話（D-STAR）の各区分でそれぞれ1交信まで得点可。'
}
so=['全運用を一人で行い、第三者のマイクコントロール・交互運用等の補助を受けていない','移動SOの場所変更は開始時マルチ内の許可範囲のみであり、それ以外の場所変更をしていない']
mo=['第三者の補助を含む全運用者を申告し、途中で運用地を変更していない']
phone=['SSB','AM','FM','DV'];cats=[]
def add(code,name,bs,modes,op='SO',power=None):
 c=dict(id=code,name=name,bands=bs,modes=modes,max_power=power,min_bands=1,max_bands=len(bs),min_calls=1,operator=op,required_flags=deepcopy(so if op=='SO' else mo));cats.append(c);return c
for code,label,bs in [('CA','全帯',bands),('CHL','HF低',low),('CHH','HF高',high),('CHF','HF',hf),('CVU','50MHz以上',vu)]:add(code,'電信 SO '+label,bs,['CW'])
add('CMA','電信 MO 全帯',bands,['CW'],'MO')
for code,label,bs in [('XA','全帯',bands)]+[('X'+{'1.9':'19','3.5':'35'}.get(b,b),b+'MHz',[b]) for b in hf+['50','144','430']]+[('XG','1200MHz以上',ghz),('XHL','HF低',low),('XHH','HF高',high),('XHF','HF',hf),('XVU','50MHz以上',vu),('XQRP','QRP',bands),('XJ','ジュニア',bands)]:
 add(code,'電信電話 SO '+label,bs,['CW']+phone,power=5 if code=='XQRP' else None)
add('XMA','電信電話 MO 全帯',bands,['CW']+phone,'MO');add('XMJ','電信電話 MO ジュニア',bands,['CW']+phone,'MO')
for code,label,bs,op in [('PA','全帯',bands,'SO'),('PHL','HF低',low,'SO'),('PHH','HF高',high,'SO'),('PHF','HF',hf,'SO'),('PVU','50MHz以上',vu,'SO'),('PD','D-STAR',bands,'SO'),('PMA','全帯',bands,'MO'),('PMMK','モリゾー＆キッコロ',bands,'MO')]:
 c=add(code,'電話 '+op+' '+label,bs,['DV'] if code=='PD' else phone,op,20);c['power_by_band']={b:10 if b in hf else 20 for b in bs}
for c in cats:
 if c['id'] in ('XJ','XMJ','PMMK'):
  c['participation']=dict(max_age=20,min_percent=80,family_pair=c['id']=='PMMK')
  c['required_flags'].append('参加中の全交信を対象ログに含め、重複・無得点を含む担当交信数を実運用記録で確認した')
 if c['id']=='PMMK':
  c['fallback_category']='PMA';c['required_flags'].append('子と父母又は祖父母の2名で、子の局免許範囲内の運用とし、同時2波以上の発射をしていない')
assert len(cats)==33 and len({c['id'] for c in cats})==33
e['categories']=cats;e['band_modes']={b:['CW','SSB','AM','DV']+(['FM'] if b not in ['1.9','3.5','7','14','21'] else []) for b in bands}
e['submission']=dict(formats=['JARL R1.0'],zone='JST',contest='第21回愛・地球博記念コンテスト',required_fields=[],order='band_time',instructions='2026年規約・33種目。9/23 00:00～06:00休止。電話HF10W/VU20W、混合はCWだけでも可。DVはD-STARシンプレックスを確認。XJ/XMJ/PMMKは担当交信数を申告。PMMK不適合時のPMA変更は本人選択で再検査。JARL R1.0をバンド順で出力、専用Web受付又は郵送。締切2026-10-06。自動提出しません。')
apply_remaining_view(r)
(root/'config/rules/ai_chikyu_2026.txt').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('AI: 33 categories, 3 contact groups, 3 participation-count categories')
