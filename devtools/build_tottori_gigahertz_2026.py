from rule_view_verified_remaining71 import apply as apply_remaining_view
"""2026 Tottori and Gigahertz definitions; build from explicit event fields.

Source notes retain local rules, JARL references and unverified boundaries.
No other event's category, award, location or power constraints are inherited.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contest_rules import loads, dumps
import rule_pack


def pack(path, rules, ident):
    with tempfile.TemporaryDirectory(dir=path.parent) as tmp:
        staged = Path(tmp)/path.name
        rule_pack.build(staged, [(r, 1, '1.01') for r in rules], ident)
        staged.replace(path)


def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def base(ident, name, reading, organizer, url, bands, windows):
    return dict(
        schema=2, id=ident, name=name, year=2026, url=url, organizer=organizer,
        sort_name=reading, points=dict(cw=1, phone=1, digital=0), conditions=[],
        duplicate=dict(enabled=True, by_mode=False),
        multi1=dict(kind='off', start=0, length=2, per_band=True),
        multi2=dict(kind='off', value=1, condition=dict(all=[])), formula='total',
        scoring=dict(eligible=dict(all=[]), multipliers=[dict(
            id='region', source='area', kind='whole', start=0, length=2,
            per_band=True, when=dict(all=[]))], bonus=0),
        event=dict(timezone='JST', windows=[dict(start=s, end=e, bands=bands) for s, e in windows],
                   categories=[], required_flags=[], duplicate_fields=['call', 'band', 'mode_family'],
                   prefer='first', special='none', entrant=dict(station_types=['individual', 'club'], guest_policy='allowed'),
                   normalization=dict(bands={b+'MHZ': b for b in bands}, modes={'USB': 'SSB', 'LSB': 'SSB'}, mode_families={})))


def category(code, name, bands, modes, sent, station_type, eligible=None):
    c = dict(id=code, name=name, bands=bands, modes=modes, max_power=None,
             min_bands=1, max_bands=len(bands), min_calls=1, required_flags=[],
             sent_codes=sent, station_types=[station_type])
    # Individual/club is a station licence classification, not SO/MO.
    if eligible is not None:
        c['eligible'] = dict(field='area', op='in', value=','.join(eligible))
    return c


def write(rule, db, source_name):
    ident = rule['id']
    apply_remaining_view(rule)
    data = dumps(rule)
    loads(data)
    (ROOT / f'config/rules/{ident}_2026.txt').write_text(data+'\n', encoding='utf-8')
    source = ROOT / 'docs/contest-research/sources' / source_name
    db.update(id=ident+'_numbers', year=2026, source=rule['url'],
              source_file=source_name, sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    (ROOT / f'config/db/contest/{ident}_2026.json').write_text(json.dumps(db, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    pack(ROOT / f'distribution/rules/{ident}_2026_r1.zip', [rule], ident+'_2026_r1')
    print(ident, len(rule['event']['categories']), 'categories')


def tottori():
    bands = ['3.5', '7', '14', '21', '28', '50', '144', '430', '1200']
    r = base('all_tottori', 'オール鳥取コンテスト', 'おーるとっとり', 'JARL鳥取県支部',
             'https://www.jarl.com/tottori/files/2026tttest_rules.pdf', bands,
             [('2026-10-12 06:00', '2026-10-12 12:00')])
    inside = dict(x.split(':') for x in '3401:鳥取市 3402:倉吉市 3403:米子市 3404:境港市 34001:岩美郡 34003:西伯郡 34004:東伯郡 34005:日野郡 34006:八頭郡'.split())
    outside = [f'{i:02}' for i in range(1, 48) if i != 34]
    local = list(inside)
    e = r['event']
    e['exchange'] = dict(kind='numbered_region', codes=local+outside, same_sent_region=True)
    e['normalization']['bands'].update({'1.2G': '1200', '1.2GHZ': '1200'})
    e['band_modes'] = {b: ['CW', 'SSB', 'AM'] + (['FM'] if b in bands[4:] else []) for b in bands}
    e['required_flags'] = [
        '国内局として参加し、県内外は実運用地、個人局・社団局は局の免許区分で確認した',
        '鳥取の独自番号（県内市郡、北海道01、小笠原10）を実際に完全交換し、事後に未受信情報を補っていない',
        '鳥取の周波数表と免許範囲を確認し、CW・AM・SSB・FM以外のデータモードを得点対象に含めない',
        '交信上の禁止事項はALL JA共通規約を確認した（クロスバンド・CW電話間クロスモード・レピータ・セルフスポット等）',
        '実際のSO/MOに従って同時送信制限と移動条件を確認した。移動SOの例外は運用開始時の鳥取用マルチ内で、MOへ流用しない',
        'この出力は選択した1種目の提出分であり、規約にない複数提出の許可を推定していない']
    phone = ['SSB', 'AM', 'FM']
    for prefix, label, sent in [('G', '県外', outside), ('T', '県内', local)]:
        eligible = local if prefix == 'G' else None
        for m, title, modes in [('C', '電信', ['CW']), ('X', '電信電話', ['CW']+phone)]:
            e['categories'].append(category(prefix+m+'A', label+' 個人局 マルチ '+title, bands, modes, sent, 'individual', eligible))
            for band in (['7'] if prefix == 'G' else bands):
                code = prefix+m+('35' if band == '3.5' else band)
                e['categories'].append(category(code, label+' 個人局 '+band+'MHz '+title, [band], modes, sent, 'individual', eligible))
        e['categories'].append(category(prefix+'P7', label+' 個人局 7MHz 電話', ['7'], phone, sent, 'individual', eligible))
        e['categories'].append(category(prefix+'XM', label+' 社団局 マルチ 電信電話', bands, ['CW']+phone, sent, 'club', eligible))
    assert len(e['categories']) == 28
    e['submission'] = dict(formats=['JARL R1.0', 'JARL R2.1'], zone='JST', contest='2026 オール鳥取コンテスト', instructions=(
        '2026年28種目。個人／社団は免許区分で、SO／MOと別です。申告得点（審査前）。'
        '電子ログはJARL R1.0又はR2.1をプレーンテキストのメール本文へ貼付。HTML・添付禁止。'
        '主催者はR2.0も受付しますが本ソフトの出力対象はR1.0/R2.1です。宛先test-tt@jarl.com、件名は運用時の自局コールのみ。'
        '締切2026-10-26 23:59必着。県内は紙提出も可（同日消印）、県外の紙提出はチェックログ扱い。'
        '開催前の支部告知と提出後の受理一覧を確認してください。自動送信・紙の正式様式生成は行いません。'))
    write(r, dict(inside=inside, outside=outside, notes='北海道01／小笠原10。県番号34は市郡番号の代用不可。'), 'all_tottori_2026.pdf')
    return r


def gigahertz():
    bands = ['1200', '2400', '5600', '10G', '24000', '47000', '77000', '135000', '248000']
    r = base('gigahertz', 'ギガヘルツコンテスト', 'ぎがへるつ', 'JARL新潟県支部',
             'https://www.jarl.com/08test/contest/2026/ghz/rule.html', bands,
             [('2026-09-12 21:00', '2026-09-13 00:00'), ('2026-09-13 06:00', '2026-09-13 12:00')])
    db = read('config/db/contest/jarl_municipal_2026.json')
    rows = [x for x in db['rows'] if x['contest_usable']]
    codes = [x['code'] for x in rows]
    inside = [x for x in codes if x[:2] in ('08', '09')]
    outside = [x for x in codes if x[:2] not in ('08', '09')]
    e = r['event']
    e['exchange'] = dict(kind='numbered_region', codes=codes, same_sent_region=True)
    e['entrant']['guest_policy'] = 'forbidden'
    e['duplicate_fields'] = ['call', 'band', 'mode_group']
    e['mode_groups'] = {'CW': 'cw', 'SSB': 'ssb', 'FM': 'fm'}
    e['band_modes'] = {b: ['CW', 'SSB', 'FM'] for b in bands}
    aliases = e['normalization']['bands']
    for number, target in [('1.2', '1200'), ('2.4', '2400'), ('5.6', '5600'), ('5.7', '5600'), ('10', '10G'), ('10.1', '10G'), ('10.4', '10G'), ('24', '24000'), ('47', '47000'), ('77', '77000'), ('135', '135000'), ('248', '248000')]:
        for suffix in ['G', 'GHZ']:
            aliases[number+suffix] = target
    aliases.update({'5700': '5600', '5700MHZ': '5600', '10100': '10G', '10100MHZ': '10G', '10400': '10G', '10400MHZ': '10G'})
    r['conditions'] = [dict(when=dict(field='band', op='eq', value='2400'), points=2),
                       dict(when=dict(field='band', op='in', value=','.join(bands[2:])), points=5)]
    e['required_flags'] = [
        '国内局としてゲスト運用せず、個人局／社団局と信越管内（新潟・長野）／管外を実態で確認した',
        '全帯域で実際の市郡区ナンバーを完全交換し、2桁県番号へ丸めたり事後に未受信情報を補っていない',
        '指定周波数・免許範囲を確認し、CW・SSB・FM以外、クロスバンド・クロスモード・レピータ・中継交信を含めない',
        '参加時間内に運用場所を変更していない。休止中に移動した場合は主催者等で可否を確認しており、ソフトが移動を許可したとは扱わない',
        '同一運用者による複数コール参加を行わず、JARL共通規約の実際のSO/MOに応じた同時送信等の条件を確認した',
        '放送・他通信への障害のおそれを避け、弥彦山で放送通信に影響する範囲の運用を行っていない',
        '提出種目と提出数は規約の範囲で確認し、未記載を理由に複数種目提出を独断で許可していない']
    for suffix, label, sent in [('I', '管内', inside), ('O', '管外', outside)]:
        for stem, title, bs, kind in [('KML', '個人局 マルチ', bands, 'individual'),
                                      ('K12', '個人局 1200MHz', ['1200'], 'individual'),
                                      ('K24', '個人局 2400MHz', ['2400'], 'individual'),
                                      ('K56', '個人局 5600MHz以上', bands[2:], 'individual'),
                                      ('SML', '社団局 マルチ', bands, 'club')]:
            e['categories'].append(category(stem+suffix, label+' '+title, bs, ['CW', 'SSB', 'FM'], sent, kind, inside if suffix=='O' else None))
    e['submission'] = dict(formats=['JARL R1.0', 'JARL R2.1'], zone='JST', contest='第35回ギガヘルツコンテスト',
        band_labels={b: b[:-3]+'G' for b in bands if b.endswith('000')},
        club_entry=dict(prefix=None, station_types=['individual', 'club'], regions=dict(inside_prefixes=['08-', '09-'], inside_label='信越管内', outside_label='信越管外')),
        instructions=('2026年10種目。CW/SSB/FM別に得点、マルチはモード共通・バンド別。10.1/10.4GHzは参照JARL表による10GHzの1バンド、5.6GHz等とは別。'
        'JARL R1.0を推奨、R2.1も出力可能（主催受付未検証）。件名は運用時コールと部門コード。宛先nitestlog@jarl.com、締切2026-09-28（郵送は消印有効）。'
        'メール本文／添付の別は規約に明記なし。クラブ対抗は登録番号と名称を記入し、08/09始まりを管内と判定。自局運用地の管内外とは独立です。'
        '休止中の移動・複数提出・最低バンド数は地方本文の明示なし。自動的に許可／禁止を補わず個別確認。紙は主催者リンクの新様式を使用。自動提出しません。'))
    source = next(x.name for x in (ROOT/'docs/contest-research/sources').glob('*gigahertz*.html'))
    write(r, dict(rows=rows, inside_codes=inside, outside_codes=outside, municipal_source_versions=db['source_versions'],
                  band_reference='https://www.jarl.org/Japanese/1_Tanoshimo/1-1_Contest/frequency.html',
                  notes='10.1/10.4GHz統合は2026-09-15参照表確認。最低帯数等の未記載事項は確認対象。'), source)
    return r


if __name__ == '__main__':
    rules = [tottori(), gigahertz()]
    pack(ROOT/'distribution/rules/tottori_gigahertz_2026_r1.zip', rules, 'tottori_gigahertz_2026_r1')
