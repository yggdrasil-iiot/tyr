"""Independent fixture-driven P3-A acceptance and boundary checks."""
import argparse, copy, json, socket, sys, tempfile
from pathlib import Path
import p3a_contracts as p3
import validate_contracts as vc
from jsonschema import Draft202012Validator
ROOT=vc.ROOT;BASE=ROOT/"fixtures/p3a";FIX=BASE/"two-motors"
sys.path.insert(0,str(ROOT/"backend"));import server
def rewrite(root,rel,change):
    d=vc.load(root/rel);change(d);vc.save(root/rel,d)
def rehash(root):
    p=vc.load(root/"proposal.json")
    for e in p["files"]:e["sha256"]=vc.hashed(vc.safe(root,e["path"]))
    vc.save(root/"proposal.json",p)
def mutate(root,name):
    graph="graphs/motor-a.json";mapping="mappings/motor-a.json";source="sources/motor-a-low.json"
    def g(f):rewrite(root,graph,f)
    def m(f):rewrite(root,mapping,f)
    def s(f):rewrite(root,source,f)
    if name=="cycle":g(lambda d:d["nodes"][0]["inputs"].update(low={"kind":"node","nodeId":"result"}))
    elif name=="missing-node":g(lambda d:d["nodes"][1]["inputs"]["value"].update(nodeId="absent"))
    elif name in ("missing-source","source-version"):g(lambda d:d["nodes"][0]["inputs"]["low"]["sourceRef"].update(**({"id":"absent"} if name=="missing-source" else {"version":"9.0.0"})))
    elif name in ("missing-target","target-version"):m(lambda d:d["targetInstanceRef"].update(**({"id":"absent"} if name=="missing-target" else {"version":"9.0.0"})))
    elif name=="missing-semantic":rewrite(root,"targets/motor-a.json",lambda d:d["semanticDefinitionRef"].update(id="absent"))
    elif name=="duplicate-target":
        def duplicate(d):
            x=copy.deepcopy(d["mappings"][0]);x["mappingId"]="second-binding";d["mappings"].append(x)
        m(duplicate)
    elif name=="duplicate-node":g(lambda d:d["nodes"].append(copy.deepcopy(d["nodes"][0])))
    elif name=="duplicate-mapping":rewrite(root,"mappings/motor-b.json",lambda d:d["mappings"][0].update(mappingId="motor-a-speed-binding"))
    elif name=="graph-equipment":g(lambda d:d.update(equipmentInstanceId="other-equipment"))
    elif name=="source-equipment":s(lambda d:d.update(equipmentInstanceId="other-equipment"))
    elif name=="mapping-equipment":m(lambda d:d.update(equipmentInstanceId="other-equipment"))
    elif name=="input-type":s(lambda d:d["rawRepresentation"].update(valueType="Int16"))
    elif name=="input-unit":s(lambda d:d.update(unit={"status":"known","code":"rpm"}))
    elif name=="input-stage":s(lambda d:d.update(inputStage="already-engineered"))
    elif name=="identity-type":g(lambda d:d["nodes"][1].update(valueType="Int32"))
    elif name=="identity-unit":g(lambda d:d["nodes"][1].update(unit={"status":"known","code":"rpm"}))
    elif name=="unknown-op":g(lambda d:d["nodes"][0].update(op="vendor-expression"))
    elif name=="missing-high":g(lambda d:d["nodes"][0]["inputs"].pop("high"))
    elif name=="extra-input":g(lambda d:d["nodes"][0]["inputs"].update(unexpected=copy.deepcopy(d["nodes"][0]["inputs"]["low"])))
    elif name=="ambiguous-value":m(lambda d:d["mappings"][0]["valueRef"].update(graphRef={"id":"motor-a-counter-graph","version":"1.0.0"},nodeId="result"))
    elif name=="member":m(lambda d:d["mappings"][0]["memberPath"][0].update(memberId="absent"))
    elif name=="nested-path":m(lambda d:d["mappings"][0]["memberPath"].append({"kind":"member","memberId":"nested"}))
    elif name=="incomplete":m(lambda d:d["mappings"].pop())
    elif name=="target-type":m(lambda d:d["mappings"][1].update(transform=[]))
    elif name=="evidence":s(lambda d:d["evidenceRefs"][0].update(artifactId="absent"))
    elif name=="graph-evidence":g(lambda d:d["nodes"][0].update(evidenceRefs=d["nodes"][0]["evidenceRefs"][:1]))
    elif name=="mapping-evidence":m(lambda d:d["mappings"][1].update(evidenceRefs=d["mappings"][1]["evidenceRefs"][:1]))
    elif name=="target-multiple-versions":
        d=vc.load(root/"targets/motor-a.json");d["version"]="2.0.0";vc.save(root/"targets/duplicate.json",d)
        p=vc.load(root/"proposal.json");p["files"].append({"path":"targets/duplicate.json","kind":"target-instance","id":d["id"],"version":d["version"],"sha256":vc.hashed(root/"targets/duplicate.json")});vc.save(root/"proposal.json",p)
    elif name=="path":
        p=vc.load(root/"proposal.json");p["files"][0]["path"]="../outside.json";vc.save(root/"proposal.json",p);return
    elif name=="digest":
        s(lambda d:d.update(rawAddressText="changed-but-not-rehashed"));return
    else:raise AssertionError(name)
    rehash(root)
def main():
    parser=argparse.ArgumentParser();parser.add_argument("--report",type=Path);a=parser.parse_args()
    def deny(*args,**kwargs):raise RuntimeError("Network forbidden")
    socket.socket=deny;socket.create_connection=deny
    results=[]
    def check(id,fn):
        try:actual=fn();assert actual is True,actual;results.append({"id":id,"passed":True})
        except Exception as e:results.append({"id":id,"passed":False,"error":repr(e)})
    def base():
        errors,details=p3.validate_package(FIX);o=vc.load(BASE/"oracles.json")
        assert not errors,errors
        assert details["targets"]==o["targetInstances"]
        assert len(details["bindings"])==o["bindingCount"]
        targets=[vc.load(FIX/("targets/"+id+".json")) for id in details["targets"]]
        assert {t["equipmentInstanceId"] for t in targets}=={o["sameEquipment"]}
        assert len({json.dumps(t["semanticDefinitionRef"],sort_keys=True) for t in targets})==1
        return True
    check("same-equipment-two-objects",base)
    for path in (ROOT/"contracts/2.0.0").glob("*.schema.json"):
        check("meta:"+path.name,lambda path=path:(Draft202012Validator.check_schema(vc.load(path)) is None))
    for sample in vc.load(BASE/"oracles.json")["samples"]:
        def oracle(sample=sample):
            graph=next(vc.load(p) for p in (FIX/"graphs").glob("*.json") if vc.load(p)["id"]==sample["graphId"])
            values={(id,"1.0.0"):v for id,v in sample["samples"].items()}
            assert p3.decode_fixture(graph,values)==sample["expected"]
            return True
        check("oracle:"+sample["id"],oracle)
    for case in vc.load(BASE/"invalid-cases.json")["cases"]:
        def negative(case=case):
            with tempfile.TemporaryDirectory() as t:
                p=Path(t)/"package";p3.shutil.copytree(FIX,p);mutate(p,case["mutation"])
                errors,_=p3.validate_package(p);rules={e["ruleCode"] for e in errors}
                assert set(case["rules"])<=rules,sorted(rules)
            return True
        check("reject:"+case["id"],negative)
    graph=vc.load(FIX/"graphs/motor-a.json")
    for id,values,expected in [
        ("missing-input",{("motor-a-low","1.0.0"):1},"sample.missing"),
        ("negative-word",{("motor-a-low","1.0.0"):-1,("motor-a-high","1.0.0"):2},"sample.u16-range"),
        ("word-overflow",{("motor-a-low","1.0.0"):65536,("motor-a-high","1.0.0"):2},"sample.u16-range"),
        ("boolean-is-not-word",{("motor-a-low","1.0.0"):True,("motor-a-high","1.0.0"):2},"sample.u16-range")]:
        def badsample(values=values,expected=expected):
            try:p3.decode_fixture(graph,values)
            except ValueError as e:return str(e)==expected
            return False
        check("oracle-reject:"+id,badsample)
    def renamed():
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"package";p3.shutil.copytree(FIX,p)
            before=p3.validate_package(p)[1]
            rewrite(p,"targets/motor-a.json",lambda d:d.update(label="Renamed display only"));rehash(p)
            errors,after=p3.validate_package(p)
            return not errors and before==after
    check("display-label-does-not-change-identity",renamed)
    def migrate_roundtrip():
        with tempfile.TemporaryDirectory() as t:
            folder=Path(t);legacy=folder/"legacy";legacy.mkdir()
            w=vc.load(ROOT/"fixtures/realistic/workspace.json");server.build_package(w,legacy)
            before={p.relative_to(legacy):vc.hashed(p) for p in legacy.rglob("*") if p.is_file()}
            assignments=vc.load(BASE/"migration-assignments.json");dest=folder/"v2"
            p3.migrate(legacy,dest,assignments)
            errors,details=p3.validate_package(dest);assert not errors,errors
            assert len(details["bindings"])==32 and details["targets"]==sorted(assignments.values())
            for entry in vc.load(dest/"proposal.json")["files"]:
                if entry["kind"] in ("source-definition","semantic-definition","evidence-artifact"):assert vc.hashed(dest/entry["path"])==before[Path(entry["path"])]
            assert before=={p.relative_to(legacy):vc.hashed(p) for p in legacy.rglob("*") if p.is_file()}
            for prior in w["mappings"]:
                current=next(vc.load(dest/e["path"]) for e in vc.load(dest/"proposal.json")["files"] if e["id"]==prior["id"])
                for old,new in zip(prior["mappings"],current["mappings"]):
                    assert new["valueRef"]["sourceRef"]==old["sourceRef"]
                    assert new["memberPath"]==[{"kind":"member","memberId":old["targetMemberId"]}]
                    for k in ("mappingId","transform","outputUnit","invalidValuePolicy","evidenceRefs"):assert old[k]==new[k]
            try:p3.migrate(legacy,folder/"missing",{})
            except ValueError:assert not (folder/"missing").exists()
            else:raise AssertionError("Guessed object IDs")
            try:p3.migrate(legacy,dest,assignments)
            except ValueError:pass
            else:raise AssertionError("Overwrote destination")
        return True
    check("explicit-migration-byte-preservation-and-reload",migrate_roundtrip)
    def legacy_boundary():
        d=vc.load(FIX/"mappings/motor-a.json")
        assert vc.validate_schema("mapping-set",d)
        try:server.schema(d,"mapping-set")
        except server.Invalid:return True
        return False
    check("legacy-api-rejects-v2-cleanly",legacy_boundary)
    def original_schemas():
        baseline=vc.load(BASE/"legacy-schema-baseline.json")
        return all(vc.hashed(ROOT/rel)==digest for rel,digest in baseline.items())
    check("legacy-1x-schema-bytes-unchanged",original_schemas)
    def reordered_graph():
        reordered=copy.deepcopy(graph);reordered["nodes"].reverse()
        reordered["nodes"][1]["inputs"]=dict(reversed(list(reordered["nodes"][1]["inputs"].items())))
        return p3.decode_fixture(reordered,{("motor-a-low","1.0.0"):1,("motor-a-high","1.0.0"):2})=={"counter":131073,"result":131073}
    check("node-and-input-order-independent",reordered_graph)
    def duplicate_across_sets():
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"package";p3.shutil.copytree(FIX,p)
            d=vc.load(p/"mappings/motor-a.json");d["id"]="another-set";d["mappings"]=d["mappings"][:1];d["mappings"][0]["mappingId"]="another-binding"
            rel="mappings/duplicate.json";vc.save(p/rel,d)
            prop=vc.load(p/"proposal.json");prop["files"].append({"path":rel,"kind":d["kind"],"id":d["id"],"version":d["version"],"sha256":vc.hashed(p/rel)});vc.save(p/"proposal.json",prop)
            return any(e["ruleCode"]=="mapping.duplicate-target" for e in p3.validate_package(p)[0])
    check("duplicate-target-across-mapping-sets",duplicate_across_sets)
    hashes={str(p.relative_to(ROOT)).replace(chr(92),"/"):vc.hashed(p) for p in [*BASE.rglob("*"),*(ROOT/"contracts").rglob("*.json"),Path(__file__),ROOT/"scripts/p3a_contracts.py",ROOT/"backend/server.py"] if p.is_file()}
    report={"scope":"P3-A contract/fixture acceptance; no device communication","networkDenied":True,"total":len(results),"passed":sum(r["passed"] for r in results),"failed":[r for r in results if not r["passed"]],"results":results,"sha256":hashes}
    if a.report:vc.save(a.report,report)
    print(json.dumps({k:v for k,v in report.items() if k not in ("results","sha256")},ensure_ascii=True,indent=2))
    return bool(report["failed"])
if __name__=="__main__":sys.exit(main())
