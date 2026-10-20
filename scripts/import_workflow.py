"""Immutable import observations + append-only review and bounded three-way reconciliation."""
import copy,hashlib,json,re
from decimal import Decimal
import validate_contracts as vc
VERSION="2.14.0"
IMMUTABLE={"kind","id","version","equipmentInstanceId","status","evidenceRefs"}
def canonical(v):
 if v is None:return ["null"]
 if isinstance(v,bool):return ["boolean",v]
 if isinstance(v,(int,float,Decimal)):
  d=Decimal(str(v))
  if not d.is_finite():raise ValueError("workflow.nonfinite")
  text=format(d,"f")
  if "." in text:text=text.rstrip("0").rstrip(".")
  if Decimal(text)==0:text="0"
  return ["number",text]
 if isinstance(v,str):return ["string",v]
 if isinstance(v,list):return ["array",[canonical(x) for x in v]]
 if isinstance(v,dict):return ["object",[[k,canonical(v[k])] for k in sorted(v)]]
 raise ValueError("workflow.json")
def digest(v):return hashlib.sha256(json.dumps(canonical(v),ensure_ascii=False,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def require(ok,code):
 if not ok:raise ValueError(code)
def metadata(q):
 require(all(isinstance(q.get(k),str) and q[k].strip() and len(q[k])<=2000 for k in ("reviewer","reason")),"review.metadata")
 import sample_quality
 sample_quality.timestamp(q["reviewedAt"])
def promote(b,state=None):
 b=copy.deepcopy(b)
 if b["schemaVersion"]==VERSION:return b
 b.update(schemaVersion=VERSION,reviews=[],adoptions=[],reconciliation=None)
 if state:
  for row in state["sources"]:
   ref=row.get("importRef",{})
   if ref.get("batchId")==b["id"]:
    o=next(o for o in b["observations"] if o["id"]==ref["observationId"])
    b["adoptions"].append({"observationId":o["id"],"recordKey":key(b,o),"sourceId":row["definition"]["id"],"imported":project_draft(o["draft"],o["raw"].get("label") or o["draft"]["id"])})
 return b
def latest(b,o):
 return next((x for x in reversed(b.get("reviews",[])) if x["observationId"]==o["id"]),None)
def key(b,o):
 review=latest(b,o)
 if review and review["decision"]=="resolve-source":return review["recordKey"]
 raw=o["raw"]
 return raw.get("id") if isinstance(raw,dict) and isinstance(raw.get("id"),str) else None
def interpreted(b,o):
 review=latest(b,o)
 if review:return copy.deepcopy(review["source"]) if review["decision"]=="resolve-source" else None
 return copy.deepcopy(o["draft"])
def pending(b,o):
 if latest(b,o):return False
 return bool(o["issues"]) or o["draft"] is None
def unresolved(b):return "fileIssue" in b or any(pending(b,o) for o in b["observations"])
def refs(b,o):return [{"artifactId":"import-"+b["id"],"locator":loc} for loc in o["derivation"]]
def project_draft(d,label):
 return {**{k:copy.deepcopy(v) for k,v in d.items() if k not in IMMUTABLE},"label":label}
def project(row):return project_draft(row["definition"],row["label"])
def wrapper(d,k):return {"present":k in d,**({"value":d[k]} if k in d else {})}
def diff(base,ours,incoming):
 fields=[]
 for k in sorted(set(base)|set(ours)|set(incoming)):
  a,b,c=(wrapper(x,k) for x in (base,ours,incoming))
  conflict=b!=a and c!=a and b!=c
  fields.append({"field":k,"base":a,"ours":b,"incoming":c,"conflict":conflict,"suggested":"ours" if c==a else "incoming"})
 return fields
def materialize(b,o):
 d=interpreted(b,o)
 if d is None:return None
 a=next((a for a in b.get("adoptions",[]) if a["observationId"]==o["id"]),None)
 if a:
  d["id"]=a["sourceId"]
  rec=b.get("reconciliation")
  if rec and a["recordKey"] in rec["results"]:
   managed=rec["results"][a["recordKey"]]
   d={**{k:v for k,v in d.items() if k in IMMUTABLE},**{k:v for k,v in managed.items() if k!="label"}}
 return d
def check_source(b,o,d,record_key):
 import p3a_contracts as p3
 require(isinstance(record_key,str) and re.fullmatch("[a-z][a-z0-9-]{0,47}",record_key),"review.record-key")
 require(isinstance(d,dict) and not p3.schema_errors("source-definition",d),"review.source-schema")
 require(d["kind"]=="source-definition" and d["status"]=="draft" and d["version"]=="1.0.0","review.draft-required")
 require(d["id"]=="imp-"+b["id"]+"-"+record_key,"review.source-id")
 require(d["equipmentInstanceId"]==b["equipmentInstanceId"] and d["evidenceRefs"]==refs(b,o),"review.source-evidence")
 require(any(c["id"]==d["connectionProfileRef"] and c["accessProfileRef"]==d["accessProfileRef"] and c["equipmentInstanceId"]==d["equipmentInstanceId"] for c in b["contextConnections"]),"review.connection")
 ready=copy.deepcopy(d);ready["status"]="ready"
 require(not vc.source_rules(ready) and d["unit"]["status"]!="unknown","review.incomplete-source")
 require(d.get("sourceKind","plc")=="plc" and d.get("accessMode","read")=="read" and d.get("viewOf") is None,"review.plc-read-only")
def review(state,batch_id,decision):
 out=copy.deepcopy(state);b=next((b for b in out.get("imports",[]) if b["id"]==batch_id),None);require(b is not None,"import.batch-missing")
 require(not b.get("reconciliation") and not any(x.get("reconciliation") and x["reconciliation"]["previousBatchRef"]["id"]==batch_id for x in out["imports"]),"review.used-baseline-immutable")
 b=promote(b,out);o=next((o for o in b["observations"] if o["id"]==decision["observationId"]),None);require(o is not None,"review.observation-missing")
 metadata(decision);require(decision["observationSha256"]==digest(o),"review.observation-stale")
 old=latest(b,o);require(decision["previousReviewSha256"]==(digest(old) if old else None),"review.decision-stale")
 b["reviews"].append(copy.deepcopy(decision))
 out["imports"][next(i for i,x in enumerate(out["imports"]) if x["id"]==batch_id)]=b
 return out
def adopted_row(b,o,d,label=None,note=None):
 d=copy.deepcopy(d);d["status"]="draft";d["evidenceRefs"]=[{"artifactId":"manual-"+d["id"],"locator":{"kind":"text-line","line":1}}]+refs(b,o)
 review=latest(b,o)
 return {"definition":d,"label":label or (o["raw"].get("label") if isinstance(o["raw"],dict) else None) or d["id"],"note":note or ("Imported draft. SHA256 "+b["sha256"]+(" Review "+review["reviewer"]+": "+review["reason"] if review else "")),"origin":b["origin"],"capturedAt":b["capturedAt"],"importRef":{"batchId":b["id"],"observationId":o["id"]}}
def adopt(state,batch_id,selected):
 out=copy.deepcopy(state);b=next(b for b in out["imports"] if b["id"]==batch_id)
 require(not b.get("reconciliation") and not any(x.get("reconciliation") and x["reconciliation"]["previousBatchRef"]["id"]==batch_id for x in out["imports"]),"review.used-baseline-immutable")
 b=promote(b,out)
 require(isinstance(selected,list) and len(selected)==len(set(selected)),"import.selection")
 for oid in selected:
  o=next((o for o in b["observations"] if o["id"]==oid),None);require(o and not pending(b,o) and interpreted(b,o),"import.unresolved-adoption")
  d=interpreted(b,o);require(not any(r["definition"]["id"]==d["id"] for r in out["sources"]),"import.already-adopted")
  row=adopted_row(b,o,d);out["sources"].append(row)
  b["adoptions"].append({"observationId":oid,"recordKey":key(b,o),"sourceId":d["id"],"imported":project_draft(d,row["label"])})
 out["imports"][next(i for i,x in enumerate(out["imports"]) if x["id"]==batch_id)]=b
 return out
def previous_entries(old,rows):
 if old.get("adoptions"):return copy.deepcopy(old["adoptions"])
 entries=[]
 for row in rows:
  ref=row.get("importRef",{})
  if ref.get("batchId")==old["id"]:
   o=next(o for o in old["observations"] if o["id"]==ref["observationId"]);d=interpreted(old,o)
   require(d is not None,"merge.base-unresolved")
   entries.append({"observationId":o["id"],"recordKey":key(old,o),"sourceId":row["definition"]["id"],"imported":project_draft(d,o["raw"].get("label") or d["id"])})
 return entries
def plan(old,new,rows,workspace_hash):
 require(old["id"]!=new["id"] and old["equipmentInstanceId"]==new["equipmentInstanceId"] and old["format"]==new["format"],"merge.context")
 require("fileIssue" not in new and not new.get("reconciliation") and not new.get("adoptions"),"merge.new-batch-not-pristine")
 entries=previous_entries(old,rows);require(entries,"merge.no-adopted-base")
 require(len({e["recordKey"] for e in entries})==len(entries),"merge.ambiguous-base")
 existing={e["recordKey"]:e for e in entries};current={r["definition"]["id"]:r for r in rows};actions=[];seen=set()
 for o in new["observations"]:
  k=key(new,o) or o["id"]
  require(k not in seen,"merge.ambiguous-key");seen.add(k);e=existing.get(k)
  d=interpreted(new,o);inc=project_draft(d,(o["raw"].get("label") if isinstance(o["raw"],dict) else None) or d["id"]) if d else None
  if inc and e and inc["label"]==d["id"]:inc["label"]=e["sourceId"]
  ours=project(current[e["sourceId"]]) if e and e["sourceId"] in current else None
  require(not e or ours is not None,"merge.base-source-missing")
  if e and e["observationId"] is not None:require(current[e["sourceId"]].get("importRef")=={"batchId":old["id"],"observationId":e["observationId"]},"merge.base-not-current")
  base=e["imported"] if e else None;fs=diff(base,ours,inc) if base is not None and inc is not None else []
  cls="excluded" if latest(new,o) and latest(new,o)["decision"]=="exclude-non-source" else "unresolved" if pending(new,o) else "new" if not e else "conflict" if any(f["conflict"] for f in fs) else "unchanged" if base==ours==inc else "incoming-only" if ours==base else "local-only" if inc==base else "both-same" if ours==inc else "mergeable"
  actions.append({"key":k,"observationId":o["id"],"recordKey":k,"sourceId":e["sourceId"] if e else d["id"] if d else "imp-"+new["id"]+"-"+k,"classification":cls,"base":base,"ours":ours,"incoming":inc,"fields":fs})
 for k,e in existing.items():
  if k not in seen:
   require(e["sourceId"] in current,"merge.base-source-missing")
   actions.append({"key":k,"observationId":None,"recordKey":k,"sourceId":e["sourceId"],"classification":"removed","base":e["imported"],"ours":project(current[e["sourceId"]]),"incoming":None,"fields":[]})
 p={"previousBatchRef":{"id":old["id"],"version":old["version"]},"previousBatchSha256":digest(old),"workspaceSha256":workspace_hash,"ours":copy.deepcopy(rows),"actions":actions}
 p["planSha256"]=digest(p);return p
def results(p,choices):
 require(isinstance(choices,dict) and set(choices)=={a["key"] for a in p["actions"]},"merge.choices-incomplete")
 out={}
 for a in p["actions"]:
  q=choices[a["key"]];require(isinstance(q,dict) and set(q)=={"mode","fields"} and isinstance(q["fields"],dict),"merge.choice")
  mode=q["mode"];cls=a["classification"]
  if cls=="removed":
   require(mode=="retain" and not q["fields"],"merge.removal-policy");out[a["key"]]=a["ours"];continue
  if mode=="retain":
   require(cls not in ("new","excluded","unresolved") and a["ours"] is not None and not q["fields"],"merge.retain-policy")
   out[a["key"]]=copy.deepcopy(a["ours"]);continue
  if mode=="skip":
   require(cls in ("new","excluded") and not q["fields"],"merge.skip-policy");out[a["key"]]=None;continue
  require(mode=="apply" and cls not in ("unresolved","excluded"),"merge.unresolved")
  require(set(q["fields"])=={f["field"] for f in a["fields"] if f["conflict"]},"merge.conflicts-unresolved")
  if cls=="new":value=copy.deepcopy(a["incoming"])
  else:
   value={}
   for f in a["fields"]:
    choice=q["fields"].get(f["field"],f["suggested"]);require(choice in ("ours","incoming"),"merge.field-choice")
    picked=f[choice]
    if picked["present"]:value[f["field"]]=copy.deepcopy(picked["value"])
  out[a["key"]]=value
 return out
def apply(state,new,p,choices,meta):
 metadata(meta);require(p["workspaceSha256"]==digest(state),"merge.workspace-stale")
 out=copy.deepcopy(state);new=promote(new);res=results(p,choices)
 rec={**copy.deepcopy(p),"choices":copy.deepcopy(choices),"results":res,**{k:meta[k] for k in ("reviewer","reason","reviewedAt")}};new["reconciliation"]=rec
 for a in p["actions"]:
  value=res[a["key"]]
  if a["classification"]=="removed":
   new["adoptions"].append({"observationId":None,"recordKey":a["recordKey"],"sourceId":a["sourceId"],"imported":a["base"]});continue
  if value is None:continue
  o=next(o for o in new["observations"] if o["id"]==a["observationId"]);d=interpreted(new,o)
  new["adoptions"].append({"observationId":o["id"],"recordKey":a["recordKey"],"sourceId":a["sourceId"],"imported":a["incoming"]})
  d["id"]=a["sourceId"];d={**{k:v for k,v in d.items() if k in IMMUTABLE},**{k:v for k,v in value.items() if k!="label"}}
  old=next((row for row in out["sources"] if row["definition"]["id"]==a["sourceId"]),None)
  row=adopted_row(new,o,d,value["label"],old["note"] if old else None)
  require(old is None or a["base"] is not None,"merge.source-id-collision")
  if old:
   row["definition"]["version"]=old["definition"]["version"];out["sources"][out["sources"].index(old)]=row
  else:out["sources"].append(row)
 # Preserve dependent provenance without rewriting any original import observation.
 updated={a["sourceId"] for a in p["actions"] if a["observationId"] is not None and res[a["key"]] is not None}
 source_evidence={r["definition"]["id"]:r["definition"]["evidenceRefs"] for r in out["sources"] if r["definition"]["id"] in updated}
 def evidence_closure(v):
  if isinstance(v,dict):
   if isinstance(v.get("evidenceRefs"),list):
    refs=v["evidenceRefs"]
    for sid,new_refs in source_evidence.items():
     if any(e.get("artifactId")=="manual-"+sid for e in refs):
      for ref in new_refs:
       if ref not in refs:refs.append(copy.deepcopy(ref))
   for child in v.values():evidence_closure(child)
  elif isinstance(v,list):
   for child in v:evidence_closure(child)
 for section in ("targets","graphs","mappings","writes"):evidence_closure(out.get(section,[]))
 prior=next((i for i,b in enumerate(out.get("imports",[])) if b["id"]==new["id"]),None)
 if prior is None:out.setdefault("imports",[]).append(new)
 else:out["imports"][prior]=new
 return out
def check(b,batches):
 if b["schemaVersion"]!=VERSION:return
 if list(vc.schema_validator("import-batch",VERSION).iter_errors(b)):raise ValueError("workflow.schema")
 obs={o["id"]:o for o in b["observations"]};seen={};keys={}
 for q in b["reviews"]:
  metadata(q);o=obs.get(q["observationId"]);require(o is not None and q["observationSha256"]==digest(o),"review.observation-stale")
  prior=seen.get(o["id"]);require(q["previousReviewSha256"]==(digest(prior) if prior else None),"review.decision-chain")
  if q["decision"]=="resolve-source":check_source(b,o,q["source"],q["recordKey"])
  else:require(q["decision"]=="exclude-non-source" and q["source"] is None and q["recordKey"] is None,"review.exclusion")
  seen[o["id"]]=q
 for o in b["observations"]:
  if latest(b,o) and latest(b,o)["decision"]=="exclude-non-source":continue
  k=key(b,o)
  if not pending(b,o):
   require(k and k not in keys,"review.duplicate-key");keys[k]=o["id"]
 adopted=set();adopted_obs=set()
 for a in b["adoptions"]:
  require(a["sourceId"] not in adopted and a["observationId"] not in adopted_obs,"merge.duplicate-adoption") if a["observationId"] is not None else require(a["sourceId"] not in adopted,"merge.duplicate-adoption")
  adopted.add(a["sourceId"]);adopted_obs.add(a["observationId"])
  if a["observationId"] is None:require(b["reconciliation"] is not None,"merge.retained-without-plan");continue
  o=obs.get(a["observationId"]);require(o is not None and interpreted(b,o) is not None,"import.unresolved-adoption")
  d=interpreted(b,o);expected=project_draft(d,(o["raw"].get("label") if isinstance(o["raw"],dict) else None) or d["id"])
  if not b["reconciliation"]:require(a["sourceId"]==d["id"] and a["recordKey"]==key(b,o) and a["imported"]==expected,"merge.adoption-mismatch")
 if b["reconciliation"]:
  rec=b["reconciliation"];metadata(rec);old=next((x for x in batches if x["id"]==rec["previousBatchRef"]["id"] and x["version"]==rec["previousBatchRef"]["version"]),None)
  require(old is not None,"merge.previous-missing")
  clean=copy.deepcopy(b);clean["adoptions"]=[];clean["reconciliation"]=None
  expected=plan(old,clean,rec["ours"],rec["workspaceSha256"])
  require(all(rec[k]==v for k,v in expected.items()),"merge.plan-mismatch")
  require(rec["results"]==results(expected,rec["choices"]),"merge.result-mismatch")
  expected_adoptions=[]
  for a in expected["actions"]:
   if a["classification"]=="removed":expected_adoptions.append({"observationId":None,"recordKey":a["recordKey"],"sourceId":a["sourceId"],"imported":a["base"]})
   elif rec["results"][a["key"]] is not None:expected_adoptions.append({"observationId":a["observationId"],"recordKey":a["recordKey"],"sourceId":a["sourceId"],"imported":a["incoming"]})
  require(b["adoptions"]==expected_adoptions,"merge.adoption-mismatch")

def check_transition(previous,current):
 """Once opted into workflow 2.14, preserve original and append-only audit through every save."""
 old_batches={b["id"]:b for b in previous.get("imports",[])}
 new_batches={b["id"]:b for b in current.get("imports",[])}
 for id,old in old_batches.items():
  if old["schemaVersion"]!=VERSION:continue
  new=new_batches.get(id);require(new is not None and new.get("schemaVersion")==VERSION,"import.history-removal")
  old_core={k:v for k,v in old.items() if k not in ("reviews","adoptions","reconciliation")}
  new_core={k:v for k,v in new.items() if k not in ("reviews","adoptions","reconciliation")}
  require(digest(old_core)==digest(new_core),"import.original-immutable")
  for name in ("reviews","adoptions"):
   require(len(new[name])>=len(old[name]) and digest(new[name][:len(old[name])])==digest(old[name]),"import.history-truncation")
  if old["reconciliation"] is not None:require(digest(old)==digest(new),"import.reconciliation-immutable")
