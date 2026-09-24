"""Conservative import of service-specific ADIF states into PSLog notes."""
from qsl_marks import tokens,change
from remarks_sections import append_primary


def import_marks(fields,remarks):
    notices=[]
    for service,prefix in (('LoTW','LOTW'),('eQSL','EQSL')):
        sent=fields.get(prefix+'_QSL_SENT','').strip().upper()
        received=fields.get(prefix+'_QSL_RCVD','').strip().upper()
        if not sent and not received:continue
        before=tokens(remarks)
        confirmed=(service+'.R').casefold()
        waiting=service.casefold()
        # Existing handwritten notes are authoritative enough to preserve,
        # but incompatible explicit standard fields must be shown for review.
        if (confirmed in before and (sent in ('N','R','Q','I') or received in ('N','R','I'))
                or service=='eQSL' and waiting in before and sent in ('N','R','Q','I')):
            notices.append(service+'の標準項目とRMKS記号が一致しません。RMKSを保持するため確認してください。')
            continue
        if sent=='Y' and received=='Y':
            remarks,_,_=change(remarks,service+'.R')
            if confirmed not in before:notices.append(service+'.Rを送信済み・受領済みの標準項目から設定します。')
        elif service=='eQSL' and sent=='Y' and received in ('','N','R'):
            if not before & {waiting,confirmed}:
                remarks=append_primary(remarks,service)
                notices.append('eQSLを送信済みの標準項目から設定します。')
        else:
            notices.append(service+'の状態はPSLog記号へ確定できないため、標準項目をADIF_EXTRAに保持します。')
    return remarks,notices
