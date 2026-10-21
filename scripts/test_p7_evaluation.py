"""Independent evaluation scoring, conservation, read-only API and compatibility."""
import copy,json,sys,tempfile,threading,unittest,subprocess
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/"backend"),str(R/"scripts")]
import server,pov_evaluation as p
F=R/"fixtures/p7-evaluation"
def load(path):return server.contracts.load(path)
class Evaluator(unittest.TestCase):
    def setUp(self):self.w=load(R/"fixtures/p3eb/workspace.json");self.pack=load(F/"oracle.json")
    def run_report(self):return p.evaluate(self.w,self.pack,17)
    def test_four_profiles_nested_identity_and_splits(self):
        v=self.run_report();self.assertEqual(len(v["cases"]),40)
        for split,n in [("calibration",10),("evaluation",20),("heldout",10)]:self.assertEqual(v["metrics"][split]["counts"]["verified-fixture"],n)
        self.assertEqual(v["metrics"]["evaluation"]["time"]["savingPercent"],"20.00");self.assertEqual(v["metrics"]["heldout"]["time"]["state"],"not-measured")
        actual=next(g for g in v["semanticGroups"] if g["semanticId"]=="urn:tyr:concept:pressure.actual");self.assertEqual(actual["count"],12);self.assertFalse(actual["canonicalConflict"])
    def test_blank_template_never_derives_truth(self):
        t=p.template(self.w,self.pack["mappingSetIds"]);self.assertFalse(t["expectedValuesGenerated"]);self.assertTrue(all(c["expected"] is None and not c["samples"] for c in t["pack"]["cases"]));v=p.evaluate(self.w,t["pack"]);self.assertEqual(v["metrics"]["evaluation"]["counts"]["unreviewed"],40);self.assertEqual(v["metrics"]["evaluation"]["verifiedPercent"],"0.00")
    def test_partial_without_samples(self):
        self.pack["cases"][10]["samples"]=[];self.assertEqual(self.run_report()["cases"][10]["status"],"partial")
    def test_partial_without_definition_pin(self):
        self.pack["cases"][10]["expected"]["definitionSha256"]=None;self.assertEqual(self.run_report()["cases"][10]["status"],"partial")
    def test_missing_and_conservation(self):
        self.w["mappings"][1]["mappings"].pop(0);v=self.run_report();m=v["metrics"]["evaluation"];self.assertEqual(m["counts"]["missing"],1);self.assertEqual(sum(m["counts"].values()),20);self.assertEqual(m["notRunSamples"],1)
    def test_ambiguous_identity_never_selects_first(self):
        b=copy.deepcopy(self.w["mappings"][1]["mappings"][0]);b["mappingId"]="duplicate";self.w["mappings"][1]["mappings"].append(b);self.assertEqual(self.run_report()["cases"][10]["status"],"ambiguous")
    def test_unexpected_mapping_not_counted_as_correct(self):
        self.pack["cases"].pop();v=self.run_report();self.assertEqual(len(v["unexpectedMappings"]),1);self.assertEqual(v["metrics"]["heldout"]["oracleCases"],9)
    def test_incomplete_oracle_coverage_not_silently_full(self):
        self.pack["cases"]=self.pack["cases"][:1];v=self.run_report();self.assertEqual(v["coverage"]["reviewedIdentityCoveragePercent"],"2.50");self.assertEqual(len(v["unexpectedMappings"]),39)
    def test_pending_oracle_coverage_is_zero(self):
        pack=p.template(self.w,self.pack["mappingSetIds"])["pack"];self.assertEqual(p.evaluate(self.w,pack)["coverage"]["reviewedIdentityCoveragePercent"],"0.00")
    def test_empty_scope_template_refused(self):
        self.w["mappings"][0]["mappings"]=[];self.assertRaises(ValueError,p.template,self.w,[self.w["mappings"][0]["id"]])
    def test_semantic_mismatch_is_separate_from_definition(self):
        self.w["semantics"][0]["members"][0]["members"][0]["members"][0]["semanticId"]="urn:different:pressure";v=self.run_report();self.assertEqual(v["cases"][0]["status"],"meaning-mismatch");self.assertEqual(v["cases"][0]["definitionStatus"],"match")
    def test_address_change_detected(self):
        source=next(s for s in self.w["sources"] if s["definition"]["id"]=="structure-ab-actual");source["definition"]["access"]["symbolPath"]="Different.Address";v=self.run_report();self.assertEqual(v["cases"][0]["status"],"definition-difference");self.assertTrue(v["baselineWorkspaceChanged"])
    def test_graph_dependency_change_detected(self):
        self.w["graphs"][0]["nodes"][0]["indices"]=[0,1];self.assertEqual(self.run_report()["cases"][4]["status"],"definition-difference")
    def test_presentation_names_ignored(self):
        self.w["sources"][0]["label"]="Unrelated label";self.w["targets"][0]["label"]="Renamed";v=self.run_report();self.assertTrue(all(c["status"]=="verified-fixture" for c in v["cases"]))
    def test_wrong_value_detected(self):
        self.pack["cases"][10]["samples"][0]["expected"]["result"]["value"]="999";v=self.run_report();self.assertEqual(v["cases"][10]["status"],"sample-mismatch");self.assertEqual(v["metrics"]["evaluation"]["sampleMismatches"],1)
    def test_numeric_spelling_equal_but_boolean_not_number(self):
        self.pack["cases"][10]["samples"][0]["expected"]["result"]["value"]="150.000";self.assertEqual(self.run_report()["cases"][10]["status"],"verified-fixture")
        self.pack["cases"][13]["samples"][0]["expected"]["result"]["value"]="false";self.assertEqual(self.run_report()["cases"][13]["status"],"sample-mismatch")
    def test_precision_loss_present_and_missing_detection(self):
        w=load(F/"loss-workspace.json");pack=load(F/"loss-oracle.json");v=p.evaluate(w,pack);self.assertEqual(v["cases"][0]["status"],"verified-fixture")
        pack["cases"][0]["samples"][0]["expected"]["losses"]=[];v=p.evaluate(w,pack);self.assertEqual(v["cases"][0]["status"],"sample-mismatch");self.assertEqual(v["metrics"]["evaluation"]["lossDiagnosticMismatches"],1)
    def test_unknown_sample_exception_is_failure(self):
        self.pack["cases"][10]["samples"][0]["samples"]={"no-source":{}};v=self.run_report();self.assertEqual(v["cases"][10]["status"],"sample-mismatch")
    def test_all_phases_and_order_are_counted(self):
        t=self.run_report()["metrics"]["evaluation"]["time"];self.assertEqual(t["manualSeconds"],1000);self.assertEqual(t["toolSeconds"],800);self.assertTrue(t["counterbalanced"]);self.assertEqual(set(t["phases"]),set(p.PHASES))
    def test_incomplete_pair_not_included(self):
        self.pack["timePairs"][0]["completed"]=False;t=self.run_report()["metrics"]["evaluation"]["time"];self.assertEqual(t["completePairs"],1);self.assertEqual(t["incompletePairs"],1);self.assertEqual(t["manualSeconds"],400);self.assertFalse(t["counterbalanced"])
    def test_zero_time_denominator_not_perfect(self):
        self.pack["timePairs"]=[];t=self.run_report()["metrics"]["evaluation"]["time"];self.assertIsNone(t["savingPercent"]);self.assertEqual(t["state"],"not-measured")
    def test_field_label_never_certifies_pov(self):
        self.pack["origin"]="field-declared";v=self.run_report();self.assertEqual(v["fieldPoV"],"not-certified");self.assertEqual(v["evidenceClass"],"field-declared-unverified")
    def test_duplicate_oracles_refused(self):
        self.pack["cases"].append(copy.deepcopy(self.pack["cases"][0]));self.assertRaises(ValueError,self.run_report)
    def test_duplicate_identity_refused_across_splits(self):
        c=copy.deepcopy(self.pack["cases"][0]);c.update(caseId="different-id",split="heldout");self.pack["cases"].append(c);self.assertRaises(ValueError,self.run_report)
    def test_duplicate_time_pairs_refused(self):
        self.pack["timePairs"].append(copy.deepcopy(self.pack["timePairs"][0]));self.assertRaises(ValueError,self.run_report)
    def test_independence_declaration_required(self):
        self.pack["review"]["independenceAttested"]=False;self.assertRaises(ValueError,self.run_report)
    def test_conflicting_canonical_truth_refused(self):
        self.pack["cases"][10]["expected"]["meaning"]["role"]="setpoint";self.assertRaises(ValueError,self.run_report)
    def test_bounds_and_unknown_fields_refused(self):
        for edit in [lambda q:q.update(unknown=True),lambda q:q["timePairs"][0]["manual"].update(map=-1),lambda q:q["timePairs"][0]["manual"].update(map=True),lambda q:q.update(cases=[]),lambda q:q["timePairs"][0]["manual"].pop("inquire")]:
            q=copy.deepcopy(self.pack);edit(q);self.assertRaises(ValueError,p.evaluate,self.w,q)
    def test_readonly_and_report_digest(self):
        before=copy.deepcopy(self.w);v=self.run_report();self.assertEqual(before,self.w);pin=v.pop("reportSha256");self.assertEqual(p.sq.digest(v),pin)
    def test_legacy_refused_without_migration(self):
        self.w.pop("workspaceVersion");self.assertRaises(ValueError,self.run_report)
    def test_old_contract_fixture_and_java_schema_preserved(self):
        baseline=load(R/"docs/verification/p6r-validation.json")
        for name,h in baseline["sha256"].items():
            if name.startswith(("contracts/","fixtures/")):self.assertEqual(server.contracts.hashed(R/name),h,name)
        for name,h in baseline['sha256'].items():
            if name.startswith('contracts/') and name.endswith('.schema.json'):
                self.assertEqual(server.contracts.hashed(R.parent/'bifrost/core/src/main/resources/mapping-contracts'/Path(name).relative_to('contracts')),h,name)
class API(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=server.Store(Path(self.tmp.name)/"db.sqlite3");self.store.migrate(0,{});self.store.save(1,load(R/"fixtures/p3eb/workspace.json"));self.before=self.store.read();self.http=server.make_server(self.store,0);self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start();self.origin='http://127.0.0.1:'+str(self.http.server_port)
    def tearDown(self):self.http.shutdown();self.http.server_close();self.thread.join();self.tmp.cleanup()
    def request(self,path,body,origin=None):
        headers={'Content-Type':'application/json','X-Tyr-Editor':'1'}
        if origin:headers['Origin']=origin
        with urlopen(Request(self.origin+path,data=json.dumps(body).encode(),headers=headers)) as r:return json.load(r)
    def test_template_and_evaluation_no_sqlite_changes(self):
        pack=load(F/'oracle.json');t=self.request('/api/pov-template',{'revision':2,'mappingSetIds':pack['mappingSetIds']});self.assertFalse(t['expectedValuesGenerated']);self.assertTrue(all(c['expected'] is None for c in t['pack']['cases']))
        v=self.request('/api/pov-evaluate',{'revision':2,'pack':pack});self.assertFalse(v['persisted']);self.assertEqual(self.before,self.store.read());self.assertEqual(server.Store(self.store.path).read(),self.before)
    def test_revision_conflict(self):
        with self.assertRaises(HTTPError) as e:self.request('/api/pov-evaluate',{'revision':1,'pack':load(F/'oracle.json')})
        self.assertEqual(e.exception.code,409)
    def test_foreign_origin_refused(self):
        with self.assertRaises(HTTPError) as e:self.request('/api/pov-template',{'revision':2,'mappingSetIds':['structure-ab-mapping']},'https://invalid.example')
        self.assertEqual(e.exception.code,403)
    def test_invalid_oracle_is_structured_refusal(self):
        with self.assertRaises(HTTPError) as e:self.request('/api/pov-evaluate',{'revision':2,'pack':{}})
        self.assertEqual(e.exception.code,422);self.assertEqual(self.store.read(),self.before)
if __name__=='__main__':unittest.main(verbosity=2)
