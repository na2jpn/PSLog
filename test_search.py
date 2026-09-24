import tempfile
import unittest
from dataclasses import replace
from model import QSO
from storage import Repository, ExternalChange, InvalidLog
from search import Criteria, search, hits_to_rows, delete_hits, base_station_call, station_call_candidates

class SearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.repo=Repository(self.tmp.name)
        self.q=QSO('2026-01-01','00:05','7','CW','JA1YYY','599','599','Japan','Soka Saitama Japan','BURO','')
    def put(self,own='JH1HST',qs=None):
        p=self.repo.path_for(own,'',self.q.date);p.parent.mkdir(exist_ok=True)
        p.write_bytes(('\ufeff'+'\r\n'.join(q.to_ps() for q in (qs or [self.q]))+'\r\n').encode())
        return p

    def test_station_call_candidates_are_base_calls_from_filenames(self):
        self.put('JH1HST/1');self.put('JH1HST/P');self.put('JJ1VMP')
        self.assertEqual(base_station_call('jh1hst/JD1'),'JH1HST')
        self.assertEqual(station_call_candidates(self.repo,'JH1HST/P'),['JH1HST','JJ1VMP'])

    def test_scope_filters_and_boundaries(self):
        self.put();self.put('JH1HST/1');self.put('JH1HST/P');self.put('JH1HSTA')
        self.assertEqual(len(search(self.repo,Criteria('JH1HST')).hits),1)
        self.assertEqual(len(search(self.repo,Criteria('JH1HST',portable=True)).hits),3)
        self.assertEqual(len(search(self.repo,Criteria('JH1HST/1')).hits),1)
        c=Criteria('JH1HST',call='ja1',remarks='buro',band='7',mode='cw',start='202601010005',end='202601010005')
        self.assertEqual(len(search(self.repo,c).hits),1)
        self.assertFalse(search(self.repo,replace(c,start='202601010006',end='')).hits)
        self.assertFalse(search(self.repo,replace(c,filename='2025')).hits)
        with self.assertRaises(ValueError):search(self.repo,replace(c,start='202602300000'))

    def test_partial_datetime_prefixes_and_qth_filters(self):
        q1=replace(self.q,date='2026-01-01',time='00:05',his_qth='Tokyo Japan',my_qth='Soka Saitama Japan')
        q2=replace(self.q,date='2027-01-01',time='00:05',his_qth='Osaka Japan',my_qth='Sendai Miyagi Japan')
        self.put(qs=[q1,q2])
        # Short date/time input is not rewritten in the UI/model.  Start uses
        # the beginning of the selected period and end uses its final moment.
        c=Criteria('JH1HST',start='2026')
        c.validate();self.assertEqual(c.start,'2026')
        self.assertEqual(len(search(self.repo,c).hits),2)
        self.assertEqual(len(search(self.repo,Criteria('JH1HST',start='2027')).hits),1)
        # A partial END includes the whole selected period.
        self.assertEqual(len(search(self.repo,Criteria('JH1HST',end='2027')).hits),2)
        self.assertEqual(len(search(self.repo,Criteria('JH1HST',his_qth='tokyo')).hits),1)
        self.assertEqual(len(search(self.repo,Criteria('JH1HST',my_qth='sendai')).hits),1)
        with self.assertRaises(ValueError):Criteria('JH1HST',start='20260A').validate()


    def test_end_prefix_means_end_of_day_or_hour(self):
        q1=replace(self.q,date='2026-09-17',time='00:00',call='JA1AAA')
        q2=replace(self.q,date='2026-09-17',time='15:59',call='JA1BBB')
        q3=replace(self.q,date='2026-09-17',time='23:59',call='JA1CCC')
        q4=replace(self.q,date='2026-09-18',time='00:00',call='JA1DDD')
        self.put(qs=[q1,q2,q3,q4])
        day=search(self.repo,Criteria('JH1HST',start='20260917',end='20260917')).hits
        self.assertEqual({h.qso.call for h in day},{'JA1AAA','JA1BBB','JA1CCC'})
        hour=search(self.repo,Criteria('JH1HST',start='2026091715',end='2026091715')).hits
        self.assertEqual([h.qso.call for h in hour],['JA1BBB'])

    def test_no_cap(self):
        self.put(qs=[self.q]*2501)
        self.assertEqual(len(search(self.repo,Criteria('JH1HST')).hits),2501)
    def test_exact_search_hits_convert_to_export_rows(self):
        q1=replace(self.q,time='00:06',call='JA1AAA',remarks='POTA')
        q2=replace(self.q,time='00:07',call='JA1BBB',remarks='OTHER')
        self.put(qs=[q1,q2])
        result=search(self.repo,Criteria('JH1HST',remarks='POTA'))
        sessions,rows=hits_to_rows(result.hits)
        self.assertEqual(len(sessions),1);self.assertEqual(len(rows),1)
        self.assertEqual(rows[0][1].call,'JA1AAA');self.assertEqual(rows[0][1].remarks,'POTA')
    def test_exact_duplicate_row_identity_and_stale_selection(self):
        p=self.put(qs=[self.q,replace(self.q,remarks='CARD')])
        hits=search(self.repo,Criteria('JH1HST')).hits
        card=next(h for h in hits if h.qso.remarks=='CARD')
        card.apply(replace(card.qso,remarks='CARD.R'))
        records=self.repo.open(p).log.records
        self.assertEqual([q.remarks for _,q in records],['BURO','CARD.R'])
        with self.assertRaises(ExternalChange):hits[1].apply()
        self.assertEqual(len(self.repo.open(p).log.records),2)
        self.assertTrue(self.repo.backups(p))

    def test_checked_batch_delete_preserves_unchecked_and_backs_up(self):
        q1=replace(self.q,time='00:01',call='JA1AAA')
        q2=replace(self.q,time='00:02',call='JA1BBB')
        q3=replace(self.q,time='00:03',call='JA1CCC')
        p=self.put(qs=[q1,q2,q3])
        hits=search(self.repo,Criteria('JH1HST')).hits
        chosen=[h for h in hits if h.qso.call in {'JA1AAA','JA1CCC'}]
        self.assertEqual(delete_hits(self.repo,chosen),2)
        remaining=[q.call for _,q in self.repo.open(p).log.records]
        self.assertEqual(remaining,['JA1BBB'])
        self.assertTrue(self.repo.backups(p))

    def test_checked_batch_delete_rejects_stale_search(self):
        p=self.put(qs=[self.q,replace(self.q,time='00:06',call='JA1ZZZ')])
        hits=search(self.repo,Criteria('JH1HST')).hits
        p.write_bytes(p.read_bytes()+b'\r\n')
        with self.assertRaises(ExternalChange):delete_hits(self.repo,hits)
        self.assertEqual(len(self.repo.open(p).log.records),2)

    def test_external_change_and_problem_file_block(self):
        p=self.put();hit=search(self.repo,Criteria('JH1HST')).hits[0]
        raw=p.read_bytes()+b'invalid\r\n';p.write_bytes(raw)
        with self.assertRaises(ExternalChange):hit.apply()
        result=search(self.repo,Criteria('JH1HST'))
        self.assertTrue(result.problems);self.assertFalse(result.hits[0].editable)
        with self.assertRaises(InvalidLog):result.hits[0].apply()
        self.assertEqual(p.read_bytes(),raw)
