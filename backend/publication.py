"""P6 file/CLI adapter. Publication authority and private keys stay outside Tyr."""
import base64,copy,hashlib,io,json,re,shutil,subprocess,tempfile,uuid,zipfile,time,os
from pathlib import Path
from datetime import datetime,timezone
import sample_quality as sq
import p3a_contracts as p3
import validate_contracts as vc
ID=re.compile(r"^[a-z][a-z0-9._-]{0,127}$")
def require(v,message):
    if not v:raise ValueError(message)
def schema(kind,doc):
    require(not list(vc.schema_validator(kind,"2.9.0").iter_errors(doc)),kind+": schema")
def manifest_digest(files):
    return hashlib.sha256("".join(p+"\t"+h+"\n" for p,h in sorted(files.items())).encode()).hexdigest()
def _fault(point):pass # Test-only process interruption seam, no request parameter.

def file_pins(folder):
    try:return _file_pins(folder)
    except OSError as e:raise ValueError("Submission file missing or unreadable") from e

def _file_pins(folder):
    require(not folder.is_symlink() and not folder.parent.is_symlink(),"Submission symlink")
    require(not any(p.is_symlink() for p in folder.rglob("*")),"Submission symlink")
    proposal=vc.load(folder/"proposal.json");pins={"proposal.json":vc.hashed(folder/"proposal.json"),"submission.json":vc.hashed(folder/"submission.json")}
    for e in proposal["files"]:
        pins[e["path"]]=e["sha256"]
        if e["kind"]=="evidence-artifact":
            f=vc.load(folder/e["path"])["file"];pins[f["path"]]=f["sha256"]
    for path,h in pins.items():require(vc.hashed(vc.safe(folder,path))==h,"Submission file digest mismatch")
    require({str(p.relative_to(folder)).replace(chr(92),"/") for p in folder.rglob("*") if p.is_file()}==set(pins),"Submission inventory mismatch")
    return pins
def build(state,folder,id,stream,by,base,mapping_ids,include_writes,build_package):
    require(isinstance(stream,str) and ID.fullmatch(stream) and isinstance(id,str) and ID.fullmatch(id) and isinstance(by,str) and ID.fullmatch(by),"Invalid submission ID/principal")
    require(isinstance(mapping_ids,list) and (1<=len(mapping_ids)<=1000 or len(mapping_ids)==0 and bool(state.get("semanticLifecycles"))) and len(set(mapping_ids))==len(mapping_ids),"Choose mapping sets")
    require(type(include_writes) is bool,"Explicit includeWrites Boolean required")
    require(set(mapping_ids)<=({m["id"] for m in state["mappings"]}|{"record:"+r["id"]+"@"+r["version"] for r in state.get("recordMappings",[])}),"Mapping set missing")
    with tempfile.TemporaryDirectory(prefix="tyr-p6-build-") as tmp:
        root=Path(tmp);build_package(state,root);p=vc.load(root/"proposal.json")
        entries={(e["kind"],e["id"],e["version"]):e for e in p["files"]};docs={k:vc.load(root/e["path"]) for k,e in entries.items()}
        selected={k for k in docs if k[0]=="mapping-set" and k[1] in mapping_ids or k[0]=="record-mapping" and "record:"+k[1]+"@"+k[2] in mapping_ids}
        targets={docs[k]["targetInstanceRef"]["id"] for k in selected if k[0]=="mapping-set"}
        if include_writes:selected|={k for k,d in docs.items() if k[0]=="write-definition" and d["targetInstanceRef"]["id"] in targets}
        if state.get("semanticLifecycles"):
            selected|={k for k in docs if k[0] in ("semantic-lifecycle","semantic-definition")}
        # The hierarchy is the context every published equipmentInstanceId resolves against.
        selected|={k for k in docs if k[0]=="equipment-hierarchy"}
        # Template/application documents contain historical snapshots, not live recursive refs.
        active=[d for d in docs.values() if d["kind"]=="template-application" and any((g["kind"],g["id"],g["version"]) in selected for g in d["generated"] if g["kind"]=="mapping-set")]
        def include(kind,ref):
            k=(kind,ref["id"],ref["version"]);require(k in docs,"Missing template history");selected.add(k);return docs[k]
        def include_template(ref):
            t=include("mapping-template",ref)
            if t["previousTemplateRef"] is not None:include_template(t["previousTemplateRef"])
        def include_record(r):
            include("record-mapping",r);include_template(r['templateRef']);include("semantic-definition",r['semanticDefinitionRef'])
            if r['previousMappingRef'] is not None:include_record(include("record-mapping",r['previousMappingRef']))
        for k in list(selected):
            if k[0]=="record-mapping":include_record(docs[k])
        def include_application(a):
            include("template-application",a);include_template(a["templateRef"])
            if a["previousApplicationRef"] is not None:include_application(include("template-application",a["previousApplicationRef"]))
        for a in active:
            include_application(a)
            for g in a["generated"]:include(g["kind"],g)
            for s in a["sourceSnapshots"]:include("source-definition",s)
        refs={"recordMappingRef":"record-mapping","sourceRef":"source-definition","destinationRef":"source-definition","graphRef":"value-graph","targetInstanceRef":"target-instance","semanticDefinitionRef":"semantic-definition","viewOf":"source-definition","previousBatchRef":"import-batch"}
        def visit(v):
            if isinstance(v,dict):
                for name,x in v.items():
                    if name in refs and x is not None:
                        key=(refs[name],x["id"],x["version"]);require(key in docs,"Missing proposal reference");selected.add(key)
                    if name=="artifactId":
                        keys=[k for k in docs if k[0]=="evidence-artifact" and k[1]==x];require(len(keys)==1,"Ambiguous evidence");selected.update(keys)
                    visit(x)
            elif isinstance(v,list):
                for x in v:visit(x)
        done=set()
        while selected-done:
            k=next(iter(selected-done));
            if k[0]=="record-mapping":include_record(docs[k])
            if k[0] not in ("mapping-template","template-application"):visit(docs[k])
            done.add(k)
        # A normal graph consumer may refer to a managed graph: retain its owning application proof too.
        while True:
            before=len(selected)
            for a in [d for d in docs.values() if d["kind"]=="template-application"]:
                if any((g["kind"],g["id"],g["version"]) in selected for g in a["generated"]):
                    latest=max((d for d in docs.values() if d["kind"]=="template-application" and d["applicationId"]==a["applicationId"]),key=lambda d:d["revision"])
                    include_application(latest)
                    for g in latest["generated"]:include(g["kind"],g)
                    for source in latest["sourceSnapshots"]+a["sourceSnapshots"]:include("source-definition",source)
            while selected-done:
                k=next(iter(selected-done))
                if k[0]=="record-mapping":include_record(docs[k])
                if k[0] not in ("mapping-template","template-application"):visit(docs[k])
                done.add(k)
            if len(selected)==before:break
        source_ids={k[1] for k in selected if k[0]=="source-definition"}
        selected|={k for k,d in docs.items() if k[0]=="import-batch" and d.get("reconciliation") and any(a["sourceId"] in source_ids for a in d["reconciliation"]["actions"])}
        while selected-done:
            k=next(iter(selected-done));
            if k[0]=="record-mapping":include_record(docs[k])
            if k[0] not in ("mapping-template","template-application"):visit(docs[k])
            done.add(k)
        for k in list(selected):
            if k[0]=="import-batch":
                selected.update(x for x in docs if x[0]=="evidence-artifact" and x[1]=="import-"+k[1])
        # Import metadata is part of the evidence closure, even if source evidence was manually updated.
        artifact_ids={k[1] for k in selected if k[0]=="evidence-artifact"}
        selected|={k for k in docs if k[0]=="import-batch" and "import-"+k[1] in artifact_ids}
        if any(k[0]=="import-batch" for k in selected):
            selected|={k for k,d in docs.items() if k[0]=="source-observation" and any(r["artifactId"] in artifact_ids for r in d["evidenceRefs"])}
        while selected-done:
            k=next(iter(selected-done));
            if k[0]=="record-mapping":include_record(docs[k])
            if k[0] not in ("mapping-template","template-application"):visit(docs[k])
            done.add(k)
        folder.mkdir(parents=True,exist_ok=False)
        p["files"]=[entries[k] for k in sorted(selected)]
        p["baseRelease"]=copy.deepcopy(base)
        for e in p["files"]:
            dest=folder/e["path"];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/e["path"],dest)
            d=docs[(e["kind"],e["id"],e["version"])]
            if e["kind"]=="evidence-artifact":
                dest=folder/d["file"]["path"];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/d["file"]["path"],dest)
        vc.save(folder/"proposal.json",p)
    submission={"kind":"mapping-submission","schemaVersion":"2.9.0","id":id,"streamId":stream,"version":"1.0.0","workspaceSha256":sq.digest(state),"proposalSha256":vc.hashed(folder/"proposal.json"),"baseRelease":base,"proposedBy":by,"execution":"excluded","context":{"equipment":copy.deepcopy(state["equipment"]),"connections":copy.deepcopy(state["connections"])}}
    schema("mapping-submission",submission);vc.save(folder/"submission.json",submission)
    errors,details=p3.validate_package(folder)
    return submission,file_pins(folder),errors+details.get("warnings",[])
def init(c):c.execute("CREATE TABLE IF NOT EXISTS mapping_submissions (id TEXT PRIMARY KEY,revision INTEGER NOT NULL,body TEXT NOT NULL)")
class Adapter:
    def __init__(self,jar=None,registry=None):
        self.jar=Path(jar).resolve() if jar else None;self.registry=Path(registry).resolve() if registry else None
    @property
    def configured(self):return self.jar is not None and self.registry is not None and self.jar.is_file()
    def call(self,*args):
        require(self.configured,"Bifrost CLI/registry is not configured")
        try:p=subprocess.run(["java","-jar",str(self.jar),"mapping",*map(str,args)],capture_output=True,timeout=120)
        except (OSError,subprocess.TimeoutExpired) as e:raise ValueError("Bifrost CLI unavailable or timed out") from e
        try:doc=json.loads(p.stdout,object_pairs_hook=vc.pairs)
        except (ValueError,TypeError) as e:raise ValueError("Invalid Bifrost CLI response") from e
        require(p.returncode in (0,1),"Bifrost CLI usage/error")
        return doc
    def status(self,id):return self.call("status",self.registry,id)
def listing(store,adapter):
    with store.connect() as c:
        rev,body=c.execute("SELECT revision,body FROM workspace WHERE id=1").fetchone();w=json.loads(body)
        rows=[dict(json.loads(body),submissionRevision=r) for r,body in c.execute("SELECT revision,body FROM mapping_submissions ORDER BY id")]
    return {"workspaceRevision":rev,"configured":adapter.configured,"submissions":[dict(r,stale=r["workspaceSha256"]!=sq.digest(w)) for r in rows],"approvalAuthority":"bifrost","activation":"not-performed","execution":"excluded"}
def export(store,request,Conflict,build_package,adapter):
    require(set(request)=={"revision","id","streamId","proposedBy","mappingSetIds","includeWrites"},"Invalid export request")
    id=request["id"];require(isinstance(id,str) and ID.fullmatch(id),"Invalid submission ID")
    require(type(request["revision"]) is int and request["revision"]>=0,"Invalid revision")
    require(isinstance(request["streamId"],str) and ID.fullmatch(request["streamId"]),"Invalid stream ID")
    base=None
    if adapter.configured:
        status=adapter.status(request["streamId"]);require("error" not in status,"Bifrost status unavailable");base=status["head"]
    with store.connect() as c:
        c.execute("BEGIN IMMEDIATE");revision,body=c.execute("SELECT revision,body FROM workspace WHERE id=1").fetchone()
        if revision!=request["revision"]:raise Conflict("작성본이 변경됐습니다. 다시 제출본을 만드세요.")
        if c.execute("SELECT 1 FROM mapping_submissions WHERE id=?",(id,)).fetchone():raise Conflict("제출본은 불변입니다. 새 제출본 ID를 사용하세요.")
        require(c.execute("SELECT COUNT(*) FROM mapping_submissions").fetchone()[0]<100,"At most 100 submissions")
        w=json.loads(body);folder=store.path.resolve().with_suffix(".submissions")/(id+"-"+uuid.uuid4().hex)
        doc,pins,findings=build(w,folder,id,request["streamId"],request["proposedBy"],base,request["mappingSetIds"],request["includeWrites"],build_package)
        _fault("bundle-built")
        record={"id":id,"streamId":request["streamId"],"workspaceRevision":revision,"workspaceSha256":doc["workspaceSha256"],"proposalSha256":doc["proposalSha256"],"bundleSha256":manifest_digest(pins),"mappingSetIds":request["mappingSetIds"],"includeWrites":request["includeWrites"],"path":str(folder),"exportedAt":datetime.now(timezone.utc).isoformat(),"preflightFindings":findings,"validation":None,"publication":None}
        c.execute("INSERT INTO mapping_submissions VALUES (?,?,?)",(id,1,json.dumps(record,ensure_ascii=False,allow_nan=False)))
        _fault("row-inserted")
    _fault("row-committed")
    return dict(record,submissionRevision=1)
def lookup(store,id):
    require(isinstance(id,str) and ID.fullmatch(id),"Invalid submission ID")
    with store.connect() as c:
        row=c.execute("SELECT revision,body FROM mapping_submissions WHERE id=?",(id,)).fetchone()
    require(row is not None,"Submission missing");return row[0],json.loads(row[1])
def refresh(store,request,Conflict,adapter):
    require(set(request)=={"id","submissionRevision"},"Invalid publication refresh")
    require(type(request["submissionRevision"]) is int,"Invalid submission revision")
    rev,record=lookup(store,request["id"])
    if rev!=request["submissionRevision"]:raise Conflict("제출 기록이 변경됐습니다. 목록을 다시 여세요.")
    folder=Path(record["path"]);pins=file_pins(folder);require(manifest_digest(pins)==record["bundleSha256"],"Stored submission changed")
    validation=adapter.call("validate",folder);schema("mapping-validation",validation)
    require(not validation["accepted"] or (validation["proposalSha256"]==record["proposalSha256"] and validation["bundleSha256"]==record["bundleSha256"]),"Receiver response digest mismatch")
    status=adapter.status(record["streamId"]);require(status.get("kind")=="mapping-publication-status" and status.get("streamId")==record["streamId"] and "error" not in status,"Invalid publication status")
    # Status is observed via trusted configured CLI; never accepted as an uploaded client claim.
    record["validation"]=validation;record["publication"]=status;record["observedAt"]=datetime.now(timezone.utc).isoformat()
    release=status.get("release")
    if release and release.get("bundleSha256")==record["bundleSha256"]:record["publicationState"]="published"
    elif status["head"]!=vc.load(folder/"submission.json")["baseRelease"]:record["publicationState"]="base-conflict"
    elif any(a["payload"]["bundleSha256"]==record["bundleSha256"] for a in status["approvals"]):record["publicationState"]="approved"
    else:record["publicationState"]="awaiting-approval" if validation["accepted"] else "receiver-refused"
    with store.connect() as c:
        c.execute("BEGIN IMMEDIATE")
        cursor=c.execute("UPDATE mapping_submissions SET revision=revision+1,body=? WHERE id=? AND revision=?",(json.dumps(record,ensure_ascii=False,allow_nan=False),record["id"],rev))
        if cursor.rowcount!=1:raise Conflict("제출 기록이 변경됐습니다. 다시 조회하세요.")
    return dict(record,submissionRevision=rev+1)
def download(store,id):
    _,r=lookup(store,id);folder=Path(r["path"]);pins=file_pins(folder);require(manifest_digest(pins)==r["bundleSha256"],"Stored submission changed")
    data=io.BytesIO()
    with zipfile.ZipFile(data,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for rel in sorted(pins):z.write(folder/rel,rel)
    return {"filename":id+".zip","bytesBase64":base64.b64encode(data.getvalue()).decode(),"bundleSha256":r["bundleSha256"]}


def maintenance(store,request):
    """DB lock serializes export and quarantine. Never repairs or adopts uncommitted bundles."""
    require(set(request) in ({"graceSeconds"},{"graceSeconds","planSha256"}),"Invalid maintenance request")
    grace=request["graceSeconds"];require(type(grace) is int and 3600<=grace<=31536000,"GC grace must be 1 hour to 1 year")
    if "planSha256" in request:require(isinstance(request["planSha256"],str) and re.fullmatch("[0-9a-f]{64}",request["planSha256"]),"Invalid GC plan")
    root=store.path.resolve().with_suffix(".submissions")
    require(not root.is_symlink(),"Submission root symlink")
    with store.connect() as c:
        c.execute("BEGIN IMMEDIATE")
        rows=[dict(json.loads(body),submissionRevision=rev) for rev,body in c.execute("SELECT revision,body FROM mapping_submissions ORDER BY id")]
        referenced=set();integrity=[]
        for row in rows:
            folder=Path(row["path"])
            require(folder.is_absolute() and folder.parent==root,"Submission outside managed root")
            referenced.add(folder.name)
            try:
                require(manifest_digest(file_pins(folder))==row["bundleSha256"],"Stored submission changed")
                integrity.append({"id":row["id"],"state":"verified"})
            except (OSError,ValueError) as e:integrity.append({"id":row["id"],"state":"corrupt","error":str(e)})
        candidates=[]
        if root.exists():
            for folder in sorted(root.iterdir()):
                if folder.name in referenced or not re.fullmatch("[a-z][a-z0-9._-]{0,127}-[0-9a-f]{32}",folder.name):continue
                require(folder.is_dir() and not folder.is_symlink(),"GC candidate is not a safe directory")
                if folder.stat().st_mtime+grace>time.time():continue
                pins={}
                for f in sorted(folder.rglob("*")):
                    require(not f.is_symlink(),"GC candidate symlink")
                    if f.is_file():pins[f.relative_to(folder).as_posix()]=vc.hashed(f)
                    else:require(f.is_dir(),"GC candidate special file")
                candidates.append({"path":folder.name,"sha256":manifest_digest(pins),"modifiedNs":folder.stat().st_mtime_ns})
        plan={"kind":"submission-maintenance","version":1,"graceSeconds":grace,"integrity":integrity,"candidates":candidates,"rootsSha256":sq.digest(rows),"execution":"excluded","activation":"not-performed"}
        plan["planSha256"]=sq.digest(plan)
        if "planSha256" in request:
            require(all(i["state"]=="verified" for i in integrity),"Stored submission corrupt; quarantine refused")
            require(request["planSha256"]==plan["planSha256"],"GC plan changed; preview again")
            for candidate in candidates:
                dest=root/"quarantine"/uuid.uuid4().hex/candidate["path"]
                require(not (root/"quarantine").is_symlink(),"Quarantine symlink")
                dest.parent.mkdir(parents=True,exist_ok=False);os.replace(root/candidate["path"],dest);_fault("gc-quarantined")
            plan["action"]="quarantine"
        plan["dryRun"]="planSha256" not in request
    return plan
