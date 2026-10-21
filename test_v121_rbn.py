import copy,json,tempfile,unittest
from pathlib import Path
from storage import Repository
from rbn_settings import RbnSettings,DEFAULT_NODES,validate,PROFILES
class Rbn121Tests(unittest.TestCase):
 def test_upstream_has_no_cluster_commands(self):
  n=DEFAULT_NODES[2];self.assertEqual((n['host'],n['port']),('telnet.reversebeacon.net',7000));self.assertEqual(PROFILES[n['profile']],[])
 def test_untouched_shanghai_migrates_preserving_disabled(self):
  with tempfile.TemporaryDirectory() as tmp:
   repo=Repository(tmp);p=Path(tmp)/'config/rbn.json';p.parent.mkdir();data={'own':'JX1XXX','nodes':copy.deepcopy(DEFAULT_NODES)};data['nodes'][2].update(name='中国（上海） BH4HKZ',host='spots.bh4hkz.com',port=7373,profile='AR-Cluster',enabled=False);raw=json.dumps(data);p.write_text(raw)
   s=RbnSettings(repo);self.assertEqual(s.data['nodes'][2]['host'],'telnet.reversebeacon.net');self.assertFalse(s.data['nodes'][2]['enabled']);self.assertEqual(p.read_text(),raw)
 def test_custom_c_is_preserved(self):
  with tempfile.TemporaryDirectory() as tmp:
   repo=Repository(tmp);p=Path(tmp)/'config/rbn.json';p.parent.mkdir();data={'own':'JX1XXX','nodes':copy.deepcopy(DEFAULT_NODES)};data['nodes'][2].update(name='自分用',host='spots.bh4hkz.com',port=7373,profile='AR-Cluster');p.write_text(json.dumps(data));self.assertEqual(RbnSettings(repo).data['nodes'][2],data['nodes'][2])
 def test_loaded_upstream_cannot_send_cluster_filter_commands(self):
  data={'own':'JX1XXX','nodes':copy.deepcopy(DEFAULT_NODES)};data['nodes'][2]['profile']='AR-Cluster';self.assertEqual(validate(data)['nodes'][2]['profile'],'設定なし')
if __name__=='__main__':unittest.main()
