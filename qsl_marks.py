"""Known independent QSL markers; preserve all unrelated note text."""
import re
from model import QSL_FLAGS
from storage import StorageError
from remarks_sections import primary,replace_primary

METHODS = ('BURO.R','CARD.R','1way.R','Direct.R','LoTW.R','eQSL.R','hQSL.R','QRZ.R','Other.R')
TOKEN = re.compile(r'(?<![\w./-])(?:'+ '|'.join(re.escape(x) for x in sorted(set(METHODS) | {m[:-2] for m in METHODS},key=len,reverse=True))+r')(?![\w./-])',re.I)


def tokens(remarks):
    return {m.group().casefold() for m in TOKEN.finditer(primary(remarks))}


def buro_judgement(remarks):
    """Return a human-facing BURO state for the current log contents."""
    before=tokens(remarks)
    if 'buro.r' in before:return '発送/受領済'
    if 'buro' in before:return '発送済'
    return ''


def receipt_state(remarks,method):
    """Describe whether the selected receipt method is already recorded/sent."""
    if method not in METHODS:raise StorageError('受領方法を選択してください。')
    before=tokens(remarks);received=method.casefold() in before;waiting=method[:-2].casefold() in before
    return {'received':received,'sent':waiting,'buro':buro_judgement(remarks)}


def _collapse_selected_tokens(text,method):
    """Promote waiting->received and keep a single selected receipt token.

    Other note text and other QSL methods are left untouched.  Removing an
    accidental duplicate can leave doubled spaces around punctuation; trim only
    obviously redundant horizontal whitespace, never rewrite arbitrary prose.
    """
    wanted={method.casefold(),method[:-2].casefold()};seen=False
    def repl(match):
        nonlocal seen
        if match.group().casefold() not in wanted:return match.group()
        if not seen:
            seen=True;return method
        return ''
    updated=TOKEN.sub(repl,text)
    updated=re.sub(r'[ \t]{2,}',' ',updated)
    updated=re.sub(r' +([,;])',r'\1',updated)
    return updated.strip() if text.strip()==text else updated


def change(remarks, method):
    if method not in METHODS: raise StorageError('受領方法を選択してください。')
    before=tokens(remarks);rmks1=primary(remarks)
    first=not bool(before & {x.casefold() for x in QSL_FLAGS})
    buro=method=='BURO.R' and not bool(before & {'buro','buro.r'})
    received=method.casefold() in before;waiting=method[:-2].casefold() in before
    if received or waiting:
        updated=_collapse_selected_tokens(rmks1,method)
    else:
        updated=rmks1+(' ' if rmks1 and not rmks1[-1].isspace() else '')+method
    return replace_primary(remarks,updated),first,buro
