"""2.23 equipment hierarchy: authoring acceptance, refusals, publication closure, 2.22 behaviour unchanged."""
import sys,copy,json,tempfile,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'backend'),str(R/'scripts')]
import server,publication,equipment_hierarchy as eh
BUNDLE=R/'fixtures/equipment-hierarchy/bundle'
# Bifrost's copy (core/src/test/resources), run by its MappingEquipmentHierarchyTest.
BIFROST_COPY=R.parent/'bifrost/core/src/test/resources/mapping-fixtures/equipment-hierarchy'
JAR=R.parent/'bifrost/gates/target/bifrost-gates.jar'
def load(p):return server.contracts.load(R/p)
def base():return load('fixtures/broadcast/workspace.json')
def w():
 state=base();state['equipment'].insert(0,{"id":"synthetic-site","label":"Synthetic site"})
 state['equipmentHierarchies']=[load('fixtures/equipment-hierarchy/hierarchy.json')];state['hierarchyEvidence']=load('fixtures/equipment-hierarchy/evidence.json');return state
def mutated(f):
 state=w();f(state['equipmentHierarchies'][0]);return state
def record_id(state):
 r=state['recordMappings'][-1];return 'record:'+r['id']+'@'+r['version']
def package(state,folder):
 server.build_package(state,folder);return load(folder/'proposal.json')
def publish(state,folder):
 _,_,findings=publication.build(state,folder,'hierarchy-sub','hierarchy-stream','proposer',None,[record_id(state)],False,server.build_package)
 return load(folder/'proposal.json'),findings
class EquipmentHierarchy(unittest.TestCase):
 def refused(self,state,code):self.assertRaisesRegex(ValueError,code,server.check_state,state)
 def test_accepted_and_packaged_at_2_23(self):
  state=w();server.check_state(state);self.assertEqual(server.findings_for(state),[])
  with tempfile.TemporaryDirectory() as t:
   p=package(state,Path(t));self.assertEqual(p['schemaVersion'],'2.23.0')
   self.assertEqual([e['path'] for e in p['files'] if e['kind']==eh.KIND],['hierarchy/0.json'])
   self.assertEqual(server.v2.p3.validate_package(Path(t))[0],[])
 def test_publication_always_carries_hierarchy_and_node_evidence(self):
  with tempfile.TemporaryDirectory() as t:
   p,findings=publish(w(),Path(t)/'b');self.assertEqual(findings,[]);self.assertEqual(p['schemaVersion'],'2.23.0')
   kinds={(e['kind'],e['id']) for e in p['files']}
   self.assertIn((eh.KIND,'synthetic-plant'),kinds);self.assertIn(('evidence-artifact','manual-mixed-plc-pressure'),kinds)
 def test_without_hierarchy_2_22_unchanged(self):
  state=base();self.assertEqual(server.findings_for(state),[])
  with tempfile.TemporaryDirectory() as t:
   self.assertEqual(package(state,Path(t))['schemaVersion'],'2.22.0')
   p,_=publish(state,Path(t)/'b');self.assertEqual(p['schemaVersion'],'2.22.0');self.assertFalse(any(e['kind']==eh.KIND for e in p['files']))
 def test_parent_missing(self):self.refused(mutated(lambda h:h['nodes'][1].update(parentEquipmentInstanceId='record-line-z')),'hierarchy.parent-missing')
 def test_self_parent(self):self.refused(mutated(lambda h:h['nodes'][0].update(parentEquipmentInstanceId='synthetic-site')),'hierarchy.cycle')
 def test_cycle(self):self.refused(mutated(lambda h:h['nodes'][0].update(parentEquipmentInstanceId='record-line-a')),'hierarchy.cycle')
 def test_duplicate_node(self):self.refused(mutated(lambda h:h['nodes'].append(copy.deepcopy(h['nodes'][1]))),'hierarchy.duplicate-node')
 def test_node_outside_workspace_equipment(self):
  self.refused(mutated(lambda h:h['nodes'].append(dict(copy.deepcopy(h['nodes'][1]),equipmentInstanceId='record-line-z'))),'hierarchy.context-equipment')
 def test_unresolved_instance(self):self.refused(mutated(lambda h:h['nodes'].pop()),'hierarchy.unresolved-instance')
 def test_multiple(self):
  state=w();state['equipmentHierarchies'].append(dict(copy.deepcopy(state['equipmentHierarchies'][0]),id='second-plant'));self.refused(state,'hierarchy.multiple')
 def test_other_level_needs_name_and_only_there(self):
  self.refused(mutated(lambda h:h['nodes'][0].update(equipmentLevel='OTHER_14')),'schema')
  self.refused(mutated(lambda h:h['nodes'][0].update(otherLevel='Campus')),'schema')
  server.check_state(mutated(lambda h:h['nodes'][0].update(equipmentLevel='OTHER_14',otherLevel='Campus')))
 def test_published_token_spelling(self):
  server.check_state(mutated(lambda h:h['nodes'][1].update(equipmentLevel='PRODUCTIONUINT_7')))
  self.refused(mutated(lambda h:h['nodes'][1].update(equipmentLevel='PRODUCTIONUNIT_7')),'schema')
 def test_node_evidence_resolves(self):
  self.refused(mutated(lambda h:h['nodes'][2]['evidenceRefs'][0].update(artifactId='manual-missing')),'evidence.missing')
 def test_depth_limit(self):
  chain=lambda n:{'nodes':[{'equipmentInstanceId':'n'+str(i),'parentEquipmentInstanceId':None if i==0 else 'n'+str(i-1)} for i in range(n)]}
  eh.check(chain(eh.MAX_DEPTH));self.assertRaisesRegex(ValueError,'hierarchy.depth',eh.check,chain(eh.MAX_DEPTH+1))
 def test_older_envelope_refused(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);package(w(),root);p=load(root/'proposal.json');p['schemaVersion']='2.22.0';server.contracts.save(root/'proposal.json',p)
   self.assertEqual([e['ruleCode'] for e in server.v2.p3.validate_package(root)[0]],['schema'])
 def test_package_checks_without_workspace(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);package(w(),root);p=load(root/'proposal.json')
   e=next(x for x in p['files'] if x['kind']==eh.KIND);h=load(root/e['path']);h['nodes'].pop()
   server.contracts.save(root/e['path'],h);e['sha256']=server.contracts.hashed(root/e['path']);server.contracts.save(root/'proposal.json',p)
   self.assertIn('hierarchy.unresolved-instance',[x['ruleCode'] for x in server.v2.p3.validate_package(root)[0]])
 def test_fixture_bundle_is_the_build_of_the_fixture_workspace(self):
  with tempfile.TemporaryDirectory() as t:
   state=w();publication.build(state,Path(t)/'b','hierarchy-fixture','hierarchy-line','proposer',None,[record_id(state)],False,server.build_package)
   tree=lambda root:{p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
   self.assertEqual(tree(Path(t)/'b'),tree(BUNDLE))
 def test_bifrost_receiver_accepts_the_same_bundle(self):
  tree=lambda root:{p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
  self.assertEqual(tree(BIFROST_COPY),tree(BUNDLE))
  with tempfile.TemporaryDirectory() as t:
   v=publication.Adapter(JAR,Path(t)/'registry').call('validate',BUNDLE);self.assertTrue(v['accepted'],v)
 def test_2_23_schemas_extend_2_22_only_where_intended(self):
  for kind,changed in (('common',{'$id'}),('mapping-proposal',{'$id','properties'})):
   old,new=(load('contracts/'+v+'/'+kind+'.schema.json') for v in ('2.22.0','2.23.0'))
   self.assertEqual({k for k in old.keys()|new.keys() if old.get(k)!=new.get(k)}-{'$defs'},changed-{'$defs'})
  old,new=(load('contracts/'+v+'/common.schema.json')['$defs'] for v in ('2.22.0','2.23.0'))
  self.assertEqual(new['fileEntry']['properties']['kind']['enum'],old['fileEntry']['properties']['kind']['enum']+[eh.KIND])
  self.assertEqual({k for k in old if old[k]!=new[k]},{'fileEntry'})
import base64,hashlib,hierarchy_authoring as ha,import_files
def record(raw,id='site-note',fmt='text',scope=('synthetic-site',),version='1.0.0'):
 return {'id':id,'version':version,'label':'Reviewer note','format':fmt,'bytesBase64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest(),'origin':'synthetic','capturedAt':'2026-10-31T00:00:00Z','reviewer':'fixture-reviewer','product':None,'scope':list(scope)}
class Authoring(unittest.TestCase):
 """The screen's API: listing, plan, apply under revision CAS. Evidence is a note or a register."""
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.store=server.Store(Path(self.tmp.name)/'db.sqlite3');self.store.migrate(0,{})
  state=base();state['equipment'].insert(0,{"id":"synthetic-site","label":"Synthetic site"});self.store.save(1,state)
 def tearDown(self):self.tmp.cleanup()
 def rev(self):return self.store.read()['revision']
 def plan(self,hierarchy,evidence,revision=None):
  return ha.plan(self.store,{'revision':self.rev() if revision is None else revision,'hierarchy':hierarchy,'evidence':evidence},server.Conflict,server.check_state)[0]
 def apply(self,hierarchy,evidence):
  p=self.plan(hierarchy,evidence);return ha.apply(self.store,{'revision':self.rev(),'hierarchy':hierarchy,'evidence':evidence,'planSha256':p['planSha256']},server.Conflict)
 def fixture(self):return load('fixtures/equipment-hierarchy/hierarchy.json'),load('fixtures/equipment-hierarchy/evidence.json')
 def test_listing_offers_levels_equipment_and_citable_lines(self):
  self.apply(*self.fixture());l=ha.listing(self.store,server.build_package)
  self.assertEqual(l['levels'][7],'PRODUCTIONUINT_7');self.assertIn('synthetic-site',[e['id'] for e in l['equipment']])
  reg=next(a for a in l['artifacts'] if a['artifactId']=='hierarchy-plant-register')
  self.assertEqual(reg['preview']['lines'][1],'synthetic-site,Synthetic site,SITE_1,');self.assertEqual(reg['source'],'hierarchy')
  self.assertTrue(any(a['source']=='manual' for a in l['artifacts']));self.assertEqual(l['evidence'],load('fixtures/equipment-hierarchy/evidence.json'));self.assertEqual(l['findings'],[])
 def test_apply_saves_and_clears(self):
  r=self.apply(*self.fixture());self.assertEqual(r['saved']['workspace']['equipmentHierarchies'][0]['id'],'synthetic-plant')
  r=self.apply(None,[]);self.assertNotIn('equipmentHierarchies',r['saved']['workspace']);self.assertNotIn('hierarchyEvidence',r['saved']['workspace'])
 def test_stale_revision_and_changed_plan(self):
  h,e=self.fixture();p=self.plan(h,e)
  self.assertRaises(server.Conflict,self.plan,h,e,self.rev()-1)
  h2=copy.deepcopy(h);h2['label']='Other'
  self.assertRaisesRegex(ValueError,'hierarchy.plan-changed',ha.apply,self.store,{'revision':self.rev(),'hierarchy':h2,'evidence':e,'planSha256':p['planSha256']},server.Conflict)
 def test_reviewer_note_is_citable_evidence(self):
  h,e=self.fixture();note=record('Reviewer: fixture-reviewer\nsynthetic-site is the site; both lines sit under it.\n'.encode())
  h['nodes'][0]['evidenceRefs']=[{'artifactId':'hierarchy-site-note','locator':{'kind':'text-line','line':2}}]
  self.apply(h,e+[note])
  h['nodes'][0]['evidenceRefs'][0]['locator']['line']=3;self.assertRaisesRegex(ValueError,'evidence.locator',self.plan,h,e+[note])
 def test_register_cells_are_citable(self):
  raw=(R/'fixtures/p4a/memory-map.xlsx').read_bytes();sheet,cell=next(iter(import_files.xlsx(raw)[1]))
  h,e=self.fixture();h['nodes'][0]['evidenceRefs']=[{'artifactId':'hierarchy-site-register','locator':{'kind':'xlsx-cell','sheet':sheet,'cell':cell}}]
  self.apply(h,e+[record(raw,'site-register','xlsx')])
  h['nodes'][0]['evidenceRefs'][0]['locator']['cell']='ZZ999';self.assertRaisesRegex(ValueError,'evidence.locator',self.plan,h,e+[record(raw,'site-register','xlsx')])
 def test_evidence_must_cover_the_node(self):
  h,e=self.fixture();e[0]['scope']=['record-line-a','record-line-b']
  self.assertRaisesRegex(ValueError,'hierarchy.evidence-scope',self.plan,h,e)
  h,e=self.fixture();h['nodes'][0]['evidenceRefs']=[{'artifactId':'manual-mixed-plc-pressure','locator':{'kind':'text-line','line':1}}]
  self.assertRaisesRegex(ValueError,'hierarchy.evidence-scope',self.plan,h,e)
 def test_evidence_record_refusals(self):
  h,e=self.fixture()
  bad=copy.deepcopy(e);bad[0]['sha256']='0'*64;self.assertRaisesRegex(ValueError,'hierarchy-evidence.digest',self.plan,h,bad)
  self.assertRaisesRegex(ValueError,'hierarchy-evidence.encoding',self.plan,h,e+[record(b'\xff\xfe')])
  self.assertRaisesRegex(ValueError,'hierarchy-evidence.xlsx',self.plan,h,e+[record(b'not a workbook','r','xlsx')])
  self.assertRaisesRegex(ValueError,'hierarchy-evidence.scope',self.plan,h,e+[record(b'x','n','text',('record-line-z',))])
  self.assertRaisesRegex(ValueError,'hierarchy-evidence.duplicate',self.plan,h,e+e)
  bad=copy.deepcopy(e);bad[0]['format']='pdf';self.assertRaisesRegex(ValueError,'hierarchy-evidence.schema',self.plan,h,bad)
 def test_cited_evidence_cannot_be_dropped(self):
  h,e=self.fixture();self.apply(h,e);self.assertRaisesRegex(ValueError,'evidence.missing',self.plan,h,[])
 def test_changed_evidence_needs_new_version(self):
  h,e=self.fixture();self.apply(h,e)
  csv=base64.b64decode(e[0]['bytesBase64'])+b'spare-row,Spare,OTHER_14,\n';changed=record(csv,'plant-register','csv',e[0]['scope'])
  self.assertRaisesRegex(ValueError,'hierarchy-evidence.version-required',self.plan,h,[changed])
  self.apply(h,[record(csv,'plant-register','csv',e[0]['scope'],'1.1.0')])
 def test_http_routes(self):
  import threading,urllib.request
  http=server.make_server(self.store,0);threading.Thread(target=http.serve_forever,daemon=True).start()
  try:
   base_url='http://127.0.0.1:'+str(http.server_address[1])
   def call(path,body=None):
    req=urllib.request.Request(base_url+path,data=None if body is None else json.dumps(body).encode(),method='GET' if body is None else 'POST',headers={'Content-Type':'application/json','X-Tyr-Editor':'1','Origin':base_url})
    with urllib.request.urlopen(req) as r:return json.loads(r.read())
   self.assertEqual(call('/api/equipment-hierarchy')['hierarchy'],None)
   h,e=self.fixture();p=call('/api/equipment-hierarchy-plan',{'revision':self.rev(),'hierarchy':h,'evidence':e})
   s=call('/api/equipment-hierarchy-apply',{'revision':self.rev(),'hierarchy':h,'evidence':e,'planSha256':p['planSha256']})
   self.assertEqual(s['saved']['findings'],[]);self.assertEqual(call('/api/equipment-hierarchy')['hierarchy']['id'],'synthetic-plant')
   with urllib.request.urlopen(base_url+'/hierarchy.js') as r:self.assertIn(b'hierarchyView',r.read())
  finally:http.shutdown();http.server_close()
if __name__=='__main__':unittest.main(verbosity=2)
