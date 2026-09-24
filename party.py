"""Party exchanges and submission documents; never mutate canonical QSOs."""
import re,unicodedata,io,zipfile
from collections import Counter
from xml.sax.saxutils import escape
from datetime import date
from qsl_marks import TOKEN
from remarks_sections import primary
from activity_values import band_value,mode_group,norm
PARTIES={
 'nyp':('QSO パーティ NYP（JARL）','2026','202601020900','202601072100'),
 'hamtte_spring':('JARD HAMtte交信パーティー 春','2025','202505030000','202505182359'),
 'hamtte_summer':('JARD HAMtte交信パーティー 夏','2025','202508090000','202508242359'),
 'hamtte_winter':('JARD HAMtte交信パーティー 冬','2025','202501110000','202501262359'),
 'jag_warc':('JAG QSOパーティー（WARC band部門）','2026','202607110600','202607121759'),
 'welcome':('100周年/ニューカマー＆HAMtte ウェルカムQSOパーティ','2026','202609070900','202609142100')}
def cleaned(text,marker=''):
 text=unicodedata.normalize('NFKC',primary(text))
 if marker:text=re.sub(re.escape(unicodedata.normalize('NFKC',marker)),' ',text,flags=re.I)
 text=TOKEN.sub(' ',text)
 text=re.sub(r'(?<!\w)\d+(?:\.\d+)?\s*(?:MHz|GHz|kHz)(?!\w)|(?<![\w.])\d+\.\d+(?![\w.])',' ',text,flags=re.I)
 return text.strip(' \\')
def member(text):
 s=norm(primary(text));s=''.join(chr(ord(c)-96) if 'ァ'<=c<='ヶ' else c for c in s)
 return bool(re.search(r'(?<![A-Z])(?:HMT|HAMUTTE|HAMTTE)(?![A-Z])|はむっ?て',s))
def exchange(kind,text,rst='',marker=''):
 s=cleaned(text,marker)
 if kind=='nyp':return s
 if kind.startswith('hamtte') and member(s):return 'HMT'
 if kind=='jag_warc':return 'M' if re.search(r'(?<![A-Z])(?:\d{2,3})?M(?![A-Z])',norm(s)) else ''
 pattern=r'(?<![\w])(?:\d{2,3})?\d{2}(?:HN|HC|HW|N|C|W)(?!\w)' if kind=='welcome' else r'(?<![\w])\d{2,5}(?!\w)'
 found=[]
 for m in re.finditer(pattern,norm(s)):
  v=m.group()
  if kind=='welcome':v=re.search(r'\d{2}(?:HN|HC|HW|N|C|W)$',v).group()
  elif len(v)>2 and rst and v.startswith(rst):v=v[len(rst):]
  if v not in found:found.append(v)
 return found[0] if len(found)==1 else ''
def report(rst,ex):return (rst+' '+ex).strip()
def stats(kind,rows,own_exchange=''):
 # rows are explicitly selected working dictionaries; warnings never remove them.
 seen=set();members=set();notes=[]
 for r in rows:
  from contest_regional import base_call
  call=base_call(r['call'].upper());key=(r['date'],call) if kind.startswith('hamtte') else call
  if kind=='welcome':key=(r['date'],r['band'],call)
  seen.add(key)
  if r.get('member'):members.add(key)
  if not r['received'] and kind not in ('jag_warc',):notes.append(r['call']+'：受信交換内容を確認')
  if kind=='jag_warc' and band_value(r['band']) not in (10,18,24):notes.append(r['call']+'：WARC外のバンド')
  if kind.startswith('hamtte') and band_value(r['band']) not in ((3.5,7,21,50,144,430,1200,2400,5600) if r['date']>='2025-05-03' else (3.5,7,21,50,144,430,1200)):notes.append(r['call']+'：指定バンド外')
  if kind=='welcome':
   if band_value(r['band']) not in (3.5,7,21,28,50,144,430,1200):notes.append(r['call']+'：指定バンド外')
   if re.search(r'\d{2}W$',r.get('sent','')) and re.search(r'\d{2}W$',r['received']):notes.append(r['call']+'：W同士（賞の対象外）')
 return {'rows':len(rows),'units':len(seen),'members':len(members),'warnings':notes}
def jarl_text(kind,rows,info):
 if not rows:raise ValueError('提出対象を選択してください。')
 def clean(s):
  if any(c in str(s) for c in '<>\r\n\t'):raise ValueError('提出欄に改行・タブ・山括弧は使えません。')
  return str(s)
 def tag(k,v):return '<'+k+'>'+clean(v)+'</'+k+'>'
 version=info.get('version','R2.1')
 if version not in ('R1.0','R2.1'):raise ValueError('JARL形式を選択してください。')
 for k in ('own','name','address','signature'):
  if not info.get(k,'').strip():raise ValueError(k+'を入力してください。')
 if not info.get('oath'):raise ValueError('内容と宣誓を確認してください。')
 cat='30' if kind=='nyp' else info.get('category','')
 comments=info.get('comments','')
 if info.get('licensedate'):comments+=' 免許年月日：'+info['licensedate']
 if kind=='jag_warc':comments+=' 部門：'+info.get('categoryname','')+' '+info.get('sticker','ステッカー不要')
 title=info.get('title',PARTIES[kind][0]).replace('100周年/','')
 lines=['<SUMMARYSHEET VERSION='+version+'>',tag('CONTESTNAME',title),tag('CATEGORYCODE',cat)]
 if version=='R1.0':lines.append(tag('CATEGORYNAME',info.get('categoryname','')))
 for k,v in [('CALLSIGN',info['own']),('NAME',info['name']),('ADDRESS',info['address']),('EMAIL',info.get('email','')),('TEL',info.get('tel','')),('POWER',info.get('power','')),('OPPLACE',info.get('opplace','')),('COMMENTS',comments)]:lines.append(tag(k,v))
 if version=='R1.0':
  for b,n in Counter(r['band'] for r in rows).items():lines.append('<SCORE BAND='+clean(b)+'MHz>'+str(n)+',,</SCORE>')
  lines.append('<SCORE BAND=TOTAL>'+str(len(rows))+',,</SCORE>')
 lines += [tag('TOTALSCORE',''),tag('OATH','申請内容と交信記録が事実と相違ないことを誓います。'),tag('DATE',date.today().isoformat()),tag('SIGNATURE',info['signature']),'</SUMMARYSHEET>','<LOGSHEET TYPE="PSLog">','DATE(JST)\tTIME\tBAND\tMODE\tCALLSIGN\tSENT\tRCVD']
 for r in rows:lines.append('\t'.join(clean(v) for v in [r['date'],r['time'],r['band'],r['mode'],r['call'],report(r['rst_sent'],r['sent']),report(r['rst_received'],r['received'])]))
 return '\r\n'.join(lines+['</LOGSHEET>',''])
def xlsx_bytes(sheets):
 """Small portable OOXML writer for application-generated submission tables."""
 def col(n):
  s=''
  while n:n,a=divmod(n-1,26);s=chr(65+a)+s
  return s
 ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main';rels='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
 out=io.BytesIO()
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
  z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'+''.join('<Override PartName="/xl/worksheets/sheet%d.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'%i for i in range(1,len(sheets)+1))+'<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>')
  z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="'+rels+'/officeDocument" Target="xl/workbook.xml"/></Relationships>')
  z.writestr('xl/workbook.xml','<workbook xmlns="'+ns+'" xmlns:r="'+rels+'"><sheets>'+''.join('<sheet name="'+escape(name,{'"':'&quot;'})+'" sheetId="'+str(i)+'" r:id="rId'+str(i)+'"/>' for i,(name,_) in enumerate(sheets,1))+'</sheets></workbook>')
  z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+''.join('<Relationship Id="rId%d" Type="%s/worksheet" Target="worksheets/sheet%d.xml"/>'%(i,rels,i) for i in range(1,len(sheets)+1))+'<Relationship Id="styles" Type="'+rels+'/styles" Target="styles.xml"/></Relationships>')
  z.writestr('xl/styles.xml','<styleSheet xmlns="'+ns+'"><fonts count="1"><font><sz val="11"/><name val="Yu Gothic"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')
  for i,(sheet_name,rows) in enumerate(sheets,1):
   body=''
   for rn,row in enumerate(rows,1):
    body+='<row r="%d" ht="%d" customHeight="1">'%(rn,22 if sheet_name=='サマリー' else 32)
    for cn,v in enumerate(row,1):
     body+='<c r="'+col(cn)+str(rn)+'" t="inlineStr"><is><t xml:space="preserve">'+escape(str(v))+'</t></is></c>'
    body+='</row>'
   z.writestr('xl/worksheets/sheet%d.xml'%i,'<worksheet xmlns="'+ns+'"><sheetPr><pageSetUpPr fitToPage="1"/></sheetPr><sheetViews><sheetView workbookViewId="0"/></sheetViews><cols>'+('<col min="1" max="1" width="36" customWidth="1"/><col min="2" max="2" width="90" customWidth="1"/>' if sheet_name=='サマリー' else '<col min="1" max="10" width="20" customWidth="1"/>')+'</cols><sheetData>'+body+'</sheetData><pageMargins left="0.3" right="0.3" top="0.4" bottom="0.4" header="0.2" footer="0.2"/><pageSetup paperSize="9" orientation="landscape" fitToWidth="1" fitToHeight="'+('1' if sheet_name=='サマリー' else '0')+'"/></worksheet>')
 return out.getvalue()
def hamtte_sheets(rows,info):
 summary=[['JARD HAMtte交信パーティー サマリー'],['大会名',info['title']],['参加部門','パーティー部門']]+[[label,info.get(k,'')] for k,label in [('own','コールサイン'),('category','会員／一般・会員番号'),('name','氏名'),('address','住所'),('email','メール'),('tel','電話'),('opplace','運用地'),('power','最大電力'),('comments','意見'),('signature','署名')]]
 summary += [['バンド','交信行数']]+[[b,n] for b,n in Counter(r['band'] for r in rows).items()]+[['合計',len(rows)],['日別同一局1回の参考局数',stats('hamtte',rows)['units']],['宣誓','上記内容と交信記録が事実と相違ないことを誓います。'],['年月日',date.today().isoformat()]]
 log=[['日時 JST','時刻','MHz','Mode','Callsign','送信','受信','HAMtteメンバー']]+[[r['date'],r['time'],r['band'],r['mode'],r['call'],report(r['rst_sent'],r['sent']),report(r['rst_received'],r['received']),'✓' if r['member'] else ''] for r in rows]
 return [('サマリー',summary),('ログ',log)]
