"""JARL 100th-anniversary and Japan/World 10,000-station award helpers."""
from collections import Counter,defaultdict
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape
import io,re,unicodedata,zipfile

from activity_values import norm
from contest_regional import base_call
from input_normalization import jccjcg_parts
from remarks_sections import primary

ANNIVERSARY={
 '100周年 J賞':('prefix',10),'100周年 A賞':('cityward',10),'100周年 R賞':('gun',10),
 '100周年 L賞':('pref',10),'100周年 100賞':('callband',100),'100周年 1000賞':('callband',1000),
 '100周年 10000賞':('call',10000),'100周年 100 AJD・銅賞':('ajd_bronze',10),
 '100周年 100 AJD・銀賞':('ajd_silver',10),'100周年 100 AJD・金賞':('ajd_gold',100),
 '100周年 100 WAJA・銅賞':('waja_bronze',47),'100周年 100 WAJA・銀賞':('waja_silver',94),
 '100周年 100 WAJA・金賞':('waja_gold',94),'100周年 イベント局賞':('event',1),
}
JAPAN_LEVELS={f'全日本 {n:,}局賞'.replace(',',''):n for n in (2500,5000,7500,10000)}
WORLD_LEVELS={f'全世界 {n:,}局賞'.replace(',',''):n for n in (2500,5000,7500,10000)}
SPECIAL_AWARDS=tuple(ANNIVERSARY)+tuple(JAPAN_LEVELS)+tuple(WORLD_LEVELS)
WORLD_REQUIREMENTS={2500:(100,40,7),5000:(130,50,7),7500:(160,60,7),10000:(200,70,7)}
PREF_AREA={'01':'8','02':'7','03':'7','04':'7','05':'7','06':'7','07':'7','08':'0','09':'0','10':'1','11':'1','12':'1','13':'1','14':'1','15':'1','16':'1','17':'1','18':'2','19':'2','20':'2','21':'2','22':'3','23':'3','24':'3','25':'3','26':'3','27':'3','28':'9','29':'9','30':'9','31':'4','32':'4','33':'4','34':'4','35':'4','36':'5','37':'5','38':'5','39':'5','40':'6','41':'6','42':'6','43':'6','44':'6','45':'6','46':'6','47':'6'}
CONTINENTS=('AF','AN','AS','EU','NA','OC','SA')

def is_anniversary(award):return award in ANNIVERSARY
def is_japan(award):return award in JAPAN_LEVELS
def is_world(award):return award in WORLD_LEVELS
def is_ten_thousand(award):return is_japan(award) or is_world(award)
def target(award):return ANNIVERSARY.get(award,('',0))[1] or JAPAN_LEVELS.get(award) or WORLD_LEVELS.get(award) or 0

def _region(q):
 typ,raw_code=jccjcg_parts(q.code);m=re.match(r'^(\d{4,6})',raw_code or '')
 return (typ,m.group(1)) if typ and m else ('','')

def _prefix(call):
 call=base_call(call)
 m=re.match(r'^((?:[A-Z]+\d|\d[A-Z]+\d))',call)
 return m[1] if m else ''

def _portable_area(call,pref=''):
 m=re.search(r'/([0-9])$',norm(call))
 return m[1] if m else PREF_AREA.get(pref,'')

def _anniv_type(remarks):
 text=norm(primary(remarks))
 kind='公募局' if re.search(r'100TH[. _-]?(?:PUBLIC|P)(?![A-Z])',text) else 'イベント局' if re.search(r'100TH[. _-]?(?:EVENT|E)(?![A-Z])',text) else ''
 extra=re.search(r'100TH[. _-]?EXTRA\s*[=:]\s*([^\s,;]+)',text)
 return kind,(extra[1] if extra else '')

def anniversary_candidate(award,q):
 rule,_=ANNIVERSARY[award];typ,code=_region(q);pref=code[:2] if code else ''
 call=base_call(q.call);band=norm(q.band);mode=norm(q.mode);kind,extra=_anniv_type(q.remarks)
 notes=[];unit='';anniv_required=rule.startswith(('ajd_','waja_')) or rule=='event'
 if rule=='prefix':unit=_prefix(q.call)
 elif rule=='cityward' and typ=='JCC' and len(code) in (4,6):unit=code
 elif rule=='gun' and typ=='JCG' and len(code)==5:unit=code
 elif rule=='pref' and pref:unit=pref
 elif rule=='callband':unit=call+'@'+band
 elif rule=='call':unit=call
 elif rule=='ajd_bronze' and kind:unit=_prefix(q.call)
 elif rule=='ajd_silver' and kind=='公募局':unit=_portable_area(q.call,pref)
 elif rule=='ajd_gold' and kind=='公募局':unit='@'.join((_portable_area(q.call,pref),band,mode))
 elif rule=='waja_bronze' and kind=='公募局' and pref:unit=pref
 elif rule in ('waja_silver','waja_gold') and kind=='公募局' and (pref or extra):unit='@'.join((extra or pref,band,mode))
 elif rule=='event' and kind=='イベント局':unit=call
 if anniv_required and not kind:notes.append('記念運用局はRMKSへ100TH.PUBLICまたは100TH.EVENTを記入して確認')
 if rule=='waja_gold' and kind=='公募局' and not extra:notes.append('別に定める局はRMKSへ100TH.EXTRA=名称を記入')
 if rule in ('cityward','gun','pref') and not code:notes.append('JCC/JCG番号を確認')
 return {'unit':unit,'station_key':call,'anniv_type':kind,'extra_region':extra,'pref':pref,'area':_portable_area(q.call,pref),'notes':' / '.join(notes)}

def _invalid_link(q):
 text=norm(primary(q.remarks)+' '+q.mode)
 if q.call.upper().endswith(('/MM','/AM')):return '海上・航空移動局は対象外'
 if re.search(r'\b(?:SAT(?:ELLITE)?|REPEATER|RPT|CROSS[ -]?BAND)\b',text):return '中継局・衛星・クロスバンドの可能性を確認'
 return ''

def _japan_group(q,country):
 text=norm(q.his_qth+' '+primary(q.remarks)+' '+q.call)
 if q.call.upper()=='8J1RL' or 'SYOWA' in text or 'SHOWA' in text:return '南極'
 if 'MINAMITORISHIMA' in text or 'MARCUS' in text:return '南鳥島'
 if q.call.upper().startswith('JD1') or '/JD1' in q.call.upper():return '小笠原' if 'OGASAWARA' in text or 'CHICHIJIMA' in text or 'HAHAJIMA' in text else ''
 return '日本本土' if country and country.get('country')=='Japan' else ''

def ten_thousand_candidate(award,q,countries):
 call=base_call(q.call);typ,code=_region(q);pref=code[:2] if code else '';country=countries.lookup(q.call)
 notes=[];invalid=_invalid_link(q)
 if invalid:notes.append(invalid)
 if q.my_qth and 'JAPAN' not in norm(q.my_qth):notes.append('自局の交信地点が日本国内陸上か確認')
 if is_japan(award):
  domestic=bool(country and country.get('country')=='Japan') or q.call.upper().startswith(('JA','JE','JF','JG','JH','JI','JJ','JK','JL','JM','JN','JO','JP','JQ','JR','JS','7J','7K','7L','7M','7N','8J','8N'))
  if not domestic:notes.append('日本のアマチュア局ではありません')
  if not pref:notes.append('47都道府県セットにはJCC/JCG番号が必要')
  return {'unit':call if domestic and not invalid else '','station_key':call,'licensee':'','pref':pref,'area':_portable_area(q.call,pref),'country':'Japan' if domestic else (country or {}).get('country',''),'entity':'JA','itu':(country or {}).get('itu',''),'continent':'AS','japan_group':'日本本土' if domestic else '','eligible':domestic and not invalid,'notes':' / '.join(notes)}
 if not country:
  notes.append('CTYでエンティティー・ITUゾーンを判定できません')
 group=_japan_group(q,country);entity=(country or {}).get('entity_prefix','');itu=(country or {}).get('itu','');continent=(country or {}).get('continent','')
 if group=='小笠原':entity='JD1-OGASAWARA';itu=45;continent='AS'
 elif group=='南鳥島':entity='JD1-MINAMITORISHIMA';itu=45;continent='OC'
 elif group=='南極':continent='AN';itu=67
 if entity:notes.append('現行CTY候補：QSLの運用地・エンティティー・ITUゾーンを確認')
 eligible=bool(country or group) and not invalid
 return {'unit':call if eligible else '','station_key':call,'licensee':'','pref':pref,'area':_portable_area(q.call,pref),'country':(country or {}).get('country','Japan' if group else ''),'entity':entity,'itu':str(itu) if itu!='' else '','continent':continent,'japan_group':group,'eligible':eligible,'notes':' / '.join(notes)}

def special_candidate(award,q,countries=None):
 return anniversary_candidate(award,q) if is_anniversary(award) else ten_thousand_candidate(award,q,countries)

def _unique_indices(rows,key='unit'):
 seen=set();out=[]
 for i,r in enumerate(rows):
  value=r.get(key,'')
  if value and value not in seen:seen.add(value);out.append(i)
 return out

def _station_id(record):
 call=base_call(record.get('call',''));licensee=str(record.get('licensee','')).strip()
 return call+('#'+licensee if licensee else '')

def _pref_sets(rows,maxsets):
 used=set();assign={};setno=0
 by_band=defaultdict(lambda:defaultdict(list))
 for i,r in enumerate(rows):
  if r.get('pref') in PREF_AREA:by_band[norm(r.get('band',''))][r['pref']].append(i)
 bands=sorted(by_band,key=lambda b:(sum(bool(by_band[b][p]) for p in PREF_AREA),b),reverse=True)
 for band in bands:
  for _ in range(4):
   chosen=[]
   for pref in sorted(PREF_AREA):
    pick=next((i for i in by_band[band][pref] if _station_id(rows[i]) not in used),None)
    if pick is None:chosen=[];break
    chosen.append(pick)
   if not chosen:break
   setno+=1
   for i in chosen:used.add(_station_id(rows[i]));assign[i]=setno
   if setno>=maxsets:return assign
 return assign

def selection_indices(award,rows):
 if is_anniversary(award):return _unique_indices(rows)
 limit=target(award);chosen=[];seen=set();jgroups=set()
 assignments=_pref_sets(rows,{2500:3,5000:6,7500:9,10000:12}.get(limit,0)) if is_japan(award) else {}
 for i in assignments:
  call=_station_id(rows[i])
  if call not in seen:chosen.append(i);seen.add(call);rows[i]['set_no']=assignments[i]
 for i,r in enumerate(rows):
  call=_station_id(r)
  if not r.get('unit') or call in seen:continue
  if is_world(award) and r.get('japan_group'):
   if r['japan_group'] in jgroups:continue
   jgroups.add(r['japan_group'])
  chosen.append(i);seen.add(call)
  if len(chosen)>=limit:break
 return chosen

def metrics(award,records):
 indices=selection_indices(award,[dict(r) for r in records]);rows=[records[i] for i in indices];n=len(rows);goal=target(award)
 result={'selected':n,'target':goal,'complete':n>=goal,'warnings':[]}
 if is_anniversary(award):
  rule,_=ANNIVERSARY[award]
  if rule=='ajd_silver':result['complete']=set(r.get('area') for r in rows)==set('0123456789')
  elif rule=='ajd_gold':result['complete']=all(sum(1 for r in rows if r.get('area')==a)>=10 for a in '0123456789')
  elif rule=='waja_bronze':result['complete']=set(r.get('pref') for r in rows)>=set(PREF_AREA)
  elif rule in ('waja_silver','waja_gold'):result['complete']=all(sum(1 for r in rows if r.get('pref')==p)>=2 for p in PREF_AREA)
  if rule=='waja_gold':result['warnings'].append('別に定める100周年記念運用局の全対象は公式発表と照合してください。')
 elif is_japan(award):
  required={2500:3,5000:6,7500:9,10000:12}[goal];assign=_pref_sets(rows,required);sets=len(set(assign.values()));areas=Counter(r.get('area') for r in rows)
  result.update(pref_sets=sets,required_sets=required,areas=areas)
  result['complete']=n>=goal and sets>=required
  if goal==10000:
   bad=[a for a in '0123456789' if not 500<=areas[a]<=1500]
   if bad:result['complete']=False;result['warnings'].append('10,000局賞のエリア比率5～15%を満たさないエリア：'+','.join(bad))
 elif is_world(award):
  entities=len({r.get('entity') for r in rows if r.get('entity')});itus=len({str(r.get('itu')) for r in rows if r.get('itu')});continents=len({r.get('continent') for r in rows if r.get('continent') in CONTINENTS});req=WORLD_REQUIREMENTS[goal]
  result.update(entities=entities,itus=itus,continents=continents,requirements=req)
  result['complete']=n>=goal and entities>=req[0] and itus>=req[1] and continents>=req[2]
 return result

def _col(n):
 s=''
 while n:n,r=divmod(n-1,26);s=chr(65+r)+s
 return s

def _cell(ref,value,style=0):
 if isinstance(value,(int,float)):return f'<c r="{ref}" s="{style}" t="n"><v>{value}</v></c>'
 if style==0 and re.fullmatch(r'0\d+',str(value)):style=3
 return f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{escape(str(value))}</t></is></c>'

def _sheet(rows,widths=None,footer='',landscape=True):
 body=[]
 for rn,row in enumerate(rows,1):
  style=1 if rn==1 else 2 if rn in (2,4) and len(rows)<30 else 0
  body.append(f'<row r="{rn}">'+''.join(_cell(_col(c)+str(rn),v,style) for c,v in enumerate(row,1))+'</row>')
 cols=''.join(f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>' for i,w in enumerate(widths or [14]*max((len(r) for r in rows),default=1),1))
 last=_col(max((len(r) for r in rows),default=1));headerfooter=f'<headerFooter><oddFooter>&amp;L{escape(footer)}&amp;RPage &amp;P / &amp;N</oddFooter></headerFooter>' if footer else ''
 return '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols>'+cols+'</cols><sheetData>'+''.join(body)+'</sheetData><autoFilter ref="A1:'+last+str(max(1,len(rows)))+'"/><pageMargins left="0.25" right="0.25" top="0.4" bottom="0.4" header="0.2" footer="0.35"/><pageSetup paperSize="9" orientation="'+('landscape' if landscape else 'portrait')+'" fitToWidth="1" fitToHeight="0"/>'+headerfooter+'</worksheet>'

def _package(sheets):
 out=io.BytesIO();styles='''<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="10"/><name val="Arial"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="10"/><name val="Arial"/></font></fonts><fills count="4"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF1F4E78"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFD9EAF7"/></patternFill></fill></fills><borders count="2"><border/><border><left style="thin"><color rgb="FFD9D9D9"/></left><right style="thin"><color rgb="FFD9D9D9"/></right><top style="thin"><color rgb="FFD9D9D9"/></top><bottom style="thin"><color rgb="FFD9D9D9"/></bottom></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="4"><xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyAlignment="1"><alignment vertical="center"/></xf><xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf><xf numFmtId="0" fontId="0" fillId="3" borderId="1" xfId="0" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf><xf numFmtId="49" fontId="0" fillId="0" borderId="1" xfId="0" applyAlignment="1"><alignment vertical="center"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>'''
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  overrides=''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1,len(sheets)+1))
  z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'+overrides+'</Types>')
  z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
  sheetdefs=''.join(f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>' for i,(name,_,_) in enumerate(sheets,1));z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'+sheetdefs+'</sheets><calcPr fullCalcOnLoad="1"/></workbook>')
  rels=''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1,len(sheets)+1));z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+rels+'<Relationship Id="styles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
  z.writestr('xl/styles.xml',styles)
  for i,(_,rows,options) in enumerate(sheets,1):z.writestr(f'xl/worksheets/sheet{i}.xml',_sheet(rows,**options))
 return out.getvalue()

def _info_rows(award,info,m):
 return [['項目','内容'],['アワード',award],['申請コールサイン',info.get('own','')],['氏名',info.get('name','')],['作成日',date.today().isoformat()],['選択局数',m['selected']],['必要局数・ポイント',m['target']],['判定','条件充足候補' if m['complete'] else '未達または要確認'],['申請者署名',info.get('signature','')],['審査者1',info.get('reviewer1','')],['審査者1署名',''],['審査者2',info.get('reviewer2','')],['審査者2署名',''],['確認事項',' / '.join(m.get('warnings',[]))]]

def _list_rows(records,world=False,ten=False):
 header=['No.','印','Callsign','Date','Time','Band','Mode','JCC/JCG','QTH','計数単位']
 if ten:header.insert(3,'同一コール識別')
 if world:header+=['Entity','ITU','大陸','日本区分','確認事項']
 rows=[header]
 for i,r in enumerate(records,1):
  mark=('○' if r.get('entity_pick') else '')+('△' if r.get('itu_pick') else '')+('□' if r.get('continent_pick') else '')
  row=[i,mark,r.get('call',''),r.get('date',''),r.get('time',''),r.get('band',''),r.get('mode',''),r.get('code',''),r.get('qth',''),r.get('unit','')]
  if ten:row.insert(3,r.get('licensee',''))
  if world:row += [r.get('entity',''),r.get('itu',''),r.get('continent',''),r.get('japan_group',''),r.get('notes','')]
  rows.append(row)
 return rows

def workbook_bytes(award,records,info=None):
 info=info or {};indices=selection_indices(award,[dict(r) for r in records]);records=[dict(records[i]) for i in indices];m=metrics(award,records)
 footer='申請者所持証明署名：________________　審査者署名：________________'
 sheets=[]
 if is_anniversary(award):
  sheets=[('申請書',_info_rows(award,info,m),{'widths':[24,90],'footer':''}),('交信局リスト',_list_rows(records),{'widths':[8,6,16,13,9,11,11,14,28,24],'footer':'申請者確認：________________'})]
 elif is_japan(award):
  sets=_pref_sets(records,{2500:3,5000:6,7500:9,10000:12}[target(award)])
  for i,s in sets.items():records[i]['set_no']=s
  m=metrics(award,records);areas=Counter(r.get('area') for r in records)
  summary=_info_rows(award,info,m)+[['47都道府県セット',f'{len(set(sets.values()))} / {m["required_sets"]}'],['10,000局エリア比率','5～15%（500～1,500局）' if target(award)==10000 else '規約上の比率指定なし']]
  prefrows=[['Set','Band','都道府県番号','Callsign','Date','JCC/JCG']]+[[s,records[i].get('band',''),records[i].get('pref',''),records[i].get('call',''),records[i].get('date',''),records[i].get('code','')] for i,s in sorted(sets.items(),key=lambda x:(x[1],records[x[0]].get('pref','')))]
  arearows=[['コールエリア','局数','比率','10,000局条件']]+[[a,areas[a],f'{areas[a]/len(records):.1%}' if records else '0.0%',('OK' if 500<=areas[a]<=1500 else '要確認') if target(award)==10000 else '対象外'] for a in '0123456789']
  sheets=[('申請概要',summary,{'widths':[28,88],'footer':''}),('47都道府県',prefrows,{'widths':[8,12,14,18,13,16],'footer':footer}),('交信局リスト',_list_rows(records,ten=True),{'widths':[8,6,16,18,13,9,11,11,14,28,24],'footer':footer}),('エリア別累計',arearows,{'widths':[14,12,14,22],'footer':footer})]
 else:
  entitypick={};itupick={};contpick={}
  for i,r in enumerate(records):
   if r.get('entity') and r['entity'] not in entitypick:entitypick[r['entity']]=i;r['entity_pick']=True
   if r.get('itu') and str(r['itu']) not in itupick:itupick[str(r['itu'])]=i;r['itu_pick']=True
   if r.get('continent') in CONTINENTS and r['continent'] not in contpick:contpick[r['continent']]=i;r['continent_pick']=True
  m=metrics(award,records);req=m['requirements'];summary=_info_rows(award,info,m)+[['ARRLエンティティー',f'達成 {m["entities"]} / 必要 {req[0]}'],['ITUゾーン',f'達成 {m["itus"]} / 必要 {req[1]}'],['六大州＋南極',f'達成 {m["continents"]} / 必要 {req[2]}']]
  reps=lambda field,picks:[[field,'Callsign','Date','Country']]+[[key,records[i].get('call',''),records[i].get('date',''),records[i].get('country','')] for key,i in sorted(picks.items(),key=lambda x:str(x[0]))]
  sheets=[('申請概要',summary,{'widths':[28,88],'footer':''}),('交信局リスト',_list_rows(records,True,True),{'widths':[8,6,16,18,13,9,11,11,14,24,18,16,8,9,12,36],'footer':footer}),('ARRLエンティティ',reps('Entity',entitypick),{'widths':[20,18,13,28],'footer':footer}),('ITUゾーン',reps('ITU',itupick),{'widths':[12,18,13,28],'footer':footer}),('六大州・南極',reps('大陸',contpick),{'widths':[12,18,13,28],'footer':footer})]
 return _package(sheets)
