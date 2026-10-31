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
 state['equipmentHierarchies']=[load('fixtures/equipment-hierarchy/hierarchy.json')];return state
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
if __name__=='__main__':unittest.main(verbosity=2)
