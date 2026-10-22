"""P4-F A2: receive Mímir interpretation snapshots and check Týr editor documents. Offline; no vendor file is read."""
import copy, hashlib, json, sys, unittest
from pathlib import Path
from unittest.mock import patch
R = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(R/"backend"), str(R/"scripts")]
import interpretation_intake as ii

PIN = R/"vendor-contracts/mimir/interpretation/PIN.json"
MIMIR = R/"fixtures/solution-intake/mimir-1.0.0"
EDITOR = R/"fixtures/solution-intake/editor-2.0.0"


def mimir(base, file): return ii.load(MIMIR/"valid"/base/file)
def editor(file): return ii.load(EDITOR/"valid"/file)


def apply(doc, edit):
    """JSON-pointer set/remove, enough for the case files."""
    *parents, last = edit["path"].split("/")[1:]
    node = doc
    for p in parents: node = node[int(p)] if isinstance(node, list) else node[p]
    key = int(last) if isinstance(node, list) else last
    if edit["op"] == "set": node[key] = copy.deepcopy(edit["value"])
    else: del node[key]


def edited(doc, case_or_spec):
    doc = copy.deepcopy(doc)
    for e in case_or_spec.get("edits", []): apply(doc, e)
    if case_or_spec.get("restamp"): doc["digest"] = ii.digest(doc)
    return doc


class Pins(unittest.TestCase):
    def test_vendored_files_match_the_pin_list(self):
        pin = json.loads(PIN.read_text(encoding="utf-8")); self.assertEqual(pin["source"]["commit"], "f8691d0")
        for group, root in (("contracts", R/"vendor-contracts/mimir/interpretation/1.0.0"), ("fixtures", MIMIR)):
            listed = {e["path"]: e["sha256"] for e in pin[group]}
            present = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
            self.assertEqual(set(listed), present, group)
            for path, sha in listed.items(): self.assertEqual(hashlib.sha256((root/path).read_bytes()).hexdigest(), sha, path)
        self.assertEqual(len(pin["contracts"]), 6)


class Jcs(unittest.TestCase):
    def test_vendored_vectors(self):
        v = json.loads((MIMIR/"jcs-vectors.json").read_text(encoding="utf-8")); n = 0
        for c in v["canonical"]:
            with self.subTest(c["name"]): self.assertEqual(ii.jcs(ii.parse(c["input"])), c["canonical"]); n += 1
        for c in v["rejected"]:
            with self.subTest(c["name"]):
                with self.assertRaises(ii.Violation) as e: ii.jcs(ii.parse(c["input"]))
                self.assertEqual(e.exception.code, c["code"]); n += 1
        self.assertEqual(n, 14)


class MimirSnapshots(unittest.TestCase):
    def test_valid_sets_are_received(self):
        for base in ("pio-like", "kepware-like"):
            with self.subTest(base):
                ii.check_pinned(mimir(base, "interpretation-snapshot.json"), mimir(base, "source-bundle.json"), mimir(base, "interpretation-profile.json"))
        req = mimir("pio-like", "interpret-request.json")
        ii.check_request(req, mimir("pio-like", "source-bundle.json"), mimir("pio-like", "interpretation-profile.json"))
        ii.check_result(mimir("pio-like", "interpret-result.json"), req, mimir("pio-like", "interpretation-snapshot.json"))

    def test_tyr_digest_agrees_with_mimirs(self):
        # Mímir stamped these with its Python script and checks them in Java; this is a third, separate implementation.
        for base in ("pio-like", "kepware-like"):
            for f in ("source-bundle.json", "interpretation-profile.json", "interpretation-snapshot.json"):
                with self.subTest(f"{base}/{f}"): d = mimir(base, f); self.assertEqual(ii.digest(d), d["digest"])

    def test_receiving_never_opens_a_vendor_artifact(self):
        opened = []
        real = Path.read_bytes
        def spy(self_): opened.append(self_); return real(self_)
        docs = [mimir("pio-like", f) for f in ("interpretation-snapshot.json", "source-bundle.json", "interpretation-profile.json")]
        for kind in ("interpretation-snapshot", "source-bundle", "interpretation-profile"): ii._validator(kind)  # schemas are read once, before the spy
        with patch.object(Path, "read_bytes", spy), patch.object(Path, "read_text", lambda *a, **k: (_ for _ in ()).throw(AssertionError("read_text"))):
            ii.check_pinned(*docs)
        self.assertFalse([p for p in opened if "artifacts" in p.parts])

    def test_mimir_rejection_cases(self):
        cases = json.loads((MIMIR/"invalid/cases.json").read_text(encoding="utf-8"))["cases"]; ran = 0
        for c in cases:
            with self.subTest(c["name"]):
                base = c["base"]; doc = edited(mimir(base, c["file"]), c); comp = c.get("companions", {})
                def other(role, file):
                    spec = comp.get(role, {}); return edited(mimir(spec.get("base", base), file), spec)
                run = {"single": lambda: ii.check(doc),
                       "pinned": lambda: ii.check_pinned(doc, other("bundle", "source-bundle.json"), other("profile", "interpretation-profile.json")),
                       "request": lambda: ii.check_request(doc, other("bundle", "source-bundle.json"), other("profile", "interpretation-profile.json")),
                       "result": lambda: ii.check_result(doc, other("request", "interpret-request.json"), other("snapshot", "interpretation-snapshot.json"))}[c["mode"]]
                if c["expect"] is None: run()
                else:
                    with self.assertRaises(ii.Violation) as e: run()
                    self.assertEqual(e.exception.code, c["expect"], str(e.exception))
                ran += 1
        self.assertEqual(ran, 37)


class SI19(unittest.TestCase):
    """The Týr half of SI19: a tampered pin, an unknown snapshot contract version and an evidence-ownership breach are refused."""
    def refused(self, code, fn):
        with self.assertRaises(ii.Violation) as e: fn()
        self.assertEqual(e.exception.code, code)

    def test_pin_tampered(self):
        s = mimir("pio-like", "interpretation-snapshot.json"); s["body"]["inputManifest"][0]["sha256"] = "f" * 64
        self.refused("digest.mismatch", lambda: ii.check(s))
        s["digest"] = ii.digest(s)
        self.refused("pin.artifact-mismatch", lambda: ii.check_pinned(s, mimir("pio-like", "source-bundle.json"), mimir("pio-like", "interpretation-profile.json")))

    def test_unknown_snapshot_contract_version(self):
        s = mimir("pio-like", "interpretation-snapshot.json"); s["contractVersion"] = "1.1.0"; s["digest"] = ii.digest(s)
        self.refused("contract.version-unsupported", lambda: ii.check(s))

    def test_evidence_ownership_both_ways(self):
        s = mimir("pio-like", "interpretation-snapshot.json"); s["body"]["claims"][0]["evidenceBasis"] = "declared-by-reviewer"; s["digest"] = ii.digest(s)
        self.refused("snapshot.evidence-basis-not-owned", lambda: ii.check(s))
        d = editor("decision-1.json"); d["body"]["evidenceBasis"] = "observed-in-artifact"; d["digest"] = ii.digest(d)
        self.refused("editor.evidence-basis-not-owned", lambda: ii.check(d))


class EditorDocuments(unittest.TestCase):
    def snapshot(self): return mimir("pio-like", "interpretation-snapshot.json")
    def profile(self): return mimir("pio-like", "interpretation-profile.json")
    def decisions(self): return [editor(f"decision-{i}.json") for i in (1, 2, 3)]

    def test_valid_set(self):
        s, ds = self.snapshot(), self.decisions(); ii.check_decisions(ds, s)
        for n in ("temp", "count"):
            with self.subTest(n):
                a = editor(f"assessment-line1-{n}.json"); ii.check_assessment(a, s, self.profile(), ds); ii.check_plan(editor(f"plan-line1-{n}.json"), a, s, self.profile(), ds)

    def test_rejection_cases(self):
        cases = json.loads((EDITOR/"invalid/cases.json").read_text(encoding="utf-8"))["cases"]; ran = 0
        for c in cases:
            with self.subTest(c["name"]):
                doc = edited(editor(c["file"]), c); s, ds = self.snapshot(), self.decisions()
                if c["file"].startswith("decision-"):
                    i = int(c["file"][9]) - 1; ds = ds[:i] + [doc]
                run = {"single": lambda: ii.check(doc),
                       "decisions": lambda: ii.check_decisions(ds, s),
                       "assessment": lambda: ii.check_assessment(doc, s, self.profile(), ds),
                       "plan": lambda: ii.check_plan(doc, editor(c["assessment"]), s, self.profile(), ds)}[c["mode"]]
                if c["expect"] is None: run()
                else:
                    with self.assertRaises(ii.Violation) as e: run()
                    self.assertEqual(e.exception.code, c["expect"], str(e.exception))
                ran += 1
        self.assertEqual(ran, len(cases)); self.assertGreaterEqual(ran, 28)


if __name__ == "__main__":
    unittest.main()
