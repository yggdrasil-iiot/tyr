"""P7 evaluation preparation: explicit independent oracle, read-only workspace, no field certification."""
import argparse,copy,json,re,sys
from decimal import Decimal
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/"backend"),str(R/"scripts")]
import jsonschema,logical_structures as ls,sample_quality as sq,preview
PHASES=("import","interpret","map","inquire","correct","review")
SPLITS=("calibration","evaluation","heldout")
def require(ok,msg):
    if not ok:raise ValueError(msg)
def exact(d,keys,label):require(isinstance(d,dict) and set(d)==set(keys),label+": unexpected/missing fields")
def identity(equipment,target,path):return {"equipmentInstanceId":equipment,"targetInstanceRef":copy.deepcopy(target),"memberPath":copy.deepcopy(path)}
def key(v):return sq.digest(v)
def meaning(member):return {k:copy.deepcopy(member[k]) for k in ("semanticId","valueType","unit","role")}
def inventory(state,scope):
    require(state.get("workspaceVersion")=="2.0.0","Explicit workspace 2.0 migration required")
    require(isinstance(scope,list) and 1<=len(scope)<=32 and all(isinstance(x,str) for x in scope) and len(set(scope))==len(scope),"Choose 1..32 unique mapping sets")
    require(set(scope)<={m["id"] for m in state["mappings"]},"Mapping set missing")
    sources={(x["definition"]["id"],x["definition"]["version"]):x["definition"] for x in state["sources"]}
    graphs={(x["id"],x["version"]):x for x in state.get("graphs",[])}
    targets={(x["id"],x["version"]):x for x in state["targets"]};models={(x["id"],x["version"]):x for x in state["semantics"]}
    rows=[]
    def ref(v):return (v["id"],v["version"])
    def projection(binding):
        closure={};pending=[binding];seen=set()
        while pending:
            obj=pending.pop()
            if isinstance(obj,dict):
                for name,value in obj.items():
                    if name in ("sourceRef","viewOf","destinationRef","graphRef") and value is not None:
                        kind="graph" if name=="graphRef" else "source";rk=(kind,*ref(value))
                        if rk not in seen:
                            seen.add(rk);doc=(graphs if kind=="graph" else sources).get(ref(value));require(doc is not None,"Definition closure reference missing")
                            clean={k:copy.deepcopy(v) for k,v in doc.items() if k not in ("name","label","description","status","evidenceRefs","rawAddressText")}
                            closure["/".join(rk)]=clean;pending.append(clean)
                    elif name!="evidenceRefs":pending.append(value)
            elif isinstance(obj,list):pending.extend(obj)
            require(len(seen)<=512,"Definition closure too large")
        b={k:copy.deepcopy(v) for k,v in binding.items() if k not in ("mappingId","memberPath","evidenceRefs")}
        return {"binding":b,"closure":closure}
    for m in state["mappings"]:
        if m["id"] not in scope:continue
        target=targets.get(ref(m["targetInstanceRef"]));require(target is not None,"Target reference missing")
        model=models.get(ref(target["semanticDefinitionRef"]));require(model is not None,"Semantic reference missing")
        for b in m["mappings"]:
            member=ls.resolve(model,b["memberPath"])
            rows.append({"identity":identity(m["equipmentInstanceId"],m["targetInstanceRef"],b["memberPath"]),"mappingSetId":m["id"],"mappingId":b["mappingId"],"label":ls.label(b["memberPath"]),"meaning":meaning(member),"definitionSha256":sq.digest(projection(b)),"evidenceRefs":copy.deepcopy(b["evidenceRefs"])})
            require(len(rows)<=256,"Scope exceeds 256 mappings; select fewer mapping sets")
    return rows

def template(state,scope):
    rows=inventory(state,scope)
    require(rows,"Selected mapping sets contain no bindings")
    return {"pack":{"kind":"pov-evaluation-pack","version":"1.0.0","id":"review-required","origin":"synthetic","baselineWorkspaceSha256":sq.digest(state),"mappingSetIds":scope,"review":{"reviewerId":"","independenceAttested":False},"cases":[{"caseId":"case-%03d"%i,"split":"evaluation","identity":r["identity"],"expected":None,"oracleEvidence":"","samples":[]} for i,r in enumerate(rows,1)],"timePairs":[]},"inventory":rows,"expectedValuesGenerated":False,"fieldPoV":"not-performed"}

def validate(pack):
    schema=json.loads((R/"evaluation-contracts/1.0.0/pov-evaluation.schema.json").read_text(encoding="utf-8"))
    errors=list(jsonschema.Draft202012Validator(schema).iter_errors(pack));require(not errors,"Evaluation pack schema: "+("/".join(map(str,errors[0].absolute_path))+" "+errors[0].message if errors else ""))
    ids=set();identities=set();concepts={}
    for c in pack["cases"]:
        require(c["caseId"] not in ids,"Duplicate case ID");ids.add(c["caseId"])
        k=key(c["identity"]);require(k not in identities,"Duplicate oracle identity");identities.add(k)
        if c["expected"] is not None:
            require(pack["review"]["reviewerId"].strip() and pack["review"]["independenceAttested"] and c["oracleEvidence"].strip(),"Reviewed oracle and independence declaration required")
            sig=c["expected"]["meaning"];uri=sig["semanticId"];require(uri not in concepts or concepts[uri]==sig,"Conflicting canonical oracle meaning");concepts[uri]=sig
        require(len({s["sampleId"] for s in c["samples"]})==len(c["samples"]),"Duplicate sample ID")
        for s in c["samples"]:require(len(s["samples"])<=256,"Too many virtual inputs")
    pairs=set()
    for p in pack["timePairs"]:
        k=(p["participantId"],p["taskId"]);require(k not in pairs,"Duplicate time pair");pairs.add(k)

def sample_match(actual,expected):
    if key({k:v for k,v in actual.items() if k!="result"})!=key({k:v for k,v in expected.items() if k!="result"}):return False
    a,b=actual["result"],expected["result"]
    if a is None or b is None:return a is None and b is None
    if a["valueType"]!=b["valueType"] or a["unit"]!=b["unit"]:return False
    if a["valueType"] in preview.NUMERIC:
        try:return preview.decimal(a["value"])==preview.decimal(b["value"])
        except ValueError:return False
    return type(a["value"]) is type(b["value"]) and a["value"]==b["value"]

def ratio(n,d):return None if d==0 else str((Decimal(n)*100/Decimal(d)).quantize(Decimal("0.01")))
def time_metrics(pairs,split):
    selected=[p for p in pairs if p["split"]==split];completed=[p for p in selected if p["completed"]]
    manual=sum(sum(p["manual"].values()) for p in completed);tool=sum(sum(p["tool"].values()) for p in completed)
    orders={"manual-first":sum(p["order"][0]=="manual" for p in completed),"tool-first":sum(p["order"][0]=="tool" for p in completed)}
    return {"state":"measured-declared" if completed else "not-measured","completePairs":len(completed),"incompletePairs":len(selected)-len(completed),"manualSeconds":manual,"toolSeconds":tool,"savingPercent":ratio(manual-tool,manual),"orders":orders,"counterbalanced":all(orders.values()),"phases":{phase:{mode:sum(p[mode][phase] for p in completed) for mode in ("manual","tool")} for phase in PHASES}}

def evaluate(state,pack,revision=0):
    validate(pack);before=sq.digest(state);actual=inventory(state,pack["mappingSetIds"]);by_key={}
    for r in actual:by_key.setdefault(key(r["identity"]),[]).append(r)
    results=[];expected_keys=set()
    for c in pack["cases"]:
        k=key(c["identity"]);expected_keys.add(k);found=by_key.get(k,[])
        row={"caseId":c["caseId"],"split":c["split"],"identity":c["identity"],"oracleEvidence":c["oracleEvidence"],"samples":[],"meaningStatus":"not-assessed","definitionStatus":"not-assessed"}
        if not found:row["status"]="missing"
        elif len(found)>1:row.update(status="ambiguous",actual=found)
        elif c["expected"] is None:row.update(status="unreviewed",actual=found[0])
        else:
            a=found[0];row["actual"]=a;row["expected"]=c["expected"]
            row["meaningStatus"]="match" if key(a["meaning"])==key(c["expected"]["meaning"]) else "mismatch"
            pin=c["expected"]["definitionSha256"];row["definitionStatus"]="not-assessed" if pin is None else "match" if pin==a["definitionSha256"] else "difference"
            for sample in c["samples"]:
                try:
                    v=preview.run(state,a["mappingSetId"],a["mappingId"],sample["samples"],revision,sample.get("evaluationContext"))
                    observed={"result":v["result"],"quality":v["quality"],"issues":sorted({i["code"] for i in v["issues"]}),"losses":sorted({i["code"] for i in v["losses"]})}
                    expected=copy.deepcopy(sample["expected"]);expected["issues"]=sorted(expected["issues"]);expected["losses"]=sorted(expected["losses"])
                    row["samples"].append({"sampleId":sample["sampleId"],"matched":sample_match(observed,expected),"lossesMatched":observed["losses"]==expected["losses"],"expected":expected,"actual":observed,"preview":v})
                except (ValueError,KeyError,TypeError) as e:row["samples"].append({"sampleId":sample["sampleId"],"matched":False,"error":str(e)})
            row["status"]="meaning-mismatch" if row["meaningStatus"]=="mismatch" else "definition-difference" if row["definitionStatus"]=="difference" else "sample-mismatch" if any(not s["matched"] for s in row["samples"]) else "partial" if row["definitionStatus"]=="not-assessed" or not row["samples"] else "verified-fixture"
        results.append(row)
    groups=[]
    for uri in sorted({r["meaning"]["semanticId"] for r in actual}):
        rows=[r for r in actual if r["meaning"]["semanticId"]==uri]
        groups.append({"semanticId":uri,"count":len(rows),"identities":[r["identity"] for r in rows],"canonicalConflict":len({key(r["meaning"]) for r in rows})>1})
    metrics={}
    for split in SPLITS:
        rows=[r for r in results if r["split"]==split];counts={status:sum(r["status"]==status for r in rows) for status in ("missing","ambiguous","unreviewed","meaning-mismatch","definition-difference","sample-mismatch","partial","verified-fixture")}
        samples=[s for r in rows for s in r["samples"]];planned=sum(len(c["samples"]) for c in pack["cases"] if c["split"]==split)
        metrics[split]={"plannedSamples":planned,"evaluatedSamples":len(samples),"notRunSamples":planned-len(samples),"sampleMismatches":sum(not s["matched"] for s in samples),"lossChecks":sum("lossesMatched" in s for s in samples),"lossDiagnosticMismatches":sum(s.get("lossesMatched") is False for s in samples),"definitionDifferenceCases":sum(r["definitionStatus"]=="difference" for r in rows),"oracleCases":len(rows),"counts":counts,"verifiedPercent":ratio(counts["verified-fixture"],len(rows)),"meaningMatchCases":sum(r["meaningStatus"]=="match" for r in rows),"time":time_metrics(pack["timePairs"],split)}
    require(sq.digest(state)==before,"Evaluator modified workspace")
    reviewed=sum(len(found)==1 and any(key(c["identity"])==k and c["expected"] is not None for c in pack["cases"]) for k,found in by_key.items())
    coverage={"actualBindings":len(actual),"uniqueActualIdentities":len(by_key),"reviewedUnambiguousIdentities":reviewed,"reviewedIdentityCoveragePercent":ratio(reviewed,len(by_key))}
    report={"coverage":coverage,"kind":"pov-evaluation-report","version":"1.0.0","packId":pack["id"],"origin":pack["origin"],"fieldPoV":"not-certified","evidenceClass":"synthetic-only" if pack["origin"]=="synthetic" else "field-declared-unverified","revision":revision,"workspaceSha256":before,"baselineWorkspaceChanged":pack["baselineWorkspaceSha256"]!=before,"packSha256":sq.digest(pack),"reviewDeclaration":pack["review"],"scope":pack["mappingSetIds"],"metrics":metrics,"cases":results,"unexpectedMappings":[r for r in actual if key(r["identity"]) not in expected_keys],"semanticGroups":groups,"deviceCommunication":"excluded","externalSQL":"excluded","writeExecution":"excluded","activation":"not-performed","persisted":False}
    report["reportSha256"]=sq.digest(report);return report

def main():
    p=argparse.ArgumentParser();p.add_argument("workspace",type=Path);p.add_argument("--pack",type=Path);p.add_argument("--template",action="store_true");p.add_argument("--mapping-set",action="append");p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    require(a.template != bool(a.pack),"Choose --template or --pack")
    import validate_contracts as vc,server
    state=vc.load(a.workspace);server.check_state(state)
    result=template(state,a.mapping_set or [m["id"] for m in state["mappings"]])["pack"] if a.template else evaluate(state,vc.load(a.pack))
    require(a.out.resolve() not in {a.workspace.resolve(),a.pack.resolve() if a.pack else a.workspace.resolve()},"Do not overwrite inputs")
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("x",encoding="utf-8") as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False)
    print(json.dumps({"kind":result.get("kind","pov-evaluation-template"),"output":str(a.out),"fieldPoV":"not-certified"}))
if __name__=="__main__":main()
