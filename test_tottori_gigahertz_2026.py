from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json
import tempfile
import unittest

from PySide6.QtWidgets import QApplication, QComboBox
from contest import select_logs
from contest_rules import score, loads, dumps, RuleStore
from contest_export import plan, key
from contest_event_ui import EventDialog
from contest_submit_ui import SubmissionPane
from model import QSO
from storage import Repository
import rule_pack

ROOT = Path(__file__).parent


def rule(ident):
    return loads((ROOT/f'config/rules/{ident}_2026.txt').read_text(encoding='utf-8'))


def context(r, code):
    c = next(c for c in r['event']['categories'] if c['id'] == code)
    return dict(category=code, power=10, station_type=c['station_types'][0],
                flags={f: True for f in r['event']['required_flags']+c['required_flags']})


def trow(**kw):
    return dict(dict(date='2026-10-12', time='06:00', band='7', mode='CW',
                     call='JA4AAA', sent='13', exchange='3401'), **kw)


def grow(**kw):
    return dict(dict(date='2026-09-12', time='21:00', band='1200', mode='CW',
                     call='JA0AAA', sent='1319', exchange='0901'), **kw)


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def fixture(self, r, rows, ctx, **overrides):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        repo = Repository(tmp.name)
        own = overrides.pop('own', 'JH1HST')
        p = repo.path_for(own, '', rows[0]['date'])
        for v in rows:
            rst = '-01' if v['mode'] in ('FT8', 'FT4', 'FT2') else '599' if v['mode'] == 'CW' else '59'
            repo.open(p).append(QSO(v['date'], v['time'], v['band'], v['mode'], v['call'],
                                   rst, rst, 'Japan', 'Soka Japan', '元備考 KEEP', ''))
        before = p.read_bytes()
        sel = select_logs(repo, [p], own)
        draft = {key(rec): dict(sent=v['sent'], received=v['exchange'],
                               checklog=v.get('checklog', False), status='確認済み')
                 for rec, v in zip(sel.rows, rows)}
        info = dict(contest=r['event']['submission']['contest'], category=ctx['category'],
                    name='試験', address='試験', power=str(ctx['power']), date='2026-10-26',
                    signature='試験', oath=True, email='test@example.com', multiop=False,
                    comments='元の意見', multioplist='')
        info.update(overrides)
        return p, before, sel, draft, info


class TottoriTests(Fixture):
    def test_all_28_codes_both_jarl_versions_and_originals(self):
        r = rule('all_tottori')
        expected = {'GCA', 'GXA', 'GC7', 'GP7', 'GX7', 'GXM', 'TCA', 'TXA', 'TP7', 'TXM'}
        expected |= {'T'+m+b for m in 'CX' for b in ['35', '7', '14', '21', '28', '50', '144', '430', '1200']}
        self.assertEqual({c['id'] for c in r['event']['categories']}, expected)
        for c in r['event']['categories']:
            with self.subTest(code=c['id']):
                ctx = context(r, c['id'])
                rows = [trow(band=c['bands'][0], mode=c['modes'][0], sent=c['sent_codes'][0])]
                self.assertEqual(score(r, rows, ctx).total, 1)
                p, b, sel, d, info = self.fixture(r, rows, ctx)
                snapshot = deepcopy((d, info, ctx))
                for fmt in ('JARL R1.0', 'JARL R2.1'):
                    out = plan(sel, r, d, fmt, info, context=ctx)
                    self.assertIn('<CATEGORYCODE>'+c['id']+'</CATEGORYCODE>', out.preview())
                    self.assertIn('<TOTALSCORE>1</TOTALSCORE>', out.preview())
                    self.assertIn(b'\r\n', out.data)
                    self.assertNotIn(b'\n', out.data.replace(b'\r\n', b''))
                self.assertEqual((d, info, ctx), snapshot)
                self.assertEqual(p.read_bytes(), b)

    def test_cw_phone_points_and_phone_duplicate(self):
        r = rule('all_tottori'); ctx = context(r, 'GXA')
        rows = [trow(mode=m, band='430') for m in ('CW', 'SSB', 'FM', 'AM')]
        s = score(r, rows, ctx)
        self.assertEqual([x['points'] for x in s.rows], [1, 1, 0, 0])
        self.assertEqual((s.points, s.multi1, s.total), (2, 1, 2))
        rows.append(trow(band='1200'))
        self.assertEqual(score(r, rows, ctx).total, 6)

    def test_hokkaido_and_ogasawara_do_not_split(self):
        r = rule('all_tottori'); ctx = context(r, 'TCA')
        rows = [trow(sent='3401', exchange=e, call='JA1AA'+chr(65+i))
                for i, e in enumerate(['01', '01', '10', '10'])]
        s = score(r, rows, ctx)
        self.assertEqual((s.points, s.multi1, s.total), (4, 2, 8))
        for e in ('48', '106', '010', '34', '34002', '34001A'):
            self.assertIsNone(score(r, [trow(sent='3401', exchange=e)], ctx).total)
        db = json.loads((ROOT/'config/db/contest/all_tottori_2026.json').read_text(encoding='utf-8'))
        self.assertEqual(len(db['inside'])+len(db['outside']), 55)

    def test_outside_opponents_no_points_or_multipliers(self):
        r = rule('all_tottori'); ctx = context(r, 'GCA')
        rows = [trow(exchange='10'), trow(exchange='3401'), trow(exchange='3402', call='JA4BBB')]
        s = score(r, rows, ctx)
        self.assertEqual([x['points'] for x in s.rows], [0, 1, 1])
        self.assertEqual((s.multi1, s.total), (2, 4))
        self.assertEqual(score(r, [trow(sent='3401', exchange='10')], context(r, 'TCA')).total, 1)

    def test_time_band_mode_exclusions_keep_output_rows(self):
        r = rule('all_tottori'); ctx = context(r, 'GXA')
        rows = [trow(time='05:59'), trow(), trow(time='12:00'), trow(band='1.9'),
                trow(band='2400'), trow(band='10'), trow(mode='FM'), trow(mode='FT8'), trow(mode='DV')]
        s = score(r, rows, ctx)
        self.assertEqual([x['points'] for x in s.rows], [0, 1, 0, 0, 0, 0, 0, 0, 0])
        p, b, sel, d, info = self.fixture(r, rows, ctx)
        out = plan(sel, r, d, 'JARL R1.0', info, context=ctx)
        self.assertEqual(out.qsos, len(rows))
        self.assertEqual(p.read_bytes(), b)

    def test_station_classification_is_not_operator_count(self):
        r = rule('all_tottori')
        for code, station in [('GXM', 'club'), ('GXA', 'individual')]:
            ctx = context(r, code)
            for multiop in (False, True):
                p, b, sel, d, info = self.fixture(r, [trow()], ctx, multiop=multiop,
                                                multioplist='JA1AAA JA1BBB' if multiop else '')
                self.assertIn('<CATEGORYCODE>'+code+'</CATEGORYCODE>', plan(sel, r, d, 'JARL R1.0', info, context=ctx).preview())
                self.assertEqual(p.read_bytes(), b)
            ctx['station_type'] = 'individual' if station == 'club' else 'club'
            self.assertIsNone(score(r, [trow()], ctx).total)

    def test_sent_region_and_unsupported_category_stop(self):
        r = rule('all_tottori')
        self.assertIsNone(score(r, [trow(sent='3401')], context(r, 'GCA')).total)
        self.assertIsNone(score(r, [trow()], context(r, 'TCA')).total)
        self.assertIsNone(score(r, [trow(), trow(sent='10')], context(r, 'GCA')).total)
        self.assertIsNone(score(r, [trow()], dict(context(r, 'GCA'), category='GC14')).total)

    def test_modes_of_mixed_and_explicit_checklog(self):
        r = rule('all_tottori'); ctx = context(r, 'GXA')
        # Tottori imports ALL JA prohibitions, not its category composition.
        for m in ('CW', 'SSB'):
            self.assertEqual(score(r, [trow(mode=m)], ctx).total, 1)
        rows = [trow(checklog=True), trow(mode='SSB')]
        p, b, sel, d, info = self.fixture(r, rows, ctx)
        out = plan(sel, r, d, 'JARL R1.0', info, context=ctx).preview()
        self.assertIn('X 2026-10-12', out)
        self.assertIn('<TOTALSCORE>1</TOTALSCORE>', out)
        self.assertEqual(p.read_bytes(), b)


class GigahertzTests(Fixture):
    def test_all_10_categories_and_both_versions(self):
        r = rule('gigahertz')
        self.assertEqual({c['id'] for c in r['event']['categories']}, {s+p for s in ('KML', 'K12', 'K24', 'K56', 'SML') for p in 'IO'})
        for c in r['event']['categories']:
            with self.subTest(code=c['id']):
                ctx = context(r, c['id']); band = c['bands'][0]
                rows = [grow(band=band, sent=c['sent_codes'][0])]
                total = 1 if band == '1200' else 2 if band == '2400' else 5
                self.assertEqual(score(r, rows, ctx).total, total)
                p, b, sel, d, info = self.fixture(r, rows, ctx)
                for fmt in ('JARL R1.0', 'JARL R2.1'):
                    out = plan(sel, r, d, fmt, info, context=ctx).preview()
                    self.assertIn('<CATEGORYCODE>'+c['id']+'</CATEGORYCODE>', out)
                    self.assertIn('<TOTALSCORE>'+str(total)+'</TOTALSCORE>', out)
                self.assertEqual(p.read_bytes(), b)

    def test_raw_modes_each_point_but_common_multiplier(self):
        r = rule('gigahertz'); ctx = context(r, 'KMLO')
        for band, points in [('1200', 3), ('2400', 6), ('5600', 15)]:
            rows = [grow(band=band, mode=m) for m in ('CW', 'SSB', 'FM')]
            s = score(r, rows, ctx)
            self.assertEqual((s.points, s.multi1, s.total), (points, 1, points))
            rows += [grow(band=band, mode='USB'), grow(band=band, mode='FM', call='JA0BBB')]
            s = score(r, rows, ctx)
            self.assertEqual(s.rows[3]['points'], 0)
            self.assertEqual(s.multi1, 1)

    def test_nagano_niigata_and_full_municipal_codes(self):
        r = rule('gigahertz'); ctx = context(r, 'KMLO')
        rows = [grow(exchange=e, call='JA0AA'+chr(65+i)) for i, e in enumerate(['0901', '080101', '1319'])]
        s = score(r, rows, ctx)
        self.assertEqual([x['points'] for x in s.rows], [1, 1, 0])
        self.assertEqual(s.total, 4)
        for bad in ('08', '09', '0801', '99999', '09001A'):
            self.assertIsNone(score(r, [grow(exchange=bad)], ctx).total)
        self.assertEqual(score(r, [grow(sent='0901', exchange='1319')], context(r, 'KMLI')).total, 1)
        self.assertIsNone(score(r, [grow(sent='0901')], ctx).total)
        self.assertGreater(len(next(c for c in r['event']['categories'] if c['id']=='KMLO')['sent_codes']), 1000)

    def test_band_weights_and_10ghz_merge_with_output_labels(self):
        r = rule('gigahertz'); ctx = context(r, 'KMLO')
        rows = [grow(band=b) for b in ['1200', '2400', '5.7GHz', '10.1GHz', '10400', '24GHz', '47G', '77G', '135G', '248G']]
        s = score(r, rows, ctx)
        self.assertEqual([x['points'] for x in s.rows], [1, 2, 5, 5, 0, 5, 5, 5, 5, 5])
        self.assertEqual((s.points, s.multi1, s.total), (38, 9, 342))
        p, b, sel, d, info = self.fixture(r, rows, ctx)
        out = plan(sel, r, d, 'JARL R1.0', info, context=ctx).preview()
        self.assertEqual(out.count(' 10G CW '), 2)
        self.assertIn('<SCORE BAND=10G>2,5,1</SCORE>', out)
        self.assertIn('<SCORE BAND=24G>1,5,1</SCORE>', out)
        self.assertIn(' 248G CW ', out)
        self.assertEqual(p.read_bytes(), b)
        rows = [grow(), grow(band='2400')]
        self.assertEqual(score(r, rows, ctx).total, 6)

    def test_time_gaps_and_unsupported_modes(self):
        r = rule('gigahertz'); ctx = context(r, 'KMLO')
        rows = [grow(time='20:59'), grow(), grow(date='2026-09-13', time='00:00'),
                grow(date='2026-09-13', time='05:59'), grow(date='2026-09-13', time='06:00', mode='SSB'),
                grow(date='2026-09-13', time='12:00'), grow(mode='AM'), grow(mode='DV'), grow(mode='FT8'), grow(band='430')]
        s = score(r, rows, ctx)
        self.assertEqual([x['points'] for x in s.rows], [0, 1, 0, 0, 1, 0, 0, 0, 0, 0])
        self.assertEqual(s.total, 2)
        # The two windows share one duplicate ledger.
        self.assertEqual(score(r, [grow(), grow(date='2026-09-13', time='06:00')], ctx).total, 1)

    def test_k56_only_high_bands_and_club_not_mo(self):
        r = rule('gigahertz'); ctx = context(r, 'K56O')
        s = score(r, [grow(band='2400'), grow(band='5600')], ctx)
        self.assertEqual([x['points'] for x in s.rows], [0, 5])
        ctx = context(r, 'SMLO')
        p, b, sel, d, info = self.fixture(r, [grow()], ctx, own='JS1YJY')
        self.assertIn('<CATEGORYCODE>SMLO</CATEGORYCODE>', plan(sel, r, d, 'JARL R1.0', info, context=ctx).preview())
        ctx['station_type'] = 'individual'
        self.assertIsNone(score(r, [grow()], ctx).total)

    def test_guest_and_inconsistent_sent_location_stop(self):
        r = rule('gigahertz'); ctx = context(r, 'KMLO')
        for kwargs in [dict(guest=True, opcall='JA1BBB'), dict(guest=False, opcall='JA1BBB')]:
            p, b, sel, d, info = self.fixture(r, [grow()], ctx, **kwargs)
            with self.assertRaisesRegex(ValueError, 'ゲスト'):
                plan(sel, r, d, 'JARL R1.0', info, context=ctx)
            self.assertEqual(p.read_bytes(), b)
        self.assertIsNone(score(r, [grow(), grow(sent='100116', mode='SSB')], ctx).total)

    def test_registered_club_location_independent_and_name_retained_r21(self):
        r = rule('gigahertz')
        for code, sent, number, label in [('KMLO', '1319', '08-01-01', '信越管内'),
                                          ('KMLO', '1319', '09-01-01', '信越管内'),
                                          ('KMLI', '0901', '13-01-01', '信越管外')]:
            ctx = context(r, code)
            p, b, sel, d, info = self.fixture(r, [grow(sent=sent)], ctx, clubnumber=number, clubname='試験クラブ')
            original = deepcopy(info)
            for fmt in ('JARL R1.0', 'JARL R2.1'):
                for _ in range(2):
                    out = plan(sel, r, d, fmt, info, context=ctx).preview()
                    self.assertIn('区分: '+label, out)
                    self.assertIn('試験クラブ', out)
                    self.assertEqual(out.count('登録クラブ対抗:'), 1)
                    self.assertIn('<CATEGORYCODE>'+code+'</CATEGORYCODE>', out)
            self.assertEqual(info, original)
            self.assertEqual(p.read_bytes(), b)

    def test_club_optional_and_bad_fields_rejected(self):
        r = rule('gigahertz'); ctx = context(r, 'KMLO')
        p, b, sel, d, info = self.fixture(r, [grow()], ctx)
        self.assertNotIn('登録クラブ対抗:', plan(sel, r, d, 'JARL R1.0', info, context=ctx).preview())
        for number, name in [('08-01-01', ''), ('', '名前')]:
            allowed = dict(info, clubnumber=number, clubname=name)
            plan(sel, r, d, 'JARL R1.0', allowed, context=ctx)
        for number in ['08', '08-01-01x']:
            bad = dict(info, clubnumber=number, clubname='名前')
            with self.assertRaises(ValueError):
                plan(sel, r, d, 'JARL R1.0', bad, context=ctx)
        self.assertEqual(p.read_bytes(), b)


class IntegrationTests(Fixture):
    def test_gui_categories_station_and_submission_fields(self):
        for ident, code, row, count in [('all_tottori', 'GXM', trow(), 28), ('gigahertz', 'SMLO', grow(), 10)]:
            r = rule(ident); ctx = context(r, code)
            dialog = EventDialog(r['event'], ctx)
            self.assertEqual(dialog.category.count(), count)
            self.assertEqual(dialog.station_type.currentData(), 'club')
            self.assertIn('社団局', dialog.summary.text())
            dialog.apply(); self.assertEqual(dialog.context['category'], code)
            dialog.deleteLater()
            p, b, sel, d, info = self.fixture(r, [row], ctx)
            tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
            fmt = QComboBox(); fmt.addItem('JARL R1.0')
            w = SimpleNamespace(repo=Repository(tmp.name), format=fmt, selection=sel, draft=d,
                                loaded_scope=('JH1HST',), rule=r, result=score(r, [row], ctx),
                                event_context=lambda: ctx, activity_name='コンテスト')
            pane = SubmissionPane(w); pane.set_context()
            self.assertEqual(pane.fields['callsign'].text(), 'JH1HST')
            self.assertEqual(pane.fields['categoryname'].text(), next(c['name'] for c in r['event']['categories'] if c['id']==code))
            self.assertTrue(pane.folder.text().endswith(str(Path('output')/'contest')))
            self.assertIn('#c62828', pane.score_overview.styleSheet())
            self.assertIn('入力内容を確認', pane.status.text())
            for field, value in info.items():
                if field not in pane.fields: continue
                widget = pane.fields[field]
                if isinstance(value, bool): widget.setChecked(value)
                else: widget.setText(value)
            self.assertIn('<CATEGORYCODE>'+code+'</CATEGORYCODE>', plan(sel, r, d, 'JARL R1.0', pane.info(), context=ctx).preview())
            pane.deleteLater(); fmt.deleteLater()
            self.assertEqual(p.read_bytes(), b)

    def test_packs_install_idempotent_and_self_contained(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = RuleStore(Path(tmp)); folder = ROOT/'distribution/rules'
            both = folder/'tottori_gigahertz_2026_r1.zip'
            self.assertEqual(rule_pack.install(store, rule_pack.preview(store, both)), 2)
            for name in ['all_tottori_2026_r1.zip', 'gigahertz_2026_r1.zip', both.name]:
                self.assertEqual(rule_pack.install(store, rule_pack.preview(store, folder/name)), 0)
            items = {store.read(p)[0]['id']: store.read(p)[0] for p in store.files()}
            self.assertEqual(score(items['all_tottori'], [trow()], context(items['all_tottori'], 'GCA')).total, 1)
            self.assertEqual(score(items['gigahertz'], [grow()], context(items['gigahertz'], 'KMLO')).total, 1)

    def test_club_schema_and_old_restriction(self):
        mutations = [lambda c: c.update(prefix=''), lambda c: c.update(prefix=[]),
                     lambda c: c['regions'].update(inside_prefixes=['08-', '08-']),
                     lambda c: c['regions'].update(inside_prefixes=['8-']),
                     lambda c: c['regions'].update(inside_label='<bad>'),
                     lambda c: c['regions'].update(inside_label=c['regions']['outside_label']),
                     lambda c: c.update(prefix='08-'), lambda c: c.update(station_types=['special'])]
        for change in mutations:
            r = rule('gigahertz'); change(r['event']['submission']['club_entry'])
            with self.assertRaises(ValueError): dumps(r)
        from contest_club import submission_info
        old = rule('all_chiba')['event']['submission']['club_entry']
        outside = dict(clubnumber='08-01-01', clubname='名前')
        self.assertEqual(submission_info(old, dict(station_type='individual'), outside), outside)
        info = dict(clubnumber='12-01-01', clubname='名前')
        self.assertEqual(submission_info(old, dict(station_type='individual'), info), info)

    def test_band_label_validation_and_sent_dictionary_limit(self):
        for labels in ({'1200': '10G'}, {'1200': '<bad>'}, {'999': '99G'}, {'1200': None}, {}):
            r = rule('gigahertz'); r['event']['submission']['band_labels'] = labels
            with self.assertRaises(ValueError): dumps(r)
        from contest_event import lists
        with self.assertRaises(ValueError): lists([str(i) for i in range(1001)], 'other')
        r = rule('gigahertz')
        r['event']['categories'][0]['sent_codes'] = ['99999']
        with self.assertRaises(ValueError): dumps(r)
        r = rule('gigahertz')
        r['event']['categories'][0]['sent_codes'] *= 2
        with self.assertRaises(ValueError): dumps(r)

    def test_unconfirmed_flags_and_format_mismatch_stop(self):
        for ident, code, row in [('all_tottori', 'GCA', trow()), ('gigahertz', 'KMLO', grow())]:
            r = rule(ident); ctx = context(r, code)
            ctx['flags'].pop(r['event']['required_flags'][0])
            self.assertIsNone(score(r, [row], ctx).total)
            ctx = context(r, code)
            p, b, sel, d, info = self.fixture(r, [row], ctx)
            for fmt in ['Cabrillo', 'zLog令和版CSV']:
                with self.assertRaises(ValueError): plan(sel, r, d, fmt, info, context=ctx)
            self.assertEqual(p.read_bytes(), b)


if __name__ == '__main__':
    unittest.main()
