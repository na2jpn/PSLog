"""Category-scoped timing checks. No original log or exchange is rewritten.

Operating blocks are explicitly confirmed, half-open minute intervals. Silence
between QSOs is not assumed to be a break. Band checks use chronological order
but retain the caller's row order and stable row numbers in diagnostics.
"""
from datetime import datetime, timedelta
import re

HISTORY_FLAG = '参加区分の全運用履歴を対象に含め、運用区間・送信系列を確認した'
STAMP = '%Y-%m-%d %H:%M'


def stamp(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}', value):
        raise ValueError('日時は YYYY-MM-DD hh:mm で指定してください。')
    return datetime.strptime(value, STAMP)


def positive(value, name, minimum=1):
    if type(value) is not int or not minimum <= value <= 100000:
        raise ValueError(name + 'は整数で指定してください。')


def validate_timing(t):
    from contest_rules import keys
    if not isinstance(t, dict) or not t or set(t) - {'operating', 'band_change'}:
        raise ValueError('時間条件が不正です。')
    if 'operating' in t:
        o = t['operating']; keys(o, ('max_minutes', 'min_off_minutes'), '運用時間')
        positive(o['max_minutes'], '最大運用時間'); positive(o['min_off_minutes'], '最低休止時間', 0)
    if 'band_change' in t:
        b = t['band_change']
        if not isinstance(b, dict) or b.get('kind') not in ('stay', 'hourly'):
            raise ValueError('バンド変更方式が不正です。')
        field = 'min_minutes' if b['kind'] == 'stay' else 'max_changes'
        keys(b, ('kind', field, 'tx_ids', 'on_violation'), 'バンド変更')
        positive(b[field], field, 0 if field == 'max_changes' else 1)
        ids = b['tx_ids']
        if not isinstance(ids, list) or len(ids) > 16 or any(not isinstance(x,str) or not re.fullmatch('[A-Za-z0-9_-]{1,16}',x) for x in ids) or len(set(ids)) != len(ids):
            raise ValueError('送信系列IDが不正です。空配列は全系列共通です。')
        if b['on_violation'] not in ('block', 'exclude') or (b['kind'] == 'hourly' and b['on_violation'] != 'block'):
            raise ValueError('時間違反の扱いが未対応です。毎時変更数は出力停止のみ対応します。')


def parse_blocks(text):
    blocks = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip(): continue
        parts = line.split(' / ')
        if len(parts) != 2: raise ValueError(f'運用区間 {number}行目: 開始 / 終了 の形式で入力してください。')
        start, end = (p.strip() for p in parts)
        if stamp(start) >= stamp(end): raise ValueError(f'運用区間 {number}行目: 終了は開始より後です。')
        blocks.append(dict(start=start, end=end))
    return blocks


def check_operating(spec, windows, rows, ctx):
    raw = ctx.get('operating_blocks')
    if not isinstance(raw, list) or not 1 <= len(raw) <= 1000:
        return ['実際の運用区間を入力してください。交信間隔だけでは休止と判定しません。'], None
    try:
        blocks=[]
        for b in raw:
            if not isinstance(b,dict) or set(b) != {'start','end'}: raise ValueError('運用区間が不正です。')
            a,z=stamp(b['start']),stamp(b['end'])
            if a>=z: raise ValueError('運用区間の終了は開始より後です。')
            blocks.append((a,z))
        blocks.sort()
        # Union of the event windows; band eligibility is checked separately.
        merged=[]
        for a,z,_ in sorted(windows,key=lambda w:(w[0],w[1])):
            if merged and a<=merged[-1][1]: merged[-1]=(merged[-1][0],max(z,merged[-1][1]))
            else: merged.append((a,z))
        if not ctx.get('calendar_advisory') and any(not any(x<=a<z<=y for x,y in merged) for a,z in blocks):
            raise ValueError('運用区間が開催時間外または大会の休憩時間にかかっています。')
        total=0;last=None
        for a,z in blocks:
            if last is not None and a<last: raise ValueError('運用区間が重複しています。')
            gap=0 if last is None else int((a-last).total_seconds()/60)
            # Short gaps do not earn off-time credit. Adjacent blocks likewise
            # cannot evade the limit by splitting an operating session.
            if last is not None and gap<spec['min_off_minutes']: total+=gap
            total+=int((z-a).total_seconds()/60);last=z
        problems=[]
        for i,v in rows:
            dt=v['_contest_time']
            if not any(a<=dt<z for a,z in blocks): problems.append(f'{i+1}行目: 申告した運用区間に交信が含まれていません。')
        if total>spec['max_minutes']: problems.append(f'運用時間 {total}分は上限 {spec["max_minutes"]}分を超えています。')
        return problems, f'運用時間 {total}分 / 上限 {spec["max_minutes"]}分（{spec["min_off_minutes"]}分未満の空白は運用時間に算入）'
    except (ValueError,TypeError) as ex:
        return [str(ex)],None


def check_band_changes(spec, rows):
    problems=[];states={};counts={};violations=0;simultaneous={}
    for _,v in rows:
        tx=str(v.get('tx','')).strip() if spec['tx_ids'] else '*'
        simultaneous.setdefault((tx,v['_contest_time']),set()).add(str(v['band']))
    for i,v in sorted(rows,key=lambda pair:(pair[1]['_contest_time'],pair[0])):
        tx=str(v.get('tx','')).strip() if spec['tx_ids'] else '*'
        if spec['tx_ids'] and tx not in spec['tx_ids']:
            message='送信系列を指定してください: '+', '.join(spec['tx_ids'])
            v['_event_error']=message;problems.append(f'{i+1}行目: '+message);continue
        dt=v['_contest_time'];band=str(v['band']);prior=states.get(tx);violation=False
        if len(simultaneous[(tx,dt)])>1:
            message='同一分・同一送信系列に異なるバンドがあります。分精度のログでは変更順を確定できません。'
            v['_event_error']=message;problems.append(f'{i+1}行目: '+message);continue
        if prior is None: states[tx]=(band,dt);continue
        if band==prior[0]:continue
        if spec['kind']=='stay':
            violation=dt-prior[1]<timedelta(minutes=spec['min_minutes'])
            reason=f'送信系列 {tx}: バンド変更後の最初の交信から{spec["min_minutes"]}分未満の再変更'
        else:
            bucket=(tx,dt.replace(minute=0,second=0,microsecond=0))
            counts[bucket]=counts.get(bucket,0)+1
            violation=counts[bucket]>spec['max_changes']
            reason=f'送信系列 {tx}: {dt:%Y-%m-%d %H}時台のバンド変更が{spec["max_changes"]}回を超過'
        if violation:
            violations+=1
            if spec['on_violation']=='exclude':
                # JARL two-series policy: do not advance the legal series state
                # on an excluded contact, nor let it occupy the duplicate key.
                v['_excluded_reason']=reason;continue
            v['_event_error']=reason;problems.append(f'{i+1}行目: '+reason)
        states[tx]=(band,dt)
    return problems, f'バンド変更制限: {violations}件の違反候補（規則: {"滞在時間" if spec["kind"]=="stay" else "毎時変更数"}）'


def check_timing(category, windows, rows, ctx):
    spec=category.get('timing')
    if not spec:return [],[]
    problems=[];summary=[]
    flags=ctx.get('flags',{})
    if not isinstance(flags,dict) or flags.get(HISTORY_FLAG) is not True:
        problems.append('未確認: '+HISTORY_FLAG)
    # Includes duplicates and exchanges worth zero points. Scoring eligibility
    # must never shrink the operation history used by the timing validator.
    timed=[(i,v) for i,v in enumerate(rows) if v.get('_timing_scope')]
    if 'operating' in spec:
        p,s=check_operating(spec['operating'],windows,timed,ctx);problems.extend(p)
        if s:summary.append(s)
    if 'band_change' in spec:
        p,s=check_band_changes(spec['band_change'],timed);problems.extend(p);summary.append(s)
    return problems,summary
