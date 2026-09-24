from copy import deepcopy
from pathlib import Path
import unittest
from contest_rules import default_rule,score,loads,dumps
from contest_event import wpx_prefix,grid_distance,grid_center

def rule():
    r=default_rule();r.update(schema=2);r['multi1']['kind']='off';r['scoring']=dict(eligible={'all':[]},multipliers=[dict(id='area',source='exchange',kind='whole',start=0,length=2,per_band=True,when={'all':[]})],bonus=0)
    r['event']=dict(timezone='JST',windows=[dict(start='2026-08-22 21:00',end='2026-08-23 00:00',bands=['7','14']),dict(start='2026-08-23 06:00',end='2026-08-23 15:00',bands=['7','14'])],categories=[dict(id='A',name='test',bands=['7','14'],modes=['CW','SSB','FM'],max_power=100,min_bands=1,max_bands=2,min_calls=1,required_flags=[])],required_flags=['運用条件確認'],duplicate_fields=['call','band'],prefer='first',special='none')
    return r

def entry(**kw):return dict(dict(call='JA1AAA',date='2026-08-22',time='21:00',band='7',mode='CW',exchange='11'),**kw)
CTX=dict(category='A',power=100,flags={'運用条件確認':True})
class EventTests(unittest.TestCase):
    def test_stage_edges_and_next_morning_dupe(self):
        rows=[entry(time='20:59'),entry(),entry(date='2026-08-23',time='00:00'),entry(date='2026-08-23',time='06:00'),entry(date='2026-08-23',time='15:00')]
        s=score(rule(),rows,CTX);self.assertEqual([x['points'] for x in s.rows],[0,1,0,0,0]);self.assertEqual(s.total,1)
    def test_missing_context_power_minimum(self):
        r=rule();self.assertIsNone(score(r,[entry()]).total)
        c=deepcopy(CTX);c['power']=100.001;self.assertIsNone(score(r,[entry()],c).total)
        r['event']['categories'][0]['min_bands']=2;self.assertIsNone(score(r,[entry()],CTX).total)
        self.assertIsNotNone(score(r,[entry(),entry(band='14')],CTX).total)
    def test_cw_priority_and_rover_grid(self):
        r=rule();r['event']['prefer']='cw';s=score(r,[entry(mode='SSB'),entry(time='21:01')],CTX);self.assertEqual([x['points'] for x in s.rows],[0,1])
        r['event']['duplicate_fields']+=['his_grid'];s=score(r,[entry(his_grid='PM95'),entry(his_grid='PM96')],CTX);self.assertEqual(s.points,2)
        self.assertIsNone(score(r,[entry()],CTX).total)
    def test_utc_date_shift_and_no_mutation(self):
        r=rule();r['event']['timezone']='UTC';r['event']['windows']=[dict(start='2026-08-22 12:00',end='2026-08-22 12:01',bands=[])];v=entry();original=deepcopy(v)
        self.assertEqual(score(r,[v],CTX).total,1);self.assertEqual(v,original)
    def test_prefix_examples_and_ambiguous(self):
        for c,p in [('HG19ABC','HG19'),('LY1000A','LY1000'),('PA/N8BJQ','PA0'),('XEFTJW','XE0'),('JH1HST/3','JH3'),('JH1HST/P','JH1')]:self.assertEqual(wpx_prefix(c),p)
        with self.assertRaises(ValueError):wpx_prefix('AA1AA/BB2BB')
    def test_distance_and_unknown_grid(self):
        self.assertEqual(grid_distance('PM95','PM95'),0);self.assertAlmostEqual(grid_distance('AA00','RR99'),grid_distance('RR99','AA00'))
        with self.assertRaises(ValueError):grid_center('ZZ00')
        r=rule();r['event']['special']='grid_distance';s=score(r,[entry(my_grid='PM95',his_grid='PM95')],CTX);self.assertEqual(s.points,1)
        self.assertIsNone(score(r,[entry(my_grid='PM95',his_grid='ZZ00')],CTX).total)
    def test_strict_roundtrip_and_invalid_schema(self):
        r=rule();self.assertEqual(loads(dumps(r)),r);r['event']['prefer']='eval'
        with self.assertRaises(ValueError):loads(dumps(r))
if __name__=='__main__':unittest.main()
