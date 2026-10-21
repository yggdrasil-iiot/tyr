"""P3-C independent pressure oracles, contracts and SQLite/API boundaries."""
import argparse,copy,json,sys,tempfile,threading,unittest
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"backend"))
import server,preview
import p3a_contracts as p3
CASES=server.contracts.load(ROOT/"fixtures/p3c/cases.json")["cases"]
def workspace():return server.contracts.load(ROOT/"fixtures/p3c/workspace.json")
def state_for(c):
    w=workspace();v=c["variant"];change=c.get("change",{})
    up=w["sources"][0]["definition"]
    if "unit" in change:up["unit"]={"status":"unknown"} if change["unit"]=="unknown" else {"status":"known","code":change["unit"]}
    if change.get("bool"):
        up["access"]["bitOffset"]=0;up["rawRepresentation"]["bitCoordinate"]={"kind":"decoded-value"}
    if change.get("engineered"):up["inputStage"]="already-engineered"
    graph=next(g for g in w["graphs"] if g["id"]=="pressure-"+v)
    if "factor" in change:graph["nodes"][0]["factor"]=change["factor"]
    if "outputUnit" in change:graph["nodes"][-1]["unit"]["code"]=change["outputUnit"]
    b=next(m for m in w["mappings"] if m["id"]=="pressure-"+v+"-mapping")["mappings"][0]
    if "rounding" in change:b["transform"][0]["rounding"]=change["rounding"]
    if "cast" in change:
        b["transform"][0]["to"]=change["cast"];w["semantics"][0]["members"][0]["valueType"]=change["cast"]
    return w
def run(c):return preview.run(state_for(c),"pressure-"+c["variant"]+"-mapping",c["variant"]+"-difference",c["samples"],2)
class Oracles(unittest.TestCase):pass
def oracle(c):
    def test(self):
        w=state_for(c);before=json.dumps(w,sort_keys=True)
        r=preview.run(w,"pressure-"+c["variant"]+"-mapping",c["variant"]+"-difference",c["samples"],2)
        self.assertEqual(r["quality"],c["expect"]["quality"],r["issues"])
        self.assertEqual(None if r["result"] is None else r["result"]["value"],c["expect"]["value"])
        self.assertTrue(set(c["expect"]["codes"])<={i["code"] for i in r["issues"]},r["issues"])
        self.assertEqual(before,json.dumps(w,sort_keys=True));self.assertFalse(r["persisted"])
        if r["quality"]=="good":
            stages=[t["stage"] for t in r["trace"]]
            self.assertLess(stages.index("graph:subtract"),stages.index("transform:cast"))
            if c["variant"]=="mixed":self.assertLess(stages.index("graph:unit-convert"),stages.index("graph:subtract"))
    return test
for c in CASES:setattr(Oracles,"test_"+c["id"].replace("-","_"),oracle(c))
class Contracts(unittest.TestCase):
    def test_fixture_valid(self):
        w=workspace();server.check_state(w);self.assertEqual(server.findings_for(w),[])
    def test_meta_schemas(self):
        from jsonschema import Draft202012Validator
        for p in (ROOT/"contracts/2.2.0").glob("*.json"):Draft202012Validator.check_schema(server.contracts.load(p))
    def test_older_schemas_unchanged(self):
        report=server.contracts.load(ROOT/"docs/verification/p3b-validation.json")
        for path,digest in report["sha256"].items():
            if path.startswith(("contracts/1.","contracts/2.0.0/","contracts/2.1.0/")):
                self.assertEqual(server.contracts.hashed(ROOT/path),digest,path)
    def test_legacy_cannot_claim_subtract(self):
        w=workspace();g=w["graphs"][0];g["schemaVersion"]="2.0.0"
        self.assertTrue(p3.schema_errors("value-graph",g))
    def test_static_unit_type_output(self):
        for id,code in [("mixed-units-rejected","graph.input-unit"),("unknown-unit-rejected","graph.input-unit"),("bool-rejected","graph.input-type"),("output-unit-rejected","graph.output-unit")]:
            w=state_for(next(c for c in CASES if c["id"]==id))
            self.assertIn(code,{e["ruleCode"] for e in server.findings_for(w)})
            with self.assertRaises(server.Invalid):server.check_state(w)
    def test_affine_temperature_not_guessed(self):
        w=workspace()
        for s in w["sources"][:2]:s["definition"]["unit"]={"status":"known","code":"Cel"}
        g=w["graphs"][0];g["nodes"][0]["unit"]={"status":"known","code":"Cel"}
        self.assertIn("graph.input-unit",{e["ruleCode"] for e in server.findings_for(w)})
    def test_missing_extra_ports(self):
        for edit in ("missing","extra"):
            g=workspace()["graphs"][0]
            if edit=="missing":g["nodes"][0]["inputs"].pop("right")
            else:g["nodes"][0]["inputs"]["unexpected"]=copy.deepcopy(g["nodes"][0]["inputs"]["left"])
            self.assertTrue(p3.schema_errors("value-graph",g))
    def test_unknown_operation(self):
        g=workspace()["graphs"][0];g["nodes"][0]["op"]="eval"
        self.assertTrue(p3.schema_errors("value-graph",g))
    def test_cycle(self):
        w=workspace();w["graphs"][0]["nodes"][0]["inputs"]["left"]={"kind":"node","nodeId":"difference"}
        self.assertIn("graph.cycle",{e["ruleCode"] for e in server.findings_for(w)})
    def test_missing_reference(self):
        w=workspace();w["graphs"][0]["nodes"][0]["inputs"]["left"]["sourceRef"]["version"]="9.0.0"
        self.assertIn("reference.missing",{e["ruleCode"] for e in server.findings_for(w)})
    def test_lineage_evidence(self):
        w=workspace();w["graphs"][0]["nodes"][0]["evidenceRefs"]=w["graphs"][0]["nodes"][0]["evidenceRefs"][:1]
        self.assertIn("graph.evidence-incomplete",{e["ruleCode"] for e in server.findings_for(w)})
    def test_three_inputs_by_composition(self):
        w=workspace();g=w["graphs"][0];n=copy.deepcopy(g["nodes"][0]);n["nodeId"]="second"
        third=copy.deepcopy(w["sources"][1]);d=third["definition"];d["id"]="pressure-third"
        d["rawAddressText"]="D4000";d["access"]["addressIndex"]=4000;d["evidenceRefs"][0]["artifactId"]="manual-pressure-third"
        w["sources"].append(third)
        n["inputs"]={"left":{"kind":"node","nodeId":"difference"},"right":{"kind":"source","sourceRef":{"id":"pressure-third","version":"1.0.0"}}}
        n["evidenceRefs"]+=copy.deepcopy(d["evidenceRefs"]);g["nodes"].append(n)
        binding=w["mappings"][0]["mappings"][0];binding["valueRef"]["nodeId"]="second";binding["evidenceRefs"]+=copy.deepcopy(d["evidenceRefs"])
        server.check_state(w)
        r=preview.run(w,"pressure-direct-mapping","direct-difference",{"pressure-up":{"bytesHex":"9600"},"pressure-down":{"bytesHex":"1400"},"pressure-third":{"bytesHex":"0a00"}},0)
        self.assertEqual(r["result"]["value"],"120")
    def test_pressure_mapping_unit_conversion(self):
        w=workspace();b=w["mappings"][0]["mappings"][0]
        b["transform"].insert(0,{"op":"unit-convert","from":"kPa","to":"Pa"})
        b["outputUnit"]={"status":"known","code":"Pa"}
        # Other mappings intentionally remain draft unit conflicts; use isolated fixture.
        w["mappings"]=w["mappings"][:1];w["targets"]=w["targets"][:1];w["graphs"]=w["graphs"][:1]
        w["semantics"][0]["members"][0]["unit"]={"status":"known","code":"Pa"}
        server.check_state(w);r=preview.run(w,"pressure-direct-mapping","direct-difference",CASES[0]["samples"],0)
        self.assertEqual(r["result"]["value"],"50000")
    def test_four_source_profiles_same_derivation(self):
        # Separate fixed samples: all four profiles converge to the same pressure meaning.
        for profile in server.contracts.PROFILES:
            w=workspace();w["graphs"]=w["graphs"][:1];w["mappings"]=w["mappings"][:1];w["targets"]=w["targets"][:1];w["sources"]=w["sources"][:2]
            w["connections"][0]["accessProfileRef"]=profile
            samples={}
            for i,row in enumerate(w["sources"]):
                d=row["definition"];d["accessProfileRef"]=profile
                if profile=="ab-logix-symbol-v1":
                    d["access"]={"kind":"symbol","symbolPath":["PressureUp","PressureDown"][i]}
                elif profile=="s7-1500-opcua-v1":
                    d["access"]={"kind":"opcua-node","namespaceUri":"urn:tyr:fixture:pressure","identifierType":"string","identifier":["PressureUp","PressureDown"][i]}
                elif profile=="s7-300-db-v1":
                    d["access"]={"kind":"db-offset","dbNumber":10,"byteOffset":i*2,"byteLength":2,"bitOffset":None}
                if profile in ("ab-logix-symbol-v1","s7-1500-opcua-v1"):
                    d["addressRadix"]=None;d["rawRepresentation"]={"mode":"typed","valueType":"UInt16"}
                    samples[d["id"]]={"typedValue":["150","100"][i]}
                else:
                    if profile=="s7-300-db-v1":d["addressRadix"]=None
                    samples[d["id"]]={"bytesHex":["9600","6400"][i]}
            server.check_state(w)
            r=preview.run(w,"pressure-direct-mapping","direct-difference",samples,0)
            self.assertEqual(r["quality"],"good",r["issues"]);self.assertEqual(r["result"]["value"],"50")
class StorageAPI(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=server.Store(Path(self.tmp.name)/"editor.sqlite3")
        self.store.migrate(0,{});self.store.save(1,workspace())
        self.http=server.make_server(self.store,0);self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()
        self.url="http://127.0.0.1:"+str(self.http.server_port)
    def tearDown(self):
        self.http.shutdown();self.http.server_close();self.thread.join();self.tmp.cleanup()
    def request(self,path,body,method="POST"):
        return urlopen(Request(self.url+path,data=json.dumps(body).encode(),method=method,headers={"Content-Type":"application/json","X-Tyr-Editor":"1"}))
    def body(self,c=CASES[2]):
        return {"revision":2,"mappingSetId":"pressure-"+c["variant"]+"-mapping","mappingId":c["variant"]+"-difference","samples":c["samples"]}
    def test_preview_readonly(self):
        before=self.store.read();digest=server.contracts.hashed(self.store.path)
        with self.request("/api/preview",self.body()) as r:report=json.load(r)
        self.assertEqual(report["result"]["value"],"50")
        self.assertEqual(before,self.store.read());self.assertEqual(digest,server.contracts.hashed(self.store.path))
    def test_roundtrip_reopen(self):
        self.assertEqual(server.Store(self.store.path).read()["workspace"],workspace())
    def test_update_roundtrip(self):
        w=workspace();w["graphs"][0]["nodes"][0]["inputs"]["left"],w["graphs"][0]["nodes"][0]["inputs"]["right"]=w["graphs"][0]["nodes"][0]["inputs"]["right"],w["graphs"][0]["nodes"][0]["inputs"]["left"]
        with self.request("/api/workspace",{"revision":2,"workspace":w},"PUT") as r:self.assertEqual(json.load(r)["revision"],3)
        self.assertEqual(server.Store(self.store.path).read()["workspace"],w)
    def test_stale_save_atomic(self):
        before=self.store.read()
        with self.assertRaises(server.Conflict):self.store.save(1,workspace())
        self.assertEqual(before,self.store.read())
    def test_invalid_save_atomic(self):
        before=self.store.read();w=state_for(next(c for c in CASES if c["id"]=="mixed-units-rejected"))
        with self.assertRaises(server.Invalid):self.store.save(2,w)
        self.assertEqual(before,self.store.read())
    def test_missing_sample_http(self):
        with self.request("/api/preview",self.body(next(c for c in CASES if c["id"]=="missing-downstream"))) as r:report=json.load(r)
        self.assertEqual(report["quality"],"bad");self.assertIsNone(report["result"]);self.assertEqual(self.store.read()["revision"],2)
    def test_stale_preview(self):
        b=self.body();b["revision"]=1
        with self.assertRaises(HTTPError) as e:self.request("/api/preview",b)
        self.assertEqual(e.exception.code,409)
    def test_old_workspace_still_loads(self):
        w=server.contracts.load(ROOT/"fixtures/p3a/workspace-v2.json")
        self.store.save(2,w);self.assertEqual(server.Store(self.store.path).read()["workspace"],w)
    def test_no_device_route(self):
        with self.assertRaises(HTTPError) as e:urlopen(self.url+"/api/plc/read")
        self.assertEqual(e.exception.code,404)
def main():
    p=argparse.ArgumentParser();p.add_argument("--report",type=Path);a=p.parse_args()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if a.report:
        files=[*(ROOT/"fixtures/p3c").rglob("*"),*(ROOT/"contracts").rglob("*.json"),*(ROOT/"backend").glob("*.py"),*(ROOT/"frontend").glob("*"),*(ROOT/"scripts").glob("*.py")]
        server.contracts.save(a.report,{"scope":"P3-C virtual derived pressure; no device communication","total":result.testsRun,"passed":result.testsRun-len(result.failures)-len(result.errors),"failures":[str(f) for f in result.failures],"errors":[str(e) for e in result.errors],"oracleCases":len(CASES),"sha256":{str(p.relative_to(ROOT)).replace(chr(92),"/"):server.contracts.hashed(p) for p in files if p.is_file()}})
    return not result.wasSuccessful()
if __name__=="__main__":sys.exit(main())
