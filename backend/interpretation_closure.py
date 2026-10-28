"""P4-F §5: the closure of one endpoint in a Mimir interpretation snapshot (contract 1.0.0 or 1.1.0).

Breadth-first over evaluation edges to the profile's maxReferenceDepth; contains edges are structural and
never followed for evaluation. A closure is complete only when no reason says otherwise, and a leaf counts
as explained only by an asserted claim: having no unresolved edge is not evidence. The capture scope is
reported beside completeness, never folded into it.

Snapshot 1.0.0 has no access kind and no state marker: every evaluation edge is followed, and an opaque node
with a behavior-unknown issue stands in for a stateful one. Snapshot 1.1.0 says both. A read or event edge is
followed (event edges are also listed); a write edge is the endpoint acting on something, not an input, so it is
recorded with its target and never followed; an unknown access is a reason and is not followed. Node state is
read as declared. Writes and state do not make a closure incomplete; they block a conversion plan (§3, layer 3).
"""
from collections import deque

EVALUATION = {"input", "reference", "inherits", "overrides", "policy", "external"}
EDGE_REASON = {"missing": "edge-missing", "ambiguous": "edge-ambiguous",
               "external-required": "edge-external-required", "unsupported": "edge-unsupported"}


def _cycles(nodes, adjacency):
    """Strongly connected components with more than one node or a self-loop (iterative Tarjan), as sorted id strings."""
    index, low, on, stack, out, counter = {}, {}, set(), [], [], [0]
    for root in sorted(nodes):
        if root in index: continue
        work = [(root, iter(sorted(adjacency.get(root, ()))))]
        index[root] = low[root] = counter[0]; counter[0] += 1; stack.append(root); on.add(root)
        while work:
            v, it = work[-1]
            w = next(it, None)
            if w is None:
                work.pop()
                if work: low[work[-1][0]] = min(low[work[-1][0]], low[v])
                if low[v] == index[v]:
                    comp = []
                    while True:
                        x = stack.pop(); on.discard(x); comp.append(x)
                        if x == v: break
                    if len(comp) > 1 or v in adjacency.get(v, ()): out.append(",".join(sorted(comp)))
                continue
            if w not in nodes: continue
            if w not in index:
                index[w] = low[w] = counter[0]; counter[0] += 1; stack.append(w); on.add(w)
                work.append((w, iter(sorted(adjacency.get(w, ())))))
            elif w in on:
                low[v] = min(low[v], index[w])
    return sorted(out)


def closure(snapshot, endpoint, max_depth):
    b = snapshot["body"]; marked = snapshot["contractVersion"] != "1.0.0"
    owned = {}
    for e in sorted(b["referenceEdges"], key=lambda e: e["edgeId"]):
        owned.setdefault(e["owner"]["nodeId"], []).append(e)
    if endpoint not in {n["nodeId"] for n in b["nativeNodes"]}: raise KeyError(endpoint)

    depth, edges, writes, reasons, queue = {endpoint: 0}, {}, {}, set(), deque([endpoint])
    while queue:
        v = queue.popleft()
        evaluation = [e for e in owned.get(v, []) if e["relation"] in EVALUATION]
        if depth[v] >= max_depth:
            if evaluation: reasons.add(("depth-limit", v))
            continue
        for e in evaluation:
            access = e.get("access", "read")
            if access == "write":
                writes[e["edgeId"]] = e; continue
            edges[e["edgeId"]] = e
            if access == "unknown":
                reasons.add(("access-unknown", e["edgeId"]))
                if e["resolution"] != "resolved": reasons.add((EDGE_REASON[e["resolution"]], e["edgeId"]))
                continue
            if e["resolution"] == "resolved":
                t = e["targetNodeId"]
                if t not in depth: depth[t] = depth[v] + 1; queue.append(t)
            else:
                reasons.add((EDGE_REASON[e["resolution"]], e["edgeId"]))
    nodes = set(depth)

    resolved = {}
    for e in edges.values():
        if e["resolution"] == "resolved" and e.get("access", "read") != "unknown": resolved.setdefault(e["owner"]["nodeId"], set()).add(e["targetNodeId"])
    for c in _cycles(nodes, resolved): reasons.add(("evaluation-cycle", c))

    counted = set()
    for u in b["unresolved"]:
        if u.get("nodeId") in nodes or u.get("edgeId") in edges or nodes & set(u["affectedNodeIds"]):
            reasons.add(("unresolved-issue", u["issueId"])); counted.add(u["issueId"])

    asserted = {c["subject"]["nodeId"] for c in b["claims"] if c["status"] == "asserted"}
    for n in nodes:
        if not any(e["relation"] in EVALUATION for e in owned.get(n, [])) and n not in asserted:
            reasons.add(("unexplained-leaf", n))

    if marked:
        state = {n["nodeId"]: n.get("state") for n in b["nativeNodes"]}
        stateful = {n for n in nodes if state[n] == "stateful"}
    else:
        kinds = {n["nodeId"]: n["kind"] for n in b["nativeNodes"]}
        stateful = {u["nodeId"] for u in b["unresolved"] if u["code"] == "behavior-unknown" and u.get("nodeId") in nodes and kinds[u["nodeId"]] == "opaque"}

    contains, seen, todo = {}, set(nodes), list(nodes)
    while todo:
        v = todo.pop()
        for e in owned.get(v, []):
            if e["relation"] == "contains" and e["resolution"] == "resolved":
                contains.setdefault(v, set()).add(e["targetNodeId"])
                if e["targetNodeId"] not in seen: seen.add(e["targetNodeId"]); todo.append(e["targetNodeId"])

    out = {"nodeIds": sorted(nodes), "edgeIds": sorted(edges), "completeness": "incomplete" if reasons else "complete",
           "reasons": [{"code": c, "ref": r} for c, r in sorted(reasons)], "captureScope": b["coverage"]["capture"],
           "statefulNodeIds": sorted(stateful), "structuralCycles": _cycles(seen, contains),
           "outsideUnresolved": len(b["unresolved"]) - len(counted)}
    if marked:
        out["eventEdgeIds"] = sorted(i for i, e in edges.items() if e["access"] == "event")
        out["writeTargets"] = [{"edgeId": i, "owner": e["owner"]["nodeId"], "targetText": e["targetText"], "resolution": e["resolution"],
                                **({"targetNodeId": e["targetNodeId"]} if "targetNodeId" in e else {})} for i, e in sorted(writes.items())]
        out["stateUnknownNodeIds"] = sorted(n for n in nodes if state[n] == "unknown")
    return out


def conversion_blockers(result):
    """What stops a conversion plan beyond completeness: a write is control, and state is preserved, not converted."""
    return ([("write", w["edgeId"]) for w in result.get("writeTargets", [])]
            + [("stateful", n) for n in result["statefulNodeIds"]] + [("state-unknown", n) for n in result.get("stateUnknownNodeIds", [])])
