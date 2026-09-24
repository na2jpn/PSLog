import tempfile,unittest
from pathlib import Path
from copy import deepcopy
from PySide6.QtWidgets import QApplication
from contest_rules import loads,score,RuleStore
from contest import select_logs
from contest_export import plan,key
from contest_ui import ContestDialog
from contest_event_ui import EventDialog
from storage import Repository
from model import QSO

def rule():return loads((Path(__file__).parent/'config/rules/all_saga_2026.txt').read_text(encoding='utf-8'))
def ctx(r,cat='XCSM'):
 c=next(c for c in r['event']['categories'] if c['id']==cat)
 return dict(category=cat,power=50,flags={x:True for x in r['event']['required_flags']+c['required_flags']})
def entry(**kw):return dict(dict(date='2026-08-22',time='21:00',call='JA6AAA',band='7',mode='CW',exchange='4101'),**kw)
class SagaTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def test_42_categories_and_town_multipliers(self):
  r=rule();self.assertEqual(len(r['event']['categories']),42)
  s=score(r,[entry(exchange='41003B'),entry(call='JA6BBB',exchange='41003D'),entry(call='JA1ZZZ',exchange='10')],ctx(r));self.assertEqual(s.total,4);self.assertEqual(s.rows[2]['points'],0)
  for c in r['event']['categories']:
   self.assertEqual(score(r,[entry(band=c['bands'][0],mode=c['modes'][0])],ctx(r,c['id'])).total,1)
 def test_inside_region_dictionary_and_exact_limits(self):
  r=rule();codes=r['scoring']['eligible']['value'].split(',');self.assertEqual(len(set(codes)),80)
  rows=[entry(call=f'JA1X{i}',exchange=code) for i,code in enumerate(codes)]
  self.assertEqual(score(r,rows,ctx(r,'KCSM')).total,6400)
  self.assertEqual(score(r,rows,ctx(r)).total,400)
  # No inferred city, prefecture 41, obsolete Hokkaido 01, or foreign number.
  bad=[entry(call=f'JA2X{i}',exchange=code) for i,code in enumerate(['41','01','49','100','115','41003','41003Z','001'])]
  self.assertEqual(score(r,rows+bad,ctx(r,'KCSM')).total,6400)
  self.assertEqual(score(r,[entry(exchange='106'),entry(call='JA8BBB',exchange='106',band='14')],ctx(r,'KCSM')).total,4)
 def test_category_switch_requires_location_confirmation(self):
  r=rule();c=ctx(r);c['category']='KCSM'
  self.assertIsNone(score(r,[entry(exchange='13')],c).total)
 def test_inside_so_mo_export_and_pack_upgrade(self):
  from rule_pack import preview,install
  for cat,mode in [('KCSM','CW'),('KFMM','FM')]:
   with tempfile.TemporaryDirectory() as root:
    r=rule();repo=Repository(root);p=repo.path_for('JA6AAA','','2026-08-22')
    for call,number in [('JA1BBB','10'),('JA6CCC','41003D')]:
     repo.open(p).append(QSO('2026-08-22','21:00','7',mode,call,'599' if mode=='CW' else '59','599' if mode=='CW' else '59','Japan','Saga Japan',number,''))
    original=p.read_bytes();sel=select_logs(repo,[p],'JA6AAA');draft={key(row):dict(sent='4101',received=row[1].remarks,status='確認済み') for row in sel.rows}
    info=dict(contest=r['event']['submission']['contest'],category=cat,name='試験',address='試験',power='50',date='2026-08-24',signature='試験',oath=True,multiop=cat=='KFMM',multioplist='JA6AAA JA6BBB' if cat=='KFMM' else '')
    for fmt in ('JARL R1.0','JARL R2.1'):
     output=plan(sel,r,draft,fmt,info,context=ctx(r,cat)).preview();self.assertIn('<TOTALSCORE>4</TOTALSCORE>',output);self.assertIn('<CATEGORYCODE>'+cat,output)
    self.assertEqual(p.read_bytes(),original)
  with tempfile.TemporaryDirectory() as root:
   store=RuleStore(root);packs=Path(__file__).parent/'distribution/rules'
   install(store,preview(store,packs/'all_saga_outside_2026_r1.zip'))
   upgrade=preview(store,packs/'all_saga_2026_r2.zip');self.assertEqual(upgrade.items[0].status,'更新');install(store,upgrade)
   self.assertEqual(len(store.files()),1);updated,_=store.read(store.files()[0]);self.assertEqual(len(updated['event']['categories']),42)
 def test_mode_and_rest(self):
  r=rule();c=ctx(r,'XFSM');s=score(r,[entry(mode='SSB'),entry(mode='FM',time='21:01'),entry(call='JA6BBB'),entry(call='JA6CCC',date='2026-08-23',time='03:00')],c);self.assertEqual(s.total,1)
 def test_export_and_wizard_recalculate_without_source_mutation(self):
  with tempfile.TemporaryDirectory() as root:
   r=rule();repo=Repository(root);p=repo.path_for('JH1HST','', '2026-08-22');repo.open(p).append(QSO('2026-08-22','21:00','7','CW','JA6AAA','599','599','Saga Japan','Soka Japan','41003B',''))
   raw=p.read_bytes();sel=select_logs(repo,[p],'JH1HST');draft={key(sel.rows[0]):dict(sent='13',received='41003B',status='確認済み')};info=dict(contest=r['event']['submission']['contest'],category='XCSM',name='試験',address='試験住所',power='50',date='2026-08-24',signature='試験',oath=True,zone='JST')
   for fmt in ('JARL R1.0','JARL R2.1'):
    result=plan(sel,r,draft,fmt,info,context=ctx(r));self.assertIn('41003B 41003B 1',result.preview());self.assertIn('<TOTALSCORE>1</TOTALSCORE>',result.preview())
   info['category']='XFSM'
   with self.assertRaises(ValueError):plan(sel,r,draft,'JARL R2.1',info,context=ctx(r))
   path,_=RuleStore(root).save(r);w=ContestDialog(repo,'JH1HST');w.advance();w.check_all(True);w.advance();w.draft=draft;w.rules.setCurrentIndex(1);w.event_contexts[str(path)]=ctx(r);w.calculate();self.assertEqual(w.result.total,1)
   w.stack.setCurrentIndex(3);w.advance();self.assertEqual(w.stack.currentIndex(),4);self.assertEqual(w.submission.fields['category'].text(),'XCSM');w.timer.stop();w.deleteLater()
   d=EventDialog(r['event'],ctx(r));d.apply();self.assertEqual(d.context['power'],50);d.deleteLater();self.assertEqual(p.read_bytes(),raw)
