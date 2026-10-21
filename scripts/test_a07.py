"""A07 contract, preview, immutable evidence, SQLite/API and independent receiver seam."""
import argparse,copy,json,sys,tempfile,unittest,threading,shutil
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from unittest.mock import patch
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/"backend"),str(R/"scripts")]
import server,publication as pub,source_views as views,p3a_contracts as p3,preview,sample_quality as sq,change_review as cr
F=R/"fixtures/a07"
def load(n="workspace"):return server.contracts.load(F/(n+".json"))
def definition(w,id):return next(r["definition"] for r in w["sources"] if r["definition"]["id"]==id)
def change(d,p,value):
    parts=p.strip("/").split("/");a=d
    for key in parts[:-1]:a=a[key]
    a[parts[-1]]=copy.deepcopy(value)
def wire_mutation(folder,case):
    proposal=server.contracts.load(folder/"proposal.json")
    for e in proposal["files"]:
        if e["kind"]=="source-definition" and e["id"]==case["sourceId"]:
            d=server.contracts.load(folder/e["path"]);change(d,case["pointer"],case["value"]);server.contracts.save(folder/e["path"],d);e["sha256"]=server.contracts.hashed(folder/e["path"])
    server.contracts.save(folder/"proposal.json",proposal)
    sub=server.contracts.load(folder/"submission.json");sub["proposalSha256"]=server.contracts.hashed(folder/"proposal.json");server.contracts.save(folder/"submission.json",sub)
class Contract(unittest.TestCase):
    def test_fixture(self):server.check_state(load());self.assertEqual(server.findings_for(load()),[])
    def test_old_60_schemas(self):
        baseline=server.contracts.load(R/"docs/verification/p7-baseline-sha256.json")["sha256"];n=0
        for p,h in baseline.items():
            if p.startswith("contracts/"):self.assertEqual(server.contracts.hashed(R/p),h);n+=1
        self.assertEqual(n,60)
    def test_new_schema_bytes_in_receiver(self):
        for p in (R/"contracts/2.10.0").glob("*.json"):self.assertEqual(p.read_bytes(),(R.parent/"bifrost/core/src/main/resources/mapping-contracts/2.10.0"/p.name).read_bytes())
    def test_old_contract_rejects_new_view(self):
        d=copy.deepcopy(definition(load(),"a07-melsec-alarm"));d["schemaVersion"]="2.7.0";self.assertTrue(server.contracts.validate_schema("source-definition",d))
    def test_legacy_workspace_refuses(self):
        w=load();old={k:w[k] for k in server.EMPTY}
        with self.assertRaises(ValueError):server.check_state(old)
    def test_view_extra_field_refused(self):
        d=copy.deepcopy(definition(load(),"a07-melsec-alarm"));d["view"]["script"]="bad";self.assertTrue(server.contracts.validate_schema("source-definition",d))
    def test_fractional_bit_refused(self):
        d=copy.deepcopy(definition(load(),"a07-melsec-alarm"));d["view"]["bitIndex"]=1.5;self.assertTrue(server.contracts.validate_schema("source-definition",d))
    def test_depth_limit(self):
        docs=views.index(r["definition"] for r in load()["sources"]);last=docs[("a07-melsec-word","1.0.0")]
        for i in range(17):
            d=copy.deepcopy(last);d.update(id="alias-"+str(i),schemaVersion="2.10.0",viewOf={"id":last["id"],"version":"1.0.0"},view={"kind":"alias"});docs[(d["id"],d["version"])]=d;last=d
        self.assertIn("view.depth",views.rules(last,docs))
    def test_parent_change_requires_review(self):
        w=load();target=cr.target(w,"mapping-set:a07-melsec-mapping");changed=copy.deepcopy(w);definition(changed,"a07-melsec-word")["access"]["addressIndex"]=4000
        self.assertNotEqual(target["dependencySha256"],cr.target(changed,"mapping-set:a07-melsec-mapping")["dependencySha256"])
        self.assertIn("view.snapshot-mismatch",{x["ruleCode"] for x in server.findings_for(changed)})
    def test_view_not_writable(self):
        d=copy.deepcopy(definition(load(),"a07-melsec-alarm"));d["accessMode"]="read-write";self.assertTrue(server.contracts.validate_schema("source-definition",d))
    def test_float_word_refused(self):
        w=load();d=definition(w,"a07-ab-word");d["rawRepresentation"]["valueType"]="Float32"
        self.assertIn("view.integer-required",views.rules(definition(w,"a07-ab-word-alias"),views.index(r["definition"] for r in w["sources"])))
    def test_array_word_refused(self):
        w=load();definition(w,"a07-ab-word")["fixedArray"]={}
        self.assertIn("view.scalar-word-required",views.rules(definition(w,"a07-ab-word-alias"),views.index(r["definition"] for r in w["sources"])))
class Preview(unittest.TestCase):
    def test_independent_oracles(self):
        w=load()
        for case in load("oracles")["cases"]:
            prefix=case["mappingSetId"].split("-")[1]
            for mid,expected in case["expected"].items():
                result=preview.run(w,case["mappingSetId"],prefix+"-"+mid,case["samples"],9)
                self.assertEqual(result["quality"],"good",result);self.assertEqual(result["result"]["value"],expected)
                self.assertEqual(result["requiredSources"],list(case["samples"]))
    def test_false_bit(self):
        w=load();r=preview.run(w,"a07-melsec-mapping","melsec-running",{"a07-melsec-word":{"bytesHex":"0080"}},0);self.assertIs(r["result"]["value"],False)
    def test_view_override_refused(self):
        samples={"a07-melsec-word":{"bytesHex":"0580"},"a07-melsec-alarm":{"typedValue":False}}
        r=preview.run(load(),"a07-melsec-mapping","melsec-alarm",samples,0);self.assertIsNone(r["result"]);self.assertIn("sample.view-override",{i["code"] for i in r["issues"]})
    def test_one_root_decode_and_chain_trace(self):
        r=preview.run(load(),"a07-melsec-mapping","melsec-alarm-alias",{"a07-melsec-word":{"bytesHex":"0580"}},0)
        self.assertEqual([s["stage"] for s in r["trace"]].count("decode"),1);self.assertTrue({"view:alias","view:bit"}.issubset({s["stage"] for s in r["trace"]}))
    def test_missing_root(self):
        r=preview.run(load(),"a07-melsec-mapping","melsec-alarm",{},0);self.assertEqual(r["quality"],"bad");self.assertIsNone(r["result"])
    def test_bad_quality_uses_root(self):
        w=load();m=w["mappings"][-1]["mappings"][-1];m["temporalPolicy"]={"assembly":"latest-within-window","timestampBasis":"source","maxAgeMs":1000,"maxSkewMs":100,"uncertainInput":"propagate","futureToleranceMs":0}
        # Reuse the supported temporal policy vocabulary from an existing fixture.
        policy=server.contracts.load(R/"fixtures/p3d/workspace.json")["mappings"][0]["mappings"][0]["temporalPolicy"];m["temporalPolicy"]=copy.deepcopy(policy)
        sample={"value":{"bytesHex":"0580"},"quality":"bad","sourceTimestamp":"2026-10-17T00:00:00Z","serverTimestamp":None,"sequence":None}
        r=preview.run(w,w["mappings"][-1]["id"],m["mappingId"],{"a07-melsec-word":sample},0,{"at":"2026-10-17T00:00:00Z","triggerSequence":None})
        self.assertEqual(r["quality"],"bad");self.assertEqual(r["temporal"]["requiredSources"],["a07-melsec-word"]);self.assertIn("quality.bad-input",{i["code"] for i in r["issues"]})
    def test_signed_high_bit(self):
        w=load()
        for row in w["sources"]:
            d=row["definition"]
            if d["id"].startswith("a07-melsec-"):d["rawRepresentation"]["valueType"]="Int16"
        r=preview.run(w,"a07-melsec-mapping","melsec-alarm",{"a07-melsec-word":{"bytesHex":"0080"}},0);self.assertIs(r["result"]["value"],True)
class StorageAPI(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=server.Store(Path(self.tmp.name)/"db.sqlite3");self.store.migrate(0,{});self.store.save(1,load());self.http=server.make_server(self.store,0);self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):self.http.shutdown();self.http.server_close();self.thread.join();self.tmp.cleanup()
    def request(self,path,body=None,method=None):
        with urlopen(Request("http://127.0.0.1:"+str(self.http.server_port)+path,data=json.dumps(body).encode() if body is not None else None,headers={"Content-Type":"application/json","X-Tyr-Editor":"1"},method=method or ("POST" if body is not None else "GET"))) as r:return json.load(r)
    def test_sqlite_reopen(self):self.assertEqual(server.Store(self.store.path).read()["workspace"],load())
    def test_preview_readonly(self):
        before=self.store.read();r=self.request("/api/preview",{"revision":2,"mappingSetId":"a07-melsec-mapping","mappingId":"melsec-alarm","samples":{"a07-melsec-word":{"bytesHex":"0580"}}});self.assertIs(r["result"]["value"],True);self.assertEqual(before,self.store.read())
    def test_edit_view_save_reload(self):
        w=load();definition(w,"a07-melsec-alarm")["view"]["bitIndex"]=2;self.request("/api/workspace",{"revision":2,"workspace":w},"PUT");self.assertEqual(server.Store(self.store.path).read()["workspace"],w)
    def test_invalid_view_atomic(self):
        before=self.store.read();w=load();definition(w,"a07-melsec-alarm")["view"]["bitIndex"]=16
        with self.assertRaises(HTTPError) as e:self.request("/api/workspace",{"revision":2,"workspace":w},"PUT")
        self.assertEqual(e.exception.code,422);self.assertEqual(before,self.store.read())
    def test_export_root_closure(self):
        adapter=pub.Adapter();r=pub.export(self.store,{"revision":2,"id":"view-proposal","streamId":"mixed-line","proposedBy":"proposer","mappingSetIds":["a07-melsec-mapping"],"includeWrites":False},server.Conflict,server.build_package,adapter)
        p=server.contracts.load(Path(r["path"])/"proposal.json");self.assertEqual(len([e for e in p["files"] if e["kind"]=="source-definition"]),5);self.assertFalse(r["preflightFindings"])
    def test_parent_change_saved_as_unresolved_view(self):
        w=load();definition(w,"a07-melsec-word")["access"]["addressIndex"]=4000
        saved=self.store.save(2,w);self.assertEqual(saved["revision"],3);self.assertEqual(definition(saved["workspace"],"a07-melsec-alarm")["access"]["addressIndex"],3000)
        self.assertIn("view.snapshot-mismatch",{x["ruleCode"] for x in saved["findings"]})
    def test_existing_db_open_bytes_unchanged(self):
        path=Path(self.tmp.name)/"old.sqlite3";src=server.Store(path);src.save(0,server.contracts.load(R/"fixtures/p4b/workspace.json") if False else copy.deepcopy(server.EMPTY))
        before=path.read_bytes();server.Store(path);self.assertEqual(before,path.read_bytes())
    def test_no_execution_routes(self):
        for p in ["/api/sql","/api/write","/api/plc/read","/api/execute"]:
            with self.assertRaises(HTTPError) as e:self.request(p,{})
            self.assertEqual(e.exception.code,404)
def negative(case):
    def test(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"wire";shutil.copytree(F/"wire",p);wire_mutation(p,case)
            errors,_=p3.validate_package(p);self.assertIn(case["expectedRule"],{x["ruleCode"] for x in errors},errors)
    return test
for case in load("cases")["cases"]:setattr(Contract,"test_negative_"+case["id"].replace("-","_"),negative(case))
if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--report",type=Path);opt=a.parse_args();result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if opt.report:server.contracts.save(opt.report,{"total":result.testsRun,"passed":result.testsRun-len(result.errors)-len(result.failures),"failures":[str(x) for x in result.failures],"errors":[str(x) for x in result.errors],"sha256":{p.relative_to(R).as_posix():server.contracts.hashed(p) for p in [*(F).rglob("*"),*(R/"contracts").rglob("*.json"),*(R/"backend").glob("*.py"),*(R/"scripts").glob("*.py"),*(R/"frontend").glob("*")] if p.is_file()}})
    sys.exit(not result.wasSuccessful())
