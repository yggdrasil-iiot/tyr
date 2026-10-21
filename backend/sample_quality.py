import source_views
"""Deterministic virtual time/quality assessment; no wall clock or communication."""
import re,json,hashlib
from datetime import datetime,timezone
from decimal import Decimal
import validate_contracts as vc

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def timestamp(value):
    if not isinstance(value,str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|[+-](?:0[0-9]|1[0-9]|2[0-3]):[0-5][0-9])",value):
        raise ValueError("Explicit timestamp with offset, up to six fractional digits required")
    # RFC3339 -00:00 denotes an unknown local offset, not a known UTC clock.
    if value.endswith("-00:00"):raise ValueError("Unknown local offset -00:00")
    return datetime.fromisoformat(value.replace("Z","+00:00")).astimezone(timezone.utc)

def milliseconds(delta):
    return Decimal((delta.days*86400+delta.seconds)*1000000+delta.microseconds)/1000

def source_ids(state,binding):
    v=binding.get("valueRef") or {"kind":"source","sourceRef":binding["sourceRef"]}
    constants={r["definition"]["id"] for r in state["sources"] if r["definition"].get("sourceKind")=="constant"}
    if v["kind"]=="source":return [] if v["sourceRef"]["id"] in constants else source_views.root_ids(state,[v["sourceRef"]["id"]])
    import graph_reuse
    ids={id for id,version in graph_reuse.source_refs(state.get('graphs',[]),v['graphRef'],v['nodeId'])}
    return source_views.root_ids(state,ids-constants)

def assess(state,binding,samples,evaluation,required=None):
    policy=binding["temporalPolicy"];trace=[];issues=[];rows=[];values={};times=[]
    def issue(code,identity,detail="",severity="error"):
        issues.append({"code":code,"severity":severity,"stage":"temporal:"+identity,"detail":detail})
    def step(stage,id,detail,error=None):
        row={"stage":stage,"identity":id,"status":"error" if error else "ok","detail":detail}
        if error:row["error"]=error
        trace.append(row)
    now=None
    try:
        if not isinstance(evaluation,dict) or set(evaluation)!={"at","triggerSequence"}:raise ValueError("evaluationContext.at and triggerSequence required")
        now=timestamp(evaluation["at"])
        sequence=evaluation["triggerSequence"]
        if sequence is not None and (not isinstance(sequence,str) or not 1<=len(sequence)<=128):raise ValueError("Invalid triggerSequence")
        if policy["assembly"]=="trigger-sequence" and sequence is None:raise ValueError("Explicit triggerSequence required")
    except (ValueError,TypeError,OverflowError) as e:issue("time.evaluation-invalid","context",str(e))
    step("evaluation-context","virtual",{"evaluationContext":evaluation,"policy":policy,"atomicSnapshot":False},issues[-1]["code"] if issues else None)
    for id in (source_ids(state,binding) if required is None else required):
        sample=samples.get(id);start=len(issues);row={"sourceId":id,"basis":policy["timestampBasis"]}
        if not isinstance(sample,dict):
            issue("sample.missing",id)
        elif set(sample)!={"value","quality","sourceTimestamp","serverTimestamp","sequence"}:
            issue("sample.metadata-required",id,"Virtual DataValue envelope required")
        else:
            row.update({k:sample[k] for k in ("quality","sourceTimestamp","serverTimestamp","sequence")})
            source=next(r['definition'] for r in state['sources'] if r['definition']['id']==id)
            if source.get('recordField') is not None:
                value=sample['value'];snapshot=value.get('resultSet') if isinstance(value,dict) else None
                same_clock=False
                if isinstance(snapshot,dict):
                    try:same_clock=timestamp(sample['sourceTimestamp'])==timestamp(snapshot.get('capturedAt'))==timestamp(sample['serverTimestamp'])
                    except (ValueError,TypeError,OverflowError):pass
                if not isinstance(snapshot,dict) or not same_clock or sample['quality']!=snapshot.get('quality') or sample['sequence'] is not None:issue('record-field.envelope-mismatch',id,'Result-set clock instants and quality must match the virtual envelope')

            q=sample["quality"]
            if q not in ("good","uncertain","bad"):issue("quality.invalid",id)
            elif q=="bad":issue("quality.bad-input",id,"Bad input invalidates the whole derived result")
            elif q=="uncertain":issue("quality.uncertain-input",id,"Input quality is uncertain","warning" if policy["uncertainInput"]=="propagate" else "error")
            # Check both supplied clocks for malformed values; never substitute one for the other.
            parsed={}
            for key in ("sourceTimestamp","serverTimestamp"):
                text=sample[key]
                if text is None:continue
                try:parsed[key]=timestamp(text)
                except (ValueError,OverflowError):issue("time.timestamp-invalid",id,key)
            key=policy["timestampBasis"]+"Timestamp";t=parsed.get(key)
            if sample[key] is None:issue("time.timestamp-missing",id,key)
            if t is not None:
                times.append((id,t))
                if now is not None:
                    age=milliseconds(now-t);row["ageMs"]=str(age)
                    if age<0:issue("time.future-input",id,"ageMs="+str(age))
                    elif age>policy["maxAgeMs"]:issue("time.stale-input",id,"ageMs="+str(age)+"; maxAgeMs="+str(policy["maxAgeMs"]))
            if policy["assembly"]=="trigger-sequence" and now is not None and evaluation.get("triggerSequence") is not None:
                if sample["sequence"]!=evaluation["triggerSequence"]:issue("assembly.sequence-mismatch",id,"Expected triggerSequence="+evaluation["triggerSequence"])
            seq=sample["sequence"]
            if seq is not None and (not isinstance(seq,str) or not 1<=len(seq)<=128):issue("assembly.sequence-invalid",id)
            if sample["value"] is None:issue("sample.missing-value",id)
            else:values[id]=sample["value"]
        row["issues"]=[i["code"] for i in issues[start:]];rows.append(row)
        errors=[i for i in issues[start:] if i["severity"]=="error"]
        step("input-time-quality",id,row,errors[0]["code"] if errors else None)
    skew=None;range_=None
    if times:
        low=min(t for _,t in times);high=max(t for _,t in times)
        skew=milliseconds(high-low);range_={"oldest":low.isoformat(),"newest":high.isoformat()}
        if skew>policy["maxSkewMs"]:issue("time.skew-exceeded","assembly","skewMs="+str(skew)+"; maxSkewMs="+str(policy["maxSkewMs"]))
    errors=[i for i in issues if i["severity"]=="error"]
    quality="bad" if errors else "uncertain" if issues else "good"
    temporal={"policy":policy,"evaluationContext":evaluation,"inputs":rows,"skewMs":str(skew) if skew is not None else None,"inputTimestampRange":range_,"assemblyQuality":quality,"atomicSnapshot":False,"requiredSources":source_ids(state,binding) if required is None else required}
    step("assembly-time-quality","virtual",temporal,errors[0]["code"] if errors else None)
    return values,trace,issues,temporal

def check_scenario(doc,state):
    if isinstance(doc,dict) and doc.get('kind')=='object-preview-scenario':
        errors=list(vc.schema_validator('object-preview-scenario','2.21.0').iter_errors(doc))
        if errors:raise ValueError('object-preview-scenario: '+errors[0].message)
        if doc['workspaceSha256']!=digest(state):raise ValueError('Scenario workspace hash mismatch')
        if not any(dict(id=t['id'],version=t['version'])==doc['targetInstanceRef'] for t in state.get('targets',[])):raise ValueError('Scenario target reference missing')
        if doc['evaluationContext'] is not None:timestamp(doc['evaluationContext']['at'])
        for value in doc['samples'].values():
            if isinstance(value,dict) and 'value' in value:
                for key in ('sourceTimestamp','serverTimestamp'):
                    if value[key] is not None:timestamp(value[key])
                value=value['value']
            if isinstance(value,dict) and 'resultSet' in value:timestamp(value['resultSet']['capturedAt'])
        return
    errors=list(vc.schema_validator("preview-scenario",doc.get("schemaVersion") if isinstance(doc,dict) and doc.get("schemaVersion") in ("2.3.0","2.4.0","2.21.0") else "2.3.0").iter_errors(doc))
    if errors:raise ValueError("preview-scenario: "+errors[0].message)
    if doc["workspaceSha256"]!=digest(state):raise ValueError("Scenario workspace hash mismatch")
    maps=[m for m in state["mappings"] if {"id":m["id"],"version":m["version"]}==doc["mappingSetRef"]]
    if len(maps)!=1:raise ValueError("Scenario mapping reference missing")
    bs=[b for b in maps[0]["mappings"] if b["mappingId"]==doc["mappingId"]]
    if len(bs)!=1 or "temporalPolicy" not in bs[0]:raise ValueError("Scenario requires a mapping with an explicit temporalPolicy")
    for value in doc['samples'].values():
        raw=value.get('value')
        if isinstance(raw,dict) and 'resultSet' in raw:timestamp(raw['resultSet']['capturedAt'])
    # Malformed dates may satisfy string regex; enforce parseability on save too.
    timestamp(doc["evaluationContext"]["at"])
    for value in doc["samples"].values():
        for key in ("sourceTimestamp","serverTimestamp"):
            if value[key] is not None:timestamp(value[key])
