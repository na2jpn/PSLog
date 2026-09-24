"""Optional registered-club checks, independent of the entrant's operating site."""
import re


def validate(spec, event):
    from contest_rules import keys
    from contest_event import lists
    keys(spec, {'prefix', 'station_types'} | set(spec).intersection({'regions'}), 'クラブ対抗')
    prefix = spec['prefix']
    if prefix is not None and (not isinstance(prefix, str) or not re.fullmatch('[0-9]{2}-', prefix)):
        raise ValueError('クラブ番号の接頭辞が不正です。')
    lists(spec['station_types'], 'クラブ対抗の局種')
    if not spec['station_types'] or not set(spec['station_types']) <= set(event.get('entrant', {}).get('station_types', [])):
        raise ValueError('クラブ対抗の局種が不正です。')
    if 'regions' in spec:
        regions = spec['regions']
        keys(regions, ('inside_prefixes', 'inside_label', 'outside_label'), 'クラブ地域')
        lists(regions['inside_prefixes'], 'クラブ管内接頭辞')
        if not regions['inside_prefixes'] or any(not re.fullmatch('[0-9]{2}-', x) for x in regions['inside_prefixes']):
            raise ValueError('クラブ管内接頭辞が不正です。')
        if prefix is not None:
            raise ValueError('クラブ地域分類は全国の登録番号を受け付ける設定で指定してください。')
        for key in ('inside_label', 'outside_label'):
            value = regions[key]
            if not isinstance(value, str) or not value.strip() or len(value) > 80 or any(ord(c) < 32 or c in '<>' for c in value):
                raise ValueError('クラブ地域名が不正です。')
            try:
                value.encode('cp932')
            except UnicodeEncodeError as exc:
                raise ValueError('クラブ地域名はJARL出力可能な文字で指定してください。') from exc
        if regions['inside_label'] == regions['outside_label']:
            raise ValueError('クラブ管内外の地域名は区別してください。')


def submission_info(spec, context, info):
    from contest_export import clean
    if not spec or not (info.get('clubnumber') or info.get('clubname')):
        return info
    number = clean(info.get('clubnumber', ''), '登録クラブ番号')
    name = clean(info.get('clubname', ''), '登録クラブ名')
    prefix = spec['prefix']
    pattern = (re.escape(prefix) if prefix is not None else r'[0-9]{2}-') + r'[0-9]{2}-[0-9]{2}'
    # Club fields are always allowed to pass through to the JARL summary.
    # Some organizers simply ignore an ineligible club declaration, and users may
    # intentionally keep their registered club on every submission.  Therefore
    # PSLog no longer blocks output based on area/station eligibility.  The extra
    # regional declaration is added only when this rule's club conditions match.
    if context.get('station_type') not in spec['station_types'] or not re.fullmatch(pattern, number):
        return info
    if 'regions' not in spec or not name:
        return info
    regions = spec['regions']
    label = regions['inside_label'] if number[:3] in regions['inside_prefixes'] else regions['outside_label']
    result = dict(info)
    # R2.1 has no REGCLUBNAME output in the existing exporter. Keep both
    # identifiers in the declaration as well, without editing the input dict.
    declaration = '登録クラブ対抗: ' + number + ' ' + name + '／区分: ' + label + '（登録番号による）'
    result['comments'] = ' '.join(x for x in (info.get('comments', '').strip(), declaration) if x)
    return result
