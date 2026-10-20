"""Independent cross-graph numeric oracles, rejection and compatibility checks."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'backend'),str(R/'scripts')]
import server,preview,graph_reuse as reuse,sample_quality as sq,change_review as review,publication

def load():return server.contracts.load(R/'fixtures/cross-graph/workspace.json')
def graph(w,id):return next(g for g in w['graphs'] if g['id']==id)
def binding(w,p='ab',member='quotient'):return next(b for m in w['mappings'] if m['id']=='arithmetic-mapping-'+p for b in m['mappings'] if b['mappingId']==p+'-'+member)
def ep(id,node='delta',version='1.0.0'):return {'kind':'graph','graphRef':{'id':id,'version':version},'nodeId':node}
def samples():return server.contracts.load(R/'fixtures/p3cc/samples.json')
def run(w=None,p='ab',member='quotient',s=None):
 w=load() if w is None else w;b=binding(w,p,member);available=samples() if s is None else s
 return preview.run(w,'arithmetic-mapping-'+p,p+'-'+member,{k:v for k,v in available.items() if k in sq.source_ids(w,b)},0)
class Contracts(unittest.TestCase):
 def test_schema_ids_and_independent_copies(self):
  ids=set()
  for p in (R/'contracts').glob('*/*.schema.json'):
   id=server.contracts.load(p)['$id'];self.assertNotIn(id,ids);ids.add(id)
   self.assertEqual(p.read_bytes(),(R.parent/'bifrost/core/src/main/resources/mapping-contracts'/p.relative_to(R/'contracts')).read_bytes())
 def test_four_profiles_oracles_and_out_of_order_dependencies(self):
  w=load();server.check_state(w);self.assertEqual(server.findings_for(w),[])
  for p in ['ab','ua','db','melsec']:
   for member,expected in {'sum':'200','scaled':'200','quotient':'50','ratio':'1'}.items():self.assertEqual(run(w,p,member)['result']['value'],expected)
 def test_diamond_result_evaluated_once_and_references_visible(self):
  v=run(member='sum');self.assertEqual(sum(t['stage']=='graph:subtract' for t in v['trace']),1);self.assertEqual(sum(t['stage']=='graph:reference' for t in v['trace']),2)
 def test_pinned_three_level_trace_and_leaf_samples(self):
  w=load();self.assertEqual(set(sq.source_ids(w,binding(w))),{'structure-ab-actual','structure-ab-target','arithmetic-ab-gain'});v=run(w);ids=[t['identity'] for t in v['trace']];self.assertIn('shared-ab/delta',ids);self.assertIn('consumer-ab/quotient',ids);self.assertIn('final-ab/result',ids)
 def test_same_node_ids_in_distinct_graphs_do_not_alias(self):
  w=load();g=graph(w,'final-ab');g['nodes'][0]['nodeId']='delta';binding(w)['valueRef']['nodeId']='delta';self.assertEqual(run(w)['result']['value'],'50')
 def test_self_cycle(self):
  w=load();graph(w,'consumer-ab')['nodes'][0]['inputs']['left']=ep('consumer-ab','sum');self.assertRaisesRegex(ValueError,'dependency-cycle',server.check_state,w)
 def test_two_graph_cycle(self):
  w=load();g=graph(w,'shared-ab');g['schemaVersion']='2.17.0';g['nodes'][0]['inputs']['left']=ep('consumer-ab','sum');self.assertRaisesRegex(ValueError,'dependency-cycle',server.check_state,w)
 def test_three_graph_cycle(self):
  w=load();g=graph(w,'shared-ab');g['schemaVersion']='2.17.0';g['nodes'][0]['inputs']['left']=ep('final-ab','result');self.assertRaisesRegex(ValueError,'dependency-cycle',server.check_state,w)
 def test_missing_graph_version_node_and_equipment(self):
  for target,code in [(ep('absent'),'reference.missing'),(ep('shared-ab',version='1.0.1'),'reference.missing'),(ep('shared-ab','absent'),'graph.node-missing'),(ep('shared-ua'),'value.equipment')]:
   w=load();graph(w,'consumer-ab')['nodes'][0]['inputs']['left']=target;self.assertRaisesRegex(ValueError,code,server.check_state,w)
 def test_legacy_contract_cannot_smuggle_graph_endpoint(self):
  w=load();graph(w,'consumer-ab')['schemaVersion']='2.15.0';self.assertRaisesRegex(ValueError,'schema',server.check_state,w)
 def test_declared_type_and_unit_mismatch(self):
  for key,value,code in [('valueType','UInt16','graph.output-type'),('unit',{'status':'known','code':'bar'},'graph.output-unit')]:
   w=load();graph(w,'final-ab')['nodes'][0][key]=value;self.assertRaisesRegex(ValueError,code,server.check_state,w)
 def test_transitive_evidence_required(self):
  w=load();graph(w,'final-ab')['nodes'][0]['evidenceRefs']=graph(w,'final-ab')['nodes'][0]['evidenceRefs'][:1];self.assertRaisesRegex(ValueError,'graph.evidence-incomplete',server.check_state,w)
 def test_whole_array_endpoint_forbidden(self):
  w=load();graph(w,'shared-ab')['nodes'][0].update(op='identity',valueType='FixedArray',inputs={'value':{'kind':'source','sourceRef':{'id':'structure-ab-actual','version':'1.0.0'}}});self.assertRaisesRegex(ValueError,'reference-scalar-required',server.check_state,w)
 def test_local_cycle_in_reused_graph(self):
  w=load();graph(w,'shared-ab')['nodes'][0]['inputs']['left']={'kind':'node','nodeId':'delta'};self.assertRaisesRegex(ValueError,'graph.cycle',server.check_state,w)
 def test_dependency_depth_bound(self):
  w=load();first=graph(w,'shared-ab');chain=[copy.deepcopy(first)]
  for i in range(33):
   g=copy.deepcopy(first);g.update(id='deep-'+str(i),schemaVersion='2.17.0');g['nodes']=[dict(g['nodes'][0],op='identity',inputs={'value':ep(chain[-1]['id'])})];chain.append(g)
  self.assertRaisesRegex(ValueError,'dependency-depth',reuse.order,chain)
 def test_total_node_path_bound(self):
  w=load();first=copy.deepcopy(graph(w,'shared-ab'));chain=[first]
  for i in range(3):
   g=copy.deepcopy(first);g.update(id='path-'+str(i),schemaVersion='2.17.0');g['nodes']=[]
   for j in range(64):g['nodes'].append(dict(first['nodes'][0],nodeId='n'+str(j),op='identity',inputs={'value':ep(chain[-1]['id'],chain[-1]['nodes'][-1]['nodeId']) if j==0 else {'kind':'node','nodeId':'n'+str(j-1)}}))
   chain.append(g)
  self.assertRaisesRegex(ValueError,'path-depth',reuse.order,chain)
 def test_dependency_size_bound(self):
  w=load();g=graph(w,'consumer-ab');g['nodes']=g['nodes']*2050;self.assertRaisesRegex(ValueError,'dependency-size',reuse.order,w['graphs'])
 def test_missing_zero_and_precision_loss_propagate(self):
  self.assertIsNone(run(s={})['result']);v=samples();v['arithmetic-ab-gain']={'typedValue':'0'};self.assertIn('value.divide-zero',{i['code'] for i in run(s=v)['issues']});v['arithmetic-ab-gain']={'typedValue':'3'};v['structure-ab-actual']={'typedValue':'1'};v['structure-ab-target']={'typedValue':'0'};result=run(s=v);self.assertEqual(len(result['losses']),2)
 def test_quality_time_cross_graph_leaf_policy(self):
  w=load();b=binding(w);b['temporalPolicy']={'timestampBasis':'source','maxAgeMs':1000,'maxSkewMs':100,'assembly':'latest','missingInput':'reject','badInput':'reject','uncertainInput':'propagate'}
  # Reuse the established temporal schema shape from an existing fixture.
  reference=server.contracts.load(R/'fixtures/p3d/workspace.json');b['temporalPolicy']=copy.deepcopy(next(b['temporalPolicy'] for m in reference['mappings'] for b in m['mappings'] if 'temporalPolicy' in b))
  ids=sq.source_ids(w,b);self.assertEqual(len(ids),3)
  from datetime import datetime,timezone
  available={id:{'value':samples()[id],'sourceTimestamp':'2026-10-18T00:00:00Z','serverTimestamp':'2026-10-18T00:00:00Z','quality':'bad' if id=='structure-ab-target' else 'good','sequence':None} for id in ids}
  # The existing assessor validates clocks and bad quality across transitive leaves.
  values,trace,issues,temporal=sq.assess(w,b,available,{'at':'2026-10-18T01:00:00Z','triggerSequence':None})
  self.assertEqual(temporal['assemblyQuality'],'bad');self.assertIn('quality.bad-input',{i['code'] for i in issues});self.assertIn('time.stale-input',{i['code'] for i in issues})
 def selector(self):
  w=load();g=copy.deepcopy(graph(w,'final-ab'));g['id']='selector-reuse-ab';n=g['nodes'][0];n.update(op='bounded-selector',outOfRange='reject',inputs={'index':{'kind':'source','sourceRef':{'id':'arithmetic-ab-gain','version':'1.0.0'}},'candidate0':ep('shared-ab','delta'),'candidate1':ep('consumer-ab','quotient')});w['graphs'].append(g);b=binding(w,member='sum');b['valueRef']=ep(g['id'],'result');b['evidenceRefs']=copy.deepcopy(n['evidenceRefs']);return w
 def test_external_selector_evaluates_selected_path_only(self):
  w=self.selector();server.check_state(w);v=samples();v['arithmetic-ab-gain']={'typedValue':'0'};result=run(w,member='sum',s=v);self.assertEqual(result['result']['value'],'100');self.assertNotIn('value.divide-zero',{i['code'] for i in result['issues']});self.assertFalse(any(t['stage']=='graph:divide' for t in result['trace']))
 def test_external_selector_lineage_pin_changes_with_producer(self):
  w=self.selector();v=samples();v['arithmetic-ab-gain']={'typedValue':'0'};a=run(w,member='sum',s=v);graph(w,'shared-ab')['nodes'][0]['inputs']['left'],graph(w,'shared-ab')['nodes'][0]['inputs']['right']=graph(w,'shared-ab')['nodes'][0]['inputs']['right'],graph(w,'shared-ab')['nodes'][0]['inputs']['left'];b=run(w,member='sum',s=v);self.assertNotEqual(a['selections'][0]['definitionSha256'],b['selections'][0]['definitionSha256'])
 def test_preview_cycle_is_refused_before_recursive_evaluation(self):
  w=load();graph(w,'consumer-ab')['nodes'][0]['inputs']['left']=ep('consumer-ab','sum');self.assertRaisesRegex(ValueError,'dependency-cycle',run,w)
 def test_change_review_tracks_transitive_graph_dependency(self):
  w=load();before=review.target(w,'value-graph:final-ab');graph(w,'shared-ab')['nodes'][0]['inputs']['left'],graph(w,'shared-ab')['nodes'][0]['inputs']['right']=graph(w,'shared-ab')['nodes'][0]['inputs']['right'],graph(w,'shared-ab')['nodes'][0]['inputs']['left'];after=review.target(w,'value-graph:final-ab');self.assertNotEqual(before['dependencySha256'],after['dependencySha256']);self.assertIn('value-graph:shared-ab',after['dependencies'])
class Storage(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.store=server.Store(Path(self.tmp.name)/'editor.sqlite3');self.store.migrate(0,{});self.store.save(1,load())
 def tearDown(self):self.tmp.cleanup()
 def test_round_trip_does_not_flatten_or_migrate(self):
  before=self.store.read();self.assertEqual(server.Store(self.store.path).read(),before);self.assertEqual(graph(before['workspace'],'consumer-ab')['nodes'][0]['inputs']['left'],ep('shared-ab'))
 def test_cycle_rejection_keeps_sqlite_unchanged(self):
  snap=self.store.read();w=copy.deepcopy(snap['workspace']);graph(w,'consumer-ab')['nodes'][0]['inputs']['left']=ep('consumer-ab','sum');self.assertRaises(ValueError,self.store.save,snap['revision'],w);self.assertEqual(self.store.read(),snap)
 def test_referenced_graph_removal_or_version_change_rejected(self):
  for remove in [True,False]:
   snap=self.store.read();w=copy.deepcopy(snap['workspace'])
   if remove:w['graphs']=[g for g in w['graphs'] if g['id']!='shared-ab']
   else:graph(w,'shared-ab')['version']='1.1.0'
   self.assertRaises(ValueError,self.store.save,snap['revision'],w);self.assertEqual(self.store.read(),snap)
 def test_preview_readonly(self):
  snap=self.store.read();run(snap['workspace']);self.assertEqual(self.store.read(),snap)
 def test_publication_closure_includes_upstream_graphs_and_sources(self):
  folder=Path(self.tmp.name)/'bundle';publication.build(load(),folder,'cross-submission','cross-offline','proposer',None,['arithmetic-mapping-ab'],False,server.build_package);p=server.contracts.load(folder/'proposal.json');ids={e['id'] for e in p['files'] if e['kind']=='value-graph'};self.assertEqual(ids,{'shared-ab','consumer-ab','final-ab'});self.assertEqual(server.v2.p3.validate_package(folder)[0],[])
if __name__=='__main__':unittest.main(verbosity=2)
