"""P3-A 2.0 authoring-contract gate. File-only, no device or approval execution."""
import argparse, copy, json, sys, tempfile, shutil
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone
import validate_contracts as vc
import source_codecs
import fixed_arrays
import mixed_sources
import source_views
import logical_structures as ls
import bounded_arithmetic as arithmetic
import graph_reuse
import semantic_lifecycle
import mapping_templates
import record_mappings
ROOT=vc.ROOT
NEW={"mapping-proposal","mapping-set","target-instance","value-graph"}
OLD={"source-definition","semantic-definition","evidence-artifact","source-observation"}
NUMERIC={"Int16","UInt16","Int32","UInt32","Int64","Float32","Float64","Double","Decimal"}
INTEGER={"Int16":16,"UInt16":16,"Int32":32,"UInt32":32,"Int64":64}
def schema_errors(kind,doc):
    v=doc.get("schemaVersion")
    if v=='2.22.0' and kind in ('mapping-proposal','record-mapping'):return list(vc.schema_validator(kind,v).iter_errors(doc))
    if v=="2.21.0" and kind in ("source-definition","mapping-proposal"):return list(vc.schema_validator(kind,v).iter_errors(doc))
    if v=="2.20.0" and kind in ("mapping-proposal","record-mapping","virtual-result-set"):return list(vc.schema_validator(kind,v).iter_errors(doc))
    if v=="2.19.0" and kind in ("mapping-proposal","mapping-template","template-application"):return list(vc.schema_validator(kind,v).iter_errors(doc))
    if v=="2.18.0" and kind in ("mapping-proposal","semantic-lifecycle"):return list(vc.schema_validator(kind,v).iter_errors(doc))
    if kind=="import-batch" and v=="2.14.0":return list(vc.schema_validator(kind,v).iter_errors(doc))
    if v=="2.12.0" and kind in ("semantic-definition","mapping-set"):
        if kind=="semantic-definition":
            try:ls.preflight(doc)
            except ls.StructureError as e:return [e]
        return list(vc.schema_validator(kind,v).iter_errors(doc))
    if (kind in ("mapping-proposal","write-definition") and v=="2.7.0"):return list(vc.schema_validator(kind,v).iter_errors(doc))
    if (kind in ("mapping-proposal","import-batch") and v=="2.6.0") or (kind in NEW and v=="2.0.0") or (kind in ("value-graph","mapping-set") and v=="2.2.0") or (kind=="mapping-set" and v=="2.3.0") or (kind in ("mapping-set","value-graph") and v=="2.4.0") or (kind=="value-graph" and v in ("2.5.0","2.11.0","2.13.0","2.15.0","2.17.0")):return list(vc.schema_validator(kind,v).iter_errors(doc))
    if kind in OLD and (v in ("1.0.0","1.1.0") or (kind=="source-definition" and v=="2.1.0") or (kind in ("source-definition","semantic-definition") and v=="2.2.0") or (kind=="source-definition" and v in ("2.4.0","2.7.0","2.10.0"))):return vc.validate_schema(kind,doc)
    return ["unsupported kind/schemaVersion"]
def validate_package(root):
    root=Path(root);errors=[];signatures={};lineage={}
    def add(rule,path=None):errors.append({"ruleCode":rule,"path":path})
    try:proposal=vc.load(root/"proposal.json")
    except (OSError,ValueError):return [{"ruleCode":"bundle.unreadable","path":"proposal.json"}],{}
    if schema_errors("mapping-proposal",proposal):return [{"ruleCode":"schema","path":"proposal.json"}],{}
    docs={};paths=set()
    for e in proposal["files"]:
        key=(e["kind"],e["id"],e["version"])
        if e["path"] in paths:add("bundle.duplicate-path",e["path"])
        if key in docs:add("bundle.duplicate-id",e["path"])
        paths.add(e["path"])
        try:
            p=vc.safe(root,e["path"])
            if vc.hashed(p)!=e["sha256"]:add("bundle.digest",e["path"])
            d=vc.load(p)
            if schema_errors(e["kind"],d):add("schema",e["path"]);continue
            if (d["kind"],d["id"],d["version"])!=key:add("bundle.identity",e["path"])
            docs[key]=d
        except (OSError,ValueError):add("bundle.unreadable",e["path"])
    if any(d.get('schemaVersion')=='2.21.0' for d in docs.values()):
        if proposal['schemaVersion'] not in ('2.21.0','2.22.0'):add('record-field.envelope','proposal.json')
        try:
            import record_fields
            record_fields.validate(docs.values())
        except ValueError as e:add(str(e),'record-field')
    if any(d.get('schemaVersion')=='2.22.0' for d in docs.values()) and proposal['schemaVersion']!='2.22.0':add('broadcast.envelope','proposal.json')
    if errors:return errors,{}
    def resolve(kind,ref,path):
        d=docs.get((kind,ref["id"],ref["version"]))
        if d is None:add("reference.missing",path)
        return d
    evs=[d for d in docs.values() if d["kind"]=="evidence-artifact"]
    if len({d["id"] for d in evs})!=len(evs):add("evidence.ambiguous")
    ev={d["id"]:d for d in evs};xlsx_cache={}
    def evidence(refs,path):
        for ref in refs:
            art=ev.get(ref["artifactId"])
            if art is None:add("evidence.missing",path);continue
            try:
                p=vc.safe(root,art["file"]["path"]);loc=ref["locator"]
                if loc["kind"]=="text-line":
                    if loc["line"]>len(p.read_text(encoding="utf-8").splitlines()):add("evidence.locator",path)
                elif loc["kind"]=="json-pointer":
                    x=vc.load(p)
                    if loc["pointer"]:
                        for part in loc["pointer"][1:].split("/"):
                            part=part.replace("~1","/").replace("~0","~")
                            x=x[int(part)] if isinstance(x,list) else x[part]
                elif loc["kind"]=="xlsx-cell":
                    import import_files
                    if p not in xlsx_cache:xlsx_cache[p]=import_files.xlsx(p.read_bytes())[1]
                    if (loc["sheet"],loc["cell"]) not in xlsx_cache[p]:add("evidence.locator",path)
                else:add("evidence.locator-unsupported",path)
            except (OSError,ValueError,KeyError,IndexError,TypeError):add("evidence.locator",path)
    if any(d["kind"]=="semantic-lifecycle" for d in docs.values()):
        try:
            _,le=semantic_lifecycle.validate(list(docs.values())+record_mappings.governance(docs.values()))
            errors.extend({"ruleCode":e["ruleCode"],"path":e["path"]} for e in le)
        except ValueError as e:add(str(e),"semantic-lifecycle")
    if any(d["kind"]=="record-mapping" for d in docs.values()):
        try:record_mappings.validate(docs.values(),root=root)
        except ValueError as e:add(str(e),"record-mapping")
    if any(d["kind"] in mapping_templates.KINDS for d in docs.values()):
        try:mapping_templates.validate(docs.values())
        except ValueError as e:add(str(e),"mapping-template")
    concepts={};targets={};members={}
    for key,d in docs.items():
        path=d["kind"]+":"+d["id"]
        if "evidenceRefs" in d:evidence(d["evidenceRefs"],path)
        if d["kind"]=="evidence-artifact":
            try:
                if vc.hashed(vc.safe(root,d["file"]["path"]))!=d["file"]["sha256"]:add("evidence.digest",path)
            except (OSError,ValueError):add("evidence.unreadable",path)
        elif d["kind"]=="import-batch":
            import import_files,base64
            try:
                import_files.check({"imports":[x for x in docs.values() if x["kind"]=="import-batch"],"sources":[]})
                art=ev["import-"+d["id"]]
                if art["file"]["sha256"]!=d["sha256"] or vc.safe(root,art["file"]["path"]).read_bytes()!=base64.b64decode(d["bytesBase64"],validate=True):add("import.evidence-mismatch",path)
            except (ValueError,KeyError,OSError):add("import.provenance-mismatch",path)
            import import_workflow
            if import_workflow.unresolved(d):add("import.unresolved",path)
        elif d["kind"]=="source-definition":
            for rule in vc.source_rules(d):add(rule,path)
            if d["status"]!="ready":add("source.not-ready",path)
            for rule in source_views.rules(d,source_views.index(x for x in docs.values() if x["kind"]=="source-definition")):add(rule,path)
        elif d["kind"]=="semantic-definition":
            try:definition_nodes=ls.layout(d)["definitions"]
            except ls.StructureError as e:add(e.code,path);definition_nodes=[]
            for m in definition_nodes:
                sig=ls.signature(m)
                if m["semanticId"] in concepts and concepts[m["semanticId"]]!=sig:add("semantic.identity-conflict",path)
                concepts[m["semanticId"]]=sig
                if m["valueType"] in ls.CONTAINERS:continue
                if m["unit"]["status"]=="unknown":add("semantic.unit",path)
                if m["range"] and Decimal(m["range"]["low"])>Decimal(m["range"]["high"]):add("semantic.range",path)
        elif d["kind"]=="target-instance":
            if d["id"] in targets:add("target.multiple-versions",path)
            targets[d["id"]]=d
            sem=resolve("semantic-definition",d["semanticDefinitionRef"],path)
            if sem:
                try:members[(d["id"],d["version"])]= {k:v["member"] for k,v in ls.layout(sem)["leaves"].items()}
                except ls.StructureError:pass
    def source_signature(ref,equipment,path):
        src=resolve("source-definition",ref,path)
        if not src:return None
        if src["equipmentInstanceId"]!=equipment:add("value.equipment",path)
        if mixed_sources.mode(src)=="write":add("source.not-readable",path)
        if "fixedArray" in src:return {"type":"FixedArray","unit":src["unit"],"sources":{(src["id"],src["version"])},"rawWord":False,"stage":src["inputStage"],"arraySource":src}
        try:typ=source_views.value_type(src,source_views.index(x for x in docs.values() if x["kind"]=="source-definition"))
        except ValueError:return None
        if src["access"].get("bitOffset") is not None:typ="Boolean"
        return {"type":typ,"unit":src["unit"],"sources":{(x["id"],x["version"]) for x in source_views.chain(src,source_views.index(d for d in docs.values() if d["kind"]=="source-definition"))},"rawWord":typ=="UInt16" and src["inputStage"]=="raw" and src["access"].get("bitOffset") is None,"stage":src["inputStage"]}
    try:graph_order=graph_reuse.order(d for d in docs.values() if d["kind"]=="value-graph")
    except graph_reuse.GraphError as e:add(str(e),"value-graphs");return errors,{}
    for g in graph_order:
        nodes={n["nodeId"]:n for n in g["nodes"]};path="value-graph:"+g["id"]
        if len(nodes)!=len(g["nodes"]):add("graph.duplicate-node",path);continue
        for n in nodes.values():
            evidence(n["evidenceRefs"],path+"/"+n["nodeId"])
            for endpoint in n["inputs"].values():
                if endpoint["kind"]=="node" and endpoint["nodeId"] not in nodes:add("graph.node-missing",path+"/"+n["nodeId"])
        pending=set(nodes);done={}
        while pending:
            ready=sorted(nid for nid in pending if all(v["kind"]!="node" or v["nodeId"] not in pending for v in nodes[nid]["inputs"].values()))
            if not ready:add("graph.cycle",path);break
            for nid in ready:
                n=nodes[nid];np=path+"/"+nid;ins={}
                for name,ep in n["inputs"].items():
                    ins[name]=source_signature(ep["sourceRef"],g["equipmentInstanceId"],np) if ep["kind"]=="source" else signatures.get((ep["graphRef"]["id"],ep["graphRef"]["version"],ep["nodeId"])) if ep["kind"]=="graph" else done.get(ep["nodeId"])
                signature=None
                if all(ins.values()):
                    sources=set().union(*(s["sources"] for s in ins.values()))
                    required_evidence={json.dumps(ref,sort_keys=True) for sid,sv in sources for ref in docs[("source-definition",sid,sv)]["evidenceRefs"]}
                    if not required_evidence.issubset({json.dumps(ref,sort_keys=True) for ref in n["evidenceRefs"]}):add("graph.evidence-incomplete",np)
                    if n["op"]=="decode-u32-words":
                        if any(s["type"]!="UInt16" or not s["rawWord"] for s in ins.values()):add("graph.input-type",np)
                        if any(s["unit"]!={"status":"not-applicable"} for s in ins.values()):add("graph.input-unit",np)
                        if n["unit"]["status"]=="unknown":add("graph.output-unit",np)
                        signature={"type":"UInt32","unit":n["unit"],"sources":sources,"rawWord":False,"stage":"decoded"}
                    elif n["op"]=="bounded-selector":
                        names=sorted((k for k in ins if k.startswith("candidate")),key=lambda k:int(k[9:]))
                        if names!=["candidate"+str(i) for i in range(len(names))]:add("selector.candidates",np)
                        for k in ("index","previousIndex"):
                            if k in ins and (ins[k]["type"] not in INTEGER or ins[k]["unit"]!={"status":"known","code":"1"}):add("selector.index-type",np)
                        candidates=[ins[k] for k in names]
                        if any(s["type"]!=n["valueType"] or s["type"]=="FixedArray" for s in candidates):add("selector.candidate-type",np)
                        if any(s["unit"]!=n["unit"] or s["unit"]["status"]=="unknown" for s in candidates):add("selector.candidate-unit",np)
                        if n.get("defaultCandidate",0)>=len(names):add("selector.default-range",np)
                        signature={"type":n["valueType"],"unit":n["unit"],"sources":sources,"rawWord":all(s["rawWord"] for s in candidates),"stage":"already-engineered" if any(s["stage"]=="already-engineered" for s in candidates) else "derived"}
                    elif n["op"]=="array-element":
                        value=ins["value"];src=value.get("arraySource")
                        if value["type"]!="FixedArray" or not src:add("array.input-type",np)
                        else:
                            try:fixed_arrays.index(src,n["indices"])
                            except fixed_arrays.ArrayError as e:add(e.code,np)
                            typ=source_codecs.decoded_type(src)
                            if typ!=n["valueType"]:add("graph.output-type",np)
                            if src["unit"]!=n["unit"]:add("graph.output-unit",np)
                            signature={"type":typ,"unit":src["unit"],"sources":sources,"rawWord":typ=="UInt16" and src["inputStage"]=="raw","stage":src["inputStage"]}
                    elif n["op"] in arithmetic.OPS:
                        if any(s["type"] not in NUMERIC for s in ins.values()):add("graph.input-type",np)
                        try:outunit=arithmetic.unit_for(n["op"],ins["left"]["unit"],ins["right"]["unit"])
                        except ValueError as e:add(str(e),np);outunit=n["unit"]
                        if outunit!=n["unit"]:add("graph.output-unit",np)
                        signature={"type":"Decimal","unit":outunit,"sources":sources,"rawWord":False,"stage":"derived"}
                    elif n["op"] in ("sqrt","clamp"):
                        value=ins["value"];outunit=value["unit"]
                        if value["type"] not in NUMERIC:add("graph.input-type",np)
                        if outunit.get("status")!="known" or (n["op"]=="sqrt" and outunit!={"status":"known","code":"1"}):add("graph.input-unit",np)
                        if n["op"]=="clamp" and Decimal(n["low"])>Decimal(n["high"]):add("graph.clamp-range",np)
                        if outunit!=n["unit"]:add("graph.output-unit",np)
                        signature={"type":"Decimal","unit":outunit,"sources":sources,"rawWord":False,"stage":"derived"}
                    elif n["op"] in ("subtract","linear","unit-convert"):
                        if any(s["type"] not in NUMERIC for s in ins.values()):add("graph.input-type",np)
                        value=next(iter(ins.values()));outunit=value["unit"]
                        if n["op"]=="subtract":
                            # Absolute affine temperatures require a separate delta-unit model.
                            if any(s["unit"]!=outunit for s in ins.values()) or outunit.get("code") not in ("Pa","kPa","bar","1"):
                                add("graph.input-unit",np)
                        elif n["op"]=="linear":
                            if value["stage"]=="already-engineered" and (Decimal(n["factor"])!=1 or Decimal(n["offset"])!=0):add("mapping.double-transform",np)
                        else:
                            if (n["from"],n["to"]) not in vc.UNIT_CONVERSIONS or outunit!={"status":"known","code":n["from"]}:add("graph.input-unit",np)
                            outunit={"status":"known","code":n["to"]}
                        if outunit!=n["unit"]:add("graph.output-unit",np)
                        if n["unit"]["status"]!="known":add("graph.output-unit",np)
                        signature={"type":"Decimal","unit":outunit,"sources":sources,"rawWord":False,"stage":"derived"}
                    elif n["op"]=="identity":
                        value=ins["value"]
                        if value["type"]!=n["valueType"]:add("graph.output-type",np)
                        if value["unit"]!=n["unit"]:add("graph.output-unit",np)
                        signature=copy.deepcopy(value)
                done[nid]=signature;pending.remove(nid)
        for nid,sig in done.items():
            if sig:signatures[(g["id"],g["version"],nid)]=sig
    bound=set();mapping_ids=set();coverage={};binding_lineage={};warnings=[]
    for d in docs.values():
        if d["kind"]!="mapping-set":continue
        path="mapping-set:"+d["id"];t=resolve("target-instance",d["targetInstanceRef"],path)
        if t and t["equipmentInstanceId"]!=d["equipmentInstanceId"]:add("mapping.equipment",path)
        mm=members.get((t["id"],t["version"]),{}) if t else {}
        for m in d["mappings"]:
            mp=path+"/"+m["mappingId"];evidence(m["evidenceRefs"],mp)
            if m["mappingId"] in mapping_ids:add("mapping.duplicate-id",mp)
            mapping_ids.add(m["mappingId"])
            member=ls.path_key(m["memberPath"]);target=mm.get(member)
            if t:
                sem=resolve("semantic-definition",t["semanticDefinitionRef"],mp)
                if sem:
                    try:ls.resolve(sem,m["memberPath"])
                    except ls.StructureError as e:add(e.code,mp);target=None
            if not target:add("mapping.member",mp)
            if t:
                bkey=(d["equipmentInstanceId"],t["id"],member)
                if bkey in bound:add("mapping.duplicate-target",mp)
                bound.add(bkey);coverage.setdefault(t["id"],set()).add(member)
            v=m["valueRef"]
            if v["kind"]=="source":sig=source_signature(v["sourceRef"],d["equipmentInstanceId"],mp)
            else:
                g=resolve("value-graph",v["graphRef"],mp)
                if g and g["equipmentInstanceId"]!=d["equipmentInstanceId"]:add("value.equipment",mp)
                if g and v["nodeId"] not in {n["nodeId"] for n in g["nodes"]}:add("graph.node-missing",mp)
                sig=signatures.get((v["graphRef"]["id"],v["graphRef"]["version"],v["nodeId"]))
            if not sig or not target:continue
            required_evidence={json.dumps(ref,sort_keys=True) for sid,sv in sig["sources"] for ref in docs[("source-definition",sid,sv)]["evidenceRefs"]}
            if not required_evidence.issubset({json.dumps(ref,sort_keys=True) for ref in m["evidenceRefs"]}):add("mapping.evidence-incomplete",mp)
            typ,unit=sig["type"],sig["unit"]
            if typ=="FixedArray":add("array.whole-mapping",mp)
            for transform in m["transform"]:
                op=transform["op"]
                if op=="linear":
                    if typ not in NUMERIC:add("transform.input",mp)
                    if sig["stage"]=="already-engineered" and (Decimal(transform["factor"])!=1 or Decimal(transform["offset"])!=0):add("mapping.double-transform",mp)
                    typ="Decimal"
                elif op=="unit-convert":
                    if typ not in NUMERIC or unit!={"status":"known","code":transform["from"]} or (transform["from"],transform["to"]) not in vc.UNIT_CONVERSIONS:add("transform.unit",mp)
                    typ="Decimal";unit={"status":"known","code":transform["to"]}
                elif op=="bit-select":
                    if typ not in INTEGER or transform["index"]>=INTEGER.get(typ,0):add("transform.bit",mp)
                    typ="Boolean";unit={"status":"not-applicable"}
                elif op=="enum-map":
                    if typ not in NUMERIC:add("transform.input",mp)
                    values=[Decimal(e["raw"]) for e in transform["entries"]]
                    if len(values)!=len(set(values)):add("transform.enum-duplicate",mp)
                    typ="String";unit={"status":"not-applicable"}
                elif op=="cast":
                    dest=transform["to"]
                    if dest in ("Double","Int32") and typ not in NUMERIC:add("transform.input",mp)
                    if dest in ("Boolean","String") and typ!=dest:add("transform.input",mp)
                    typ=dest
            if typ!=target["valueType"]:add("mapping.type",mp)
            if m["outputUnit"]!=target["unit"]:add("mapping.unit",mp)
            if unit["status"]=="unknown":
                if v["kind"]=="source":warnings.append({"ruleCode":"mapping.input-unit-unknown-preserved","path":mp})
                else:add("mapping.input-unit-unknown",mp)
            elif unit!=m["outputUnit"]:add("mapping.unit-conversion-required",mp)
            binding_lineage[m["mappingId"]]={"targetInstanceId":t["id"],"memberPath":m["memberPath"],"sources":[{"id":i,"version":v} for i,v in sorted(sig["sources"])]}
    mixed_sources.validate_writes(docs,add)
    for tid,t in targets.items():
        required=set(members.get((tid,t["version"]),{}))
        for missing in sorted(required-coverage.get(tid,set())):add("mapping.incomplete-object",tid+"/"+missing)
    return errors,{"bindings":binding_lineage,"targets":sorted(targets),"warnings":warnings}
def migrate(root,dest,assignments):
    """Explicit legacy mapping-set -> stable target IDs. No automatic equipment-as-object identity."""
    root=Path(root);dest=Path(dest)
    if dest.exists():raise ValueError("Destination already exists")
    problems=vc.validate_package(root)
    if problems:raise ValueError("Invalid legacy package: "+str(problems))
    proposal=vc.load(root/"proposal.json")
    docs={e["path"]:vc.load(vc.safe(root,e["path"])) for e in proposal["files"]}
    oldmaps=[d for d in docs.values() if d["kind"]=="mapping-set"]
    if set(assignments)!={d["id"] for d in oldmaps}:raise ValueError("Explicit assignment required for every mapping-set")
    # Build in temporary sibling and publish only a statically valid package.
    dest.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="tyr-migrate-",dir=dest.parent) as tmp:
        folder=Path(tmp)/"result";shutil.copytree(root,folder);entries=[];targets={}
        for rel,d in docs.items():
            if d["kind"]=="mapping-set":
                tid=assignments[d["id"]]
                target={"kind":"target-instance","schemaVersion":"2.0.0","id":tid,"version":"1.0.0","equipmentInstanceId":d["equipmentInstanceId"],"label":tid,"semanticDefinitionRef":d["semanticDefinitionRef"],"evidenceRefs":copy.deepcopy(d["mappings"][0]["evidenceRefs"])}
                if tid in targets and targets[tid]!=target:raise ValueError("Conflicting target assignment")
                targets[tid]=target
                d=copy.deepcopy(d);d["schemaVersion"]="2.0.0";d["version"]="2.0.0";d.pop("semanticDefinitionRef");d["targetInstanceRef"]={"id":tid,"version":"1.0.0"}
                for m in d["mappings"]:
                    m["valueRef"]={"kind":"source","sourceRef":m.pop("sourceRef")}
                    m["memberPath"]=[{"kind":"member","memberId":m.pop("targetMemberId")}]
                vc.save(folder/rel,d)
            entries.append({"path":rel,"kind":d["kind"],"id":d["id"],"version":d["version"],"sha256":vc.hashed(folder/rel)})
        (folder/"targets").mkdir(exist_ok=True)
        for i,t in enumerate(targets.values()):
            rel="targets/"+str(i)+".json";vc.save(folder/rel,t)
            entries.append({"path":rel,"kind":t["kind"],"id":t["id"],"version":t["version"],"sha256":vc.hashed(folder/rel)})
        proposal.update(schemaVersion="2.0.0",version="2.0.0",files=entries);vc.save(folder/"proposal.json",proposal)
        errors,_=validate_package(folder)
        if errors:raise ValueError("Migrated package invalid: "+str(errors))
        shutil.copytree(folder,dest)
def decode_fixture(graph,samples):
    """Bounded P3-A oracle harness only: typed UInt16 samples, identity and low/high U32."""
    nodes={n["nodeId"]:n for n in graph["nodes"]};done={};pending=set(nodes)
    while pending:
        ready=sorted(nid for nid in pending if all(v["kind"]!="node" or v["nodeId"] in done for v in nodes[nid]["inputs"].values()))
        if not ready:raise ValueError("graph.cycle")
        for nid in ready:
            n=nodes[nid];vals={}
            for name,ep in n["inputs"].items():
                if ep["kind"]=="source":
                    key=(ep["sourceRef"]["id"],ep["sourceRef"]["version"])
                    if key not in samples:raise ValueError("sample.missing")
                    vals[name]=samples[key]
                else:vals[name]=done[ep["nodeId"]]
            if n["op"]=="decode-u32-words":
                if any(type(v) is not int or not 0<=v<=65535 for v in vals.values()):raise ValueError("sample.u16-range")
                done[nid]=vals["low"]+(vals["high"]<<16)
            elif n["op"]=="identity":done[nid]=vals["value"]
            else:raise ValueError("operation.unsupported")
            pending.remove(nid)
    return done
def main():
    p=argparse.ArgumentParser();p.add_argument("--package",type=Path,required=True);p.add_argument("--report",type=Path);p.add_argument("--deny-network",action="store_true");p.add_argument("--migrate-to",type=Path);p.add_argument("--assignments",type=Path);a=p.parse_args()
    if a.deny_network:
        import socket
        def deny(*args,**kwargs):raise RuntimeError("Network forbidden")
        socket.socket=deny;socket.create_connection=deny
    if a.migrate_to:
        if not a.assignments:p.error("--assignments required")
        migrate(a.package,a.migrate_to,vc.load(a.assignments));a.package=a.migrate_to
    errors,details=validate_package(a.package)
    report={"scope":"P3-A file contracts; no device communication or approval","generatedAt":datetime.now(timezone.utc).isoformat(),"valid":not errors,"findings":errors,**details}
    if a.report:vc.save(a.report,report)
    print(json.dumps(report,ensure_ascii=True,indent=2));return bool(errors)
if __name__=="__main__":sys.exit(main())
