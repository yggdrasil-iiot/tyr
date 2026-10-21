"""Independent workspace/catalog comparison and persistence boundaries."""
import copy,json,sys,tempfile,unittest,threading
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'backend'),str(R/'scripts')]
import server,semantic_catalog as c,logical_structures as logical,sample_quality as sq

def workspace():return server.contracts.load(R/'fixtures/p3eb/workspace.json')
class Store:
 def __init__(self,w):self.w=w
 def read(self):return {'workspace':self.w,'revision':7}
class Adapter:
 configured=True;registry=Path('synthetic-registry')
 def __init__(self,doc):self.doc=doc;self.args=None
 def call(self,*args):self.args=args;return copy.deepcopy(self.doc)
def catalog(w):
 grouped={}
 for d in w['semantics']:
  for n,path in authored(d['members']):
   uri=n['semanticId'];sig=logical.signature(n);e=grouped.setdefault(uri,{'semanticId':uri,'compatible':True,'variants':[]})
   if not any(v['signature']==sig for v in e['variants']):e['variants'].append({'signature':sig,'occurrences':[{'streamId':'first','releaseId':'first-release','releaseVersion':'1.0.0','releaseSha256':'a'*64,'definitionId':d['id'],'definitionVersion':d['version'],'memberId':n['memberId'],'definitionPath':path,'label':n['name']}]})
 result={'kind':'semantic-catalog','schemaVersion':'2.16.0','compatible':True,'scope':'registry-history','activation':'not-performed','execution':'excluded','releases':[],'entries':list(grouped.values())};result['catalogSha256']=sq.digest(result);return copy.deepcopy(result)

def authored(nodes,path=()):
 for n in nodes:
  here=path+(n['memberId'],);yield n,list(here);yield from authored(n.get('members',[]),here)
def actual(w):return next(n for d in w['semantics'] for n,p in authored(d['members']) if n['semanticId']=='urn:tyr:concept:pressure.actual')
def rep(w,doc=None):return c.report(Store(w),Adapter(catalog(w) if doc is None else doc))
def status(report,uri='urn:tyr:concept:pressure.actual'):return next(e for e in report['entries'] if e['semanticId']==uri)['status']
class Catalog(unittest.TestCase):
 def test_unconfigured_does_not_claim_compatibility(self):
  a=Adapter(None);a.configured=False;r=c.report(Store(workspace()),a);self.assertIsNone(r['catalog']);self.assertEqual({e['status'] for e in r['entries']},{'registry-unavailable'});self.assertIsNone(a.args)
 def test_nested_same_contract_and_independent_signature_oracle(self):
  w=workspace();r=rep(w);self.assertEqual({e['status'] for e in r['entries']},{'compatible'});oracle=server.contracts.load(R/'fixtures/semantic-catalog/cases.json')['canonicalPressureSignature'];self.assertEqual(logical.signature(actual(w)),oracle)
 def test_label_and_description_do_not_define_identity(self):
  w=workspace();old=catalog(w);actual(w)['name']='Other pressure label';actual(w)['description']='different wording';self.assertEqual(status(rep(w,old)),'compatible')
 def test_role_drift_detected(self):
  w=workspace();old=catalog(w);[n.update(role='setpoint') for d in w['semantics'] for n,path in authored(d['members']) if n['semanticId']=='urn:tyr:concept:pressure.actual'];self.assertEqual(status(rep(w,old)),'registry-conflict')
 def test_unit_drift_detected(self):
  w=workspace();old=catalog(w);[n['unit'].update(code='bar') for d in w['semantics'] for n,path in authored(d['members']) if n['semanticId']=='urn:tyr:concept:pressure.actual'];self.assertEqual(status(rep(w,old)),'registry-conflict')
 def test_type_drift_detected(self):
  w=workspace();old=catalog(w);[n.update(valueType='UInt16') for d in w['semantics'] for n,path in authored(d['members']) if n['semanticId']=='urn:tyr:concept:pressure.actual'];self.assertEqual(status(rep(w,old)),'registry-conflict')
 def test_same_name_new_uri_is_not_merged(self):
  w=workspace();old=catalog(w);actual(w)['semanticId']='urn:tyr:concept:other-pressure';self.assertEqual(status(rep(w,old),'urn:tyr:concept:other-pressure'),'new')
 def test_conflicting_workspace_occurrences_remain_visible(self):
  w=workspace();actual(w)['role']='setpoint';r=rep(w);self.assertEqual(status(r),'workspace-conflict');self.assertEqual(len(next(e for e in r['entries'] if e['semanticId']=='urn:tyr:concept:pressure.actual')['variants']),2)
 def test_container_shape_compared(self):
  w=workspace();old=catalog(w);w['semantics'][0]['members'][1]['lowerBounds'][0]+=1;r=rep(w,old);self.assertEqual(status(r,w['semantics'][0]['members'][1]['semanticId']),'registry-conflict')
 def test_full_definition_paths_and_repeated_leaves(self):
  r=rep(workspace());e=next(e for e in r['entries'] if e['semanticId']=='urn:tyr:concept:pressure.actual');self.assertGreater(len(e['variants'][0]['occurrences']),1);self.assertTrue(all(o['definitionPath'][-1]==o['memberId'] for o in e['variants'][0]['occurrences']))
 def test_digest_tamper_refused(self):
  w=workspace();d=catalog(w);d['compatible']=False
  with self.assertRaisesRegex(ValueError,'digest mismatch'):rep(w,d)
 def test_schema_tamper_refused(self):
  w=workspace();d=catalog(w);d['execution']='performed'
  with self.assertRaisesRegex(ValueError,'schema'):rep(w,d)
 def test_receiver_refusal_is_not_empty_success(self):
  with self.assertRaisesRegex(ValueError,'unavailable'):rep(workspace(),{'kind':'mapping-refusal','error':'mapping.recovery-required'})
 def test_sqlite_readonly_and_existing_rows(self):
  with tempfile.TemporaryDirectory() as tmp:
   store=server.Store(Path(tmp)/'editor.sqlite3');store.migrate(0,{});store.save(1,workspace());before=store.read()
   with store.connect() as db:rows=list(db.iterdump())
   a=Adapter(catalog(workspace()));r=c.report(store,a);self.assertEqual(a.args,('catalog',a.registry));self.assertEqual(store.read(),before);self.assertEqual(server.Store(store.path).read(),before)
   with store.connect() as db:self.assertEqual(rows,list(db.iterdump()))
   self.assertEqual(r['workspaceRevision'],2)
 def test_http_local_origin_and_no_mutation(self):
  with tempfile.TemporaryDirectory() as tmp:
   store=server.Store(Path(tmp)/'editor.sqlite3');store.migrate(0,{});store.save(1,workspace());before=store.read();http=server.make_server(store,0);th=threading.Thread(target=http.serve_forever,daemon=True);th.start()
   try:
    url='http://127.0.0.1:'+str(http.server_port)+'/api/semantic-catalog'
    with urlopen(url) as response:self.assertFalse(json.load(response)['configured'])
    with self.assertRaises(HTTPError) as err:urlopen(Request(url,headers={'Origin':'http://outside.invalid'}))
    self.assertEqual(err.exception.code,403);self.assertEqual(store.read(),before)
   finally:http.shutdown();http.server_close();th.join()
if __name__=='__main__':unittest.main()
