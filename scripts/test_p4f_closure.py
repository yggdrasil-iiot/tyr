"""P4-F §5: endpoint closure over Mimir snapshots, checked against an oracle written independently of the code."""
import copy, json, random, sys, unittest
from pathlib import Path
R = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(R/"backend"), str(R/"scripts")]
import interpretation_closure as cl, interpretation_intake as ii

F = R/"fixtures/solution-intake/closure-1.0.0"


def load(sub, name): return ii.load(F/sub/name)
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


if __name__ == "__main__":
    unittest.main()
