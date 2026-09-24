import io,json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from copy import deepcopy
from contest_rules import RuleStore,default_rule,score,loads,dumps
import rule_pack as p
from storage import StorageError

class PackTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.store=RuleStore(self.root);self.n=0
    def pack(self,r,revision=1):
        self.n+=1;path=self.root/f'p{self.n}.zip';p.build(path,[(r,revision,'1.01')],'test');return path
    def test_add_update_conflict_and_old_year(self):
        r=default_rule();plan=p.preview(self.store,self.pack(r));self.assertEqual(plan.items[0].status,'追加');self.assertEqual(p.install(self.store,plan),1)
        r['points']['cw']=3;plan=p.preview(self.store,self.pack(r,2));self.assertEqual(plan.items[0].status,'更新');p.install(self.store,plan)
        target=self.store.files()[0];edited,snap=self.store.read(target);edited['name']='my edit';self.store.save(edited,target,snap)
        r['name']='publisher';plan=p.preview(self.store,self.pack(r,3));self.assertEqual(plan.items[0].status,'競合');self.assertEqual(p.install(self.store,plan),0);self.assertEqual(self.store.read(target)[0]['name'],'my edit')
        self.assertEqual(p.install(self.store,plan,[target.name]),1);self.assertEqual(self.store.read(target)[0]['name'],'publisher')
        old=deepcopy(r);old['year']=2025;p.install(self.store,p.preview(self.store,self.pack(old)));self.assertEqual(len(self.store.files()),2)
        self.assertTrue(list((self.store.folder/'history').rglob('*.txt')))
        self.assertIn('publisher',(self.store.folder/'CATALOG.md').read_text(encoding='utf-8'))
    def test_unchanged_and_downgrade(self):
        r=default_rule();p.install(self.store,p.preview(self.store,self.pack(r,4)))
        plan=p.preview(self.store,self.pack(r,4));self.assertEqual(plan.items[0].status,'変更なし');self.assertEqual(p.install(self.store,plan),0)
        r['name']='older';self.assertEqual(p.preview(self.store,self.pack(r,3)).items[0].status,'競合')
    def test_external_change_after_preview_is_not_overwritten(self):
        r=default_rule();p.install(self.store,p.preview(self.store,self.pack(r)))
        r['name']='new';plan=p.preview(self.store,self.pack(r,2));target=self.store.files()[0];target.write_bytes(target.read_bytes()+b' ')
        with self.assertRaises(StorageError):p.install(self.store,plan)
        self.assertNotEqual(self.store.read(target)[0]['name'],'new')
    def test_interrupted_install_recovers_all_before_listing(self):
        a=default_rule();b=deepcopy(a);b['id']='other';path=self.root/'both.zip';p.build(path,[(a,1,'1.01'),(b,1,'1.01')],'both');plan=p.preview(self.store,path)
        original=p.replace_bytes
        def failing(path,data,expected):
            if path.name=='other_2026.txt':raise OSError('simulated power loss')
            return original(path,data,expected)
        with patch.object(p,'replace_bytes',side_effect=failing):
            with self.assertRaises(OSError):p.install(self.store,plan)
        self.assertTrue((self.store.folder/p.JOURNAL).exists())
        self.assertEqual(len(self.store.files()),2);self.assertFalse((self.store.folder/p.JOURNAL).exists())
    def test_recovery_refuses_external_changes(self):
        r=default_rule();plan=p.preview(self.store,self.pack(r));original=p.replace_bytes
        def failing(path,data,expected):
            if path.name==p.STATE:raise OSError('loss')
            return original(path,data,expected)
        with patch.object(p,'replace_bytes',side_effect=failing):
            with self.assertRaises(OSError):p.install(self.store,plan)
        target=self.store.folder/'new-rule_2026.txt';target.write_bytes(b'user data')
        with self.assertRaises(StorageError):self.store.files()
        self.assertEqual(target.read_bytes(),b'user data')
    def test_compact_patch_version_is_accepted_and_ordered_as_decimal(self):
        self.assertEqual(p.version('1.04'), p.version('1.040'))
        self.assertGreater(p.version('1.041'), p.version('1.04'))
        self.assertGreater(p.version('1.05'), p.version('1.049'))
        self.assertGreater(p.version('1.051'), p.version('1.05'))
        self.assertGreater(p.version('1.052'), p.version('1.051'))
        self.assertGreater(p.version('1.055'), p.version('1.054'))
        with self.assertRaises(ValueError):p.version('1.4')
    def test_zip_traversal_hash_and_minimum_version_rejected(self):
        bad=self.root/'bad.zip'
        with zipfile.ZipFile(bad,'w') as z:z.writestr('../escape.txt','bad')
        with self.assertRaises(ValueError):p.preview(self.store,bad)
        self.assertFalse((self.root/'escape.txt').exists())
        valid=self.pack(default_rule())
        with zipfile.ZipFile(valid) as z:data={n:z.read(n) for n in z.namelist()}
        data['rules/new-rule_2026.txt']+=b' '
        with zipfile.ZipFile(bad,'w') as z:
            for n,b in data.items():z.writestr(n,b)
        with self.assertRaisesRegex(ValueError,'ハッシュ'):p.preview(self.store,bad)
        with self.assertRaisesRegex(ValueError,'以降'):p.build(self.root/'future.zip',[(default_rule(),1,'9.99')],'future')

class ScoringTests(unittest.TestCase):
    def rule(self):
        r=default_rule();r['schema']=2;r['multi1']['kind']='off'
        r['scoring']={'eligible':{'all':[]},'multipliers':[dict(id='number',source='exchange',kind='whole',start=0,length=1,per_band=True,when={'all':[]}),dict(id='country',source='country',kind='whole',start=0,length=1,per_band=True,when={'all':[]})],'bonus':0}
        return r
    def entry(self,**kw):return dict(dict(call='JA1AAA',band='7',mode='CW',exchange='25',country='Japan'),**kw)
    def test_zero_points_multis_add_and_dupe(self):
        r=self.rule();r['points']['cw']=0;s=score(r,[self.entry(),self.entry()]);self.assertEqual(s.multi1,2);self.assertEqual(s.multiplier_counts,{'number':1,'country':1});self.assertEqual(s.total,0)
        r['points']['cw']=3;s=score(r,[self.entry(),self.entry(call='JA2BBB',exchange='26')]);self.assertEqual(s.total,18)
    def test_excluded_does_not_block_later_qso_and_bonus_after_factor(self):
        r=self.rule();r['scoring']['eligible']={'field':'exchange','op':'ne','value':'bad'};r['multi2'].update(kind='fixed',value=2);r['scoring']['bonus']=1000
        s=score(r,[self.entry(exchange='bad'),self.entry()]);self.assertEqual(s.total,1004);self.assertEqual(s.rows[0]['reason'],'対象外')
    def test_independent_multiplier_eligibility_and_missing(self):
        r=self.rule();r['scoring']['multipliers'][1]['when']={'field':'exchange','op':'ne','value':'MM'}
        self.assertEqual(score(r,[self.entry(exchange='MM',country=None)]).total,1)
        self.assertIsNone(score(r,[self.entry(country=None)]).total)
    def test_legacy_and_strict_roundtrip(self):
        old=default_rule();self.assertEqual(loads(dumps(old)),old);self.assertEqual(score(old,[self.entry()]).total,1)
        r=self.rule();self.assertEqual(loads(dumps(r)),r);r['scoring']['multipliers'][1]['id']='number'
        with self.assertRaises(ValueError):loads(dumps(r))
    def test_scope_and_second_zero(self):
        r=self.rule();r['multi2'].update(kind='fixed',value=0);self.assertEqual(score(r,[self.entry()]).total,0)
        r['multi2']['kind']='off'
        for m in r['scoring']['multipliers']:m['per_band']=False
        self.assertEqual(score(r,[self.entry(),self.entry(band='14')]).total,4)
        r['formula']='band_sum'
        with self.assertRaises(ValueError):score(r,[self.entry()])
if __name__=='__main__':unittest.main()
