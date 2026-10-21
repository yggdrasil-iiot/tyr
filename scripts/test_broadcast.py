"""Independent offline value/identity/row/frame/storage and backwards-compatibility oracles."""
import sys,copy,json,tempfile,unittest,sqlite3,socket
from pathlib import Path
from unittest.mock import patch
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'backend'),str(R/'scripts')]
import server,broadcast_preview as bp,broadcast_authoring as ba,record_authoring as ra,record_mappings as rm,mapping_templates as mt,publication
F=R/'fixtures/broadcast'
def load(n):return server.contracts.load(F/n)
def w():return load('workspace.json')
def run(state=None,snap=None,samples=None,at='2026-10-18T00:00:00.500Z'):
 return bp.run(w() if state is None else state,'broadcast-pumps','1.0.0',load('snapshot.json') if snap is None else snap,load('common-samples.json') if samples is None else samples,3,at)
def codes(p):return {i['code'] for i in p['issues']}
def alter(policy='reject-all'):
 state=w();state['recordMappings'][-1]['rowErrorPolicy']=policy;return state
class Broadcast(unittest.TestCase):
 def test_value_oracle_common_values_and_distinct_rows(self):
  p=run();self.assertEqual(p['result'],[dict(actual='120',target='90',baseline='100',external='101',line_code='LINE-A'),dict(actual='120',target='95',baseline='100',external='101',line_code='LINE-A')]);self.assertEqual(p['quality'],'good');self.assertEqual(p['commonInputSha256'],p['records'][0]['commonInputSha256']);self.assertEqual(p['records'][0]['commonInputSha256'],p['records'][1]['commonInputSha256']);self.assertFalse(p['atomicSnapshot'])
 def test_reordered_input_keeps_canonical_identity_order(self):
  s=load('snapshot.json');s['rows'].reverse();p=run(snap=s);self.assertEqual(p['result'],run()['result']);self.assertEqual(p['records'][0]['identity']['key'],['A-001']);self.assertEqual(p['records'][0]['identity']['inputRowIndex'],0)
 def test_zero_empty_and_reject(self):
  s=load('snapshot.json');s['rows']=[];self.assertEqual(run(snap=s)['result'],[]);state=w();state['recordMappings'][-1]['output']['zeroPolicy']='reject';self.assertIn('record.zero-rows',codes(run(state,s)))
 def test_bad_common_even_zero_rows_is_global(self):
  s=load('snapshot.json');s['rows']=[];v=load('common-samples.json');v['mixed-plc-pressure']['quality']='bad';self.assertIsNone(run(alter('omit-invalid'),s,v)['result'])
 def test_missing_common_returns_diagnostic(self):
  v=load('common-samples.json');del v['mixed-plc-pressure'];p=run(samples=v);self.assertIsNone(p['result']);self.assertIn('sample.missing',codes(p))
 def test_extra_common_input_rejected(self):
  v=load('common-samples.json');v['unused']=v['mixed-plc-pressure'];self.assertRaisesRegex(ValueError,'broadcast.common-inputs',run,samples=v)
 def test_bad_decode_is_global_despite_omit(self):
  v=load('common-samples.json');v['mixed-plc-pressure']['value']['bytesHex']='ff';p=run(alter('omit-invalid'),samples=v);self.assertIsNone(p['result']);self.assertTrue(any(i.get('scope')=='common' and i['severity']=='error' for i in p['issues']))
 def test_row_bad_type_reject_all(self):
  s=load('snapshot.json');s['rows'][1]['target']='oops';p=run(snap=s);self.assertIsNone(p['result']);self.assertEqual(len(p['partialResults']),1);self.assertEqual(p['omittedRecords'][0]['key'],['A-001'])
 def test_row_bad_type_omit_explicitly(self):
  s=load('snapshot.json');s['rows'][1]['target']='oops';p=run(alter('omit-invalid'),s);self.assertTrue(p['valid']);self.assertEqual(p['quality'],'uncertain');self.assertEqual(len(p['result']),1);self.assertTrue(p['records'][0]['issues'])
 def test_required_missing_is_row_error(self):
  s=load('snapshot.json');del s['rows'][0]['target'];p=run(alter('omit-invalid'),s);self.assertEqual(len(p['result']),1);self.assertIn('record.required-field',codes(p))
 def test_duplicate_key_never_omitted(self):
  s=load('snapshot.json');s['rows'].append(copy.deepcopy(s['rows'][0]));p=run(alter('omit-invalid'),s);self.assertIsNone(p['result']);self.assertIn('record.duplicate-key',codes(p))
 def test_invalid_key_never_omitted(self):
  s=load('snapshot.json');s['rows'][1]['asset']='';p=run(alter('omit-invalid'),s);self.assertIsNone(p['result']);self.assertIn('record.key-value',codes(p))
 def test_max_rows_never_truncates(self):
  state=alter('omit-invalid');state['recordMappings'][-1]['output']['maxRows']=1;p=run(state);self.assertIsNone(p['result']);self.assertIn('record.max-rows',codes(p))
 def test_stale_common_and_db_snapshot(self):
  p=run(at='2026-10-18T00:00:02Z');self.assertIsNone(p['result']);self.assertIn('time.stale-input',codes(p))
 def test_skew_rejects_all_rows(self):
  v=load('common-samples.json');v['mixed-plc-pressure']['sourceTimestamp']='2026-10-17T23:59:59.400Z';p=run(samples=v,at='2026-10-18T00:00:00.100Z');self.assertIn('time.skew-exceeded',codes(p))
 def test_future_and_bad_db(self):
  s=load('snapshot.json');s['quality']='bad';self.assertIn('quality.bad-input',codes(run(snap=s)));s['quality']='good';s['capturedAt']='2026-10-19T00:00:00Z';self.assertIn('time.future-input',codes(run(snap=s)))
 def test_uncertain_propagation_and_reject(self):
  v=load('common-samples.json');v['mixed-plc-pressure']['quality']='uncertain';self.assertEqual(run(samples=v)['quality'],'uncertain');state=w();state['recordMappings'][-1]['commonPolicy']['uncertainInput']='reject';self.assertIsNone(run(state,samples=v)['result'])
 def test_nullable_default_per_row(self):
  state=w();r=state['recordMappings'][-1];r['resultSchema']['version']='1.0.1';next(f for f in r['resultSchema']['fields'] if f['fieldId']=='target')['nullable']=True;r['bindings'][0].update(nullPolicy='default',defaultValue='800');s=load('snapshot.json');s['resultSetRef']=rm.pin(r['resultSchema']);s['rows'][0]['target']=None;p=run(state,s);self.assertEqual(p['result'][1]['target'],'80');self.assertIn('record.default-used',codes(p));self.assertEqual(p['quality'],'uncertain')
 def test_unknown_fields_preserved(self):
  s=load('snapshot.json');s['rows'][0]['provider_extra']='raw';p=run(snap=s);self.assertEqual(p['preservedFields'][0]['fields']['provider_extra'],'raw')
 def test_no_runtime_io_and_no_mutation(self):
  state=w();s=load('snapshot.json');v=load('common-samples.json');before=copy.deepcopy([state,s,v])
  with patch.object(socket,'socket',side_effect=AssertionError('socket')),patch.object(sqlite3,'connect',side_effect=AssertionError('db')):p=run(state,s,v)
  self.assertTrue(p['valid']);self.assertEqual(before,[state,s,v])
 def test_source_definition_pin_and_duplicate_slot(self):
  state=w();state['sources'][0]['definition']['rawAddressText']='D999';self.assertRaisesRegex(ValueError,'broadcast.source-pin-mismatch',rm.check_workspace,state);state=w();r=state['recordMappings'][-1];r['commonBindings'][0]['slotId']=r['bindings'][0]['slotId'];self.assertRaisesRegex(ValueError,'record.slot-bindings',rm.check_workspace,state)
 def test_static_projection_and_package(self):
  state=w();self.assertEqual(rm.compile(state['recordMappings'][-1],state['mappingTemplates'][-1]),load('static-projection.json'));self.assertEqual(server.findings_for(state),[])
 def test_legacy_only_preview_cannot_drop_common(self):
  import record_preview as rp
  self.assertRaisesRegex(ValueError,'broadcast.use-broadcast-preview',rp.run,w(),'broadcast-pumps','1.0.0',load('snapshot.json'),3)
 def test_sqlite_plan_CAS_immutable_reopen_and_scenario(self):
  with tempfile.TemporaryDirectory() as tmp:
   st=server.Store(Path(tmp)/'editor.sqlite3');st.migrate(0,{});st.save(1,load('before.json'));before=st.read();p=ba.compose(st,load('request.json'),server.Conflict);self.assertEqual(st.read(),before);req=dict(revision=2,draft=p['draft'],planSha256=p['planSha256']);bad=dict(req,planSha256='0'*64);self.assertRaises(ValueError,ra.apply,st,bad,server.Conflict);saved=ra.apply(st,req,server.Conflict);self.assertEqual(saved['saved']['revision'],3);self.assertRaises(server.Conflict,ra.apply,st,req,server.Conflict);r=saved['record'];scene=dict(revision=3,id='array-scene',scenarioRevision=0,mappingRef=rm.pin(r),snapshot=load('snapshot.json'),commonSamples=load('common-samples.json'),evaluatedAt='2026-10-18T00:00:00.500Z');before=st.read();ba.save_scenario(st,scene,server.Conflict);self.assertEqual(st.read(),before);self.assertRaises(server.Conflict,ba.save_scenario,st,scene,server.Conflict);self.assertEqual(ra.scenarios(server.Store(st.path))[0]['commonSamples'],scene['commonSamples']);state=st.read()['workspace'];state['recordMappings'][-1]['rowErrorPolicy']='omit-invalid';self.assertRaisesRegex(ValueError,'record.history-immutable',st.save,3,state)
 def test_template_reuse_new_array_version(self):
  with tempfile.TemporaryDirectory() as tmp:
   st=server.Store(Path(tmp)/'editor.sqlite3');st.migrate(0,{});st.save(1,w());req=load('request.json');req['revision']=2;req['id']='broadcast-copy';req['templateRef']=w()['recordMappings'][-1]['templateRef'];req['memberBindings']=[];req['slotBindings']=[dict(slotId=b['slotId'],input=dict(kind='field',fieldId=b['fieldId'],nullPolicy=b['nullPolicy'],defaultValue=b['defaultValue'])) for b in w()['recordMappings'][-1]['bindings']]+[dict(slotId=b['slotId'],input=dict(kind='common',sourceRef={k:b['sourceRef'][k] for k in ('id','version')})) for b in w()['recordMappings'][-1]['commonBindings']];p=ba.compose(st,req,server.Conflict);self.assertIsNone(p['draft']['template']);self.assertTrue(p['valid'])
 def test_row_cast_loss_is_visible(self):
  s=load('snapshot.json');s['rows'][0]['target']='951';p=run(snap=s);self.assertEqual(p['quality'],'uncertain');self.assertTrue(any(m['preview']['losses'] for row in p['records'] for m in row['members']))
 def test_common_transform_error_blocks_even_zero_rows(self):
  state=w();t=state['mappingTemplates'][-1];t['mapping']['mappings'][0]['transform'][0]['factor']='1'+'0'*256;state['recordMappings'][-1]['templateRef']=mt.pin(t);s=load('snapshot.json');s['rows']=[];p=run(state,s);self.assertIsNone(p['result']);self.assertTrue(any(i.get('scope')=='common-transform' and i['severity']=='error' for i in p['issues']))
 def test_template_graph_combines_row_and_common(self):
  state=w();t=state['mappingTemplates'][-1];g=server.contracts.load(R/'fixtures/p4b/workspace.json')['graphs'][0];g=mt.clean(g);g['equipmentInstanceId']='record-line-b';field=next(b for b in t['slots'] if b['slotId']==state['recordMappings'][-1]['bindings'][0]['slotId']);g['nodes'][0]['inputs']['right']['sourceRef']=field['sourceRef'];t['graphs']=[g];t['mapping']['mappings'][0]['valueRef']=dict(kind='graph',graphRef=dict(id=g['id'],version=g['version']),nodeId='difference');state['recordMappings'][-1]['templateRef']=mt.pin(t);p=run(state);self.assertEqual([row['actual'] for row in p['result']],['30','25'])
 def test_persisted_negative_and_loss_fixtures(self):
  for case in load('cases.json'):
   with self.subTest(case=case['id']):
    p=run(alter(case['rowErrorPolicy']),case['snapshot'],case['commonSamples']);self.assertEqual({k:p[k] for k in case['expected']},case['expected'])
 def test_baseline_bytes_preserved(self):
  import hashlib
  pins=server.contracts.load(R/'docs/verification/broadcast-baseline-pins.json');self.assertEqual([n for n,h in pins.items() if hashlib.sha256((R/n).read_bytes()).hexdigest()!=h],[])
if __name__=='__main__':unittest.main(verbosity=2)
