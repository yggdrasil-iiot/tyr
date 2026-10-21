"""P3-D deterministic virtual time/quality oracles and SQLite/API acceptance."""
import argparse,copy,json,sys,tempfile,threading,unittest
from contextlib import closing
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"backend"))
import server,preview,sample_quality
CASES=server.contracts.load(ROOT/"fixtures/p3d/cases.json")["cases"]
def workspace():return server.contracts.load(ROOT/"fixtures/p3d/workspace.json")
def scenario():return server.contracts.load(ROOT/"fixtures/p3d/scenario.json")
def state_for(c):
    w=workspace();w["mappings"][0]["mappings"][0]["temporalPolicy"].update(c["policyChange"]);return w
class Oracles(unittest.TestCase):pass
def oracle(c):
    def test(self):
        w=state_for(c);before=json.dumps(w,sort_keys=True);samples=copy.deepcopy(c["samples"])
        r=preview.run(w,"pressure-direct-mapping","direct-difference",samples,2,c["evaluationContext"])
        self.assertEqual(r["quality"],c["expect"]["quality"],r["issues"])
        self.assertEqual(None if r["result"] is None else r["result"]["value"],c["expect"]["result"])
        self.assertTrue(set(c["expect"]["codes"])<={i["code"] for i in r["issues"]},r["issues"])
        if not c["expect"]["codes"]:self.assertEqual(r["issues"],[])
        self.assertEqual(w,state_for(c));self.assertEqual(before,json.dumps(w,sort_keys=True));self.assertEqual(samples,c["samples"])
        self.assertFalse(r["persisted"]);self.assertFalse(r["dataValue"]["atomicSnapshot"]);self.assertEqual(r["dataValue"]["quality"],r["quality"])
        self.assertIsNone(r["dataValue"]["sourceTimestamp"]);self.assertIsNone(r["dataValue"]["serverTimestamp"])
        self.assertEqual(r["evaluationSha256"],sample_quality.digest({"samples":c["samples"],"evaluationContext":c["evaluationContext"]}))
        self.assertEqual(r,preview.run(w,"pressure-direct-mapping","direct-difference",samples,2,c["evaluationContext"]))
        if any(i["severity"]=="error" for i in r["issues"] if i["stage"].startswith("temporal:")):
            self.assertFalse(any(t["stage"]=="graph:subtract" for t in r["trace"]))
    return test
for c in CASES:setattr(Oracles,"test_"+c["id"].replace("-","_"),oracle(c))
class Contracts(unittest.TestCase):
    def test_fixture(self):
        server.check_state(workspace());self.assertEqual(server.findings_for(workspace()),[]);sample_quality.check_scenario(scenario(),workspace())
    def test_meta(self):
        from jsonschema import Draft202012Validator
        for p in (ROOT/"contracts/2.3.0").glob("*.json"):Draft202012Validator.check_schema(server.contracts.load(p))
    def test_older_schemas_unchanged(self):
        hashes=server.contracts.load(ROOT/"docs/verification/p3c-validation.json")["sha256"]
        for path,digest in hashes.items():
            if path.startswith("contracts/"):self.assertEqual(server.contracts.hashed(ROOT/path),digest,path)
    def test_limits_and_unknown_policy(self):
        for k,v in [("maxAgeMs",-1),("maxAgeMs",1.5),("maxSkewMs",86400001),("timestampBasis","auto"),("missingInput","zero"),("badInput","ignore"),("assembly","atomic")]:
            w=workspace();w["mappings"][0]["mappings"][0]["temporalPolicy"][k]=v
            with self.assertRaises(server.Invalid):server.check_state(w)
    def test_old_mapping_cannot_claim_policy(self):
        w=workspace();w["mappings"][0]["schemaVersion"]="2.2.0"
        with self.assertRaises(server.Invalid):server.check_state(w)
    def test_required_metadata_not_implicit(self):
        for key in ("quality","sourceTimestamp","serverTimestamp","sequence"):
            c=copy.deepcopy(CASES[0]);c["samples"]["pressure-up"].pop(key)
            r=preview.run(state_for(c),"pressure-direct-mapping","direct-difference",c["samples"],0,c["evaluationContext"])
            self.assertIn("sample.metadata-required",{i["code"] for i in r["issues"]})
    def test_evaluation_hash_captures_clock(self):
        c=CASES[0];a=preview.run(workspace(),"pressure-direct-mapping","direct-difference",c["samples"],0,c["evaluationContext"])
        b=preview.run(workspace(),"pressure-direct-mapping","direct-difference",c["samples"],0,{"at":"2026-10-17T10:00:01Z","triggerSequence":None})
        self.assertEqual(a["sampleSha256"],b["sampleSha256"]);self.assertNotEqual(a["evaluationSha256"],b["evaluationSha256"]);self.assertEqual(b["quality"],"bad")
    def test_sequence_output(self):
        c=next(c for c in CASES if c["id"]=="trigger-record")
        r=preview.run(state_for(c),"pressure-direct-mapping","direct-difference",c["samples"],2,c["evaluationContext"])
        self.assertEqual(r["dataValue"]["sequence"],"42")
    def test_low_high_temporal_lineage(self):
        w=server.contracts.load(ROOT/"fixtures/p3a/workspace-v2.json");m=w["mappings"][0];m["schemaVersion"]="2.3.0";b=m["mappings"][1]
        b["temporalPolicy"]=copy.deepcopy(workspace()["mappings"][0]["mappings"][0]["temporalPolicy"])
        s=copy.deepcopy(CASES[0]["samples"]);low=s.pop("pressure-up");high=s.pop("pressure-down");low["value"]={"bytesHex":"0100"};high["value"]={"bytesHex":"0200"}
        r=preview.run(w,m["id"],b["mappingId"],{"motor-a-low":low,"motor-a-high":high},0,CASES[0]["evaluationContext"])
        self.assertEqual(r["result"]["value"],"131073");self.assertEqual(r["temporal"]["requiredSources"],["motor-a-high","motor-a-low"])
    def test_derived_graph_all_sources_checked(self):
        w=workspace();s=copy.deepcopy(CASES[0]["samples"]);up=s.pop("pressure-up");up["value"]={"bytesHex":"9600"};s["pressure-bar"]=up
        s["pressure-down"]["quality"]="bad"
        r=preview.run(w,"pressure-mixed-mapping","mixed-difference",s,0,CASES[0]["evaluationContext"])
        self.assertIn("quality.bad-input",{i["code"] for i in r["issues"]});self.assertIsNone(r["result"])
    def test_source_only_policy(self):
        w=workspace();b=w["mappings"][0]["mappings"][0];b["valueRef"]={"kind":"source","sourceRef":{"id":"pressure-up","version":"1.0.0"}}
        r=preview.run(w,"pressure-direct-mapping","direct-difference",{"pressure-up":CASES[0]["samples"]["pressure-up"]},0,CASES[0]["evaluationContext"])
        self.assertEqual(r["result"]["value"],"150");self.assertEqual(r["temporal"]["skewMs"],"0")
    def test_scenario_schema_unknown_fields(self):
        s=scenario();s["executePLC"]=True
        with self.assertRaises(ValueError):sample_quality.check_scenario(s,workspace())
    def test_scenario_calendar_and_unknown_offset(self):
        for text in ("2026-02-30T00:00:00Z","2026-10-17T10:00:00-00:00"):
            s=scenario();s["evaluationContext"]["at"]=text
            with self.assertRaises(ValueError):sample_quality.check_scenario(s,workspace())
    def test_legacy_timing_not_implicitly_checked(self):
        w=server.contracts.load(ROOT/"fixtures/p3c/workspace.json")
        with self.assertRaises(ValueError):preview.run(w,"pressure-direct-mapping","direct-difference",{},0,CASES[0]["evaluationContext"])
    def test_uncertain_and_numeric_loss_both_propagate(self):
        w=workspace();b=w["mappings"][1]["mappings"][0];b["transform"][0]["rounding"]="half-even"
        samples=copy.deepcopy(CASES[0]["samples"]);samples["pressure-up"]["value"]={"bytesHex":"0100"};samples["pressure-up"]["quality"]="uncertain"
        samples["pressure-down"]["value"]={"bytesHex":"0000"}
        r=preview.run(w,"pressure-scaled-mapping","scaled-difference",samples,0,CASES[0]["evaluationContext"])
        self.assertEqual(r["quality"],"uncertain");self.assertEqual(r["dataValue"]["quality"],"uncertain")
        self.assertTrue({"quality.uncertain-input","loss.precision"}<={i["code"] for i in r["issues"]})
        self.assertEqual(r["result"]["value"],"0.1000000000000000055511151231257827021181583404541015625")
    def test_mixed_typed_and_bytes_metadata(self):
        w=workspace();d=w["sources"][0]["definition"];profile="ab-logix-symbol-v1"
        w["connections"].append({"id":"virtual-ab","label":"Virtual AB","equipmentInstanceId":d["equipmentInstanceId"],"accessProfileRef":profile})
        d.update(connectionProfileRef="virtual-ab",accessProfileRef=profile,addressRadix=None,access={"kind":"symbol","symbolPath":"PressureUp"},rawRepresentation={"mode":"typed","valueType":"UInt16"})
        server.check_state(w);samples=copy.deepcopy(CASES[0]["samples"]);samples["pressure-up"]["value"]={"typedValue":"150"}
        r=preview.run(w,"pressure-direct-mapping","direct-difference",samples,0,CASES[0]["evaluationContext"])
        self.assertEqual(r["quality"],"good");self.assertEqual(r["result"]["value"],"50")
class StorageAPI(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=server.Store(Path(self.tmp.name)/"editor.sqlite3");self.store.migrate(0,{});self.store.save(1,workspace())
        self.http=server.make_server(self.store,0);self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start();self.url="http://127.0.0.1:"+str(self.http.server_port)
    def tearDown(self):self.http.shutdown();self.http.server_close();self.thread.join();self.tmp.cleanup()
    def request(self,path,body=None,origin=None):
        headers={"Content-Type":"application/json","X-Tyr-Editor":"1"}
        if origin:headers["Origin"]=origin
        return urlopen(Request(self.url+path,data=None if body is None else json.dumps(body).encode(),headers=headers,method="GET" if body is None else "POST"))
    def body(self,c=CASES[0]):return {"revision":2,"mappingSetId":"pressure-direct-mapping","mappingId":"direct-difference","samples":c["samples"],"evaluationContext":c["evaluationContext"]}
    def test_preview_readonly(self):
        self.store.save_scenario(2,0,scenario());before=self.store.read();rows=self.store.scenarios();digest=server.contracts.hashed(self.store.path)
        with self.request("/api/preview",self.body()) as r:report=json.load(r)
        self.assertEqual(report["quality"],"good");self.assertEqual(report["result"]["value"],"50")
        self.assertEqual(before,self.store.read());self.assertEqual(rows,self.store.scenarios());self.assertEqual(digest,server.contracts.hashed(self.store.path))
    def test_policy_and_scenario_reopen(self):
        self.store.save_scenario(2,0,scenario());reopen=server.Store(self.store.path)
        self.assertEqual(reopen.read()["workspace"],workspace());self.assertEqual(reopen.scenarios()["scenarios"][0]["scenario"],scenario());self.assertFalse(reopen.scenarios()["scenarios"][0]["stale"])
    def test_scenario_http_save_get(self):
        with self.request("/api/scenarios",{"workspaceRevision":2,"scenarioRevision":0,"scenario":scenario()}) as r:self.assertEqual(json.load(r)["scenarioRevision"],1)
        with self.request("/api/scenarios") as r:saved=json.load(r)
        self.assertEqual(saved["scenarios"][0]["scenario"],scenario());self.assertEqual(self.store.read()["revision"],2)
    def test_scenario_CAS_atomic(self):
        self.store.save_scenario(2,0,scenario());before=self.store.scenarios()
        with self.assertRaises(server.Conflict):self.store.save_scenario(2,0,scenario())
        self.assertEqual(before,self.store.scenarios())
    def test_stale_workspace_rejected(self):
        before=self.store.scenarios()
        with self.assertRaises(server.Conflict):self.store.save_scenario(1,0,scenario())
        self.assertEqual(before,self.store.scenarios())
    def test_wrong_reference_and_hash_atomic(self):
        before=self.store.scenarios()
        for key,value in (("workspaceSha256","0"*64),("mappingId","absent"),("mappingSetRef",{"id":"pressure-direct-mapping","version":"9.0.0"})):
            s=scenario();s[key]=value
            with self.assertRaises(ValueError):self.store.save_scenario(2,0,s)
        self.assertEqual(before,self.store.scenarios())
    def test_stale_scenario_preserved(self):
        self.store.save_scenario(2,0,scenario());w=workspace();w["mappings"][0]["mappings"][0]["temporalPolicy"]["maxAgeMs"]=900;self.store.save(2,w)
        row=self.store.scenarios()["scenarios"][0];self.assertTrue(row["stale"]);self.assertEqual(row["scenario"],scenario())
    def test_same_content_resave_not_stale(self):
        self.store.save_scenario(2,0,scenario());self.store.save(2,workspace());self.assertFalse(self.store.scenarios()["scenarios"][0]["stale"])
    def test_invalid_policy_save_atomic(self):
        before=self.store.read();w=workspace();w["mappings"][0]["mappings"][0]["temporalPolicy"]["maxAgeMs"]=-1
        with self.assertRaises(server.Invalid):self.store.save(2,w)
        self.assertEqual(before,self.store.read())
    def test_foreign_origin_blocked(self):
        with self.assertRaises(HTTPError) as e:self.request("/api/scenarios",{"workspaceRevision":2,"scenarioRevision":0,"scenario":scenario()},"https://other.example")
        self.assertEqual(e.exception.code,403)
    def test_stale_preview(self):
        body=self.body();body["revision"]=1
        with self.assertRaises(HTTPError) as e:self.request("/api/preview",body)
        self.assertEqual(e.exception.code,409)
    def test_bad_metadata_is_trace(self):
        with self.request("/api/preview",self.body(next(c for c in CASES if c["id"]=="bad-input-propagated"))) as r:report=json.load(r)
        self.assertEqual(report["quality"],"bad");self.assertIsNone(report["result"])
    def test_legacy_database_additive_upgrade(self):
        import sqlite3
        path=Path(self.tmp.name)/"old.sqlite3"
        with closing(sqlite3.connect(path)) as c:
            c.execute("CREATE TABLE workspace (id INTEGER PRIMARY KEY,revision INTEGER NOT NULL,body TEXT NOT NULL,updated_at TEXT NOT NULL)")
            old=server.contracts.load(ROOT/"fixtures/p3a/workspace-v2.json")
            c.execute("INSERT INTO workspace VALUES (1,7,?,?)",(json.dumps(old),"original-time"));c.commit()
        store=server.Store(path);self.assertEqual(store.read()["revision"],7);self.assertEqual(store.read()["workspace"],old);self.assertEqual(store.scenarios()["scenarios"],[])
    def test_no_device_route(self):
        with self.assertRaises(HTTPError) as e:self.request("/api/plc/read")
        self.assertEqual(e.exception.code,404)
def main():
    p=argparse.ArgumentParser();p.add_argument("--report",type=Path);a=p.parse_args()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if a.report:
        files=[*(ROOT/"fixtures/p3d").rglob("*"),*(ROOT/"contracts").rglob("*.json"),*(ROOT/"backend").glob("*.py"),*(ROOT/"frontend").glob("*"),*(ROOT/"scripts").glob("*.py")]
        server.contracts.save(a.report,{"scope":"P3-D virtual time/quality/sequence and explicitly saved scenarios; no device communication","total":result.testsRun,"passed":result.testsRun-len(result.failures)-len(result.errors),"oracleCases":len(CASES),"failures":[str(x) for x in result.failures],"errors":[str(x) for x in result.errors],"sha256":{str(p.relative_to(ROOT)).replace(chr(92),"/"):server.contracts.hashed(p) for p in files if p.is_file()}})
    return not result.wasSuccessful()
if __name__=="__main__":sys.exit(main())
