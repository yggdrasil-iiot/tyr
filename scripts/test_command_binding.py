"""2.25 command binding: imported read bindings kept byte for byte, reconciliation refusals, publication closure, Bifrost seam."""
import sys,copy,json,base64,hashlib,tempfile,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'backend'),str(R/'scripts')]
import server,publication,read_bindings,command_binding as cb,command_binding_authoring as cba
BUNDLE=R/'fixtures/command-binding/bundle'
# Bifrost's copy (core/src/test/resources), run by its MappingTyrCommandBindingTest.
BIFROST_COPY=R.parent/'bifrost/core/src/test/resources/mapping-fixtures/command-binding'
# The profile the read bindings were imported from: Bifrost's vor-read fixture, as Vor's fixture release carries it.
BIFROST_PROFILE=R.parent/'bifrost/core/src/test/resources/mapping-fixtures/vor-read/data/vor-read-binding.json'
JAR=R.parent/'bifrost/gates/target/bifrost-gates.jar'
def load(p):return server.contracts.load(R/p)
def w():return load('fixtures/command-binding/workspace.json')
def profile(state,n=0):return json.loads(base64.b64decode(state['readBindings'][n]['bytesBase64']))
def imported(state,n,raw):
 state['readBindings'][n].update(bytesBase64=base64.b64encode(raw).decode(),sha256=hashlib.sha256(raw).hexdigest());return state
def reprofiled(f,n=0):
 state=w();b=profile(state,n);f(b);return imported(state,n,json.dumps(b,indent=2).encode())
def relinked(f,n=0):
 state=w();f(state['commandBindings'][n]);return state
def package(state,folder):
 server.build_package(state,folder);return load(folder/'proposal.json')
def publish(state,folder,sets=('mixer1-mapping','mixer2-mapping'),stream='line1'):
 _,_,findings=publication.build(state,folder,'command-binding-fixture',stream,'proposer',None,list(sets),False,server.build_package)
 return load(folder/'proposal.json'),findings
def tree(root):return {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
class CommandBinding(unittest.TestCase):
 def refused(self,state,code):self.assertRaisesRegex(ValueError,code,server.check_state,state)
 def test_accepted_and_packaged_at_2_25(self):
  state=w();server.check_state(state);self.assertEqual(server.findings_for(state),[])
  with tempfile.TemporaryDirectory() as t:
   p=package(state,Path(t));self.assertEqual(p['schemaVersion'],'2.25.0')
   self.assertEqual([e['path'] for e in p['files'] if e['kind']==cb.KIND],['command-bindings/0.json','command-bindings/1.json'])
   self.assertEqual(server.v2.p3.validate_package(Path(t))[0],[])
 def test_imported_bytes_are_packaged_unchanged(self):
  raw=BIFROST_PROFILE.read_bytes();self.assertEqual(w()['readBindings'][0]['sha256'],hashlib.sha256(raw).hexdigest())
  # tabs and no final newline: a re-serializing writer would change the digest Vor and Bifrost pin
  odd=json.dumps(json.loads(raw),indent='\t').encode()
  state=imported(w(),0,odd);server.check_state(state)
  with tempfile.TemporaryDirectory() as t:
   p=package(state,Path(t));art=next(load(Path(t)/e['path']) for e in p['files'] if e['id']=='read-binding-mixer1-temp')
   self.assertEqual((Path(t)/art['file']['path']).read_bytes(),odd);self.assertEqual(art['file']['sha256'],hashlib.sha256(odd).hexdigest())
   self.assertEqual((art['scope'],art['file']['mediaType']),(['mixer1'],'application/json'))
 def test_a_profile_for_another_stream_is_refused_at_export_and_left_as_imported(self):
  state=w();before=copy.deepcopy(state['readBindings'])
  with tempfile.TemporaryDirectory() as t:
   self.assertRaisesRegex(ValueError,'read-binding.stream',publish,state,Path(t)/'b',stream='line2')
   self.assertFalse((Path(t)/'b').exists())
  self.assertEqual(state['readBindings'],before)
 def test_publication_carries_each_link_with_the_mapping_set_its_read_binding_reads(self):
  with tempfile.TemporaryDirectory() as t:
   p,findings=publish(w(),Path(t)/'b',('mixer2-mapping',));self.assertEqual(findings,[]);self.assertEqual(p['schemaVersion'],'2.25.0')
   ids={(e['kind'],e['id']) for e in p['files']}
   self.assertIn((cb.KIND,'mixer2-set-temperature'),ids);self.assertIn(('evidence-artifact','read-binding-mixer2-temp'),ids)
   self.assertNotIn((cb.KIND,'mixer1-set-temperature'),ids);self.assertNotIn(('evidence-artifact','read-binding-mixer1-temp'),ids)
   self.assertTrue((Path(t)/'b/data/read-binding-1.json').is_file())
 def test_without_links_2_23_unchanged(self):
  state=w();del state['commandBindings'],state['readBindings'];self.assertEqual(server.findings_for(state),[])
  with tempfile.TemporaryDirectory() as t:self.assertEqual(package(state,Path(t))['schemaVersion'],'2.23.0')
 # reconciliation: every field Tyr can derive must agree with its own documents
 def test_device_not_the_hierarchy_path(self):self.refused(reprofiled(lambda b:b.update(device='Line1/Mixer1')),'command-binding.device-path')
 def test_mapping_set_of_another_equipment(self):
  self.refused(reprofiled(lambda b:(b['mappingSetRef'].update(id='mixer1-mapping'),b.update(mappingId='temp')),1),'command-binding.device-path')
 def test_mapping_set_not_in_the_package(self):self.refused(reprofiled(lambda b:b['mappingSetRef'].update(version='9.9.9')),'command-binding.unresolved')
 def test_mapping_not_in_the_set(self):self.refused(reprofiled(lambda b:b.update(mappingId='pressure')),'command-binding.unresolved')
 def test_semantic_id(self):self.refused(reprofiled(lambda b:b.update(semanticId='urn:bifrost:sem:Mixer/Pressure')),'read-binding.semantic-id')
 def test_metric(self):self.refused(reprofiled(lambda b:b.update(metric='Pressure')),'read-binding.metric')
 def test_source_node(self):
  state=w();state['sources'][0]['definition']['access']['identifier']='Line1/Mixer1.Temperature';self.refused(state,'read-binding.source-node')
 def test_output_unit(self):
  state=w();state['mappings'][0]['mappings'][0]['outputUnit']={'status':'known','code':'K'};self.refused(state,'read-binding.output-unit')
 def test_unsupported_profile(self):self.refused(reprofiled(lambda b:b.update(projection='scaled')),'read-binding.profile')
 def test_extra_profile_field(self):self.refused(reprofiled(lambda b:b.update(note='x')),'read-binding.profile')
 def test_digest(self):
  state=w();state['readBindings'][0]['sha256']='0'*64;self.refused(state,'read-binding.digest')
 def test_unknown_equipment(self):self.refused(reprofiled(lambda b:b.update(equipmentInstanceId='mixer9')),'read-binding.equipment')
 # the link itself: the checks Bifrost runs at publish
 def test_link_to_another_equipments_read_binding(self):
  self.refused(relinked(lambda c:c['readBindingRef'].update(id='read-binding-mixer1-temp'),1),'command-binding.device-path')
 def test_unknown_read_binding(self):self.refused(relinked(lambda c:c['readBindingRef'].update(version='9.9.9')),'command-binding.unresolved')
 def test_link_to_an_artifact_that_is_not_an_imported_read_binding(self):
  # A valid profile under another evidence id would skip reconciliation scope and the export stream check.
  p=load(BUNDLE/'proposal.json');docs=[load(BUNDLE/e['path']) for e in p['files']]
  for d in docs:
   if d['kind']=='evidence-artifact' and d['id']=='read-binding-mixer1-temp':d['id']='commissioning-mixer1-temp'
   if d['kind']==cb.KIND and d['readBindingRef']['id']=='read-binding-mixer1-temp':d['readBindingRef']['id']='commissioning-mixer1-temp'
  self.assertRaisesRegex(ValueError,'command-binding.unresolved',cb.validate,docs,lambda q:(BUNDLE/q).read_bytes())
  cb.validate([load(BUNDLE/e['path']) for e in p['files']],lambda q:(BUNDLE/q).read_bytes())
 def test_unknown_equipment_node(self):self.refused(relinked(lambda c:c['equipmentRef'].update(equipmentInstanceId='mixer9')),'command-binding.unresolved')
 def test_two_inputs(self):
  self.refused(relinked(lambda c:c['method']['inputs'].append(dict(c['method']['inputs'][0],name='rampRate'))),'command-binding.inputs')
 def test_unit_outside_ucum_list(self):self.refused(relinked(lambda c:c['method']['inputs'][0].update(unit='degC')),'command-binding.inputs')
 def test_second_link_for_one_device_and_method(self):
  def same(c):
   c['equipmentRef']['equipmentInstanceId']='mixer1';c['readBindingRef']['id']='read-binding-mixer1-temp'
   c['method'].update(objectNodeId='nsu=urn:bifrost:opcua:sim;s=Line1/Mixer1',methodNodeId='nsu=urn:bifrost:opcua:sim;s=Line1/Mixer1.SetTemperature')
  self.refused(relinked(same,1),'command-binding.duplicate')
 def test_duplicate_id(self):
  state=w();state['commandBindings'].append(copy.deepcopy(state['commandBindings'][0]));self.refused(state,'command-binding: duplicate id')
 def test_changed_read_binding_needs_a_new_version(self):
  before=w();after=reprofiled(lambda b:b.update(group='Bifrost:Line2'))
  self.assertRaisesRegex(ValueError,'read-binding.version-required',read_bindings.transition,before,after)
  after['readBindings'][0]['version']='1.1.0';read_bindings.transition(before,after)
 def test_package_checks_without_workspace(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);p=package(w(),root)
   e=next(x for x in p['files'] if x['kind']==cb.KIND);c=load(root/e['path']);c['readBindingRef']['id']='read-binding-mixer2-temp'
   server.contracts.save(root/e['path'],c);e['sha256']=server.contracts.hashed(root/e['path']);server.contracts.save(root/'proposal.json',p)
   self.assertIn('command-binding.device-path',[x['ruleCode'] for x in server.v2.p3.validate_package(root)[0]])
 def test_older_envelope_refused(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);package(w(),root);p=load(root/'proposal.json');p['schemaVersion']='2.24.0';server.contracts.save(root/'proposal.json',p)
   self.assertEqual([e['ruleCode'] for e in server.v2.p3.validate_package(root)[0]],['schema'])
 def test_2_25_schemas_extend_2_24_only_where_intended(self):
  old,new=(load('contracts/'+v+'/common.schema.json')['$defs'] for v in ('2.24.0','2.25.0'))
  self.assertEqual(new['fileEntry']['properties']['kind']['enum'],old['fileEntry']['properties']['kind']['enum']+[cb.KIND])
  self.assertEqual({k for k in old if old[k]!=new[k]},{'fileEntry'})
 def test_fixture_bundle_is_the_build_of_the_fixture_workspace(self):
  with tempfile.TemporaryDirectory() as t:
   publish(w(),Path(t)/'b');self.assertEqual(tree(Path(t)/'b'),tree(BUNDLE))
 def test_bifrost_receiver_accepts_the_same_bundle(self):
  self.assertEqual(tree(BIFROST_COPY),tree(BUNDLE))
  with tempfile.TemporaryDirectory() as t:
   v=publication.Adapter(JAR,Path(t)/'registry').call('validate',BUNDLE);self.assertTrue(v['accepted'],v)
class Authoring(unittest.TestCase):
 """The screen's API: the profile text and digest the reviewer approves, reconciliation, plan and apply under revision CAS."""
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.store=server.Store(Path(self.tmp.name)/'db.sqlite3');self.store.migrate(0,{})
  state=w();state.pop('readBindings');state.pop('commandBindings');self.store.save(1,state)
 def tearDown(self):self.tmp.cleanup()
 def rev(self):return self.store.read()['revision']
 def req(self,state,revision=None):return {'revision':self.rev() if revision is None else revision,'readBindings':state.get('readBindings',[]),'commandBindings':state.get('commandBindings',[])}
 def plan(self,state,revision=None):return cba.plan(self.store,self.req(state,revision),server.Conflict,server.check_state)[0]
 def apply(self,state):
  p=self.plan(state);return cba.apply(self.store,{**self.req(state),'planSha256':p['planSha256']},server.Conflict)
 def test_listing_shows_profile_text_digest_and_reconciliation(self):
  self.apply(w());l=cba.listing(self.store,server.build_package);p=l['profiles'][0]
  self.assertEqual(p['text'].encode(),base64.b64decode(w()['readBindings'][0]['bytesBase64']))
  self.assertEqual(p['sha256'],hashlib.sha256(p['text'].encode()).hexdigest());self.assertEqual(p['artifactId'],'read-binding-mixer1-temp')
  self.assertEqual([x['reconciliation'] for x in l['profiles']],['ok','ok']);self.assertEqual(l['hierarchy']['id'],'vor-plant');self.assertIn('mixer2',l['hierarchy']['equipment'])
  self.assertIn('Cel',l['units']);self.assertIn('manual-mixer1-temp',l['citable']);self.assertEqual(l['findings'],[]);self.assertEqual(l['approvalAuthority'],'bifrost')
 def test_plan_refuses_a_profile_that_does_not_reconcile(self):
  self.assertRaisesRegex(ValueError,'command-binding.device-path',self.plan,reprofiled(lambda b:b.update(device='synthetic-site:line1:mixer9')))
 def test_apply_saves_and_clears(self):
  r=self.apply(w());self.assertEqual(r['saved']['workspace']['readBindings'],w()['readBindings']);self.assertEqual(len(r['saved']['workspace']['commandBindings']),2)
  r=self.apply({});self.assertNotIn('readBindings',r['saved']['workspace']);self.assertNotIn('commandBindings',r['saved']['workspace'])
 def test_stale_revision_changed_plan_and_unversioned_change(self):
  p=self.plan(w());self.assertRaises(server.Conflict,self.plan,w(),self.rev()-1)
  other=relinked(lambda c:c['command'].update(edge='other-edge'))
  self.assertRaisesRegex(ValueError,'command-binding.plan-changed',cba.apply,self.store,{**self.req(other),'planSha256':p['planSha256']},server.Conflict)
  self.apply(w());changed=imported(w(),0,base64.b64decode(w()['readBindings'][0]['bytesBase64'])+bytes([10]))
  self.assertRaisesRegex(ValueError,'read-binding.version-required',self.plan,changed)
 def test_http_routes(self):
  import threading,urllib.request
  http=server.make_server(self.store,0);threading.Thread(target=http.serve_forever,daemon=True).start()
  try:
   base_url='http://127.0.0.1:'+str(http.server_address[1])
   def call(path,body=None):
    req=urllib.request.Request(base_url+path,data=None if body is None else json.dumps(body).encode(),method='GET' if body is None else 'POST',headers={'Content-Type':'application/json','X-Tyr-Editor':'1','Origin':base_url})
    with urllib.request.urlopen(req) as r:return json.loads(r.read())
   self.assertEqual(call('/api/command-binding')['profiles'],[])
   p=call('/api/command-binding-plan',self.req(w()));s=call('/api/command-binding-apply',{**self.req(w()),'planSha256':p['planSha256']})
   self.assertEqual(s['saved']['findings'],[]);self.assertEqual([x['reconciliation'] for x in call('/api/command-binding')['profiles']],['ok','ok'])
   with urllib.request.urlopen(base_url+'/command-binding.js') as r:self.assertIn(b'commandBindingView',r.read())
   with urllib.request.urlopen(base_url+'/') as r:self.assertIn(b'data-tab="commandBindings"',r.read())
  finally:http.shutdown();http.server_close()
if __name__=='__main__':unittest.main()
