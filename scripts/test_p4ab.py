"""P4-A B independent review and three-way reconciliation acceptance."""
import copy,json,sys,tempfile,threading,unittest
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/"backend"),str(R/"scripts")]
import server,import_files as imp,import_workflow as wf,publication
F=R/"fixtures/p4ab"
def load(n):return server.contracts.load(F/(n+".json"))
def w():return load("reviewed-workspace")
def incoming(state=None):return imp.parse(load("incoming-request"),state or load("local-workspace"))
def plan(state=None,new=None):
 state=state or load("local-workspace");old=state["imports"][0];ids={a["sourceId"] for a in wf.previous_entries(old,state["sources"])}
 return wf.plan(old,new or incoming(state),[r for r in state["sources"] if r["definition"]["id"] in ids],wf.digest(state))
def apply(state=None,choices=None,new=None):
 state=state or load("local-workspace");new=new or incoming(state);p=plan(state,new)
 return wf.apply(state,new,p,choices or load("merge-choices"),load("review-metadata"))
def source(state,suffix):return next(row for row in state["sources"] if row["definition"]["id"].endswith(suffix))
class Review(unittest.TestCase):
 def test_contract(self):server.check_state(w())
 def test_schema_meta(self):
  from jsonschema import Draft202012Validator
  for p in (R/"contracts/2.14.0").glob("*.json"):Draft202012Validator.check_schema(server.contracts.load(p))
 def test_old_contracts_and_fixtures_unchanged(self):
  pins=server.contracts.load(R/"docs/verification/p3fb-full-acceptance.json")["inputSha256"]
  for p,h in pins.items():
   if p.startswith(("contracts/","fixtures/")):self.assertEqual(server.contracts.hashed(R/p),h,p)
 def test_original_replay_unchanged(self):
  original=load("original-workspace")["imports"][0];reviewed=w()["imports"][0]
  self.assertEqual(original["observations"],reviewed["observations"]);self.assertEqual(original["bytesBase64"],reviewed["bytesBase64"]);self.assertEqual(original["sha256"],reviewed["sha256"])
 def test_effective_resolution(self):
  b=w()["imports"][0];o=next(o for o in b["observations"] if o["raw"].get("id")=="unresolved")
  self.assertIn("address.register",o["issues"]);self.assertEqual(wf.materialize(b,o)["rawAddressText"],"D4000");self.assertFalse(wf.unresolved(b))
 def test_exclusion_preserves_opaque(self):
  b=w()["imports"][0];o=b["observations"][-1];self.assertIsNone(wf.materialize(b,o));self.assertEqual(o["raw"]["value"],{"opaque":"preserve exactly"});self.assertFalse(wf.pending(b,o))
 def test_unresolved_still_blocks_gate(self):
  self.assertIn("import.unresolved",{x["ruleCode"] for x in server.findings_for(load("original-workspace"))})
  self.assertNotIn("import.unresolved",{x["ruleCode"] for x in server.findings_for(w())})
 def test_resolution_source_adopted_draft(self):
  original=load("original-workspace");review=load("resolve-review");s=wf.review(original,"review-base",review);s=wf.adopt(s,"review-base",[review["observationId"]]);self.assertEqual(source(s,"-unresolved")["definition"]["status"],"draft")
 def test_invalid_decision_no_mutation(self):
  original=load("original-workspace");before=copy.deepcopy(original);q=load("resolve-review");q["observationSha256"]="0"*64
  with self.assertRaisesRegex(ValueError,"stale"):wf.review(original,"review-base",q)
  self.assertEqual(original,before)
 def test_missing_reason(self):
  q=load("resolve-review");q["reason"]=" "
  with self.assertRaisesRegex(ValueError,"metadata"):wf.review(load("original-workspace"),"review-base",q)
 def test_bad_source_unit(self):
  state=w();state["imports"][0]["reviews"][0]["source"]["unit"]={"status":"unknown"}
  with self.assertRaises(server.Invalid):server.check_state(state)
 def test_bad_source_evidence(self):
  state=w();state["imports"][0]["reviews"][0]["source"]["evidenceRefs"]=[]
  with self.assertRaises(server.Invalid):server.check_state(state)
 def test_write_resolution_rejected(self):
  state=w();state["imports"][0]["reviews"][0]["source"]["accessMode"]="write"
  with self.assertRaises(server.Invalid):server.check_state(state)
 def test_review_chain(self):
  state=w();b=state["imports"][0];q=copy.deepcopy(b["reviews"][0]);q["previousReviewSha256"]=wf.digest(q);q["reason"]="Second explicit review, same address";q["reviewedAt"]="2026-10-18T01:00:00Z"
  state=wf.review(state,"review-base",q);server.check_state(state);self.assertEqual(len(state["imports"][0]["reviews"]),3)
 def test_forged_chain(self):
  state=w();state["imports"][0]["reviews"][0]["previousReviewSha256"]="0"*64
  with self.assertRaises(server.Invalid):server.check_state(state)
 def test_exclude_adopted_source_rejected(self):
  state=w();b=state["imports"][0];o=b["observations"][0];q={**load("exclude-review"),"observationId":o["id"],"observationSha256":wf.digest(o)}
  state=wf.review(state,"review-base",q)
  with self.assertRaises(server.Invalid):server.check_state(state)
 def test_file_issue_not_waived(self):
  q=load("base-request");q["bytesBase64"]="bm90LWpzb24=";b=imp.parse(q,load("original-workspace"));self.assertTrue(wf.unresolved(wf.promote(b)))
 def test_xlsx_formula_explicit_manual_resolution(self):
  q=server.contracts.load(R/"fixtures/p4a/excel-request.json");q["id"]="review-excel";context=server.contracts.load(R/"fixtures/p4a/context.json")
  b=imp.parse(q,context);state=imp.adopt(context,b,[])
  o=next(o for o in b["observations"] if o["raw"].get("id")=="formula");d=copy.deepcopy(source(w(),"-unresolved")["definition"])
  d.update(id="imp-review-excel-formula",status="draft",rawAddressText="D6400",evidenceRefs=wf.refs(b,o));d["access"]["addressIndex"]=6400
  review={**load("resolve-review"),"observationId":o["id"],"observationSha256":wf.digest(o),"recordKey":"formula","source":d}
  state=wf.review(state,b["id"],review);state=wf.adopt(state,b["id"],[o["id"]]);server.check_state(state)
  self.assertEqual(state["imports"][0]["observations"],b["observations"]);self.assertEqual(source(state,"-formula")["definition"]["rawAddressText"],"D6400")
 def test_json_numbers_and_unicode_digest(self):
  self.assertEqual(wf.digest({"한글":1.0,"😀":[True,None,-0.0]}),wf.digest({"😀":[True,None,0],"한글":1}))
class Merge(unittest.TestCase):
 def test_classifications(self):self.assertEqual({a["recordKey"]:a["classification"] for a in plan()["actions"]},load("expected")["classifications"])
 def test_fixture_replays(self):self.assertEqual(apply(),load("merged-workspace"));server.check_state(apply())
 def test_stable_identity_and_mapping(self):
  result=apply();expected=load("expected");s=source(result,"speed-ab")
  self.assertEqual(s["definition"]["id"],expected["stableSourceId"]);self.assertEqual(result["mappings"][0]["mappings"][0]["valueRef"],w()["mappings"][0]["mappings"][0]["valueRef"])
 def test_non_overlapping_auto_merge(self):
  s=source(apply(),"speed-ab");self.assertEqual(s["label"],"Local speed label");self.assertEqual(s["definition"]["rawAddressText"],"Motor.ActualSpeedV2")
 def test_conflict_choose_ours(self):
  s=source(apply(),"pressure-ua");self.assertEqual(s["definition"]["rawAddressText"],"Line.LocalPressure");self.assertEqual(s["note"],"Local engineering note must survive")
 def test_conflict_choose_incoming(self):
  choices=load("merge-choices");choices["pressure-ua"]["fields"]={k:"incoming" for k in choices["pressure-ua"]["fields"]}
  self.assertEqual(source(apply(choices=choices),"pressure-ua")["definition"]["rawAddressText"],"Line.IncomingPressure")
 def test_conflict_requires_all_fields(self):
  choices=load("merge-choices");choices["pressure-ua"]["fields"]={}
  with self.assertRaisesRegex(ValueError,"conflicts"):apply(choices=choices)
 def test_choices_cannot_change_nonconflicts(self):
  choices=load("merge-choices");choices["speed-ab"]["fields"]={"unit":"ours"}
  with self.assertRaisesRegex(ValueError,"conflicts"):apply(choices=choices)
 def test_removed_is_retained(self):
  s=next(s for s in apply()["sources"] if s["definition"]["id"]==load("expected")["retainedDbId"]);self.assertEqual(s["importRef"]["batchId"],"review-base")
 def test_delete_not_supported(self):
  choices=load("merge-choices");choices["pressure-db"]["mode"]="delete"
  with self.assertRaisesRegex(ValueError,"removal-policy"):apply(choices=choices)
 def test_incoming_change_can_explicitly_keep_current_definition(self):
  choices=load("merge-choices");choices["speed-ab"]={"mode":"retain","fields":{}}
  state=apply(choices=choices);server.check_state(state)
  self.assertEqual(source(state,"speed-ab")["definition"]["rawAddressText"],"Motor.ActualSpeed")
  self.assertEqual(state["imports"][-1]["reconciliation"]["results"]["speed-ab"],plan()["actions"][next(i for i,a in enumerate(plan()["actions"]) if a["key"]=="speed-ab")]["ours"])
 def test_retain_conflict_uses_no_field_choices(self):
  choices=load("merge-choices");choices["pressure-ua"]={"mode":"retain","fields":{}}
  state=apply(choices=choices);server.check_state(state);self.assertEqual(source(state,"pressure-ua")["definition"]["rawAddressText"],"Line.LocalPressure")
 def test_removed_record_returns_with_same_identity(self):
  import base64
  state=apply();q=load("incoming-request");doc=json.loads(base64.b64decode(q["bytesBase64"]));base=json.loads(base64.b64decode(load("base-request")["bytesBase64"]))
  doc["records"].append(next(x for x in base["records"] if x["id"]=="pressure-db"));q["id"]="review-return";q["bytesBase64"]=base64.b64encode(json.dumps(doc).encode()).decode()
  new=imp.parse(q,state);old=state["imports"][-1];ids={a["sourceId"] for a in old["adoptions"]}
  p=wf.plan(old,new,[row for row in state["sources"] if row["definition"]["id"] in ids],wf.digest(state))
  choices={a["key"]:{"mode":"retain" if a["classification"]=="removed" else "apply","fields":{f["field"]:"ours" for f in a["fields"] if f["conflict"]}} for a in p["actions"]}
  out=wf.apply(state,new,p,choices,load("review-metadata"));server.check_state(out);db=source(out,"pressure-db")
  self.assertEqual(db["definition"]["id"],load("expected")["retainedDbId"]);self.assertEqual(db["importRef"]["batchId"],"review-return");self.assertEqual(len(out["sources"]),9)
 def test_new_can_skip(self):
  choices=load("merge-choices");choices["new-signal"]["mode"]="skip";s=apply(choices=choices);self.assertEqual(len(s["sources"]),8);server.check_state(s)
 def test_template_alias_reordered(self):
  result=apply();self.assertEqual(source(result,"pump-1")["definition"]["access"]["addressIndex"],5999);self.assertEqual(source(result,"alias")["definition"]["access"]["addressIndex"],5999)
 def test_merged_sources_need_review(self):
  result=apply()
  for row in result["sources"]:
   if row["importRef"]["batchId"]=="review-next":self.assertEqual(row["definition"]["status"],"draft")
 def test_provenance_closure_appended(self):
  result=apply();ev=result["mappings"][0]["mappings"][0]["evidenceRefs"];self.assertTrue(any(e["artifactId"]=="import-review-base" for e in ev));self.assertTrue(any(e["artifactId"]=="import-review-next" for e in ev))
 def test_original_batches_preserved(self):
  self.assertEqual(apply()["imports"][0],w()["imports"][0]);self.assertEqual(apply()["imports"][1]["observations"],incoming()["observations"])
 def test_second_reimport_after_removal(self):
  state=apply();q=load("incoming-request");q["id"]="review-third";new=imp.parse(q,state);old=state["imports"][-1];ids={a["sourceId"] for a in old["adoptions"]};p=wf.plan(old,new,[r for r in state["sources"] if r["definition"]["id"] in ids],wf.digest(state))
  choices={a["key"]:{"mode":"retain" if a["classification"]=="removed" else "apply","fields":{f["field"]:"ours" for f in a["fields"] if f["conflict"]}} for a in p["actions"]}
  out=wf.apply(state,new,p,choices,load("review-metadata"));server.check_state(out);self.assertEqual(len(out["sources"]),9)
 def test_stale_workspace(self):
  state=load("local-workspace");p=plan(state);state["sources"][0]["note"]="changed"
  with self.assertRaisesRegex(ValueError,"stale"):wf.apply(state,incoming(state),p,load("merge-choices"),load("review-metadata"))
 def test_bad_previous_batch_hash(self):
  state=apply();state["imports"][-1]["reconciliation"]["previousBatchSha256"]="0"*64
  with self.assertRaises(server.Invalid):server.check_state(state)
 def test_forged_result(self):
  state=apply();state["imports"][-1]["reconciliation"]["results"]["speed-ab"]["rawAddressText"]="Injected"
  with self.assertRaises(server.Invalid):server.check_state(state)
 def test_forged_adoption(self):
  state=apply();state["imports"][-1]["adoptions"][0]["sourceId"]="wrong"
  with self.assertRaises(server.Invalid):server.check_state(state)
 def test_original_observation_tamper(self):
  state=apply();state["imports"][-1]["observations"][0]["raw"]["address"]="D1111"
  with self.assertRaises(server.Invalid):server.check_state(state)
 def test_base_locked_after_merge(self):
  state=apply();q=load("resolve-review");q["previousReviewSha256"]=wf.digest(state["imports"][0]["reviews"][0])
  with self.assertRaisesRegex(ValueError,"immutable"):wf.review(state,"review-base",q)
 def test_unresolved_new_batch_must_be_resolved_before_merge(self):
  import base64
  state=load("local-workspace");q=load("incoming-request");doc=json.loads(base64.b64decode(q["bytesBase64"]));record=next(x for x in doc["records"] if x["id"]=="speed-ab");record["unsupported"]="preserve this claim"
  q["bytesBase64"]=base64.b64encode(json.dumps(doc).encode()).decode();new=imp.parse(q,state)
  with self.assertRaisesRegex(ValueError,"unresolved"):wf.apply(state,new,plan(state,new),load("merge-choices"),load("review-metadata"))
  state=imp.adopt(state,new,[]);o=next(o for o in new["observations"] if o["raw"].get("id")=="speed-ab");d=copy.deepcopy(source(w(),"-speed-ab")["definition"])
  d.update(id="imp-review-next-speed-ab",status="draft",evidenceRefs=wf.refs(new,o))
  review={**load("resolve-review"),"observationId":o["id"],"observationSha256":wf.digest(o),"recordKey":"speed-ab","source":d}
  state=wf.review(state,new["id"],review);new=state["imports"][-1]
  p=plan(state,new);out=wf.apply(state,new,p,load("merge-choices"),load("review-metadata"));server.check_state(out);self.assertEqual(len(out["imports"]),2)
 def test_pure_plan(self):
  state=load("local-workspace");before=copy.deepcopy(state);self.assertEqual(plan(state),plan(state));self.assertEqual(state,before)
 def test_sqlite_reopen_cas(self):
  with tempfile.TemporaryDirectory() as t:
   st=server.Store(Path(t)/"editor.sqlite3");st.migrate(0,{});st.save(1,load("local-workspace"));st.save(2,apply());self.assertEqual(server.Store(st.path).read(),st.read())
   with self.assertRaises(server.Conflict):st.save(2,apply())
 def test_store_cannot_truncate_review_history(self):
  with tempfile.TemporaryDirectory() as t:
   st=server.Store(Path(t)/"history.sqlite3");st.migrate(0,{});st.save(1,w());before=st.read();changed=w();changed["imports"][0]["reviews"].pop()
   server.check_state(changed)
   with self.assertRaisesRegex(server.Invalid,"history-truncation"):st.save(2,changed)
   self.assertEqual(st.read(),before)
 def test_store_cannot_replace_original_filename(self):
  with tempfile.TemporaryDirectory() as t:
   st=server.Store(Path(t)/"history.sqlite3");st.migrate(0,{});st.save(1,w());before=st.read();changed=w();changed["imports"][0]["filename"]="rewritten.json"
   server.check_state(changed)
   with self.assertRaisesRegex(server.Invalid,"original-immutable"):st.save(2,changed)
   self.assertEqual(st.read(),before)
 def test_publication_closure_includes_review_history(self):
  with tempfile.TemporaryDirectory() as t:
   folder=Path(t)/"bundle";publication.build(load("publication-workspace"),folder,"p4ab","mixed-line","proposer",None,["import-speed-mapping"],False,server.build_package)
   proposal=server.contracts.load(folder/"proposal.json");ids={e["id"] for e in proposal["files"] if e["kind"]=="import-batch"};self.assertEqual(ids,{"review-base","review-next"})
   self.assertEqual(server.v2.p3.validate_package(folder)[0],[])
class HTTP(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.store=server.Store(Path(self.tmp.name)/"editor.sqlite3");self.store.migrate(0,{});self.store.save(1,load("local-workspace"));self.http=server.make_server(self.store,0);self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start();self.url="http://127.0.0.1:"+str(self.http.server_port)
 def tearDown(self):self.http.shutdown();self.http.server_close();self.thread.join();self.tmp.cleanup()
 def request(self,path,body=None,origin=None):
  headers={"X-Tyr-Editor":"1","Content-Type":"application/json"}
  if origin:headers["Origin"]=origin
  with urlopen(Request(self.url+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)) as r:return json.loads(r.read())
 def test_metadata_get_readonly(self):
  before=self.store.read();meta=self.request("/api/import-workflow");self.assertEqual(meta["revision"],2);self.assertEqual(meta["batches"][0]["observations"][0]["observationSha256"],wf.digest(before["workspace"]["imports"][0]["observations"][0]));self.assertEqual(self.store.read(),before)
 def test_merge_preview_apply_reopen(self):
  body={"revision":2,"previousBatchId":"review-base","request":load("incoming-request")};before=self.store.read();p=self.request("/api/import-merge-preview",body);self.assertEqual(self.store.read(),before);self.assertFalse(p["persisted"])
  got=self.request("/api/import-merge-apply",{**body,"planSha256":p["plan"]["planSha256"],"choices":load("merge-choices"),**load("review-metadata")});self.assertEqual(got["revision"],3);self.assertEqual(server.Store(self.store.path).read(),self.store.read())
 def test_stale_revision_atomic(self):
  before=self.store.read()
  with self.assertRaises(HTTPError) as e:self.request("/api/import-merge-preview",{"revision":1,"previousBatchId":"review-base","request":load("incoming-request")})
  self.assertEqual(e.exception.code,409);self.assertEqual(before,self.store.read())
 def test_forged_plan_atomic(self):
  before=self.store.read()
  with self.assertRaises(HTTPError) as e:self.request("/api/import-merge-apply",{"revision":2,"previousBatchId":"review-base","request":load("incoming-request"),"planSha256":"0"*64,"choices":load("merge-choices"),**load("review-metadata")})
  self.assertEqual(e.exception.code,422);self.assertEqual(before,self.store.read())
 def test_missing_conflict_atomic(self):
  body={"revision":2,"previousBatchId":"review-base","request":load("incoming-request")};p=self.request("/api/import-merge-preview",body);choices=load("merge-choices");choices["pressure-ua"]["fields"]={}
  before=self.store.read()
  with self.assertRaises(HTTPError):self.request("/api/import-merge-apply",{**body,"planSha256":p["plan"]["planSha256"],"choices":choices,**load("review-metadata")})
  self.assertEqual(before,self.store.read())
 def test_resolution_then_adopt_through_http(self):
  self.http.shutdown();self.http.server_close();self.thread.join()
  self.store=server.Store(Path(self.tmp.name)/"original.sqlite3");self.store.migrate(0,{});self.store.save(1,load("original-workspace"))
  self.http=server.make_server(self.store,0);self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start();self.url="http://127.0.0.1:"+str(self.http.server_port)
  got=self.request("/api/import-review",{"revision":2,"batchId":"review-base","review":load("resolve-review")})
  self.assertEqual(got["revision"],3)
  got=self.request("/api/import-adopt-reviewed",{"revision":3,"batchId":"review-base","selected":[load("resolve-review")["observationId"]]})
  self.assertEqual(got["revision"],4);self.assertEqual(source(got["workspace"],"-unresolved")["definition"]["status"],"draft")
 def test_duplicate_adoption_atomic(self):
  before=self.store.read()
  with self.assertRaises(HTTPError) as e:self.request("/api/import-adopt-reviewed",{"revision":2,"batchId":"review-base","selected":[load("resolve-review")["observationId"]]})
  self.assertEqual(e.exception.code,422);self.assertEqual(before,self.store.read())
 def test_origin_protection(self):
  with self.assertRaises(HTTPError) as e:self.request("/api/import-merge-preview",{"revision":2,"previousBatchId":"review-base","request":load("incoming-request")},"https://evil.invalid")
  self.assertEqual(e.exception.code,403)
if __name__=="__main__":unittest.main()
