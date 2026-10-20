"""P5 independent diff expectations, review invalidation and SQLite/API acceptance."""
import argparse,copy,json,sys,tempfile,threading,unittest,hashlib,sqlite3
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from unittest.mock import patch
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/"backend"),str(R/"scripts")]
import server,change_review as cr,sample_quality as sq
def load(n):return json.loads((R/"fixtures/p5"/(n+".json")).read_text(encoding="utf-8"))
def mutate(w,p,value):
    parts=p.strip("/").split("/");v=w
    for part in parts[:-1]:v=v[int(part)] if isinstance(v,list) else v[part]
    if isinstance(v,list):v[int(parts[-1])]=value
    else:v[parts[-1]]=value
def base(w):return {"id":"base","workspace":copy.deepcopy(w),"workspaceSha256":sq.digest(w)}
def record(w,id="check",key="mapping-set:mixed-tank-mapping"):
    t=cr.target(w,key)
    return {"kind":"change-review","schemaVersion":"2.8.0","id":id,"baselineId":"base","baselineSha256":sq.digest(w),"workspaceSha256":sq.digest(w),"targetKey":key,"targetSha256":t["targetSha256"],"dependencySha256":t["dependencySha256"],"decision":"reviewed","by":"engineer-a","at":"2026-10-17T10:00:00+09:00","rationale":"Checked address, units and document evidence.","evidenceRefs":t["evidenceRefs"],"approval":"not-requested","deviceVerification":"not-performed"}
class Diff(unittest.TestCase):
    def setUp(self):self.w=load("before")
    def test_fixture_valid(self):
        server.check_state(self.w);server.check_state(load("after"))
    def test_unchanged(self):
        d=cr.compare(base(self.w),self.w,2,[]);self.assertEqual(d["changes"],[]);self.assertEqual(d["affected"],[])
    def test_schema_immutability(self):
        old=json.loads((R/"docs/verification/p4b-validation.json").read_text())
        paths={p:h for p,h in old["sha256"].items() if p.startswith("contracts/")}
        self.assertEqual(len(paths),53)
        for p,h in paths.items():self.assertEqual(server.contracts.hashed(R/p),h,p)
    def test_schemas_meta(self):
        from jsonschema import Draft202012Validator
        for p in (R/"contracts/2.8.0").glob("*.json"):Draft202012Validator.check_schema(json.loads(p.read_text()))
    def test_no_network_or_query(self):
        with patch("socket.socket",side_effect=AssertionError("network")),patch("sqlite3.connect",side_effect=AssertionError("SQL")):
            d=cr.compare(base(self.w),load("after"),3,[]);self.assertTrue(d["changes"])
    def test_presentation_not_meaning(self):
        new=copy.deepcopy(self.w);new["sources"][0]["label"]="A new label"
        d=cr.compare(base(self.w),new,3,[])
        self.assertTrue(all(c["category"]=="presentation" and not c["reviewRequired"] for c in d["changes"]))
        self.assertEqual(cr.review_status(record(self.w),new),"needs-review")
    def test_stable_id_removed_added(self):
        new=copy.deepcopy(self.w);new["targets"][0]["id"]="new-tank"
        d=cr.compare(base(self.w),new,3,[]);self.assertEqual({c["change"] for c in d["changes"]},{"removed","added"})
        self.assertEqual(cr.review_status(record(self.w,key="target-instance:mixed-tank"),new),"target-removed")
    def test_unrelated_source_not_invalidated(self):
        new=copy.deepcopy(self.w);extra=copy.deepcopy(new["sources"][0]);extra["definition"]["id"]="unused";extra["label"]="Unused";new["sources"].append(extra)
        self.assertEqual(cr.review_status(record(self.w),new),"reviewed")
    def test_graph_dependency_changed(self):
        new=copy.deepcopy(self.w);new["graphs"][0]["nodes"][0]["inputs"]["left"]["sourceRef"]["id"]="mixed-tag-pressure"
        d=cr.compare(base(self.w),new,3,[]);self.assertTrue(any(x["category"]=="graph" for x in d["changes"]))
        self.assertEqual(cr.review_status(record(self.w),new),"needs-review")
    def test_missing_dependency_invalidates(self):
        new=copy.deepcopy(self.w);new["sources"].pop(0)
        self.assertEqual(cr.review_status(record(self.w),new),"needs-review")
        self.assertIn("source-definition:mixed-plc-pressure",cr.target(new,"mapping-set:mixed-tank-mapping")["missingDependencies"])
    def test_cyclic_closure_bounded(self):
        self.w["graphs"][0]["extra"]={"graphRef":{"id":"mixed-pressure-difference","version":"1.0.0"}}
        self.assertTrue(cr.target(self.w,"value-graph:mixed-pressure-difference")["dependencies"])
    def test_incomplete_vs_conflict(self):
        f=[{"ruleCode":"source.incomplete","path":"x"},{"ruleCode":"semantic.identity-conflict","path":"y"},{"ruleCode":"import.unresolved","path":"z"}]
        d=cr.diagnostics(self.w,f);self.assertEqual([x["classification"] for x in d],["incomplete","definition-conflict","incomplete"])
    def test_same_constant_value_not_physical_collision(self):
        w=copy.deepcopy(self.w);r=copy.deepcopy(w["sources"][1]);r["definition"]["id"]="other-constant";w["sources"].append(r)
        self.assertNotIn("source.shared-access-review",{x["code"] for x in cr.diagnostics(w,[])})
    def test_unconfirmed_is_incomplete(self):
        d=cr.diagnostics(self.w,[{"ruleCode":"source.unit-unconfirmed","path":"x"}]);self.assertEqual(d[0]["classification"],"incomplete")
    def test_duplicate_active_sources_A07(self):
        new=copy.deepcopy(self.w);r=copy.deepcopy(new["sources"][0]);r["definition"]["id"]="other";new["sources"].append(r)
        self.assertIn("source.shared-access-review",{x["code"] for x in cr.diagnostics(new,[])})
        r["definition"]["viewOf"]={"id":"mixed-plc-pressure","version":"1.0.0"}
        self.assertIn("source.shared-access-view",{x["code"] for x in cr.diagnostics(new,[])})
    def test_legacy_explicit_view_not_rejected_by_review(self):
        old=server.contracts.load(R/"fixtures/p2-workspace.json") if (R/"fixtures/p2-workspace.json").exists() else self.w
        # Review comparison retains declarations; the existing authoring gate owns support.
        old=copy.deepcopy(old);old["sources"][0]["definition"]["viewOf"]={"id":"declared-word","version":"1.0.0"}
        self.assertTrue(any(x["classification"]=="declared-view" for x in cr.diagnostics(old,[])))
    def test_import_raw_and_effective_separate(self):
        w=copy.deepcopy(self.w);w["imports"]=[{"id":"file","raw":"template-A","observations":[{"id":"one","derivation":["alias-A"]}]}]
        w["sources"][0]["importRef"]={"batchId":"file","observationId":"one"};new=copy.deepcopy(w);new["imports"][0]["raw"]="template-B"
        d=cr.compare(base(w),new,3,[]);self.assertEqual({c["category"] for c in d["changes"]},{"import-evidence"})
        self.assertTrue(any(a["key"]=="mapping-set:mixed-tank-mapping" and not a["direct"] for a in d["affected"]))
        self.assertEqual(cr.review_status(record(w),new),"needs-review")
    def test_member_ID_not_fuzzy_matched(self):
        new=copy.deepcopy(self.w);new["semantics"][0]["members"][0]["memberId"]="other-member"
        d=cr.compare(base(self.w),new,3,[]);self.assertEqual({c["change"] for c in d["changes"]},{"removed","added"})
    def test_reorder_visible(self):
        new=copy.deepcopy(self.w);new["semantics"][0]["members"].reverse()
        d=cr.compare(base(self.w),new,3,[]);self.assertTrue(any(c["path"].endswith("/order") for c in d["changes"]))
    def test_decode_array_changes(self):
        new=copy.deepcopy(self.w);new["sources"][0]["definition"]["fixedArray"]={"shape":[2],"strides":[1]}
        d=cr.compare(base(self.w),new,3,[]);self.assertTrue(any(c["category"]=="decode" for c in d["changes"]))
    def test_selector_indices_change(self):
        new=copy.deepcopy(self.w);new["graphs"][0]["nodes"][0]["inputs"]["left"]["indices"]=[1]
        d=cr.compare(base(self.w),new,3,[]);self.assertTrue(any(c["category"]=="graph" for c in d["changes"]))
    def test_temporal_policy_change(self):
        new=copy.deepcopy(self.w);new["mappings"][0]["mappings"][0]["temporalPolicy"]={"maxAgeMs":100}
        d=cr.compare(base(self.w),new,3,[]);self.assertTrue(any(c["category"]=="transform" for c in d["changes"]))
    def test_real_array_index_diff(self):
        w=server.contracts.load(R/"fixtures/p3e/workspace.json");new=copy.deepcopy(w);new["graphs"][0]["nodes"][0]["indices"]=[0,1];server.check_state(new)
        d=cr.compare(base(w),new,3,[]);self.assertEqual({x["category"] for x in d["changes"]},{"graph"})
        self.assertTrue(any(x["key"].startswith("mapping-set:") and not x["direct"] for x in d["affected"]))
    def test_real_selector_candidate_diff(self):
        w=server.contracts.load(R/"fixtures/p3f/workspace.json");new=copy.deepcopy(w)
        inputs=new["graphs"][0]["nodes"][0]["inputs"];inputs["candidate0"],inputs["candidate1"]=inputs["candidate1"],inputs["candidate0"];server.check_state(new)
        d=cr.compare(base(w),new,3,[]);self.assertEqual({x["category"] for x in d["changes"]},{"graph"})
        self.assertTrue(any(x["key"].startswith("mapping-set:") for x in d["affected"]))
    def test_real_temporal_diff(self):
        w=server.contracts.load(R/"fixtures/p3d/workspace.json");new=copy.deepcopy(w);new["mappings"][0]["mappings"][0]["temporalPolicy"]["maxAgeMs"]=1234;server.check_state(new)
        d=cr.compare(base(w),new,3,[]);self.assertEqual({x["category"] for x in d["changes"]},{"transform"})
    def test_pure_input_not_mutated(self):
        before=copy.deepcopy(self.w);cr.compare(base(self.w),self.w,2,[]);self.assertEqual(before,self.w)
def oracle(case):
    def test(self):
        new=copy.deepcopy(self.w);mutate(new,case["pointer"],case["value"]);d=cr.compare(base(self.w),new,3,[])
        self.assertIn(case["category"],{c["category"] for c in d["changes"]},d)
        self.assertTrue(set(case["affected"]).issubset({a["key"] for a in d["affected"]}),d)
        if case["category"]=="presentation":self.assertFalse(any(c["reviewRequired"] for c in d["changes"]))
    return test
for case in load("cases")["cases"]:setattr(Diff,"test_oracle_"+case["id"].replace("-","_"),oracle(case))
class Persistence(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/"editor.sqlite3";self.store=server.Store(self.path);self.store.migrate(0,{});self.w=load("before");self.store.save(1,self.w)
        cr.baseline(self.store,{"revision":2,"id":"base","label":"Before revision"},server.Conflict)
    def tearDown(self):self.tmp.cleanup()
    def save(self,d=None,revision=2):return cr.save_review(self.store,{"revision":revision,"record":d or record(self.w)},server.Conflict)
    def test_baseline_append_without_revision(self):
        self.assertEqual(self.store.read()["revision"],2);self.assertEqual(self.store.read()["workspace"],self.w)
    def test_baseline_duplicate_immutable(self):
        with self.assertRaises(server.Conflict):cr.baseline(self.store,{"revision":2,"id":"base","label":"overwrite"},server.Conflict)
        self.assertEqual(cr.baselines(self.store)["baselines"][0]["label"],"Before revision")
    def test_review_reopen(self):
        self.save();s=server.Store(self.path);self.assertEqual(cr.reviews(s)["records"][0]["currentStatus"],"reviewed");self.assertEqual(s.read()["workspace"],self.w)
    def test_review_append_immutable(self):
        self.save();d=record(self.w);d["rationale"]="overwrite"
        with self.assertRaises(server.Conflict):self.save(d)
        self.assertEqual(cr.reviews(self.store)["records"][0]["record"]["rationale"],record(self.w)["rationale"])
    def test_review_revision_conflict_A16(self):
        self.store.save(2,self.w)
        with self.assertRaises(server.Conflict):self.save()
        self.assertEqual(cr.reviews(self.store)["records"],[])
    def test_baseline_revision_conflict(self):
        with self.assertRaises(server.Conflict):cr.baseline(self.store,{"revision":1,"id":"other","label":"stale"},server.Conflict)
    def test_diff_revision_conflict(self):
        with self.assertRaises(server.Conflict):cr.assessment(self.store,{"revision":1,"baselineId":"base"},server.Conflict,server.findings_for)
    def test_latest_review_overrides_without_deleting(self):
        self.save();d=record(self.w,"second");d["decision"]="disputed";self.save(d)
        result=cr.reviews(self.store)
        self.assertTrue(result["records"][0]["superseded"]);self.assertFalse(result["records"][1]["superseded"])
        t=next(t for t in result["targets"] if t["key"]==d["targetKey"]);self.assertEqual(t["reviewStatus"],"disputed")
    def test_review_transitive_stale(self):
        self.save();w=copy.deepcopy(self.w);w["sources"][0]["definition"]["access"]["addressIndex"]=1001;self.store.save(2,w)
        r=cr.reviews(self.store)["records"][0];self.assertEqual(r["currentStatus"],"needs-review");self.assertEqual(r["record"],record(self.w))
    def test_review_forged_hash(self):
        d=record(self.w);d["dependencySha256"]="0"*64
        with self.assertRaises(server.Conflict):self.save(d)
    def test_review_forged_workspace_hash(self):
        d=record(self.w);d["workspaceSha256"]="0"*64
        with self.assertRaises(server.Conflict):self.save(d)
    def test_review_forged_baseline_hash(self):
        d=record(self.w);d["baselineSha256"]="0"*64
        with self.assertRaises(server.Conflict):self.save(d)
    def test_review_unknown_evidence(self):
        d=record(self.w);d["evidenceRefs"][0]["artifactId"]="unrelated"
        with self.assertRaises(ValueError):self.save(d)
    def test_review_empty_evidence(self):
        d=record(self.w);d["evidenceRefs"]=[]
        with self.assertRaises(ValueError):self.save(d)
    def test_review_no_rationale(self):
        d=record(self.w);d["rationale"]="  "
        with self.assertRaises(ValueError):self.save(d)
    def test_review_no_device_claim(self):
        d=record(self.w);d["deviceVerification"]="verified"
        with self.assertRaises(ValueError):self.save(d)
    def test_review_no_approval(self):
        d=record(self.w);d["approval"]="approved"
        with self.assertRaises(ValueError):self.save(d)
    def test_review_invalid_timestamp(self):
        d=record(self.w);d["at"]="2026-10-17T10:00:00-00:00"
        with self.assertRaises(ValueError):self.save(d)
    def test_bad_baseline_id(self):
        with self.assertRaises(ValueError):cr.assessment(self.store,{"revision":2,"baselineId":[]},server.Conflict,server.findings_for)
    def test_tampered_baseline(self):
        with self.store.connect() as c:
            body=json.loads(c.execute("SELECT body FROM review_baselines").fetchone()[0]);body["workspace"]["sources"][0]["label"]="tampered";c.execute("UPDATE review_baselines SET body=?",(json.dumps(body),))
        with self.assertRaises(ValueError):cr.assessment(self.store,{"revision":2,"baselineId":"base"},server.Conflict,server.findings_for)
    def test_read_compare_does_not_write(self):
        h=server.contracts.hashed(self.path);before=self.store.read();cr.assessment(self.store,{"revision":2,"baselineId":"base"},server.Conflict,server.findings_for);cr.reviews(self.store)
        self.assertEqual(h,server.contracts.hashed(self.path));self.assertEqual(before,self.store.read())
    def test_additive_migration_preserves_rows(self):
        with self.store.connect() as c:
            c.execute("INSERT INTO preview_scenarios VALUES (?,?,?,?)",("preserved",1,"{}","now"))
            c.execute("DROP TABLE change_reviews");c.execute("DROP TABLE review_baselines")
        server.Store(self.path)
        with self.store.connect() as c:self.assertEqual(c.execute("SELECT id,revision,body FROM preview_scenarios").fetchone(),("preserved",1,"{}"))
        self.assertEqual(self.store.read()["workspace"],self.w);self.assertEqual(self.store.read()["revision"],2)
class API(unittest.TestCase):
    def setUp(self):
        Persistence.setUp(self);self.http=server.make_server(self.store,0);self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):self.http.shutdown();self.http.server_close();self.thread.join();Persistence.tearDown(self)
    def request(self,path,body=None,origin=None,editor=True):
        headers={"Content-Type":"application/json"}
        if editor:headers["X-Tyr-Editor"]="1"
        if origin:headers["Origin"]=origin
        with urlopen(Request("http://127.0.0.1:"+str(self.http.server_port)+path,data=json.dumps(body).encode() if body is not None else None,headers=headers,method="POST" if body is not None else "GET")) as r:return json.load(r)
    def test_HTTP_diff(self):self.assertEqual(self.request("/api/review-diff",{"revision":2,"baselineId":"base"})["changes"],[])
    def test_HTTP_review(self):self.request("/api/reviews",{"revision":2,"record":record(self.w)});self.assertEqual(self.request("/api/reviews")["records"][0]["currentStatus"],"reviewed")
    def test_HTTP_baselines(self):self.assertEqual(len(self.request("/api/review-baselines")["baselines"]),1)
    def test_HTTP_stale(self):
        with self.assertRaises(HTTPError) as e:self.request("/api/review-diff",{"revision":1,"baselineId":"base"})
        self.assertEqual(e.exception.code,409)
    def test_HTTP_origin(self):
        with self.assertRaises(HTTPError) as e:self.request("/api/reviews",{"revision":2,"record":record(self.w)},origin="https://evil.invalid")
        self.assertEqual(e.exception.code,403)
    def test_HTTP_header(self):
        with self.assertRaises(HTTPError) as e:self.request("/api/review-baselines",{"revision":2,"id":"x","label":"x"},editor=False)
        self.assertEqual(e.exception.code,403)
    def test_HTTP_no_execution(self):
        for path in ("/api/sql","/api/write","/api/execute","/api/plc/read","/api/approve"):
            with self.assertRaises(HTTPError) as e:self.request(path,{})
            self.assertEqual(e.exception.code,404)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--report",type=Path);a=p.parse_args();r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if a.report:
        files=[*(R/"contracts").rglob("*.json"),*(R/"backend").glob("*.py"),*(R/"frontend").glob("*"),*(R/"fixtures/p5").glob("*"),Path(__file__)]
        server.contracts.save(a.report,{"total":r.testsRun,"passed":r.testsRun-len(r.failures)-len(r.errors),"oracleCases":17,"failures":[str(x) for x in r.failures],"errors":[str(x) for x in r.errors],"sha256":{str(p.relative_to(R)).replace(chr(92),"/"):server.contracts.hashed(p) for p in files if p.is_file()}})
    sys.exit(not r.wasSuccessful())
