from pathlib import Path
import json,hashlib,zipfile
p=Path(__file__).resolve().parents[1]
deadlines={'cq-ww-cw':'2026年12月1日23:59 UTC（終了後48時間以内）','cq-ww-ssb':'2026年10月27日23:59 UTC（終了後48時間以内）','kcwa_cw':'2026年12月31日（当日送信・消印有効）','all_ja0_160m':'2026年12月31日（紙は消印有効）'}
f=p/'devtools/contest_rule_view_verified_remaining71.json';items=json.loads(f.read_text(encoding='utf-8-sig'))
for ident,deadline in deadlines.items():
 f2=p/f'config/rules/{ident}_2026.txt';r=json.loads(f2.read_text(encoding='utf-8-sig'));r['event']['rule_view']['submission_deadline']=deadline;f2.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
 source='cqww_rules_2026.html' if ident.startswith('cq-ww') else 'kcwa_2026.html' if ident=='kcwa_cw' else 'all_ja0_18_2026.html'
 items[ident].update(year=2026,source_file=source,source_url=r['url'],source_checked='2026-10-20',rule_view=r['event']['rule_view'])
items['tokyo_cw'].update(source_url='https://jarltokyo.com/_media/contest/contest_rules_cw_ver20261003.pdf',source_checked='2026-10-20')
f.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
for f in (p/'config/templates/cabrillo').glob('cq-ww-*_2026.txt'):
 d=json.loads(f.read_text(encoding='utf-8-sig'));d['id']=d['id'].replace('2025','2026');d['name']=d['name'].replace('2025','2026');d['year']=2026;f.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
for f in [p/'config/rules/TARGETS_73.json',p/'config/rules/ADDITIONAL_RESEARCH.json']:
 data=json.loads(f.read_text(encoding='utf-8-sig'))
 for row in data['contests']:
  ident=row['id']
  if ident in deadlines or ident=='tokyo_cw':
   r=json.loads((p/f'config/rules/{ident}_2026.txt').read_text(encoding='utf-8-sig'));row.update(year=2026,rule_file=f'{ident}_2026.txt',rules_url=r['url'],status='2026年公式規約反映・1.19自動試験済み（Windows実機未検証）',implementation_note='docs/contest-research/PSLOG119_RULE_CHANGES.md')
 f.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
for name in ('test_contest_rule_view_audit_87.py','test_contest_rule_view_verified_15.py'):
 f=p/name;s=f.read_text(encoding='utf-8-sig').replace('len(paths), 87','len(paths), 91').replace('len(paths),87','len(paths),91').replace('for rule in rules),86','for rule in rules),90');f.write_text(s, encoding='utf-8')
f=p/'test_contest_rule_view_remaining71.py';s=f.read_text(encoding='utf-8-sig').replace("self.rules['kcwa_cw']['year'],2025","self.rules['kcwa_cw']['year'],2026");f.write_text(s, encoding='utf-8')
# Refresh payload digests after presentation deadline additions.
for f in (p/'distribution/rules').glob('*.zip'):
 with zipfile.ZipFile(f) as z:data={n:z.read(n) for n in z.namelist()}
 m=json.loads(data['manifest.json']);changed=False
 for entry in m['rules']:
  if entry['year']==2026 and entry['id'] in deadlines:
   raw=(p/'config'/entry['file']).read_bytes()
   if raw!=data[entry['file']]:data[entry['file']]=raw;entry['sha256']=hashlib.sha256(raw).hexdigest();changed=True
 if changed:
  data['manifest.json']=json.dumps(m,ensure_ascii=False,indent=2).encode()
  with zipfile.ZipFile(f,'w',zipfile.ZIP_DEFLATED) as z:
   for name,raw in data.items():z.writestr(name,raw)
