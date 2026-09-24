"""Declarative Cabrillo layouts; explicit widths and no executable formatting."""
import json,re
from pathlib import Path
from contest_rules import keys,RuleStore,seed_bundled_folder

SOURCES=('frequency','mode','date','time','own','rst_sent','sent','call','rst_received','received','my_grid','his_grid','tx','literal')
COMMON=('NAME','ADDRESS','ADDRESS-CITY','ADDRESS-STATE-PROVINCE','ADDRESS-POSTALCODE','ADDRESS-COUNTRY','EMAIL','CLUB','OPERATORS','SOAPBOX','CATEGORY-OVERLAY','CERTIFICATE','GRID-LOCATOR')
V3=('CATEGORY-OPERATOR','CATEGORY-BAND','CATEGORY-POWER','CATEGORY-MODE','CATEGORY-ASSISTED','CATEGORY-STATION','CATEGORY-TIME','CATEGORY-TRANSMITTER','LOCATION')
V2=('CATEGORY','ARRL-SECTION')
ENUMS={'CATEGORY-OPERATOR':['SINGLE-OP','MULTI-OP','CHECKLOG','ROVER','HILLTOPPER'],'CATEGORY-POWER':['HIGH','LOW','QRP'],'CATEGORY-MODE':['CW','SSB','RTTY','FM','DIGI','DG','MIXED'],'CATEGORY-ASSISTED':['ASSISTED','NON-ASSISTED'],'CATEGORY-TRANSMITTER':['ONE','TWO','LIMITED','UNLIMITED','SWL'],'CERTIFICATE':['YES','NO']}
MODE_MAP={'CW':'CW','SSB':'PH','USB':'PH','LSB':'PH','AM':'PH','FM':'FM','RTTY':'RY','FT8':'DG','FT4':'DG','FT2':'DG','FREEDV':'DG'}
BAND_MAP={'1.8':'1800','1.9':'1800','3.5':'3500','3.8':'3500','7':'7000','14':'14000','21':'21000','28':'28000','29':'28000','50':'50','144':'144','430':'432','433':'432','1200':'1.2G','2400':'2.3G','5600':'5.7G','10000':'10G','24000':'24G'}

def default_template():
    fields=[('frequency',5,'right'),('mode',2,'left'),('date',10,'left'),('time',4,'left'),('own',13,'left'),('rst_sent',3,'right'),('sent',6,'left'),('call',13,'left'),('rst_received',3,'right'),('received',6,'left')]
    headers=[{'tag':tag,'required':tag in ('NAME','ADDRESS','CATEGORY-OPERATOR','CATEGORY-BAND','CATEGORY-POWER','CATEGORY-MODE'),'default':'','choices':ENUMS.get(tag,[])} for tag in (*V3,*COMMON)]
    return dict(schema=1,id='new-template',name='新しいテンプレート',year=2026,url='',version='3.0',contest='',encoding='ascii',frequency='band',rule_id='',headers=headers,columns=[{'source':s,'width':w,'align':a,'part':0,'literal':''} for s,w,a in fields],modes=dict(MODE_MAP))

def text(value,label):
    if not isinstance(value,str) or any(ord(c)<32 or ord(c)==127 for c in value):raise ValueError(label+' は改行・制御文字のない文字列です。')
    return value

def validate(t):
    keys(t,default_template(),'テンプレート')
    if type(t['schema']) is not int or t['schema']!=1:raise ValueError('未対応のテンプレート版です。')
    if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,79}',text(t['id'],'識別子')):raise ValueError('識別子は半角英数字・_・-（80文字まで）です。')
    for f in ('name','url','contest','rule_id'):text(t[f],f)
    if not t['name'].strip():raise ValueError('名称を入力してください。')
    if type(t['year']) is not int or not 1900<=t['year']<=9999:raise ValueError('参照年が不正です。')
    if t['version'] not in ('2.0','3.0') or t['encoding'] not in ('ascii','utf-8','cp932') or t['frequency'] not in ('band','actual'):raise ValueError('版・文字コード・周波数方針が未対応です。')
    if t['contest'] and not re.fullmatch('[A-Z0-9-]{1,32}',t['contest']):raise ValueError('CONTESTは半角大文字英数字と-、32文字までです。')
    if not isinstance(t['headers'],list) or len(t['headers'])>100:raise ValueError('ヘッダーは100項目までです。')
    seen=set();allowed=set(COMMON+(V3 if t['version']=='3.0' else V2))
    for h in t['headers']:
        keys(h,('tag','required','default','choices'),'ヘッダー');tag=text(h['tag'],'タグ')
        if tag in seen or tag not in allowed and not re.fullmatch('X-(?!QSO$)[A-Z0-9-]+',tag):raise ValueError('重複または選択版で未対応のヘッダー: '+tag)
        seen.add(tag);text(h['default'],'初期値')
        if type(h['required']) is not bool or not isinstance(h['choices'],list):raise ValueError('必須・候補の指定が不正です。')
        for c in h['choices']:text(c,'候補')
        if h['choices'] and h['default'] and h['default'] not in h['choices']:raise ValueError('初期値が候補に含まれていません: '+tag)
    if not isinstance(t['columns'],list) or not 1<=len(t['columns'])<=40:raise ValueError('QSO列は1～40列です。')
    for c in t['columns']:
        keys(c,('source','width','align','part','literal'),'QSO列')
        if c['source'] not in SOURCES or c['align'] not in ('left','right'):raise ValueError('未対応の列・文字寄せです。')
        if type(c['width']) is not int or not 1<=c['width']<=100 or type(c['part']) is not int or not 0<=c['part']<=20:raise ValueError('幅は1～100、部分番号は0～20です。')
        text(c['literal'],'固定文字')
    if not {'frequency','mode','date','time','own','call'} <= {c['source'] for c in t['columns']}:raise ValueError('周波数・MODE・日付・時刻・自局・相手局は必須のQSO列です。')
    if not isinstance(t['modes'],dict) or not t['modes']:raise ValueError('モード対応表が空です。')
    for k,v in t['modes'].items():
        if not text(k,'元モード').strip() or not re.fullmatch('[A-Z0-9]{2}',text(v,'出力モード')):raise ValueError('出力モードは半角大文字英数字2文字です。')
    return t

def loads(value):
    def pairs(items):
        r={}
        for k,v in items:
            if k in r:raise ValueError('JSONキーが重複しています: '+k)
            r[k]=v
        return r
    try:return validate(json.loads(value,object_pairs_hook=pairs))
    except (json.JSONDecodeError,RecursionError) as e:raise ValueError('テンプレートJSONが不正です: '+str(e)) from e

def dumps(t):return json.dumps(validate(t),ensure_ascii=False,indent=2)+'\n'
class TemplateStore(RuleStore):
    catalog_enabled=False
    decode=staticmethod(loads);encode=staticmethod(dumps)
    def __init__(self,root):
        root=Path(root).resolve()
        self.folder=root/'config'/'templates'/'cabrillo'
        seed_bundled_folder(self.folder,'config/templates/cabrillo','*.txt')
