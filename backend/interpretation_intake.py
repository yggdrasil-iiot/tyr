"""P4-F A2: receive Mimir interpretation snapshots (contract 1.0.0 or 1.1.0) and check Tyr's editor documents (2.0.0).

Tyr never parses a vendor file. It checks what Mimir published — schema, digest, internal references and pins
against the bundle/profile/request it names — and its own review, assessment and plan documents against that
snapshot. Nothing here writes: storage (sidecar) is P4-F B. Documents checked together must share one snapshot
contract version; a mixed set is refused, not reconciled.

Digest (both contracts): SHA-256 over the UTF-8 bytes of the RFC 8785 (JCS) form of the document without its
top-level "digest" and "envelope". Numbers are integers within +/-(2**53-1); a decimal travels as a string.
This is Tyr's own implementation of that rule; it shares no code with Mimir's.
"""
import hashlib, json
from functools import lru_cache
from pathlib import Path
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
import interpretation_closure

R = Path(__file__).resolve().parents[1]
MIMIR = R/"vendor-contracts"/"mimir"/"interpretation"
EDITOR = R/"editor-contracts"/"2.0.0"
EDITOR_PREFIX = "urn:tyr:editor:2.0.0:"
SNAPSHOT_KINDS = {"source-bundle", "interpretation-profile", "interpretation-snapshot", "interpret-request", "interpret-result"}
EDITOR_KINDS = {"review-decision", "endpoint-assessment", "conversion-plan"}
DIGESTED = {"source-bundle", "interpretation-profile", "interpretation-snapshot"} | EDITOR_KINDS
SNAPSHOT_VERSIONS = ("1.0.0", "1.1.0")
VERSIONS = {**{k: SNAPSHOT_VERSIONS for k in SNAPSHOT_KINDS}, **{k: ("2.0.0",) for k in EDITOR_KINDS}}
MIMIR_EVIDENCE = {"observed-in-artifact", "derived-by-rule"}
TYR_EVIDENCE = {"declared-by-reviewer", "verified-by-virtual-case"}
MAX_SAFE = 2**53 - 1


class Violation(Exception):
    def __init__(self, code, at=""):
        super().__init__(code + (" at " + at if at else "")); self.code = code


def _pairs(items):
    d = {}
    for k, v in items:
        if k in d: raise Violation("json.duplicate-key", k)
        d[k] = v
    return d


class _Decimal(str):
    """A non-integer number token, kept so the number rule can reject it with a location."""


def parse(text):
    try:
        return json.loads(text, object_pairs_hook=_pairs, parse_float=_Decimal,
                          parse_constant=lambda c: (_ for _ in ()).throw(Violation("jcs.non-integer-number", c)))
    except json.JSONDecodeError as e:
        raise Violation("json.invalid", str(e))


def load(path): return parse(Path(path).read_bytes().decode("utf-8"))


_ESC = {'"': '\\"', "\\": "\\\\", "\b": "\\b", "\f": "\\f", "\n": "\\n", "\r": "\\r", "\t": "\\t"}


def _string(s, at):
    out = []
    for ch in s:
        c = ord(ch)
        if ch in _ESC: out.append(_ESC[ch])
        elif c < 0x20: out.append("\\u%04x" % c)
        elif 0xD800 <= c <= 0xDFFF: raise Violation("jcs.lone-surrogate", at)
        else: out.append(ch)
    return '"' + "".join(out) + '"'


def jcs(v, at=""):
    if v is None: return "null"
    if v is True: return "true"
    if v is False: return "false"
    if isinstance(v, (_Decimal, float)): raise Violation("jcs.non-integer-number", at)
    if isinstance(v, int):
        if abs(v) > MAX_SAFE: raise Violation("jcs.unsafe-integer", at)
        return str(v)
    if isinstance(v, str): return _string(v, at)
    if isinstance(v, list): return "[" + ",".join(jcs(x, f"{at}/{i}") for i, x in enumerate(v)) + "]"
    if isinstance(v, dict):
        keys = sorted(v, key=lambda k: k.encode("utf-16-be", "surrogatepass"))
        return "{" + ",".join(_string(k, at) + ":" + jcs(v[k], f"{at}/{k}") for k in keys) + "}"
    raise Violation("jcs.unsupported-node", at)


def digest(doc):
    return hashlib.sha256(jcs({k: v for k, v in doc.items() if k not in ("digest", "envelope")}).encode("utf-8")).hexdigest()


def _no_remote(uri): raise ValueError("External schema retrieval prohibited: " + uri)


@lru_cache(maxsize=1)
def _registry():
    reg = Registry(retrieve=_no_remote)
    for p in [p for v in SNAPSHOT_VERSIONS for p in (MIMIR/v).glob("*.schema.json")] + list(EDITOR.glob("*.schema.json")):
        s = json.loads(p.read_text(encoding="utf-8")); Draft202012Validator.check_schema(s)
        reg = reg.with_resource(s["$id"], Resource.from_contents(s))
    return reg


@lru_cache(maxsize=32)
def _validator(kind, version):
    prefix = EDITOR_PREFIX if kind in EDITOR_KINDS else f"urn:mimir:interpretation:{version}:"
    return Draft202012Validator(_registry().contents(prefix + kind + ".schema.json"), registry=_registry())


def _schema(doc, kind):
    # A decimal token is a str subclass; the number rule has already rejected it before this point.
    errors = sorted(_validator(kind, doc["contractVersion"]).iter_errors(doc), key=lambda e: list(map(str, e.path)))
    if errors: raise Violation("contract.schema", errors[0].message)


def check(doc):
    """One document on its own: kind, contract version, number rules, evidence ownership, schema, digest, internal references."""
    if not isinstance(doc, dict): raise Violation("contract.not-an-object")
    kind = doc.get("kind")
    if kind not in VERSIONS: raise Violation("contract.kind-unknown", str(kind))
    if doc.get("contractVersion") not in VERSIONS[kind]: raise Violation("contract.version-unsupported", str(doc.get("contractVersion")))
    jcs(doc)
    if kind == "interpretation-snapshot":
        for c in doc.get("body", {}).get("claims", []):
            if c.get("evidenceBasis") in TYR_EVIDENCE: raise Violation("snapshot.evidence-basis-not-owned", str(c.get("claimId")))
    if kind == "review-decision" and doc.get("body", {}).get("evidenceBasis") in MIMIR_EVIDENCE:
        raise Violation("editor.evidence-basis-not-owned", str(doc.get("id")))
    _schema(doc, kind)
    if kind in DIGESTED and digest(doc) != doc["digest"]: raise Violation("digest.mismatch", f"{kind}:{doc['id']}")
    if kind == "source-bundle": _bundle(doc["body"])
    if kind == "interpretation-snapshot": _snapshot(doc["body"], doc["contractVersion"])


def _same_version(first, *others):
    for o in others:
        if o["contractVersion"] != first["contractVersion"]:
            raise Violation("contract.version-mixed", f"{first['contractVersion']} and {o['contractVersion']}")


def _ref(ref, doc, code):
    if [ref.get(k) for k in ("kind", "id", "version", "digest")] != [doc.get(k) for k in ("kind", "id", "version", "digest")]:
        raise Violation(code, str(ref.get("id")))


def _pins(pins, known):
    for p in pins:
        if p["artifactId"] not in known: raise Violation("pin.artifact-unknown", p["artifactId"])
        if known[p["artifactId"]] != p["sha256"]: raise Violation("pin.artifact-mismatch", p["artifactId"])


def _artifacts(bundle): return {a["artifactId"]: a["sha256"] for a in bundle["body"]["artifacts"]}


def check_pinned(snapshot, bundle, profile):
    """A snapshot against the bundle and profile it names. This is the SI19 receive check: no vendor file is read."""
    for d in (snapshot, bundle, profile): check(d)
    _same_version(snapshot, bundle, profile)
    b = snapshot["body"]; _ref(b["bundleRef"], bundle, "pin.bundle-mismatch"); _ref(b["profileRef"], profile, "pin.profile-mismatch")
    known = _artifacts(bundle); _pins(b["inputManifest"], known)
    if b["coverage"]["artifactsRead"] + b["coverage"]["artifactsSkipped"] > len(known):
        raise Violation("snapshot.coverage-mismatch", "more artifacts counted than the bundle holds")
    rules = {(r["ruleId"], r["version"]) for r in profile["body"]["rules"]}
    for c in b["claims"]:
        if "rule" in c and (c["rule"]["ruleId"], c["rule"]["version"]) not in rules: raise Violation("pin.rule-unknown", c["claimId"])


def check_request(request, bundle, profile):
    for d in (request, bundle, profile): check(d)
    _same_version(request, bundle, profile)
    _ref(request["bundleRef"], bundle, "pin.bundle-mismatch"); _ref(request["profileRef"], profile, "pin.profile-mismatch")
    _pins(request["artifactPins"], _artifacts(bundle))


def check_result(result, request, snapshot):
    check(result); check(request); _same_version(result, request)
    if result["requestId"] != request["requestId"]: raise Violation("result.request-mismatch", result["requestId"])
    if "snapshotRef" not in result: return
    check(snapshot); _same_version(result, snapshot); _ref(result["snapshotRef"], snapshot, "pin.snapshot-mismatch")
    b = snapshot["body"]
    if b["bundleRef"] != request["bundleRef"]: raise Violation("pin.bundle-mismatch", "snapshot and request name different bundles")
    if b["profileRef"] != request["profileRef"]: raise Violation("pin.profile-mismatch", "snapshot and request name different profiles")
    _pins(b["inputManifest"], {p["artifactId"]: p["sha256"] for p in request["artifactPins"]})


def _bundle(body):
    ids = set()
    for a in body["artifacts"]:
        if a["artifactId"] in ids: raise Violation("bundle.artifact-duplicate", a["artifactId"])
        ids.add(a["artifactId"])
    for a in body["artifacts"]:
        r = a.get("redaction")
        if r and (r["derivedFrom"] not in ids or r["derivedFrom"] == a["artifactId"]): raise Violation("bundle.redaction-source-missing", a["artifactId"])
    for c in body["productClaims"]:
        for i in c.get("artifactIds", []):
            if i not in ids: raise Violation("bundle.claim-artifact-missing", i)


def _unique(items, field):
    seen = set()
    for x in items:
        if x[field] in seen: raise Violation("snapshot.id-duplicate", f"{field}:{x[field]}")
        seen.add(x[field])
    return seen


def _snapshot(b, version):
    pinned = set()
    for p in b["inputManifest"]:
        if p["artifactId"] in pinned: raise Violation("snapshot.id-duplicate", "inputManifest:" + p["artifactId"])
        pinned.add(p["artifactId"])
    if b["coverage"]["artifactsRead"] != len(pinned): raise Violation("snapshot.coverage-mismatch", "artifactsRead differs from inputManifest")
    nodes = _unique(b["nativeNodes"], "nodeId"); edges = _unique(b["referenceEdges"], "edgeId")
    claims = _unique(b["claims"], "claimId"); _unique(b["unresolved"], "issueId")

    def node(i):
        if i not in nodes: raise Violation("snapshot.node-missing", i)

    def loc(l):
        if l["artifactId"] not in pinned: raise Violation("snapshot.locator-artifact-unpinned", l["artifactId"])
    for n in b["nativeNodes"]:
        loc(n["locator"])
        if "payload" in n: loc(n["payload"])
    for e in b["referenceEdges"]:
        node(e["owner"]["nodeId"])
        if "targetNodeId" in e: node(e["targetNodeId"])
        for c in e.get("candidates", []): node(c)
    for c in b["claims"]:
        node(c["subject"]["nodeId"])
        for l in c["locators"]: loc(l)
        for d in c.get("dependsOn", {}).get("claimIds", []):
            if d not in claims: raise Violation("snapshot.claim-missing", d)
        for d in c.get("dependsOn", {}).get("edgeIds", []):
            if d not in edges: raise Violation("snapshot.edge-missing", d)
    for u in b["unresolved"]:
        if "nodeId" in u: node(u["nodeId"])
        if "edgeId" in u and u["edgeId"] not in edges: raise Violation("snapshot.edge-missing", u["edgeId"])
        if "locator" in u: loc(u["locator"])
        for a in u["affectedNodeIds"]: node(a)
    for d in b["diagnostics"]:
        if "locator" in d: loc(d["locator"])
    if version != "1.0.0": _state(b)


def _state(b):
    """1.1.0: a known state rests on an asserted claim about that node's "state" with the same value; an unknown
    state comes with a behavior-unknown item on that node. The interpreter does not guess, and neither does Tyr."""
    claims = {c["claimId"]: c for c in b["claims"]}
    behavior_unknown = {u["nodeId"] for u in b["unresolved"] if u["code"] == "behavior-unknown" and "nodeId" in u}
    for n in b["nativeNodes"]:
        if "state" not in n: continue
        if n["state"] == "unknown":
            if n["nodeId"] not in behavior_unknown: raise Violation("snapshot.state-unknown-unexplained", n["nodeId"])
            continue
        c = claims.get(n["stateClaimId"])
        if c is None: raise Violation("snapshot.claim-missing", n["stateClaimId"])
        if (c["subject"]["nodeId"], c["subject"]["field"], c["value"], c["status"]) != (n["nodeId"], "state", n["state"], "asserted"):
            raise Violation("snapshot.state-claim-mismatch", n["nodeId"])


# ---- Tyr editor documents (2.0.0) -------------------------------------------------------------------------

def _pin(doc): return {k: doc[k] for k in ("kind", "id", "version", "digest")}


def _targets(snapshot):
    b = snapshot["body"]
    return {"node": {n["nodeId"] for n in b["nativeNodes"]}, "edge": {e["edgeId"] for e in b["referenceEdges"]},
            "claim": {c["claimId"] for c in b["claims"]}, "issue": {u["issueId"] for u in b["unresolved"]}}


def check_decisions(decisions, snapshot):
    """Review decisions about one snapshot, oldest first: each names an existing target and links to the one before it."""
    check(snapshot); targets = _targets(snapshot); previous = None; seen = set()
    for d in decisions:
        check(d); b = d["body"]
        _ref(b["snapshotRef"], snapshot, "pin.snapshot-mismatch")
        if b["target"]["id"] not in targets[b["target"]["type"]]: raise Violation("editor.target-missing", b["target"]["id"])
        if b["previousDecisionDigest"] != previous or d["digest"] in seen: raise Violation("editor.chain-broken", d["id"])
        previous = d["digest"]; seen.add(d["digest"])


def check_assessment(assessment, snapshot, profile, decisions=()):
    """The declared closure must be the computed one (§5); a complete claim over an incomplete closure is an over-claim."""
    check(assessment); check(snapshot); check(profile); b = assessment["body"]
    _ref(b["snapshotRef"], snapshot, "pin.snapshot-mismatch")
    _ref(snapshot["body"]["profileRef"], profile, "pin.profile-mismatch")
    t = _targets(snapshot)
    if b["endpoint"]["nodeId"] not in t["node"]: raise Violation("editor.target-missing", b["endpoint"]["nodeId"])
    for n in b["closure"]["nodeIds"]:
        if n not in t["node"]: raise Violation("editor.target-missing", n)
    for e in b["closure"]["edgeIds"]:
        if e not in t["edge"]: raise Violation("editor.target-missing", e)
    if b["endpoint"]["nodeId"] not in b["closure"]["nodeIds"]: raise Violation("editor.closure-without-endpoint", b["endpoint"]["nodeId"])
    computed = interpretation_closure.closure(snapshot, b["endpoint"]["nodeId"], profile["body"]["limits"]["maxReferenceDepth"])
    if b["closure"]["completeness"] == "complete" and computed["completeness"] != "complete":
        raise Violation("editor.closure-overclaimed", ",".join(r["ref"] for r in computed["reasons"]))
    if (sorted(b["closure"]["nodeIds"]), sorted(b["closure"]["edgeIds"]), b["closure"]["completeness"]) != \
            (computed["nodeIds"], computed["edgeIds"], computed["completeness"]):
        raise Violation("editor.closure-mismatch", b["endpoint"]["nodeId"])
    axes = b["axes"]
    if axes["structure"]["status"] == "complete" and b["closure"]["completeness"] != "complete":
        raise Violation("editor.axis-inconsistent", "structure complete over an incomplete closure")
    if axes["capture"]["status"] == "declared-complete" and snapshot["body"]["coverage"]["capture"] != "declared-complete":
        raise Violation("editor.axis-inconsistent", "capture claimed beyond the snapshot's coverage")
    known = {d["digest"]: d for d in decisions}
    for ref in b.get("decisionRefs", []):
        if ref["digest"] not in known: raise Violation("pin.decision-unknown", ref["id"])
        _ref(ref, known[ref["digest"]], "pin.decision-mismatch")


def check_plan(plan, assessment, snapshot, profile, decisions=()):
    check(plan); check_assessment(assessment, snapshot, profile, decisions); b = plan["body"]
    _ref(b["assessmentRef"], assessment, "pin.assessment-mismatch")
    _ref(b["snapshotRef"], snapshot, "pin.snapshot-mismatch")
    if b["profileRef"] != snapshot["body"]["profileRef"]: raise Violation("pin.profile-mismatch", b["profileRef"]["id"])
    known = {d["digest"]: d for d in decisions}
    for ref in b.get("decisionRefs", []):
        if ref["digest"] not in known: raise Violation("pin.decision-unknown", ref["id"])
        _ref(ref, known[ref["digest"]], "pin.decision-mismatch")
    nodes = _targets(snapshot)["node"]
    for m in b["mappings"]:
        if m["nativeNodeId"] not in nodes: raise Violation("editor.target-missing", m["nativeNodeId"])
    if b["status"] == "candidate":
        a = assessment["body"]; axes = a["axes"]
        ready = (a["closure"]["completeness"] == "complete" and axes["structure"]["status"] == "complete"
                 and axes["representation"]["status"] == "representable" and axes["meaning"]["status"] == "reviewer-confirmed"
                 and axes["virtualEquivalence"]["status"] == "passed-within-scope" and not b["losses"]
                 and not any(x["blockers"] for x in axes.values()))
        if not ready: raise Violation("editor.plan-overclaimed", plan["id"])
        computed = interpretation_closure.closure(snapshot, a["endpoint"]["nodeId"], profile["body"]["limits"]["maxReferenceDepth"])
        blockers = interpretation_closure.conversion_blockers(computed)
        if blockers: raise Violation("editor.plan-blocked", ",".join(f"{k}:{r}" for k, r in blockers))
