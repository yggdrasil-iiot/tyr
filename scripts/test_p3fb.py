"""P3-F B independent graph candidate, temporal and persistence oracles."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/"backend"),str(ROOT/"scripts")]
import server,preview,sample_quality,publication,p3a_contracts as p3
F=ROOT/"fixtures/p3fb"
def load(n):return server.contracts.load(F/(n+".json"))
def select(s,i,previous=0,timed=False):
 for id,v in [("selector-index",i),("selector-previous",previous)]:
  value={"bytesHex":v.to_bytes(2,"little").hex()}
  if timed:s[id]["value"]=value
  else:s[id]=value
 return s
def run(w=None,s=None,ctx=None):
 return preview.run(w or load("workspace"),"bounded-pressure-mapping","selected-pressure",load("samples") if s is None else s,2,ctx)
def codes(r):return {i["code"] for i in r["issues"]}
def findings(w):return {i["ruleCode"] for i in server.findings_for(w)}
class GraphCandidates(unittest.TestCase):
 def test_contract(self):server.check_state(load("workspace"))
 def test_timed_contract(self):server.check_state(load("timed-workspace"))
 def test_meta(self):
  from jsonschema import Draft202012Validator
  for p in (ROOT/"contracts/2.13.0").glob("*.json"):Draft202012Validator.check_schema(server.contracts.load(p))
 def test_legacy_refusal(self):
  g=load("workspace")["graphs"][0];g["schemaVersion"]="2.5.0";self.assertTrue(p3.schema_errors("value-graph",g))
 def test_equal_values_different_paths(self):
  a=run(s=select(load("samples"),0));b=run(s=select(load("samples"),1))
  self.assertEqual(a["result"]["value"],b["result"]["value"]);self.assertTrue(b["selections"][-1]["sourceChanged"])
  self.assertNotEqual(a["selections"][-1]["definitionSha256"],b["selections"][-1]["definitionSha256"])
 def test_duplicate_endpoint_is_same_origin(self):
  w=load("workspace");w["graphs"][0]["nodes"][-1]["inputs"]["candidate1"]={"kind":"node","nodeId":"scaled-up"}
  self.assertFalse(run(w,select(load("samples"),1))["selections"][-1]["sourceChanged"])
 def test_same_roots_different_calculation(self):
  w=load("workspace");g=w["graphs"][0];n=copy.deepcopy(g["nodes"][0]);n["nodeId"]="other-scale";n["factor"]="0.2";g["nodes"].insert(0,n);g["nodes"][-1]["inputs"]["candidate1"]={"kind":"node","nodeId":"other-scale"}
  r=run(w,select(load("samples"),1));self.assertEqual(r["result"]["value"],"200");self.assertTrue(r["selections"][-1]["sourceChanged"])
 def test_unselected_missing_not_evaluated(self):
  s=load("samples");del s["pressure-down"];r=run(s=s)
  self.assertEqual(r["result"]["value"],"100");self.assertEqual(set(r["requiredSources"]),{"pressure-up","selector-index","selector-previous"})
  self.assertFalse(any(t["identity"].endswith("/converted-down") for t in r["trace"]))
 def test_previous_value_not_evaluated(self):
  s=select(load("samples"),0,1);del s["pressure-down"];r=run(s=s);self.assertEqual(r["result"]["value"],"100");self.assertTrue(r["selections"][-1]["sourceChanged"])
 def test_selected_missing_no_failover(self):
  s=select(load("samples"),1);del s["pressure-down"];r=run(s=s);self.assertIsNone(r["result"]);self.assertIn("selector.selected-invalid",codes(r))
 def test_default_graph(self):
  w=load("workspace");w["graphs"][0]["nodes"][-1].update(outOfRange="default-candidate",defaultCandidate=2)
  r=run(w,select(load("samples"),9));self.assertEqual(r["result"]["value"],"0");self.assertIn("selector.default-used",codes(r))
 def test_bad_default_no_failover(self):
  w=load("workspace");w["graphs"][0]["nodes"][-1].update(outOfRange="default-candidate",defaultCandidate=2)
  s=select(load("samples"),9);del s["pressure-down"];self.assertIsNone(run(w,s)["result"])
 def test_type_all_candidates(self):
  w=load("workspace");w["graphs"][0]["nodes"][-1]["valueType"]="UInt16";self.assertIn("selector.candidate-type",findings(w))
 def test_unit_all_candidates(self):
  w=load("workspace");w["graphs"][0]["nodes"][-1]["unit"]["code"]="bar";self.assertIn("selector.candidate-unit",findings(w))
 def test_missing_node(self):
  w=load("workspace");w["graphs"][0]["nodes"][-1]["inputs"]["candidate1"]["nodeId"]="absent";self.assertIn("graph.node-missing",findings(w))
 def test_cycle(self):
  w=load("workspace");w["graphs"][0]["nodes"][-1]["inputs"]["candidate1"]["nodeId"]="selected";self.assertIn("graph.cycle",findings(w))
 def test_branch_evidence(self):
  w=load("workspace");w["graphs"][0]["nodes"][-1]["evidenceRefs"]=w["graphs"][0]["nodes"][-1]["evidenceRefs"][:1];self.assertIn("graph.evidence-incomplete",findings(w))
 def test_33_refused(self):
  w=load("workspace");n=w["graphs"][0]["nodes"][-1]
  for i in range(3,33):n["inputs"]["candidate"+str(i)]=copy.deepcopy(n["inputs"]["candidate0"])
  with self.assertRaises(server.Invalid):server.check_state(w)
 def test_mixed_direct_and_graph(self):
  w=load("workspace");n=w["graphs"][0]["nodes"][-1];n["inputs"]["candidate1"]=copy.deepcopy(w["graphs"][0]["nodes"][0]["inputs"]["value"])
  self.assertIn("selector.candidate-type",findings(w))
 def test_mixed_direct_and_graph_valid(self):
  w=load("workspace");g=w["graphs"][0];sel=g["nodes"][-1];source=g["nodes"][0]["inputs"]["value"]
  identity={"nodeId":"direct-copy","op":"identity","inputs":{"value":source},"valueType":"UInt16","unit":{"status":"known","code":"kPa"},"evidenceRefs":copy.deepcopy(sel["evidenceRefs"])}
  g["nodes"].insert(0,identity);sel["valueType"]="UInt16";sel["inputs"]["candidate0"]=copy.deepcopy(source);sel["inputs"]["candidate1"]={"kind":"node","nodeId":"direct-copy"};del sel["inputs"]["candidate2"]
  server.check_state(w);self.assertEqual(run(w,select(load("samples"),1))["result"]["value"],"1000")
 def test_selected_graph_loss(self):
  w=load("workspace");g=w["graphs"][0];sel=g["nodes"][-1]
  n={"nodeId":"limited","op":"clamp","inputs":{"value":{"kind":"node","nodeId":"scaled-up"}},"low":"0","high":"50","valueType":"Decimal","unit":copy.deepcopy(sel["unit"]),"evidenceRefs":copy.deepcopy(sel["evidenceRefs"])}
  g["nodes"].insert(-1,n);sel["inputs"]["candidate0"]={"kind":"node","nodeId":"limited"}
  server.check_state(w);r=run(w);self.assertEqual(r["result"]["value"],"50");self.assertIn("loss.clamp",codes(r))
 def test_unselected_loss_ignored(self):
  w=load("workspace");g=w["graphs"][0];sel=g["nodes"][-1]
  n={"nodeId":"limited","op":"clamp","inputs":{"value":{"kind":"node","nodeId":"scaled-up"}},"low":"0","high":"50","valueType":"Decimal","unit":copy.deepcopy(sel["unit"]),"evidenceRefs":copy.deepcopy(sel["evidenceRefs"])}
  g["nodes"].insert(-1,n);sel["inputs"]["candidate1"]={"kind":"node","nodeId":"limited"}
  self.assertNotIn("loss.clamp",codes(run(w)))
 def test_nested_lazy_selector(self):
  w=load("workspace");g=w["graphs"][0];inner=copy.deepcopy(g["nodes"][-1]);inner["nodeId"]="inner";inner["inputs"].pop("previousIndex");inner["inputs"].pop("candidate2")
  g["nodes"].insert(-1,inner);g["nodes"][-1]["inputs"]["candidate0"]={"kind":"node","nodeId":"inner"}
  server.check_state(w);s=load("samples");del s["pressure-down"];r=run(w,s);self.assertEqual(r["result"]["value"],"100");self.assertEqual(len(r["selections"]),2)
 def test_pure(self):
  w=load("workspace");s=load("samples");before=copy.deepcopy((w,s));self.assertEqual(run(w,s),run(w,s));self.assertEqual((w,s),before)
 def test_sqlite_reopen_cas(self):
  with tempfile.TemporaryDirectory() as t:
   st=server.Store(Path(t)/"editor.sqlite3");st.migrate(0,{});st.save(1,load("workspace"));before=st.read()
   self.assertEqual(server.Store(st.path).read(),before);run();self.assertEqual(st.read(),before)
   with self.assertRaises(server.Conflict):st.save(1,load("workspace"))
 def test_control_stage_does_not_contaminate_candidate(self):
  w=load("workspace");w["sources"][2]["definition"]["inputStage"]="already-engineered";g=w["graphs"][0]
  n=copy.deepcopy(g["nodes"][0]);n["nodeId"]="after-selection";n["inputs"]["value"]={"kind":"node","nodeId":"selected"};n["factor"]="2";g["nodes"].append(n)
  w["mappings"][0]["mappings"][0]["valueRef"]["nodeId"]="after-selection";server.check_state(w)
  self.assertEqual(run(w)["result"]["value"],"200")
 def test_previous_schema_fixture_immutable(self):
  pins=server.contracts.load(ROOT/"docs/verification/p3eb-ui-acceptance.json")["inputSha256"]
  for p,h in pins.items():
   if p.startswith(("contracts/","fixtures/")):self.assertEqual(server.contracts.hashed(ROOT/p),h,p)
class Temporal(unittest.TestCase):
 def go(self,s):return run(load("timed-workspace"),s,load("evaluation"))
 def test_unselected_bad_stale_missing_ignored(self):
  for mode in ["bad","stale","missing"]:
   s=load("timed-samples")
   if mode=="bad":s["pressure-down"]["quality"]="bad"
   elif mode=="stale":s["pressure-down"]["sourceTimestamp"]="2000-01-01T00:00:00Z"
   else:del s["pressure-down"]
   with self.subTest(mode):self.assertEqual(self.go(s)["quality"],"good")
 def test_selected_bad(self):
  s=load("timed-samples");s["pressure-up"]["quality"]="bad";r=self.go(s);self.assertIsNone(r["result"]);self.assertFalse(r["selectionValueValidated"]);self.assertIn("quality.bad-input",codes(r));self.assertTrue(r["selections"][-1]["selectedInputDataValues"])
 def test_selected_stale(self):
  s=load("timed-samples");s["pressure-up"]["sourceTimestamp"]="2000-01-01T00:00:00Z";self.assertIn("time.stale-input",codes(self.go(s)))
 def test_selected_skew(self):
  s=select(load("timed-samples"),2,timed=True);s["pressure-down"]["sourceTimestamp"]="2026-10-17T09:59:59Z";self.assertIn("time.skew-exceeded",codes(self.go(s)))
 def test_index_bad(self):
  s=load("timed-samples");s["selector-index"]["quality"]="bad";self.assertIsNone(self.go(s)["result"])
 def test_previous_index_bad(self):
  s=load("timed-samples");s["selector-previous"]["quality"]="bad";self.assertIsNone(self.go(s)["result"])
 def test_uncertain(self):
  s=load("timed-samples");s["pressure-up"]["quality"]="uncertain";self.assertNotEqual(self.go(s)["quality"],"good")
 def test_candidates_metadata(self):
  r=self.go(load("timed-samples"));c=r["selections"][-1]["candidates"]
  self.assertEqual(c[0]["timeQualityAssessment"],"selected-path");self.assertEqual(c[1]["timeQualityAssessment"],"not-evaluated");self.assertEqual(c[1]["unit"]["code"],"kPa")
 def test_scenario_sqlite(self):
  w=load("timed-workspace");s={"kind":"preview-scenario","schemaVersion":"2.3.0","id":"graph-candidates","version":"1.0.0","label":"graph candidates","mappingSetRef":{"id":"bounded-pressure-mapping","version":"1.0.0"},"mappingId":"selected-pressure","workspaceSha256":sample_quality.digest(w),"evaluationContext":load("evaluation"),"samples":load("timed-samples")}
  sample_quality.check_scenario(s,w)
  with tempfile.TemporaryDirectory() as t:
   st=server.Store(Path(t)/"db");st.migrate(0,{});st.save(1,w);st.save_scenario(2,0,s);self.assertEqual(server.Store(st.path).scenarios()["scenarios"][0]["scenario"],s)
for c in load("cases")["cases"]:
 def test(self,c=c):
  r=run(s=select(load("samples"),c["index"]));self.assertEqual(r["result"]["value"],c["value"]);self.assertEqual(r["selections"][-1]["sourceChanged"],c["sourceChanged"]);self.assertEqual([x["id"] for x in r["selections"][-1]["selectedSourceRefs"]],c["selectedSourceIds"])
 setattr(GraphCandidates,"test_oracle_"+str(c["index"]),test)
if __name__=="__main__":unittest.main()
