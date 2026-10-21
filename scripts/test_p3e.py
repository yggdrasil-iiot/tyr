"""P3-E independent fixed-array geometry/value oracles and SQLite/API acceptance."""
import argparse,copy,json,sys,tempfile,threading,unittest
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"backend"))
import server,preview,sample_quality,fixed_arrays
CASES=server.contracts.load(ROOT/"fixtures/p3e/cases.json")["cases"]
def workspace():return server.contracts.load(ROOT/"fixtures/p3e/workspace.json")
def samples():return server.contracts.load(ROOT/"fixtures/p3e/samples.json")
def state_for(c):
    w=workspace()
    if "indices" in c:next(n for g in w["graphs"] if g["id"]=="array-"+c["prefix"]+"-graph" for n in g["nodes"] if n["nodeId"]==c["node"])["indices"]=c["indices"]
    return w
def run(c):
    id="array-pressures-"+c["prefix"];s={id:copy.deepcopy(c.get("sample",samples()[id]))}
    return preview.run(state_for(c),"array-"+c["prefix"]+"-"+c["node"]+"-mapping",c["prefix"]+"-"+c["node"]+"-pressure",s,2)
class Oracles(unittest.TestCase):pass
def oracle(c):
    def test(self):
        w=state_for(c);before=json.dumps(w,sort_keys=True);id="array-pressures-"+c["prefix"];payload={id:copy.deepcopy(c.get("sample",samples()[id]))};raw=copy.deepcopy(payload)
        r=preview.run(w,"array-"+c["prefix"]+"-"+c["node"]+"-mapping",c["prefix"]+"-"+c["node"]+"-pressure",payload,2)
        self.assertEqual(r["quality"],c["expect"]["quality"],r["issues"])
        self.assertEqual(None if r["result"] is None else r["result"]["value"],c["expect"]["result"])
        self.assertTrue(set(c["expect"]["codes"])<={i["code"] for i in r["issues"]},r["issues"])
        if not c["expect"]["codes"]:self.assertEqual(r["issues"],[])
        self.assertEqual(before,json.dumps(w,sort_keys=True));self.assertEqual(raw,payload);self.assertFalse(r["persisted"])
        self.assertEqual(r["sampleSha256"],sample_quality.digest(raw))
        if r["quality"]=="good":
            stages=[x["stage"] for x in r["trace"]];self.assertLess(stages.index("array-index"),stages.index("graph:array-element"));self.assertLess(stages.index("graph:array-element"),stages.index("transform:cast"))
    return test
for c in CASES:setattr(Oracles,"test_"+c["id"].replace("-","_"),oracle(c))
class Contracts(unittest.TestCase):
    def test_fixture(self):
        server.check_state(workspace());self.assertEqual(server.findings_for(workspace()),[])
    def test_meta(self):
        from jsonschema import Draft202012Validator
        for p in (ROOT/"contracts/2.4.0").glob("*.json"):Draft202012Validator.check_schema(server.contracts.load(p))
    def test_older_schemas_unchanged(self):
        for p,h in server.contracts.load(ROOT/"docs/verification/p3d-validation.json")["sha256"].items():
            if p.startswith("contracts/"):self.assertEqual(server.contracts.hashed(ROOT/p),h,p)
    def test_shape_stride_ranges_static(self):
        mutations=[({"lowerBounds":[2147483647,0]},"array.bounds"),({"shape":[2,3],"strides":[1,1]},"array.overlap"),({"strides":[4]},"array.rank"),({"range":{"start":0,"endExclusive":6}},"array.storage-range"),({"range":{"start":1,"endExclusive":8}},"array.storage-range"),({"strideUnit":"byte"},"array.stride-unit"),({"shape":[17,17]},"array.count"),({"strides":[4096,1],"range":{"start":0,"endExclusive":4097}},"array.buffer-limit")]
        for change,code in mutations:
            w=workspace();d=w["sources"][0]["definition"];d["fixedArray"].update(change)
            self.assertIn(code,server.contracts.source_rules(d))
            with self.assertRaises(server.Invalid):server.check_state(w)
    def test_invalid_index_save_blocked(self):
        for id in ("below-lower","at-exclusive-upper","db-column-too-high","wrong-rank","fraction-index"):
            with self.assertRaises(server.Invalid):server.check_state(state_for(next(c for c in CASES if c["id"]==id)))
    def test_unit_and_declared_type(self):
        for key,value,code in (("unit",{"status":"known","code":"bar"},"graph.output-unit"),("valueType","UInt16","graph.output-type")):
            w=workspace();w["graphs"][0]["nodes"][0][key]=value
            self.assertIn(code,{e["ruleCode"] for e in server.findings_for(w)})
    def test_no_implicit_array_scalar_cast(self):
        w=workspace();b=w["mappings"][0]["mappings"][0];b["valueRef"]={"kind":"source","sourceRef":{"id":"array-pressures-ab","version":"1.0.0"}}
        self.assertIn("array.whole-mapping",{e["ruleCode"] for e in server.findings_for(w)})
        with self.assertRaises(server.Invalid):server.check_state(w)
    def test_legacy_workspace_cannot_claim_array_semantics(self):
        w=workspace();legacy={k:w[k] for k in ("equipment","connections","sources","semantics","mappings")};legacy["mappings"]=[]
        with self.assertRaises(server.Invalid):server.check_state(legacy)
    def test_legacy_file_gate_rejects_array_feature(self):
        w=workspace();legacy={k:w[k] for k in ("equipment","connections","sources","semantics","mappings")};legacy["mappings"]=[]
        with tempfile.TemporaryDirectory() as t:
            path=Path(t);server.legacy_build_package(legacy,path)
            self.assertIn("array.legacy-unsupported",{e["ruleCode"] for e in server.contracts.validate_package(path)})
    def test_old_schema_cannot_claim_arrays(self):
        d=workspace()["sources"][0]["definition"];d["schemaVersion"]="2.2.0";self.assertTrue(server.contracts.validate_schema("source-definition",d))
        g=workspace()["graphs"][0];g["schemaVersion"]="2.2.0";self.assertTrue(server.v2.p3.schema_errors("value-graph",g))
    def test_db_and_register_resolved_addresses(self):
        w=workspace();db=w["sources"][2]["definition"];mel=w["sources"][3]["definition"]
        a=fixed_arrays.index(db,[2,12]);b=fixed_arrays.index(mel,[2,12])
        self.assertEqual(a["resolvedAccess"]["byteOffset"],88);self.assertEqual(a["byteOffset"],24)
        self.assertEqual(b["resolvedAccess"]["addressIndex"],7012);self.assertEqual(b["byteOffset"],24)
        self.assertEqual(a["upperBounds"],[2,12]);self.assertEqual(b["upperBounds"],[2,12])
    def test_column_major_not_guessed(self):
        w=workspace();d=w["sources"][0]["definition"];d["fixedArray"].update(shape=[2,2],strides=[1,2],range={"start":0,"endExclusive":4})
        w["graphs"][0]["nodes"][0]["indices"]=[1,0];w["graphs"][0]["nodes"][1]["indices"]=[1,1]
        server.check_state(w)
        r=preview.run(w,"array-ab-first-mapping","ab-first-pressure",{"array-pressures-ab":{"typedValues":["10","20","30","40"]}},0)
        self.assertEqual(r["result"]["value"],"20")
    def test_rank_three(self):
        w=workspace();d=w["sources"][0]["definition"];d["fixedArray"].update(shape=[2,2,2],lowerBounds=[0,0,0],strides=[4,2,1],range={"start":0,"endExclusive":8})
        for n in w["graphs"][0]["nodes"]:n["indices"]=[1,0,1]
        server.check_state(w);r=preview.run(w,"array-ab-first-mapping","ab-first-pressure",{"array-pressures-ab":{"typedValues":["0","1","2","3","4","5","6","7"]}},0)
        self.assertEqual(r["result"]["value"],"5")
    def test_scalar_only_array_node_input_rejected(self):
        w=server.contracts.load(ROOT/"fixtures/p3c/workspace.json");g=w["graphs"][0];g["schemaVersion"]="2.4.0";g["nodes"][0].update(op="array-element",inputs={"value":g["nodes"][0]["inputs"]["left"]},indices=[0],valueType="UInt16")
        self.assertIn("array.input-type",{e["ruleCode"] for e in server.findings_for(w)})
    def test_array_identity_preserves_layout(self):
        w=workspace();g=w["graphs"][0];g["nodes"].insert(0,{"nodeId":"whole","op":"identity","inputs":copy.deepcopy(g["nodes"][0]["inputs"]),"valueType":"FixedArray","unit":w["sources"][0]["definition"]["unit"],"evidenceRefs":copy.deepcopy(w["sources"][0]["definition"]["evidenceRefs"])})
        g["nodes"][1]["inputs"]={"value":{"kind":"node","nodeId":"whole"}}
        server.check_state(w);r=preview.run(w,"array-ab-first-mapping","ab-first-pressure",{"array-pressures-ab":samples()["array-pressures-ab"]},0);self.assertEqual(r["result"]["value"],"100")
    def test_same_array_two_indices_in_derived_graph(self):
        w=workspace();g=w["graphs"][0];g["nodes"].append({"nodeId":"difference","op":"subtract","inputs":{"left":{"kind":"node","nodeId":"last"},"right":{"kind":"node","nodeId":"first"}},"valueType":"Decimal","unit":w["sources"][0]["definition"]["unit"],"evidenceRefs":copy.deepcopy(w["sources"][0]["definition"]["evidenceRefs"])})
        w["mappings"][0]["mappings"][0]["valueRef"]["nodeId"]="difference";server.check_state(w)
        r=preview.run(w,"array-ab-first-mapping","ab-first-pressure",{"array-pressures-ab":samples()["array-pressures-ab"]},0)
        self.assertEqual(r["result"]["value"],"120");self.assertEqual(sum(t["stage"]=="array-input" for t in r["trace"]),1)
    def test_elements_do_not_mutate_base_access(self):
        d=workspace()["sources"][2]["definition"];before=copy.deepcopy(d);scalar,_,_=fixed_arrays.select(d,samples()["array-pressures-db"],[2,12]);self.assertEqual(d,before);self.assertEqual(scalar["access"]["byteOffset"],88);self.assertNotIn("fixedArray",scalar)
    def test_temporal_typed_array(self):
        w=server.contracts.load(ROOT/"fixtures/p3e/timed-workspace.json");s=server.contracts.load(ROOT/"fixtures/p3e/scenario.json")
        server.check_state(w);sample_quality.check_scenario(s,w)
        r=preview.run(w,s["mappingSetRef"]["id"],s["mappingId"],s["samples"],0,s["evaluationContext"])
        self.assertEqual(r["quality"],"good");self.assertEqual(r["result"]["value"],"100");self.assertEqual(r["temporal"]["requiredSources"],["array-pressures-ab"])
        s["samples"]["array-pressures-ab"]["quality"]="bad"
        r=preview.run(w,s["mappingSetRef"]["id"],s["mappingId"],s["samples"],0,s["evaluationContext"]);self.assertEqual(r["quality"],"bad");self.assertIsNone(r["result"])
    def test_missing_array_sample(self):
        r=preview.run(workspace(),"array-ab-first-mapping","ab-first-pressure",{},0);self.assertIn("sample.missing",{i["code"] for i in r["issues"]})
    def test_unsupported_codec_array(self):
        d=workspace()["sources"][3]["definition"];d["rawRepresentation"]["codec"]={"kind":"bcd16"}
        self.assertIn("array.element-unsupported",server.contracts.source_rules(d))
    def test_flat_array_is_not_native_structure(self):
        w=workspace();w["sources"][0]["definition"]["fixedArray"]["memberFields"]=["x","y"]
        with self.assertRaises(server.Invalid):server.check_state(w)
class StorageAPI(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=server.Store(Path(self.tmp.name)/"editor.sqlite3");self.store.migrate(0,{});self.store.save(1,workspace())
        self.http=server.make_server(self.store,0);self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start();self.url="http://127.0.0.1:"+str(self.http.server_port)
    def tearDown(self):self.http.shutdown();self.http.server_close();self.thread.join();self.tmp.cleanup()
    def request(self,path,body=None,origin=None):
        h={"Content-Type":"application/json","X-Tyr-Editor":"1"}
        if origin:h["Origin"]=origin
        return urlopen(Request(self.url+path,data=None if body is None else json.dumps(body).encode(),headers=h,method="GET" if body is None else "POST"))
    def test_reopen_full_definition(self):self.assertEqual(server.Store(self.store.path).read()["workspace"],workspace())
    def test_edit_index_and_reopen(self):
        w=workspace();w["graphs"][0]["nodes"][0]["indices"]=[0,1];self.store.save(2,w);self.assertEqual(server.Store(self.store.path).read()["workspace"],w)
    def test_invalid_index_atomic(self):
        before=self.store.read()
        with self.assertRaises(server.Invalid):self.store.save(2,state_for(next(c for c in CASES if c["id"]=="at-exclusive-upper")))
        self.assertEqual(before,self.store.read())
    def test_preview_readonly(self):
        before=self.store.read();digest=server.contracts.hashed(self.store.path)
        with self.request("/api/preview",{"revision":2,"mappingSetId":"array-melsec-last-mapping","mappingId":"melsec-last-pressure","samples":{"array-pressures-melsec":samples()["array-pressures-melsec"]}}) as r:report=json.load(r)
        self.assertEqual(report["result"]["value"],"220");self.assertEqual(before,self.store.read());self.assertEqual(digest,server.contracts.hashed(self.store.path))
    def test_index_probe_readonly_and_range(self):
        digest=server.contracts.hashed(self.store.path)
        for indices,quality in (([2,12],"good"),([2,13],"bad")):
            with self.request("/api/array-index",{"revision":2,"sourceRef":{"id":"array-pressures-db","version":"1.0.0"},"indices":indices}) as r:report=json.load(r)
            self.assertEqual(report["quality"],quality);self.assertFalse(report["persisted"])
            if quality=="good":self.assertEqual(report["layout"]["resolvedAccess"]["byteOffset"],88)
            else:self.assertEqual(report["issues"][0]["code"],"array.index-range")
        self.assertEqual(digest,server.contracts.hashed(self.store.path))
    def test_probe_stale_and_foreign_origin(self):
        b={"revision":1,"sourceRef":{"id":"array-pressures-db","version":"1.0.0"},"indices":[1,10]}
        with self.assertRaises(HTTPError) as e:self.request("/api/array-index",b)
        self.assertEqual(e.exception.code,409)
        b["revision"]=2
        with self.assertRaises(HTTPError) as e:self.request("/api/array-index",b,"https://other.example")
        self.assertEqual(e.exception.code,403)
    def test_timed_scenario_save_reopen(self):
        w=server.contracts.load(ROOT/"fixtures/p3e/timed-workspace.json");s=server.contracts.load(ROOT/"fixtures/p3e/scenario.json")
        self.store.save(2,w);self.store.save_scenario(3,0,s)
        self.assertEqual(server.Store(self.store.path).scenarios()["scenarios"][0]["scenario"],s)
    def test_legacy_scenario_rejected_for_typed_array(self):
        w=server.contracts.load(ROOT/"fixtures/p3e/timed-workspace.json");s=server.contracts.load(ROOT/"fixtures/p3e/scenario.json");s["schemaVersion"]="2.3.0";self.store.save(2,w)
        with self.assertRaises(ValueError):self.store.save_scenario(3,0,s)
    def test_assets(self):
        for path in ("/arrays.js","/preview.js","/quality.js"):
            with self.request(path) as r:self.assertEqual(r.status,200)
    def test_revision_conflict(self):
        before=self.store.read()
        with self.assertRaises(server.Conflict):self.store.save(1,workspace())
        self.assertEqual(before,self.store.read())
    def test_no_device_route(self):
        with self.assertRaises(HTTPError) as e:self.request("/api/plc/read")
        self.assertEqual(e.exception.code,404)
def main():
    p=argparse.ArgumentParser();p.add_argument("--report",type=Path);a=p.parse_args()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if a.report:
        files=[*(ROOT/"fixtures/p3e").rglob("*"),*(ROOT/"contracts").rglob("*.json"),*(ROOT/"backend").glob("*.py"),*(ROOT/"frontend").glob("*"),*(ROOT/"scripts").glob("*.py")]
        server.contracts.save(a.report,{"scope":"P3-E bounded fixed scalar arrays; no native structures/dynamic indices/device communication","total":result.testsRun,"passed":result.testsRun-len(result.failures)-len(result.errors),"oracleCases":len(CASES),"failures":[str(x) for x in result.failures],"errors":[str(x) for x in result.errors],"sha256":{str(p.relative_to(ROOT)).replace(chr(92),"/"):server.contracts.hashed(p) for p in files if p.is_file()}})
    return not result.wasSuccessful()
if __name__=="__main__":sys.exit(main())
