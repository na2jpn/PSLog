"""Read-only rule/condition summaries shared by contest, party and award viewers.

No Qt dependency: summaries can be regression-tested on Linux.  Missing facts are
reported as missing instead of guessed.
"""
from __future__ import annotations

import re
from datetime import datetime
from contest_overview import overview_rows
from party import PARTIES
from award_registry import AWARDS,target_count


def _sentences(values):
    out=[]
    for raw in values:
        for part in re.split(r'[。\n]+',str(raw or '')):
            part=part.strip()
            if part and part not in out:out.append(part)
    return out


def _event_texts(rule):
    event=rule.get('event',{}) or {}
    submission=event.get('submission',{}) or {}
    return _sentences(list(event.get('required_flags',[]) or [])+[submission.get('instructions','')])


def _view(rule,key):
    value=(rule.get('event',{}) or {}).get('rule_view',{}).get(key,'')
    return str(value).strip() if value else ''


def _pick(rule,*needles):
    matches=[]
    for sentence in _event_texts(rule):
        if any(n in sentence for n in needles):matches.append(sentence)
    return ' ／ '.join(matches[:3]) if matches else ''


def contest_call_method(rule):
    explicit=_view(rule,'call_method')
    if explicit:return explicit
    return '規約表示データに未登録（公式規約を確認）'


def contest_frequency(rule):
    # Frequency rules are display-only facts.  Do not infer them from submission
    # confirmation flags such as 「指定周波数を守った」 because those often
    # omit the actual permitted range and can even contain unrelated limits.
    return _view(rule,'frequency') or '規約表示データに未登録（公式規約を確認）'


def contest_repeat(rule):
    explicit=_view(rule,'repeat')
    if explicit:return explicit
    event=rule.get('event',{}) or {}
    if not (rule.get('duplicate') or {}).get('enabled',True):
        return 'PSLog規約データでは重複判定を行いません。公式規約を確認してください。'
    fields=list(event.get('duplicate_fields',[]) or [])
    if not fields:
        return '登録なし（公式規約を確認）'
    labels={'call':'相手局','band':'バンド','mode_family':'モード種別','mode_group':'モードグループ','my_grid':'自局GL','his_grid':'相手GL','own':'自局'}
    keys='＋'.join(labels.get(f,f) for f in fields)
    if fields==['call','band'] or set(fields)=={'call','band'}:
        return '同一相手局・同一バンドは重複扱い。バンドが変われば別交信として判定します。'
    return f'PSLog重複判定キー：{keys}。同じキーの交信は重複扱いです。'


def contest_counterparts(rule):
    explicit=_view(rule,'counterparts')
    if explicit:return explicit
    event=rule.get('event',{}) or {}
    flags=_event_texts(rule)
    joined=' ／ '.join(flags)
    # Common prefectural pattern explicitly represented by several registered
    # rules.  Only render the matrix when the rule text itself supports it.
    m=re.search(r'県外局の(?:得点)?相手は([^。／]+?県内)(?:のみ|局のみ)',joined)
    if m or ('県外局' in joined and '県内のみ' in joined):
        return '県内局 → 県内局：○\n県内局 → 県外局：○\n県外局 → 県内局：○\n県外局 → 県外局：×\n（県外局の得点相手は県内局のみ）'
    text=_pick(rule,'交信相手','得点相手','県外局','管外局','都外局','市外局','国内局','海外局')
    if text:return text
    # Region-labelled categories are useful context, but not enough to invent a
    # permitted-contact matrix.
    names=' / '.join(str(c.get('name','')) for c in event.get('categories',[]) if c.get('name'))
    if any(token in names for token in ('県内','県外','管内','管外','都内','都外')):
        return '地域別部門の登録あり。交信できる相手の組合せは公式規約を確認してください。'
    return '登録なし（公式規約を確認）'


def contest_restrictions(rule):
    return _view(rule,'restrictions') or '規約表示データに未登録（公式規約を確認）'


def contest_scoring(rule):
    point_override=_view(rule,'points_display')
    multi_override=_view(rule,'multipliers_display')
    pts=rule.get('points',{}) or {}
    point_text=' / '.join(f'{k}:{v}点' for k,v in pts.items()) or '得点登録なし'
    scoring=rule.get('scoring',{}) or {}
    multipliers=scoring.get('multipliers',[]) or []
    multi=[]
    for item in multipliers:
        name=str(item.get('id') or item.get('source') or 'multi')
        suffix='（バンド別）' if item.get('per_band') else ''
        multi.append(name+suffix)
    if not multi and (rule.get('multi1') or {}).get('kind')!='off':multi.append('第一マルチ')
    return point_override or point_text,multi_override or (' / '.join(multi) if multi else 'マルチなし／登録なし')


def is_contest_rule(rule):
    """Keep the QSO Party in its dedicated view, outside contest lists."""
    return rule.get('id') != 'qso_party'


def contest_sections(rule):
    overview={label:(text,important) for label,text,important in overview_rows(rule)}
    point_text,multi_text=contest_scoring(rule)
    event=rule.get('event',{}) or {};submission=event.get('submission',{}) or {}
    formats=' / '.join(submission.get('formats',[]) or []) or '提出形式の登録なし'
    required=' / '.join(submission.get('required_fields',[]) or []) or '追加必須欄の登録なし'
    url=str(rule.get('url') or '') or '登録なし'
    basic=[]
    view_overrides={'参加できる局':'participants','送信出力':'power','移動運用':'movement'}
    for label in ('主催','開催日時','対象バンド','対象モード','参加できる局','送信出力','移動運用'):
        if label in overview:
            if label=='移動運用' and not _view(rule,'movement'):
                continue
            text=overview[label][0]
            if label in view_overrides:text=_view(rule,view_overrides[label]) or text
            if label=='送信出力' and not _view(rule,'power'):
                text='制限なし'
            basic.append((label,text,overview[label][1]))
    exchange=_view(rule,'exchange') or overview.get('ナンバー交換',('登録なし',False))[0]
    special=contest_restrictions(rule)
    timing=overview.get('10分間ルール・時間制限',('登録なし',False))[0]
    if timing!='登録なし':
        special=(special+'\n' if _view(rule,'restrictions') else '')+timing
    practical=[
        ('呼び出し方法',contest_call_method(rule),True),
        ('交信対象',contest_counterparts(rule),True),
        ('同一局再交信条件',contest_repeat(rule),True),
        ('特殊なルール',special,True),
        ('ナンバー交換',exchange,True),
    ]
    scoring=[('通常得点',point_text,False),('マルチ定義',multi_text,False),('マルチバンド／オールバンド部門',overview.get('マルチバンド／オールバンド部門',('登録なし',False))[0],False)]
    submission_rows=[('提出締切',_view(rule,'submission_deadline') or overview.get('提出締切',('登録なし',False))[0],True),('提出形式',formats,False),('提出時の追加必須項目',required,False),('公式規約URL',url,False)]
    submission_notes=_view(rule,'submission_notes')
    if submission_notes:submission_rows.insert(1,('提出時の注意',submission_notes,True))
    other=[('参照年',str(rule.get('year','')),False),('ルールID',str(rule.get('id','')),False)]
    return [('基本情報','#2f6fa7',basic),('交信ルール','#2f7d4a',practical),('得点・マルチ','#b56a16',scoring),('提出','#7451a3',submission_rows),('その他','#66727a',other)]


def _fmt_party_stamp(value):
    try:return datetime.strptime(value,'%Y%m%d%H%M').strftime('%Y-%m-%d %H:%M JST')
    except ValueError:return value


PARTY_INFO={
    'nyp':dict(bands='アマチュア局に許可されたバンド（公式規約を確認）',exchange='PSLogではRMKSの交換内容を使用します。交換内容の詳細は公式規約を確認してください。',repeat='同一相手局は1局として集計します。'),
    'hamtte_spring':dict(bands='3.5 / 7 / 21 / 50 / 144 / 430 / 1200MHz以上（PSLog登録条件）',exchange='HAMtteメンバーは HMT を判定します。',repeat='同一相手局は1日1回として集計します。'),
    'hamtte_summer':dict(bands='3.5 / 7 / 21 / 50 / 144 / 430 / 1200MHz以上（PSLog登録条件）',exchange='HAMtteメンバーは HMT を判定します。',repeat='同一相手局は1日1回として集計します。'),
    'hamtte_winter':dict(bands='3.5 / 7 / 21 / 50 / 144 / 430 / 1200MHz以上（PSLog登録条件）',exchange='HAMtteメンバーは HMT を判定します。',repeat='同一相手局は1日1回として集計します。'),
    'jag_warc':dict(bands='10 / 18 / 24 MHz',exchange='PSLogでは会員交換内容 M を判定します。',repeat='同一相手局は1局として集計します。'),
    'welcome':dict(bands='3.5 / 7 / 21 / 28 / 50 / 144 / 430 / 1200 MHz（PSLog登録条件）',exchange='参加区分 N / C / W / HN / HC / HW を判定します。',repeat='同一相手局は同一日・同一バンドで1回として集計します。'),
}


def party_sections(kind):
    name,year,start,end=PARTIES[kind];info=PARTY_INFO.get(kind,{})
    basic=[('名称',name,False),('年度',year,False),('開催期間',_fmt_party_stamp(start)+' ～ '+_fmt_party_stamp(end),True),('対象バンド',info.get('bands','公式規約を確認'),False)]
    rules=[('交換内容',info.get('exchange','公式規約を確認'),True),('同一局の扱い',info.get('repeat','公式規約を確認'),True),('提出・達成条件','提出画面の登録条件と公式規約を確認してください。',False)]
    return [('基本情報','#2f6fa7',basic),('参加・交信ルール','#2f7d4a',rules),('補足','#66727a',[('注意','開催条件は年度ごとに変更される可能性があります。公式規約を併せて確認してください。',False)])]


AWARD_TYPE_LABELS={
    'area':'コールエリア','pref':'都道府県','city':'市','gun':'郡','ward':'区','aja':'AJA地域×バンド','asia':'アジアのエンティティ','grid_hf':'HFグリッド','grid_vu':'V/U/SHFグリッド','warc':'WARCバンド','vu':'V/UHF局','fuji':'ふじ対象衛星等','station':'JARL局','special':'専用条件'
}


def award_sections(root,award):
    kind=AWARDS[award][1]
    if kind.startswith('band:'):condition=kind.split(':',1)[1]+' MHz帯の交信'
    else:condition=AWARD_TYPE_LABELS.get(kind,kind)
    try:target=target_count(root,award)
    except Exception:target=0
    basic=[('アワード',award,False),('PSLog判定種別',condition,False),('目標数',str(target) if target else '専用条件による',True)]
    qualification=[('QSL条件','通常はQSL受領済みを初期条件にします。100周年系など一部はQSL不要です。',False),('重複整理','アワードごとの単位・同一局条件に従ってPSLogが候補を整理します。',False),('特記','バンド・モード・QRP等の特記は対応アワードで選択できます。',False)]
    application=[('申請用ログ','候補抽出後、申請用カードリスト／帳票を作成できます。',False),('過去実績','提出済み・認定済みの実績をPSLog内のアワード実績DBで管理できます。',False),('注意','正式な申請条件・最新規約は発行団体の案内を確認してください。',True)]
    return [('基本条件','#2f6fa7',basic),('達成条件','#b56a16',qualification),('申請','#7451a3',application)]
