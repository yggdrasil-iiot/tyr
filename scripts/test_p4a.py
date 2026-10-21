
"""P4-A independent import, preservation, authoring and SQLite/API acceptance."""
import argparse,base64,copy,io,json,sys,tempfile,threading,unittest,zipfile
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'backend'),str(R/'scripts')]
import server,import_files as imp,sample_quality
F=R/'fixtures/p4a'
def load(n):return server.contracts.load(F/(n+'.json'))
def parsed(name='settings',mutate=None):
 q=load(name+'-request')
 if mutate:
  doc=json.loads(base64.b64decode(q['bytesBase64']));mutate(doc);q['bytesBase64']=base64.b64encode(json.dumps(doc).encode()).decode()
 return imp.parse(q,load('context'))
def byid(b,id):return next(o for o in b['observations'] if isinstance(o['raw'],dict) and o['raw'].get('id')==id)
class Contracts(unittest.TestCase):
 def test_old_schema_hashes(self):
  for p,h in server.contracts.load(R/'docs/verification/p3f-validation.json')['sha256'].items():
   if p.startswith('contracts/'):self.assertEqual(server.contracts.hashed(R/p),h,p)
 def test_meta(self):
  from jsonschema import Draft202012Validator
  for p in (R/'contracts/2.6.0').glob('*.json'):Draft202012Validator.check_schema(server.contracts.load(p))
 def test_import_to_canonical_preview(self):
  import preview
  w=load('settings-workspace');src=w['sources'][0]['definition'];src['status']='ready'
  prior=server.contracts.load(R/'fixtures/p3c/workspace.json')
  sem=copy.deepcopy(prior['semantics'][0]);sem['id']='import-speed-model';sem['members']=sem['members'][:1];sem['members'][0].update(memberId='speed',semanticId='urn:tyr:concept:motor.actual-speed',name='실제 속도',unit={'status':'known','code':'rpm'},range=None)
  target=copy.deepcopy(prior['targets'][0]);target.update(id='import-motor',equipmentInstanceId='import-line',semanticDefinitionRef={'id':sem['id'],'version':sem['version']},evidenceRefs=src['evidenceRefs'])
  mapping=copy.deepcopy(prior['mappings'][0]);mapping.update(id='import-speed-mapping',equipmentInstanceId='import-line',targetInstanceRef={'id':target['id'],'version':target['version']});mapping['mappings']=mapping['mappings'][:1]
  binding=mapping['mappings'][0];binding.update(mappingId='speed-binding',valueRef={'kind':'source','sourceRef':{'id':src['id'],'version':src['version']}},memberPath=[{'kind':'member','memberId':'speed'}],evidenceRefs=src['evidenceRefs'],outputUnit={'status':'known','code':'rpm'})
  w['semantics']=[sem];w['targets']=[target];w['mappings']=[mapping];server.check_state(w)
  r=preview.run(w,'import-speed-mapping','speed-binding',{src['id']:{'typedValue':'1500'}},2);self.assertEqual(r['result']['value'],'1500');self.assertEqual(r['result']['unit'],{'status':'known','code':'rpm'});self.assertEqual(r['quality'],'good')
 def test_missing_stage_not_confirmed(self):
  b=parsed(mutate=lambda d:d['records'][0].pop('stage'));o=byid(b,'speed-ab');self.assertEqual(o['draft']['inputStage'],'raw');self.assertIn('source.stage-unconfirmed',o['issues'])
 def test_tampered_export_raw_detected(self):
  w=load('settings-workspace')
  with tempfile.TemporaryDirectory() as t:
   folder=Path(t);server.build_package(w,folder);(folder/'data/import-0.json').write_bytes(b'changed')
   errors,_=server.v2.p3.validate_package(folder);self.assertIn('evidence.digest',{e['ruleCode'] for e in errors});self.assertIn('import.evidence-mismatch',{e['ruleCode'] for e in errors})
 def test_four_profiles(self):
  b=parsed();self.assertEqual(len(b['observations']),14);drafts=[o['draft'] for o in b['observations'] if o['draft']];self.assertEqual(len(drafts),9);self.assertEqual({d['accessProfileRef'] for d in drafts},set(server.contracts.PROFILES));self.assertTrue(all(d['status']=='draft' for d in drafts))
 def test_alias_cycles(self):
  b=parsed()
  for id in ('cycle-a','cycle-b'):self.assertIn('alias.cycle',byid(b,id)['issues']);self.assertIsNone(byid(b,id)['draft'])
 def test_missing_alias(self):self.assertIn('alias.missing-target',byid(parsed(),'missing-alias')['issues'])
 def test_opaque_preserved(self):
  b=parsed();self.assertEqual(byid(b,'opaque')['raw']['vendorExpression'],'PLC_POINTER()');self.assertEqual(b['observations'][-1]['raw']['value'],{'custom':'must preserve exactly'})
 def test_xlsx_formula_no_cached_value(self):
  b=parsed('excel');o=byid(b,'formula');self.assertIsNone(o['draft']);self.assertIn('xlsx.formula',o['issues']);self.assertEqual(o['originalColumns']['주소'],'3');self.assertEqual(imp.xlsx(base64.b64decode(b['bytesBase64']))[1][('메모리맵','D6')]['formula'],'SUM(1,2)')
 def test_xlsx_original_columns_locator(self):
  o=byid(parsed('excel'),'tank-pv');self.assertEqual(o['originalColumns']['주소'],'D3000');self.assertEqual(o['locator'],{'kind':'xlsx-cell','sheet':'메모리맵','cell':'A2'})
 def test_alias_chain_locators(self):
  b=parsed();o=byid(b,'pump-alias-chain');self.assertEqual(o['draft']['access']['addressIndex'],2050);self.assertEqual([x['pointer'] for x in o['derivation']],['/records/6','/records/5','/records/4'])
 def test_template_missing_param(self):
  b=parsed(mutate=lambda d:d['records'][4].pop('base'));self.assertIsNone(byid(b,'pump')['draft']);self.assertNotIn('pump-0',{o['raw'].get('id') for o in b['observations'] if isinstance(o['raw'],dict)})
 def test_unknown_placeholder(self):
  b=parsed(mutate=lambda d:d['records'][4].update(address='D{runtime}'));self.assertIn('template.parameter',byid(b,'pump')['issues'])
 def test_template_override_atomic(self):
  b=parsed(mutate=lambda d:d['records'][4].update(overrides={'1':{'vendorWrite':'x'}}));self.assertIsNone(byid(b,'pump')['draft'])
 def test_duplicate_ids_not_adopted(self):
  b=parsed(mutate=lambda d:d['records'].append(copy.deepcopy(d['records'][0])));self.assertIsNone(byid(b,'speed-ab')['draft']);self.assertIn('record.duplicate-id',byid(b,'speed-ab')['issues'])
 def test_alias_to_unknown_never_adopted(self):
  b=parsed(mutate=lambda d:d['records'].append({'id':'bad-alias','kind':'alias','target':'opaque'}));self.assertIsNone(byid(b,'bad-alias')['draft'])
 def test_unknown_order_preserved(self):
  b=parsed(mutate=lambda d:d['records'][3].pop('byteOrder'));o=byid(b,'pressure-mel');self.assertIsNotNone(o['draft']);self.assertIsNone(o['draft']['rawRepresentation']['byteOrder']);self.assertIn('source.incomplete',o['issues'])
 def test_ambiguous_connection(self):
  w=load('context');w['connections'].append({**w['connections'][0],'id':'another'});b=imp.parse(load('settings-request'),w);self.assertIsNone(byid(b,'speed-ab')['draft'])
 def test_connection_snapshot_survives_addition(self):
  w=load('settings-workspace');w['connections'].append({**w['connections'][0],'id':'another'});server.check_state(w)
 def test_tampered_provenance(self):
  for field,value in [('sha256','0'*64),('filename','../escape')]:
   w=load('settings-workspace');w['imports'][0][field]=value
   with self.assertRaises(server.Invalid):server.check_state(w)
 def test_tampered_observation(self):
  w=load('settings-workspace');w['imports'][0]['observations'][0]['draft']['rawAddressText']='Other'
  with self.assertRaises(server.Invalid):server.check_state(w)
 def test_unresolved_adoption_blocked(self):
  b=parsed()
  with self.assertRaises(ValueError):imp.adopt(load('context'),b,[byid(b,'cycle-a')['id']])
 def test_source_reference_required(self):
  w=load('settings-workspace');w['sources'][0]['definition']['evidenceRefs']=[]
  with self.assertRaises(server.Invalid):server.check_state(w)
 def test_export_original_bytes_and_observations(self):
  for name,extension in [('settings','json'),('excel','xlsx')]:
   w=load(name+'-workspace');server.check_state(w)
   with tempfile.TemporaryDirectory() as t:
    folder=Path(t);server.build_package(w,folder);self.assertEqual((folder/('data/import-0.'+extension)).read_bytes(),base64.b64decode(w['imports'][0]['bytesBase64']))
    p=server.contracts.load(folder/'proposal.json');self.assertEqual(p['schemaVersion'],'2.6.0');self.assertEqual(sum(e['kind']=='source-observation' for e in p['files']),len(w['imports'][0]['observations']))
    errors,_=server.v2.p3.validate_package(folder);self.assertEqual({e['ruleCode'] for e in errors},{'source.not-ready','import.unresolved'})
 def test_raw_only_invalid_file_preserved(self):
  q=load('settings-request');q['bytesBase64']=base64.b64encode(b'not valid JSON\x00').decode();b=imp.parse(q,load('context'));self.assertIn('fileIssue',b);w=imp.adopt(load('context'),b,[]);server.check_state(w);self.assertIn('import.unresolved',{e['ruleCode'] for e in server.findings_for(w)})
 def test_pure_repeat(self):
  q=load('settings-request');w=load('context');before=copy.deepcopy((q,w));self.assertEqual(imp.parse(q,w),imp.parse(q,w));self.assertEqual(before,(q,w))
 def test_column_map_collision(self):
  q=load('excel-request');q['columnMap']['別名']='id'
  with self.assertRaises(ValueError):imp.parse(q,load('context'))
 def test_duplicate_json_key(self):
  q=load('settings-request');q['bytesBase64']=base64.b64encode(b'{"format":"tyr-config-v1","format":"bad","records":[]}').decode();self.assertIn('fileIssue',imp.parse(q,load('context')))
 def test_row_expansion_limit(self):
  q=load('settings-request');doc={'format':'tyr-config-v1','records':[{'id':'t'+str(i),'kind':'template','base':0,'stride':1,'count':64,'address':'D{offset}'} for i in range(5)]};q['bytesBase64']=base64.b64encode(json.dumps(doc).encode()).decode()
  with self.assertRaises(ValueError):imp.parse(q,load('context'))
 def test_xlsx_external_not_followed(self):
  q=load('excel-request');raw=base64.b64decode(q['bytesBase64']);out=io.BytesIO()
  with zipfile.ZipFile(io.BytesIO(raw)) as a,zipfile.ZipFile(out,'w') as z:
   for name in a.namelist():
    data=a.read(name)
    if name=='xl/_rels/workbook.xml.rels':data=data.replace(b'Target="worksheets/sheet1.xml"',b'Target="https://invalid.example/private" TargetMode="External"')
    z.writestr(name,data)
  q['bytesBase64']=base64.b64encode(out.getvalue()).decode();b=imp.parse(q,load('context'));self.assertEqual(b['fileIssue'],'xlsx.external');self.assertEqual(b['observations'],[])
 def test_xlsx_duplicate_cell(self):
  q=load('excel-request');raw=base64.b64decode(q['bytesBase64']);out=io.BytesIO()
  with zipfile.ZipFile(io.BytesIO(raw)) as a,zipfile.ZipFile(out,'w') as z:
   for name in a.namelist():
    data=a.read(name)
    if name.endswith('sheet1.xml'):data=data.replace(b'r="B2"',b'r="A2"')
    z.writestr(name,data)
  q['bytesBase64']=base64.b64encode(out.getvalue()).decode();self.assertEqual(imp.parse(q,load('context'))['fileIssue'],'xlsx.duplicate-cell')
class API(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.store=server.Store(Path(self.tmp.name)/'editor.sqlite3');self.store.migrate(0,{});self.store.save(1,load('context'));self.http=server.make_server(self.store,0);self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()
 def tearDown(self):self.http.shutdown();self.http.server_close();self.thread.join();self.tmp.cleanup()
 def request(self,path,body,origin=None):
  h={'Content-Type':'application/json','X-Tyr-Editor':'1'}
  if origin:h['Origin']=origin
  return urlopen(Request('http://127.0.0.1:'+str(self.http.server_port)+path,data=json.dumps(body).encode(),headers=h,method='POST'))
 def test_preview_readonly(self):
  before=self.store.read();h=server.contracts.hashed(self.store.path)
  with self.request('/api/import-preview',{'revision':2,'request':load('settings-request')}) as r:self.assertFalse(json.load(r)['persisted'])
  self.assertEqual(before,self.store.read());self.assertEqual(h,server.contracts.hashed(self.store.path))
 def test_apply_reopen_and_byte_roundtrip(self):
  for name in ('settings','excel'):
   rev=self.store.read()['revision'];b=load(name+'-batch');ids=[o['id'] for o in b['observations'] if o['draft'] and not o['issues']]
   with self.request('/api/import-apply',{'revision':rev,'request':load(name+'-request'),'selected':ids}) as r:self.assertEqual(json.load(r)['revision'],rev+1)
  w=server.Store(self.store.path).read()['workspace'];self.assertEqual(len(w['sources']),13);self.assertEqual(len(w['imports']),2)
  for b in w['imports']:self.assertEqual(b,load(b['id']+'-batch'))
 def test_stale_import_no_side_effect(self):
  before=self.store.read()
  with self.assertRaises(HTTPError) as e:self.request('/api/import-apply',{'revision':1,'request':load('settings-request'),'selected':[]})
  self.assertEqual(e.exception.code,409);self.assertEqual(before,self.store.read())
 def test_duplicate_batch_atomic(self):
  self.store.save(2,load('settings-workspace'));before=self.store.read()
  with self.assertRaises(HTTPError) as e:self.request('/api/import-apply',{'revision':3,'request':load('settings-request'),'selected':[]})
  self.assertEqual(e.exception.code,422);self.assertEqual(before,self.store.read())
 def test_invalid_selected_atomic(self):
  before=self.store.read()
  with self.assertRaises(HTTPError) as e:self.request('/api/import-apply',{'revision':2,'request':load('settings-request'),'selected':['row-999']})
  self.assertEqual(e.exception.code,422);self.assertEqual(before,self.store.read())
 def test_origin_protection(self):
  with self.assertRaises(HTTPError) as e:self.request('/api/import-preview',{'revision':2,'request':load('settings-request')},'https://evil.invalid')
  self.assertEqual(e.exception.code,403)
 def test_legacy_sqlite_unchanged_on_open(self):
  with tempfile.TemporaryDirectory() as t:
   st=server.Store(Path(t)/'old.sqlite3');before=st.read();server.Store(st.path);self.assertEqual(st.read(),before);self.assertNotIn('imports',before['workspace'])
 def test_edited_source_preserves_raw_evidence(self):
  self.store.save(2,load('settings-workspace'));w=self.store.read()['workspace'];w['sources'][0]['note']='Reviewed original label and symbol';w['sources'][0]['definition']['status']='ready';self.store.save(3,w);self.assertEqual(server.Store(self.store.path).read()['workspace'],w)
ORACLES=[('settings','speed-ab','Motor.ActualSpeed','symbol'),('settings','pressure-ua','Line.Pressure','opcua-node'),('settings','pressure-db','DB10.DBB64','db-offset'),('settings','pump-0','D2000','device-register'),('settings','pump-1','D2050','device-register'),('settings','pump-2','D2020','device-register'),('settings','pump-alias-chain','D2050','device-register'),('excel','tank-0','D3100','device-register'),('excel','tank-1','D3190','device-register'),('excel','tank-alias','D3190','device-register')]
def oracle(name,id,address,kind):
 def test(self):
  o=byid(parsed(name),id);self.assertEqual(o['draft']['rawAddressText'],address);self.assertEqual(o['draft']['access']['kind'],kind);self.assertEqual(o['issues'],[])
 return test
for name,id,a,k in ORACLES:setattr(Contracts,'test_oracle_'+name+'_'+id.replace('-','_'),oracle(name,id,a,k))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--report',type=Path);a=p.parse_args();r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
 if a.report:
  files=[*(R/'fixtures/p4a').glob('*'),*(R/'contracts').rglob('*.json'),*(R/'backend').glob('*.py'),*(R/'frontend').glob('*'),R/'scripts/import_files.py',R/'scripts/p3a_contracts.py',Path(__file__)]
  server.contracts.save(a.report,{'total':r.testsRun,'passed':r.testsRun-len(r.failures)-len(r.errors),'oracleCases':len(ORACLES),'failures':[str(x) for x in r.failures],'errors':[str(x) for x in r.errors],'sha256':{str(p.relative_to(R)).replace(chr(92),'/'):server.contracts.hashed(p) for p in files if p.is_file()}})
 sys.exit(not r.wasSuccessful())
