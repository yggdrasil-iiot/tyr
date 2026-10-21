
"""P4-B mixed definitions, forward reads and separate write metadata acceptance."""
import argparse,copy,json,sys,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request,urlopen
from urllib.error import HTTPError
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'backend'),str(R/'scripts')]
import server,preview,sample_quality
F=R/'fixtures/p4b'
def load(n):return server.contracts.load(F/(n+'.json'))
def src(w,id):return next(r['definition'] for r in w['sources'] if r['definition']['id']==id)
def run(mid='p4b-difference',w=None,s=None,evaluation=None):
 w=w or load('workspace');b=next(b for b in w['mappings'][0]['mappings'] if b['mappingId']==mid)
 if s is None:s={id:load('samples')[id] for id in sample_quality.source_ids(w,b)}
 return preview.run(w,'mixed-tank-mapping',mid,s,2,evaluation)
def codes(w):return {e['ruleCode'] for e in server.findings_for(w)}
class Oracles(unittest.TestCase):pass
def oracle(c):
 def test(self):
  w=load('workspace');before=copy.deepcopy(w);r=run(c['mappingId'],w);self.assertEqual(r['quality'],c['quality'],r['issues']);self.assertEqual(r['result']['value'],c['result']);self.assertEqual(before,w);self.assertFalse(r['persisted'])
 return test
for c in load('cases')['cases']:setattr(Oracles,'test_'+c['mappingId'].replace('-','_'),oracle(c))
class Contracts(unittest.TestCase):
 def test_fixture(self):server.check_state(load('workspace'));self.assertEqual(server.findings_for(load('workspace')),[])
 def test_old_schemas(self):
  for p,h in server.contracts.load(R/'docs/verification/p4a-validation.json')['sha256'].items():
   if p.startswith('contracts/'):self.assertEqual(server.contracts.hashed(R/p),h,p)
 def test_meta(self):
  from jsonschema import Draft202012Validator
  for p in (R/'contracts/2.7.0').glob('*.json'):Draft202012Validator.check_schema(server.contracts.load(p))
 def test_string_whitespace_preserved(self):
  w=load('workspace');value='  LINE-A\n ';src(w,'mixed-line-code')['access']['value']=value;self.assertEqual(run('p4b-line-code',w,{})['result']['value'],value)
 def test_virtual_string_whitespace_preserved(self):
  w=load('workspace');d=src(w,'mixed-tag-pressure');d['rawRepresentation']['valueType']='String';d['unit']={'status':'not-applicable'};member=next(m for m in w['semantics'][0]['members'] if m['memberId']=='solution-pressure');member.update(valueType='String',unit={'status':'not-applicable'});b=next(b for b in w['mappings'][0]['mappings'] if b['mappingId']=='p4b-solution-pressure');b['transform'][0]['to']='String';b['outputUnit']={'status':'not-applicable'}
  self.assertEqual(run('p4b-solution-pressure',w,{'mixed-tag-pressure':{'typedValue':'  PV\n '}})['result']['value'],'  PV\n ')
 def test_constant_no_sample(self):
  r=run('p4b-baseline',s={});self.assertEqual(r['result']['value'],'100');self.assertEqual(r['requiredSources'],[]);self.assertIn('constant-definition',{t['stage'] for t in r['trace']});self.assertEqual(next(t['detail']['execution'] for t in r['trace'] if t['stage']=='typed-input'),'definition-value')
 def test_constant_override_rejected(self):
  r=run('p4b-baseline',s={'mixed-baseline':{'typedValue':'999'}});self.assertIsNone(r['result']);self.assertIn('sample.constant-override',{i['code'] for i in r['issues']})
 def test_constant_double_precision(self):
  w=load('workspace');src(w,'mixed-baseline')['access']['value']='0.1';r=run('p4b-baseline',w,{});self.assertEqual(r['quality'],'uncertain');self.assertIn('loss.input-precision',{i['code'] for i in r['issues']})
 def test_external_sql_preserved_no_execution(self):
  w=load('workspace');text="  NOT VALID SQL;\nSELECT '보존'; -- :parameter\n ";src(w,'mixed-external-reference')['access']['expression']=text
  with patch('socket.create_connection',side_effect=AssertionError('network forbidden')),patch('sqlite3.connect',side_effect=AssertionError('SQL forbidden')):
   r=run('p4b-external-reference',w,{'mixed-external-reference':{'typedValue':'70'}})
  self.assertEqual(r['result']['value'],'70');self.assertEqual(next(t['detail']['access']['expression'] for t in r['trace'] if t['stage']=='typed-input'),text)
 def test_external_requires_virtual_value(self):
  r=run('p4b-external-reference',s={});self.assertIsNone(r['result']);self.assertIn('sample.missing',{i['code'] for i in r['issues']})
 def test_solution_tag_is_typed_virtual(self):
  r=run('p4b-solution-pressure',s={'mixed-tag-pressure':{'bytesHex':'00'}});self.assertIsNone(r['result']);self.assertIn('sample.mode',{i['code'] for i in r['issues']})
 def test_write_only_cannot_read(self):
  w=load('workspace');src(w,'mixed-plc-pressure').update(schemaVersion='2.7.0',sourceKind='plc',accessMode='write')
  self.assertIn('source.not-readable',codes(w))
  with self.assertRaises(server.Invalid):server.check_state(w)
  self.assertIsNone(run(w=w)['result'])
 def test_legacy_read_default_not_writable(self):
  w=load('workspace');w['writes'][0]['destinationRef']={'id':'mixed-plc-pressure','version':'1.0.0'};self.assertIn('write.destination-readonly',codes(w))
  with self.assertRaises(server.Invalid):server.check_state(w)
 def test_constant_not_destination(self):
  w=load('workspace');w['writes'][0]['destinationRef']={'id':'mixed-baseline','version':'1.0.0'};self.assertIn('write.destination-readonly',codes(w))
 def test_external_not_destination(self):
  w=load('workspace');w['writes'][0]['destinationRef']={'id':'mixed-external-reference','version':'1.0.0'};self.assertIn('write.destination-readonly',codes(w))
 def test_write_direction_type(self):
  w=load('workspace');w['writes'][0]['transform']=[{'op':'cast','to':'Double','rounding':'exact','overflow':'error'}];self.assertIn('write.output-type',codes(w))
 def test_write_direction_unit(self):
  w=load('workspace');src(w,'mixed-plc-write')['unit']={'status':'known','code':'bar'};self.assertIn('write.output-unit',codes(w))
 def test_explicit_write_unit_conversion(self):
  w=load('workspace');src(w,'mixed-plc-write')['unit']={'status':'known','code':'bar'};w['writes'][0]['transform']=[{'op':'unit-convert','from':'kPa','to':'bar'},{'op':'cast','to':'UInt16','rounding':'exact','overflow':'error'}];server.check_state(w)
 def test_wrong_write_unit_direction(self):
  w=load('workspace');w['writes'][0]['transform'].insert(0,{'op':'unit-convert','from':'bar','to':'kPa'});self.assertIn('write.transform-unit',codes(w))
 def test_read_not_automatically_inverted(self):
  w=load('workspace');before=copy.deepcopy(w['mappings']);w['writes'][0]['transform'][0]['factor']='20';server.check_state(w);self.assertEqual(w['mappings'],before);self.assertEqual(run('p4b-setpoint',w)['result']['value'],'80')
 def test_write_evidence(self):
  w=load('workspace');w['writes'][0]['evidenceRefs']=src(w,'mixed-plc-write')['evidenceRefs'];self.assertIn('write.evidence-incomplete',codes(w))
 def test_write_missing_ref(self):
  w=load('workspace');w['writes'][0]['destinationRef']['id']='absent';self.assertIn('write.reference',codes(w))
 def test_duplicate_write_member(self):
  w=load('workspace');w['writes'][1]['memberPath']=copy.deepcopy(w['writes'][0]['memberPath']);self.assertIn('write.duplicate-member',codes(w))
 def test_duplicate_write_destination(self):
  w=load('workspace');d=copy.deepcopy(w['writes'][1]);d['id']='duplicate';d['memberPath']=[{'kind':'member','memberId':'plc-pressure'}];w['writes'].append(d);self.assertIn('write.duplicate-destination',codes(w))
 def test_tag_identity_ignores_display_version(self):
  w=load('workspace');r=copy.deepcopy(next(r for r in w['sources'] if r['definition']['id']=='mixed-tag-setpoint'));r['definition']['id']='same-tag';r['definition']['access']['solutionVersion']='2.0';r['definition']['evidenceRefs']=[{'artifactId':'manual-same-tag','locator':{'kind':'text-line','line':1}}];w['sources'].append(r)
  d=copy.deepcopy(w['writes'][1]);d['id']='same-tag-write';d['destinationRef']['id']='same-tag';d['memberPath']=[{'kind':'member','memberId':'plc-pressure'}];d['evidenceRefs']+=r['definition']['evidenceRefs'];w['writes'].append(d);self.assertIn('write.duplicate-destination',codes(w))
 def test_cross_equipment_write(self):
  w=load('workspace');w['equipment'].append({'id':'other','label':'Other'});w['writes'][0]['equipmentInstanceId']='other';self.assertIn('write.equipment',codes(w))
 def test_legacy_workspace_rejects_new(self):
  w=load('workspace');old={k:w[k] for k in ('equipment','connections','sources','semantics','mappings')};old['mappings']=[]
  with self.assertRaises(server.Invalid):server.check_state(old)
 def test_legacy_bundle_gate_rejects_new(self):
  w=load('workspace');old={k:w[k] for k in ('equipment','connections','sources','semantics','mappings')};old['mappings']=[]
  with tempfile.TemporaryDirectory() as t:
   server.legacy_build_package(old,Path(t));self.assertIn('source.mixed-legacy-unsupported',{e['ruleCode'] for e in server.contracts.validate_package(Path(t))})
 def test_new_proposal_and_query_roundtrip(self):
  w=load('workspace')
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);server.build_package(w,p);d=server.contracts.load(p/'proposal.json');self.assertEqual(d['schemaVersion'],'2.7.0');self.assertEqual(sum(e['kind']=='write-definition' for e in d['files']),2)
   external=next(server.contracts.load(p/e['path']) for e in d['files'] if e['id']=='mixed-external-reference');self.assertEqual(external['access']['expression'],src(w,'mixed-external-reference')['access']['expression'])
 def test_temporal_constant_excluded(self):
  w=load('workspace');b=next(b for b in w['mappings'][0]['mappings'] if b['mappingId']=='p4b-difference');policy=server.contracts.load(R/'fixtures/p3e/timed-workspace.json')['mappings'][0]['mappings'][0]['temporalPolicy'];b['temporalPolicy']=policy;w['mappings'][0]['schemaVersion']='2.3.0'
  at='2026-10-17T10:00:00Z';s={'mixed-plc-pressure':{'value':{'bytesHex':'9600'},'quality':'good','sourceTimestamp':at,'serverTimestamp':at,'sequence':None}};e={'at':at,'triggerSequence':None};server.check_state(w)
  r=run(w=w,s=s,evaluation=e);self.assertEqual(r['result']['value'],'50');self.assertEqual(r['temporal']['requiredSources'],['mixed-plc-pressure']);self.assertEqual(r['quality'],'good')
  s['mixed-plc-pressure']['quality']='bad';self.assertIsNone(run(w=w,s=s,evaluation=e)['result'])
 def test_constant_only_temporal_no_fake_time(self):
  w=load('workspace');b=next(b for b in w['mappings'][0]['mappings'] if b['mappingId']=='p4b-baseline');b['temporalPolicy']=server.contracts.load(R/'fixtures/p3e/timed-workspace.json')['mappings'][0]['mappings'][0]['temporalPolicy'];w['mappings'][0]['schemaVersion']='2.3.0';r=run('p4b-baseline',w,{}, {'at':'2026-10-17T10:00:00Z','triggerSequence':None});self.assertEqual(r['result']['value'],'100');self.assertEqual(r['temporal']['inputs'],[]);self.assertIsNone(r['dataValue']['inputTimestampRange'])
class API(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.store=server.Store(Path(self.tmp.name)/'editor.sqlite3');self.store.migrate(0,{});self.store.save(1,load('workspace'));self.http=server.make_server(self.store,0);self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()
 def tearDown(self):self.http.shutdown();self.http.server_close();self.thread.join();self.tmp.cleanup()
 def request(self,path,body,origin=None):
  headers={'Content-Type':'application/json','X-Tyr-Editor':'1'}
  if origin:headers['Origin']=origin
  return urlopen(Request('http://127.0.0.1:'+str(self.http.server_port)+path,data=json.dumps(body).encode(),headers=headers,method='POST'))
 def test_sqlite_reopen_all(self):self.assertEqual(server.Store(self.store.path).read()['workspace'],load('workspace'))
 def test_preview_readonly(self):
  before=self.store.read();h=server.contracts.hashed(self.store.path)
  with self.request('/api/preview',{'revision':2,'mappingSetId':'mixed-tank-mapping','mappingId':'p4b-difference','samples':{'mixed-plc-pressure':{'bytesHex':'9600'}}}) as r:self.assertEqual(json.load(r)['result']['value'],'50')
  self.assertEqual(before,self.store.read());self.assertEqual(h,server.contracts.hashed(self.store.path))
 def test_edit_write_reopen(self):
  w=load('workspace');w['writes'][0]['transform'][0]['factor']='20';self.store.save(2,w);self.assertEqual(server.Store(self.store.path).read()['workspace'],w)
 def test_stale_save_atomic(self):
  before=self.store.read()
  with self.assertRaises(server.Conflict):self.store.save(1,load('workspace'))
  self.assertEqual(before,self.store.read())
 def test_invalid_write_atomic(self):
  w=load('workspace');w['writes'][0]['destinationRef']['id']='mixed-baseline';before=self.store.read()
  with self.assertRaises(server.Invalid):self.store.save(2,w)
  self.assertEqual(before,self.store.read())
 def test_no_execute_routes(self):
  for path in ('/api/write','/api/sql','/api/execute','/api/plc/read'):
   with self.assertRaises(HTTPError) as e:self.request(path,{})
   self.assertEqual(e.exception.code,404)
 def test_foreign_origin(self):
  with self.assertRaises(HTTPError) as e:self.request('/api/workspace',{'revision':2,'workspace':load('workspace')},'https://evil.invalid')
  self.assertEqual(e.exception.code,403)
def invalid(name,change):
 def test(self):
  w=load('workspace');change(w)
  with self.assertRaises(server.Invalid):server.check_state(w)
 return test
mutations={
 'constant-nan':lambda w:src(w,'mixed-baseline')['access'].update(value='NaN'),
 'constant-infinity':lambda w:src(w,'mixed-baseline')['access'].update(value='1e309'),
 'constant-bool-as-number':lambda w:src(w,'mixed-baseline')['access'].update(value=True),
 'constant-int-fraction':lambda w:(src(w,'mixed-baseline')['rawRepresentation'].update(valueType='Int32'),src(w,'mixed-baseline')['access'].update(value='1.5')),
 'constant-writable':lambda w:src(w,'mixed-baseline').update(accessMode='read-write'),
 'external-writable':lambda w:src(w,'mixed-external-reference').update(accessMode='write'),
 'sql-missing-expression':lambda w:src(w,'mixed-external-reference')['access'].update(expression=None),
 'expression-none-but-text':lambda w:src(w,'mixed-external-reference')['access'].update(expressionLanguage='none'),
 'execute-enabled':lambda w:w['writes'][0].update(execution='enabled'),
 'unsupported-write-op':lambda w:w['writes'][0].update(transform=[{'op':'eval','expression':'x'}]),
 'nonplc-plc-connection':lambda w:src(w,'mixed-tag-pressure').update(connectionProfileRef='mixed-melsec'),
 'invalid-mode':lambda w:src(w,'mixed-tag-pressure').update(accessMode='execute'),
}
for name,change in mutations.items():setattr(Contracts,'test_invalid_'+name.replace('-','_'),invalid(name,change))
def profile_case(profile,access,raw,sample):
 def test(self):
  w=load('workspace');d=src(w,'mixed-plc-pressure');conn={'id':'other-read','label':'Metadata','equipmentInstanceId':'mixed-line','accessProfileRef':profile};w['connections'].append(conn);d.update(accessProfileRef=profile,connectionProfileRef=conn['id'],access=access,rawRepresentation=raw,addressRadix=10 if profile=='melsec-device-v1' else None,inputStage='already-engineered' if raw['mode']=='typed' else 'raw');server.check_state(w);r=run(w=w,s={'mixed-plc-pressure':sample});self.assertEqual(r['result']['value'],'50')
 return test
for profile,a,r,s in [
 ('ab-logix-symbol-v1',{'kind':'symbol','symbolPath':'Tank.PV'},{'mode':'typed','valueType':'Float32'},{'typedValue':'150'}),
 ('s7-1500-opcua-v1',{'kind':'opcua-node','namespaceUri':'urn:synthetic','identifierType':'string','identifier':'Tank.PV'},{'mode':'typed','valueType':'Float32'},{'typedValue':'150'}),
 ('s7-300-db-v1',{'kind':'db-offset','dbNumber':1,'byteOffset':0,'byteLength':2,'bitOffset':None},{'mode':'bytes','valueType':'UInt16','byteOrder':'big','wordOrder':'high-first'},{'bytesHex':'0096'}),
]:setattr(Contracts,'test_profile_'+profile.replace('-','_'),profile_case(profile,a,r,s))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--report',type=Path);a=p.parse_args();r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
 if a.report:
  files=[*(R/'contracts').rglob('*.json'),*(F).glob('*'),*(R/'backend').glob('*.py'),*(R/'frontend').glob('*'),R/'scripts/mixed_sources.py',R/'scripts/p3a_contracts.py',R/'scripts/validate_contracts.py',Path(__file__)]
  server.contracts.save(a.report,{'total':r.testsRun,'passed':r.testsRun-len(r.failures)-len(r.errors),'oracleCases':9,'failures':[str(x) for x in r.failures],'errors':[str(x) for x in r.errors],'sha256':{str(p.relative_to(R)).replace(chr(92),'/'):server.contracts.hashed(p) for p in files if p.is_file()}})
 sys.exit(not r.wasSuccessful())
