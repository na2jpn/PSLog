"""Reload a previously generated PSLog JARL contest submission.

The importer is intentionally conservative: it accepts JARL R1.0/R2.1 text,
verifies the selected contest/category in the UI, and matches every submitted
QSO back to the canonical PSLog TXT records.  Canonical log files are never
modified by this module.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re

from contest_normalization import values as normalized_values
from model import validate_station
from search import file_identity
from sota_export import Selection
from storage import InvalidLog, StorageError


TAG_TO_INFO = {
    'CONTESTNAME': 'contest',
    'CATEGORYCODE': 'category',
    'CATEGORYNAME': 'categoryname',
    'CALLSIGN': 'callsign',
    'ADDRESS': 'address',
    'NAME': 'name',
    'POWER': 'power',
    'OPCALLSIGN': 'opcall',
    'TEL': 'tel',
    'EMAIL': 'email',
    'OPPLACE': 'opplace',
    'POWERSUPPLY': 'powersupply',
    'COMMENTS': 'comments',
    'MULTIOPLIST': 'multioplist',
    'LICENSECLASS': 'licenseclass',
    'POWERTYPE': 'powertype',
    'EQUIPMENT': 'equipment',
    'REGCLUBNAME': 'clubname',
    'REGCLUBNUMBER': 'clubnumber',
    'LICENSEDATE': 'licensedate',
    'AGE': 'age',
    'SIGNATURE': 'signature',
}


@dataclass
class ImportedQSO:
    date: str
    time: str
    band: str
    mode: str
    call: str
    checklog: bool = False
    rst_sent: str = ''
    sent: str = ''
    rst_received: str = ''
    received: str = ''
    combined_sent: str = ''
    combined_received: str = ''
    tx: str = ''


@dataclass
class ImportedSubmission:
    format: str
    zone: str
    info: dict
    rows: list
    total_score: str = ''


def _decode(data):
    for encoding in ('cp932', 'utf-8-sig', 'utf-8'):
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        if '<SUMMARYSHEET' in text and '<LOGSHEET' in text:
            return text
    raise ValueError('JARL提出TXTとして読み込めません。文字コード又は内容を確認してください。')


def _date_value(value):
    value = str(value).strip()
    m = re.fullmatch(r'(\d{4})年(\d{2})月(\d{2})日', value)
    return '-'.join(m.groups()) if m else value


def _tx_ids(rule, context):
    if (context or {}).get('submission_mode') == 'checklog':
        return []
    category = next((c for c in rule.get('event', {}).get('categories', []) if c.get('id') == (context or {}).get('category')), {})
    result = category.get('timing', {}).get('band_change', {}).get('tx_ids', [])
    if result:
        try:
            from contest_jarl import jarl_tx_ids
            result = jarl_tx_ids(rule, category)
        except (ImportError, ValueError, KeyError, TypeError):
            pass
    return list(result or [])


def _parse_log_row(line, rule, context):
    checklog = line.startswith('X ')
    if checklog:
        line = line[2:]
    rid = rule.get('id')
    profile = rule.get('event', {}).get('regional', {}).get('profile')
    parts = line.split('\t') if rid == 'qso_party' else line.split()
    if profile == 'ja0_serial':
        if len(parts) < 9:
            raise ValueError('提出ログの交信行を解釈できません: ' + line)
        row = ImportedQSO(parts[0], parts[1], parts[6], parts[7], parts[2], checklog=checklog,
                          combined_sent=parts[3], combined_received=parts[4])
        return row
    if len(parts) < 9:
        raise ValueError('提出ログの交信行を解釈できません: ' + line)
    date, time, band, mode, call = parts[:5]
    combined_ids = {'kcj', 'kcj-topband', 'miyazaki', 'all_hyogo', 'kcwa_cw', 'shizuoka', 'hiroshima_was'}
    if rid in combined_ids or profile == 'nara':
        row = ImportedQSO(date, time, band, mode, call, checklog=checklog,
                          combined_sent=parts[5], combined_received=parts[6])
        base_len = 9 if rid in combined_ids else 10
    else:
        if len(parts) < 11:
            raise ValueError('提出ログの交信行を解釈できません: ' + line)
        row = ImportedQSO(date, time, band, mode, call, checklog=checklog,
                          rst_sent=parts[5], sent=parts[6], rst_received=parts[7], received=parts[8])
        base_len = 11
    if _tx_ids(rule, context) and len(parts) > base_len:
        row.tx = parts[-1]
    return row


def parse_jarl(data, rule, context=None):
    """Parse a PSLog-generated JARL R1.0/R2.1 submission text."""
    text = _decode(data)
    m = re.search(r'<SUMMARYSHEET\s+VERSION=(R1\.0|R2\.1)>', text, re.I)
    if not m:
        raise ValueError('JARL R1.0/R2.1の提出TXTではありません。')
    version = m.group(1).upper()
    summary_end = text.find('</SUMMARYSHEET>')
    log_start = text.find('<LOGSHEET', summary_end)
    log_end = text.find('</LOGSHEET>', log_start)
    if summary_end < 0 or log_start < 0 or log_end < 0:
        raise ValueError('JARL提出TXTのSUMMARYSHEET/LOGSHEETが完結していません。')
    summary = text[:summary_end]
    info = {}
    tags = {name.upper(): value.strip() for name, value in re.findall(r'<([A-Z0-9]+)>(.*?)</\1>', summary, re.I | re.S)}
    for tag, key in TAG_TO_INFO.items():
        if tag in tags:
            info[key] = tags[tag]
    if 'DATE' in tags:
        info['date'] = _date_value(tags['DATE'])
    info['oath'] = bool(tags.get('OATH'))
    info['fd'] = 'FDCOEFF' in tags
    info['multiop'] = bool(tags.get('MULTIOPLIST'))
    info['guest'] = bool(tags.get('OPCALLSIGN'))
    total = tags.get('TOTALSCORE', '')
    log_text = text[log_start:log_end].splitlines()
    header_index = next((i for i, line in enumerate(log_text) if line.strip().startswith('DATE (')), None)
    if header_index is None:
        raise ValueError('JARL提出TXTのLOGSHEET見出しが見つかりません。')
    hm = re.search(r'DATE\s*\((JST|UTC)\)', log_text[header_index], re.I)
    zone = hm.group(1).upper() if hm else 'JST'
    info['zone'] = zone
    rows = []
    for raw in log_text[header_index + 1:]:
        line = raw.strip()
        if not line:
            continue
        rows.append(_parse_log_row(line, rule, context or {}))
    if not rows:
        raise ValueError('提出TXTに交信行がありません。')
    return ImportedSubmission('JARL ' + version, zone, info, rows, total)


def read_jarl(path, rule, context=None):
    path = Path(path)
    try:
        data = path.read_bytes()
    except OSError as e:
        raise StorageError('提出ログを読み込めません: ' + str(e)) from e
    return parse_jarl(data, rule, context)


def _to_jst(date, time, zone):
    try:
        dt = datetime.strptime(date + ' ' + time, '%Y-%m-%d %H:%M')
    except ValueError as e:
        raise ValueError('提出ログの日時形式が不正です: ' + date + ' ' + time) from e
    if zone == 'UTC':
        dt += timedelta(hours=9)
    return dt.strftime('%Y-%m-%d'), dt.strftime('%H:%M')


def _mode_equivalent(a, b):
    a = str(a).strip().upper(); b = str(b).strip().upper()
    if a == b:
        return True
    if a == 'SSB' and b in ('USB', 'LSB') or b == 'SSB' and a in ('USB', 'LSB'):
        return True
    return False


def _split_combined(value, rst):
    value = str(value); rst = str(rst or '')
    if rst and value.startswith(rst):
        return rst, value[len(rst):]
    # Last-resort split for ordinary RST-prefixed domestic rows.  Keep the
    # whole value as the exchange when no reliable prefix exists.
    for n in (3, 2):
        prefix = value[:n]
        if len(value) > n and re.fullmatch(r'[+-]?\d{2,3}', prefix):
            return prefix, value[n:]
    return rst, value


def _candidate_score(imported, qso, event):
    band, mode = normalized_values(event, qso.band, qso.mode)
    score = 0
    if str(imported.band).strip().upper() == str(band).strip().upper():
        score += 2
    if _mode_equivalent(imported.mode, mode):
        score += 2
    if imported.rst_sent and imported.rst_sent == qso.sent:
        score += 1
    if imported.rst_received and imported.rst_received == qso.received:
        score += 1
    return score


def match_to_pslog(repo, imported, rule, context=None):
    """Match every imported QSO back to one canonical PSLog row.

    Returns ``(Selection, draft)``.  No canonical file is modified.
    """
    context = context or {}
    sessions = {}
    index = {}
    for path in sorted(repo.book.glob('*.txt')):
        ident = file_identity(path)
        if not ident:
            continue
        session = repo.open(path)
        if session.log.issues:
            raise InvalidLog(path.name + 'に要確認行があります。提出ログの再読込を停止しました。')
        rp = path.resolve(); sessions[rp] = session
        for line, q in session.log.records:
            idx = (q.date, q.time, q.call.upper())
            index.setdefault(idx, []).append((ident[1], q, rp, line))
    event = rule.get('event', {})
    matched = []
    draft = {}
    for number, item in enumerate(imported.rows, 1):
        date, time = _to_jst(item.date, item.time, imported.zone)
        call = validate_station(item.call, '')
        candidates = list(index.get((date, time, call), []))
        if not candidates:
            raise ValueError(f'{number}行目 {date} {time} {call} に一致するPSLog原本交信が見つかりません。')
        if len(candidates) > 1:
            scored = [( _candidate_score(item, row[1], event), row) for row in candidates]
            best = max(s for s, _ in scored)
            candidates = [row for s, row in scored if s == best]
        if len(candidates) != 1:
            names = ', '.join(f'{r[2].name}:{r[3]}' for r in candidates[:5])
            raise ValueError(f'{number}行目 {date} {time} {call} がPSLog原本で複数候補になりました。通常の対象ログ選択から確認してください。候補: {names}')
        row = candidates[0]; matched.append(row); q = row[1]
        d = {'status': '確認済み'}
        if item.combined_sent:
            rst, exchange = _split_combined(item.combined_sent, q.sent); d['sent'] = exchange
            if rst and rst != q.sent: d['rst_sent'] = rst
        else:
            d['sent'] = item.sent
            if item.rst_sent and item.rst_sent != q.sent: d['rst_sent'] = item.rst_sent
        if item.combined_received:
            rst, exchange = _split_combined(item.combined_received, q.received); d['received'] = exchange
            if rst and rst != q.received: d['rst_received'] = rst
        else:
            d['received'] = item.received
            if item.rst_received and item.rst_received != q.received: d['rst_received'] = item.rst_received
        if item.checklog: d['checklog'] = True
        if item.tx: d['tx'] = item.tx
        spec = event.get('exchange', {})
        if spec.get('kind') in ('numbered_region', 'literal_region') and d.get('received') in set(spec.get('codes', [])):
            d['area'] = spec.get('region_map', {}).get(d['received'], d['received'])
        base_band, _ = normalized_values(event, q.band, q.mode)
        choices = event.get('band_choices', {}).get(base_band)
        if choices and str(item.band).strip().upper() in [str(x).upper() for x in choices]:
            d['contest_band'] = str(item.band).strip().upper()
        draft[(str(row[2]), row[3])] = d
    used = {row[2] for row in matched}
    return Selection([sessions[p] for p in sorted(used, key=str)], matched), draft


def scores_equal(imported_total, calculated):
    if imported_total in (None, '') or calculated is None:
        return True
    try:
        return Decimal(str(imported_total)) == Decimal(str(calculated))
    except (InvalidOperation, ValueError):
        return str(imported_total).strip() == str(calculated).strip()
