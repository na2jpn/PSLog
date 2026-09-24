"""Schema 2: independent multiplier eligibility, additive sets and final bonus.

No eval, imports or executable expressions in rule documents. Legacy schema 1
retains its original semantics. Entry annotations belong to submission drafts.
"""
from decimal import Decimal

SOURCES = ('exchange', 'area', 'prefix', 'country', 'continent')

def validate_scoring(s):
    from contest_rules import keys, condition, number
    keys(s, ('eligible', 'multipliers', 'bonus'), '拡張採点')
    condition(s['eligible']); number(s['bonus'], '最終加算点')
    if not isinstance(s['multipliers'], list) or not 1 <= len(s['multipliers']) <= 16:
        raise ValueError('マルチは1～16種類で指定してください。')
    seen = set()
    for m in s['multipliers']:
        keys(m, ('id', 'source', 'kind', 'start', 'length', 'per_band', 'when'), 'マルチ集合')
        import re
        if not isinstance(m['id'], str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,39}', m['id']) or m['id'] in seen:
            raise ValueError('マルチ集合の識別子が不正または重複しています。')
        seen.add(m['id'])
        if m['source'] not in SOURCES or m['kind'] not in ('whole', 'digits', 'slice'):
            raise ValueError('未対応のマルチ抽出です。')
        if type(m['start']) is not int or not 0 <= m['start'] <= 100000 or type(m['length']) is not int or not 1 <= m['length'] <= 100000 or type(m['per_band']) is not bool:
            raise ValueError('マルチの位置・文字数・バンド指定が不正です。')
        condition(m['when'])

def steps(rule, entries):
    from contest_rules import Score, matches, family, digits
    from dataclasses import replace
    s = rule['scoring']; seen = set(); sets = {m['id']: set() for m in s['multipliers']}
    rows = []; problems = []; bands = {}; qualifying = []
    for i, entry in enumerate(entries):
        try:
            v = dict(entry)
            if v.get('_event_error'):raise ValueError(v['_event_error'])
            for field in ('call', 'band', 'mode'):
                if not isinstance(v.get(field), str) or not v[field].strip():
                    raise ValueError(field + 'が未設定です。')
                v[field] = v[field].strip().upper()
            v['exchange'] = str(v.get('exchange', '')).strip().upper()
            if v.get('continent') is not None:
                v['continent'] = v['continent'].strip().upper()
                if v['continent'] not in ('AF','AN','AS','EU','NA','OC','SA'):
                    raise ValueError('大陸が不正です。')
            mode = v.get('mode_family',family(v['mode'])) if 'event' in rule else family(v['mode'])
            if mode is None and not v.get('_whole_checklog') and '_uniform_mode_points' not in v: raise ValueError('未分類のモード: ' + v['mode'])
            key = v.get('_duplicate_key',(v['call'], v['band'], v['mode'] if rule['duplicate']['by_mode'] else ''))
            duplicate = rule['duplicate']['enabled'] and key in seen
            eligible = False if duplicate or v.get('_excluded_reason') else matches(s['eligible'], v)
            points = Decimal(0); tokens = []; qualifies = False
            reason = v.get('_excluded_reason') or ('重複' if duplicate else '対象外')
            if eligible:
                points = Decimal(str(v['_uniform_mode_points'] if '_uniform_mode_points' in v else rule['points'][mode])); reason = '通常点'
                for n, c in enumerate(rule['conditions'], 1):
                    if matches(c['when'], v):
                        points = Decimal(str(c['points'])); reason = f'条件 {n}'; break
                if '_computed_points' in v:points=Decimal(str(v['_computed_points']))
                for m in s['multipliers']:
                    if v.get('_regional_multi') is False or m['id'] in v.get('_skip_multis',[]) or not matches(m['when'], v): continue
                    token = v.get(m['source'])
                    if token is None or not str(token).strip():
                        raise ValueError('マルチ抽出元が空欄です: ' + m['source'])
                    token = str(token).strip().upper()
                    if m['kind'] == 'digits': token = digits(token)
                    if m['kind'] == 'slice':
                        if len(token) < m['start'] + m['length']:
                            raise ValueError('マルチ抽出位置が範囲外です。')
                        token = token[m['start']:m['start']+m['length']]
                    tokens.append((m['id'], v['band'] if m['per_band'] else '', token))
                if points > 0 and rule['multi2']['kind'] in ('bands', 'qsos'):
                    qualifies = matches(rule['multi2']['condition'], v)
            # Commit only after the entire row passes validation. Ineligible rows
            # must not prevent a later eligible contact from scoring.
            if eligible: seen.add(key)
            band = bands.setdefault(v['band'], {'points': Decimal(0), 'multis': set()})
            band['points'] += points
            judgements=[]
            for ident, scope, token in tokens:
                is_new=(scope,token) not in sets[ident]
                judgements.append((ident,'新規' if is_new else '既出'))
                sets[ident].add((scope, token)); band['multis'].add((ident, token))
            if qualifies: qualifying.append(v['band'])
            if len(judgements)==1:multi_judgement=judgements[0][1]
            else:multi_judgement=' / '.join(ident+':'+status for ident,status in judgements) if judgements else None
            rows.append({'points': points, 'multi': ' / '.join(k+':'+t for k,_,t in tokens) or None, 'reason': reason, 'eligible': eligible, 'multiplier_values': [t for _,_,t in tokens], 'multiplier_tokens': list(tokens), 'multiplier_judgement': multi_judgement})
        except (ValueError, TypeError) as e:
            problems.append(f'{i+1}行目: {e}'); rows.append({'points': None, 'multi': None, 'reason': str(e)})
        if (i+1) % 100 == 0: yield i+1
    points = sum((b['points'] for b in bands.values()), Decimal(0))
    counts = {name: len(values) for name, values in sets.items()}; m1 = sum(counts.values())
    m = rule['multi2']; m2 = (1 if m['kind']=='off' else Decimal(str(m['value'])) if m['kind']=='fixed'
                              else len(set(qualifying)) if m['kind']=='bands' else len(qualifying))
    base = points*m1 if rule['formula']=='total' else sum(b['points']*len(b['multis']) for b in bands.values())
    result = Score(points, m1, m2, None if problems else base*m2+Decimal(str(s['bonus'])), rows, problems)
    result.multiplier_counts = counts
    result.final_bonus = s['bonus']
    return result
