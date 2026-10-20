"""P5 offline comparison and immutable review records. No runtime authority."""
import copy,json,re
from datetime import datetime,timezone
from jsonschema import Draft202012Validator,FormatChecker
from pathlib import Path
from sample_quality import digest,timestamp
ROOT=Path(__file__).resolve().parents[1]
SECTIONS={"semanticLifecycles":"semantic-lifecycle","equipment":"equipment-context","connections":"connection-profile","sources":"source-definition","semantics":"semantic-definition","targets":"target-instance","graphs":"value-graph","mappings":"mapping-set","writes":"write-definition","imports":"import-batch"}
REFS={"connectionProfileRef":"connection-profile","semanticDefinitionRef":"semantic-definition","targetInstanceRef":"target-instance","sourceRef":"source-definition","destinationRef":"source-definition","graphRef":"value-graph","viewOf":"source-definition"}
def validate(kind,doc):
    schema=json.loads((ROOT/"contracts/2.8.0"/(kind+".schema.json")).read_text())
    errors=list(Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(doc))
    if errors:raise ValueError(kind+": "+errors[0].message)
def index(state):
    out={}
    for section,kind in SECTIONS.items():
        for row in state.get(section,[]):
            d=row["definition"] if section=="sources" else row
            out[kind+":"+d["id"]]=copy.deepcopy(row)
    return out
def definition(row):return row.get("definition",row)
def references(row):
    out=set()
    def visit(v):
        if isinstance(v,dict):
            for k,x in v.items():
                if k in REFS and x:
                    id=x.get("id") if isinstance(x,dict) else x
                    if id:out.add(REFS[k]+":"+id)
                elif k=="equipmentInstanceId" and x:out.add("equipment-context:"+x)
                elif k=="batchId" and x:out.add("import-batch:"+x)
                visit(x)
        elif isinstance(v,list):
            for x in v:visit(x)
    visit(row);return out
def refs_in(value):
    out={}
    def visit(v):
        if isinstance(v,dict):
            if "evidenceRefs" in v:
                for r in v["evidenceRefs"]:out[digest(r)]=r
            for x in v.values():visit(x)
        elif isinstance(v,list):
            for x in v:visit(x)
    visit(value);return [out[k] for k in sorted(out)]
def target(state,key):
    rows=index(state)
    if key not in rows:raise ValueError("Review target missing")
    closure={};pending=[key];missing=[]
    while pending:
        k=pending.pop()
        if k in closure:continue
        if k not in rows:
            if k not in missing:missing.append(k)
            continue
        closure[k]=rows[k];pending.extend(references(rows[k])-set(closure))
    deps={k:digest(v) for k,v in sorted(closure.items())}
    return {"key":key,"targetSha256":digest(rows[key]),"dependencySha256":digest({"documents":deps,"missing":sorted(missing)}),
            "dependencies":deps,"missingDependencies":sorted(missing),"evidenceRefs":refs_in(list(closure.values()))}
def category(path):
    p=path.split("/")
    if "memberPath" in p:return "identity"
    if any(x in p for x in ("semanticId","role","outputUnit","unit","valueType")):
        return "decode" if "rawRepresentation" in p else "meaning"
    if any(x in p for x in ("access","accessProfileRef","accessMode","sourceKind","addressRadix")):return "access"
    if any(x in p for x in ("rawRepresentation","codec","fixedArray","inputStage")):return "decode"
    if any(x in p for x in ("transform","invalidValuePolicy","temporalPolicy","samplePolicy","assemblyPolicy","qualityPolicy")):return "transform"
    if any(x in p for x in ("label","name","description")):return "presentation"
    if any(x in p for x in ("rawAddressText","note","origin","capturedAt","evidenceRefs","importRef")):return "evidence"
    if "members" in p and any(x in p for x in ("shape","lowerBounds")):return "meaning"
    if any(x in p for x in ("range","status")):return "constraint"
    if p[-1] in ("id","memberId","mappingId","nodeId","memberPath") and not any(x.endswith("Ref") or x=="inputs" for x in p):return "identity"
    if "view" in p:return "decode"
    if any(x in p for x in ("inputs","nodes","valueRef","resultNodeId","candidates","indices","selector")):return "graph"
    if any(x in p for x in ("equipmentInstanceId","connectionProfileRef")):return "context"
    if any(x.endswith("Ref") or x=="viewOf" for x in p):return "reference"
    return "definition"
def leaves(a,b,path=""):
    if digest(a)==digest(b):return []
    if isinstance(a,dict) and isinstance(b,dict):
        out=[]
        for k in sorted(a.keys()|b.keys()):
            ptr=path+"/"+k.replace("~","~0").replace("/","~1")
            if k not in a or k not in b:out.append((ptr,a.get(k),b.get(k),"added" if k not in a else "removed"))
            else:out.extend(leaves(a[k],b[k],ptr))
        return out
    if isinstance(a,list) and isinstance(b,list):
        stable=next((k for k in ("memberId","mappingId","nodeId") if a and b and all(isinstance(x,dict) and k in x for x in a+b)),None)
        if stable:
            aa={x[stable]:x for x in a};bb={x[stable]:x for x in b};out=[]
            for k in sorted(aa.keys()|bb.keys()):
                ptr=path+"/"+k.replace("~","~0").replace("/","~1")
                if k not in aa or k not in bb:out.append((ptr,aa.get(k),bb.get(k),"added" if k not in aa else "removed"))
                else:out.extend(leaves(aa[k],bb[k],ptr))
            if [x[stable] for x in a]!=[x[stable] for x in b] and set(aa)==set(bb):out.append((path+"/order",[x[stable] for x in a],[x[stable] for x in b],"modified"))
            return out
    # Non-identity arrays preserve order and compare as an explicit before/after value.
    return [(path or "/",a,b,"modified")]
def diagnostics(state,findings):
    out=[{"code":f["ruleCode"],"path":f.get("path"),"classification":"incomplete" if any(s in f["ruleCode"] for s in ("incomplete","not-ready","unresolved","unknown","unconfirmed","timezone-required","bit-coordinate-required","empty","no-mapping","draft")) else "definition-conflict"} for f in findings]
    seen={}
    for row in state["sources"]:
        d=row["definition"]
        if d.get("viewOf"):out.append({"code":"source.explicit-view","path":d["id"],"classification":"declared-view"})
        if d.get("status")!="ready" or d.get("sourceKind")=="constant":continue
        a=copy.deepcopy(d["access"]);a.pop("bitOffset",None);a.pop("bitIndex",None)
        key=digest([d["equipmentInstanceId"],d.get("connectionProfileRef"),d["accessProfileRef"],a])
        if key in seen:
            other=seen[key]
            declared=bool(d.get("viewOf") or other.get("viewOf"))
            out.append({"code":"source.shared-access-view" if declared else "source.shared-access-review","path":other["id"]+" / "+d["id"],"classification":"declared-view" if declared else "definition-conflict"})
        else:seen[key]=d
    for b in state.get("imports",[]):
        for o in b.get("observations",[]):
            if o.get("derivation"):out.append({"code":"import.derivation-preserved","path":b["id"]+"/"+o["id"],"classification":"observation"})
    return out
def compare(baseline,state,revision,findings):
    before=baseline["workspace"];old=index(before);new=index(state);changes=[]
    for key in sorted(old.keys()|new.keys()):
        if key not in old or key not in new:
            changes.append({"key":key,"path":"/","category":"identity","change":"added" if key not in old else "removed","before":old.get(key),"after":new.get(key),"reviewRequired":True})
        else:
            for p,a,b,mode in leaves(old[key],new[key]):
                cat="import-evidence" if key.startswith("import-batch:") else category(p)
                changes.append({"key":key,"path":p,"category":cat,"change":mode,"before":a,"after":b,"reviewRequired":cat!="presentation"})
    changed={c["key"] for c in changes};affected=[]
    for key in sorted(new):
        now=target(state,key)
        prior=target(before,key) if key in old else None
        if prior is None or prior["dependencySha256"]!=now["dependencySha256"]:
            affected.append({"key":key,"direct":key in changed,"causes":sorted(changed & (set(now["dependencies"]) | (set(prior["dependencies"]) if prior else set()))),
                             "targetSha256":now["targetSha256"],"dependencySha256":now["dependencySha256"]})
    report={"kind":"change-assessment","schemaVersion":"2.8.0","baselineId":baseline["id"],"baselineSha256":baseline["workspaceSha256"],"workspaceRevision":revision,"workspaceSha256":digest(state),
            "changes":changes,"affected":affected,"diagnostics":diagnostics(state,findings),"approval":"not-requested","deviceVerification":"not-performed"}
    validate("change-assessment",report)
    return report
def review_status(record,state):
    key=record["targetKey"]
    if key not in index(state):return "target-removed"
    now=target(state,key)
    if now["targetSha256"]!=record["targetSha256"] or now["dependencySha256"]!=record["dependencySha256"]:return "needs-review"
    return record["decision"]
def init(c):
    c.execute("CREATE TABLE IF NOT EXISTS review_baselines (id TEXT PRIMARY KEY,body TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS change_reviews (seq INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT UNIQUE NOT NULL,body TEXT NOT NULL)")
def snapshot(c,revision,Conflict):
    if type(revision) is not int or revision<0:raise ValueError("Invalid workspace revision")
    actual,body=c.execute("SELECT revision,body FROM workspace WHERE id=1").fetchone()
    if actual!=revision:raise Conflict("작성본이 변경됐습니다. 비교와 검토를 다시 확인하세요.")
    return json.loads(body)
def baselines(store):
    with store.connect() as c:
        return {"baselines":[{k:v for k,v in json.loads(body).items() if k!="workspace"} for body, in c.execute("SELECT body FROM review_baselines ORDER BY id")]}
def baseline(store,request,Conflict):
    if set(request)!={"revision","id","label"}:raise ValueError("Invalid baseline request")
    with store.connect() as c:
        c.execute("BEGIN IMMEDIATE");w=snapshot(c,request["revision"],Conflict)
        d={"kind":"review-baseline","schemaVersion":"2.8.0","id":request["id"],"label":request["label"],"workspaceRevision":request["revision"],"workspaceSha256":digest(w),"capturedAt":datetime.now(timezone.utc).isoformat(),"workspace":w}
        validate("review-baseline",d)
        if c.execute("SELECT 1 FROM review_baselines WHERE id=?",(d["id"],)).fetchone():raise Conflict("기준본 ID는 불변입니다. 새 ID를 사용하세요.")
        if c.execute("SELECT COUNT(*) FROM review_baselines").fetchone()[0]>=20:raise ValueError("At most 20 baselines")
        c.execute("INSERT INTO review_baselines VALUES (?,?)",(d["id"],json.dumps(d,ensure_ascii=False,allow_nan=False)))
    return {k:v for k,v in d.items() if k!="workspace"}
def load_baseline(c,id):
    if not isinstance(id,str) or not re.fullmatch(r"[a-z][a-z0-9._/-]{0,127}",id):raise ValueError("Invalid baseline ID")
    row=c.execute("SELECT body FROM review_baselines WHERE id=?",(id,)).fetchone()
    if not row:raise ValueError("Baseline missing")
    b=json.loads(row[0])
    if digest(b["workspace"])!=b["workspaceSha256"]:raise ValueError("Baseline digest mismatch")
    return b
def assessment(store,request,Conflict,findings_for):
    if set(request)!={"revision","baselineId"}:raise ValueError("Invalid compare request")
    with store.connect() as c:
        c.execute("BEGIN");w=snapshot(c,request["revision"],Conflict);b=load_baseline(c,request["baselineId"])
    return compare(b,w,request["revision"],findings_for(w))
def reviews(store):
    with store.connect() as c:
        revision,body=c.execute("SELECT revision,body FROM workspace WHERE id=1").fetchone();w=json.loads(body)
        docs=[json.loads(body) for body, in c.execute("SELECT body FROM change_reviews ORDER BY seq")]
    latest={r["targetKey"]:r for r in docs}
    return {"workspaceRevision":revision,"targets":[dict(target(w,k),reviewStatus=review_status(latest[k],w) if k in latest else "unreviewed",latestReviewId=latest[k]["id"] if k in latest else None) for k in sorted(index(w))],"records":[{"record":r,"currentStatus":review_status(r,w),"superseded":latest[r["targetKey"]]["id"]!=r["id"]} for r in docs],"approval":"not-requested","deviceVerification":"not-performed"}
def save_review(store,request,Conflict):
    if set(request)!={"revision","record"}:raise ValueError("Invalid review request")
    d=request["record"];validate("change-review",d);timestamp(d["at"])
    if not d["rationale"].strip():raise ValueError("Review rationale required")
    with store.connect() as c:
        c.execute("BEGIN IMMEDIATE");w=snapshot(c,request["revision"],Conflict)
        b=load_baseline(c,d["baselineId"])
        if d["workspaceSha256"]!=digest(w) or d["baselineSha256"]!=b["workspaceSha256"]:raise Conflict("검토 대상 해시가 변경됐습니다. 다시 비교하세요.")
        t=target(w,d["targetKey"])
        if any(d[k]!=t[k] for k in ("targetSha256","dependencySha256")):raise Conflict("대상 또는 의존 정의가 변경됐습니다.")
        if not set(map(digest,d["evidenceRefs"])).issubset(set(map(digest,t["evidenceRefs"]))):raise ValueError("Review evidence must belong to target dependency closure")
        if c.execute("SELECT 1 FROM change_reviews WHERE id=?",(d["id"],)).fetchone():raise Conflict("검토 기록은 불변입니다. 새 ID로 후속 검토를 남기세요.")
        if c.execute("SELECT COUNT(*) FROM change_reviews").fetchone()[0]>=1000:raise ValueError("At most 1000 review records")
        c.execute("INSERT INTO change_reviews(id,body) VALUES (?,?)",(d["id"],json.dumps(d,ensure_ascii=False,allow_nan=False)))
    return {"record":d,"currentStatus":d["decision"]}
