"""Conservative Name and three-position paper QSL projection."""
import re
from qsl_marks import tokens
from adif_paper_qsl import fields
from remarks_sections import primary


def name_from_remarks(remarks,warnings):
    # Stored source metadata is evidence, not handwritten OP syntax.
    note=re.split(r'(?:ADIF_EXTRA|HAMLOG_EXTRA):',primary(remarks),maxsplit=1)[0].strip()
    starts=list(re.finditer(r'(?<![\w:])OP:',note,re.I))
    if not starts:return ''
    if len(starts)!=1:
        warnings.add('OP:が複数あるためName欄は空欄です。RMKSを確認してください。');return ''
    tail=note[starts[0].end():].strip()
    quoted=re.match(r'"([^"\r\n]+)"(?=$|[\s;,])',tail)
    if quoted:return quoted[1]
    first=re.match(r'([^\s;,"\r\n]+)(.*)$',tail)
    if first:
        value,rest=first.groups()
        if not rest.strip() or rest.startswith((';',',')) or all(tokens(x)=={x.casefold()} for x in rest.split()):
            return value
    warnings.add('OP:の名前とメモの境界が不明なためName欄は空欄です。複数語の名前はOP:"Taro Yamada"の形で指定できます。')
    return ''


def qsl_from_remarks(remarks,warnings):
    data=fields(remarks,warnings)
    if not data:return ''
    routes={data[k] for k in ('QSL_SENT_VIA','QSL_RCVD_VIA') if k in data}
    via=next(iter(routes)) if len(routes)==1 else ' '
    if len(routes)>1:warnings.add('紙カードの送受領経路が異なるためHAMLOGの経由先は空白です。詳細はRMKSに保持します。')
    return via+('*' if data.get('QSL_SENT')=='Y' else ' ')+('*' if data.get('QSL_RCVD')=='Y' else ' ')
