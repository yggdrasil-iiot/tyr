"""P4-F SI11: which review work over snapshot S1 still applies to S2, a later revision of the same source.

Rules: fixtures/solution-intake/revision-1.1.0/RULES.md. Identity across revisions is the native key Mimir publishes
(namespace, nativeId), never a snapshot-local id or a locator; edges, claims and issues are keyed through their node.
A reviewer's mapping is the only way a renamed node keeps its identity: nothing is chosen from candidates. Evidence is
compared as interpreted content (claims, edges, state), not as file hashes, which change on every revision. S1
documents are never edited: a judgment that carries is copied onto S2, and the review-transfer records the act.
"""
import hashlib
import interpretation_closure as cl
import interpretation_intake as ii

RULE = "si11-1"


def _plain(x):
    """Keys are tuples while computing; JCS takes lists."""
    if isinstance(x, (list, tuple)): return [_plain(v) for v in x]
    if isinstance(x, dict): return {k: _plain(v) for k, v in x.items()}
    return x


def fp(x): return hashlib.sha256(ii.jcs(_plain(x)).encode("utf-8")).hexdigest()


def _sorted(xs): return sorted((_plain(x) for x in xs), key=ii.jcs)


def _nk(key): return {"namespace": key[0], "nativeId": key[1]}


class View:
    """One snapshot seen through native keys. For S1, sigma (the reviewer's mappings) renames node keys first,
    so every key and fingerprint is already in S2's vocabulary."""

    def __init__(self, snapshot, profile, sigma=None):
        self.snapshot, self.profile, b = snapshot, profile, snapshot["body"]
        self.marked = snapshot["contractVersion"] != "1.0.0"
        self.nodes = {n["nodeId"]: n for n in b["nativeNodes"]}
        self.edges = {e["edgeId"]: e for e in b["referenceEdges"]}
        self.claims = {c["claimId"]: c for c in b["claims"]}
        self.issues = {u["issueId"]: u for u in b["unresolved"]}
        sigma = sigma or {}
        self.raw = {i: (n["namespace"], n["nativeId"]) for i, n in self.nodes.items()}
        self.key = {i: sigma.get(k, k) for i, k in self.raw.items()}
        self.edge_base = {i: (self.key[e["owner"]["nodeId"]], e["owner"]["field"], e["relation"]) for i, e in self.edges.items()}
        self.claim_base = {i: (self.key[c["subject"]["nodeId"]], c["subject"]["field"]) for i, c in self.claims.items()}
        self.edge_key = self._extend(self.edge_base, lambda i: self.edges[i]["targetText"])
        self.claim_key = self._extend(self.claim_base, lambda i: self.claims[i]["evidenceBasis"])
        self.owned = {}
        for i, e in self.edges.items(): self.owned.setdefault(e["owner"]["nodeId"], []).append(i)

    @staticmethod
    def _extend(base, refine):
        count = {}
        for k in base.values(): count[k] = count.get(k, 0) + 1
        return {i: k + (refine(i),) if count[k] > 1 else k for i, k in base.items()}

    def issue_key(self, i):
        u = self.issues[i]
        if "nodeId" in u: return (u["code"], "node", self.key[u["nodeId"]], u.get("field"))
        if "edgeId" in u: return (u["code"], "edge", self.edge_key[u["edgeId"]], u.get("field"))
        return None

    # ---- content (RULES.md §3) -------------------------------------------------------------------------------
    def node_content(self, i):
        n = self.nodes[i]
        return {"kind": n["kind"], "state": n.get("state") if self.marked else None,
                "stateKinds": sorted(n["stateKinds"]) if self.marked and "stateKinds" in n else None,
                "outputs": _sorted({"name": o["name"], "value": o["value"]} for o in n.get("outputs", []))}

    def edge_content(self, i):
        e = self.edges[i]
        return {"field": e["owner"]["field"], "relation": e["relation"], "access": e.get("access") if self.marked else None,
                "targetText": e["targetText"], "resolution": e["resolution"], "basis": e["basis"],
                "target": list(self.key[e["targetNodeId"]]) if "targetNodeId" in e else None,
                "candidates": _sorted(list(self.key[c]) for c in e["candidates"]) if "candidates" in e else None}

    def claim_content(self, i):
        c = self.claims[i]; dep = c.get("dependsOn", {})
        return {"field": c["subject"]["field"], "value": c["value"], "evidenceBasis": c["evidenceBasis"], "status": c["status"],
                "rule": {"ruleId": c["rule"]["ruleId"], "version": c["rule"]["version"]} if "rule" in c else None,
                "dependsOn": {"claims": _sorted(list(self.claim_key[d]) for d in dep.get("claimIds", [])),
                              "edges": _sorted(list(self.edge_key[d]) for d in dep.get("edgeIds", []))}}

    def issue_content(self, i):
        u = self.issues[i]
        anchor = ["node", list(self.key[u["nodeId"]])] if "nodeId" in u else ["edge", list(self.edge_key[u["edgeId"]])] if "edgeId" in u else None
        return {"code": u["code"], "field": u.get("field"), "reason": u["reason"], "anchor": anchor,
                "affected": _sorted(list(self.key[a]) for a in u["affectedNodeIds"])}

    def content(self, type_, i):
        return {"node": self.node_content, "edge": self.edge_content, "claim": self.claim_content, "issue": self.issue_content}[type_](i)

    # ---- scopes (RULES.md §3.2) ------------------------------------------------------------------------------
    def hop_items(self, n):
        """oneHop(n): the node, its claims, the edges it owns and the issues anchored on it or on those edges."""
        owned = self.owned.get(n, [])
        return ([("node", n)] + [("claim", c) for c, x in self.claims.items() if x["subject"]["nodeId"] == n]
                + [("edge", e) for e in owned]
                + [("issue", u) for u, x in self.issues.items() if x.get("nodeId") == n or x.get("edgeId") in owned])

    def hop(self, n):
        items = self.hop_items(n)
        return {"node": self.node_content(n), "claims": _sorted(self.claim_content(i) for t, i in items if t == "claim"),
                "edges": _sorted(self.edge_content(i) for t, i in items if t == "edge"),
                "issues": _sorted(self.issue_content(i) for t, i in items if t == "issue")}

    def claim_scope(self, c):
        claims, edges, todo = [], [], [c]
        while todo:
            x = todo.pop()
            if x in claims: continue
            claims.append(x); dep = self.claims[x].get("dependsOn", {})
            todo += dep.get("claimIds", []); edges += [e for e in dep.get("edgeIds", []) if e not in edges]
        return [("claim", x) for x in claims] + [("edge", e) for e in edges]

    def closure(self, n): return cl.closure(self.snapshot, n, self.profile["body"]["limits"]["maxReferenceDepth"])

    def _reason_ref(self, code, ref):
        if code in ("depth-limit", "unexplained-leaf"): return list(self.key[ref])
        if code == "unresolved-issue":
            k = self.issue_key(ref); return list(k) if k else ["unkeyed", ref]
        if code == "evaluation-cycle": return _sorted(list(self.key[x]) for x in ref.split(","))
        return list(self.edge_key[ref])

    def closure_view(self, n, members=True):
        r = self.closure(n)
        view = {"edges": _sorted(self.edge_content(e) for e in r["edgeIds"]), "completeness": r["completeness"],
                "reasons": _sorted({"code": x["code"], "ref": self._reason_ref(x["code"], x["ref"])} for x in r["reasons"]),
                "captureScope": r["captureScope"],
                "stateful": _sorted(list(self.key[x]) for x in r["statefulNodeIds"]) if self.marked else [],
                "stateUnknown": _sorted(list(self.key[x]) for x in r.get("stateUnknownNodeIds", [])),
                "events": _sorted(list(self.edge_key[x]) for x in r.get("eventEdgeIds", [])),
                "writes": _sorted({"edge": list(self.edge_key[w["edgeId"]]), "targetText": w["targetText"], "resolution": w["resolution"],
                                   "target": list(self.key[w["targetNodeId"]]) if "targetNodeId" in w else None} for w in r.get("writeTargets", []))}
        if members: view["members"] = _sorted([list(self.key[m]), fp(self.hop(m))] for m in r["nodeIds"])
        return view, r


class Match:
    """Correspondence of every S1 item in S2 (RULES.md §2.3)."""

    def __init__(self, v1, v2):
        self.v1, self.v2 = v1, v2
        self.out = {}  # (type, s1 id) -> (outcome, s2 id or None)
        by = lambda m: {k: [i for i in m if m[i] == k] for k in set(m.values())}
        n1, n2 = by(v1.raw), by(v2.key)
        for i in v1.nodes:
            here, there = n1[v1.raw[i]], n2.get(v1.key[i], [])
            self.out[("node", i)] = ("ambiguous", None) if len(here) > 1 or len(there) > 1 else ("absent", None) if not there else ("matched", there[0])
        for type_, owner, base1, base2, refine in (
                ("edge", lambda i: v1.edges[i]["owner"]["nodeId"], v1.edge_base, v2.edge_base, lambda v, i: v.edges[i]["targetText"]),
                ("claim", lambda i: v1.claims[i]["subject"]["nodeId"], v1.claim_base, v2.claim_base, lambda v, i: v.claims[i]["evidenceBasis"])):
            g1, g2 = by(base1), by(base2)
            for i in base1:
                o = self.out[("node", owner(i))]
                if o[0] != "matched": self.out[(type_, i)] = (o[0], None); continue
                b1, b2 = g1[base1[i]], g2.get(base1[i], [])
                if len(b1) == 1 and len(b2) <= 1: self.out[(type_, i)] = ("matched", b2[0]) if b2 else ("absent", None); continue
                t1 = [x for x in b1 if refine(v1, x) == refine(v1, i)]; t2 = [x for x in b2 if refine(v2, x) == refine(v1, i)]
                self.out[(type_, i)] = ("matched", t2[0]) if len(t1) == 1 and len(t2) == 1 else ("absent", None) if len(t1) == 1 and not t2 else ("ambiguous", None)
        k1 = {i: v1.issue_key(i) for i in v1.issues}; k2 = {i: v2.issue_key(i) for i in v2.issues}
        for i, k in k1.items():
            if k is None: self.out[("issue", i)] = ("unkeyed", None); continue
            u1 = [x for x in k1 if k1[x] == k]; u2 = [x for x in k2 if k2[x] == k]
            self.out[("issue", i)] = ("matched", u2[0]) if len(u1) == 1 and len(u2) == 1 else ("absent", None) if not u2 else ("ambiguous", None)

    def outcome(self, type_, i):
        o, j = self.out[(type_, i)]
        if o != "matched": return o, j
        return ("same" if fp(self.v1.content(type_, i)) == fp(self.v2.content(type_, j)) else "changed"), j

    def candidates(self, i):
        """Unmatched S2 nodes with the same node content as an absent S1 node: reported, never chosen."""
        taken = {j for (t, _), (o, j) in self.out.items() if t == "node" and o == "matched"}
        mine = fp(self.v1.node_content(i))
        return sorted(j for j in self.v2.nodes if j not in taken and fp(self.v2.node_content(j)) == mine)

    def classify(self, items, compare=True):
        """Reasons for a keep scope: absent, ambiguous or changed items, one reason each. When the target itself is
        missing nothing is compared, but the scope is still classified (RULES.md §4.1)."""
        reasons = set()
        for t, i in items:
            o, _ = self.outcome(t, i)
            if o == "absent": reasons.add(("scope-item-absent", i))
            elif o in ("ambiguous", "unkeyed"): reasons.add(("scope-item-ambiguous", i))
            elif o == "changed" and compare: reasons.add(("evidence-changed", i))
        return reasons

    def nodes_by_hop(self, nodes, compare=True):
        """Assessment and plan scope (RULES.md §4.4–§4.5): each node is compared by its whole oneHop fingerprint."""
        reasons = set()
        for n in nodes:
            o, j = self.out[("node", n)]
            if o == "absent": reasons.add(("scope-item-absent", n))
            elif o == "ambiguous": reasons.add(("scope-item-ambiguous", n))
            elif compare and fp(self.v1.hop(n)) != fp(self.v2.hop(j)): reasons.add(("evidence-changed", n))
        return reasons

def _globals(s1, p1, s2, p2):
    ctx = lambda s: fp(_sorted(s["body"]["context"]))
    return {"profileChanged": p1["digest"] != p2["digest"], "contextChanged": ctx(s1) != ctx(s2),
            "captureChanged": s1["body"]["coverage"]["capture"] != s2["body"]["coverage"]["capture"]}


def _global_reasons(g, capture):
    r = set()
    if g["profileChanged"]: r.add(("profile-changed", "profile"))
    if g["contextChanged"]: r.add(("context-changed", "context"))
    if capture and g["captureChanged"]: r.add(("capture-changed", "capture"))
    return r


def _record(doc, verdict, target, reasons, candidates=()):
    return {"document": ii._pin(doc), "verdict": verdict, "target": target,
            "reasons": [{"code": c, "ref": r} for c, r in sorted(reasons)], "candidates": sorted(candidates)}


def _closure_items(v, result):
    return [x for n in result["nodeIds"] for x in v.hop_items(n)] + [("edge", e) for e in result["edgeIds"]]


def _decision_verdict(d, m, g):
    v1, v2 = m.v1, m.v2; t = d["body"]["target"]; type_, i = t["type"], t["id"]
    o, j = m.out[(type_, i)]; found = o == "matched"
    target = {"type": type_, "fromId": i, "toId": j}
    if type_ == "claim": items = v1.claim_scope(i)
    elif type_ == "edge": items = [("edge", i)]
    elif type_ == "issue":
        u = v1.issues[i]; items = [("issue", i), ("node", u["nodeId"]) if "nodeId" in u else ("edge", u["edgeId"])]
    else: items = v1.hop_items(i)
    reasons = m.classify([x for x in items if x != (type_, i)] + ([(type_, i)] if found else []), found) | _global_reasons(g, False)
    if type_ == "node" and d["body"]["evidenceBasis"] == "verified-by-virtual-case":
        view1, r1 = v1.closure_view(i, members=False)
        reasons |= m.classify([x for x in _closure_items(v1, r1) if x != ("node", i)], found)
        if found:
            view2, r2 = v2.closure_view(j, members=False)
            if view1 != view2 or {v1.key[x] for x in r1["nodeIds"]} != {v2.key[x] for x in r2["nodeIds"]}: reasons.add(("closure-changed", i))
    if o == "unkeyed": return _record(d, "orphaned", target, reasons | {("target-unkeyed", i)})
    if o == "absent": return _record(d, "orphaned", target, reasons | {("target-absent", i)}, m.candidates(i) if type_ == "node" else ())
    if o == "ambiguous": return _record(d, "needs-mapping", target, reasons | {("target-ambiguous", i)})
    if any(c == "scope-item-ambiguous" for c, _ in reasons): verdict = "needs-mapping"
    elif reasons: verdict = "re-review"
    else: verdict = "carried"
    return _record(d, verdict, target, reasons)


def _assessment_verdict(a, m, g, decision_ok):
    v1, v2 = m.v1, m.v2; x = a["body"]["endpoint"]["nodeId"]; o, j = m.out[("node", x)]; found = o == "matched"
    target = {"type": "node", "fromId": x, "toId": j}
    view1, r1 = v1.closure_view(x, members=False)
    reasons = (m.nodes_by_hop([n for n in r1["nodeIds"] if n != x or found], found)
               | m.classify([("edge", e) for e in r1["edgeIds"]], found) | _global_reasons(g, True)
               | {("decision-not-carried", r["id"]) for r in a["body"].get("decisionRefs", []) if not decision_ok(r["id"])})
    if o == "absent": return _record(a, "orphaned", target, reasons | {("target-absent", x)}, m.candidates(x))
    if o == "ambiguous": return _record(a, "needs-mapping", target, reasons | {("target-ambiguous", x)})
    view2, r2 = v2.closure_view(j, members=False)
    mine = {v1.key[n] for n in r1["nodeIds"]}
    for n in r2["nodeIds"]:
        if v2.key[n] not in mine and sum(1 for k in v2.key.values() if k == v2.key[n]) > 1: reasons.add(("scope-item-ambiguous", n))
    if view1 != view2 or mine != {v2.key[n] for n in r2["nodeIds"]}: reasons.add(("closure-changed", x))
    if any(c == "scope-item-ambiguous" for c, _ in reasons): return _record(a, "needs-mapping", target, reasons)
    return _record(a, "stale" if reasons else "reusable", target, reasons)


def _plan_verdict(c, m, g, assessments, decision_ok, workspace):
    b = c["body"]; target = {"type": "assessment", "fromId": b["assessmentRef"]["id"], "toId": None}
    av = assessments[b["assessmentRef"]["id"]]["verdict"]
    reasons = (_global_reasons(g, True) | m.nodes_by_hop([mp["nativeNodeId"] for mp in b["mappings"]])
               | {("decision-not-carried", r["id"]) for r in b.get("decisionRefs", []) if not decision_ok(r["id"])})
    if av != "reusable": reasons.add(("assessment-not-reusable", b["assessmentRef"]["id"]))
    if b["workspace"] != workspace: reasons.add(("workspace-changed", "workspace"))
    if av == "orphaned": return _record(c, "orphaned", target, reasons)
    if av == "needs-mapping" or any(code == "scope-item-ambiguous" for code, _ in reasons): return _record(c, "needs-mapping", target, reasons)
    return _record(c, "stale" if reasons else "reusable", target, reasons)


def _carry(d, s2, target_id, previous):
    copy = {k: v for k, v in d.items() if k not in ("digest", "envelope")}
    body = dict(d["body"]); copy["body"] = body
    copy["id"] = f"{d['id']}.carried.{s2['digest'][:12]}"; copy["version"] = "1.0.0"
    body["snapshotRef"] = ii._pin(s2); body["target"] = {"type": d["body"]["target"]["type"], "id": target_id}
    body["previousDecisionDigest"] = previous
    body["evidenceRefs"] = list(d["body"]["evidenceRefs"]) + [f"carried-from:review-decision:{d['id']}@{d['digest']}"]
    copy["digest"] = ii.digest(copy)
    return copy


def _sigma(mappings):
    return {(x["from"]["namespace"], x["from"]["nativeId"]): (x["to"]["namespace"], x["to"]["nativeId"]) for x in mappings}


def transfer(s1, b1, p1, s2, b2, p2, d1, a1, c1, declaration):
    """RULES.md §1. Returns (body, carried decisions). Nothing given is modified."""
    v1, v2 = View(s1, p1, _sigma(declaration["mappings"])), View(s2, p2)
    m, g = Match(v1, v2), _globals(s1, p1, s2, p2)
    last = {}
    for d in d1: last[(d["body"]["target"]["type"], d["body"]["target"]["id"])] = d
    heads = {d["id"] for d in last.values()}
    superseded = [{"decision": ii._pin(d), "supersededBy": ii._pin(last[(d["body"]["target"]["type"], d["body"]["target"]["id"])])}
                  for d in d1 if d["id"] not in heads]
    decisions = {d["id"]: _decision_verdict(d, m, g) for d in d1 if d["id"] in heads}
    ok = lambda i: i in decisions and decisions[i]["verdict"] == "carried"
    assessments = {a["id"]: _assessment_verdict(a, m, g, ok) for a in a1}
    plans = {c["id"]: _plan_verdict(c, m, g, assessments, ok, declaration["workspace"]) for c in c1}
    copies, carried, previous = [], [], None
    for d in d1:
        if d["id"] in decisions and decisions[d["id"]]["verdict"] == "carried":
            c = _carry(d, s2, decisions[d["id"]]["target"]["toId"], previous); previous = c["digest"]
            copies.append(c); carried.append({"from": ii._pin(d), "to": ii._pin(c)})
    correspondence = []
    for (t, i) in sorted(m.out):
        o, j = m.outcome(t, i)
        correspondence.append({"type": t, "fromId": i, "toId": j, "outcome": "absent" if o == "unkeyed" else o,
                               "candidates": m.candidates(i) if t == "node" and o == "absent" else []})
    side = lambda s, b, p: {"snapshot": ii._pin(s), "bundle": ii._pin(b), "profile": ii._pin(p), "artifactPins": s["body"]["inputManifest"]}
    verdicts = sorted([*decisions.values(), *assessments.values(), *plans.values()],
                      key=lambda r: (r["document"]["kind"], r["document"]["id"]))
    body = {"identityRule": RULE, "snapshotContractVersion": s1["contractVersion"],
            "from": side(s1, b1, p1), "to": side(s2, b2, p2),
            "sourceContinuity": declaration["sourceContinuity"], "workspace": declaration["workspace"],
            "mappings": declaration["mappings"], "retired": declaration["retired"], "globals": g,
            "correspondence": correspondence, "fromDecisionChainHead": ii._pin(d1[-1]) if d1 else None,
            "superseded": superseded, "verdicts": verdicts, "carried": carried}
    return body, copies


def document(id_, body, version="1.0.0"):
    doc = {"kind": "review-transfer", "contractVersion": "2.1.0", "id": id_, "version": version, "body": body}
    doc["digest"] = ii.digest(doc)
    return doc


def _keys(snapshot): return [(n["namespace"], n["nativeId"]) for n in snapshot["body"]["nativeNodes"]]


def _first_difference(recorded, computed, name):
    if recorded == computed: return
    if isinstance(recorded, list) and isinstance(computed, list):
        for a, b in zip(recorded, computed):
            if a != b: raise ii.Violation(f"transfer.{name}-mismatch", ii.jcs(a)[:200])
    raise ii.Violation(f"transfer.{name}-mismatch", name)


def check_transfer(t, s1, b1, p1, s2, b2, p2, d1, a1, c1, d2):
    """RULES.md §6: the recorded transfer is what the rules compute, and the carried copies head S2's chain."""
    ii.check(t); b = t["body"]
    if s1["contractVersion"] != s2["contractVersion"]: raise ii.Violation("transfer.contract-version-mixed", f"{s1['contractVersion']} and {s2['contractVersion']}")
    for side, (s, bu, pr) in (("from", (s1, b1, p1)), ("to", (s2, b2, p2))):
        ii.check_pinned(s, bu, pr)
        if [b[side]["snapshot"], b[side]["bundle"], b[side]["profile"]] != [ii._pin(s), ii._pin(bu), ii._pin(pr)]:
            raise ii.Violation("transfer.snapshot-mismatch", side)
        if b[side]["artifactPins"] != s["body"]["inputManifest"]: raise ii.Violation("transfer.artifact-pins-mismatch", side)
    if b["snapshotContractVersion"] != s1["contractVersion"]: raise ii.Violation("transfer.contract-version-mixed", b["snapshotContractVersion"])
    if b["sourceContinuity"]["evidenceBasis"] != "declared-by-reviewer": raise ii.Violation("transfer.continuity-missing")
    k1, k2 = _keys(s1), _keys(s2); froms, tos = set(), set()
    for x in b["mappings"]:
        f, to = (x["from"]["namespace"], x["from"]["nativeId"]), (x["to"]["namespace"], x["to"]["nativeId"])
        if x["evidenceBasis"] != "declared-by-reviewer": raise ii.Violation("transfer.mapping-evidence-not-owned", f[1])
        if f not in k1: raise ii.Violation("transfer.mapping-source-missing", f[1])
        if to not in k2: raise ii.Violation("transfer.mapping-target-missing", to[1])
        if k2.count(to) > 1: raise ii.Violation("transfer.mapping-target-ambiguous", to[1])
        if f in froms or to in tos: raise ii.Violation("transfer.mapping-conflict", f[1])
        froms.add(f); tos.add(to)
    for x in b["retired"]:
        if (x["key"]["namespace"], x["key"]["nativeId"]) in k2: raise ii.Violation("transfer.retired-key-present", x["key"]["nativeId"])
    if c1 and b["workspace"] is None: raise ii.Violation("transfer.workspace-missing")
    try: ii.check_decisions(d1, s1)
    except ii.Violation as e: raise ii.Violation("transfer.decision-chain-invalid", str(e))
    if b["fromDecisionChainHead"] != (ii._pin(d1[-1]) if d1 else None): raise ii.Violation("transfer.decision-chain-invalid", "chain head")
    try:
        assessments = {a["id"]: a for a in a1}
        for a in a1: ii.check_assessment(a, s1, p1, d1)
        for c in c1: ii.check_plan(c, assessments[c["body"]["assessmentRef"]["id"]], s1, p1, d1)
    except (ii.Violation, KeyError) as e: raise ii.Violation("transfer.input-document-invalid", str(e))
    declaration = {k: b[k] for k in ("sourceContinuity", "mappings", "retired", "workspace")}
    computed, copies = transfer(s1, b1, p1, s2, b2, p2, d1, a1, c1, declaration)
    for field, name in (("globals", "globals"), ("correspondence", "correspondence"), ("superseded", "superseded"), ("verdicts", "verdict")):
        _first_difference(b[field], computed[field], name)
    by_id, superseded = {d["id"]: d for d in d1}, {x["decision"]["id"] for x in b["superseded"]}
    verdict = {r["document"]["id"]: r for r in b["verdicts"]}
    for x in b["carried"]:
        if x["from"]["id"] not in by_id or x["from"] != ii._pin(by_id[x["from"]["id"]]): raise ii.Violation("transfer.carried-source-missing", x["from"]["id"])
        if x["from"]["id"] in superseded: raise ii.Violation("transfer.carried-source-superseded", x["from"]["id"])
        if verdict[x["from"]["id"]]["verdict"] != "carried": raise ii.Violation("transfer.carried-verdict-not-carried", x["from"]["id"])
    listed = [x["from"]["id"] for x in b["carried"]]
    for r in b["verdicts"]:
        if r["verdict"] == "carried" and r["document"]["id"] not in listed: raise ii.Violation("transfer.carried-verdict-not-carried", r["document"]["id"])
    pins = [ii._pin(d) for d in d2]
    for n, (x, want) in enumerate(zip(b["carried"], copies)):
        if x["to"] not in pins: raise ii.Violation("transfer.carried-copy-missing", x["to"]["id"])
        got = d2[n]
        if ii._pin(got) != x["to"]: raise ii.Violation("transfer.carried-copy-order", x["to"]["id"])
        refs, wanted = got["body"].get("evidenceRefs", []), want["body"]["evidenceRefs"]
        if not refs or refs[-1] != wanted[-1]: raise ii.Violation("transfer.carried-evidence-ref-missing", got["id"])
        if {k: v for k, v in got.items() if k != "envelope"} != want: raise ii.Violation("transfer.carried-copy-differs", got["id"])
    if len(b["carried"]) != len(copies): raise ii.Violation("transfer.carried-verdict-not-carried", "carried list")
    ii.check_decisions(d2, s2)
