"""P2 persistence/API acceptance tests using temporary SQLite only."""
import copy
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"backend"))
import server

def sample():
    w=copy.deepcopy(server.EMPTY)
    w["semantics"]=[server.contracts.load(ROOT/"fixtures/packages/motor/semantics/motor.json")]
    for letter in "abcd":
        d=server.contracts.load(ROOT/f"fixtures/packages/motor/sources/source-{letter}.json")
        w["equipment"].append({"id":d["equipmentInstanceId"],"label":"Motor "+letter})
        w["connections"].append({"id":d["connectionProfileRef"],"label":"Logical "+letter,
                                 "equipmentInstanceId":d["equipmentInstanceId"],"accessProfileRef":d["accessProfileRef"]})
        d["evidenceRefs"]=[{"artifactId":"manual-"+d["id"],"locator":{"kind":"text-line","line":1}}]
        w["sources"].append({"definition":d,"note":"Synthetic manual declaration "+letter,"origin":"synthetic","capturedAt":"2026-10-17T00:00:00Z"})
        m=server.contracts.load(ROOT/f"fixtures/packages/motor/mappings/map-{letter}.json")
        m["mappings"][0]["evidenceRefs"]=d["evidenceRefs"]
        w["mappings"].append(m)
    return w

class Persistence(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="tyr-p2-test-")
        self.db=Path(self.tmp.name)/"workspace.sqlite3";self.store=server.Store(self.db)
    def tearDown(self):self.tmp.cleanup()
    def test_four_profiles_same_meaning_restart(self):
        state=sample();saved=self.store.save(0,state)
        self.assertEqual(saved["findings"],[])
        reopened=server.Store(self.db).read()
        self.assertEqual(reopened["workspace"],state)
        self.assertEqual(reopened["revision"],1)
        self.assertEqual({x["definition"]["access"]["kind"] for x in state["sources"]},set(server.contracts.PROFILES.values()))
        self.assertEqual(len({x["semanticDefinitionRef"]["id"] for x in state["mappings"]}),1)
    def test_revision_conflict_keeps_saved_state(self):
        self.store.save(0,sample())
        with self.assertRaises(server.Conflict):self.store.save(0,copy.deepcopy(server.EMPTY))
        self.assertEqual(len(self.store.read()["workspace"]["sources"]),4)
    def test_draft_null_saved_with_submission_block(self):
        state=sample();d=state["sources"][2]["definition"];d["status"]="draft";d["access"]["symbolPath"]=None
        saved=self.store.save(0,state)
        self.assertIn("source.draft",{f["ruleCode"] for f in saved["findings"]})
        self.assertIn("mapping.source-not-ready",{f["ruleCode"] for f in saved["findings"]})
        self.assertIsNone(server.Store(self.db).read()["workspace"]["sources"][2]["definition"]["access"]["symbolPath"])
    def test_missing_context_rejected_atomically(self):
        state=sample();state["connections"][0]["equipmentInstanceId"]="unknown"
        with self.assertRaises(server.Invalid):self.store.save(0,state)
        self.assertEqual(self.store.read()["revision"],0)
    def test_bad_schema_rejected(self):
        state=sample();state["sources"][0]["definition"]["access"]["bitOffset"]=16
        with self.assertRaises(server.Invalid):self.store.save(0,state)
    def test_multi_member_draft_saved_without_loss(self):
        state=sample();member=copy.deepcopy(state["semantics"][0]["members"][0]);member["memberId"]="second"
        state["semantics"][0]["members"].append(member)
        saved=self.store.save(0,state)
        self.assertEqual(len(saved["workspace"]["semantics"][0]["members"]),2)
        self.assertIn("mapping.incomplete-object",{f["ruleCode"] for f in saved["findings"]})
    def test_editor_rejects_unsupported_transform(self):
        state=sample();state["mappings"][0]["mappings"][0]["transform"]=[{"op":"script","expression":"arbitrary()"}]
        with self.assertRaises(server.Invalid):self.store.save(0,state)
    def test_cross_equipment_rejected(self):
        state=sample();state["mappings"][0]["equipmentInstanceId"]="conveyor-b"
        with self.assertRaises(server.Invalid):self.store.save(0,state)
    def test_semantic_change_marks_mapping_unit(self):
        state=sample();self.store.save(0,state)
        state["semantics"][0]["members"][0]["unit"]["code"]="Cel"
        saved=self.store.save(1,state)
        self.assertIn("mapping.unit",{f["ruleCode"] for f in saved["findings"]})
    def test_manual_evidence_packaged(self):
        state=sample()
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);server.build_package(state,folder)
            self.assertEqual(server.contracts.validate_package(folder),[])
            self.assertEqual((folder/"data/manual-0.txt").read_text(encoding="utf-8"),state["sources"][0]["note"]+"\n")

class Realistic(unittest.TestCase):
    def state(self):return server.contracts.load(ROOT/"fixtures/realistic/workspace.json")
    def test_full_object_package(self):
        state=self.state();server.check_state(state)
        self.assertEqual(server.findings_for(state),[])
        self.assertEqual(len(state["sources"]),32)
        self.assertEqual(len(state["semantics"][0]["members"]),8)
        self.assertEqual([len(d["mappings"]) for d in state["mappings"]],[8,8,8,8])
    def test_distributed_single_word_addresses(self):
        rows={r["definition"]["id"]:r["definition"] for r in self.state()["sources"]}
        for id,address in (("melsec-actual-speed",1000),("melsec-target-speed",2000),("melsec-state",3000)):
            self.assertEqual(rows[id]["access"]["addressIndex"],address)
            self.assertEqual(rows[id]["access"]["wordCount"],1)
        mapping=self.state()["mappings"][3]
        self.assertEqual([m["targetMemberId"] for m in mapping["mappings"][:3]],["actual-speed","target-speed","state"])
    def test_alias_and_name_collision(self):
        rows={r["definition"]["id"]:r for r in self.state()["sources"]}
        self.assertEqual(rows["db-actual-speed"]["label"],"PV")
        self.assertEqual(rows["ab-torque"]["label"],"PV")
        self.assertEqual(rows["ab-state"]["label"],rows["ua-alarm-active"]["label"])
        self.assertEqual(len({rows[p+"-actual-speed"]["label"] for p in ("ab","ua","db","melsec")}),4)
    def test_wrong_conversion_source_blocked(self):
        state=self.state();state["mappings"][1]["mappings"][0]["transform"][0]["from"]="K"
        rules={f["ruleCode"] for f in server.findings_for(state)}
        self.assertIn("transform.unit-source",rules)
        self.assertIn("transform.unit-conversion",rules)
    def test_missing_unit_conversion_blocked(self):
        state=self.state()
        state["mappings"][1]["mappings"][0]["transform"]=[{"op":"cast","to":"Double","rounding":"exact","overflow":"error"}]
        self.assertIn("mapping.unit-conversion-required",{f["ruleCode"] for f in server.findings_for(state)})
    def test_unit_conversion_target_blocked(self):
        state=self.state();state["mappings"][1]["mappings"][0]["transform"][0]={"op":"unit-convert","from":"mN.m","to":"N.m"}
        rules={f["ruleCode"] for f in server.findings_for(state)}
        self.assertIn("transform.unit-target",rules)
    def test_legacy_contract_not_silently_extended(self):
        d=copy.deepcopy(self.state()["sources"][8]["definition"]);d["schemaVersion"]="1.0.0"
        self.assertTrue(server.contracts.validate_schema("source-definition",d))
    def test_partial_object_saved_with_coverage_findings(self):
        state=self.state();state["mappings"][3]["mappings"]=state["mappings"][3]["mappings"][:3]
        findings=server.findings_for(state)
        self.assertEqual(sum(f["ruleCode"]=="mapping.incomplete-object" for f in findings),5)
    def test_property_edit_preserves_siblings_restart(self):
        state=self.state()
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/"object.sqlite3";store=server.Store(db);store.save(0,state)
            state["semantics"][0]["members"][0]["name"]="renamedActual"
            store.save(1,state);restored=server.Store(db).read()["workspace"]
            self.assertEqual(restored["semantics"][0]["members"][1:],self.state()["semantics"][0]["members"][1:])
            self.assertEqual(len(restored["mappings"][3]["mappings"]),8)
    def test_definition_driven_oracles(self):
        from governance_checks import bindings,evaluate
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);server.build_package(self.state(),folder)
            from governance_checks import documents
            rows={r["mappingId"]:r for r in bindings(documents(folder))}
            for case in server.contracts.load(ROOT/"fixtures/realistic/oracles.json")["cases"]:
                value,issues=evaluate(rows[case["mappingId"]],case)
                self.assertEqual(value,case["expected"],case["mappingId"]);self.assertEqual(issues,[],case["mappingId"])

class API(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="tyr-p2-api-")
        self.http=server.make_server(server.Store(Path(self.tmp.name)/"api.sqlite3"),0)
        self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()
        self.url=f"http://127.0.0.1:{self.http.server_port}"
    def tearDown(self):
        self.http.shutdown();self.http.server_close();self.thread.join();self.tmp.cleanup()
    def call(self,method,path="/api/workspace",body=None,headers=None):
        h={"Content-Type":"application/json","X-Tyr-Editor":"1"};h.update(headers or {})
        data=json.dumps(body).encode() if body is not None else None
        try:
            with urlopen(Request(self.url+path,data=data,method=method,headers=h),timeout=5) as response:return response.status,response.read()
        except HTTPError as e:return e.code,e.read()
    def test_api_save_get_conflict(self):
        code,body=self.call("PUT",body={"revision":0,"workspace":sample()});self.assertEqual(code,200,body)
        code,body=self.call("GET");self.assertEqual(json.loads(body)["revision"],1)
        code,_=self.call("PUT",body={"revision":0,"workspace":sample()});self.assertEqual(code,409)
    def test_reject_foreign_origin(self):
        code,_=self.call("PUT",body={"revision":0,"workspace":sample()},headers={"Origin":"https://example.invalid"});self.assertEqual(code,403)
    def test_reject_nonlocal_host(self):
        code,_=self.call("GET",headers={"Host":"example.invalid"});self.assertEqual(code,403)
    def test_static_page_and_no_device_routes(self):
        code,body=self.call("GET","/");self.assertEqual(code,200);self.assertIn("데이터 정의".encode(),body)
        code,_=self.call("GET","/api/connect");self.assertEqual(code,404)

if __name__=="__main__":
    import argparse, hashlib
    from datetime import datetime, timezone
    parser=argparse.ArgumentParser();parser.add_argument("--report",type=Path);args=parser.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if args.report:
        files=["backend/server.py","frontend/index.html","frontend/app.js","frontend/style.css","scripts/test_p2.py","scripts/seed_realistic.py","fixtures/realistic/workspace.json","fixtures/realistic/oracles.json","scripts/validate_contracts.py","scripts/governance_checks.py"]
        report={"scope":"P2 expanded object/property authoring, 32-signal maps and SQLite persistence; no device communication","generatedAt":datetime.now(timezone.utc).isoformat(),
                "total":result.testsRun,"passed":result.testsRun-len(result.failures)-len(result.errors),"failures":[str(t) for t,_ in result.failures],"errors":[str(t) for t,_ in result.errors],
                "contractSchemas":{str(p.relative_to(ROOT)).replace(chr(92),"/"):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/"contracts").glob("*/*.schema.json"))},"sourceHashes":{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files}}
        args.report.parent.mkdir(parents=True,exist_ok=True);server.contracts.save(args.report,report)
    raise SystemExit(not result.wasSuccessful())
