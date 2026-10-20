
"""P3-F offline bounded selection acceptance."""
import argparse,copy,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/"backend"),str(ROOT/"scripts")]
import server,preview,sample_quality
def load(n):return server.contracts.load(ROOT/("fixtures/p3f/"+n+".json"))
def run(w=None,s=None):return preview.run(w or load("workspace"),"bounded-pressure-mapping","selected-pressure",s or load("samples"),2)
class Tests(unittest.TestCase):
 def test_negative_index(self):
  w=load("workspace");w["sources"][2]["definition"]["rawRepresentation"]["valueType"]="Int16";s=load("samples");s["selector-index"]={"bytesHex":"ffff"}
  self.assertIn("selector.out-of-range",{i["code"] for i in run(w,s)["issues"]})
 def test_default_does_not_hide_missing_selected(self):
  w=load("workspace");w["graphs"][0]["nodes"][0].update(outOfRange="default-candidate",defaultCandidate=1);s=load("samples");del s["pressure-up"]
  r=run(w,s);self.assertIsNone(r["result"]);self.assertNotIn("selector.default-used",{i["code"] for i in r["issues"]})
 def test_missing_default_candidate(self):
  w=load("workspace");w["graphs"][0]["nodes"][0].update(outOfRange="default-candidate",defaultCandidate=1);s=load("samples");s["selector-index"]={"bytesHex":"0200"};del s["pressure-down"]
  self.assertIsNone(run(w,s)["result"])
 def test_fraction_index_static(self):
  w=load("workspace");w["sources"][2]["definition"]["rawRepresentation"]["valueType"]="Float32";w["sources"][2]["definition"]["access"]["wordCount"]=2
  with self.assertRaises(server.Invalid):server.check_state(w)
 def test_32_candidates(self):
  w=load("workspace");n=w["graphs"][0]["nodes"][0]
  for i in range(2,32):n["inputs"]["candidate"+str(i)]=copy.deepcopy(n["inputs"]["candidate0"])
  server.check_state(w);s=load("samples");s["selector-index"]={"bytesHex":"1f00"};r=run(w,s);self.assertEqual(r["result"]["value"],"100");self.assertEqual(r["selections"][0]["candidateCount"],32)
  n["inputs"]["candidate32"]=n["inputs"]["candidate0"]
  with self.assertRaises(server.Invalid):server.check_state(w)
 def test_previous_range_rejected(self):
  s=load("samples");s["selector-previous"]={"bytesHex":"0200"};self.assertIsNone(run(s=s)["result"])
 def test_scenario_fixture(self):
  w=load("timed-workspace");s=load("scenario");sample_quality.check_scenario(s,w);r=preview.run(w,"bounded-pressure-mapping","selected-pressure",s["samples"],2,s["evaluationContext"]);self.assertEqual(r["result"]["value"],"200");self.assertTrue(r["selections"][0]["sourceChanged"])
 def test_quality_and_time_only_required(self):
  w=load("timed-workspace");s=load("scenario");s["samples"]["pressure-up"]["sourceTimestamp"]="2000-01-01T00:00:00Z"
  r=preview.run(w,"bounded-pressure-mapping","selected-pressure",s["samples"],2,s["evaluationContext"]);self.assertEqual(r["result"]["value"],"200")
  s["samples"]["pressure-down"]["sourceTimestamp"]="2000-01-01T00:00:00Z"
  r=preview.run(w,"bounded-pressure-mapping","selected-pressure",s["samples"],2,s["evaluationContext"]);self.assertIn("time.stale-input",{i["code"] for i in r["issues"]});self.assertIsNone(r["result"])
 def test_engineered_candidate_double_transform(self):
  w=load("workspace");w["sources"][0]["definition"]["inputStage"]="already-engineered"
  n=w["graphs"][0]["nodes"][0];w["graphs"][0]["nodes"].append({"nodeId":"rescale","op":"linear","inputs":{"value":{"kind":"node","nodeId":"selected"}},"factor":"2","offset":"0","valueType":"Decimal","unit":n["unit"],"evidenceRefs":n["evidenceRefs"]})
  self.assertIn("mapping.double-transform",{e["ruleCode"] for e in server.findings_for(w)})
 def test_contract(self):server.check_state(load("workspace"))
 def test_immutable(self):
  for p,h in server.contracts.load(ROOT/"docs/verification/p3e-validation.json")["sha256"].items():
   if p.startswith("contracts/"):self.assertEqual(server.contracts.hashed(ROOT/p),h)
 def test_unselected_missing(self):
  s=load("samples");del s["pressure-down"];self.assertEqual(run(s=s)["quality"],"good")
 def test_selected_missing(self):
  s=load("samples");del s["pressure-up"];self.assertIsNone(run(s=s)["result"])
 def test_invalid_index_no_default(self):
  w=load("workspace");n=w["graphs"][0]["nodes"][0];n.update(outOfRange="default-candidate",defaultCandidate=1)
  s=load("samples");s["selector-index"]={"bytesHex":"00"};self.assertIsNone(run(w,s)["result"])
 def test_equal_value_changed_source(self):
  s=load("samples");s["selector-index"]={"bytesHex":"0100"};s["pressure-down"]=s["pressure-up"];r=run(s=s);self.assertTrue(r["selections"][0]["sourceChanged"]);self.assertEqual(r["result"]["value"],"100")
 def test_alias_not_changed(self):
  w=load("workspace");n=w["graphs"][0]["nodes"][0];n["inputs"]["candidate1"]=copy.deepcopy(n["inputs"]["candidate0"])
  s=load("samples");s["selector-index"]={"bytesHex":"0100"};self.assertFalse(run(w,s)["selections"][0]["sourceChanged"])
 def test_no_previous(self):
  w=load("workspace");del w["graphs"][0]["nodes"][0]["inputs"]["previousIndex"];s=load("samples");del s["selector-previous"];self.assertIsNone(run(w,s)["selections"][0]["sourceChanged"])
 def test_pure(self):
  w=load("workspace");s=load("samples");before=copy.deepcopy((w,s));self.assertEqual(run(w,s),run(w,s));self.assertEqual((w,s),before)
 def test_sqlite_reopen_and_cas(self):
  with tempfile.TemporaryDirectory() as t:
   st=server.Store(Path(t)/"editor.sqlite3");st.migrate(0,{});st.save(1,load("workspace"));before=st.read();h=server.contracts.hashed(st.path);run();self.assertEqual(server.Store(st.path).read(),before);self.assertEqual(h,server.contracts.hashed(st.path))
   with self.assertRaises(server.Conflict):st.save(1,load("workspace"))
 def test_temporal(self):
  w=load("workspace");b=w["mappings"][0]["mappings"][0];b["temporalPolicy"]=server.contracts.load(ROOT/"fixtures/p3e/timed-workspace.json")["mappings"][0]["mappings"][0]["temporalPolicy"];w["mappings"][0]["schemaVersion"]="2.3.0"
  ctx={"at":"2026-10-17T10:00:00Z","triggerSequence":None}
  s={k:{"value":v,"quality":"good","sourceTimestamp":ctx["at"],"serverTimestamp":ctx["at"],"sequence":None} for k,v in load("samples").items()}
  s["pressure-down"]["quality"]="bad"
  r=preview.run(w,"bounded-pressure-mapping","selected-pressure",s,2,ctx);self.assertEqual(r["quality"],"good",r["issues"]);self.assertNotIn("pressure-down",r["temporal"]["requiredSources"])
  s["pressure-up"]["quality"]="bad";r=preview.run(w,"bounded-pressure-mapping","selected-pressure",s,2,ctx);self.assertFalse(r["selectionValueValidated"]);self.assertEqual(r["selections"][0]["sourceRef"]["id"],"pressure-up");self.assertFalse(any(t["stage"]=="decode" for t in r["trace"]));self.assertIsNone(r["result"]);self.assertIn("quality.bad-input",{i["code"] for i in r["issues"]})
  scenario={"kind":"preview-scenario","schemaVersion":"2.3.0","id":"selector-timed","version":"1.0.0","label":"selector","mappingSetRef":{"id":w["mappings"][0]["id"],"version":w["mappings"][0]["version"]},"mappingId":"selected-pressure","workspaceSha256":sample_quality.digest(w),"evaluationContext":ctx,"samples":s}
  sample_quality.check_scenario(scenario,w)
  with tempfile.TemporaryDirectory() as t:
   st=server.Store(Path(t)/"editor.sqlite3");st.migrate(0,{});st.save(1,w);st.save_scenario(2,0,scenario);self.assertEqual(server.Store(st.path).scenarios()["scenarios"][0]["scenario"],scenario)
def oracle(c):
 def test(self):
  w=load("workspace");s=load("samples");n=w["graphs"][0]["nodes"][0];n["outOfRange"]=c["policy"]
  if c["default"] is not None:n["defaultCandidate"]=c["default"]
  for k,i in (("selector-index",c["index"]),("selector-previous",c["previous"])):s[k]={"bytesHex":i.to_bytes(2,"little").hex()}
  r=run(w,s);self.assertEqual(None if r["result"] is None else r["result"]["value"],c["result"]);self.assertEqual({i["code"] for i in r["issues"]},set(c["codes"]))
 return test
for c in load("cases")["cases"]:setattr(Tests,"test_oracle_"+c["id"].replace("-","_"),oracle(c))
def invalid(change):
 def test(self):
  w=load("workspace");change(w["graphs"][0]["nodes"][0])
  with self.assertRaises(server.Invalid):server.check_state(w)
 return test
for name,change in {
 "gap":lambda n:n["inputs"].update(candidate3=n["inputs"].pop("candidate1")),
 "default":lambda n:n.update(outOfRange="default-candidate",defaultCandidate=2),
 "type":lambda n:n.update(valueType="Float32"),
 "unit":lambda n:n.update(unit={"status":"known","code":"bar"}),
 "node_candidate":lambda n:n["inputs"].update(candidate0={"kind":"node","nodeId":"selected"}),
 "index_unit":lambda n:n["inputs"].update(index=n["inputs"]["candidate0"]),
 "missing_ref":lambda n:n["inputs"]["candidate0"]["sourceRef"].update(id="absent"),
}.items():setattr(Tests,"test_invalid_"+name,invalid(change))

class HTTP(unittest.TestCase):
 def setUp(self):
  import threading
  self.tmp=tempfile.TemporaryDirectory();self.st=server.Store(Path(self.tmp.name)/"editor.sqlite3");self.st.migrate(0,{});self.st.save(1,load("workspace"));self.http=server.make_server(self.st,0);self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()
 def tearDown(self):self.http.shutdown();self.http.server_close();self.thread.join();self.tmp.cleanup()
 def request(self,path,body):
  from urllib.request import Request,urlopen
  return urlopen(Request("http://127.0.0.1:"+str(self.http.server_port)+path,data=json.dumps(body).encode(),headers={"Content-Type":"application/json","X-Tyr-Editor":"1"},method="POST"))
 def test_preview_readonly(self):
  before=self.st.read();h=server.contracts.hashed(self.st.path)
  with self.request("/api/preview",{"revision":2,"mappingSetId":"bounded-pressure-mapping","mappingId":"selected-pressure","samples":load("samples")}) as r:self.assertEqual(json.load(r)["result"]["value"],"100")
  self.assertEqual(before,self.st.read());self.assertEqual(h,server.contracts.hashed(self.st.path))
 def test_stale(self):
  from urllib.error import HTTPError
  with self.assertRaises(HTTPError) as e:self.request("/api/preview",{"revision":1,"mappingSetId":"bounded-pressure-mapping","mappingId":"selected-pressure","samples":load("samples")})
  self.assertEqual(e.exception.code,409)
 def test_invalid_save_atomic(self):
  from urllib.error import HTTPError
  w=load("workspace");w["graphs"][0]["nodes"][0].update(outOfRange="default-candidate",defaultCandidate=30);before=self.st.read()
  with self.assertRaises(HTTPError) as e:self.request("/api/workspace",{"revision":2,"workspace":w})
  self.assertEqual(e.exception.code,422);self.assertEqual(before,self.st.read())
 def test_save_reload_default(self):
  w=load("workspace");w["graphs"][0]["nodes"][0].update(outOfRange="default-candidate",defaultCandidate=1)
  with self.request("/api/workspace",{"revision":2,"workspace":w}) as r:self.assertEqual(json.load(r)["revision"],3)
  self.assertEqual(server.Store(self.st.path).read()["workspace"],w)

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--report",type=Path);a=p.parse_args();r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
 if a.report:server.contracts.save(a.report,{"total":r.testsRun,"passed":r.testsRun-len(r.failures)-len(r.errors),"failures":[str(x) for x in r.failures],"errors":[str(x) for x in r.errors],"sha256":{str(p.relative_to(ROOT)).replace(chr(92),"/"):server.contracts.hashed(p) for p in [*(ROOT/"contracts").rglob("*.json"),*(ROOT/"fixtures/p3f").glob("*"),*(ROOT/"backend").glob("*.py"),*(ROOT/"frontend").glob("*"),ROOT/"scripts/test_p3f.py",ROOT/"scripts/p3a_contracts.py"] if p.is_file()}})
 sys.exit(not r.wasSuccessful())
