"""2.24 metric definition: authoring acceptance, refusals, publication closure, 2.23 behaviour unchanged."""
import sys,copy,tempfile,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'backend'),str(R/'scripts')]
import server,publication,metric_definition as md
BUNDLE=R/'fixtures/metric-definition/bundle'
# Bifrost's copy (core/src/test/resources), run by its MappingMetricDefinitionTest.
BIFROST_COPY=R.parent/'bifrost/core/src/test/resources/mapping-fixtures/metric-definition'
def load(p):return server.contracts.load(R/p)
def hierarchy():
 state=load('fixtures/broadcast/workspace.json');state['equipment'].insert(0,{"id":"synthetic-site","label":"Synthetic site"})
 state['equipmentHierarchies']=[load('fixtures/equipment-hierarchy/hierarchy.json')];state['hierarchyEvidence']=load('fixtures/equipment-hierarchy/evidence.json');return state
def w():
 state=hierarchy();state['recordMappings'].append(load('fixtures/metric-definition/record-mapping.json'))
 state['metricDefinitions']=[load('fixtures/metric-definition/metric.json')];return state
def mutated(f):
 state=w();f(state['metricDefinitions'][0]);return state
RECORD='record:availability-samples@1.0.0'
def package(state,folder):
 server.build_package(state,folder);return load(folder/'proposal.json')
def publish(state,folder,records=(RECORD,)):
 _,_,findings=publication.build(state,folder,'metric-sub','metric-line','proposer',None,list(records),False,server.build_package)
 return load(folder/'proposal.json'),findings
def tree(root):return {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
class MetricDefinition(unittest.TestCase):
 def refused(self,state,code):self.assertRaisesRegex(ValueError,code,server.check_state,state)
 def test_accepted_and_packaged_at_2_24(self):
  state=w();server.check_state(state);self.assertEqual(server.findings_for(state),[])
  with tempfile.TemporaryDirectory() as t:
   p=package(state,Path(t));self.assertEqual(p['schemaVersion'],'2.24.0')
   self.assertEqual([e['path'] for e in p['files'] if e['kind']==md.KIND],['metrics/0.json'])
   self.assertEqual(server.v2.p3.validate_package(Path(t))[0],[])
 def test_publication_carries_metric_with_its_dataset(self):
  with tempfile.TemporaryDirectory() as t:
   p,findings=publish(w(),Path(t)/'b');self.assertEqual(findings,[]);self.assertEqual(p['schemaVersion'],'2.24.0')
   kinds={(e['kind'],e['id']) for e in p['files']}
   self.assertIn((md.KIND,'running-availability'),kinds);self.assertIn(('record-mapping','availability-samples'),kinds)
 def test_metric_stays_out_when_its_dataset_is_not_published(self):
  with tempfile.TemporaryDirectory() as t:
   p,findings=publish(w(),Path(t)/'b',('record:broadcast-pumps@1.0.0',));self.assertEqual(findings,[])
   self.assertFalse(any(e['kind']==md.KIND for e in p['files']))
 def test_without_metric_2_23_unchanged(self):
  state=hierarchy();self.assertEqual(server.findings_for(state),[])
  with tempfile.TemporaryDirectory() as t:self.assertEqual(package(state,Path(t))['schemaVersion'],'2.23.0')
 def test_dataset_missing(self):self.refused(mutated(lambda m:m['dataset']['recordMappingRef'].update(id='absent-samples')),'metric.dataset-missing')
 def test_input_missing(self):self.refused(mutated(lambda m:m['inputs'].append('downtime')),'metric.input-missing')
 def test_input_unreferenced(self):self.refused(mutated(lambda m:m['inputs'].append('pressure')),'metric.input-unreferenced')
 def test_input_inside_a_string_literal_is_not_read(self):
  self.refused(mutated(lambda m:(m['inputs'].append('pressure'),m['ossie']['metric']['expression'].update(sql="100.0 * COUNT(*) FILTER (WHERE running) / COUNT(*) || 'pressure'"))),'metric.input-unreferenced')
 def test_grain_not_an_input(self):self.refused(mutated(lambda m:m['inputs'].remove('bucket')),'metric.grain-input')
 def test_grain_key_must_be_a_string_key(self):
  self.refused(mutated(lambda m:m['grain']['groupBy'].append('running')),'metric.grain-key')
 def test_unit_unconfirmed(self):self.refused(mutated(lambda m:m['result'].update(unit={'status':'unknown'})),'metric.unit-unconfirmed')
 def test_duplicate_name(self):
  state=w();state['metricDefinitions'].append(dict(copy.deepcopy(state['metricDefinitions'][0]),id='running-availability-copy'));self.refused(state,'metric.duplicate-name')
 def test_duplicate_id(self):
  state=w();state['metricDefinitions'].append(copy.deepcopy(state['metricDefinitions'][0]));self.refused(state,'duplicate id')
 def test_other_dialects_refused(self):
  self.refused(mutated(lambda m:m['ossie']['metric']['expression'].update(dialects=[{'dialect':'SNOWFLAKE','expression':'x'}])),'metric-definition: schema validation failed')
 def test_custom_extensions_refused(self):
  self.refused(mutated(lambda m:m['ossie']['metric'].update(custom_extensions=[{'vendor_name':'yggdrasil','data':'{}'}])),'metric-definition: schema validation failed')
 def test_other_spec_version_refused(self):self.refused(mutated(lambda m:m['ossie'].update(specVersion='0.1.1')),'metric-definition: schema validation failed')
 def test_percent_is_a_2_24_unit(self):
  self.assertEqual(server.v2.p3.schema_errors(md.KIND,load('fixtures/metric-definition/metric.json')),[])
  r=load('fixtures/metric-definition/record-mapping.json');r['resultSchema']['fields'][2]['unit']={'status':'known','code':'%'}
  self.assertNotEqual(server.v2.p3.schema_errors('record-mapping',r),[])
 def test_older_envelope_refused(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);package(w(),root);p=load(root/'proposal.json');p['schemaVersion']='2.23.0';server.contracts.save(root/'proposal.json',p)
   self.assertEqual([e['ruleCode'] for e in server.v2.p3.validate_package(root)[0]],['schema'])
 def test_package_checks_without_workspace(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);package(w(),root);p=load(root/'proposal.json')
   e=next(x for x in p['files'] if x['kind']==md.KIND);m=load(root/e['path']);m['inputs'].append('pressure')
   server.contracts.save(root/e['path'],m);e['sha256']=server.contracts.hashed(root/e['path']);server.contracts.save(root/'proposal.json',p)
   self.assertIn('metric.input-unreferenced',[x['ruleCode'] for x in server.v2.p3.validate_package(root)[0]])
 def test_fixture_bundle_is_the_build_of_the_fixture_workspace(self):
  with tempfile.TemporaryDirectory() as t:
   publish(w(),Path(t)/'b');self.assertEqual(tree(Path(t)/'b'),tree(BUNDLE))
 def test_bifrost_receiver_accepts_the_same_bundle(self):self.assertEqual(tree(BIFROST_COPY),tree(BUNDLE))
if __name__=='__main__':unittest.main()
