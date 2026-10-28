"""P4-F §5: endpoint closure over Mimir snapshots (1.0.0 and 1.1.0), checked against oracles written independently of the code."""
import copy, json, random, sys, unittest
from pathlib import Path
R = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(R/"backend"), str(R/"scripts")]
import interpretation_closure as cl, interpretation_intake as ii

F = R/"fixtures/solution-intake/closure-1.0.0"
F11 = R/"fixtures/solution-intake/closure-1.1.0"
EDITOR = R/"fixtures/solution-intake/editor-2.0.0/valid"


def load(sub, name): return ii.load((F11 if sub == "closure-c" else F)/sub/name)
def depth(sub): return load(sub, "interpretation-profile.json")["body"]["limits"]["maxReferenceDepth"]


class Fixtures(unittest.TestCase):
    def test_snapshots_are_received(self):
        for sub in ("closure-a", "closure-b"):
            with self.subTest(sub):
                ii.check_pinned(load(sub, "interpretation-snapshot.json"), load(sub, "source-bundle.json"), load(sub, "interpretation-profile.json"))

    def test_oracle_covers_every_case(self):
        cases = json.loads((F/"cases.json").read_text(encoding="utf-8"))["cases"]
        oracle = json.loads((F/"oracle.json").read_text(encoding="utf-8"))["cases"]
        self.assertEqual([(c["snapshot"], c["endpoint"]) for c in cases], [(c["snapshot"], c["endpoint"]) for c in oracle])
        self.assertEqual(len(cases), 12)


class Closure(unittest.TestCase):
    def test_matches_the_oracle(self):
        oracle = json.loads((F/"oracle.json").read_text(encoding="utf-8"))["cases"]
        for c in oracle:
            with self.subTest(f"{c['snapshot']}:{c['endpoint']}"):
                self.assertEqual(cl.closure(load(c["snapshot"], "interpretation-snapshot.json"), c["endpoint"], depth(c["snapshot"])), c["expected"])

    def test_order_of_snapshot_lists_does_not_matter(self):
        rng = random.Random(7)
        for sub in ("closure-a", "closure-b"):
            s = load(sub, "interpretation-snapshot.json")
            for endpoint in [c["endpoint"] for c in json.loads((F/"cases.json").read_text(encoding="utf-8"))["cases"] if c["snapshot"] == sub]:
                want = cl.closure(s, endpoint, depth(sub))
                for _ in range(5):
                    t = copy.deepcopy(s)
                    for k in ("nativeNodes", "referenceEdges", "claims", "unresolved"): rng.shuffle(t["body"][k])
                    with self.subTest(f"{sub}:{endpoint}"): self.assertEqual(cl.closure(t, endpoint, depth(sub)), want)

    def test_no_edges_is_not_completeness(self):
        r = cl.closure(load("closure-a", "interpretation-snapshot.json"), "n.lonely", depth("closure-a"))
        self.assertEqual((r["edgeIds"], r["completeness"]), ([], "incomplete"))
        self.assertEqual(r["reasons"], [{"code": "unexplained-leaf", "ref": "n.lonely"}])

    def test_ambiguous_candidates_are_not_chosen(self):
        r = cl.closure(load("closure-a", "interpretation-snapshot.json"), "n.avg", depth("closure-a"))
        self.assertEqual(r["nodeIds"], ["n.avg"])

    def test_capture_scope_is_reported_not_folded_in(self):
        r = cl.closure(load("closure-b", "interpretation-snapshot.json"), "n.b-ok", depth("closure-b"))
        self.assertEqual((r["completeness"], r["captureScope"]), ("complete", "partial"))

    def test_unknown_endpoint(self):
        with self.assertRaises(KeyError): cl.closure(load("closure-a", "interpretation-snapshot.json"), "n.nowhere", 3)


class Closure11(unittest.TestCase):
    """Contract 1.1.0: access decides what is followed, and declared state is reported as it is."""
    def snapshot(self): return load("closure-c", "interpretation-snapshot.json")
    def run_on(self, endpoint): return cl.closure(self.snapshot(), endpoint, depth("closure-c"))

    def test_snapshot_is_received(self):
        ii.check_pinned(self.snapshot(), load("closure-c", "source-bundle.json"), load("closure-c", "interpretation-profile.json"))

    def test_matches_the_oracle(self):
        cases = json.loads((F11/"cases.json").read_text(encoding="utf-8"))["cases"]
        oracle = json.loads((F11/"oracle.json").read_text(encoding="utf-8"))["cases"]
        self.assertEqual([(c["snapshot"], c["endpoint"]) for c in cases], [(c["snapshot"], c["endpoint"]) for c in oracle])
        self.assertEqual(len(oracle), 9)
        for c in oracle:
            with self.subTest(c["endpoint"]): self.assertEqual(self.run_on(c["endpoint"]), c["expected"])

    def test_order_of_snapshot_lists_does_not_matter(self):
        rng, s = random.Random(11), self.snapshot()
        for c in json.loads((F11/"cases.json").read_text(encoding="utf-8"))["cases"]:
            want = cl.closure(s, c["endpoint"], depth("closure-c"))
            for _ in range(5):
                t = copy.deepcopy(s)
                for k in ("nativeNodes", "referenceEdges", "claims", "unresolved"): rng.shuffle(t["body"][k])
                with self.subTest(c["endpoint"]): self.assertEqual(cl.closure(t, c["endpoint"], depth("closure-c")), want)

    def test_a_write_is_recorded_not_followed(self):
        r = self.run_on("n.c-script")
        self.assertNotIn("n.c-out", r["nodeIds"]); self.assertNotIn("e.script-out", r["edgeIds"])
        self.assertEqual([w["edgeId"] for w in r["writeTargets"]], ["e.script-gone", "e.script-out"])
        self.assertEqual(r["completeness"], "complete")

    def test_an_unknown_access_is_a_reason_and_not_followed(self):
        r = self.run_on("n.c-guess")
        self.assertEqual((r["nodeIds"], r["reasons"]), (["n.c-guess"], [{"code": "access-unknown", "ref": "e.guess-plc"}]))

    def test_state_is_read_as_declared(self):
        self.assertEqual(self.run_on("n.c-total")["statefulNodeIds"], ["n.c-total"])
        self.assertEqual(self.run_on("n.c-blind")["stateUnknownNodeIds"], ["n.c-blind"])

    def test_1_0_0_results_keep_their_shape(self):
        r = cl.closure(load("closure-a", "interpretation-snapshot.json"), "n.final", depth("closure-a"))
        self.assertNotIn("writeTargets", r); self.assertNotIn("eventEdgeIds", r)


class PlanBlock(unittest.TestCase):
    """A write is control and state is preserved, not converted: a candidate plan over either is refused."""
    def documents(self, endpoint, status="candidate"):
        s, p = load("closure-c", "interpretation-snapshot.json"), load("closure-c", "interpretation-profile.json")
        r = cl.closure(s, endpoint, depth("closure-c"))
        a = ii.load(EDITOR/"assessment-line1-temp.json"); b = a["body"]
        a["id"] = "synthetic/closure-c/assessment-" + endpoint
        b["snapshotRef"], b["endpoint"], b["decisionRefs"] = ii._pin(s), {"nodeId": endpoint}, []
        b["closure"].update(nodeIds=r["nodeIds"], edgeIds=r["edgeIds"], completeness=r["completeness"])
        a["digest"] = ii.digest(a)
        plan = ii.load(EDITOR/"plan-line1-temp.json"); b = plan["body"]
        plan["id"] = "synthetic/closure-c/plan-" + endpoint
        b.update(assessmentRef=ii._pin(a), snapshotRef=ii._pin(s), profileRef=s["body"]["profileRef"], decisionRefs=[], status=status)
        b["mappings"][0]["nativeNodeId"] = endpoint
        plan["digest"] = ii.digest(plan)
        return plan, a, s, p

    def test_a_plain_endpoint_can_be_a_candidate(self):
        ii.check_plan(*self.documents("n.c-read"))

    def test_writes_and_state_block_a_candidate(self):
        for endpoint, ref in (("n.c-script", "write:e.script-gone"), ("n.c-total", "stateful:n.c-total"), ("n.c-chain", "write:e.script-gone")):
            with self.subTest(endpoint):
                with self.assertRaises(ii.Violation) as e: ii.check_plan(*self.documents(endpoint))
                self.assertEqual(e.exception.code, "editor.plan-blocked"); self.assertIn(ref, str(e.exception))

    def test_snapshot_and_profile_share_a_version(self):
        plan, a, s, _ = self.documents("n.c-read")
        for run in (lambda: ii.check_assessment(a, s, load("closure-a", "interpretation-profile.json")),
                    lambda: ii.check_plan(plan, a, s, load("closure-a", "interpretation-profile.json"))):
            with self.assertRaises(ii.Violation) as e: run()
            self.assertEqual(e.exception.code, "contract.version-mixed")

    def test_a_blocked_plan_may_say_so(self):
        ii.check_plan(*self.documents("n.c-script", status="blocked"))


if __name__ == "__main__":
    unittest.main()
