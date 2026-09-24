"""Paper-card export: receipt never proves that our card was sent."""
import re
from qsl_marks import tokens
from remarks_sections import primary,append_primary


def fields(remarks,warnings):
    marks=tokens(remarks);result={}
    one_way_sent=bool(re.search(r'(?<![\w./-])my1way(?![\w./-])',primary(remarks),re.I))
    if marks & {'buro','card'} or one_way_sent:
        result['QSL_SENT']='Y'
        if 'buro' in marks and 'card' not in marks and not one_way_sent:
            result['QSL_SENT_VIA']='B'
    received=marks & {'buro.r','card.r','1way.r','direct.r'}
    if received:
        result['QSL_RCVD']='Y'
        if 'buro.r' in received and 'direct.r' not in received:
            result['QSL_RCVD_VIA']='B'
        elif 'direct.r' in received and 'buro.r' not in received:
            result['QSL_RCVD_VIA']='D'
        elif {'buro.r','direct.r'} <= received:
            warnings.add('紙カードの受領経路が複数あるためQSL_RCVD_VIAは省略し、RMKSに保持します。')
    return result


def import_marks(source,remarks):
    """Only explicit bureau routing has an unambiguous PSLog counterpart."""
    values={k:source.get(k,'').strip().upper() for k in
            ('QSL_SENT','QSL_SENT_VIA','QSL_RCVD','QSL_RCVD_VIA')}
    if not any(values.values()):return remarks,[]
    before=tokens(remarks);notices=[]
    sent=values['QSL_SENT'];received=values['QSL_RCVD']
    if (('buro' in before and sent in ('N','R','Q','I')) or
            ('buro.r' in before and received in ('N','R','I'))):
        return remarks,['紙カードの標準項目と既存BURO記号が矛盾します。RMKSを保持するため確認してください。']
    additions=[]
    if sent=='Y' and values['QSL_SENT_VIA']=='B' and 'buro' not in before:
        additions.append('BURO')
    if received=='Y' and values['QSL_RCVD_VIA']=='B' and 'buro.r' not in before:
        additions.append('BURO.R')
    if additions:
        remarks=append_primary(remarks,' '.join(additions))
        notices.append('ビューロ経由の標準項目から'+', '.join(additions)+'を反映します。')
    if received=='Y' and values['QSL_RCVD_VIA']=='B' and not (sent=='Y' or 'buro' in before):
        notices.append('ビューロ受領の記録がありますが発送済みか確認できません。返送の要否を確認してください。')
    for status,route in ((sent,values['QSL_SENT_VIA']),(received,values['QSL_RCVD_VIA'])):
        if (status or route) and not (status=='Y' and route=='B'):
            notices.append('紙カードの送受領状態・経路はPSLog記号へ確定できないためADIF_EXTRAに保持します。')
            break
    return remarks,notices
