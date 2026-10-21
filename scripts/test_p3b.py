"""Independent P3-B byte/transform oracles and read-only API acceptance."""
import argparse,copy,json,sys,tempfile,threading,unittest
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"backend"))
import server,preview
CASES=server.contracts.load(ROOT/"fixtures/p3b/cases.json")["cases"]
def state_for(case):
    state=server.contracts.load(ROOT/"fixtures/p3a/workspace-v2.json")
    if "source" in case:
        row=next(r for r in state["sources"] if r["definition"]["id"]=="motor-a-speed")
        row["definition"]=copy.deepcopy(case["source"]);d=row["definition"]
        if d["connectionProfileRef"] not in {c["id"] for c in state["connections"]}:
            state["connections"].append({"id":d["connectionProfileRef"],"label":"Synthetic","equipmentInstanceId":d["equipmentInstanceId"],"accessProfileRef":d["accessProfileRef"]})
    b=next(b for m in state["mappings"] if m["id"]==case["mappingSetId"] for b in m["mappings"] if b["mappingId"]==case["mappingId"])
    if "transform" in case:b["transform"]=copy.deepcopy(case["transform"])
    if "member" in case:
        member=next(m for m in state["semantics"][0]["members"] if m["memberId"]==b["memberPath"][0]["memberId"])
        member.update(copy.deepcopy(case["member"]));member["semanticId"]="urn:tyr:fixture:"+case["id"];b["outputUnit"]=member["unit"]
    if "graphUnit" in case:
        g=next(g for g in state["graphs"] if g["id"]==b["valueRef"]["graphRef"]["id"])
        for n in g["nodes"]:n["unit"]=copy.deepcopy(case["graphUnit"])
    return state
class Oracles(unittest.TestCase):
    pass
def oracle_test(case):
    def test(self):
        state=state_for(case);before=json.dumps(state,sort_keys=True)
        report=preview.run(state,case["mappingSetId"],case["mappingId"],case["samples"],13)
        self.assertEqual(report["quality"],case["expect"]["quality"])
        expected=case["expect"]["result"]
        actual=report["result"]
        if expected is None:self.assertIsNone(actual)
        else:
            self.assertEqual({k:actual[k] for k in ("value","valueType")},expected)
        codes={i["code"] for i in report["issues"]}
        self.assertTrue(set(case["expect"]["codes"])<=codes,codes)
        if not case["expect"]["codes"]:self.assertEqual(report["issues"],[])
        stages=[t["stage"] for t in report["trace"]];pos=0
        for stage in case["expect"].get("stages",[]):
            pos=stages.index(stage,pos)+1
        self.assertEqual(before,json.dumps(state,sort_keys=True))
        self.assertFalse(report["persisted"]);self.assertEqual(report["deviceCommunication"],"excluded")
    return test
for case in CASES:setattr(Oracles,"test_"+case["id"].replace("-","_"),oracle_test(case))
class Boundaries(unittest.TestCase):
    def test_meta_new_schemas(self):
        from jsonschema import Draft202012Validator
        for p in (ROOT/"contracts/2.1.0").glob("*.json"):Draft202012Validator.check_schema(server.contracts.load(p))
    def test_codec_roundtrip_sqlite(self):
        for id in ("ascii-nul","bcd-valid","s7-date","native-relay","coordinate-native-byte"):
            state=state_for(next(c for c in CASES if c["id"]==id))
            with tempfile.TemporaryDirectory() as t:
                s=server.Store(Path(t)/"test.sqlite3");s.migrate(0,{});s.save(1,state)
                self.assertEqual(server.Store(s.path).read()["workspace"],state)
    def test_native_area_and_legacy_scope(self):
        d=copy.deepcopy(next(c for c in CASES if c["id"]=="native-relay")["source"])
        d["access"].update(addressUnit="word16",wordCount=1);d["access"].pop("bitCount")
        d["rawRepresentation"]["valueType"]="UInt16"
        self.assertIn("source.native-bit-unit",server.contracts.source_rules(d))
        d["schemaVersion"]="1.1.0"
        self.assertEqual(server.contracts.source_rules(d),[])
    def test_reject_codec_and_coordinate_errors(self):
        d=copy.deepcopy(next(c for c in CASES if c["id"]=="ascii-nul")["source"])
        d["rawRepresentation"]["codec"]["kind"]="python"
        self.assertTrue(server.contracts.validate_schema("source-definition",d))
        d=copy.deepcopy(next(c for c in CASES if c["id"]=="coordinate-native-byte")["source"])
        d["rawRepresentation"]["bitCoordinate"]["byteIndex"]=2
        self.assertIn("source.bit-coordinate",server.contracts.source_rules(d))
    def test_typed_boolean_and_nonfinite(self):
        c=copy.deepcopy(next(c for c in CASES if c["id"]=="typed-float32-loss"));c["samples"]={"motor-a-speed":{"typedValue":"NaN"}}
        r=preview.run(state_for(c),c["mappingSetId"],c["mappingId"],c["samples"],0)
        self.assertIn("value.nonfinite",{i["code"] for i in r["issues"]})
    def test_numeric_input_limit(self):
        c=copy.deepcopy(next(c for c in CASES if c["id"]=="typed-float32-loss"));c["samples"]={"motor-a-speed":{"typedValue":"9"*300}}
        r=preview.run(state_for(c),c["mappingSetId"],c["mappingId"],c["samples"],0)
        self.assertEqual(r["quality"],"bad");self.assertIn("sample.numeric",{i["code"] for i in r["issues"]})
    def test_four_profile_speed_convergence(self):
        state=server.contracts.load(ROOT/"fixtures/realistic/workspace.json")
        values=[]
        for prefix,sample in [("ab",{"typedValue":"2400"}),("ua",{"typedValue":"40"}),("db",{"bytesHex":"5dc0"}),("melsec",{"bytesHex":"c05d"})]:
            r=preview.run(state,"motor-object-"+prefix,prefix+"-actual-speed-binding",{prefix+"-actual-speed":sample},0)
            self.assertNotEqual(r["quality"],"bad",r["issues"]);values.append(r["result"]["value"])
        self.assertEqual(values,["2400"]*4)
    def test_underflow_and_boolean(self):
        c=copy.deepcopy(next(c for c in CASES if c["id"]=="typed-float32-loss"));c["samples"]={"motor-a-speed":{"typedValue":"1e-999"}}
        r=preview.run(state_for(c),c["mappingSetId"],c["mappingId"],c["samples"],0)
        self.assertEqual(r["result"]["value"],"0");self.assertIn("loss.underflow",{i["code"] for i in r["issues"]})
        c["source"]["rawRepresentation"]["valueType"]="Boolean";c["source"]["unit"]={"status":"not-applicable"}
        c["member"]={"valueType":"Boolean","unit":{"status":"not-applicable"},"range":None}
        c["transform"]=[{"op":"cast","to":"Boolean","overflow":"error","rounding":"exact"}];c["samples"]={"motor-a-speed":{"typedValue":False}}
        r=preview.run(state_for(c),c["mappingSetId"],c["mappingId"],c["samples"],0)
        self.assertIs(r["result"]["value"],False)
    def test_engineered_identity_graph_is_not_rescaled(self):
        state=server.contracts.load(ROOT/"fixtures/p3a/workspace-v2.json")
        s=next(r["definition"] for r in state["sources"] if r["definition"]["id"]=="motor-a-speed");s["inputStage"]="already-engineered"
        g=state["graphs"][0];g["nodes"]=[{"nodeId":"engineered","op":"identity","inputs":{"value":{"kind":"source","sourceRef":{"id":s["id"],"version":s["version"]}}},"valueType":"UInt16","unit":s["unit"],"evidenceRefs":s["evidenceRefs"]}]
        b=state["mappings"][0]["mappings"][0];b["valueRef"]={"kind":"graph","graphRef":{"id":g["id"],"version":g["version"]},"nodeId":"engineered"}
        report=preview.run(state,"motor-a-mapping",b["mappingId"],{s["id"]:{"bytesHex":"0100"}},0)
        self.assertEqual(report["quality"],"bad");self.assertIn("mapping.double-transform",{i["code"] for i in report["issues"]})
    def test_old_schema_bytes_unchanged(self):
        for rel,digest in server.contracts.load(ROOT/"fixtures/p3a/legacy-schema-baseline.json").items():self.assertEqual(server.contracts.hashed(ROOT/rel),digest)
class API(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=server.Store(Path(self.tmp.name)/"editor.sqlite3")
        self.store.migrate(0,{});self.state=server.contracts.load(ROOT/"fixtures/p3a/workspace-v2.json");self.store.save(1,self.state)
        self.http=server.make_server(self.store,0);self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()
        self.url="http://127.0.0.1:"+str(self.http.server_port)
    def tearDown(self):self.http.shutdown();self.http.server_close();self.thread.join();self.tmp.cleanup()
    def request(self,body,origin=None):
        headers={"Content-Type":"application/json","X-Tyr-Editor":"1"}
        if origin:headers["Origin"]=origin
        return urlopen(Request(self.url+"/api/preview",data=json.dumps(body).encode(),method="POST",headers=headers))
    def body(self):
        return {"revision":2,"mappingSetId":"motor-a-mapping","mappingId":"motor-a-counter-binding","samples":{"motor-a-low":{"bytesHex":"0100"},"motor-a-high":{"bytesHex":"0200"}}}
    def test_read_only_snapshot(self):
        before=self.store.read();digest=server.contracts.hashed(self.store.path)
        with self.request(self.body()) as response:r=json.load(response)
        self.assertEqual(r["result"]["value"],"131073");self.assertEqual(r["quality"],"good")
        self.assertEqual(self.store.read(),before);self.assertEqual(server.contracts.hashed(self.store.path),digest)
    def test_stale_revision(self):
        b=self.body();b["revision"]=1
        with self.assertRaises(HTTPError) as e:self.request(b)
        self.assertEqual(e.exception.code,409);self.assertEqual(self.store.read()["revision"],2)
    def test_foreign_origin(self):
        with self.assertRaises(HTTPError) as e:self.request(self.body(),"https://other.example")
        self.assertEqual(e.exception.code,403)
    def test_missing_mapping_and_extra_field(self):
        for field,value in (("mappingId","absent"),("execute","anything")):
            body=self.body();body[field]=value
            with self.assertRaises(HTTPError) as e:self.request(body)
            self.assertEqual(e.exception.code,422)
    def test_bad_sample_is_trace_not_500(self):
        body=self.body();body["samples"]["motor-a-high"]["bytesHex"]="zz"
        with self.request(body) as response:r=json.load(response)
        self.assertEqual(r["quality"],"bad");self.assertIsNone(r["result"])
    def test_no_device_route(self):
        with self.assertRaises(HTTPError) as e:urlopen(self.url+"/api/plc/read")
        self.assertEqual(e.exception.code,404)
def main():
    p=argparse.ArgumentParser();p.add_argument("--report",type=Path);a=p.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]);result=unittest.TextTestRunner(verbosity=2).run(suite)
    if a.report:
        files=[* (ROOT/"fixtures/p3b").rglob("*"),* (ROOT/"contracts").rglob("*.json"),ROOT/"requirements-contracts.txt",ROOT/"scripts/test_p3b.py",ROOT/"scripts/source_codecs.py",ROOT/"scripts/validate_contracts.py",ROOT/"scripts/p3a_contracts.py",* (ROOT/"backend").glob("*.py"),*(ROOT/"frontend").glob("*")]
        report={"scope":"P3-B virtual bytes/codec/graph/transform/cast preview; no device communication","total":result.testsRun,"passed":result.testsRun-len(result.failures)-len(result.errors),"failures":[str(x) for x in result.failures],"errors":[str(x) for x in result.errors],"oracleCases":len(CASES),"python":sys.version,"tzdata":__import__("importlib.metadata",fromlist=["version"]).version("tzdata"),"sha256":{str(p.relative_to(ROOT)).replace(chr(92),"/"):server.contracts.hashed(p) for p in files if p.is_file()}}
        server.contracts.save(a.report,report)
    return not result.wasSuccessful()
if __name__=="__main__":sys.exit(main())
