"""AJA candidate rules, legacy workbook import, and corrected OOXML output."""
from collections import Counter
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape
import io,json,re,zipfile

from activity_filters import band_value,norm
from contest_regional import base_call
from input_normalization import jccjcg_parts
from remarks_sections import primary

BANDS=(
 ('0.135','135kHz'),('0.475','475kHz'),('1.9','1.9MHz'),('3.5','3.5MHz'),
 ('7','7MHz'),('10','10MHz'),('14','14MHz'),('18','18MHz'),('21','21MHz'),
 ('24','24MHz'),('28','28MHz'),('50','50MHz'),('144','144MHz'),('430','430MHz'),
 ('1200','1200MHz'),('2400','2400MHz'),('5600','5600MHz'),('10000','10GHz'),
 ('24000','24GHz'),('47000','47GHz'),('77000','77GHz'),('135000','135GHz'),
 ('248000','248GHz'),('SAT','Satellite'))
BAND_LABEL=dict(BANDS)
LEGACY_BANDS=('1.9','3.5','7','10','14','18','21','24','28','50','144','430','1200','2400','5600','10000','24000','47000','77000','SAT')
DESIGNATED={
 '0101':'1972-04-01','0601':'1989-04-01','0801':'2007-04-01','1001':'1947-05-03',
 '1101':'1956-09-01','1103':'1972-04-01','1110':'2010-04-01','1201':'1992-04-01',
 '1344':'2003-04-01','1801':'2005-04-01','1802':'2007-04-01','2001':'1956-09-01',
 '2201':'1956-09-01','2501':'1956-09-01','2502':'2006-04-01','2701':'1956-09-01',
 '3101':'2009-04-01','3501':'1980-04-01','4001':'1972-04-01','4021':'1963-04-01',
 '4301':'2012-04-01'}

def load_master(root):
 path=Path(root)/'config/db/aja_locations.json'
 if not path.exists():
  import sys
  path=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'config/db/aja_locations.json'
 data=json.loads(path.read_text('utf-8'))
 if data.get('schema')!=1 or not isinstance(data.get('rows'),list):raise ValueError('AJA地域一覧を読めません。')
 return data

def canonical_band(band,remarks='',mode=''):
 text=norm(primary(remarks)+' '+mode)
 if re.search(r'(?<![A-Z0-9])(?:SAT(?:ELLITE)?|FO[- ]?\d+|JAS[- ]?\d+)(?![A-Z0-9])',text):return 'SAT'
 value=band_value(band)
 if value is None:return ''
 if value in (3.8,3.5):return '3.5'
 for key,_ in BANDS:
  if key!='SAT' and abs(value-float(key))<max(1e-9,float(key)*1e-9):return key
 if value in (10100,10400):return '10000'
 return ''

def region_kind(code,date):
 """Return current AJA count type, or blank when date/code combination is impossible."""
 if len(code)==5:return 'gun',''
 if len(code)==4:
  start=DESIGNATED.get(code)
  if start and date and date>=start:return '',f'{code}は{start}以後、市ではなく区を指定してください'
  return 'city',''
 if len(code)==6:
  parent=code[:4]
  if parent=='1001':return ('city' if date and date>='2010-04-01' else 'ward'),('交信日未入力：東京23区の市・区扱いを確認' if not date else '')
  start=DESIGNATED.get(parent)
  if start and date and date<start:return '',f'{parent}の区は{start}以後の交信が対象です'
  return 'ward',('交信日未入力：政令指定都市化の前後を確認' if not date else '')
 return '','市郡区番号を確認'

def candidate(q):
 typ,raw_code=jccjcg_parts(q.code);m=re.match(r'^(\d{4,6})',raw_code or '')
 if not typ or not m:return {'unit':'','region':'','region_type':'','aja_band':'','station_key':'','notes':'JCC/JCG番号を確認'}
 code=m.group(1);band=canonical_band(q.band,q.remarks,q.mode);kind,note=region_kind(code,q.date)
 if typ=='JCG' and len(code)!=5:kind='';note='JCG番号を確認'
 if typ=='JCC' and len(code)==5:kind='';note='JCC番号を確認'
 if not band:note=(note+' / ' if note else '')+'AJAのバンドを確認'
 unit=code+'@'+band if kind and band else ''
 return {'unit':unit,'region':code,'region_type':kind,'aja_band':band,'station_key':base_call(q.call)+'@'+band if band else '','notes':note}

def distinct(records):
 units=set();stations=set();out=[];warnings=[]
 for record in records:
  unit=record.get('unit','');station=record.get('station_key') or base_call(record.get('call',''))+'@'+record.get('aja_band',record.get('band',''))
  if not unit or unit in units:
   if unit:warnings.append(unit+'：地域×バンドが重複')
   continue
  if station in stations:
   warnings.append(record.get('call','')+'：同一コール・同一バンドが重複')
   continue
  units.add(unit);stations.add(station);out.append(record)
 return out,warnings

def stats(records):
 rows,warnings=distinct(records);bands={r.get('aja_band') or r['unit'].rsplit('@',1)[-1] for r in rows}
 kinds=Counter(r.get('region_type') or region_kind(r['unit'].split('@')[0],r.get('date',''))[0] for r in rows)
 return {'points':len(rows),'bands':len(bands),'cities':kinds['city'],'guns':kinds['gun'],'wards':kinds['ward'],'warnings':warnings}

def _cell(ref,value='',style=0,formula=''):
 if formula:return f'<c r="{ref}" s="{style}"><f>{escape(formula)}</f><v>{escape(str(value))}</v></c>'
 if isinstance(value,(int,float)):return f'<c r="{ref}" s="{style}" t="n"><v>{value}</v></c>'
 return f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{escape(str(value))}</t></is></c>'

def _col(number):
 value=''
 while number:number,rem=divmod(number-1,26);value=chr(65+rem)+value
 return value

def _sheet_xml(master,records):
 by_unit={r['unit']:r for r in records};body=[];merges=[];maxcol=4+len(BANDS)*2
 headers=['','都道府県','市郡区名','番号']
 body.append('<row r="1" ht="28" customHeight="1">'+''.join(_cell(_col(i+1)+'1',v,1) for i,v in enumerate(headers)))
 for index,(key,label) in enumerate(BANDS):
  col=5+index*2;a=_col(col);b=_col(col+1);body.append(_cell(a+'1',label,1));body.append(_cell(b+'1','',1));merges.append(f'{a}1:{b}1')
 body.append('</row>')
 body.append('<row r="2" ht="24" customHeight="1">'+''.join(_cell(_col(i)+'2',v,2) for i,v in enumerate(['','','','',]+sum((['Mode','Callsign'] for _ in BANDS),[]),1))+'</row>')
 body.append('<row r="3" ht="24" customHeight="1">'+''.join(_cell(_col(i)+'3',v,2) for i,v in enumerate(['','','','',]+sum((['QSL','Date'] for _ in BANDS),[]),1))+'</row>')
 rows=list(master['rows']);known={r['code'] for r in rows}
 for r in records:
  code=r['unit'].split('@')[0]
  if code not in known:rows.append({'code':code,'name':r.get('qth','') or '追加地域','prefecture':'','kind':r.get('region_type','')});known.add(code)
 for n,location in enumerate(rows):
  row=4+n*2;ward=location['kind']=='ward';style=4 if ward else 3
  values=['',location.get('prefecture',''),location.get('name',''),location['code']]
  top=[_cell(_col(i+1)+str(row),v,style) for i,v in enumerate(values)]
  bottom=[_cell(_col(i+1)+str(row+1),'',style) for i in range(4)]
  for index,(band,_) in enumerate(BANDS):
   rec=by_unit.get(location['code']+'@'+band);col=5+index*2
   top.extend([_cell(_col(col)+str(row),rec.get('mode','') if rec else '',5),_cell(_col(col+1)+str(row),rec.get('call','') if rec else '',5)])
   bottom.extend([_cell(_col(col)+str(row+1),'✓' if rec else '',6),_cell(_col(col+1)+str(row+1),rec.get('date','') if rec else '',6)])
  body.append(f'<row r="{row}" ht="21" customHeight="1">'+''.join(top)+'</row>')
  body.append(f'<row r="{row+1}" ht="18" customHeight="1">'+''.join(bottom)+'</row>')
 widths='<cols><col min="1" max="1" width="2" customWidth="1"/><col min="2" max="2" width="14" customWidth="1"/><col min="3" max="3" width="25" customWidth="1"/><col min="4" max="4" width="10" customWidth="1"/><col min="5" max="%d" width="13" customWidth="1"/></cols>'%maxcol
 return '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews><sheetView workbookViewId="0"><pane xSplit="4" ySplit="3" topLeftCell="E4" activePane="bottomRight" state="frozen"/></sheetView></sheetViews>'+widths+'<sheetData>'+''.join(body)+'</sheetData><mergeCells count="%d">%s</mergeCells><pageMargins left="0.2" right="0.2" top="0.3" bottom="0.3" header="0.1" footer="0.1"/><pageSetup paperSize="8" orientation="landscape" fitToWidth="1" fitToHeight="0"/></worksheet>'%(len(merges),''.join('<mergeCell ref="'+m+'"/>' for m in merges))

def _totals_xml(records,info):
 counts=Counter((r.get('region_type') or region_kind(r['unit'].split('@')[0],r.get('date',''))[0],r.get('aja_band') or r['unit'].rsplit('@',1)[-1]) for r in records)
 rows=[];last=2+len(BANDS);totalcol=_col(last)
 rows.append('<row r="1" ht="30" customHeight="1">'+_cell('A1','AJA QSLカード累計記録表',7)+'</row>')
 rows.append('<row r="2">'+_cell('A2','申請コールサイン',2)+_cell('B2',info.get('own',''),8)+_cell('D2','氏名',2)+_cell('E2',info.get('name',''),8)+_cell('G2','作成日',2)+_cell('H2',datetime.now().date().isoformat(),8)+'</row>')
 header=[_cell('A4','区分',1)]+[_cell(_col(i+2)+'4',label,1) for i,(_,label) in enumerate(BANDS)]+[_cell(totalcol+'4','計',1)]
 rows.append('<row r="4" ht="28" customHeight="1">'+''.join(header)+'</row>')
 for rn,(kind,label) in enumerate([('city','市の局数'),('gun','郡の局数'),('ward','区の局数')],5):
  cells=[_cell('A'+str(rn),label,2)]+[_cell(_col(i+2)+str(rn),counts[kind,key],8) for i,(key,_) in enumerate(BANDS)]
  cells.append(_cell(totalcol+str(rn),sum(counts[kind,key] for key,_ in BANDS),8));rows.append(f'<row r="{rn}">'+''.join(cells)+'</row>')
 cells=[_cell('A8','合計',1)]+[_cell(_col(i+2)+'8',sum(counts[k,key] for k in ('city','gun','ward')),8) for i,(key,_) in enumerate(BANDS)]
 cells.append(_cell(totalcol+'8',len(records),8));rows.append('<row r="8">'+''.join(cells)+'</row>')
 rows.append('<row r="10" ht="32" customHeight="1">'+_cell('A10','申請者は、累計記録表に記載したQSLカードを所持し、AJAリストと相違ないことを確認してください。',9)+'</row>')
 rows.append('<row r="11">'+_cell('A11','証明年月日',2)+_cell('B11','',8)+_cell('D11','コールサイン',2)+_cell('E11',info.get('own',''),8)+_cell('G11','氏名',2)+_cell('H11',info.get('signature') or info.get('name',''),8)+'</row>')
 widths='<cols><col min="1" max="1" width="18" customWidth="1"/><col min="2" max="%d" width="12" customWidth="1"/></cols>'%last
 return '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews><sheetView workbookViewId="0"><pane ySplit="4" topLeftCell="A5" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'+widths+'<sheetData>'+''.join(rows)+'</sheetData><mergeCells count="2"><mergeCell ref="A1:H1"/><mergeCell ref="A10:%s10"/></mergeCells><pageMargins left="0.3" right="0.3" top="0.4" bottom="0.4" header="0.2" footer="0.2"/><pageSetup paperSize="8" orientation="landscape" fitToWidth="1" fitToHeight="1"/></worksheet>'%totalcol

def xlsx_bytes(root,records,info=None):
 info=info or {};records,warnings=distinct(records)
 if not records:raise ValueError('AJA出力対象を選択してください。')
 master=load_master(root);out=io.BytesIO()
 styles='''<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="3"><font><sz val="9"/><name val="Arial"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="9"/><name val="Arial"/></font><font><b/><sz val="14"/><name val="Arial"/></font></fonts><fills count="5"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF1F4E78"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFD9EAF7"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFDDF3DD"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="2"><border/><border><left style="thin"><color rgb="FFB7B7B7"/></left><right style="thin"><color rgb="FFB7B7B7"/></right><top style="thin"><color rgb="FFB7B7B7"/></top><bottom style="thin"><color rgb="FFB7B7B7"/></bottom><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="10"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf><xf numFmtId="0" fontId="0" fillId="3" borderId="1" xfId="0" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf><xf numFmtId="49" fontId="0" fillId="0" borderId="1" xfId="0" applyAlignment="1"><alignment vertical="center"/></xf><xf numFmtId="49" fontId="0" fillId="4" borderId="1" xfId="0" applyAlignment="1"><alignment vertical="center"/></xf><xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>'''
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>')
  z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
  z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="AJA-List" sheetId="1" r:id="rId1"/><sheet name="累計記録表" sheetId="2" r:id="rId2"/></sheets><calcPr calcId="191029" fullCalcOnLoad="1" forceFullCalc="1"/></workbook>')
  z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/><Relationship Id="styles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
  z.writestr('xl/styles.xml',styles);z.writestr('xl/worksheets/sheet1.xml',_sheet_xml(master,records));z.writestr('xl/worksheets/sheet2.xml',_totals_xml(records,info))
 return out.getvalue()

def _value_xls(sheet,row,col,book):
 import xlrd
 cell=sheet.cell(row,col)
 if cell.ctype==3:return xlrd.xldate_as_datetime(cell.value,book.datemode).date().isoformat()
 if isinstance(cell.value,float) and cell.value.is_integer():return str(int(cell.value))
 return str(cell.value).strip()

def _xlsx_sheets(path):
 ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships','p':'http://schemas.openxmlformats.org/package/2006/relationships'}
 with zipfile.ZipFile(path) as z:
  shared=[]
  if 'xl/sharedStrings.xml' in z.namelist():shared=[''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',ns)]
  rels={x.attrib['Id']:x.attrib['Target'] for x in ET.fromstring(z.read('xl/_rels/workbook.xml.rels')).findall('p:Relationship',ns)};out={}
  book=ET.fromstring(z.read('xl/workbook.xml'))
  for sh in book.findall('m:sheets/m:sheet',ns):
   target=rels[sh.attrib['{'+ns['r']+'}id']].lstrip('/');target=target if target.startswith('xl/') else 'xl/'+target
   cells={}
   for c in ET.fromstring(z.read(target)).findall('.//m:c',ns):
    ref=c.attrib['r'];letters=re.match(r'[A-Z]+',ref)[0];col=0
    for ch in letters:col=col*26+ord(ch)-64
    row=int(re.search(r'\d+',ref)[0]);kind=c.attrib.get('t');v=c.find('m:v',ns)
    if kind=='inlineStr':value=''.join(c.find('m:is',ns).itertext())
    elif kind=='s' and v is not None:value=shared[int(v.text)]
    else:value=v.text if v is not None else ''
    cells[(row-1,col-1)]=value
   out[sh.attrib['name']]=cells
  return out

def import_workbook(path):
 path=Path(path);records=[];warnings=[]
 if path.suffix.lower()=='.xls':
  import xlrd
  book=xlrd.open_workbook(str(path));sheet=book.sheet_by_name('AJA-List')
  get=lambda r,c:_value_xls(sheet,r,c,book);ncols=sheet.ncols;maxrows=sheet.nrows
 else:
  sheets=_xlsx_sheets(path);cells=sheets.get('AJA-List')
  if cells is None:raise ValueError('AJA-Listシートがありません。')
  get=lambda r,c:cells.get((r,c),'');ncols=max((c for _,c in cells),default=0)+1;maxrows=max((r for r,_ in cells),default=0)+1
 bands=LEGACY_BANDS if ncols==44 else tuple(canonical_band(get(0,c)) or ('SAT' if 'SAT' in norm(get(0,c)) else '') for c in range(4,ncols,2))
 for row in range(3,maxrows):
  code=re.sub(r'\.0$','',get(row,3))
  if not re.fullmatch(r'\d{4,6}',code):
   continue
  for index,col in enumerate(range(4,ncols,2)):
   if index>=len(bands) or not bands[index]:continue
   mode=get(row,col);call=get(row,col+1)
   if not call:continue
   date=get(row+1,col+1);kind,note=region_kind(code,date)
   band=bands[index];unit=code+'@'+band;records.append({'unit':unit,'region':code,'region_type':kind or {4:'city',5:'gun',6:'ward'}[len(code)],'aja_band':band,'band':BAND_LABEL.get(band,band),'mode':mode,'call':call,'date':date,'station_key':base_call(call)+'@'+band,'confirmed':True,'source':'AJA表取込'})
   if note:warnings.append(code+' '+call+'：'+note)
 selected,duplicates=distinct(records);warnings.extend(duplicates)
 return {'records':selected,'warnings':warnings,'read':len(records),'selected':len(selected)}
