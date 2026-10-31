"""2.0 authoring workspace, retaining the 1.x validation boundary."""
import copy
import tempfile
from pathlib import Path
import validate_contracts as vc
import p3a_contracts as p3
import import_files
VERSION="2.0.0"
def is_v2(state):return state.get("workspaceVersion")==VERSION
def upgrade(state,assignments):
    required={m["id"] for m in state["mappings"]}
    if set(assignments)!=required:raise ValueError("모든 기존 매핑에 객체 ID를 지정하세요.")
    out=copy.deepcopy(state);out.update(workspaceVersion=VERSION,targets=[],graphs=[])
    used=set()
    for m in out["mappings"]:
        tid=assignments[m["id"]]
        if not isinstance(tid,str) or tid in used:raise ValueError("서로 다른 객체 ID를 지정하세요.")
        used.add(tid)
        out["targets"].append({"kind":"target-instance","schemaVersion":VERSION,"id":tid,"version":"1.0.0","equipmentInstanceId":m["equipmentInstanceId"],"label":tid,"semanticDefinitionRef":m.pop("semanticDefinitionRef"),"evidenceRefs":copy.deepcopy(m["mappings"][0]["evidenceRefs"])})
        m.update(schemaVersion=VERSION,version="2.0.0",targetInstanceRef={"id":tid,"version":"1.0.0"})
        for b in m["mappings"]:
            b["valueRef"]={"kind":"source","sourceRef":b.pop("sourceRef")}
            b["memberPath"]=[{"kind":"member","memberId":b.pop("targetMemberId")}]
    return out
def build(state,folder,legacy_build):
    projected=import_files.projection(state)
    prior={k:copy.deepcopy(projected[k]) for k in ("equipment","connections","sources","semantics","mappings")};prior["mappings"]=[]
    if prior["sources"] or prior["semantics"]:
        legacy_build(prior,folder)
        p=vc.load(folder/"proposal.json");p.update(schemaVersion=VERSION,version="2.0.0")
    else:
        for directory in ("data","evidence","sources","semantics","mappings"):(folder/directory).mkdir(parents=True,exist_ok=True)
        p={"kind":"mapping-proposal","schemaVersion":VERSION,"id":"local-workspace","version":"2.0.0","baseRelease":None,"files":[]}
    for directory in ("targets","graphs","mappings")+(("writes",) if "writes" in state else ()):
        (folder/directory).mkdir(exist_ok=True)
        for i,d in enumerate(state[directory]):
            rel=directory+"/"+str(i)+".json";vc.save(folder/rel,d)
            p["files"].append({"path":rel,"kind":d["kind"],"id":d["id"],"version":d["version"],"sha256":vc.hashed(folder/rel)})
    import_files.build(state,folder,p)
    if state.get("writes") or any(r["definition"].get("schemaVersion") in ("2.7.0","2.10.0") for r in state["sources"]):p["schemaVersion"]="2.7.0"
    if state.get("semanticLifecycles"):
        (folder/"lifecycle").mkdir(exist_ok=True)
        p["schemaVersion"]="2.18.0"
        for i,d in enumerate(state["semanticLifecycles"]):
            rel="lifecycle/"+str(i)+".json";vc.save(folder/rel,d)
            p["files"].append({"path":rel,"kind":d["kind"],"id":d["id"],"version":d["version"],"sha256":vc.hashed(folder/rel)})
    if state.get("mappingTemplates") or state.get("templateApplications"):
        p["schemaVersion"]="2.19.0"
        for section in ("mappingTemplates","templateApplications"):
            (folder/section).mkdir(exist_ok=True)
            for i,d in enumerate(state.get(section,[])):
                rel=section+"/"+str(i)+".json";vc.save(folder/rel,d)
                p["files"].append({"path":rel,"kind":d["kind"],"id":d["id"],"version":d["version"],"sha256":vc.hashed(folder/rel)})
    import record_mappings
    record_mappings.build(state,folder,p)
    if any(r["definition"].get("recordField") for r in state["sources"]) and p['schemaVersion']!='2.22.0':p["schemaVersion"]="2.21.0"
    import hierarchy_evidence
    hierarchy_evidence.build(state,folder,p)
    if state.get("equipmentHierarchies"):
        (folder/"hierarchy").mkdir(exist_ok=True)
        p["schemaVersion"]="2.23.0"
        for i,d in enumerate(state["equipmentHierarchies"]):
            rel="hierarchy/"+str(i)+".json";vc.save(folder/rel,d)
            p["files"].append({"path":rel,"kind":d["kind"],"id":d["id"],"version":d["version"],"sha256":vc.hashed(folder/rel)})
    vc.save(folder/"proposal.json",p)
def findings(state,legacy_build):
    if not any(state[k] for k in ("sources","semantics","targets","graphs","mappings")) and not state.get("imports") and not state.get("writes"):return [{"ruleCode":"workspace.empty","path":None}]
    with tempfile.TemporaryDirectory(prefix="tyr-v2-") as t:
        root=Path(t);build(state,root,legacy_build)
        errors,details=p3.validate_package(root)
    return errors+details.get("warnings",[])

def check(state,legacy_check,legacy_build):
    keys={"workspaceVersion","equipment","connections","sources","semantics","mappings","targets","graphs"}
    if not keys<=set(state) or set(state)-keys-{"imports","writes","semanticLifecycles","mappingTemplates","templateApplications","recordMappings","resultSchemas","equipmentHierarchies","hierarchyEvidence"}:raise ValueError("workspace: unexpected/missing fields")
    if state["workspaceVersion"]!=VERSION:raise ValueError("Unsupported workspaceVersion")
    for k in keys-{"workspaceVersion"}:
        if not isinstance(state[k],list) or len(state[k])>1000:raise ValueError(k+": expected list")
    if "writes" in state and (not isinstance(state["writes"],list) or len(state["writes"])>256):raise ValueError("writes: expected list (max 256)")
    if "semanticLifecycles" in state:
        import semantic_lifecycle as lc
        events=state["semanticLifecycles"]
        if not isinstance(events,list) or len(events)>1024:raise ValueError("lifecycle.limit")
        if len({(e.get("id"),e.get("version")) for e in events})!=len(events):raise ValueError("lifecycle.event-conflict")
        lc.replay(events,lc.signatures(state["semantics"]))
    import mapping_templates
    mapping_templates.check_workspace(state)
    import result_schemas
    result_schemas.check(state)
    import record_mappings
    record_mappings.check_workspace(state)
    import record_fields
    record_fields.check_workspace(state)
    import_files.check(state)
    projected=import_files.projection(state)
    prior={k:projected[k] for k in ("equipment","connections","sources","semantics","mappings")};prior["mappings"]=[]
    legacy_check(prior)
    equip={e["id"] for e in state["equipment"]}
    for section,kind in (("targets","target-instance"),("graphs","value-graph"),("mappings","mapping-set")):
        ids=set()
        for d in state[section]:
            if p3.schema_errors(kind,d):raise ValueError(kind+": schema validation failed")
            if d["id"] in ids:raise ValueError(kind+": duplicate id")
            ids.add(d["id"])
            if d["equipmentInstanceId"] not in equip:raise ValueError(kind+": missing equipment")
    ids=set()
    for d in state.get("writes",[]):
        if p3.schema_errors("write-definition",d) or d["id"] in ids or d["equipmentInstanceId"] not in equip:raise ValueError("write-definition: schema/id/equipment")
        ids.add(d["id"])
    if "equipmentHierarchies" in state:
        import equipment_hierarchy as eh
        hs=state["equipmentHierarchies"]
        if not isinstance(hs,list) or len(hs)>1:raise ValueError("hierarchy.multiple")
        for d in hs:
            if p3.schema_errors(eh.KIND,d):raise ValueError(eh.KIND+": schema validation failed")
        eh.validate(hs,equip,evidence_scope=False)
    if "hierarchyEvidence" in state:
        import hierarchy_evidence
        hierarchy_evidence.check(state,equip)
    # Incomplete objects and changed semantic constraints may remain drafts.
    draft={"lifecycle.retired-binding","view.snapshot-mismatch","view.parent-not-ready","source.timezone-required","source.bit-coordinate-required","workspace.empty","mapping.incomplete-object","mapping.type","mapping.unit","mapping.unit-conversion-required",
           "mapping.input-unit-unknown-preserved","semantic.identity-conflict","semantic.unit","semantic.range",
           "write.source-not-ready","source.unit-unconfirmed","import.unresolved","source.not-ready","source.incomplete","source.width","mapping.double-transform"}
    blocked=[e for e in findings(state,legacy_build) if e["ruleCode"] not in draft]
    if blocked:raise ValueError("; ".join(e["ruleCode"]+" @ "+str(e["path"]) for e in blocked[:8]))
    return state
