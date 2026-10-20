"""Read-only assembly of canonical leaf previews, never vendor native decoding."""
import logical_structures as ls
import preview,sample_quality
def run(state,target_ref,samples,revision,evaluation=None):
    target=next((t for t in state["targets"] if t["id"]==target_ref.get("id") and t["version"]==target_ref.get("version")),None)
    if target is None:raise ValueError("Missing target-instance version")
    model=next(s for s in state["semantics"] if s["id"]==target["semanticDefinitionRef"]["id"] and s["version"]==target["semanticDefinitionRef"]["version"])
    layout=ls.layout(model);bound={}
    for m in state["mappings"]:
        if m["targetInstanceRef"]!=target_ref:continue
        for b in m["mappings"]:
            ls.resolve(model,b["memberPath"]);key=ls.path_key(b["memberPath"])
            if key in bound:raise ValueError("mapping.duplicate-target")
            bound[key]=(m,b)
    values={};reports=[];quality="good";issues=[];used=set()
    for key,leaf in layout["leaves"].items():
        if key not in bound:
            report={"quality":"bad","result":None,"trace":[],"issues":[{"code":"mapping.incomplete-object","severity":"error","stage":"logical-member","detail":leaf["label"]}],"persisted":False}
        else:
            mapping,binding=bound[key]
            report=preview.run(state,mapping["id"],binding["mappingId"],samples,revision,evaluation if "temporalPolicy" in binding else None)
            # Object samples are the union of leaf requirements, not unexpected leaf input.
            report["issues"]=[i for i in report["issues"] if i["code"]!="sample.unused"]
            report["quality"]="bad" if any(i["severity"]=="error" for i in report["issues"]) else "uncertain" if report["issues"] else "good"
        used.update(report.get("requiredSources",report.get("temporal",{}).get("requiredSources",[])))
        if "dataValue" in report:report["dataValue"]["quality"]=report["quality"]
        values[key]=report["result"]["value"] if report["result"] is not None else None
        reports.append({"memberPath":leaf["memberPath"],"label":leaf["label"],"report":report})
        if report["quality"]=="bad":quality="bad"
        elif report["quality"]=="uncertain" and quality!="bad":quality="uncertain"
        issues.extend(dict(i,memberPath=leaf["memberPath"]) for i in report["issues"])
    frames={}
    for member in reports:
        for step in member['report'].get('trace',[]):
            if step['stage']!='record-field-select':continue
            p=step['detail'];key=sample_quality.digest(p['recordMappingRef'])
            if key in frames and frames[key]!=p['inputSha256']:
                issues.append(dict(code='record-field.snapshot-conflict',severity='error',stage='logical-object',detail='Fields of one pinned record must use the same virtual result-set',memberPath=member['memberPath']));quality='bad'
            frames[key]=p['inputSha256']
    partial=ls.assemble(model,values)
    return {"revision":revision,"targetInstanceRef":target_ref,"semanticDefinitionRef":target["semanticDefinitionRef"],"quality":quality,"result":None if quality=="bad" else partial,"partialResult":partial,"members":reports,"arrays":layout["arrays"],"issues":issues,"workspaceSha256":sample_quality.digest(state),"sampleSha256":sample_quality.digest(samples),"evaluationContext":evaluation,"unusedSamples":sorted(set(samples)-used),"atomicSnapshot":False,"temporalScope":"per-binding; no cross-member atomicity or skew guarantee","persisted":False,"deviceCommunication":"excluded","writeExecution":"excluded"}
