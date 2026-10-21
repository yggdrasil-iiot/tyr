"""Verify raw A14 evidence and emit a separate current A01-A16 acceptance record."""
import argparse,hashlib,json,sqlite3
from pathlib import Path
R=Path(__file__).resolve().parents[1];OUT=R/"docs/verification"
def read(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def main():
    a=argparse.ArgumentParser();a.add_argument("run",type=Path);x=a.parse_args();run=x.run.resolve()
    result=read(run/"a14-results.json");assert result["passed"] and all(c["passed"] for c in result["checks"])
    docker=read(run/"docker-inspect-after.json")[0];host=docker["HostConfig"]
    assert host["NetworkMode"]=="none" and host["Dns"]==["127.0.0.1"] and "ALL" in host["CapDrop"]
    assert "no-new-privileges" in host["SecurityOpt"] and not host["PortBindings"]
    assert docker["State"]["ExitCode"]==0 and not docker["State"]["OOMKilled"]
    assert all(not m["RW"] or m["Destination"]=="/evidence" for m in docker["Mounts"])
    regression=read(run/"a14-regression.json");views=read(run/"a14-a07.json")
    assert regression["total"]==regression["passed"]==701 and not regression["failed"] and regression["inputsUnchanged"]
    assert views["total"]==views["passed"]==39 and not views["errors"] and not views["failures"]
    assert all(sha(R/p)==h for p,h in result["inputSha256"].items())
    old=read(OUT/"a07-final-artifacts.json")["sha256"]
    paths={p:h for p,h in old.items() if p.startswith(("contracts/","backend/","frontend/","fixtures/")) or p=="../bifrost/gates/target/bifrost-gates.jar"}
    delta=[p for p,h in paths.items() if sha(R/p)!=h]
    assert delta==["frontend/views.js"],delta
    contracts=list((R/"contracts").rglob("*.json"));assert len(contracts)==62
    original=read(OUT/"p7-validation.json")["sha256"]
    old_schemas={p:h for p,h in original.items() if p.startswith("contracts/")}
    assert len(old_schemas)==60 and all(sha(R/p)==h for p,h in old_schemas.items())
    files=["a14-results.json","a14-network.json","a14-java-network.json","a14-browser.json","a14-browser.har","a14-preview.png","a14-publication.png","a14-submission.zip","a14-a07.json","a14-a07.log","a14-regression.json","a14-regression.log","a14-regression-tests.log","a14-regression-p3a.json","a14-regression-p3a.log","docker-arguments.json","docker-inspect-before.json","docker-inspect-after.json","image-inspect.json","container.log"]
    import shutil
    for name in files:shutil.copy2(run/name,OUT/name)
    for p in run.glob("java-*.json"):shutil.copy2(p,OUT/("a14-"+p.name))
    acceptance=read(OUT/"a07-acceptance.json")
    acceptance["scope"]="P7 current bounded offline acceptance including A14 Linux OS network namespace; field PoV not performed"
    for c in acceptance["criteria"]:
        if c["id"]=="A14":
            c.update(status="pass",detail="Docker --network none; loopback-only IPv4/IPv6 namespace and localhost DNS. Real headless Chromium/Python/Java author/save/preview/sign/publish/reload; not host-wide Windows isolation.",executedTestIds=[c["id"] for c in result["checks"]])
    acceptance["summary"]={"pass":16,"partial":0,"partialIds":[],"fail":0,"fieldPoV":"not-performed"}
    acceptance["note"]="Prior P7/A07 reports remain historical. Inner test_p7 runner reports only its own Python guard scope; outer A14 Docker/OS evidence proves runtime-wide isolation. Existing Java mapping test report is retained as historical unchanged-JAR evidence, not a new Maven reactor run."
    acceptance["evidenceSha256"]={n:sha(OUT/n) for n in files}
    acceptance["a14Run"]=str(run);save(OUT/"a14-acceptance.json",acceptance)
    archive=read(run/"image-inspect.json")[0]
    summary={"checks":len(result["checks"]),"regression":701,"views":39,"networkMode":"none","imageId":docker["Image"],"rootFSLayers":archive["RootFS"]["Layers"],"inputArchiveSha256":sha(run/"package.tar"),"scope":result["scope"],"fieldPoV":"not-performed","productDeltaFromA07":delta,"unchangedProductPins":len(paths)-len(delta),"contractSchemas":62,"oldSchemasImmutable":60,"jarSha256":result["jarSha256"],"rawEvidence":str(run),"evidenceSha256":{n:sha(OUT/n) for n in files}}
    save(OUT/"a14-summary.json",summary);print(json.dumps({k:summary[k] for k in ["checks","regression","views","productDeltaFromA07"]}))
if __name__=="__main__":main()
