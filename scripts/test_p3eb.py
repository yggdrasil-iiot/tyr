"""Independent canonical object oracles, bounds, compatibility and SQLite/HTTP paths."""
import copy,json,sys,tempfile,threading,unittest
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/"backend"),str(ROOT/"scripts")]
import server,preview,logical_preview,logical_structures as ls,p3a_contracts as p3,change_review
F=ROOT/"fixtures/p3eb"
def load(name):return server.contracts.load(F/(name+".json"))
def workspace():return load("workspace")
def findings(w):return {x["ruleCode"] for x in server.findings_for(w)}
def target(prefix="ab"):return {"id":"structure-skid-"+prefix,"version":"1.0.0"}
def result(w=None,samples=None,prefix="ab",evaluation=None):
 return logical_preview.run(w or workspace(),target(prefix),load("samples") if samples is None else samples,2,evaluation)
class Contract(unittest.TestCase):
 def test_fixture(self):
  w=workspace();server.check_state(w);self.assertEqual(server.findings_for(w),[])
 def test_negative_fixture_contracts(self):
  for c in load("negative-cases")["cases"]:
   with self.subTest(c["id"]):
    w=workspace();node=w[c["section"]][c["index"]]
    for k in c["path"][:-1]:node=node[k]
    node[c["path"][-1]]=copy.deepcopy(c["value"])
    self.assertIn(c["expectedRule"],findings(w))
 def test_meta_and_legacy_refusal(self):
  from jsonschema import Draft202012Validator
  for p in (ROOT/"contracts/2.12.0").glob("*.schema.json"):Draft202012Validator.check_schema(server.contracts.load(p))
  w=workspace()
  for v in ("1.1.0","2.2.0"):
   m=copy.deepcopy(w["semantics"][0]);m["schemaVersion"]=v;self.assertTrue(p3.schema_errors("semantic-definition",m))
  m=copy.deepcopy(w["mappings"][0]);m["schemaVersion"]="2.4.0";self.assertTrue(p3.schema_errors("mapping-set",m))
 def test_full_paths_do_not_collide(self):
  layout=ls.layout(workspace()["semantics"][0]);self.assertEqual(len(layout["leaves"]),10)
  w=workspace();self.assertNotIn("mapping.duplicate-target",findings(w))
  self.assertEqual(len({ls.path_key(b["memberPath"]) for b in w["mappings"][0]["mappings"]}),10)
 def test_duplicate_full_path_rejected(self):
  w=workspace();b=copy.deepcopy(w["mappings"][0]["mappings"][4]);b["mappingId"]="duplicate-path";w["mappings"][0]["mappings"].append(b)
  self.assertIn("mapping.duplicate-target",findings(w))
  with self.assertRaises(server.Invalid):server.check_state(w)
 def test_indices_rank_and_range(self):
  for ix,code in [([0],"structure.index-range"),([3],"structure.index-range"),([1,0],"structure.array-rank"),([1.0],"structure.index-range")]:
   w=workspace();w["mappings"][0]["mappings"][4]["memberPath"][1]["indices"]=ix
   self.assertIn(code,findings(w))
   with self.assertRaises(server.Invalid):server.check_state(w)
 def test_paths_require_leaf_and_index(self):
  for path,code in [([{"kind":"member","memberId":"process"}],"structure.whole-mapping"),([{"kind":"member","memberId":"modules"},{"kind":"member","memberId":"running"}],"structure.index-required"),([{"kind":"member","memberId":"missing"}],"mapping.member"),([{"kind":"member","memberId":"process"},{"kind":"member","memberId":"running"},{"kind":"member","memberId":"extra"}],"mapping.member-path")]:
   w=workspace();w["mappings"][0]["mappings"][0]["memberPath"]=path;self.assertIn(code,findings(w))
 def test_duplicate_sibling_id_and_legal_repeated_leaf_names(self):
  w=workspace();self.assertEqual(findings(w),set())
  w["semantics"][0]["members"][0]["members"].append(copy.deepcopy(w["semantics"][0]["members"][0]["members"][0]))
  self.assertIn("semantic.duplicate",findings(w))
 def test_shape_and_expansion_limits(self):
  for shape,lb,code in [([2,2],[1],"structure.array-rank"),([17,17],[0,0],"structure.array-range"),([256],[0],"structure.size"),([2],[2147483647],"structure.array-range"),([2.0],[1],"structure.array-rank")]:
   w=workspace();w["semantics"][0]["members"][1].update(shape=shape,lowerBounds=lb);self.assertIn(code,findings(w))
 def test_deep_definition_rejected_before_recursive_schema(self):
  w=workspace();n=w["semantics"][0]["members"][0]
  for i in range(40):n["members"]=[copy.deepcopy(n)];n=n["members"][0]
  self.assertTrue(p3.schema_errors("semantic-definition",w["semantics"][0]))
  with self.assertRaises(server.Invalid):server.check_state(w)
 def test_meaning_conflicts_and_shape_change(self):
  w=workspace();w["semantics"][0]["members"][1]["members"][0]["members"][0]["unit"]={"status":"known","code":"bar"}
  self.assertIn("semantic.identity-conflict",findings(w))
  base=workspace();changed=copy.deepcopy(base)
  # A container semantic URI cannot refer to two incompatible shapes.
  duplicate=copy.deepcopy(base["semantics"][0]);duplicate["id"]="second-model";duplicate["members"][1]["shape"]=[3]
  changed["semantics"].append(duplicate);self.assertIn("semantic.identity-conflict",findings(changed))
 def test_leaf_unit_type_evidence_and_equipment(self):
  for change,code in [("unit","mapping.unit"),("type","mapping.type"),("evidence","mapping.evidence-incomplete"),("equipment","value.equipment")]:
   w=workspace();b=w["mappings"][0]["mappings"][0]
   if change=="unit":b["outputUnit"]={"status":"known","code":"bar"}
   elif change=="type":b["transform"][0]["to"]="Int32"
   elif change=="evidence":b["evidenceRefs"]=w["mappings"][0]["mappings"][1]["evidenceRefs"]
   else:b["valueRef"]["sourceRef"]["id"]="structure-ua-actual"
   self.assertIn(code,findings(w))
 def test_old_contracts_and_fixtures_unchanged(self):
  pins=server.contracts.load(ROOT/"docs/verification/p3cb-acceptance.json")["inputSha256"]
  for p,h in pins.items():
   if (p.startswith("contracts/") and p.endswith(".schema.json")) or p.startswith("fixtures/"):self.assertEqual(server.contracts.hashed(ROOT/p),h,p)
 def test_change_review_distinguishes_logical_identity_and_shape(self):
  self.assertEqual(change_review.category("mappings/0/mappings/4/memberPath/1/indices/0"),"identity")
  self.assertEqual(change_review.category("semantics/0/members/1/lowerBounds/0"),"meaning")
  self.assertEqual(change_review.category("graphs/0/nodes/0/indices/0"),"graph")
 def test_old_flat_model_keeps_prior_limits(self):
  m=server.contracts.load(ROOT/"fixtures/p3c/workspace.json")["semantics"][0]
  first=m["members"][0];m["members"]=[dict(first,memberId="member-"+str(i),semanticId="urn:fixture:member:"+str(i)) for i in range(300)]
  self.assertFalse(p3.schema_errors("semantic-definition",m));self.assertEqual(len(ls.layout(m)["leaves"]),300)
class Values(unittest.TestCase):
 def test_four_profiles_same_object_and_no_mutation(self):
  w=workspace();samples=load("samples");before=copy.deepcopy((w,samples))
  for prefix in ("ab","ua","db","melsec"):
   r=result(w,samples,prefix);self.assertEqual(r["quality"],"good",r["issues"]);self.assertEqual(r["result"],load("expected"));self.assertEqual(len(r["members"]),10)
   self.assertEqual(r["arrays"][0]["lowerBounds"],[1]);self.assertFalse(r["persisted"]);self.assertFalse(r["atomicSnapshot"])
  self.assertEqual((w,samples),before)
 def test_leaf_preview_uses_full_path(self):
  w=workspace()
  for pos,value in [(4,"100"),(7,"220")]:
   b=w["mappings"][0]["mappings"][pos];r=preview.run(w,"structure-ab-mapping",b["mappingId"],load("samples"),2)
   self.assertEqual(r["result"]["value"],value)
   self.assertIn("array-index",{s["stage"] for s in r["trace"]})
 def test_missing_binding_kept_as_draft_and_bad_assembly(self):
  w=workspace();w["mappings"][0]["mappings"].pop(7)
  server.check_state(w);self.assertIn("mapping.incomplete-object",findings(w))
  r=result(w);self.assertEqual(r["quality"],"bad");self.assertIsNone(r["result"])
  self.assertIsNone(r["partialResult"]["modules"][1]["pressure"]["actual"])
  self.assertEqual(r["partialResult"]["modules"][0]["pressure"]["actual"],"100")
 def test_missing_source_propagates_without_zero_replacement(self):
  s=load("samples");s.pop("structure-ab-actual");r=result(samples=s)
  self.assertIsNone(r["result"]);self.assertEqual(r["quality"],"bad")
  self.assertIsNone(r["partialResult"]["process"]["pressure"]["actual"])
  self.assertEqual(r["partialResult"]["process"]["pressure"]["target"],"180")
 def test_selected_array_element_missing_keeps_other_members(self):
  s=load("samples");s["array-pressures-ab"]["typedValues"][6]=None;r=result(samples=s)
  self.assertIsNone(r["result"]);self.assertIsNone(r["partialResult"]["modules"][1]["pressure"]["actual"])
  self.assertEqual(r["partialResult"]["modules"][0]["pressure"]["actual"],"100")
 def test_uncertain_loss_propagates(self):
  w=workspace();b=w["mappings"][0]["mappings"][0];b["transform"].insert(0,{"op":"linear","factor":"0.1","offset":"0"});s=load("samples");s["structure-ab-actual"]["typedValue"]="151";b["transform"][-1]["rounding"]="half-even"
  r=result(w,s);self.assertEqual(r["quality"],"uncertain");self.assertIsNotNone(r["result"]);self.assertIn("loss.precision",{i["code"] for i in r["issues"]})
 def test_temporal_bad_and_stale_propagate(self):
  w=workspace();b=w["mappings"][0]["mappings"][0]
  b["temporalPolicy"]={"timestampBasis":"source","maxAgeMs":1000,"maxSkewMs":100,"uncertainInput":"propagate","missingInput":"reject","badInput":"propagate","assembly":"latest"}
  for q,time,code in [("bad","2026-10-17T09:59:59.500Z","quality.bad-input"),("good","2026-10-17T09:59:58Z","time.stale-input")]:
   s=load("samples");s["structure-ab-actual"]={"value":s["structure-ab-actual"],"quality":q,"sourceTimestamp":time,"serverTimestamp":"2026-10-17T10:00:00Z","sequence":None}
   r=result(w,s,evaluation={"at":"2026-10-17T10:00:00Z","triggerSequence":None})
   self.assertEqual(r["quality"],"bad");self.assertIn(code,{i["code"] for i in r["issues"]});self.assertIsNone(r["result"])
 def test_missing_target_version_and_duplicate_runtime_guard(self):
  with self.assertRaises(ValueError):logical_preview.run(workspace(),{"id":"structure-skid-ab","version":"9.0.0"},load("samples"),2)
  w=workspace();w["mappings"][0]["mappings"].append(copy.deepcopy(w["mappings"][0]["mappings"][0]))
  with self.assertRaises(ValueError):result(w)
 def test_literal_member_ids_do_not_alias_paths(self):
  scalar={"memberId":"a.b","name":"literal","semanticId":"urn:fixture:literal","description":"literal ID","valueType":"Double","unit":{"status":"known","code":"1"},"role":"measurement","range":None}
  nested=dict(scalar,memberId="b",semanticId="urn:fixture:nested")
  model={"schemaVersion":"2.12.0","members":[scalar,{"memberId":"a","valueType":"Structure","members":[nested]}]}
  leaves=ls.layout(model)["leaves"];self.assertEqual(len(leaves),2)
  self.assertEqual({x["label"] for x in leaves.values()},{'["a.b"]',"a.b"})
  self.assertEqual(ls.assemble(model,{k:("1" if x["member"] is scalar else "2") for k,x in leaves.items()}),{"a.b":"1","a":{"b":"2"}})
 def test_nested_arrays_and_negative_lower_bounds(self):
  model=load("nested-model");leaf=model["members"][0]["members"][0]["members"][0]
  self.assertFalse(p3.schema_errors("semantic-definition",model));layout=ls.layout(model);self.assertEqual(len(layout["leaves"]),8)
  values={k:"7" for k in layout["leaves"]};expected=load("nested-expected")
  self.assertEqual(ls.assemble(model,values),expected)
  p=[{"kind":"member","memberId":"racks"},{"kind":"index","indices":[-1]},{"kind":"member","memberId":"slots"},{"kind":"index","indices":[2,4]},{"kind":"member","memberId":"value"}]
  self.assertEqual(ls.resolve(model,p),leaf)
class StorageHTTP(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.store=server.Store(Path(self.tmp.name)/"editor.sqlite3");self.store.migrate(0,{});self.store.save(1,workspace())
  self.http=server.make_server(self.store,0);self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start();self.url="http://127.0.0.1:"+str(self.http.server_port)
 def tearDown(self):
  self.http.shutdown();self.http.server_close();self.thread.join();self.tmp.cleanup()
 def request(self,path,body):
  return urlopen(Request(self.url+path,data=json.dumps(body).encode(),method="POST",headers={"Content-Type":"application/json","X-Tyr-Editor":"1"}))
 def test_object_api_readonly(self):
  before=self.store.read();sha=server.contracts.hashed(self.store.path)
  with self.request("/api/logical-preview",{"revision":2,"targetInstanceRef":target(),"samples":load("samples")}) as response:r=json.load(response)
  self.assertEqual(r["result"],load("expected"));self.assertEqual(before,self.store.read());self.assertEqual(sha,server.contracts.hashed(self.store.path))
 def test_stale_and_wrong_target_ref(self):
  for body,status in [({"revision":1,"targetInstanceRef":target(),"samples":{}},409),({"revision":2,"targetInstanceRef":{"id":"absent","version":"1.0.0"},"samples":{}},422)]:
   with self.assertRaises(HTTPError) as e:self.request("/api/logical-preview",body)
   self.assertEqual(e.exception.code,status)
 def test_reopen_old_new_and_atomic_save(self):
  self.assertEqual(server.Store(self.store.path).read()["workspace"],workspace())
  before=self.store.read();bad=workspace();bad["mappings"][0]["mappings"][4]["memberPath"][1]["indices"]=[3]
  with self.assertRaises(server.Invalid):self.store.save(2,bad)
  with self.assertRaises(server.Conflict):self.store.save(1,workspace())
  self.assertEqual(before,self.store.read())
  old=server.contracts.load(ROOT/"fixtures/p3eb/workspace.json");old["targets"][0]["label"]="renamed";self.store.save(2,old)
  self.assertEqual(server.Store(self.store.path).read()["workspace"],old)
 def test_legacy_database_bytes_unchanged_on_open(self):
  p=Path(self.tmp.name)/"legacy.sqlite3";s=server.Store(p);s.save(0,copy.deepcopy(server.EMPTY));before=p.read_bytes()
  server.Store(p);self.assertEqual(p.read_bytes(),before)
 def test_no_execution_routes(self):
  for path in ("/api/sql","/api/write","/api/plc/read","/api/execute"):
   with self.assertRaises(HTTPError) as e:self.request(path,{})
   self.assertEqual(e.exception.code,404)
if __name__=="__main__":unittest.main()
