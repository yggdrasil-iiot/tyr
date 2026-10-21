"""Read-only virtual sample preview. No sockets, drivers, eval, or persistence."""
import hashlib,json,math,re,struct
from decimal import Decimal,InvalidOperation,Inexact,localcontext,ROUND_HALF_EVEN
from datetime import datetime,timezone
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
import validate_contracts as vc
import source_codecs
import fixed_arrays
import sample_quality
import mixed_sources
import source_views
import logical_structures as ls
import bounded_arithmetic as arithmetic
NUMERIC={"Int16","UInt16","Int32","UInt32","Int64","Float32","Float64","Double","Decimal"}
INTEGER={"Int16":(-32768,32767,16),"UInt16":(0,65535,16),"Int32":(-(2**31),2**31-1,32),"UInt32":(0,2**32-1,32),"Int64":(-(2**63),2**63-1,64)}
FMT={"Double":"d","Int16":"h","UInt16":"H","Int32":"i","UInt32":"I","Int64":"q","Float32":"f","Float64":"d"}
class Fault(ValueError):
    def __init__(self,code,detail=""):self.code=code;self.detail=detail
def decimal(value):
    if isinstance(value,bool) or not isinstance(value,(str,int,float,Decimal)):raise Fault("sample.numeric")
    text=str(value)
    if text.lower() in ("nan","infinity","inf","-infinity","-inf","+inf"):raise Fault("value.nonfinite")
    if len(text)>256 or not re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]{1,4})?",text):raise Fault("sample.numeric")
    d=Decimal(text)
    if not d.is_finite():raise Fault("value.nonfinite")
    if abs(d.as_tuple().exponent)>1000:raise Fault("value.numeric-limit")
    return d
def pack(value,typ,unit):return {"value":value,"type":typ,"unit":unit}
def encoded(value):return str(value) if isinstance(value,Decimal) else value
def _run_values(state,mapping_set_id,mapping_id,samples,revision):
    if not isinstance(samples,dict) or len(samples)>256:raise ValueError("samples: expected object (max 256)")
    maps=[m for m in state["mappings"] if m["id"]==mapping_set_id]
    if len(maps)!=1:raise ValueError("Missing mapping-set")
    mapping_set=maps[0];bindings=[b for b in mapping_set["mappings"] if b["mappingId"]==mapping_id]
    if len(bindings)!=1:raise ValueError("Missing mapping")
    binding=bindings[0]
    if "targetInstanceRef" in mapping_set:
        target=next(t for t in state["targets"] if t["id"]==mapping_set["targetInstanceRef"]["id"] and t["version"]==mapping_set["targetInstanceRef"]["version"])
        semref=target["semanticDefinitionRef"];memberid=binding["memberPath"][0]["memberId"];value_ref=binding["valueRef"]
    else:
        semref=mapping_set["semanticDefinitionRef"];memberid=binding["targetMemberId"];value_ref={"kind":"source","sourceRef":binding["sourceRef"]}
    model=next(m for m in state["semantics"] if m["id"]==semref["id"] and m["version"]==semref["version"])
    member=ls.resolve(model,binding["memberPath"]) if "memberPath" in binding else next(m for m in model["members"] if m["memberId"]==memberid)
    sources={(r["definition"]["id"],r["definition"]["version"]):r["definition"] for r in state["sources"]}
    graphs={(g["id"],g["version"]):g for g in state.get("graphs",[])}
    trace=[];issues=[];source_cache={};node_cache={};active=set();consumed=set();selections=[];possible=set();record_frames={}
    def issue(code,severity,stage,detail=""):
        row={"code":code,"severity":severity,"stage":stage,"detail":detail}
        if row not in issues:issues.append(row)
    def step(stage,identity,result=None,meta=None,error=None):
        row={"index":len(trace)+1,"stage":stage,"identity":identity,"status":"error" if error else "ok"}
        if result is not None:row.update(value=encoded(result["value"]),valueType=result["type"],unit=result["unit"])
        if meta:row["detail"]=meta
        if error:row["error"]=error
        trace.append(row)
    def fail(stage,identity,fault):
        issue(fault.code,"error",stage+":"+identity,fault.detail);step(stage,identity,error=fault.code)
    def source(ref,element=None):
        key=(ref["id"],ref["version"]) if element is None else (ref["id"],ref["version"],tuple(element["indices"]));id=ref["id"] if element is None else ref["id"]+str(element["indices"])
        if key in source_cache:return source_cache[key]
        s=sources.get(key) if element is None else element["source"]
        if s is None:raise Fault("reference.missing",id)
        r,a=s["rawRepresentation"],s["access"];codec=r.get("codec",{})
        try:
            static=vc.source_rules(s)
            if static:raise Fault(static[0])
            if s["status"]!="ready":raise Fault("source.not-ready")
            if mixed_sources.mode(s)=="write":raise Fault("source.not-readable")
            if s.get("viewOf") is not None:
                invalid=source_views.rules(s,sources)
                if invalid:raise Fault(invalid[0])
                if id in samples:raise Fault("sample.view-override","Supply the root source sample only")
                parent=source(s["viewOf"])
                if parent is None:raise Fault("view.parent-invalid")
                value=parent["value"];typ=parent["type"];unit=s["unit"]
                if s["view"]["kind"]=="bit":value=bool(int(value)&(1<<s["view"]["bitIndex"]));typ="Boolean"
                result=pack(value,typ,unit);result["inputStage"]=s["inputStage"]
                step("view:"+s["view"]["kind"],id,result,{"viewOf":s["viewOf"],"view":s["view"],"rootSource":source_views.chain(s,sources)[-1]["id"]})
                source_cache[key]=result;return result
            constant=mixed_sources.kind(s)=="constant"
            if constant:
                if ref["id"] in samples:raise Fault("sample.constant-override")
                sample={"typedValue":s["access"]["value"]}
                step("constant-definition",id,meta={"definitionValue":s["access"]["value"],"sourceRef":ref,"evidenceRefs":s["evidenceRefs"]})
            else:
                consumed.add(ref["id"])
                sample=samples.get(ref["id"]) if element is None else element["sample"]
            if s.get('recordField') is not None:
                import record_field_preview
                try:sample,provenance=record_field_preview.resolve(state,s,sample)
                except ValueError as e:raise Fault(str(e),id)
                frame=sample_quality.digest(provenance['recordMappingRef']);prior=record_frames.get(frame)
                if prior is not None and prior!=provenance['inputSha256']:raise Fault('record-field.snapshot-conflict',id)
                record_frames[frame]=provenance['inputSha256']
                step('record-field-select',id,meta=provenance)
                if provenance['defaultUsed']:issue('record-field.default-used','warning',id,'Explicit nullable field default')
                if provenance['quality']=='uncertain':issue('record-field.uncertain-quality','warning',id,'Virtual result-set quality')
            if not isinstance(sample,dict):raise Fault("sample.missing",id)
            if not constant:consumed.add(ref["id"])
            typ=r["valueType"];unit=s["unit"]
            if "fixedArray" in s:
                layout=fixed_arrays.validate_sample(s,sample)
                result=pack(None,"FixedArray",unit);result.update(inputStage=s["inputStage"],arraySource=s,arraySample=sample,arraySourceRef=ref)
                step("array-input",id,result,{"layout":layout,"sampleMode":"typedValues" if r["mode"]=="typed" else "bytesHex"})
                source_cache[key]=result;return result
            if r["mode"]=="typed":
                if set(sample)!={"typedValue"}:raise Fault("sample.mode","typedValue required")
                if typ=="Boolean":
                    if type(sample["typedValue"]) is not bool:raise Fault("sample.boolean")
                    value=sample["typedValue"]
                elif typ=="String":
                    if not isinstance(sample["typedValue"],str) or len(sample["typedValue"])>4096:raise Fault("sample.string")
                    value=sample["typedValue"]
                else:
                    value=decimal(sample["typedValue"])
                    if typ in INTEGER and (value!=value.to_integral_value() or not INTEGER[typ][0]<=value<=INTEGER[typ][1]):raise Fault("sample.type-range")
                    if typ in ("Float32","Float64") or (typ=="Double" and mixed_sources.nonplc(s)):
                        try:f=struct.unpack(">"+FMT[typ],struct.pack(">"+FMT[typ],float(value)))[0]
                        except (OverflowError,struct.error):raise Fault("value.overflow")
                        if not math.isfinite(f):raise Fault("value.overflow")
                        binary=Decimal.from_float(f)
                        if binary!=value:
                            issue("loss.input-precision","loss","input:"+id,"Declared decimal quantized to "+typ)
                            if binary==0 and value!=0:issue("loss.underflow","loss","input:"+id,"Nonzero input rounded to zero")
                        value=binary
                result=pack(value,typ,unit);step("typed-input",id,result,{"sample":sample["typedValue"],"sourceKind":mixed_sources.kind(s),"accessMode":mixed_sources.mode(s),"execution":"definition-value" if constant else "virtual-input-only","access":s["access"]})
            else:
                if set(sample)!={"bytesHex"} or not isinstance(sample["bytesHex"],str):raise Fault("sample.mode","bytesHex required")
                text=sample["bytesHex"]
                if len(text)>8192 or not re.fullmatch(r"[0-9a-fA-F\s]*",text):raise Fault("sample.hex")
                try:data=bytes.fromhex(text)
                except ValueError:raise Fault("sample.hex")
                width=source_codecs.storage_width(s)
                step("raw-bytes",id,meta={"bytesHex":data.hex(),"byteLength":len(data),"expectedLength":width})
                if width is None or len(data)!=width:raise Fault("sample.width","expected "+str(width)+" bytes")
                if codec.get("kind") in ("ascii-fixed","s7-date-time"):
                    ordered=data
                    step("byte-layout",id,meta={"policy":"codec wire order; no numeric byte/word shuffle","bytesHex":ordered.hex()})
                else:
                    words=[data[i:i+2] for i in range(0,len(data),2)]
                    if r["wordOrder"]=="low-first":words.reverse()
                    ordered=b"".join(w[::-1] if r["byteOrder"]=="little" else w for w in words)
                    step("byte-layout",id,meta={"byteOrder":r["byteOrder"],"wordOrder":r["wordOrder"],"orderedBigEndianHex":ordered.hex()})
                if typ=="Boolean":
                    if ordered not in (b"\x00",b"\x01"):raise Fault("sample.boolean-carrier")
                    value=ordered==b"\x01"
                elif typ=="String":value=None
                else:
                    v=struct.unpack(">"+FMT[typ],ordered)[0]
                    if isinstance(v,float) and not math.isfinite(v):raise Fault("value.nonfinite")
                    value=Decimal.from_float(v) if isinstance(v,float) else Decimal(v)
                if typ!="String":step("decode",id,pack(value,typ,unit))
                kind=codec.get("kind")
                if kind=="bcd16":
                    n=int(value);digits=[(n>>shift)&15 for shift in (12,8,4,0)]
                    if any(d>9 for d in digits):raise Fault("value.bcd-digit")
                    value=Decimal(sum(d*10**(3-i) for i,d in enumerate(digits)));typ="Int32"
                    step("codec:bcd16",id,pack(value,typ,unit))
                elif kind=="ascii-fixed":
                    payload=ordered
                    if codec["termination"]=="nul":
                        pos=payload.find(b"\x00")
                        if pos>=0:
                            tail=payload[pos+1:];payload=payload[:pos]
                            if any(tail):issue("loss.truncation","loss","codec:"+id,"Nonzero bytes after NUL: "+tail.hex())
                    try:value=payload.decode("ascii")
                    except UnicodeDecodeError:raise Fault("value.ascii")
                    step("codec:ascii-fixed",id,pack(value,"String",unit),{"rawPreserved":data.hex(),"payloadBytes":len(payload),"termination":codec["termination"]})
                elif kind=="s7-date-time":
                    def bcd(b):
                        if b>>4>9 or b&15>9:raise Fault("value.bcd-digit")
                        return (b>>4)*10+(b&15)
                    year,month,day,hour,minute,second=[bcd(b) for b in ordered[:6]]
                    ms=bcd(ordered[6])*10+(ordered[7]>>4);weekday=ordered[7]&15
                    if ordered[7]>>4>9 or not 1<=weekday<=7:raise Fault("value.date-fields")
                    if codec["timezone"] is None:raise Fault("source.timezone-required")
                    try:zone=ZoneInfo(codec["timezone"])
                    except ZoneInfoNotFoundError:raise Fault("source.timezone-unavailable")
                    try:local=datetime(1900+year if year>=90 else 2000+year,month,day,hour,minute,second,ms*1000,tzinfo=zone)
                    except ValueError:raise Fault("value.date-fields")
                    if (local.isoweekday()%7)+1!=weekday:raise Fault("value.weekday")
                    value=local.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
                    step("codec:s7-date-time",id,pack(value,"String",unit),{"local":local.isoformat(timespec="milliseconds"),"timezone":codec["timezone"],"rawPreserved":data.hex()})
                bit=a.get("bitOffset")
                if bit is not None:
                    coord=r.get("bitCoordinate",{"kind":"decoded-value"})
                    if coord["kind"]=="native-byte":value=bool(data[coord["byteIndex"]]&(1<<bit))
                    else:
                        if typ not in INTEGER:raise Fault("source.bit-coordinate")
                        value=bool(int(value)&(1<<bit))
                    typ="Boolean";unit={"status":"not-applicable"}
                    step("bit-access",id,pack(value,typ,unit),{"coordinate":coord,"bitOffset":bit,"legacyDefault":s["schemaVersion"]!="2.1.0"})
                result=pack(value,typ,unit)
            if s["unit"]["status"]=="unknown":issue("input.unit-unknown","warning","source:"+id,"Original unknown unit retained")
            result["inputStage"]=s["inputStage"]
            source_cache[key]=result;return result
        except fixed_arrays.ArrayError as e:
            fail("source",id,Fault(e.code,e.detail));source_cache[key]=None;return None
        except Fault as f:
            fail("source",id,f);source_cache[key]=None;return None
    def candidate_lineage(graph_ref,ep,runtime=False):
        definitions={};roots={};visiting=set();done=set()
        def visit(endpoint,current_ref):
            if endpoint['kind']=='source':
                ref=endpoint['sourceRef'];roots[json.dumps(ref,sort_keys=True)]=ref;return
            target=endpoint.get('graphRef',current_ref);key=(target['id'],target['version'],endpoint['nodeId'])
            if key in visiting:raise Fault('graph.cycle')
            if key in done:return
            if len(done)+len(visiting)>=8192:raise Fault('graph.dependency-size')
            g=graphs.get(key[:2])
            if g is None:raise Fault('reference.missing')
            matches=[n for n in g['nodes'] if n['nodeId']==key[2]]
            if len(matches)!=1:raise Fault('graph.node-missing')
            visiting.add(key);n=matches[0];inputs=n['inputs']
            label=key[2] if target==graph_ref else key[0]+'@'+key[1]+'/'+key[2]
            definitions[label]=n
            if runtime and n['op']=='bounded-selector':
                selection=next((v for v in reversed(selections) if v['selector']==g['id']+'/'+key[2]),None)
                if selection:inputs={k:v for k,v in inputs.items() if not k.startswith('candidate') or k=='candidate'+str(selection['selectedIndex'])}
            for value in inputs.values():visit(value,target)
            visiting.remove(key);done.add(key)
        visit(ep,graph_ref)
        tree=ep if ep['kind']=='source' else {'graphRef':graph_ref,'output':ep,'nodes':definitions}
        return [roots[k] for k in sorted(roots)],tree
    def candidate_info(graph_ref,ep):
        refs,tree=candidate_lineage(graph_ref,ep)
        definition=sources[(ep["sourceRef"]["id"],ep["sourceRef"]["version"])] if ep["kind"]=="source" else next(n for n in graphs[(ep.get("graphRef",graph_ref)["id"],ep.get("graphRef",graph_ref)["version"])]["nodes"] if n["nodeId"]==ep["nodeId"])
        typ=source_views.value_type(definition,sources) if ep["kind"]=="source" else definition["valueType"]
        return {"candidateRef":ep,"valueType":typ,"unit":definition["unit"],"sourceRefs":refs,"definitionSha256":hashlib.sha256(json.dumps(tree,sort_keys=True,separators=(",",":")).encode()).hexdigest()}
    def node(graph_ref,node_id):
        key=(graph_ref["id"],graph_ref["version"],node_id)
        if key in node_cache:return node_cache[key]
        if key in active:raise Fault("graph.cycle")
        active.add(key);id=graph_ref["id"]+"/"+node_id
        try:
            g=graphs.get((graph_ref["id"],graph_ref["version"]))
            if g is None:raise Fault("reference.missing")
            ns=[n for n in g["nodes"] if n["nodeId"]==node_id]
            if len(ns)!=1:raise Fault("graph.node-missing")
            n=ns[0];values={}
            if n["op"]=="bounded-selector":
                candidates=[n["inputs"]["candidate"+str(i)] for i in range(sum(k.startswith("candidate") for k in n["inputs"]))]
                possible.update(source_views.root_ids(state,[ref["id"] for ep in n["inputs"].values() for ref in candidate_lineage(graph_ref,ep)[0]]))
                def read_index(name):
                    v=source(n["inputs"][name]["sourceRef"])
                    if v is None:raise Fault("selector.index-invalid",name)
                    if v["type"] not in INTEGER or v["unit"]!={"status":"known","code":"1"} or isinstance(v["value"],bool) or v["value"]!=v["value"].to_integral_value():raise Fault("selector.index-type",name)
                    return int(v["value"])
                def choose(i):
                    if 0<=i<len(candidates):return i,False
                    if n["outOfRange"]=="default-candidate":return n["defaultCandidate"],True
                    raise Fault("selector.out-of-range",str(i))
                requested=read_index("index");selected,fallback=choose(requested);previous=None
                if "previousIndex" in n["inputs"]:previous=choose(read_index("previousIndex"))[0]
                ep=candidates[selected];result=source(ep["sourceRef"]) if ep["kind"]=="source" else node(ep.get("graphRef",graph_ref),ep["nodeId"])
                if ep['kind']=='graph':step('graph:reference',id+'/candidate'+str(selected),result,{'graphRef':ep['graphRef'],'nodeId':ep['nodeId']})
                current=candidate_info(graph_ref,ep);prior=None if previous is None else candidate_info(graph_ref,candidates[previous])
                detail={"selector":id,"requestedIndex":requested,"selectedIndex":selected,"sourceRef":ep.get("sourceRef"),"defaultUsed":fallback,"previousSourceRef":None if previous is None else candidates[previous].get("sourceRef"),"sourceChanged":None if prior is None else current!=prior,"candidateCount":len(candidates),
                    **current,"previousCandidate":prior,"selectedSourceRefs":candidate_lineage(graph_ref,ep,True)[0],"previousLineageMode":"definition-only","candidateChanged":None if prior is None else current["candidateRef"]!=prior["candidateRef"],
                    "candidates":[{"index":i,"selected":i==selected,"timeQualityAssessment":"value-only" if i==selected else "not-evaluated",**candidate_info(graph_ref,e)} for i,e in enumerate(candidates)]}
                selections.append(detail)
                if fallback:issue("selector.default-used","warning",id,"Explicit default candidate")
                if detail["sourceChanged"]:issue("selector.source-changed","warning",id,"Candidate reference or calculation definition differs from explicit previous selection")
                if result is None:raise Fault("selector.selected-invalid")
                if result["type"]!=n["valueType"]:raise Fault("selector.candidate-type")
                if result["unit"]!=n["unit"]:raise Fault("selector.candidate-unit")
                step("graph:bounded-selector",id,result,detail)
                node_cache[key]=result;return result
            for name,endpoint in n["inputs"].items():
                values[name]=source(endpoint["sourceRef"]) if endpoint["kind"]=="source" else node(endpoint.get("graphRef",graph_ref),endpoint["nodeId"])
                if endpoint['kind']=='graph':step('graph:reference',id+'/'+name,values[name],{'graphRef':endpoint['graphRef'],'nodeId':endpoint['nodeId']})
            if any(v is None for v in values.values()):raise Fault("graph.input-invalid")
            if n["op"]=="decode-u32-words":
                if set(values)!={"low","high"} or any(v["type"]!="UInt16" or v.get("inputStage")!="raw" or v["unit"]!={"status":"not-applicable"} or isinstance(v["value"],bool) or not 0<=v["value"]<=65535 for v in values.values()):raise Fault("graph.input-type")
                value=Decimal(int(values["low"]["value"])+(int(values["high"]["value"])<<16))
                result=pack(value,"UInt32",n["unit"])
                step("graph:decode-u32-words",id,result,{"low":encoded(values["low"]["value"]),"high":encoded(values["high"]["value"]),"formula":"low | (high << 16)"})
            elif n["op"]=="array-element":
                parent=values["value"]
                if parent["type"]!="FixedArray":raise Fault("array.input-type")
                scalar,payload,detail=fixed_arrays.select(parent["arraySource"],parent["arraySample"],n["indices"])
                step("array-index",id,meta=detail)
                result=source(parent["arraySourceRef"],{"source":scalar,"sample":payload,"indices":n["indices"]})
                if result is None:raise Fault("graph.input-invalid")
                if result["type"]!=n["valueType"] or result["unit"]!=n["unit"]:raise Fault("graph.output-type")
                step("graph:array-element",id,result,detail)
            elif n["op"]=="identity":
                result=values["value"]
                if result["type"]!=n["valueType"] or result["unit"]!=n["unit"]:raise Fault("graph.output-type")
                step("graph:identity",id,result)
            elif n["op"] in arithmetic.OPS:
                if g["schemaVersion"] not in ("2.15.0","2.17.0"):raise Fault("arithmetic.schema-version")
                if set(values)!={"left","right"} or any(v["type"] not in NUMERIC for v in values.values()):raise Fault("graph.input-type")
                if n["valueType"]!="Decimal":raise Fault("graph.output-type")
                left,right=values["left"],values["right"]
                try:
                    unit=arithmetic.unit_for(n["op"],left["unit"],right["unit"])
                    value,approximate=arithmetic.calculate(n["op"],left["value"],right["value"],n.get("precision"),n.get("rounding"))
                except ValueError as e:raise Fault(str(e))
                if unit!=n["unit"]:raise Fault("graph.output-unit")
                if approximate:issue("loss.precision","loss","graph:divide","precision=34; rounding=half-even; approximate=true")
                result=pack(value,"Decimal",unit);result["inputStage"]="derived"
                step("graph:"+n["op"],id,result,{"inputs":{k:{"value":encoded(v["value"]),"valueType":v["type"],"unit":v["unit"]} for k,v in values.items()},"definition":n,"approximate":approximate,"precision":34 if n["op"]=="divide" else 4096,"rounding":"half-even"})
            elif n["op"] in ("sqrt","clamp"):
                first=values["value"];unit=first["unit"];value=first["value"]
                if first["type"] not in NUMERIC:raise Fault("graph.input-type")
                if n["valueType"]!="Decimal":raise Fault("graph.output-type")
                if unit.get("status")!="known" or (n["op"]=="sqrt" and unit!={"status":"known","code":"1"}):raise Fault("graph.input-unit")
                if unit!=n["unit"]:raise Fault("graph.output-unit")
                ctx.clear_flags()
                meta={"definition":n,"input":encoded(value)}
                if n["op"]=="sqrt":
                    if n.get("precision")!=34 or n.get("rounding")!="half-even":raise Fault("value.sqrt-policy")
                    if value<0:raise Fault("value.sqrt-domain")
                    with localcontext() as mathctx:
                        mathctx.prec=34;mathctx.rounding=ROUND_HALF_EVEN;mathctx.clear_flags()
                        value=value.sqrt();approximate=mathctx.flags[Inexact]
                    meta.update(precision=34,rounding="half-even",approximate=approximate)
                    if approximate:issue("loss.precision","loss","graph:sqrt","input="+meta["input"]+"; precision=34; rounding=half-even; approximate=true")
                else:
                    low,high=decimal(n["low"]),decimal(n["high"])
                    if low>high:raise Fault("graph.clamp-range")
                    branch="low" if value<low else "high" if value>high else "pass"
                    value=low if branch=="low" else high if branch=="high" else value
                    meta.update(low=encoded(low),high=encoded(high),branch=branch)
                    if branch!="pass":issue("loss.clamp","loss","graph:clamp","before="+meta["input"]+"; bounds=["+str(low)+", "+str(high)+"]; after="+str(value)+"; branch="+branch)
                result=pack(value,"Decimal",unit);result["inputStage"]="derived"
                step("graph:"+n["op"],id,result,meta)
            elif n["op"] in ("subtract","linear","unit-convert"):
                if any(v["type"] not in NUMERIC for v in values.values()):raise Fault("graph.input-type")
                if n["valueType"]!="Decimal":raise Fault("graph.output-type")
                ctx.clear_flags()
                first=next(iter(values.values()));unit=first["unit"]
                if n["op"]=="subtract":
                    if set(values)!={"left","right"}:raise Fault("graph.input-type")
                    if any(v["unit"]!=unit for v in values.values()) or unit.get("code") not in ("Pa","kPa","bar","1"):raise Fault("graph.input-unit")
                    value=values["left"]["value"]-values["right"]["value"]
                elif n["op"]=="linear":
                    factor,offset=decimal(n["factor"]),decimal(n["offset"])
                    if first.get("inputStage")=="already-engineered" and (factor!=1 or offset!=0):raise Fault("mapping.double-transform")
                    value=first["value"]*factor+offset
                else:
                    if unit!={"status":"known","code":n["from"]} or (n["from"],n["to"]) not in vc.UNIT_CONVERSIONS:raise Fault("graph.input-unit")
                    factor,offset=map(Decimal,vc.UNIT_CONVERSIONS[(n["from"],n["to"])])
                    value=first["value"]*factor+offset;unit={"status":"known","code":n["to"]}
                if unit!=n["unit"] or unit["status"]!="known":raise Fault("graph.output-unit")
                if ctx.flags[Inexact]:raise Fault("value.numeric-limit")
                result=pack(value,"Decimal",unit);result["inputStage"]="derived"
                step("graph:"+n["op"],id,result,{"inputs":{k:{"value":encoded(v["value"]),"valueType":v["type"],"unit":v["unit"]} for k,v in values.items()},"definition":n})
            else:raise Fault("operation.unsupported")
            node_cache[key]=result;return result
        except fixed_arrays.ArrayError as e:fail("graph",id,Fault(e.code,e.detail));node_cache[key]=None;return None
        except Fault as f:fail("graph",id,f);node_cache[key]=None;return None
        finally:active.remove(key)
    failure_stage="mapping";failure_id=mapping_id
    with localcontext() as ctx:
        ctx.prec=4096
        try:
            current=source(value_ref["sourceRef"]) if value_ref["kind"]=="source" else node(value_ref["graphRef"],value_ref["nodeId"])
            if current is None:raise Fault("mapping.input-invalid")
            input_engineered=current.get("inputStage")=="already-engineered"
            for index,t in enumerate(binding["transform"]):
                id=mapping_id+"/"+str(index+1);op=t["op"];failure_stage="transform:"+op;failure_id=id;value,typ,unit=current["value"],current["type"],current["unit"];ctx.clear_flags()
                step("transform-input",id,current,{"op":op,"definition":t})
                if op in ("linear","unit-convert"):
                    if typ not in NUMERIC:raise Fault("transform.input")
                    if op=="linear":
                        factor,offset=decimal(t["factor"]),decimal(t["offset"])
                        if input_engineered and (factor!=1 or offset!=0):raise Fault("mapping.double-transform")
                    else:
                        pair=(t["from"],t["to"])
                        if pair not in vc.UNIT_CONVERSIONS or unit!={"status":"known","code":t["from"]}:raise Fault("transform.unit")
                        factor,offset=map(Decimal,vc.UNIT_CONVERSIONS[pair]);unit={"status":"known","code":t["to"]}
                    value=value*factor+offset;typ="Decimal"
                elif op=="bit-select":
                    if typ not in INTEGER or not 0<=t["index"]<INTEGER[typ][2]:raise Fault("transform.bit")
                    value=bool(int(value)&(1<<t["index"]));typ="Boolean";unit={"status":"not-applicable"}
                elif op=="enum-map":
                    if typ not in NUMERIC:raise Fault("transform.input")
                    matches=[e["value"] for e in t["entries"] if decimal(e["raw"])==value]
                    if not matches:raise Fault("value.enum-unknown")
                    if len(matches)!=1:raise Fault("transform.enum-duplicate")
                    value=matches[0];typ="String";unit={"status":"not-applicable"}
                elif op=="cast":
                    dest=t["to"]
                    if dest=="Int32":
                        if typ not in NUMERIC:raise Fault("transform.input")
                        rounded=value.to_integral_value(rounding=ROUND_HALF_EVEN)
                        if rounded!=value:
                            issue("loss.rounding","loss","cast:"+id,"before="+str(value)+"; after="+str(rounded))
                            if t["rounding"]=="exact":raise Fault("value.inexact")
                        if not -(2**31)<=rounded<=2**31-1:raise Fault("value.overflow")
                        value=rounded
                    elif dest=="Double":
                        if typ not in NUMERIC:raise Fault("transform.input")
                        try:f=float(value)
                        except OverflowError:raise Fault("value.overflow")
                        if not math.isfinite(f):raise Fault("value.overflow")
                        binary=Decimal.from_float(f)
                        if binary!=value:
                            issue("loss.precision","loss","cast:"+id,"before="+str(value)+"; exact binary64="+str(binary))
                            if binary==0 and value!=0:issue("loss.underflow","loss","cast:"+id,"Nonzero Decimal rounded to zero")
                            if t["rounding"]=="exact":raise Fault("value.inexact")
                        value=binary
                    elif dest not in ("String","Boolean") or typ!=dest:raise Fault("transform.input")
                    typ=dest
                else:raise Fault("operation.unsupported")
                if ctx.flags[Inexact]:raise Fault("value.numeric-limit","Decimal intermediate precision limit")
                current=pack(value,typ,unit);step("transform:"+op,id,current)
            failure_stage="canonical-result";failure_id=mapping_id
            if current["type"]!=member["valueType"]:raise Fault("mapping.type")
            if binding["outputUnit"]!=member["unit"]:raise Fault("mapping.unit")
            if current["unit"]["status"]!="unknown" and current["unit"]!=binding["outputUnit"]:raise Fault("mapping.unit-conversion-required")
            current=pack(current["value"],current["type"],binding["outputUnit"])
            bounds=member["range"]
            if bounds and isinstance(current["value"],Decimal) and not decimal(bounds["low"])<=current["value"]<=decimal(bounds["high"]):raise Fault("value.range")
            step("canonical-result",mapping_id,current)
        except Fault as f:fail(failure_stage,failure_id,f);current=None
        except (InvalidOperation,OverflowError,KeyError,TypeError,struct.error) as f:
            fail("mapping",mapping_id,Fault("preview.invalid-definition",type(f).__name__));current=None
    for id in sorted(set(samples)-consumed-possible):issue("sample.unused","warning","input:"+id,"Not used by selected binding")
    errors=[i for i in issues if i["severity"]=="error"];losses=[i for i in issues if i["severity"]=="loss"]
    return {"revision":revision,"mappingSetId":mapping_set_id,"mappingId":mapping_id,
        "workspaceSha256":hashlib.sha256(json.dumps(state,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False).encode()).hexdigest(),
        "sampleSha256":hashlib.sha256(json.dumps(samples,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False).encode()).hexdigest(),
        "quality":"bad" if errors else "uncertain" if issues else "good","result":None if current is None else {"value":encoded(current["value"]),"valueType":current["type"],"unit":current["unit"]},
        "requiredSources":sorted(consumed),"selections":selections,"trace":trace,"issues":issues,"losses":losses,"deviceCommunication":"excluded","persisted":False}

def run(state,mapping_set_id,mapping_id,samples,revision,evaluation=None):
    import graph_reuse
    graph_reuse.order(state.get('graphs',[]))
    if not isinstance(samples,dict) or len(samples)>256:raise ValueError("samples: expected object (max 256)")
    maps=[m for m in state["mappings"] if m["id"]==mapping_set_id]
    if len(maps)!=1:raise ValueError("Missing mapping-set")
    bindings=[b for b in maps[0]["mappings"] if b["mappingId"]==mapping_id]
    if len(bindings)!=1:raise ValueError("Missing mapping")
    binding=bindings[0]
    if "temporalPolicy" not in binding:
        if evaluation is not None:raise ValueError("evaluationContext requires an explicit temporalPolicy")
        return _run_values(state,mapping_set_id,mapping_id,samples,revision)
    required=None
    if any(n["op"]=="bounded-selector" for g in state.get("graphs",[]) for n in g["nodes"]):
        raw={k:v.get("value") if isinstance(v,dict) else None for k,v in samples.items()}
        probe=_run_values(state,mapping_set_id,mapping_id,raw,revision)
        required=probe["requiredSources"]
    values,temporal_trace,temporal_issues,temporal=sample_quality.assess(state,binding,samples,evaluation,required)
    if any(i["severity"]=="error" for i in temporal_issues):
        report={"revision":revision,"mappingSetId":mapping_set_id,"mappingId":mapping_id,"workspaceSha256":sample_quality.digest(state),"result":None,"trace":[],"issues":[],"losses":[],"quality":"bad","deviceCommunication":"excluded","persisted":False}
        if required is not None:
            report["selections"]=probe["selections"]
            report["selectionValueValidated"]=False
            report["trace"]=[{"stage":"selector-resolution","identity":d["selector"],"status":"ok","detail":d} for d in probe["selections"]]
            report["issues"]=[i for i in probe["issues"] if i["code"] in ("selector.default-used","selector.source-changed")]
    else:
        # Extra samples retain the legacy unused warning, but cannot affect the assembly.
        for id in set(samples)-set(temporal["requiredSources"]):values[id]=samples[id].get("value") if isinstance(samples[id],dict) else None
        report=_run_values(state,mapping_set_id,mapping_id,values,revision)
    report["trace"]=temporal_trace+report["trace"]
    report["issues"]=temporal_issues+report["issues"]
    for index,row in enumerate(report["trace"],1):row["index"]=index
    report["quality"]="bad" if any(i["severity"]=="error" for i in report["issues"]) else "uncertain" if report["issues"] else "good"
    if report["quality"]=="bad":report["result"]=None
    report["sampleSha256"]=sample_quality.digest(samples)
    report["evaluationSha256"]=sample_quality.digest({"samples":samples,"evaluationContext":evaluation})
    report["temporal"]=temporal
    for selection in report.get("selections",[]):
        selected_ids=set(source_views.root_ids(state,[r["id"] for r in selection["selectedSourceRefs"]]))
        selection["selectedInputDataValues"]=[row for row in temporal["inputs"] if row["sourceId"] in selected_ids]
        for candidate in selection["candidates"]:
            candidate["selected"]=candidate["index"]==selection["selectedIndex"]
            candidate["timeQualityAssessment"]="selected-path" if candidate["selected"] else "not-evaluated"

    report["dataValue"]={"quality":report["quality"],"sourceTimestamp":None,"serverTimestamp":None,"evaluatedAt":evaluation.get("at") if isinstance(evaluation,dict) else None,"inputTimestampRange":temporal["inputTimestampRange"],"sequence":evaluation.get("triggerSequence") if isinstance(evaluation,dict) and binding["temporalPolicy"]["assembly"]=="trigger-sequence" else None,"atomicSnapshot":False}
    return report
