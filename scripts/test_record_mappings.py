"""Offline row/cardinality/numeric/identity and persistence oracles."""
import copy,json,sys,tempfile,unittest,subprocess,sqlite3,socket
from pathlib import Path
from decimal import Decimal
from unittest.mock import patch
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'backend'),str(R/'scripts')]
import server,record_mappings as rm,record_preview as rp,record_authoring as ra,mapping_templates as mt,publication

def w():return server.contracts.load(R/'fixtures/record-mappings/workspace.json')
def sample():return server.contracts.load(R/'fixtures/record-mappings/snapshot.json')
def run(state=None,s=None,id='pressure-records'):return rp.run(w() if state is None else state,id,'1.0.0',sample() if s is None else s,4,'2026-10-18T00:00:01Z')
def one():
 state=w();state['recordMappings']=state['recordMappings'][:1];return state,state['recordMappings'][0]
def snap(r,s=None):
 s=sample() if s is None else s;s['resultSetRef']=rm.pin(r['resultSchema']);return s
def codes(p):return {x['code'] for x in p['issues']}
class Records(unittest.TestCase):
 def test_template_usage_includes_record_history(self):
  import template_authoring as ta
  with tempfile.TemporaryDirectory() as tmp:
   st=server.Store(Path(tmp)/'editor.sqlite3');st.migrate(0,{});st.save(1,w());data=ta.listing(st);self.assertEqual(len(data['recordApplications']),2);self.assertFalse(any(a['updateAvailable'] for a in data['recordApplications']))
 def test_independent_static_projection_oracle(self):
  state=w();expected=server.contracts.load(R/'fixtures/record-mappings/static-projections.json');self.assertEqual([rm.compile(r,next(t for t in state['mappingTemplates'] if mt.pin(t)==r['templateRef'])) for r in state['recordMappings']],expected)
 def test_record_semantic_lifecycle_impacts_and_retirement(self):
  import semantic_lifecycle as lc
  state=w();docs=rm.workspace_docs(state);derived=rm.governance(docs);impacts=lc.impacts(state['semantics']+derived);uri='urn:tyr:concept:record.pressure';self.assertEqual(len([x for x in impacts if x['semanticId']==uri]),2)
  e=copy.deepcopy(server.contracts.load(R/'fixtures/semantic-lifecycle/workspace.json')['semanticLifecycles'][0]);e.update(id='record-deprecated',action='deprecate',semanticId=uri,signatureSha256=mt.digest(lc.signatures(state['semantics'])[uri]));second=copy.deepcopy(e);second.update(id='record-retired',revision=2,action='retire',previousEvent=dict(id=e['id'],version=e['version'],sha256=mt.digest(e)));state['semanticLifecycles']=[e,second];server.check_state(state);self.assertIn('lifecycle.retired-binding',{x['ruleCode'] for x in server.findings_for(state)})
 def test_template_temporal_policy_uses_snapshot_clock(self):
  state,r=one();t=state['mappingTemplates'][0];base=server.contracts.load(R/'fixtures/p3cb/temporal-workspace.json');policy=base['mappings'][0]['mappings'][0]['temporalPolicy']
  t['mapping']['schemaVersion']='2.3.0'
  for b in t['mapping']['mappings']:b['temporalPolicy']=copy.deepcopy(policy)
  r['templateRef']=mt.pin(t);p=rp.run(state,r['id'],r['version'],sample(),4,'2026-10-18T00:00:02Z');self.assertFalse(p['valid']);self.assertIn('time.stale-input',codes(p))
 def test_fixture_and_numeric_ieee_loss_oracle(self):
  server.check_state(w());self.assertEqual(server.findings_for(w()),[]);p=run();self.assertTrue(p['valid']);self.assertEqual([r['asset'] for r in p['result']],['A-001','A-002']);self.assertEqual(p['result'][0]['pressure'],'100');self.assertEqual(p['result'][1]['pressure'],'123.4500000000000028421709430404007434844970703125');self.assertEqual(p['result'][1]['target'],'95');self.assertTrue(p['result'][1]['running']);self.assertEqual(p['quality'],'uncertain');self.assertTrue(any(m['preview']['losses'] for row in p['records'] for m in row['members']))
 def test_same_template_across_equipment_and_key_selected_object(self):
  state=w();self.assertEqual(state['recordMappings'][0]['templateRef'],state['recordMappings'][1]['templateRef']);p=run(id='pressure-object');self.assertEqual(p['result']['asset'],'A-002');self.assertEqual(p['result']['target'],'95')
 def test_order_independence_and_identity(self):
  a=run();s=sample();s['rows'].reverse();b=run(s=s);self.assertEqual(a['result'],b['result']);self.assertEqual([r['identity']['sha256'] for r in a['records']],[r['identity']['sha256'] for r in b['records']]);self.assertNotEqual(a['inputSha256'],b['inputSha256'])
 def test_zero_array_and_object_null(self):
  s=sample();s['rows']=[];a=run(s=s);self.assertEqual(a['result'],[]);self.assertTrue(a['empty']);self.assertEqual(a['quality'],'good');b=run(s=s,id='pressure-object');self.assertIsNone(b['result']);self.assertTrue(b['valid'])
 def test_zero_reject(self):
  state,r=one();r['output']['zeroPolicy']='reject';s=snap(r);s['rows']=[];self.assertIn('record.zero-rows',codes(run(state,s)))
 def test_many_object_requires_explicit_selection(self):
  state=w();r=state['recordMappings'][1];r['selection']={'kind':'all','key':[]};p=run(state,id='pressure-object');self.assertFalse(p['valid']);self.assertIn('record.many-rows',codes(p))
 def test_max_rows_is_not_truncation(self):
  state,r=one();r['output']['maxRows']=1;p=run(state);self.assertIsNone(p['result']);self.assertIn('record.max-rows',codes(p))
 def test_duplicate_key_even_unselected(self):
  s=sample();s['rows'].append(copy.deepcopy(s['rows'][0]));self.assertIn('record.duplicate-key',codes(run(s=s,id='pressure-object')))
 def test_composite_key_and_unicode_order(self):
  state,r=one();r['resultSchema']['fields'].append(dict(fieldId='batch',name='batch',valueType='String',unit={'status':'not-applicable'},inputStage='already-engineered',nullable=False));r['resultSchema']['keyFields']=['asset','batch'];s=snap(r);s['rows'][0]['batch']='나';s['rows'][1]['batch']='가';p=run(state,s);self.assertTrue(p['valid']);self.assertEqual(p['records'][0]['identity']['key'],['A-001','가'])
 def test_missing_empty_and_null_key(self):
  for value in [None,'']:
   s=sample();s['rows'][0]['asset']=value;self.assertIn('record.key-value',codes(run(s=s)))
  s=sample();del s['rows'][0]['asset'];self.assertIn('record.required-field',codes(run(s=s)))
 def test_nullable_default_and_missing_preserved(self):
  s=sample();s['rows'][0]['pressure']=None;p=run(s=s);self.assertTrue(p['valid']);self.assertEqual(p['result'][1]['pressure'],'0');self.assertIn('record.default-used',codes(p));s['rows'][0].pop('pressure');self.assertEqual(run(s=s)['result'][1]['pressure'],'0')
 def test_null_reject(self):
  state,r=one();b=next(b for b in r['bindings'] if b['fieldId']=='pressure');b.update(nullPolicy='reject',defaultValue=None);s=sample();s['rows'][0]['pressure']=None;self.assertIn('record.null-input',codes(run(state,s)))
 def test_cell_types_and_ranges(self):
  for key,value,code in [('target','2147483648','record.cell-int32'),('target','1.5','record.cell-int32'),('running','true','record.cell-boolean'),('pressure','NaN','constant.numeric')]:
   s=sample();s['rows'][0][key]=value;self.assertIn(code,codes(run(s=s)))
 def test_numeric_json_and_nested_values_rejected(self):
  for value in [1.5,{'x':'1'}]:
   s=sample();s['rows'][0]['pressure']=value;self.assertRaisesRegex(ValueError,'record.schema',run,s=s)
 def test_unknown_preserve_and_reject(self):
  p=run();self.assertEqual(p['preservedFields'][0]['fields']['unmapped_note'],'원본 보존');state,r=one();r['resultSchema']['unknownFields']='reject';self.assertIn('record.unknown-fields',codes(run(state,snap(r))))
 def test_quality_and_clock(self):
  s=sample();s['quality']='bad';self.assertIn('record.bad-snapshot-quality',codes(run(s=s)));s['quality']='uncertain';self.assertEqual(run(s=s)['quality'],'uncertain');s['capturedAt']='2026-10-18T00:00:02Z';self.assertIn('record.future-snapshot',codes(run(s=s)))
 def test_schema_hash_and_offset_pin(self):
  s=sample();s['resultSetRef']['sha256']='0'*64;self.assertRaisesRegex(ValueError,'snapshot-pin',run,s=s);s=sample();s['capturedAt']='2026-10-18T00:00:00-00:00';self.assertRaises(ValueError,run,s=s)
 def test_contract_slot_unit_key_and_default_validation(self):
  for mutation in [lambda r:r['resultSchema']['fields'][0].update(nullable=True),lambda r:r['resultSchema']['fields'][1].update(unit={'status':'known','code':'bar'}),lambda r:r['bindings'][1].update(slotId='input-99')]:
   state,r=one();mutation(r);self.assertRaises(ValueError,rm.check_workspace,state)
  state,r=one();next(b for b in r['bindings'] if b['fieldId']=='pressure')['defaultValue']='NaN';self.assertRaises(ValueError,rm.check_workspace,state)
 def test_template_update_is_pinned_until_explicit_new_mapping(self):
  state,r=one();t=copy.deepcopy(state['mappingTemplates'][0]);t.update(version='1.1.0',previousTemplateRef=mt.pin(state['mappingTemplates'][0]),reason='Explicit scale revision');next(b for b in t['mapping']['mappings'] if b['memberPath'][0]['memberId']=='target')['transform'][0]['factor']='0.2';state['mappingTemplates'].append(t);self.assertEqual(run(state)['result'][1]['target'],'95');updated=copy.deepcopy(r);updated.update(version='1.1.0',previousMappingRef=rm.pin(r),templateRef=mt.pin(t));updated['evidenceRefs']=[dict(artifactId=rm.evidence_id(updated),locator=dict(kind='text-line',line=1))];state['recordMappings'].append(updated);p=rp.run(state,updated['id'],updated['version'],sample(),4,'2026-10-18T00:00:01Z');self.assertEqual(p['result'][1]['target'],'190');self.assertEqual(run(state)['result'][1]['target'],'95')
 def test_no_provider_sql_or_socket_execution(self):
  with patch.object(socket,'socket',side_effect=AssertionError('No socket')),patch.object(sqlite3,'connect',side_effect=AssertionError('No SQL')):self.assertTrue(run()['valid'])
 def test_sql_only_metadata_not_compiled_executable_source(self):
  state,r=one();a=rm.compile(r,state['mappingTemplates'][0]);self.assertTrue(all(s['access']['expression'] is None and s['access']['expressionLanguage']=='none' for s in a['sourceSnapshots']));self.assertIn('SELECT',r['resultSchema']['query']['text'])
 def test_sqlite_immutable_cas_and_readonly_preview(self):
  with tempfile.TemporaryDirectory() as tmp:
   store=server.Store(Path(tmp)/'editor.sqlite3');store.migrate(0,{});store.save(1,w());before=store.read()
   with store.connect() as c:rows=list(c.iterdump())
   run(before['workspace']);self.assertEqual(store.read(),before)
   with store.connect() as c:self.assertEqual(rows,list(c.iterdump()))
   bad=copy.deepcopy(before['workspace']);bad['recordMappings'].pop();self.assertRaises(ValueError,store.save,2,bad);self.assertEqual(store.read(),before);self.assertEqual(server.Store(store.path).read(),before);self.assertRaises(server.Conflict,store.save,1,before['workspace'])
 def test_scenario_opt_in_table_cas_and_workspace_unchanged(self):
  with tempfile.TemporaryDirectory() as tmp:
   store=server.Store(Path(tmp)/'editor.sqlite3');store.migrate(0,{});store.save(1,w());before=store.read();self.assertEqual(ra.scenarios(store),[])
   with store.connect() as c:self.assertFalse(c.execute("SELECT 1 FROM sqlite_master WHERE name='record_scenarios'").fetchone())
   req=dict(revision=2,id='rows',scenarioRevision=0,mappingRef=rm.pin(w()['recordMappings'][0]),snapshot=sample());saved=ra.save_scenario(store,req,server.Conflict);self.assertEqual(saved['scenarioRevision'],1);self.assertEqual(store.read(),before);self.assertRaises(server.Conflict,ra.save_scenario,store,req,server.Conflict);self.assertEqual(ra.scenarios(server.Store(store.path)),[saved])
 def test_self_contained_record_only_publication_and_no_row_payload(self):
  with tempfile.TemporaryDirectory() as tmp:
   folder=Path(tmp)/'bundle';_,_,findings=publication.build(w(),folder,'record-scope','record-line','proposer',None,['record:pressure-object@1.0.0'],False,server.build_package);self.assertEqual(findings,[]);p=server.contracts.load(folder/'proposal.json');self.assertEqual(p['schemaVersion'],'2.20.0');self.assertEqual(sum(e['kind']=='record-mapping' for e in p['files']),1);self.assertFalse(any(e['kind'] in ('virtual-result-set','mapping-set') for e in p['files']))
 def test_standalone_contract_cli_and_schema_mirrors(self):
  p=subprocess.run([sys.executable,'-B',str(R/'scripts/p3a_contracts.py'),'--package',str(R/'fixtures/record-mappings/bundle'),'--deny-network'],capture_output=True,text=True,timeout=120);self.assertEqual(p.returncode,0,p.stderr);self.assertTrue(json.loads(p.stdout)['valid'])
  for p in (R/'contracts').glob('*/*.schema.json'):self.assertEqual(p.read_bytes(),(R.parent/'bifrost/core/src/main/resources/mapping-contracts'/p.relative_to(R/'contracts')).read_bytes())
 def test_baseline_sha_unchanged(self):
  for p,h in server.contracts.load(R/'docs/verification/record-mappings-baseline-pins.json').items():self.assertEqual(server.contracts.hashed(R.parent/p),h,p)
if __name__=='__main__':unittest.main()
