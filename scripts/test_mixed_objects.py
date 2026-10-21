"""Offline mixed-object contracts, provenance, values, templates and real SQLite."""
import copy,json,sys,tempfile,unittest,sqlite3,socket,subprocess,hashlib
from pathlib import Path
from unittest.mock import patch
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'scripts'),str(R/'backend')]
import server,record_fields as rf,record_mappings as rm,mapping_templates as mt,mixed_object_authoring as ma,template_authoring as ta,logical_preview as lp,preview,record_field_preview as fp,publication
F=R/'fixtures/mixed-objects'
def load(n):return server.contracts.load(F/n)
def w():return load('workspace.json')
def samples():return load('samples.json')
def source(state=None):return next(x['definition'] for x in (w() if state is None else state)['sources'] if x['definition'].get('recordField'))
def run(state=None,s=None,e=None):return lp.run(w() if state is None else state,dict(id='reuse-combined-pump-target',version='1.0.0'),samples() if s is None else s,3,e)
def snapshot(s=None):return (samples() if s is None else s)[source()['id']]['resultSet']
class MixedObjects(unittest.TestCase):
 def test_object_scenario_storage_CAS_and_plain_inputs(self):
  import sample_quality as sq
  with tempfile.TemporaryDirectory() as tmp:
   st=server.Store(Path(tmp)/'editor.sqlite3');st.migrate(0,{});st.save(1,w());before=st.read();scene=dict(kind='object-preview-scenario',schemaVersion='2.21.0',id='combined-scene',version='1.0.0',label='Virtual mixed object',workspaceSha256=sq.digest(w()),targetInstanceRef=dict(id='reuse-combined-pump-target',version='1.0.0'),evaluationContext=None,samples=samples());st.save_scenario(2,0,scene);self.assertEqual(st.read(),before);self.assertEqual(st.scenarios()['scenarios'][0]['scenario'],scene);self.assertRaises(server.Conflict,st.save_scenario,2,0,scene);self.assertEqual(len(server.Store(st.path).scenarios()['scenarios']),1)
 def test_same_record_fields_require_same_snapshot(self):
  state=w();original=source(state);r=state['recordMappings'][1];other=rf.create(state,'db-pressure',rm.pin(r),'pressure');state['sources'].append(dict(definition=other,note='Synthetic second field',origin='synthetic',capturedAt='2026-10-18T00:00:00Z'));m=copy.deepcopy(state['mappings'][0]);state.pop('templateApplications');state['mappingTemplates']=state['mappingTemplates'][:-1];b=m['mappings'][0];b['valueRef']=dict(kind='source',sourceRef=dict(id=other['id'],version=other['version']));b['evidenceRefs']=other['evidenceRefs'];b['transform']=[dict(op='unit-convert',**{'from':'Pa','to':'kPa'}),dict(op='cast',to='Double',overflow='error',rounding='half-even')];state['mappings']=[m];s=samples();s[other['id']]=copy.deepcopy(s[original['id']]);self.assertIsNotNone(run(state,s)['result']);s[other['id']]['resultSet']['rows'][0]['target']='951';p=run(state,s);self.assertIsNone(p['result']);self.assertTrue(any(i['code']=='record-field.snapshot-conflict' for i in p['issues']))
 def test_template_can_be_reapplied_with_record_source(self):
  with tempfile.TemporaryDirectory() as tmp:
   st=server.Store(Path(tmp)/'editor.sqlite3');st.migrate(0,{});st.save(1,w());a=w()['templateApplications'][0];req=dict(revision=2,templateRef=a['templateRef'],applicationId='another-pump',equipmentInstanceId=a['equipmentInstanceId'],targetLabel='Another object',bindings=a['bindings'],authoredBy='operator');plan,_=ta.plan(st,req,server.Conflict,server.build_package);self.assertTrue(plan['valid']);r=ta.apply(st,dict(req,planSha256=plan['planSha256']),server.Conflict,server.build_package);state=r['saved']['workspace'];p=lp.run(state,dict(id='reuse-another-pump-target',version='1.0.0'),samples(),3);self.assertEqual(p['result'],load('oracle.json'))
 def test_Boolean_record_field_template_virtual_input(self):
  with tempfile.TemporaryDirectory() as tmp:
   state=load('before.json');r=state['recordMappings'][1];t=state['mappingTemplates'][0];bindings=[];boolean_slot=None
   for b in r['bindings']:
    s=rf.create(state,'proxy-'+b['fieldId'],rm.pin(r),b['fieldId'],b['nullPolicy'],b['defaultValue']);state['sources'].append(dict(definition=s,note='Synthetic field template reuse',origin='synthetic',capturedAt='2026-10-18T00:00:00Z'));bindings.append(dict(slotId=b['slotId'],sourceRef=dict(id=s['id'],version=s['version'])))
    if b['fieldId']=='running':boolean_slot=b['slotId']
   st=server.Store(Path(tmp)/'editor.sqlite3');st.migrate(0,{});st.save(1,state);req=dict(revision=2,templateRef=mt.pin(t),applicationId='record-field-bools',equipmentInstanceId='record-line-b',targetLabel='Record fields through template',bindings=bindings,authoredBy='operator',slotSamples={boolean_slot:json.dumps(snapshot())});plan,_=ta.plan(st,req,server.Conflict,server.build_package);self.assertTrue(plan['valid']);self.assertTrue(any(p['preview']['result'] and p['preview']['result']['value'] is True for p in plan['previews']))
 def test_fixture_one_object_four_source_kinds(self):
  state=w();server.check_state(state);self.assertEqual(server.findings_for(state),[]);p=run();self.assertEqual(p['result'],load('oracle.json'));self.assertEqual(p['quality'],'good');self.assertTrue(any(t['stage']=='record-field-select' for m in p['members'] for t in m['report']['trace']))
 def test_raw_record_field_not_template_engineering_result(self):
  value,proof=fp.resolve(w(),source(),samples()[source()['id']]);self.assertEqual(value['typedValue'],'950');self.assertEqual(proof['recordKey'],['A-002']);self.assertFalse(proof['atomicSnapshot']);self.assertEqual(run()['result']['target'],'95')
 def test_no_scalar_override(self):
  s=samples();s[source()['id']]={'typedValue':'950'};p=run(s=s);self.assertIsNone(p['result']);self.assertTrue(any(i['code']=='record-field.snapshot-required' for i in p['issues']))
 def test_zero_record_is_not_nullable_default(self):
  s=samples();snapshot(s)['rows']=[];p=run(s=s);self.assertIsNone(p['result']);self.assertTrue(any(i['code']=='record-field.zero-rows' for i in p['issues']))
 def test_duplicate_keys_even_unselected(self):
  s=samples();snapshot(s)['rows'].append(copy.deepcopy(snapshot(s)['rows'][1]));self.assertIsNone(run(s=s)['result'])
 def test_one_object_rejects_multiple_rows(self):
  state=w();r=state['recordMappings'][1];r['selection']=dict(kind='all',key=[]);s=source(state);s['recordField']['recordMappingRef']=rm.pin(r);self.assertRaisesRegex(ValueError,'many-rows',fp.resolve,state,s,samples()[source()['id']])
 def test_missing_required_unselected_field(self):
  s=samples();del snapshot(s)['rows'][1]['running'];self.assertIsNone(run(s=s)['result'])
 def test_snapshot_pin_and_primitive_type(self):
  for change in ['pin','type']:
   s=samples()
   if change=='pin':snapshot(s)['resultSetRef']['sha256']='0'*64
   else:snapshot(s)['rows'][0]['target']='1.5'
   self.assertIsNone(run(s=s)['result'])
 def test_explicit_field_null_default(self):
  state=w();r=state['recordMappings'][1];s=rf.create(state,'nullable-pressure',rm.pin(r),'pressure','default','0');value={'resultSet':snapshot()};value['resultSet']['rows'][0]['pressure']=None;result,proof=fp.resolve(state,s,value);self.assertEqual(result,{'typedValue':'0'});self.assertTrue(proof['defaultUsed']);s['recordField'].update(nullPolicy='reject',defaultValue=None);self.assertRaisesRegex(ValueError,'null-input',fp.resolve,state,s,value)
 def test_quality_and_unknown_fields_preserved(self):
  s=samples();snapshot(s)['quality']='uncertain';p=run(s=s);self.assertEqual(p['quality'],'uncertain');proof=next(t['detail'] for m in p['members'] for t in m['report']['trace'] if t['stage']=='record-field-select');self.assertEqual(proof['preservedFields'][0]['fields']['unmapped_note'],'원본 보존');snapshot(s)['quality']='bad';self.assertIsNone(run(s=s)['result'])
 def test_static_contract_mismatches(self):
  for change,expected in [('pin','record-pin'),('unit','signature'),('type','signature'),('stage','signature'),('equipment','equipment'),('provider','provider'),('field','field-missing'),('default','null-policy')]:
   state=w();s=source(state)
   if change=='pin':s['recordField']['recordMappingRef']['sha256']='0'*64
   if change=='unit':s['unit']['code']='Pa'
   if change=='type':s['rawRepresentation']['valueType']='Double'
   if change=='stage':s['inputStage']='already-engineered'
   if change=='equipment':s['equipmentInstanceId']='record-line-a'
   if change=='provider':s['access']['providerRef']='other-db'
   if change=='field':s['recordField']['fieldId']='missing'
   if change=='default':s['recordField'].update(nullPolicy='default',defaultValue='0')
   self.assertRaisesRegex(ValueError,expected,rf.check_workspace,state)
 def test_array_requires_explicit_object_selection(self):
  state=w();self.assertRaisesRegex(ValueError,'object-required',rf.create,state,'array-field',rm.pin(state['recordMappings'][0]),'target')
 def test_no_write_or_sql_execution_metadata(self):
  state=w();s=source(state);self.assertEqual(s['access']['expressionLanguage'],'none');self.assertIsNone(s['access']['expression']);s['accessMode']='write';self.assertRaisesRegex(ValueError,'schema',rf.check_workspace,state)
 def test_preview_never_connects(self):
  with patch.object(socket,'socket',side_effect=AssertionError('network')),patch.object(sqlite3,'connect',side_effect=AssertionError('SQL')):self.assertEqual(run()['result'],load('oracle.json'))
 def test_template_reuses_all_sources_and_record_pin(self):
  state=w();a=state['templateApplications'][0];t=next(t for t in state['mappingTemplates'] if mt.pin(t)==a['templateRef']);self.assertEqual(mt.materialize(t,a),a['generated']);self.assertEqual(next(s['recordField'] for s in a['sourceSnapshots'] if 'recordField' in s),source()['recordField']);self.assertEqual(len(a['bindings']),5)
 def test_plan_and_atomic_save_CAS_and_reopen(self):
  with tempfile.TemporaryDirectory() as tmp:
   st=server.Store(Path(tmp)/'editor.sqlite3');st.migrate(0,{});st.save(1,load('before.json'));before=st.read();plan=ma.compose(st,load('request.json'),server.Conflict,server.build_package);self.assertEqual(st.read(),before);bad=dict(revision=2,draft=plan['draft'],planSha256='0'*64);self.assertRaisesRegex(ValueError,'changed',ma.apply,st,bad,server.Conflict,server.build_package);good=dict(bad,planSha256=plan['planSha256']);r=ma.apply(st,good,server.Conflict,server.build_package);self.assertEqual(r['saved']['revision'],3);self.assertEqual(server.Store(st.path).read(),st.read());self.assertRaises(server.Conflict,ma.apply,st,good,server.Conflict,server.build_package)
 def test_source_pin_cannot_be_changed_or_downgraded(self):
  with tempfile.TemporaryDirectory() as tmp:
   st=server.Store(Path(tmp)/'editor.sqlite3');st.migrate(0,{});st.save(1,w());before=st.read();after=copy.deepcopy(before['workspace']);source(after)['rawAddressText']='renamed';self.assertRaises(ValueError,st.save,2,after);self.assertEqual(st.read(),before)
  old=source();new=copy.deepcopy(old);new.pop('recordField');new['schemaVersion']='2.7.0';self.assertRaisesRegex(ValueError,'history-conflict',rf.history,[new],[old])
 def test_legacy_read_no_migration(self):
  with tempfile.TemporaryDirectory() as tmp:
   st=server.Store(Path(tmp)/'editor.sqlite3');st.migrate(0,{});st.save(1,load('before.json'))
   with st.connect() as c:before=list(c.iterdump())
   st.read();ta.listing(st)
   with st.connect() as c:self.assertEqual(before,list(c.iterdump()))
 def test_self_contained_publication_closure(self):
  with tempfile.TemporaryDirectory() as tmp:
   folder=Path(tmp)/'bundle';_,_,errors=publication.build(w(),folder,'combined-scope','combined-line','proposer',None,['reuse-combined-pump-mapping'],False,server.build_package);self.assertEqual(errors,[]);p=server.contracts.load(folder/'proposal.json');self.assertEqual(p['schemaVersion'],'2.21.0');kinds={e['kind'] for e in p['files']};self.assertIn('record-mapping',kinds);self.assertIn('template-application',kinds);self.assertNotIn('virtual-result-set',kinds);self.assertNotIn('write-definition',kinds)
 def test_standalone_cli_and_mirrors(self):
  p=subprocess.run([sys.executable,'-B',str(R/'scripts/p3a_contracts.py'),'--package',str(F/'bundle'),'--deny-network'],capture_output=True,text=True,timeout=120);self.assertEqual(p.returncode,0,p.stdout+p.stderr)
  for p in (R/'contracts').rglob('*.schema.json'):self.assertEqual(p.read_bytes(),(R.parent/'bifrost/core/src/main/resources/mapping-contracts'/p.relative_to(R/'contracts')).read_bytes())
 def test_old_envelope_fails_closed(self):
  with tempfile.TemporaryDirectory() as tmp:
   import shutil
   folder=Path(tmp)/'bundle';shutil.copytree(F/'bundle',folder);p=server.contracts.load(folder/'proposal.json');p['schemaVersion']='2.20.0';server.contracts.save(folder/'proposal.json',p);errors,_=server.v2.p3.validate_package(folder);self.assertTrue(any(e['ruleCode']=='record-field.envelope' for e in errors))
 def test_preserved_files(self):
  pins=server.contracts.load(R/'docs/verification/mixed-objects-baseline-pins.json')
  for path,h in pins.items():self.assertEqual(hashlib.sha256((R.parent/path).read_bytes()).hexdigest(),h,path)
 def test_graph_combines_PLC_and_record(self):
  state=w();s=source(state);ev=state['sources'][0]['definition']['evidenceRefs']+s['evidenceRefs'];graph=copy.deepcopy(server.contracts.load(R/'fixtures/p4b/workspace.json')['graphs'][0]);graph.update(id='combined-difference',equipmentInstanceId='record-line-b');node=graph['nodes'][0];node['inputs']['right']['sourceRef']=dict(id=s['id'],version=s['version']);node['evidenceRefs']=ev;state['graphs'].append(graph);model=copy.deepcopy(state['semantics'][-1]);model['id']='combined-delta-model';model['members']=model['members'][:1];model['members'][0].update(memberId='difference',semanticId='urn:tyr:concept:combined.difference');state['semantics'].append(model);target=copy.deepcopy(state['targets'][0]);target.update(id='combined-delta-target',semanticDefinitionRef=dict(id=model['id'],version=model['version']));state['targets'].append(target);mapping=dict(kind='mapping-set',schemaVersion='2.3.0',id='combined-delta-mapping',version='1.0.0',equipmentInstanceId='record-line-b',targetInstanceRef=dict(id=target['id'],version=target['version']),mappings=[dict(mappingId='delta',memberPath=[dict(kind='member',memberId='difference')],valueRef=dict(kind='graph',graphRef=dict(id=graph['id'],version=graph['version']),nodeId=node['nodeId']),transform=[dict(op='linear',factor='0.1',offset='0'),dict(op='cast',to='Double',rounding='half-even',overflow='error')],outputUnit=dict(status='known',code='kPa'),invalidValuePolicy='bad-quality',evidenceRefs=ev)]);state['mappings'].append(mapping);server.check_state(state);p=preview.run(state,mapping['id'],'delta',samples(),3);self.assertEqual(p['result']['value'],'25')
 def test_time_quality_metadata_cannot_be_forged(self):
  state=w();mapping=copy.deepcopy(state['mappings'][0]);state.pop('templateApplications');state.pop('mappingTemplates');state['mappingTemplates']=w()['mappingTemplates'][:-1];mapping['schemaVersion']='2.3.0';policy=dict(timestampBasis='source',maxAgeMs=1000,maxSkewMs=100,uncertainInput='propagate',missingInput='reject',badInput='propagate',assembly='latest')
  for b in mapping['mappings']:b['temporalPolicy']=policy
  state['mappings']=[mapping];s={k:dict(value=v,quality='good',sourceTimestamp='2026-10-18T00:00:00Z',serverTimestamp='2026-10-18T00:00:00Z',sequence=None) for k,v in samples().items()};e=dict(at='2026-10-18T00:00:00.500Z',triggerSequence=None);p=run(state,s,e);self.assertIsNotNone(p['result']);s[source()['id']]['sourceTimestamp']='2026-10-18T09:00:00+09:00';s[source()['id']]['serverTimestamp']='2026-10-18T00:00:00+00:00';self.assertIsNotNone(run(state,s,e)['result']);s[source()['id']]['sourceTimestamp']='2026-10-18T00:00:00.400Z';p=run(state,s,e);self.assertTrue(any(i['code']=='record-field.envelope-mismatch' for i in p['issues']));self.assertIsNone(p['result'])
if __name__=='__main__':unittest.main()
