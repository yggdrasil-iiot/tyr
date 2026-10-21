"""Synthetic lifecycle acceptance with actual SQLite CAS and immutable wire closure."""
import copy,json,sys,tempfile,unittest,threading,subprocess
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'backend'),str(R/'scripts')]
import server,semantic_lifecycle as lc,lifecycle_authoring as author,publication,sample_quality as sq,change_review

def workspace():return server.contracts.load(R/'fixtures/semantic-lifecycle/workspace.json')
def cases():return server.contracts.load(R/'fixtures/semantic-lifecycle/cases.json')
class Adapter:configured=False
class Lifecycle(unittest.TestCase):
 def test_fixture_and_independent_signature_oracle(self):
  w=workspace();server.check_state(w);self.assertEqual(server.findings_for(w),[]);s=lc.replay(w['semanticLifecycles'],lc.signatures(w['semantics']));self.assertEqual(s[cases()['semanticId']]['state'],'deprecated');self.assertEqual(lc.signatures(w['semantics'])[cases()['semanticId']],cases()['signature'])
 def test_metadata_revision_does_not_rewrite_meaning(self):
  w=workspace();old=copy.deepcopy(w['semantics']);w['semanticLifecycles'][0]['label']='different label';w['semanticLifecycles'][1]['previousEvent']['sha256']=sq.digest(w['semanticLifecycles'][0]);server.check_state(w);self.assertEqual(old,w['semantics'])
 def test_missing_uri(self):
  w=workspace();w['semanticLifecycles'][0]['semanticId']='urn:missing';self.assertRaisesRegex(ValueError,'uri-missing',server.check_state,w)
 def test_signature_drift(self):
  w=workspace();w['semanticLifecycles'][0]['signatureSha256']='0'*64;self.assertRaisesRegex(ValueError,'signature-drift',server.check_state,w)
 def test_previous_hash_tamper(self):
  w=workspace();w['semanticLifecycles'][1]['previousEvent']['sha256']='0'*64;self.assertRaisesRegex(ValueError,'previous-conflict',server.check_state,w)
 def test_fork_revision(self):
  w=workspace();e=copy.deepcopy(w['semanticLifecycles'][0]);e['id']='fork';w['semanticLifecycles'].append(e);self.assertRaisesRegex(ValueError,'revision-conflict',server.check_state,w)
 def test_gap(self):
  w=workspace();w['semanticLifecycles'][1]['revision']=3;self.assertRaisesRegex(ValueError,'revision-conflict',server.check_state,w)
 def test_invalid_transition(self):
  w=workspace();w['semanticLifecycles'][0]['action']='retire';self.assertRaisesRegex(ValueError,'transition',server.check_state,w)
 def test_retired_terminal(self):
  w=workspace();ret=cases()['retire'];w['semanticLifecycles'].append(ret);e=copy.deepcopy(ret);e.update(id='reactivate',revision=4,action='revise',previousEvent=dict(id=ret['id'],version=ret['version'],sha256=sq.digest(ret)));w['semanticLifecycles'].append(e);self.assertRaisesRegex(ValueError,'retired-terminal',server.check_state,w)
 def test_retirement_draft_allowed_but_publication_findings(self):
  w=workspace();w['semanticLifecycles'].append(cases()['retire']);server.check_state(w);self.assertIn('lifecycle.retired-binding',{e['ruleCode'] for e in server.findings_for(w)})
 def test_unknown_and_self_replacement(self):
  for uri in ['urn:missing',cases()['semanticId']]:
   w=workspace();w['semanticLifecycles'][1]['replacementSemanticId']=uri;self.assertRaisesRegex(ValueError,'replacement-missing',server.check_state,w)
 def test_replacement_is_explicit_new_uri_not_alias(self):
  w=workspace();known=lc.signatures(w['semantics']);other=next(u for u in known if u!=cases()['semanticId']);w['semanticLifecycles'][1]['replacementSemanticId']=other;server.check_state(w);self.assertEqual(w['mappings'],workspace()['mappings'])
 def test_time_order_and_unknown_offset(self):
  w=workspace();w['semanticLifecycles'][1]['authoredAt']='2026-10-17T00:00:00Z';self.assertRaisesRegex(ValueError,'time-order',server.check_state,w)
  w=workspace();w['semanticLifecycles'][0]['authoredAt']='2026-10-18T00:00:00-00:00';self.assertRaises(ValueError,server.check_state,w)
 def test_local_read_and_write_impacts(self):
  w=workspace();i=lc.impacts(w['semantics']+w['targets']+w['mappings']+w['writes']);self.assertIn('mapping-set',{e['kind'] for e in i});self.assertIn('write-definition',{e['kind'] for e in i});self.assertEqual(len([e for e in i if e['semanticId']==cases()['semanticId']]),cases()['expectedImpacts'])
 def test_nested_and_structure_array_ancestor_impacts(self):
  w=server.contracts.load(R/'fixtures/p3eb/workspace.json');i=lc.impacts(w['semantics']+w['targets']+w['mappings']);self.assertTrue(any(len(e['memberPath'])>2 for e in i));containers={n['semanticId'] for d in w['semantics'] for n in lc.logical.layout(d)['definitions'] if n['valueType'] in lc.logical.CONTAINERS};self.assertTrue(containers&{e['semanticId'] for e in i})
 def test_same_event_replay_is_idempotent_conflict_is_not(self):
  w=workspace();events=w['semanticLifecycles'];known=lc.signatures(w['semantics']);self.assertEqual(lc.replay(events,known),lc.replay(events+events,known));bad=copy.deepcopy(events[0]);bad['reason']='changed';self.assertRaisesRegex(ValueError,'event-conflict',lc.replay,events+[bad],known)
 def test_append_only_sqlite_rollback_reopen_and_stale(self):
  with tempfile.TemporaryDirectory() as tmp:
   store=server.Store(Path(tmp)/'editor.sqlite3');store.migrate(0,{});store.save(1,workspace());before=store.read()
   for mutate in [lambda w:w.pop('semanticLifecycles'),lambda w:w['semanticLifecycles'][0].update(reason='changed')]:
    w=copy.deepcopy(before['workspace']);mutate(w);self.assertRaises(ValueError,store.save,2,w);self.assertEqual(before,store.read())
   self.assertEqual(before,server.Store(store.path).read());self.assertRaises(server.Conflict,store.save,1,before['workspace'])
 def test_report_readonly_and_authoring_atomic(self):
  with tempfile.TemporaryDirectory() as tmp:
   store=server.Store(Path(tmp)/'editor.sqlite3');store.migrate(0,{});store.save(1,workspace());before=store.read()
   with store.connect() as db:rows=list(db.iterdump())
   r=author.report(store,Adapter());self.assertEqual(r['workspaceRevision'],2)
   with store.connect() as db:self.assertEqual(rows,list(db.iterdump()))
   self.assertEqual(store.read(),before);e=workspace()['semanticLifecycles'][-1]
   req=dict(revision=2,semanticId=e['semanticId'],action='revise',replacementSemanticId=None,label='Updated',description='Description',reason='Review',authoredBy='tester');a=author.apply(store,req,server.Conflict,Adapter());self.assertEqual(a['saved']['revision'],3);self.assertEqual(len(server.Store(store.path).read()['workspace']['semanticLifecycles']),3);self.assertRaises(server.Conflict,author.apply,store,req,server.Conflict,Adapter())
 def test_export_keeps_full_chain_and_management_definitions(self):
  w=workspace()
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/'bundle';_,_,findings=publication.build(w,root,'fixture-export','mixed-line','proposer',None,[w['mappings'][0]['id']],False,server.build_package);self.assertFalse(findings);p=server.contracts.load(root/'proposal.json');self.assertEqual(p['schemaVersion'],'2.18.0');self.assertEqual(sum(e['kind']=='semantic-lifecycle' for e in p['files']),2);self.assertEqual(sum(e['kind']=='semantic-definition' for e in p['files']),len(w['semantics']))
 def test_lifecycle_only_retirement_publication(self):
  w=workspace();w["semanticLifecycles"].append(cases()["retire"])
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/"bundle";_,_,findings=publication.build(w,root,"governance-only","mixed-line","proposer",None,[],False,server.build_package);self.assertFalse(findings);self.assertFalse(any(e["kind"]=="mapping-set" for e in server.contracts.load(root/"proposal.json")["files"]))
 def test_old_contract_fixture_hashes_and_mirror(self):
  pins=server.contracts.load(R/'docs/verification/semantic-lifecycle-baseline-pins.json')
  for path,expected in pins.items():self.assertEqual(server.contracts.hashed(R.parent/path),expected,path)
  for p in (R/'contracts').glob('*/*.schema.json'):self.assertEqual(p.read_bytes(),(R.parent/'bifrost/core/src/main/resources/mapping-contracts'/p.relative_to(R/'contracts')).read_bytes())
 def test_replacement_cycle_and_retired_replacement(self):
  w=workspace();known=lc.signatures(w['semantics']);uri=cases()['semanticId'];other=next(u for u in known if u!=uri);first=copy.deepcopy(w['semanticLifecycles'][0]);first.update(id='other-first',semanticId=other,action='deprecate',replacementSemanticId=uri,signatureSha256=sq.digest(known[other]));w['semanticLifecycles'][1]['replacementSemanticId']=other;self.assertRaisesRegex(ValueError,'replacement-cycle',lc.replay,w['semanticLifecycles']+[first],known)
  w=workspace();first['replacementSemanticId']=None;second=copy.deepcopy(first);second.update(id='other-retire',revision=2,action='retire',previousEvent=dict(id=first['id'],version=first['version'],sha256=sq.digest(first)));w['semanticLifecycles'][1]['replacementSemanticId']=other;self.assertRaisesRegex(ValueError,'replacement-retired',lc.replay,w['semanticLifecycles']+[first,second],known)
 def test_retired_write_is_separately_detected(self):
  w=workspace();uri=next(i['semanticId'] for i in lc.impacts(w['semantics']+w['targets']+w['writes']) if i['kind']=='write-definition');sig=lc.signatures(w['semantics'])[uri];first=copy.deepcopy(w['semanticLifecycles'][0]);first.update(id='write-deprecated',semanticId=uri,action='deprecate',signatureSha256=sq.digest(sig));second=copy.deepcopy(first);second.update(id='write-retired',revision=2,action='retire',previousEvent=dict(id=first['id'],version=first['version'],sha256=sq.digest(first)));w['semanticLifecycles']=[first,second];states,errors=lc.validate(w['semantics']+w['targets']+w['mappings']+w['writes']+w['semanticLifecycles']);self.assertTrue(any(e['kind']=='write-definition' for e in errors))
 def test_empty_old_workspace_cannot_use_management_only_escape(self):
  w=workspace();w.pop('semanticLifecycles')
  with tempfile.TemporaryDirectory() as tmp:self.assertRaisesRegex(ValueError,'Choose mapping',publication.build,w,Path(tmp)/'bundle','empty','mixed-line','proposer',None,[],False,server.build_package)
 def test_standalone_offline_contract_cli(self):
  p=subprocess.run([sys.executable,"-B",str(R/"scripts/p3a_contracts.py"),"--package",str(R/"fixtures/semantic-lifecycle/bundle"),"--deny-network"],capture_output=True,text=True,timeout=120);self.assertEqual(p.returncode,0,p.stderr);self.assertTrue(json.loads(p.stdout)["valid"])
 def test_review_includes_lifecycle(self):
  w=workspace();self.assertTrue(any(k.startswith('semantic-lifecycle:') for k in change_review.index(w)));before=copy.deepcopy(w);before.pop('semanticLifecycles');d=change_review.compare(dict(id='baseline',workspace=before,workspaceSha256=sq.digest(before)),w,2,[]);self.assertTrue(any(c['key'].startswith('semantic-lifecycle:') for c in d['changes']))
 def test_http_guard_and_persistence(self):
  with tempfile.TemporaryDirectory() as tmp:
   store=server.Store(Path(tmp)/'editor.sqlite3');store.migrate(0,{});store.save(1,workspace());http=server.make_server(store,0);th=threading.Thread(target=http.serve_forever,daemon=True);th.start();url='http://127.0.0.1:'+str(http.server_port)
   try:
    with urlopen(url+'/api/semantic-lifecycle') as r:self.assertEqual(json.load(r)['workspaceRevision'],2)
    with self.assertRaises(HTTPError) as err:urlopen(Request(url+'/api/semantic-lifecycle',headers={'Origin':'http://outside.invalid'}))
    self.assertEqual(err.exception.code,403)
   finally:http.shutdown();http.server_close();th.join()
if __name__=='__main__':unittest.main()
