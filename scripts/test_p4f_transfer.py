"""P4-F SI11: review transfer across snapshot revisions (fixtures/solution-intake/revision-1.1.0/RULES.md). Offline."""
import copy, json, sys, unittest
from pathlib import Path
R = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(R/"backend")]
import interpretation_intake as ii, interpretation_transfer as tr

SI = R/"fixtures/solution-intake"; REV = SI/"revision-1.1.0"
SNAP = ("source-bundle", "interpretation-profile", "interpretation-snapshot")
PAIRS = {"01-reorder": "a", "02-address-change": "a", "03-rename": "ab", "04-deletion": "a", "05-twins": "ab",
         "06-retarget-capture": "a", "07-profile-change": "a", "08-closure-c-state-access": "a", "09-closure-c-context": "a",
         "10-superseded": "a"}


def load_snapshot(folder): return [ii.load(folder/f"{f}.json") for f in SNAP]


def s1(pair):
    """S1 and its editor documents: decisions in chain order, assessments, plans."""
    if "closure-c" in pair:
        docs = load_snapshot(SI/"closure-1.1.0/closure-c"); e = REV/"closure-c-s1"
        d = [ii.load(e/f"decision-{i}.json") for i in (1, 2, 3, 4)]
        a = [ii.load(e/f"assessment-{n}.json") for n in ("read", "chain")]; c = [ii.load(e/f"plan-{n}.json") for n in ("read", "chain")]
    else:
        docs = load_snapshot(SI/"mimir-1.1.0/valid/pio-like"); e = SI/"editor-2.0.0/valid"
        d = [ii.load(e/f"decision-{i}.json") for i in (1, 2, 3)]
        if pair == "10-superseded": d.append(ii.load(REV/pair/"s1-decision-4.json"))
        a = [ii.load(e/f"assessment-line1-{n}.json") for n in ("temp", "count")]; c = [ii.load(e/f"plan-line1-{n}.json") for n in ("temp", "count")]
    return docs, d, a, c


def s2(pair): return load_snapshot(REV/("01-reorder" if pair == "10-superseded" else pair)/"s2")


def run(pair, v):
    (b1, p1, sn1), d, a, c = s1(pair); b2, p2, sn2 = s2(pair)
    declaration = json.loads((REV/pair/f"transfer-input-{v}.json").read_text(encoding="utf-8"))
    body, copies = tr.transfer(sn1, b1, p1, sn2, b2, p2, d, a, c, declaration)
    return body, copies, (sn1, b1, p1, sn2, b2, p2, d, a, c)


def summary(body):
    return {"globals": body["globals"],
            "correspondence": [{"type": x["type"], "fromId": x["fromId"], "toId": x["toId"], "outcome": x["outcome"], "candidates": x["candidates"]}
                               for x in body["correspondence"]],
            "superseded": [{"decision": x["decision"]["id"], "supersededBy": x["supersededBy"]["id"]} for x in body["superseded"]],
            "verdicts": [{"kind": r["document"]["kind"], "id": r["document"]["id"], "verdict": r["verdict"], "target": r["target"],
                          "reasons": r["reasons"], "candidates": r["candidates"]} for r in body["verdicts"]]}


def transfer_doc(pair, v):
    body, copies, args = run(pair, v)
    return tr.document(f"synthetic/transfer/{pair}-{v}", body), copies, args


def restamp(doc): doc["digest"] = ii.digest(doc); return doc


class OracleAgreement(unittest.TestCase):
    """Every pair against the oracle an independent reviewer wrote from RULES.md and the fixtures alone."""
    def test_pairs(self):
        ran = 0
        for pair, vs in PAIRS.items():
            for v in vs:
                with self.subTest(f"{pair}-{v}"):
                    oracle = json.loads((REV/pair/f"oracle-{v}.json").read_text(encoding="utf-8"))
                    body, copies, _ = run(pair, v); got = summary(body)
                    for field in ("globals", "correspondence", "superseded", "verdicts"): self.assertEqual(got[field], oracle[field], field)
                    self.assertEqual([{"from": c["from"]["id"], "to": c["to"]["id"], "targetId": d["body"]["target"]["id"]}
                                      for c, d in zip(body["carried"], copies)], oracle["carried"])
                    ran += 1
        self.assertEqual(ran, 12)


class Checker(unittest.TestCase):
    def test_every_pair_round_trips(self):
        for pair, vs in PAIRS.items():
            for v in vs:
                with self.subTest(f"{pair}-{v}"):
                    t, copies, (sn1, b1, p1, sn2, b2, p2, d, a, c) = transfer_doc(pair, v)
                    tr.check_transfer(t, sn1, b1, p1, sn2, b2, p2, d, a, c, copies)

    def refused(self, code, pair, edit, d2_edit=None):
        t, copies, args = transfer_doc(pair, "a"); t = copy.deepcopy(t); copies = copy.deepcopy(copies)
        edit(t["body"], copies)
        if d2_edit: d2_edit(t["body"], copies)
        restamp(t)
        with self.assertRaises(ii.Violation) as e: tr.check_transfer(t, *args, copies)
        self.assertEqual(e.exception.code, code, str(e.exception))

    def test_rejections(self):
        key = lambda n: {"namespace": "synthetic-pio-like", "nativeId": n}
        m = lambda frm, to, basis="declared-by-reviewer": {"from": key(frm), "to": key(to), "evidenceBasis": basis, "reviewer": "r",
                                                          "reason": "r", "evidenceRefs": [], "declaredAt": "2026-10-28T00:00:00Z"}
        def copy_reason(b, c):
            c[0]["body"]["reason"] = "changed in the copy"; restamp(c[0]); b["carried"][0]["to"] = ii._pin(c[0])
        def carry_superseded(b, c):
            d1 = ii.load(SI/"editor-2.0.0/valid/decision-1.json"); b["carried"].insert(0, {"from": ii._pin(d1), "to": b["carried"][0]["to"]})
        def drop_marker(b, c):
            c[0]["body"]["evidenceRefs"] = c[0]["body"]["evidenceRefs"][:-1]; restamp(c[0]); b["carried"][0]["to"] = ii._pin(c[0])
        def swap(b, c): c[0], c[1] = c[1], c[0]
        def verdict(b, c):
            r = next(r for r in b["verdicts"] if r["verdict"] == "reusable"); r["verdict"] = "stale"
        def s1_decision_in_s2(b, c): c.append(ii.load(SI/"editor-2.0.0/valid/decision-1.json"))
        cases = [
            ("transfer.mapping-target-missing", "10-superseded", lambda b, c: b["mappings"].append(m("Line1.Temp", "Line9.Nowhere"))),
            ("transfer.mapping-evidence-not-owned", "10-superseded", lambda b, c: b["mappings"].append(m("Line1.Temp", "Line1.Temp", "observed-in-artifact"))),
            ("transfer.mapping-source-missing", "01-reorder", lambda b, c: b["mappings"].append(m("Line9.Nowhere", "Line1.Temp"))),
            ("transfer.mapping-conflict", "01-reorder", lambda b, c: b["mappings"].extend([m("Line1.Temp", "Line1.Temp"), m("Line1.Count", "Line1.Temp")])),
            ("transfer.retired-key-present", "01-reorder", lambda b, c: b["retired"].append({"key": key("Line1.Temp"), "reviewer": "r", "reason": "r", "declaredAt": "2026-10-28T00:00:00Z"})),
            ("transfer.artifact-pins-mismatch", "01-reorder", lambda b, c: b["to"]["artifactPins"].pop()),
            ("transfer.snapshot-mismatch", "01-reorder", lambda b, c: b["from"].update(profile=b["to"]["profile"] | {"digest": "0" * 64})),
            ("transfer.decision-chain-invalid", "01-reorder", lambda b, c: b.update(fromDecisionChainHead=None)),
            ("transfer.verdict-mismatch", "02-address-change", verdict),
            ("transfer.carried-copy-differs", "10-superseded", copy_reason),
            ("transfer.carried-source-superseded", "10-superseded", carry_superseded),
            ("transfer.carried-evidence-ref-missing", "01-reorder", drop_marker),
            ("transfer.carried-copy-order", "01-reorder", swap),
            ("pin.snapshot-mismatch", "01-reorder", s1_decision_in_s2),
            ("transfer.continuity-missing", "01-reorder", lambda b, c: b["sourceContinuity"].update(evidenceBasis="observed-in-artifact")),
            ("transfer.mapping-target-ambiguous", "05-twins", lambda b, c: b["mappings"].append(m("Line1.Temp", "plc1"))),
            ("transfer.workspace-missing", "01-reorder", lambda b, c: b.update(workspace=None)),
            ("transfer.correspondence-mismatch", "02-address-change", lambda b, c: b["correspondence"][0].update(outcome="changed")),
            ("transfer.superseded-mismatch", "10-superseded", lambda b, c: b["superseded"].clear()),
            ("transfer.globals-mismatch", "01-reorder", lambda b, c: b["globals"].update(captureChanged=True)),
            ("transfer.carried-verdict-not-carried", "01-reorder", lambda b, c: b["carried"].pop()),
            ("transfer.carried-copy-missing", "01-reorder", lambda b, c: c.pop(0)),
        ]
        for code, pair, edit in cases:
            with self.subTest(code): self.refused(code, pair, edit)

    def test_digest_is_checked(self):
        t, copies, args = transfer_doc("01-reorder", "a"); t = copy.deepcopy(t); t["body"]["globals"]["profileChanged"] = True
        with self.assertRaises(ii.Violation) as e: tr.check_transfer(t, *args, copies)
        self.assertEqual(e.exception.code, "digest.mismatch")


class Keys(unittest.TestCase):
    """RULES.md §2.1 and §3 on items the pairs do not separate on their own."""
    def test_relation_is_part_of_the_edge_key_and_target_text_only_breaks_ties(self):
        (_, p, s), *_ = s1("01-reorder"); v = tr.View(s, p); script = ("synthetic-pio-like", "Line1.Reset#script")
        self.assertEqual(v.edge_key["e.reset-trigger"], (script, "script", "input"))
        self.assertEqual(v.edge_key["e.reset-write"], (script, "script", "reference"))
        (_, p, s), *_ = s1("08-closure-c-state-access"); v = tr.View(s, p)
        self.assertEqual(v.edge_key["e.script-gone"], (("synthetic-closure", "Line1.Script"), "writeTo", "reference", "Line9.Missing"))

    def test_a_state_change_alone_changes_the_node(self):
        (_, p, s), *_ = s1("01-reorder"); s2 = copy.deepcopy(s)
        tr_node = next(n for n in s2["body"]["nativeNodes"] if n["nodeId"] == "n.line1-tempavg.script"); tr_node["state"] = "stateless"
        self.assertEqual(tr.Match(tr.View(s, p), tr.View(s2, p)).outcome("node", "n.line1-tempavg.script")[0], "changed")


class Properties(unittest.TestCase):
    def against_itself(self, pair):
        (b1, p1, sn1), d, a, c = s1(pair)
        body, _ = tr.transfer(sn1, b1, p1, sn1, b1, p1, d, a, c, {"sourceContinuity": {}, "mappings": [], "retired": [], "workspace": c[0]["body"]["workspace"]})
        self.assertTrue(all(x["outcome"] == "same" for x in body["correspondence"]), pair)
        return {r["document"]["id"].split("/")[-1]: (r["verdict"], [(x["code"], x["ref"].split("/")[-1]) for x in r["reasons"]]) for r in body["verdicts"]}

    def test_a_snapshot_against_itself_carries_everything(self):
        self.assertTrue(all(v in ("carried", "reusable") and not r for v, r in self.against_itself("01-reorder").values()))

    def test_citing_a_superseded_decision_never_carries(self):
        """closure-c's decision-1 is followed by decision-2 on the same node; the documents citing decision-1 stay stale."""
        got = self.against_itself("08-closure-c-state-access")
        self.assertEqual({k: v for k, v in got.items() if v[0] != "carried" and v[0] != "reusable"},
                         {"assessment-read": ("stale", [("decision-not-carried", "decision-1")]),
                          "plan-read": ("stale", [("assessment-not-reusable", "assessment-read"), ("decision-not-carried", "decision-1")])})

    def test_list_order_does_not_matter_and_inputs_stay_untouched(self):
        for pair in ("02-address-change", "05-twins", "08-closure-c-state-access"):
            body, _, args = run(pair, "b" if pair == "05-twins" else "a"); before = copy.deepcopy(args)
            sn1, b1, p1, sn2, b2, p2, d, a, c = copy.deepcopy(args)
            for s in (sn1, sn2):
                for k in ("nativeNodes", "referenceEdges", "claims", "unresolved"): s["body"][k] = s["body"][k][1:] + s["body"][k][:1]
            declaration = json.loads((REV/pair/("transfer-input-b.json" if pair == "05-twins" else "transfer-input-a.json")).read_text(encoding="utf-8"))
            again, _ = tr.transfer(sn1, b1, p1, sn2, b2, p2, d, list(reversed(a)), list(reversed(c)), declaration)
            for field in ("globals", "correspondence", "superseded", "verdicts", "carried"): self.assertEqual(again[field], body[field], pair + " " + field)
            self.assertEqual(args, before)

    def test_carried_copies_follow_the_rule(self):
        """RULES.md §4.6, checked field by field rather than by recomputation."""
        body, copies, (sn1, b1, p1, sn2, *_rest) = run("03-rename", "b"); d1 = {d["id"]: d for d in s1("03-rename")[1]}
        previous = None
        for link, c in zip(body["carried"], copies):
            src = d1[link["from"]["id"]]
            self.assertEqual(c["id"], src["id"] + ".carried." + sn2["digest"][:12])
            self.assertEqual(c["body"]["snapshotRef"], ii._pin(sn2)); self.assertEqual(c["body"]["previousDecisionDigest"], previous)
            self.assertEqual(c["body"]["evidenceRefs"], src["body"]["evidenceRefs"] + [f"carried-from:review-decision:{src['id']}@{src['digest']}"])
            same = lambda d: {k: v for k, v in d["body"].items() if k not in ("snapshotRef", "target", "previousDecisionDigest", "evidenceRefs")}
            self.assertEqual(same(c), same(src)); self.assertEqual(c["body"]["target"]["type"], src["body"]["target"]["type"])
            self.assertTrue(c["body"]["target"]["id"].startswith("n2.") or c["body"]["target"]["id"][1:3] == "2.")
            self.assertEqual(c["digest"], ii.digest(c)); previous = c["digest"]
        self.assertEqual(len(copies), 3); ii.check_decisions(copies, sn2)

    def test_candidates_are_never_chosen(self):
        body, copies, _ = run("03-rename", "a")
        temp = next(r for r in body["verdicts"] if r["document"]["id"].endswith("decision-3"))
        self.assertEqual((temp["verdict"], temp["target"]["toId"], temp["candidates"]), ("orphaned", None, ["n2.line1-temp"]))
        self.assertNotIn("synthetic/pio-like/decision-3", [c["from"]["id"] for c in body["carried"]])


if __name__ == "__main__":
    unittest.main()
