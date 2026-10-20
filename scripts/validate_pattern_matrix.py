"""Offline mapping-pattern inventory gate. Planned specifications are never passes."""
import argparse, copy, json, sys, tempfile, hashlib, socket
from pathlib import Path
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"backend"))
import server
import validate_contracts as vc
import governance_checks as gc
CAT=ROOT/"fixtures/mapping-patterns"
def load(p): return json.loads(p.read_text(encoding="utf-8"))
def package(state):
    with tempfile.TemporaryDirectory() as t:
        root=Path(t);server.build_package(state,root)
        return gc.bindings(gc.documents(root)),vc.validate_package(root)
def rejected(f):
    try:f();return False
    except ValueError:return True
def run_case(c,w,rows):
    a=c["action"];i=c["input"];e=c["expect"];s=copy.deepcopy(w)
    byid={r["mappingId"]:r for r in copy.deepcopy(rows)}
    if a=="direct":
        server.check_state(s)
        return {"profiles":len({x["definition"]["accessProfileRef"] for x in s["sources"]}),"sourceCount":len(s["sources"])}
    if a=="dispersed":
        defs={x["definition"]["id"]:x["definition"] for x in s["sources"]}
        ms=next(x for x in s["mappings"] if x["id"]=="motor-object-melsec")["mappings"][:3]
        ss=[defs[m["sourceRef"]["id"]] for m in ms]
        return {"addresses":[x["access"]["addressIndex"] for x in ss],"wordCounts":[x["access"]["wordCount"] for x in ss],"members":[m["targetMemberId"] for m in ms]}
    if a=="names":
        labels={x["definition"]["id"]:x["label"] for x in s["sources"]}
        meanings=lambda label:{r["semanticId"] for r in rows if labels[r["source"]["id"]]==label}
        return {"speedNames":len({labels[r["source"]["id"]] for r in rows if r["member"]["memberId"]=="actual-speed"}),"pvMeaningCount":len(meanings("PV")),"statusMeaningCount":len(meanings("Status"))}
    if a=="partial-object":
        s["mappings"][0]["mappings"]=s["mappings"][0]["mappings"][:i["keepMembers"]]
        fs=server.findings_for(s)
        matches=[f for f in fs if f["ruleCode"]==e["rule"]]
        return {"rule":e["rule"] if matches else None,"count":len(matches)}
    if a=="evaluate":
        r=byid[i["mappingId"]]
        if "wordOrder" in i:r["source"]["rawRepresentation"]["wordOrder"]=i["wordOrder"]
        value,issues=gc.evaluate(r,i["sample"]);return {"value":value,"issues":issues}
    if a=="word-fanout":
        ms=next(x for x in s["mappings"] if x["id"]=="motor-object-melsec")["mappings"]
        state=next(x for x in ms if x["targetMemberId"]=="state")
        alarm=next(x for x in ms if x["targetMemberId"]=="alarm-active")
        alarm["sourceRef"]=copy.deepcopy(state["sourceRef"]);alarm["evidenceRefs"]=copy.deepcopy(state["evidenceRefs"])
        alarm["transform"]=[{"op":"bit-select","index":0},{"op":"cast","to":"Boolean","overflow":"error","rounding":"exact"}]
        rr,findings=package(s)
        if findings:raise AssertionError(findings)
        return {key:gc.evaluate(next(r for r in rr if r["mappingId"]=="melsec-"+member+"-binding"),i["sample"])[0] for key,member in [("state","state"),("alarm","alarm-active")]}
    if a=="missing-unit":
        for ms in s["mappings"]:
            for m in ms["mappings"]:
                if m["mappingId"]=="ua-actual-speed-binding":m["transform"]=[t for t in m["transform"] if t["op"]!="unit-convert"]
        _,fs=package(s);return {"rule":e["rule"] if any(f["ruleCode"]==e["rule"] for f in fs) else None}
    if a=="projection":
        _,losses=gc.project(rows);fields={x["field"] for x in losses}
        return {"requiredLossFields":[f for f in e["requiredLossFields"] if f in fields]}
    if a=="observation":
        ob=load(ROOT/"fixtures/packages/motor/observations/a.json")
        ob["status"]="unsupported";ob["claims"]=[{"field":"expression","value":i["expression"],"certainty":"explicit"}]
        if vc.validate_schema("source-observation",ob):raise AssertionError("observation schema")
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"observation.json";p.write_text(json.dumps(ob),encoding="utf-8")
            assert load(p)["claims"][0]["value"]==i["expression"]
        return {"status":ob["status"],"adoption":"not-a-source-definition"}
    if a=="multi-input-rejected":
        ms=s["mappings"][0];m=ms["mappings"][0];m.pop("sourceRef");m["inputs"]=i["inputs"]
        return {"schemaRejected":bool(vc.validate_schema("mapping-set",ms))}
    if a in ("raw-shape-rejected","native-bit-rejected","native-area-unchecked"):
        d=next(x["definition"] for x in s["sources"] if x["definition"]["id"]=="melsec-actual-speed")
        if a=="raw-shape-rejected":d["rawRepresentation"].update(i)
        elif a=="native-bit-rejected":d["access"]["addressUnit"]="bit"
        else:
            d["access"]["deviceArea"]=i["deviceArea"]
            return {"sourceRules":vc.source_rules(d),"knownGap":e["knownGap"]}
        return {"schemaRejected":bool(vc.validate_schema("source-definition",d))}
    if a=="alias-cycle":
        x,y=[v["definition"] for v in s["sources"][:2]]
        x["viewOf"]={"id":y["id"],"version":y["version"]};y["viewOf"]={"id":x["id"],"version":x["version"]}
        _,fs=package(s)
        return {"packageRules":sorted({f["ruleCode"] for f in fs}),"editorRejected":rejected(lambda:server.check_state(s)),"knownGap":e["knownGap"]}
    if a=="duplicate-object":
        ms=copy.deepcopy(s["mappings"][0]);ms["id"]+="-second"
        for m in ms["mappings"]:m["mappingId"]+="-second"
        s["mappings"].append(ms);_,fs=package(s)
        return {"rule":e["rule"] if any(f["ruleCode"]==e["rule"] for f in fs) else None,"knownGap":e["knownGap"]}
    raise AssertionError("Unknown action: "+a)
def main():
    p=argparse.ArgumentParser();p.add_argument("--deny-network",action="store_true");p.add_argument("--report",type=Path);args=p.parse_args()
    if args.deny_network:
        def deny(*a,**k):raise RuntimeError("Network forbidden")
        socket.socket=deny;socket.create_connection=deny
    matrix=load(CAT/"matrix.json");validator=Draft202012Validator(load(CAT/"case.schema.json"))
    patterns={x["id"]:x for x in matrix["patterns"]}
    assert len(patterns)==len(matrix["patterns"])==18
    assert set(patterns)=={"MP%02d"%i for i in range(1,19)}
    assert matrix["deviceCommunication"]=="excluded"
    for pat in patterns.values():
        assert set(pat["support"])==set(matrix["axes"])
        assert all(v in ("yes","partial","contract-only","no") for v in pat["support"].values())
        assert pat["priority"] in ("A","B","C")
        assert pat["phase"] in ("P3-A","P3-B","P3-C","P3-D","P3-E","P3-F","P4-A","P4-B")
        assert all(r in matrix["sources"] for r in pat["evidenceRefs"])
        assert all((ROOT/r).is_file() for r in pat["codeRefs"])
    cases=[];ids=set()
    for rel in matrix["cases"]:
        path=(CAT/rel).resolve();assert path.is_relative_to(CAT.resolve())
        c=load(path);validator.validate(c);assert c["id"] not in ids;ids.add(c["id"])
        assert c["patternId"] in patterns;cases.append(c)
    assert {c["patternId"] for c in cases}==set(patterns)
    assert {p.resolve() for p in (CAT/"cases").glob("*.json")}=={(CAT/r).resolve() for r in matrix["cases"]}
    w=load(ROOT/"fixtures/realistic/workspace.json");rows,fs=package(w);assert not fs,fs
    results=[]
    for c in cases:
        r={"id":c["id"],"patternId":c["patternId"],"mode":c["mode"]}
        if c["mode"]=="planned":
            assert c["action"]=="not-implemented"
            r.update(status="pending",expected=c["expect"])
        else:
            try:
                actual=run_case(c,w,rows)
                r.update(status="pass" if actual==c["expect"] else "fail",actual=actual,expected=c["expect"])
            except Exception as ex:r.update(status="fail",error=repr(ex),expected=c["expect"])
        results.append(r)
    inputs=[*CAT.rglob("*.json"),ROOT/"fixtures/realistic/workspace.json",Path(__file__),ROOT/"scripts/validate_contracts.py",ROOT/"scripts/governance_checks.py",ROOT/"backend/server.py",* (ROOT/"contracts").rglob("*.json")]
    report={"deviceCommunication":"excluded","networkDenied":args.deny_network,"patternCount":18,"caseCount":len(cases),
        "currentChecks":{"passed":sum(r["mode"]=="current" and r["status"]=="pass" for r in results),"total":sum(r["mode"]=="current" for r in results)},
        "gapProbes":{"matched":sum(r["mode"]=="gap-probe" and r["status"]=="pass" for r in results),"total":sum(r["mode"]=="gap-probe" for r in results)},
        "planned":{"pending":sum(r["status"]=="pending" for r in results),"countedAsPassed":False},
        "failed":sum(r["status"]=="fail" for r in results),"results":results,
        "sha256":{str(x.relative_to(ROOT)).replace(chr(92),"/"):hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(set(inputs))}}
    if args.report:args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k not in ("results","sha256")}))
    for r in results:
        if r["status"]=="fail":print(json.dumps(r,ensure_ascii=True))
    return bool(report["failed"])
if __name__=="__main__":sys.exit(main())
