"""Synthetic mapping reuse oracles; no device IO."""
import copy,json,sys,tempfile,unittest,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'backend'),str(R/'scripts')]
import server,mapping_templates as mt,template_authoring as ta,preview,sample_quality as sq,publication

def load(name='workspace'):return server.contracts.load(R/'fixtures/mapping-templates'/(name+'.json'))
def docs(w):return w['mappingTemplates']+w['templateApplications']+[r['definition'] for r in w['sources']]+w['semantics']+w['targets']+w['graphs']+w['mappings']
class Templates(unittest.TestCase):
 def test_four_profiles_numeric_oracle_and_pin(self):
  w=load();server.check_state(w);self.assertEqual(server.findings_for(w),[]);s=server.contracts.load(R/'fixtures/p3cc/samples.json')
  for p,expected in [('ab','50'),('ua','100'),('db','50'),('melsec','50')]:
   m=next(m for m in w['mappings'] if m['id']=='reuse-pump-'+p+'-mapping');b=next(b for b in m['mappings'] if b['memberPath'][0]['memberId']=='quotient');ids=sq.source_ids(w,b);v=preview.run(w,m['id'],b['mappingId'],{k:s[k] for k in ids},0);self.assertEqual(v['result']['value'],expected)
 def test_latest_template_does_not_implicitly_update(self):
  w=load('before-update');_,apps=mt.histories(docs(w));self.assertTrue(all(v[-1]['templateRef']['version']=='1.0.0' for v in apps.values()))
 def test_old_graph_generations_retained_target_identity_stable(self):
  w=load();a=[a for a in w['templateApplications'] if a['applicationId']=='pump-ua'];self.assertEqual(a[0]['generated'][1]['id'],a[1]['generated'][1]['id']);self.assertNotEqual(a[0]['generated'][1]['version'],a[1]['generated'][1]['version']);self.assertTrue(all(g in w['graphs'] for g in a[0]['generated'] if g['kind']=='value-graph'))
 def test_pin_not_just_version(self):
  w=load();w['templateApplications'][0]['templateRef']['sha256']='0'*64;self.assertRaisesRegex(ValueError,'pin-mismatch',mt.check_workspace,w)
 def test_generated_mapping_tamper(self):
  w=load();next(m for m in w['mappings'] if m['id']=='reuse-pump-ab-mapping')['mappings'][0]['invalidValuePolicy']='error';self.assertRaises(ValueError,mt.check_workspace,w)
 def test_source_pin_tamper(self):
  w=load();next(r for r in w['sources'] if r['definition']['id']=='structure-ab-actual')['definition']['rawAddressText']='changed';self.assertRaisesRegex(ValueError,'source-pin',mt.check_workspace,w)
 def test_template_parent_hash(self):
  w=load();w['mappingTemplates'][-1]['previousTemplateRef']['sha256']='0'*64;self.assertRaisesRegex(ValueError,'version-chain',mt.check_workspace,w)
 def test_missing_slot(self):
  w=load();w['templateApplications'][0]['bindings'].pop();self.assertRaisesRegex(ValueError,'bindings',mt.check_workspace,w)
 def test_duplicate_slot(self):
  w=load();w['templateApplications'][0]['bindings'].append(copy.deepcopy(w['templateApplications'][0]['bindings'][0]));self.assertRaisesRegex(ValueError,'bindings',mt.check_workspace,w)
 def test_type_unit_stage_and_layout_rejected(self):
  for k,value in [('unit',{'status':'known','code':'bar'}),('inputStage','engineering'),('rawRepresentation',{'mode':'typed','valueType':'Double'}),('fixedArray',{'shape':[2]})]:
   w=load();w['templateApplications'][0]['sourceSnapshots'][0][k]=value;self.assertRaisesRegex(ValueError,'slot-incompatible',mt.check_workspace,w)
 def test_source_other_equipment_rejected(self):
  w=load();w['templateApplications'][0]['sourceSnapshots'][0]['equipmentInstanceId']='line-a-motor-ua';self.assertRaisesRegex(ValueError,'source-context',mt.check_workspace,w)
 def test_missing_template_version(self):
  w=load();w['templateApplications'][0]['templateRef']['id']='absent';self.assertRaisesRegex(ValueError,'missing-version',mt.check_workspace,w)
 def test_application_chain_gap(self):
  w=load();w['templateApplications'][-1]['revision']=3;self.assertRaisesRegex(ValueError,'application-chain',mt.check_workspace,w)
 def test_template_graph_reference_not_captured(self):
  t=load()['mappingTemplates'][0];t['graphs'].pop();self.assertRaises(ValueError,mt.template_check,t)
 def test_global_history_fork_and_provenance_omission(self):
  w=load();prior=docs(w);d=copy.deepcopy(prior);next(x for x in d if x['kind']=='mapping-template')['reason']='fork';self.assertRaisesRegex(ValueError,'history-conflict',mt.validate,d,prior)
  self.assertRaisesRegex(ValueError,'provenance-required',mt.validate,[x for x in prior if x['kind'] not in mt.KINDS],prior)
 def test_sqlite_immutable_roundtrip_and_rollback(self):
  with tempfile.TemporaryDirectory() as tmp:
   store=server.Store(Path(tmp)/'editor.sqlite3');store.migrate(0,{});store.save(1,load());before=store.read();self.assertEqual(server.Store(store.path).read(),before)
   for section in ['mappingTemplates','templateApplications']:
    w=copy.deepcopy(before['workspace']);w[section].pop();self.assertRaises(ValueError,store.save,2,w);self.assertEqual(store.read(),before)
   self.assertRaises(server.Conflict,store.save,1,before['workspace'])
 def test_candidates_never_hide_incompatible_sources(self):
  w=load();t=copy.deepcopy(w['mappingTemplates'][0]);t['slots'][0]['signature']['unit']={'status':'known','code':'bar'};t['slots']=t['slots'][:1];rows=ta.candidates(w,t,'line-a-motor-db');self.assertTrue(all(not c['compatible'] for r in rows for c in r['candidates']));self.assertTrue(all(r['recommendation'] is None for r in rows))
 def test_standalone_cli_and_independent_schemas(self):
  p=subprocess.run([sys.executable,'-B',str(R/'scripts/p3a_contracts.py'),'--package',str(R/'fixtures/mapping-templates/bundle'),'--deny-network'],capture_output=True,text=True,timeout=120);self.assertEqual(p.returncode,0,p.stderr);self.assertTrue(json.loads(p.stdout)['valid'])
  for p in (R/'contracts').glob('*/*.schema.json'):self.assertEqual(p.read_bytes(),(R.parent/'bifrost/core/src/main/resources/mapping-contracts'/p.relative_to(R/'contracts')).read_bytes())
 def test_baseline_files_unchanged(self):
  for path,sha in server.contracts.load(R/'docs/verification/mapping-templates-baseline-pins.json').items():self.assertEqual(server.contracts.hashed(R.parent/path),sha,path)
 def test_plan_preview_scalar_inputs_and_readonly(self):
  with tempfile.TemporaryDirectory() as tmp:
   store=server.Store(Path(tmp)/'editor.sqlite3');store.migrate(0,{});store.save(1,load('before-update'));before=store.read();a=next(a for a in before['workspace']['templateApplications'] if a['applicationId']=='pump-ua');t=next(t for t in before['workspace']['mappingTemplates'] if t['version']=='1.1.0');req=dict(revision=2,templateRef=mt.pin(t),applicationId='pump-ua',equipmentInstanceId=a['equipmentInstanceId'],targetLabel=a['targetLabel'],bindings=a['bindings'],authoredBy='tester',slotSamples={'input-1':'2','input-2':'150','input-3':'50'});plan,_=ta.plan(store,req,server.Conflict,server.build_package);self.assertTrue(plan['valid']);self.assertTrue(any(p['preview']['result']['value']=='100' for p in plan['previews']));self.assertEqual(store.read(),before)
 def test_existing_consumer_keeps_old_generation_and_exports_proof(self):
  w=load();first=next(a for a in w['templateApplications'] if a['applicationId']=='pump-ua' and a['revision']==1);g=next(g for g in first['generated'] if g['kind']=='value-graph' and g['id'].endswith('-g1'));m=next(m for m in w['mappings'] if m['id']=='arithmetic-mapping-ua');b=next(b for b in m['mappings'] if b['mappingId']=='ua-quotient');b['valueRef']={'kind':'graph','graphRef':{'id':g['id'],'version':g['version']},'nodeId':'result'};server.check_state(w);available=server.contracts.load(R/'fixtures/p3cc/samples.json');ids=sq.source_ids(w,b);self.assertEqual(preview.run(w,m['id'],b['mappingId'],{k:available[k] for k in ids},0)['result']['value'],'50')
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/'bundle';_,_,f=publication.build(w,root,'consumer-proof','template-fixture','fixture-author',None,[m['id']],False,server.build_package);self.assertEqual(f,[]);p=server.contracts.load(root/'proposal.json');self.assertEqual(sum(e['kind']=='template-application' for e in p['files']),2);self.assertTrue(any(e['id']==g['id'] for e in p['files']));self.assertTrue(any(e['id']=='reuse-pump-ua-mapping' for e in p['files']))
 def test_effective_types_for_codec_native_bit_and_fixed_array(self):
  w=server.contracts.load(R/'fixtures/a07/workspace.json');sources={(r['definition']['id'],r['definition']['version']):r['definition'] for r in w['sources']};self.assertEqual(mt.signature(sources[('a07-melsec-alarm-alias','1.0.0')],sources)['rawRepresentation']['valueType'],'Boolean');s=copy.deepcopy(sources[('a07-melsec-word','1.0.0')]);s['rawRepresentation']['codec']={'kind':'bcd16'};s['inputStage']='raw';self.assertEqual(mt.signature(s)['rawRepresentation']['valueType'],'Int32');s['access']['bitOffset']=3;self.assertEqual(mt.signature(s)['rawRepresentation']['valueType'],'Boolean');s['fixedArray']={'shape':[2]};self.assertEqual(mt.signature(s)['rawRepresentation']['valueType'],'FixedArray')
 def test_view_parent_closure_preview_and_tamper(self):
  w=load('views-workspace');server.check_state(w);a=w['templateApplications'][0];self.assertEqual(len(a['bindings']),1);self.assertEqual(len(a['sourceSnapshots']),3);m=next(m for m in w['mappings'] if m['id']=='reuse-view-melsec-mapping');b=m['mappings'][0];self.assertIs(preview.run(w,m['id'],b['mappingId'],{'a07-melsec-word':{'bytesHex':'0080'}},0)['result']['value'],True)
  bad=copy.deepcopy(w);next(r for r in bad['sources'] if r['definition']['id']=='a07-melsec-word')['definition']['rawAddressText']='changed parent';self.assertRaisesRegex(ValueError,'source-pin',mt.check_workspace,bad)
  bad=copy.deepcopy(w);bad['templateApplications'][0]['sourceSnapshots']=[s for s in a['sourceSnapshots'] if s['id']!='a07-melsec-word'];self.assertRaisesRegex(ValueError,'parent-missing',mt.check_workspace,bad)
  with tempfile.TemporaryDirectory() as tmp:
   store=server.Store(Path(tmp)/'editor.sqlite3');store.migrate(0,{});store.save(1,w);req=dict(revision=2,templateRef=a['templateRef'],applicationId=a['applicationId'],equipmentInstanceId=a['equipmentInstanceId'],targetLabel=a['targetLabel'],bindings=a['bindings'],authoredBy='tester',slotSamples={'input-1':'0080'});plan,_=ta.plan(store,req,server.Conflict,server.build_package);self.assertTrue(plan['valid']);self.assertIs(plan['previews'][0]['preview']['result']['value'],True)
 def test_scoped_publication_includes_application_proof(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/'bundle';_,_,f=publication.build(load(),root,'scoped','template-fixture','fixture-author',None,['reuse-pump-ua-mapping'],False,server.build_package);self.assertEqual(f,[]);p=server.contracts.load(root/'proposal.json');self.assertEqual(p['schemaVersion'],'2.19.0');self.assertEqual(sum(e['kind']=='template-application' for e in p['files']),2)
if __name__=='__main__':unittest.main()
