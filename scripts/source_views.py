"""Bounded read-only source alias/bit views. Wire data only, no IO."""
import source_codecs
WIDTH={"Int16":16,"UInt16":16,"Int32":32,"UInt32":32,"Int64":64}
VERSION="2.10.0"
def index(rows):return {(d["id"],d["version"]):d for d in rows}
def chain(d,docs):
    out=[];seen=set()
    while True:
        key=(d["id"],d["version"])
        if key in seen:raise ValueError("view.cycle")
        if len(out)>=17:raise ValueError("view.depth")
        seen.add(key);out.append(d)
        if d.get("viewOf") is None:return out
        if d.get("schemaVersion")!=VERSION:raise ValueError("source.view-not-supported")
        ref=d["viewOf"];d=docs.get((ref["id"],ref["version"]))
        if d is None:raise ValueError("view.reference-missing")
def value_type(d,docs):
    rows=chain(d,docs)
    if any(s.get("view",{}).get("kind")=="bit" for s in rows):return "Boolean"
    root=rows[-1]
    return "Boolean" if root["access"].get("bitOffset") is not None else source_codecs.decoded_type(root)
def rules(d,docs):
    if d.get("viewOf") is None:return []
    try:rows=chain(d,docs)
    except (ValueError,KeyError,TypeError) as e:return [str(e) if isinstance(e,ValueError) else "view.invalid"]
    out=[]
    for child,parent in zip(rows,rows[1:]):
        if child.get("schemaVersion")!=VERSION or not child.get("view"):out.append("source.view-not-supported");continue
        if child.get("sourceKind")!="plc" or parent.get("sourceKind","plc")!="plc":out.append("view.plc-only")
        if child.get("accessMode")!="read" or parent.get("accessMode","read")=="write":out.append("view.readonly")
        for key in ("equipmentInstanceId","connectionProfileRef","accessProfileRef","access","rawRepresentation","inputStage","addressRadix"):
            if child[key]!=parent[key]:out.append("view.snapshot-mismatch")
        if parent["status"]!="ready":out.append("view.parent-not-ready")
        if child["view"]["kind"]=="alias":
            if child["unit"]!=parent["unit"]:out.append("view.unit")
        elif child["view"]["kind"]=="bit":
            typ=value_type(parent,docs)
            if typ not in WIDTH:out.append("view.integer-required")
            elif not 0<=child["view"]["bitIndex"]<WIDTH[typ]:out.append("view.bit-range")
            if child["unit"]!={"status":"not-applicable"}:out.append("view.unit")
        else:out.append("view.kind")
    root=rows[-1]
    if "fixedArray" in root or "codec" in root["rawRepresentation"] or root["access"].get("bitOffset") is not None or root["access"].get("addressUnit")=="bit":out.append("view.scalar-word-required")
    if root["rawRepresentation"]["valueType"] not in WIDTH:out.append("view.integer-required")
    return sorted(set(out))
def root_ids(state,ids):
    docs=index(r["definition"] for r in state["sources"])
    byid={d["id"]:d for d in docs.values()}
    return sorted({chain(byid[id],docs)[-1]["id"] for id in ids})
