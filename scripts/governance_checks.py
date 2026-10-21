"""Offline canonical governance harness; consumes file contracts only."""
import copy, struct, math
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path
import validate_contracts as vc

def documents(root):
    p=vc.load(root/"proposal.json")
    return {e["path"]:vc.load(vc.safe(root,e["path"])) for e in p["files"]}

def bindings(docs):
    index={(d["kind"],d["id"],d["version"]):d for d in docs.values()}
    rows=[]
    for d in docs.values():
        if d["kind"]!="mapping-set":continue
        ref=d["semanticDefinitionRef"]; sem=index[("semantic-definition",ref["id"],ref["version"])]
        for m in d["mappings"]:
            member=next(x for x in sem["members"] if x["memberId"]==m["targetMemberId"])
            r=m["sourceRef"];source=index[("source-definition",r["id"],r["version"])]
            rows.append({"mappingId":m["mappingId"],"equipmentInstanceId":d["equipmentInstanceId"],
                "semanticDefinitionRef":ref,"semanticId":member["semanticId"],"role":member["role"],"valueType":member["valueType"],
                "unit":member["unit"],"source":source,"mapping":m,"member":member})
    return rows

def meaning(row):
    return {k:row[k] for k in ("semanticId","role","valueType","unit")}

def conflicts(rows):
    seen={};out=[]
    for r in rows:
        key=r["semanticId"];signature=meaning(r)
        if key in seen and seen[key]!=signature:out.append("semantic.identity-conflict")
        seen[key]=signature
    return sorted(set(out))

def evaluate(row,sample):
    source=row["source"];raw=source["rawRepresentation"];typ=raw["valueType"]
    issues=[]
    if raw["mode"]=="typed": value=sample["typedValue"] if typ=="Boolean" else Decimal(str(sample["typedValue"]))
    else:
        data=bytes.fromhex(sample["bytesHex"])
        if len(data)!=vc.WIDTH[typ]:raise ValueError("sample.width")
        words=[data[i:i+2] for i in range(0,len(data),2)]
        if raw["wordOrder"]=="low-first":words.reverse()
        ordered=b"".join(w[::-1] if raw["byteOrder"]=="little" else w for w in words)
        fmt={"Int16":"h","UInt16":"H","Int32":"i","UInt32":"I","Int64":"q","Float32":"f","Float64":"d","Boolean":"?"}[typ]
        decoded=struct.unpack(">"+fmt,ordered)[0]
        if isinstance(decoded,float) and not math.isfinite(decoded):return None,["value.nonfinite"]
        value=Decimal(str(decoded))
    bit=source["access"].get("bitOffset")
    if bit is not None:value=bool(int(value)&(1<<bit))
    for t in row["mapping"]["transform"]:
        if t["op"]=="linear":value=value*Decimal(t["factor"])+Decimal(t["offset"])
        elif t["op"]=="unit-convert":
            factor,offset=vc.UNIT_CONVERSIONS[(t["from"],t["to"])]
            value=value*Decimal(factor)+Decimal(offset)
        elif t["op"]=="bit-select":value=bool(int(value)&(1<<t["index"]))
        elif t["op"]=="enum-map":
            matches=[e["value"] for e in t["entries"] if Decimal(e["raw"])==value]
            if not matches:return None,["value.enum-unknown"]
            value=matches[0]
        elif t["op"]=="cast":
            if t["to"]=="Int32":
                rounded=value.to_integral_value(rounding=ROUND_HALF_EVEN)
                if rounded!=value:
                    issues.append("loss.rounding")
                    if t["rounding"]=="exact":return None,issues+["value.inexact"]
                value=rounded
                if not -(2**31)<=value<2**31:return None,issues+["value.overflow"]
            elif t["to"]=="Double":
                f=float(value)
                if not math.isfinite(f):return None,issues+["value.overflow"]
                if Decimal.from_float(f)!=value:
                    issues.append("loss.precision")
                    if t["rounding"]=="exact":return None,issues+["value.inexact"]
                value=Decimal(str(f))
    bounds=row["member"]["range"]
    if bounds and isinstance(value,Decimal) and not Decimal(bounds["low"])<=value<=Decimal(bounds["high"]):
        issues.append("value.range")
    return str(value) if isinstance(value,Decimal) else value,issues

def project(rows):
    """Explicit legacy subset projection, not the actual Bifrost adapter."""
    docs=[];losses=[]
    for r in rows:
        m=r["member"]
        docs.append({"name":m["name"],"type":m["valueType"],"semanticId":m["semanticId"],"range":m["range"]})
        for field in ("source.access","source.rawRepresentation","source.equipmentInstanceId",
                      "mapping.transform","mapping.evidenceRefs","member.unit","member.role",
                      "source.inputStage","source.unit","source.connectionProfileRef","source.accessProfileRef",
                      "source.evidenceRefs","source.id","source.version","member.memberId","member.description",
                      "mapping.sourceRef","mapping.targetMemberId","mapping.outputUnit","mapping.invalidValuePolicy"):
            losses.append({"mappingId":r["mappingId"],"field":field,"ruleCode":"projection.field-loss"})
    return docs,losses

def changes(before,after):
    old={r["mappingId"]:r for r in bindings(before)}
    new={r["mappingId"]:r for r in bindings(after)}
    out=[]
    fields={"semanticId":"meaning","role":"meaning","unit":"meaning","valueType":"meaning",
            "member.range":"constraint","mapping.transform":"transform","mapping.invalidValuePolicy":"transform",
            "source.access":"access","source.rawRepresentation":"decode","source.inputStage":"decode",
            "source.connectionProfileRef":"context","source.equipmentInstanceId":"context",
            "source.accessProfileRef":"access","mapping.evidenceRefs":"evidence","source.evidenceRefs":"evidence",
            "member.name":"presentation","member.description":"presentation",
            "mapping.sourceRef":"reference","mapping.targetMemberId":"reference",
            "mapping.outputUnit":"meaning","semanticDefinitionRef":"reference"}
    def get(r,field):
        for part in field.split("."):r=r[part]
        return r
    for key in sorted(old.keys()|new.keys()):
        if key not in old or key not in new:
            out.append({"mappingId":key,"field":"binding","category":"binding","reviewRequired":True});continue
        for field,category in fields.items():
            if get(old[key],field)!=get(new[key],field):
                out.append({"mappingId":key,"field":field,"category":category,"reviewRequired":category!="presentation"})
    return out

def run():
    root=vc.ROOT/"fixtures/packages/motor";base=documents(root)
    fixture=vc.load(vc.ROOT/"fixtures/governance-cases.json")
    rows=bindings(base);results=[];outcomes=[]
    for sample in fixture["samples"]:
        row=next(r for r in rows if r["mappingId"]==sample["mappingId"])
        value,issues=evaluate(row,sample)
        ok=value is not None and Decimal(value)==Decimal(sample["expected"]) and issues==sample["issues"] and meaning(row)==fixture["expectedMeaning"]
        results.append({"id":"canonical:"+sample["mappingId"],"passed":ok})
        outcomes.append({"mappingId":row["mappingId"],"value":value,"issues":issues})
    results.append({"id":"canonical:four-way-convergence","passed":len({str(Decimal(x["value"])) for x in outcomes})==1 and len({r["source"]["access"]["kind"] for r in rows})==4})
    change_reports=[]
    for case in fixture["scenarios"]:
        revised=copy.deepcopy(base)
        for patch in case["mutations"]:vc.mutate(revised[patch["path"]],patch["pointer"],patch["value"])
        revised_rows=bindings(revised)
        diff=changes(base,revised)
        change_reports.append({"scenarioId":case["id"],"changes":diff})
        observed=sorted(set(x["category"] for x in diff))
        conflict=conflicts(rows+revised_rows)
        distinct=meaning(rows[0])!=meaning(revised_rows[0])
        ok=observed==case["categories"] and conflict==case["conflicts"] and distinct==case["distinct"]
        ok=ok and any(x["reviewRequired"] for x in diff)==case["reviewRequired"]
        results.append({"id":"governance:"+case["id"],"passed":ok,"categories":observed,"conflicts":conflict})
    legacy,losses=project(rows)
    # Concurrent meanings stay separate even when their presentation names coincide.
    mixed=copy.deepcopy(rows)
    other=copy.deepcopy(rows[0])
    for key in ("mappingId","semanticId","role"):other[key]=fixture["distinctBinding"][key]
    mixed.append(other)
    results.append({"id":"canonical:coexisting-same-label-different-meaning",
                    "passed":len({r["member"]["name"] for r in mixed})==fixture["distinctBinding"]["expectedNameCount"] and
                    len({r["semanticId"] for r in mixed})==fixture["distinctBinding"]["expectedConceptCount"] and not conflicts(mixed)})
    results.append({"id":"canonical:equipment-instances-preserved",
                    "passed":len({r["equipmentInstanceId"] for r in rows})==4})
    expected=set(fixture["projectionLossFields"])
    results.append({"id":"projection:loss-inventory","passed":{x["field"] for x in losses}==expected and len(losses)==len(rows)*len(expected)})
    results.append({"id":"projection:legacy-is-not-full-contract","passed":all(set(d)=={"name","type","semanticId","range"} for d in legacy) and bool(losses)})
    for case in fixture["valueCases"]:
        row=copy.deepcopy(rows[0]);row["source"]["rawRepresentation"]={"mode":"typed","valueType":"Int64"}
        row["mapping"]["transform"]=case["transform"];row["member"]["range"]=None
        value,issues=evaluate(row,case)
        results.append({"id":"loss:"+case["id"],"passed":value==case["expected"] and issues==case["issues"]})
    report={"kind":"governance-assessment","schemaVersion":"1.0.0",
            "proposalSha256":vc.hashed(root/"proposal.json"),
            "bindings":[{"mappingId":r["mappingId"],"equipmentInstanceId":r["equipmentInstanceId"],"meaning":meaning(r)} for r in rows],
            "projectionLosses":losses,"valueOutcomes":outcomes,"changeAssessments":change_reports,"deviceCommunicationRequired":False}
    results.append({"id":"governance:report-contract","passed":not vc.validate_schema("governance-assessment",report)})
    invalid_report=copy.deepcopy(report);invalid_report["deviceCommunicationRequired"]=True
    results.append({"id":"governance:communication-out-of-scope-contract","passed":bool(vc.validate_schema("governance-assessment",invalid_report))})
    return results,report
