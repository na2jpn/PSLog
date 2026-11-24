"""Keep contest instructions focused on the rules and submission steps.

The same presentation policy applies to bundled rules and previously installed
rule packs. Stored rule definitions and user edits are left intact.
"""
import re


def instructions(value):
    text = str(value or '')
    # Remove the old implementation/provenance footer without removing nearby
    # addresses, deadlines, format choices or actual contest requirements.
    for phrase in (
        '原案・原典はdocs/contest-researchに保存。',
        '主催受付・Windows実機は未検証。',
        '主催受付・Windows実機未検証。',
        '主催受付は未検証。',
        '距離境界の主催照合は未検証。',
        'JARL R1.0/R2.1の出力をPSLogで検証、主催者による受領審査は未確認。',
        '自動提出しません。', '自動送信しません。', '自動送信は行いません。',
    ):
        text = text.replace(phrase, '')
    text = text.replace('（主催受付未検証）', '')
    text = text.replace('、受付側の版別互換性は未検証', '')
    text = text.replace('自動送信・紙の正式様式生成は行いません。', '紙の正式様式生成は行いません。')
    text = re.sub(r'\d{4}参考版であり\d{4}へ自動更新しません。', '', text)
    text = re.sub(r'\d{4}へ自動更新しない。', '', text)
    return re.sub(r'[ \t]{2,}', ' ', text).strip()
