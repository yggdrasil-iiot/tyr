"""Bounded math: independent decimal oracles, static gates and SQLite/API compatibility."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"backend"),str(ROOT/"scripts")]
import server,preview,p3a_contracts as p3
def workspace():return server.contracts.load(ROOT/"fixtures/p3cb/workspace.json")
def run(w=None,sample=None,node="difference"):
    w=copy.deepcopy(w or workspace())
    w["mappings"][0]["mappings"][0]["valueRef"]["nodeId"]=node
    return preview.run(w,"pressure-direct-mapping","direct-difference",{"pressure-up":sample or {"bytesHex":"0900"}},2)
def codes(r):return {i["code"] for i in r["issues"]}
class Math(unittest.TestCase):
    def test_fixture(self):
        w=workspace();server.check_state(w);self.assertEqual(server.findings_for(w),[])
    def test_oracles(self):
        for c in server.contracts.load(ROOT/"fixtures/p3cb/cases.json")["cases"]:
            with self.subTest(c["id"]):
                w=workspace();before=copy.deepcopy(w)
                result=run(w,c["sample"],"difference" if c["op"]=="sqrt" else "limited")
                step=next(t for t in result["trace"] if t["stage"]=="graph:"+c["op"])
                self.assertEqual(step["value"],c["expectedGraphValue"])
                self.assertTrue(set(c["codes"])<=codes(result))
                self.assertEqual(w,before);self.assertFalse(result["persisted"])
                self.assertIsNotNone(result["result"])
                self.assertTrue(all(isinstance(i["detail"],str) for i in result["losses"]))
    def test_negative_domain_and_low_loss(self):
        w=workspace();n=w["graphs"][0]["nodes"]
        n.insert(0,dict(nodeId="negative",op="linear",inputs=copy.deepcopy(n[0]["inputs"]),factor="-1",offset="0",valueType="Decimal",unit={"status":"known","code":"1"},evidenceRefs=copy.deepcopy(n[0]["evidenceRefs"])))
        for node in n[1:]:node["inputs"]={"value":{"kind":"node","nodeId":"negative"}}
        self.assertIn("value.sqrt-domain",codes(run(w)))
        r=run(w,node="limited");self.assertIn("loss.clamp",codes(r));self.assertEqual(r["result"]["value"],"0")
    def test_final_exact_cast_still_rejects_approximation(self):
        w=workspace();w["mappings"][0]["mappings"][0]["transform"][0]["rounding"]="exact"
        r=run(w,{"bytesHex":"0200"});self.assertIn("value.inexact",codes(r));self.assertIsNone(r["result"])
    def test_known_pressure_clamp_and_unit_conversion(self):
        w=workspace();g=w["graphs"][0];g["nodes"]=g["nodes"][1:]
        n=g["nodes"][0];n["unit"]={"status":"known","code":"kPa"}
        w["sources"][0]["definition"]["unit"]={"status":"known","code":"bar"}
        g["nodes"].insert(0,dict(nodeId="convert",op="unit-convert",inputs=copy.deepcopy(n["inputs"]),valueType="Decimal",unit={"status":"known","code":"kPa"},evidenceRefs=copy.deepcopy(n["evidenceRefs"]),**{"from":"bar","to":"kPa"}))
        n["inputs"]={"value":{"kind":"node","nodeId":"convert"}}
        w["semantics"][0]["members"][0]["unit"]=n["unit"];w["mappings"][0]["mappings"][0]["outputUnit"]=n["unit"]
        w["mappings"][0]["mappings"][0]["valueRef"]["nodeId"]="limited"
        server.check_state(w);r=run(w,node="limited")
        self.assertEqual(r["result"]["value"],"10");self.assertIn("loss.clamp",codes(r))
        stages=[t["stage"] for t in r["trace"]];self.assertLess(stages.index("graph:unit-convert"),stages.index("graph:clamp"))
    def test_four_profiles_converge_to_same_sqrt(self):
        for profile in server.contracts.PROFILES:
            w=workspace();w["connections"][0]["accessProfileRef"]=profile
            for i,row in enumerate(w["sources"]):
                d=row["definition"];d["accessProfileRef"]=profile
                if profile=="ab-logix-symbol-v1":d["access"]={"kind":"symbol","symbolPath":["ValueA","ValueB"][i]}
                elif profile=="s7-1500-opcua-v1":d["access"]={"kind":"opcua-node","namespaceUri":"urn:tyr:fixture:bounded","identifierType":"string","identifier":["ValueA","ValueB"][i]}
                elif profile=="s7-300-db-v1":d["access"]={"kind":"db-offset","dbNumber":10,"byteOffset":i*2,"byteLength":2,"bitOffset":None}
                if profile in ("ab-logix-symbol-v1","s7-1500-opcua-v1"):
                    d["addressRadix"]=None;d["rawRepresentation"]={"mode":"typed","valueType":"UInt16"}
                elif profile=="s7-300-db-v1":d["addressRadix"]=None
            server.check_state(w)
            sample={"typedValue":"9"} if profile in ("ab-logix-symbol-v1","s7-1500-opcua-v1") else {"bytesHex":"0900"}
            result=run(w,sample);self.assertEqual(result["result"]["value"],"3",profile)
    def test_fractional_clamp_and_negative_bounds(self):
        w=workspace();g=w["graphs"][0];n=g["nodes"][1]
        n.update(low="-1.5",high="1.5")
        result=run(w,node="limited")
        self.assertEqual(result["result"]["value"],"1.5");self.assertIn("loss.clamp",codes(result))
    def test_equal_bounds(self):
        w=workspace();w["graphs"][0]["nodes"][1].update(low="7",high="7")
        server.check_state(w);self.assertEqual(run(w,node="limited")["result"]["value"],"7")
    def test_bounds_rejected_static_and_preview(self):
        w=workspace();w["graphs"][0]["nodes"][1].update(low="11",high="10")
        self.assertIn("graph.clamp-range",{e["ruleCode"] for e in server.findings_for(w)})
        with self.assertRaises(server.Invalid):server.check_state(w)
        self.assertIn("graph.clamp-range",codes(run(w,node="limited")))
    def test_sqrt_rejects_dimensional_input(self):
        w=workspace();w["sources"][0]["definition"]["unit"]={"status":"known","code":"kPa"}
        self.assertIn("graph.input-unit",{e["ruleCode"] for e in server.findings_for(w)})
        self.assertIn("graph.input-unit",codes(run(w)))
    def test_type_and_output_units(self):
        for kind in ("bool","unit"):
            w=workspace()
            if kind=="bool":w["sources"][0]["definition"]["access"]["bitOffset"]=0
            else:w["graphs"][0]["nodes"][0]["unit"]={"status":"known","code":"bar"}
            self.assertIn("graph.input-type" if kind=="bool" else "graph.output-unit",{e["ruleCode"] for e in server.findings_for(w)})
    def test_missing_and_bad_quality(self):
        r=preview.run(workspace(),"pressure-direct-mapping","direct-difference",{},2)
        self.assertIsNone(r["result"]);self.assertEqual(r["quality"],"bad")
    def test_temporal_quality_stale_and_skew_before_new_operations(self):
        base=server.contracts.load(ROOT/"fixtures/p3cb/temporal-workspace.json")
        server.check_state(base)
        samples={id:{"value":{"bytesHex":value},"quality":"good","sourceTimestamp":"2026-10-17T09:59:59.500Z","serverTimestamp":"2026-10-17T10:00:00Z","sequence":None} for id,value in [("pressure-up","0900"),("pressure-down","0100")]}
        evaluation={"at":"2026-10-17T10:00:00Z","triggerSequence":None}
        good=preview.run(base,"pressure-direct-mapping","direct-difference",samples,2,evaluation)
        self.assertEqual(good["result"]["value"],"2")
        for change,code in [("bad","quality.bad-input"),("stale","time.stale-input"),("skew","time.skew-exceeded")]:
            changed=copy.deepcopy(samples)
            if change=="bad":changed["pressure-up"]["quality"]="bad"
            else:changed["pressure-down"]["sourceTimestamp"]="2026-10-17T09:59:58Z" if change=="stale" else "2026-10-17T09:59:59.800Z"
            result=preview.run(base,"pressure-direct-mapping","direct-difference",changed,2,evaluation)
            self.assertIn(code,codes(result));self.assertIsNone(result["result"])
            self.assertFalse(any(t["stage"] in ("graph:sqrt","graph:clamp") for t in result["trace"]))
    def test_old_schema_and_policy(self):
        for version in ("2.0.0","2.2.0","2.5.0"):
            g=workspace()["graphs"][0];g["schemaVersion"]=version
            self.assertTrue(p3.schema_errors("value-graph",g))
        for field,value in (("precision",35),("rounding","floor"),("op","eval")):
            g=workspace()["graphs"][0];g["nodes"][0][field]=value
            self.assertTrue(p3.schema_errors("value-graph",g))
    def test_ports_cycles_and_evidence(self):
        for change,rule in (("port","schema"),("cycle","graph.cycle"),("evidence","graph.evidence-incomplete")):
            w=workspace();n=w["graphs"][0]["nodes"][0]
            if change=="port":n["inputs"]["other"]=copy.deepcopy(n["inputs"]["value"])
            elif change=="cycle":n["inputs"]["value"]={"kind":"node","nodeId":n["nodeId"]}
            else:n["evidenceRefs"]=n["evidenceRefs"][1:]
            self.assertIn(rule,{e["ruleCode"] for e in server.findings_for(w)})
    def test_old_contract_and_fixture_bytes(self):
        baseline=server.contracts.load(ROOT/"docs/verification/a14-results.json")["inputSha256"]
        for path,sha in baseline.items():
            if (path.startswith("contracts/") and path.endswith(".schema.json")) or path.startswith("fixtures/"):self.assertEqual(server.contracts.hashed(ROOT/path),sha,path)
class Storage(unittest.TestCase):
    def test_legacy_to_new_json_roundtrip_and_rejection_atomic(self):
        with tempfile.TemporaryDirectory() as t:
            db=Path(t)/"editor.sqlite3";s=server.Store(db);s.migrate(0,{})
            old=server.contracts.load(ROOT/"fixtures/p3c/workspace.json");s.save(1,old)
            self.assertEqual(server.Store(db).read()["workspace"],old)
            w=workspace();s.save(2,w);self.assertEqual(server.Store(db).read()["workspace"],w)
            before=s.read();sha=server.contracts.hashed(db);run(w)
            self.assertEqual(s.read(),before);self.assertEqual(server.contracts.hashed(db),sha)
            with self.assertRaises(server.Conflict):s.save(2,w)
            bad=copy.deepcopy(w);bad["graphs"][0]["nodes"][1]["low"]="1000"
            with self.assertRaises(server.Invalid):s.save(3,bad)
            self.assertEqual(s.read(),before)
if __name__=="__main__":unittest.main()
