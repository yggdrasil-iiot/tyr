"""SI11 fixtures: S1→S2 revision pairs over the pio-like and closure-c snapshots (rules: fixtures/solution-intake/revision-1.1.0/RULES.md §7).

Every S2 renumbers all snapshot-local ids, shifts every text-line locator and changes the configuration artifact's
pin, so no pair can pass on ids, locators or file hashes. The expected verdicts are not written here: oracle.json in
each pair is written separately from RULES.md and the files below."""
import copy, hashlib, json, sys
from pathlib import Path
R = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(R/"backend")]
import interpretation_intake as ii, interpretation_closure as cl

SI = R/"fixtures/solution-intake"; OUT = SI/"revision-1.1.0"
PIO, CLOSURE_C, EDITOR = SI/"mimir-1.1.0/valid/pio-like", SI/"closure-1.1.0/closure-c", SI/"editor-2.0.0/valid"
WORKSPACE = {"revision": 7, "sha256": "3" * 64}
CONTINUITY = {"evidenceBasis": "declared-by-reviewer", "reviewer": "synthetic-reviewer",
              "reason": "the second export was taken from the same synthetic site after an edit", "evidenceRefs": [],
              "declaredAt": "2026-10-28T00:00:00Z"}


def write(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))


def stamp(doc): doc["digest"] = ii.digest(doc); return doc


def source(base):
    return {f: ii.load(base/f"{f}.json") for f in ("source-bundle", "interpretation-profile", "interpretation-snapshot")}


def node_key(namespace, native_id): return {"namespace": namespace, "nativeId": native_id}


def input_doc(mappings=(), retired=()):
    return {"sourceContinuity": CONTINUITY, "mappings": list(mappings), "retired": list(retired), "workspace": WORKSPACE}


def mapping(namespace, frm, to):
    return {"from": node_key(namespace, frm), "to": node_key(namespace, to), "evidenceBasis": "declared-by-reviewer",
            "reviewer": "synthetic-reviewer", "reason": "the same map entry under a new name", "evidenceRefs": [],
            "declaredAt": "2026-10-28T00:00:00Z"}


def revise(docs, edit, tag, artifact):
    """Apply the pair's edit to the S1 body (S1 ids), then renumber ids, shift locators, re-pin and restamp."""
    bundle, profile, snap = (copy.deepcopy(docs[k]) for k in ("source-bundle", "interpretation-profile", "interpretation-snapshot"))
    edit(bundle["body"], profile["body"], snap["body"])
    b = snap["body"]
    ids = {x[f] for f, xs in (("nodeId", b["nativeNodes"]), ("edgeId", b["referenceEdges"]), ("claimId", b["claims"]),
                              ("issueId", b["unresolved"])) for x in xs}
    renumber = {i: i.split(".", 1)[0] + "2." + i.split(".", 1)[1] for i in ids}

    def walk(x, key=None):
        if isinstance(x, dict):
            if x.get("kind") == "text-line": return {**x, "line": x["line"] + 1}
            return {k: walk(v, k) for k, v in x.items()}
        if isinstance(x, list): return [walk(v, key) for v in x]
        return renumber.get(x, x) if isinstance(x, str) and key != "targetText" else x
    for k in ("nativeNodes", "referenceEdges", "claims", "unresolved"): b[k] = walk(b[k])
    old = next(a["sha256"] for a in bundle["body"]["artifacts"] if a["artifactId"] == artifact)
    new = hashlib.sha256((old + tag).encode()).hexdigest()
    for a in bundle["body"]["artifacts"]:
        if a["artifactId"] == artifact: a["sha256"] = new
    for p in b["inputManifest"]:
        if p["artifactId"] == artifact: p["sha256"] = new
    bundle["version"] = snap["version"] = "2.0.0"
    stamp(bundle); stamp(profile)
    b["bundleRef"], b["profileRef"] = ii._pin(bundle), ii._pin(profile)
    stamp(snap); ii.check_pinned(snap, bundle, profile)
    return {"source-bundle": bundle, "interpretation-profile": profile, "interpretation-snapshot": snap}


def by(xs, field, value): return next(x for x in xs if x[field] == value)


# ---- pio-like edits (S1 ids) --------------------------------------------------------------------------------

def reorder(bundle, profile, b):
    for k in ("nativeNodes", "referenceEdges", "claims", "unresolved"): b[k].reverse()


def address_change(bundle, profile, b):
    by(b["claims"], "claimId", "c.temp-address")["value"] = "D101"
    by(b["referenceEdges"], "edgeId", "e.temp-source")["targetText"] = "plc1:D101"


def rename(bundle, profile, b):
    n = by(b["nativeNodes"], "nodeId", "n.line1-temp"); n["nativeId"], n["nativePath"] = "Line1.Temperature", ["Line1", "Temperature"]
    by(b["referenceEdges"], "edgeId", "e.avg-input")["targetText"] = "Line1.Temperature"


def deletion(bundle, profile, b):
    b["nativeNodes"] = [n for n in b["nativeNodes"] if n["nodeId"] != "n.line1-count"]
    b["referenceEdges"] = [e for e in b["referenceEdges"] if e["edgeId"] != "e.count-source"]
    b["unresolved"] = [u for u in b["unresolved"] if u["issueId"] != "u.count-source"]
    e = by(b["referenceEdges"], "edgeId", "e.reset-trigger"); e["resolution"] = "missing"; del e["targetNodeId"]
    e["basis"] = "no [map Line1.Count] section in any artifact of the bundle"
    b["unresolved"].append({"issueId": "u.reset-trigger", "code": "missing", "edgeId": "e.reset-trigger",
                            "reason": "Line1.Count is not in the bundle", "affectedNodeIds": ["n.line1-reset.script"]})


def twins(bundle, profile, b):
    temp = by(b["nativeNodes"], "nodeId", "n.line1-temp"); b["nativeNodes"].remove(temp)
    owned = [c for c in b["claims"] if c["subject"]["nodeId"] == "n.line1-temp"]
    source = by(b["referenceEdges"], "edgeId", "e.temp-source"); b["referenceEdges"].remove(source)
    for c in owned: b["claims"].remove(c)
    for t in ("a", "b"):
        n = copy.deepcopy(temp); n["nodeId"] = f"n.line1-temp{t}"
        n["nativeId"], n["nativePath"] = f"Line1.Temp{t.upper()}", ["Line1", f"Temp{t.upper()}"]
        e = copy.deepcopy(source); e["edgeId"], e["owner"]["nodeId"] = f"e.temp{t}-source", n["nodeId"]
        b["nativeNodes"].append(n); b["referenceEdges"].append(e)
        for c in owned:
            c = copy.deepcopy(c); c["claimId"] = c["claimId"].replace("c.temp-", f"c.temp{t}-"); c["subject"]["nodeId"] = n["nodeId"]
            dep = c.get("dependsOn", {})
            if "claimIds" in dep: dep["claimIds"] = [d.replace("c.temp-", f"c.temp{t}-") for d in dep["claimIds"]]
            if "edgeIds" in dep: dep["edgeIds"] = [e["edgeId"]]
            b["claims"].append(c)
    avg = by(b["referenceEdges"], "edgeId", "e.avg-input"); avg["targetText"], avg["targetNodeId"] = "Line1.TempA", "n.line1-tempa"
    plc = copy.deepcopy(by(b["nativeNodes"], "nodeId", "n.plc1")); plc["nodeId"] = "n.plc1-second"
    plc["locator"] = {**plc["locator"], "at": {"kind": "text-line", "line": 40}}; b["nativeNodes"].append(plc)


def retarget_capture(bundle, profile, b):
    e = by(b["referenceEdges"], "edgeId", "e.temp-source")
    e.update(targetText="plc2:D100", resolution="missing", basis="no [connection plc2] section in any artifact of the bundle"); del e["targetNodeId"]
    b["unresolved"].append({"issueId": "u.temp-source", "code": "missing", "edgeId": "e.temp-source",
                            "reason": "connection plc2 is not in the bundle", "affectedNodeIds": ["n.line1-temp"]})
    bundle["captureScope"] = b["coverage"]["capture"] = "declared-complete"; b["coverage"]["artifactsSkipped"] = 0


def profile_change(bundle, profile, b):
    by(profile["rules"], "ruleId", "synthetic-pio-like.scale")["version"] = "1.1.0"
    profile["interpreter"]["implementationDigest"] = "4" * 64
    by(b["claims"], "claimId", "c.temp-engineering")["rule"]["version"] = "1.1.0"


# ---- closure-c edits ----------------------------------------------------------------------------------------

def state_access(bundle, profile, b):
    n = by(b["nativeNodes"], "nodeId", "n.c-scale"); n["state"], n["stateKinds"] = "stateful", ["accumulator"]
    by(b["claims"], "claimId", "c.c-scale-state")["value"] = "stateful"
    by(b["referenceEdges"], "edgeId", "e.chain-total")["access"] = "write"


def context(bundle, profile, b): b["context"] = [{"key": "site", "value": "b"}]


# ---- S1 editor documents ------------------------------------------------------------------------------------

def decision(template, id_, snapshot, target, previous, **body):
    d = copy.deepcopy(template); d["id"] = id_; d.pop("envelope", None)
    d["body"].update(snapshotRef=ii._pin(snapshot), target=target, previousDecisionDigest=previous, **body)
    return stamp(d)


def closure_c_editor(docs):
    """The S1 editor set over closure-c that pairs 8 and 9 transfer (RULES.md §7 pair 8)."""
    s, p = docs["interpretation-snapshot"], docs["interpretation-profile"]
    d1t, d3t = ii.load(EDITOR/"decision-1.json"), ii.load(EDITOR/"decision-3.json")
    out, prev = {}, None
    for i, (t, target, kw) in enumerate([(d1t, {"type": "node", "id": "n.c-read"}, {}),
                                          (d3t, {"type": "node", "id": "n.c-read"}, {}),
                                          (d1t, {"type": "claim", "id": "c.c-scale-state"}, {}),
                                          (d1t, {"type": "node", "id": "n.c-chain"}, {})], 1):
        d = decision(t, f"synthetic/closure-c/decision-{i}", s, target, prev, **kw); prev = d["digest"]; out[f"decision-{i}"] = d
    depth = p["body"]["limits"]["maxReferenceDepth"]
    for name, endpoint, template, refs, status in (("read", "n.c-read", "temp", ("decision-1", "decision-2"), "candidate"),
                                                   ("chain", "n.c-chain", "count", ("decision-4",), "blocked")):
        a = ii.load(EDITOR/f"assessment-line1-{template}.json"); a.pop("envelope", None); a["id"] = f"synthetic/closure-c/assessment-{name}"
        r = cl.closure(s, endpoint, depth); b = a["body"]
        b.update(snapshotRef=ii._pin(s), endpoint={"nodeId": endpoint}, decisionRefs=[ii._pin(out[x]) for x in refs])
        b["closure"].update(nodeIds=r["nodeIds"], edgeIds=r["edgeIds"], completeness=r["completeness"])
        stamp(a); out[f"assessment-{name}"] = a
        plan = ii.load(EDITOR/f"plan-line1-{template}.json"); plan.pop("envelope", None); plan["id"] = f"synthetic/closure-c/plan-{name}"
        pb = plan["body"]; pb.update(assessmentRef=ii._pin(a), snapshotRef=ii._pin(s), profileRef=s["body"]["profileRef"],
                                     decisionRefs=[ii._pin(out[x]) for x in refs], status=status, workspace=WORKSPACE)
        for m in pb["mappings"]: m["nativeNodeId"] = endpoint
        stamp(plan); out[f"plan-{name}"] = plan
    ds = [out[f"decision-{i}"] for i in (1, 2, 3, 4)]; ii.check_decisions(ds, s)
    for name in ("read", "chain"): ii.check_plan(out[f"plan-{name}"], out[f"assessment-{name}"], s, p, ds)
    return out


def main():
    pio, cc = source(PIO), source(CLOSURE_C)
    pairs = [("01-reorder", pio, reorder, {"a": input_doc()}),
             ("02-address-change", pio, address_change, {"a": input_doc()}),
             ("03-rename", pio, rename, {"a": input_doc(), "b": input_doc([mapping("synthetic-pio-like", "Line1.Temp", "Line1.Temperature")])}),
             ("04-deletion", pio, deletion, {"a": input_doc(retired=[{"key": node_key("synthetic-pio-like", "Line1.Count"), "reviewer": "synthetic-reviewer",
                                                                      "reason": "the map entry was removed from the site", "declaredAt": "2026-10-28T00:00:00Z"}])}),
             ("05-twins", pio, twins, {"a": input_doc(), "b": input_doc([mapping("synthetic-pio-like", "Line1.Temp", "Line1.TempA")])}),
             ("06-retarget-capture", pio, retarget_capture, {"a": input_doc()}),
             ("07-profile-change", pio, profile_change, {"a": input_doc()}),
             ("08-closure-c-state-access", cc, state_access, {"a": input_doc()}),
             ("09-closure-c-context", cc, context, {"a": input_doc()})]
    for name, docs, edit, inputs in pairs:
        artifact = docs["interpretation-snapshot"]["body"]["inputManifest"][0]["artifactId"]
        for f, d in revise(docs, edit, name, artifact).items(): write(OUT/name/"s2"/f"{f}.json", d)
        for v, d in inputs.items(): write(OUT/name/f"transfer-input-{v}.json", d)
    for f, d in closure_c_editor(cc).items(): write(OUT/"closure-c-s1"/f"{f}.json", d)
    # pair 10: S1 chain extended by a hold that supersedes decision-1; S2 is pair 1's.
    d3 = ii.load(EDITOR/"decision-3.json")
    d4 = decision(ii.load(EDITOR/"decision-1.json"), "synthetic/pio-like/decision-4", pio["interpretation-snapshot"],
                  {"type": "claim", "id": "c.temp-scale"}, d3["digest"], decision="hold", reason="the scale is being re-checked on site")
    ii.check_decisions([ii.load(EDITOR/f"decision-{i}.json") for i in (1, 2, 3)] + [d4], pio["interpretation-snapshot"])
    write(OUT/"10-superseded"/"s1-decision-4.json", d4); write(OUT/"10-superseded"/"transfer-input-a.json", input_doc())


if __name__ == "__main__":
    main()
