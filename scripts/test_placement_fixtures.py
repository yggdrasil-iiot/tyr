"""forseti step 5 placement fixtures: the two Line2 workspaces under a different site id, so that Kafka's default
partitioner (murmur2 of the UTF-8 device path, positive, mod 6) puts the five devices on the raw partitions a placement
needs. Each variant changes only the site node (id, label, its plant-register line) and is published under its own stream
and submission id; the bundles are Tyr builds, checked byte for byte, by Tyr's receiver and by Bifrost's jar."""
import base64,copy,hashlib,json,tempfile,unittest
from pathlib import Path
import test_attribution_rule as base
from test_attribution_rule import R,FIX,SETS,JAR,load,publish,tree,approved,java,OCC,INC,RULE,IMPACT
import server,publication
PLACEMENT=FIX/'placement'
BASE_SITE,BASE_LABEL='synthetic-site','Synthetic site'
# variant -> (base workspace, site id, site label, stream, submission id)
VARIANTS={
 'dedicated':('workspace.json','site-071','Placement site 071 (dedicated)','line2-dedicated','attribution-dedicated-fixture'),
 'dedicated-plc':('plc-stamped-workspace.json','site-071','Placement site 071 (dedicated)','line2-dedicated-plc','attribution-plc-stamped-dedicated-fixture'),
 'shared':('workspace.json','site-019','Placement site 019 (shared)','line2-shared','attribution-shared-fixture'),
 'shared-plc':('plc-stamped-workspace.json','site-019','Placement site 019 (shared)','line2-shared-plc','attribution-plc-stamped-shared-fixture'),
}
DEVICES=('line2:station1','line2:station1:nutrunner1','line2:station1:nutrunner2','line2:station2','line2:station3')
def placed(state,site,label):
 """The base workspace with the site id and label replaced: every equipment path is re-rooted, the plant register's CSV
 bytes are rewritten line for line and re-digested. Nothing else changes."""
 def walk(v):
  if isinstance(v,dict):return {k:walk(x) for k,x in v.items()}
  if isinstance(v,list):return [walk(x) for x in v]
  if v==BASE_SITE:return site
  if v==BASE_LABEL:return label
  if isinstance(v,str) and v.startswith(BASE_SITE+':'):return site+v[len(BASE_SITE):]
  return v
 out=walk(copy.deepcopy(state))
 for e in out['hierarchyEvidence']:
  rows=base64.b64decode(e['bytesBase64']).decode('utf-8').split('\n')
  rows=[','.join(site if c==BASE_SITE else label if c==BASE_LABEL else c for c in r.split(',')) for r in rows]
  raw='\n'.join(rows).encode('utf-8');e['bytesBase64']=base64.b64encode(raw).decode('ascii');e['sha256']=hashlib.sha256(raw).hexdigest()
 return out
def dumps(state):return (json.dumps(state,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def expected_workspace(name):
 src,site,label,_,_=VARIANTS[name];return dumps(placed(json.loads((FIX/src).read_bytes()),site,label))
def murmur2(data):
 """Kafka's org.apache.kafka.common.utils.Utils.murmur2 (seed 0x9747b28c), as an unsigned 32-bit value."""
 m,h=0x5bd1e995,(0x9747b28c^len(data))&0xffffffff;n=len(data)//4*4
 for i in range(0,n,4):
  k=int.from_bytes(data[i:i+4],'little');k=k*m&0xffffffff;k^=k>>24;k=k*m&0xffffffff;h=(h*m&0xffffffff)^k
 rest=data[n:]
 if len(rest)==3:h^=rest[2]<<16
 if len(rest)>=2:h^=rest[1]<<8
 if rest:h^=rest[0];h=h*m&0xffffffff
 h^=h>>13;h=h*m&0xffffffff;h^=h>>15;return h
def partition(key,n=6):return (murmur2(key.encode('utf-8'))&0x7fffffff)%n   # Utils.toPositive(murmur2(key)) % numPartitions
def device_paths(bundle):
 """Every equipment path of the published hierarchy: equipmentInstanceIds from the root, joined by ':'."""
 nodes=load(bundle/'hierarchy/0.json')['nodes'];parent={n['equipmentInstanceId']:n['parentEquipmentInstanceId'] for n in nodes}
 def path(i):return i if parent[i] is None else path(parent[i])+':'+i
 return {i:path(i) for i in parent}
def placement(bundle):
 paths=device_paths(bundle);site=next(i for i,p in paths.items() if ':' not in p)
 return {d:partition(site+':'+d) for d in DEVICES},paths
class Placement(unittest.TestCase):
 def test_kafka_murmur2_matches_known_values(self):
  # Kafka's own UtilsTest.testMurmur2 cases
  for key,value in ((b'21',-973932308),(b'foobar',-790332482),(b'a-little-bit-long-string',-985981536),(b'a-little-bit-longer-string',-1486304829),(b'lkjh234lh9fiuh90y23oiuhsafujhadof229phr9h19h89h8',-58897971),(b'abc',479470107)):
   self.assertEqual(murmur2(key),value&0xffffffff,key)
 def test_base_workspaces_keep_the_smoke_placement(self):
  self.assertEqual([partition('synthetic-site:'+d) for d in DEVICES],[4,1,5,2,1])
 def test_dedicated_puts_every_device_on_its_own_partition(self):
  for name in ('dedicated','dedicated-plc'):
   p,paths=placement(PLACEMENT/name/'bundle');parts=set(p.values())
   self.assertEqual([p[d] for d in DEVICES],[5,1,3,4,2],name)
   self.assertEqual(len(parts),5,name);self.assertEqual(len({x%5 for x in parts}),5,name)
   self.assertTrue(all(paths[d.split(':')[-1]]==VARIANTS[name][1]+':'+d for d in DEVICES),name)
 def test_shared_puts_station2_and_station3_on_one_partition(self):
  for name in ('shared','shared-plc'):
   p,paths=placement(PLACEMENT/name/'bundle');parts=set(p.values())
   self.assertEqual([p[d] for d in DEVICES],[2,3,5,0,0],name)
   self.assertEqual(p['line2:station2'],p['line2:station3'],name)
   self.assertNotIn(p['line2:station3'],[p[d] for d in DEVICES[:3]],name)
   self.assertEqual(len(parts),4,name);self.assertEqual(len({x%4 for x in parts}),4,name)
   self.assertTrue(all(paths[d.split(':')[-1]]==VARIANTS[name][1]+':'+d for d in DEVICES),name)
class Fixtures(unittest.TestCase):
 def test_workspace_is_the_base_workspace_with_only_the_site_changed(self):
  for name in VARIANTS:
   committed=(PLACEMENT/name/'workspace.json').read_bytes();self.assertEqual(committed,expected_workspace(name),name)
   self.assertNotIn(BASE_SITE.encode(),committed,name)
   ev=json.loads(committed)['hierarchyEvidence'][0];self.assertEqual(hashlib.sha256(base64.b64decode(ev['bytesBase64'])).hexdigest(),ev['sha256'],name)
 def test_fixture_bundle_is_the_build_of_the_fixture_workspace(self):
  for name,(src,_,_,stream,id) in VARIANTS.items():
   with self.subTest(name),tempfile.TemporaryDirectory() as t:
    p,findings=publish(load(PLACEMENT/name/'workspace.json'),Path(t)/'b',stream=stream,id=id);self.assertEqual(findings,[],name)
    self.assertEqual(tree(Path(t)/'b'),tree(PLACEMENT/name/'bundle'),name)
    self.assertEqual(len(tree(PLACEMENT/name/'bundle')),len(tree(FIX/('bundle' if src=='workspace.json' else 'plc-stamped-bundle'))),name)
 def test_tyr_receiver_validates_the_bundle(self):
  for name in VARIANTS:self.assertEqual(server.v2.p3.validate_package(PLACEMENT/name/'bundle')[0],[],name)
 def test_bundles_carry_forsetis_schema_digests_topic_and_streams(self):
  for name,(_,site,_,stream,id) in VARIANTS.items():
   b=PLACEMENT/name/'bundle';occ,inc=load(b/OCC),load(b/INC)
   self.assertEqual(occ['format']['schemaSha256'],'e97cd7c97b1ab5e2d63d5b06e6057415945b82cff6d2ca0345106d2daf9d29dc',name)
   self.assertEqual((inc['format']['schemaSha256'],inc['topic']),('7141c3115d90812f16b22049c66bfaa64942ebacf854b343fb99b3dce168fb34','quality.incidents'),name)
   s=load(b/'submission.json');self.assertEqual((s['streamId'],s['id']),(stream,id),name)
   self.assertEqual(load(b/RULE)['stations'],[site+':line2:station'+n for n in '123'],name)
   self.assertEqual(load(b/IMPACT)['incidentScope'],[site+':line2:station1:nutrunner'+n for n in '12'],name)
 def test_only_the_site_files_differ_from_the_base_bundle(self):
  for name,(src,*_) in VARIANTS.items():
   old,new=tree(FIX/('bundle' if src=='workspace.json' else 'plc-stamped-bundle')),tree(PLACEMENT/name/'bundle')
   self.assertEqual(sorted(k for k in old if old[k]!=new[k]),sorted(['attribution-rules/0.json','data/hierarchy-0.csv','evidence/hierarchy-0.json','hierarchy/0.json','impact-rules/0.json','proposal.json','submission.json']),name)
class Bifrost(unittest.TestCase):
 def test_bifrost_receiver_validates_the_bundle(self):
  for name in VARIANTS:
   with self.subTest(name),tempfile.TemporaryDirectory() as t:
    v=publication.Adapter(JAR,Path(t)/'registry').call('validate',PLACEMENT/name/'bundle');self.assertTrue(v['accepted'],v);self.assertEqual(v['findings'],[],name)
 def test_bifrost_approves_the_bundle(self):
  for name,(_,_,_,stream,_) in VARIANTS.items():
   with self.subTest(name),tempfile.TemporaryDirectory() as t:
    reg,receipt=approved(PLACEMENT/name/'bundle',Path(t),stream)
    self.assertEqual(receipt.get('kind'),'mapping-approval',receipt);self.assertEqual((receipt['payload']['streamId'],receipt['payload']['execution']),(stream,'excluded'))
 def test_one_registry_publishes_the_six_bundles(self):
  """The two existing streams and the four placement streams side by side: approve and publish each under its stream."""
  bundles=[(FIX/'bundle','line2'),(FIX/'plc-stamped-bundle','line2-plc')]+[(PLACEMENT/n/'bundle',v[3]) for n,v in VARIANTS.items()]
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);reg=t/'registry';keys=t/'keys';(reg/'identity').mkdir(parents=True)
   lines=[java('identity','keygen',who,'--out',keys) for who in ('proposer','approver')]
   (reg/'identity/authorized-keys.jsonl').write_text(''.join(json.dumps(v)+'\n' for v in lines),encoding='utf-8')
   rules=[r for _,s in bundles for r in ({'id':'p-'+s,'principal':'proposer','action':'publish','target':'mapping-publication','kind':'mapping-release','ref':s},{'id':'a-'+s,'principal':'approver','action':'approve','target':'mapping-publication','kind':'mapping-release','ref':s})]
   (reg/'identity/activation-policy.json').write_text(json.dumps({'version':'1.0.0','default':'deny','rules':rules}),encoding='utf-8')
   for b,s in bundles:
    with self.subTest(s):
     a=java('mapping','approve',reg,b,'approval-'+s,'--by','proposer','--by-key',keys/'proposer.key','--approved-by','approver','--approved-by-key',keys/'approver.key')
     self.assertEqual(a.get('kind'),'mapping-approval',a)
     p=java('mapping','publish',reg,b,s,'1.0.0','--approval','approval-'+s);self.assertNotIn('error',p,p)
     self.assertEqual(java('mapping','status',reg,s)['release']['streamId'],s)
   self.assertTrue(java('mapping','catalog',reg)['compatible'])
if __name__=='__main__':unittest.main()
