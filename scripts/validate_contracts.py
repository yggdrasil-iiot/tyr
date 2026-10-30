"""Offline P1 contract/fixture gate. No PLC, Bifrost process, network or approval actions."""
from functools import lru_cache
import source_codecs
import fixed_arrays
from pathlib import Path
from decimal import Decimal
import argparse, copy, hashlib, json, shutil, struct, tempfile, uuid
from datetime import datetime, timezone
from importlib.metadata import version as package_version
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT=Path(__file__).resolve().parents[1]
SCHEMAS=ROOT/"contracts"/"1.0.0"
KINDS={p.stem.removesuffix(".schema"):p for p in SCHEMAS.glob("*.schema.json") if p.name!="common.schema.json"}
WIDTH={"Int16":2,"UInt16":2,"Int32":4,"UInt32":4,"Int64":8,"Float32":4,"Float64":8,"Boolean":1}
UNIT_CONVERSIONS={("1/s","rpm"):("60","0"),("mN.m","N.m"):("0.001","0"),("K","Cel"):("1","-273.15")}
UNIT_CONVERSIONS.update({("Pa","kPa"):("0.001","0"),("kPa","Pa"):("1000","0"),("bar","Pa"):("100000","0"),("Pa","bar"):("0.00001","0"),("bar","kPa"):("100","0"),("kPa","bar"):("0.01","0")})
PROFILES={"melsec-device-v1":"device-register","s7-300-db-v1":"db-offset","ab-logix-symbol-v1":"symbol","s7-1500-opcua-v1":"opcua-node"}
def no_remote(uri): raise ValueError("External schema retrieval prohibited: "+uri)
def pairs(items):
    d={}
    for k,v in items:
        if k in d: raise ValueError("Duplicate JSON key: "+k)
        d[k]=v
    return d
def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"),object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError("Nonfinite JSON: "+x)))
def hashed(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value): Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8",newline="\n")
registry=Registry(retrieve=no_remote)
for p in (ROOT/"contracts").glob("*/*.schema.json"):
    s=load(p); Draft202012Validator.check_schema(s)
    resource=Resource.from_contents(s)
    registry=registry.with_resource(p.as_uri(),resource).with_resource(s["$id"],resource)
def schema_formats(node):
    if isinstance(node,dict):
        f=node.get("format");yield from ([f] if isinstance(f,str) else [])
        for v in node.values():yield from schema_formats(v)
    elif isinstance(node,list):
        for v in node:yield from schema_formats(v)
# jsonschema registers "uri" only when an optional checker package imports; without it the format is silently not asserted.
CONTRACT_FORMATS={f for p in (ROOT/"contracts").glob("*/*.schema.json") for f in schema_formats(load(p))}
MISSING_FORMATS=CONTRACT_FORMATS-set(FormatChecker.checkers)
if MISSING_FORMATS:raise RuntimeError("format checker not installed for: "+", ".join(sorted(MISSING_FORMATS))+" (pip install -r requirements-contracts.txt)")
# Base URI is the local file, allowing relative refs while registry never retrieves remotely.
@lru_cache(maxsize=64)
def schema_validator(kind,version):
    path=ROOT/"contracts"/version/(kind+".schema.json")
    s=copy.deepcopy(load(path));s["$id"]=path.as_uri()
    return Draft202012Validator(s,registry=registry,format_checker=FormatChecker())
def validate_schema(kind,value):
    version=value.get("schemaVersion","1.0.0")
    if version not in ("1.0.0","1.1.0") and not (version=="2.1.0" and kind=="source-definition") and not (version=="2.2.0" and kind in ("source-definition","semantic-definition")) and not (version in ("2.4.0","2.7.0","2.10.0","2.21.0") and kind=="source-definition"):return ["unsupported schemaVersion"]
    return sorted(schema_validator(kind,version).iter_errors(value),key=lambda e:str(list(e.path)))
def safe(root,path):
    if not isinstance(path,str) or "\\" in path or ":" in path or path.startswith("/") or any(x in ("",".","..") for x in path.split("/")):
        raise ValueError("Unsafe relative path")
    resolved=(root/path).resolve()
    if not resolved.is_relative_to(root.resolve()): raise ValueError("Path escapes package")
    return resolved
def source_rules(s):
    if s.get("schemaVersion")=="2.21.0":
        d=copy.deepcopy(s);d['schemaVersion']='2.7.0';d.pop('recordField',None);return source_rules(d)
    if s.get("schemaVersion")=="2.10.0":
        d=copy.deepcopy(s);d["schemaVersion"]="2.7.0";d.pop("view",None);return source_rules(d)
    if s.get("schemaVersion")=="2.7.0":
        import mixed_sources
        return mixed_sources.rules(s)
    out=[]
    def add(rule): out.append(rule)
    a,r=s["access"],s["rawRepresentation"];kind=a["kind"]
    if PROFILES.get(s["accessProfileRef"])!=kind: add("source.profile-mismatch")
    if s["status"]=="ready":
        required=[v for k,v in a.items() if k not in ("kind","bitOffset")]
        if any(v is None for v in required) or r.get("valueType") is None: add("source.incomplete")
        if kind=="device-register" and s["addressRadix"] is None: add("source.incomplete")
        if r["mode"]=="bytes" and (r["byteOrder"] is None or r["wordOrder"] is None): add("source.incomplete")
    if kind in ("device-register","db-offset"):
        if r["mode"]!="bytes": add("source.representation")
        w=WIDTH.get(r.get("valueType")) if s["schemaVersion"] not in ("2.1.0","2.2.0","2.4.0") else None
        actual=a.get("wordCount",0)*2 if kind=="device-register" and a.get("wordCount") is not None else a.get("byteLength")
        if w and actual is not None and actual!=w: add("source.width")
    elif r["mode"]!="typed": add("source.representation")
    if kind=="opcua-node" and a.get("identifier") is not None:
        ident=a["identifier"];t=a["identifierType"]
        if t=="numeric" and (type(ident) is not int or not 0<=ident<=4294967295): add("source.node-identifier")
        if t!="numeric" and not isinstance(ident,str): add("source.node-identifier")
        if t=="guid":
            try: uuid.UUID(str(ident))
            except ValueError: add("source.node-identifier")
    return sorted(set(out+source_codecs.rules(s)+fixed_arrays.rules(s)))
def validate_package(root):
    root=Path(root); findings=[]
    def add(rule,path=None): findings.append({"ruleCode":rule,"path":path})
    try: proposal=load(root/"proposal.json")
    except (OSError,ValueError): return [{"ruleCode":"bundle.unreadable","path":"proposal.json"}]
    if validate_schema("mapping-proposal",proposal): return [{"ruleCode":"schema","path":"proposal.json"}]
    docs={};paths=set()
    for e in proposal["files"]:
        if e["path"] in paths: add("bundle.duplicate-path",e["path"]);continue
        paths.add(e["path"]);key=(e["kind"],e["id"],e["version"])
        if key in docs: add("bundle.duplicate-id",e["path"])
        try:
            path=safe(root,e["path"])
            if hashed(path)!=e["sha256"]: add("bundle.digest",e["path"])
            d=load(path)
        except (OSError,ValueError): add("bundle.unreadable",e["path"]);continue
        if validate_schema(e["kind"],d): add("schema",e["path"]);continue
        if (d["kind"],d["id"],d["version"])!=key: add("bundle.identity",e["path"])
        docs[key]=(d,e)
    evrows=[d for (k,i,v),(d,e) in docs.items() if k=="evidence-artifact"]
    if len({d["id"] for d in evrows})!=len(evrows):add("evidence.ambiguous")
    ev={d["id"]:d for d in evrows}
    def resolve(kind,ref):
        row=docs.get((kind,ref["id"],ref["version"]))
        if row is None: add("reference.missing");return None
        return row[0]
    def check_evidence(refs):
        for r in refs:
            if r["artifactId"] not in ev: add("evidence.missing");continue
            art=ev[r["artifactId"]]
            try:
                p=safe(root,art["file"]["path"]);loc=r["locator"]
                if loc["kind"]=="text-line" and loc["line"]>len(p.read_text(encoding="utf-8").splitlines()): add("evidence.locator")
                elif loc["kind"]=="json-pointer":
                    x=load(p)
                    if loc["pointer"]:
                        for token in loc["pointer"][1:].split("/"):
                            token=token.replace("~1","/").replace("~0","~")
                            x=x[int(token)] if isinstance(x,list) else x[token]
            except (OSError,ValueError,KeyError,IndexError,TypeError): add("evidence.locator")
    identities={}
    for (kind,i,v),(d,e) in docs.items():
        if kind=="semantic-definition":
            for member in d["members"]:
                signature={k:member[k] for k in ("role","valueType","unit")}
                semantic_id=member["semanticId"]
                if semantic_id in identities and identities[semantic_id]!=signature:
                    add("semantic.identity-conflict",e["path"])
                identities[semantic_id]=signature
    bound=set()
    for (kind,i,v),(d,e) in docs.items():
        path=e["path"]
        if "evidenceRefs" in d:check_evidence(d["evidenceRefs"])
        if kind=="evidence-artifact":
            try:
                if hashed(safe(root,d["file"]["path"]))!=d["file"]["sha256"]:add("evidence.digest",path)
            except (OSError,ValueError):add("evidence.unreadable",path)
        elif kind=="source-definition":
            if "fixedArray" in d:add("array.legacy-unsupported",path)
            if d.get("schemaVersion") in ("2.7.0","2.10.0","2.21.0"):add("source.mixed-legacy-unsupported",path)
            for rule in source_rules(d):add(rule,path)
            if d["viewOf"] is not None and resolve("source-definition",d["viewOf"]) is None:pass
        elif kind=="semantic-definition":
            ids=[m["memberId"] for m in d["members"]]
            if len(ids)!=len(set(ids)):add("semantic.duplicate",path)
            for m in d["members"]:
                if m["unit"]["status"]=="unknown":add("semantic.unit",path)
                if m["range"] and Decimal(m["range"]["low"])>Decimal(m["range"]["high"]):add("semantic.range",path)
        elif kind=="mapping-set":
            sem=resolve("semantic-definition",d["semanticDefinitionRef"])
            members={m["memberId"]:m for m in sem["members"]} if sem else {}
            ids=[m["mappingId"] for m in d["mappings"]]
            if len(ids)!=len(set(ids)):add("mapping.duplicate",path)
            for m in d["mappings"]:
                check_evidence(m["evidenceRefs"])
                source=resolve("source-definition",m["sourceRef"]);target=members.get(m["targetMemberId"])
                key=(d["equipmentInstanceId"],d["semanticDefinitionRef"]["id"],d["semanticDefinitionRef"]["version"],m["targetMemberId"])
                if key in bound:add("mapping.duplicate",path)
                bound.add(key)
                if target is None:add("mapping.member",path)
                if source is None or target is None:continue
                if source["status"]!="ready":add("mapping.source-not-ready",path)
                if source["equipmentInstanceId"]!=d["equipmentInstanceId"]:add("mapping.equipment",path)
                if m["outputUnit"]!=target["unit"]:add("mapping.unit",path)
                typ=source["rawRepresentation"]["valueType"]
                if source["access"].get("bitOffset") is not None:typ="Boolean"
                transforms=m["transform"]
                current_unit=source["unit"]
                if source["inputStage"]=="already-engineered" and any(t["op"]=="linear" and (Decimal(t["factor"])!=1 or Decimal(t["offset"])!=0) for t in transforms):add("mapping.double-transform",path)
                for t in transforms:
                    op=t["op"]
                    if op=="linear":
                        if typ in ("Boolean","String",None):add("transform.input",path)
                        typ="Decimal"
                    elif op=="unit-convert":
                        pair=(t["from"],t["to"])
                        if pair not in UNIT_CONVERSIONS:add("transform.unit-conversion",path)
                        if current_unit!={"status":"known","code":t["from"]}:add("transform.unit-source",path)
                        if typ in ("Boolean","String",None):add("transform.input",path)
                        current_unit={"status":"known","code":t["to"]}
                        typ="Decimal"
                    elif op=="cast":
                        to=t["to"]
                        if to in ("Double","Int32") and typ in ("Boolean","String",None):add("transform.input",path)
                        if to in ("Boolean","String") and typ!=to:add("transform.input",path)
                        typ=to
                    elif op=="bit-select":
                        if typ not in ("Int16","UInt16","Int32","UInt32","Int64"):add("transform.input",path)
                        width=WIDTH.get(typ,0)*8
                        if t["index"]>=width:add("transform.bit-range",path)
                        if source["access"].get("bitOffset") is not None:add("transform.double-bit",path)
                        typ="Boolean"
                    elif op=="enum-map":
                        if typ in ("Boolean","String",None):add("transform.input",path)
                        keys=[Decimal(x["raw"]) for x in t["entries"]]
                        if len(keys)!=len(set(keys)):add("transform.enum-duplicate",path)
                        typ="String"
                if any(t["op"]=="unit-convert" for t in transforms) and current_unit!=m["outputUnit"]:add("transform.unit-target",path)
                if current_unit.get("status")=="known" and m["outputUnit"].get("status")=="known" and current_unit!=m["outputUnit"]:add("mapping.unit-conversion-required",path)
                if typ!=target["valueType"]:add("mapping.type",path)
        elif kind=="review-record":
            t=d["target"]; row=docs.get((t["kind"],t["id"],t["version"]))
            if row is None:add("reference.missing",path)
            elif t["sha256"]!=row[1]["sha256"]:add("review.digest",path)
    return findings
def release_rules(d,root):
    out=envelope_rules(d)
    proposal=load(root/"proposal.json")
    if hashed(root/"proposal.json")!=d["proposalSha256"]:out.append("release.proposal-digest")
    if d["files"]!=proposal["files"]:out.append("release.files")
    return out
def envelope_rules(d):
    out=[]
    if d["kind"]=="source-definition":out.extend(source_rules(d))
    if d["kind"]=="observation-bundle":
        if d["inputCount"]!=d["processedCount"]+d["unsupportedCount"] or d["processedCount"]!=len(d["observations"]):out.append("observation.count")
        known={a["id"] for a in d["artifacts"]}
        if any(r["artifactId"] not in known for o in d["observations"] for r in o["evidenceRefs"]):out.append("evidence.missing")
    if d["kind"]=="validation-report":
        if d["valid"]==any(f["severity"]=="error" for f in d["findings"]):out.append("report.consistency")
    if d["kind"]=="mapping-release":
        if d["approval"]["proposedBy"]==d["approval"]["approvedBy"]:out.append("approval.self")
        if len({f["path"] for f in d["files"]})!=len(d["files"]):out.append("bundle.duplicate-path")
    return out
def mutate(doc,pointer,value):
    tokens=pointer[1:].split("/");x=doc
    for token in tokens[:-1]:
        token=token.replace("~1","/").replace("~0","~");x=x[int(token)] if isinstance(x,list) else x[token]
    last=tokens[-1].replace("~1","/").replace("~0","~")
    if isinstance(x,list):
        idx=int(last)
        if idx==len(x):x.append(value)
        else:x[idx]=value
    else:x[last]=value
def gate():
    results=[]
    for name,path in KINDS.items():
        # meta-schema validation is performed during registry construction
        results.append({"id":"schema:"+name,"passed":True})
    for path in sorted((ROOT/"contracts/1.1.0").glob("*.schema.json")):
        results.append({"id":"schema:1.1.0:"+path.name,"passed":True})
    for path in sorted((ROOT/"fixtures/valid").glob("*.json")):
        d=load(path);errors=validate_schema(d["kind"],d)
        rules=(release_rules(d,ROOT/"fixtures/packages/motor") if d["kind"]=="mapping-release" else envelope_rules(d)) if not errors else ["schema"]
        results.append({"id":"valid:"+path.name,"passed":not rules,"rules":rules})
    rules=validate_package(ROOT/"fixtures/packages/motor")
    results.append({"id":"valid:four-profiles-package","passed":not rules,"rules":rules})
    for case in load(ROOT/"fixtures/cases.json")["cases"]:
        if case["mode"]=="schema":
            errors=validate_schema(case["schema"],load(ROOT/case["file"]))
            ok=(not errors)==case["valid"];rules=["schema"] if errors else []
        elif case["mode"]=="document":
            d=load(ROOT/case["file"]);errors=validate_schema(d["kind"],d)
            rules=(release_rules(d,ROOT/"fixtures/packages/motor") if d["kind"]=="mapping-release" else envelope_rules(d)) if not errors else ["schema"]
            ok=(not rules)==case["valid"] and case["expectedRule"] in rules
        else:
            with tempfile.TemporaryDirectory(prefix="tyr-contract-") as tmp:
                temp=Path(tmp)/"package";shutil.copytree(ROOT/case["base"],temp)
                for patch in case["mutations"]:
                    p=safe(temp,patch["path"]);d=load(p);mutate(d,patch["pointer"],patch["value"]);save(p,d)
                if case["reseal"]:
                    proposal=load(temp/"proposal.json")
                    for f in proposal["files"]:f["sha256"]=hashed(safe(temp,f["path"]))
                    save(temp/"proposal.json",proposal)
                findings=validate_package(temp);rules=sorted({f["ruleCode"] for f in findings})
                ok=(not findings)==case["valid"] and (case.get("expectedRule") is None or case["expectedRule"] in rules)
        results.append({"id":case["id"],"passed":ok,"rules":rules})
    # Expected values are stored literals; independent stdlib decoding checks them.
    for case in load(ROOT/"fixtures/oracles.json")["cases"]:
        cid=case["id"];ok=False
        if "expectedDecoded" in case:
            fmt=case.get("format",{"register-speed":"<i","db-speed":">f","opcua-speed":None,"symbol-speed":None}.get(cid))
            value=Decimal(str(struct.unpack(fmt,bytes.fromhex(case["bytesHex"]))[0])) if fmt else Decimal(case["typedValue"])
            ok=value==Decimal(case["expectedDecoded"])
            if "expectedResult" in case:ok=ok and value*Decimal(case["factor"])+Decimal(case["offset"])==Decimal(case["expectedResult"])
        elif cid=="enum-unknown":ok=case["rawCode"] not in case["entries"] and case["expectedQuality"]=="bad"
        elif cid=="bit-15":ok=bool(int(case["integer"]) & (1<<case["bit"]))==case["expected"]
        elif cid=="int32-overflow":ok=not -(2**31)<=int(case["integer"])<2**31 and case["expectedError"]=="overflow"
        results.append({"id":"oracle:"+cid,"passed":ok})
    # JSON ambiguities are rejected before schema validation.
    try:json.loads('{"id":"a","id":"b"}',object_pairs_hook=pairs);ok=False
    except ValueError:ok=True
    results.append({"id":"duplicate-json-keys","passed":ok})
    try:safe(ROOT,"../outside.json");ok=False
    except ValueError:ok=True
    results.append({"id":"path-traversal","passed":ok})
    from governance_checks import run as governance_run
    governance_results,assessment=governance_run()
    results.extend(governance_results)
    report={"extendedContractSchemas":{str(p.relative_to(ROOT)).replace(chr(92),"/"):hashed(p) for p in sorted((ROOT/"contracts/1.1.0").glob("*.schema.json"))},"governanceAssessment":assessment,"inputHashes":{str(p.relative_to(ROOT)).replace(chr(92),"/"):hashed(p) for p in sorted((ROOT/"fixtures").rglob("*")) if p.is_file()},"governanceValidatorSha256":hashed(ROOT/"scripts/governance_checks.py"),"scope":"P1 canonical-model governance: convergence, distinction, projection loss and semantic drift; offline","jsonschema":package_version("jsonschema"),"generatedAt":datetime.now(timezone.utc).isoformat(),"validatorSha256":hashed(Path(__file__)),"contractSchemas":{p.name:hashed(p) for p in sorted(SCHEMAS.glob("*.schema.json"))},"total":len(results),"passed":sum(r["passed"] for r in results),"failed":[r for r in results if not r["passed"]],"results":results}
    return report
def main():
    parser=argparse.ArgumentParser();parser.add_argument("--package",type=Path);parser.add_argument("--report",type=Path);parser.add_argument("--deny-network",action="store_true")
    a=parser.parse_args()
    if a.deny_network:
        import socket
        def deny(*args,**kwargs):raise RuntimeError("Network disabled by contract gate")
        socket.socket=deny
        socket.create_connection=deny
    if a.package:
        findings=validate_package(a.package);print(json.dumps({"valid":not findings,"findings":findings},indent=2));return bool(findings)
    report=gate()
    if a.report:
        a.report.parent.mkdir(parents=True,exist_ok=True);save(a.report,report)
    print(json.dumps({k:v for k,v in report.items() if k not in ("results","governanceAssessment","inputHashes")},indent=2))
    return bool(report["failed"])
if __name__=="__main__":raise SystemExit(main())
