"""Bounded math browser/SQLite/CLI acceptance under existing offline image."""
import copy,hashlib,json,os,shutil,subprocess,sys,tempfile,threading,traceback,tarfile
from pathlib import Path
E=Path("/work/evidence");E.mkdir(parents=True,exist_ok=True)
R=Path("/work/tyr");report={"checks":[],"passed":False,"fieldPoV":"not-performed","deviceCommunication":"excluded","externalSQL":"excluded","writeExecution":"excluded"}
def save(): (E/"p3cb-results.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
def check(id,ok,**detail):
    print(id,bool(ok),flush=True);report["checks"].append(dict(id=id,passed=bool(ok),**detail));save();assert ok,(id,detail)
def java(*args):
    p=subprocess.run(["java","-jar",str(JAR),*map(str,args)],capture_output=True,text=True,timeout=120)
    assert p.returncode in (0,1),p.stderr
    v=json.loads(p.stdout);(E/("java-%02d.json"%len(list(E.glob("java-*.json"))))).write_text(json.dumps(v,indent=2))
    return v
def main():
    shutil.copyfile("/input/package.tar","/tmp/package.tar")
    with tarfile.open("/tmp/package.tar") as t:t.extractall("/work",filter="data")
    report["inputSha256"]={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for name in ["backend","frontend","scripts","contracts","fixtures"] for p in (R/name).rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    report["jarSha256"]=hashlib.sha256((R.parent/"bifrost/gates/target/bifrost-gates.jar").read_bytes()).hexdigest()
    save()
    os.chdir(R);sys.path[:0]=[str(R/"backend"),str(R/"scripts")]
    import server
    from playwright.sync_api import sync_playwright
    global JAR;JAR=R.parent/"bifrost/gates/target/bifrost-gates.jar"
    registry=E/"registry";store=server.Store(E/"editor.sqlite3");store.migrate(0,{})
    w=server.contracts.load(R/"fixtures/p3cb/workspace.json");store.save(1,w)
    http=server.make_server(store,0,JAR,registry);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
    origin="http://127.0.0.1:"+str(http.server_port)
    errors=[];requests=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path="/usr/bin/chromium",headless=True,args=["--no-sandbox"])
        page=browser.new_page(viewport={"width":1400,"height":1050});page.set_default_timeout(90000)
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.on("request",lambda r:requests.append(r.url))
        page.on("dialog",lambda d:d.accept() if d.type=="beforeunload" else d.dismiss())
        page.goto(origin);page.locator("#counts strong").first.wait_for();check("browser.localhost-loaded",True)
        page.locator('[data-tab="graphs"]').click()
        page.locator("#graph-id").fill("ui-bounded")
        page.locator("#graph-equipment").select_option("line-a-motor-melsec")
        page.locator("#node-id-0").fill("root")
        page.locator("#node-op-0").select_option("sqrt")
        page.locator("#node-value-0").select_option("s:pressure-up")
        page.locator("#node-unit-0").select_option("1")
        page.locator("#add-node").click()
        page.locator("#node-id-1").fill("limit")
        page.locator("#node-op-1").select_option("clamp")
        page.locator("#node-value-1").select_option("n:root")
        page.locator("#node-unit-1").select_option("1")
        page.locator("#node-bound-low-1").fill("1");page.locator("#node-bound-high-1").fill("2")
        with page.expect_response(lambda r:r.url==origin+"/api/workspace" and r.request.method=="PUT") as saved:
            page.locator('#graph-form button[type="submit"]').click()
        check("browser.author-save-both-ops",saved.value.status==200,response=saved.value.json())
        page.locator("#revision").filter(has_text="저장 revision 3").wait_for()
        authored=next(g for g in store.read()["workspace"]["graphs"] if g["id"]=="ui-bounded")
        check("sqlite.new-contract-roundtrip",authored["schemaVersion"]=="2.11.0" and authored["nodes"][1]["low"]=="1" and server.Store(store.path).read()==store.read())
        page.locator('[data-tab="mappings"]').click()
        page.locator('[data-edit="mapping"][data-id="pressure-direct-mapping"]').click()
        page.locator("#bind-source-0").select_option(json.dumps(["graph","ui-bounded","limit"],separators=(",",":")))
        with page.expect_response(lambda r:r.url==origin+"/api/workspace" and r.request.method=="PUT") as mapped:
            page.locator('#mapping-form button[type="submit"]').click()
        check("browser.map-result",mapped.value.status==200,response=mapped.value.json())
        page.locator("#revision").filter(has_text="저장 revision 4").wait_for()
        page.reload();page.locator("#counts strong").first.wait_for()
        page.locator('[data-tab="graphs"]').click();page.locator('[data-edit="graph"][data-id="ui-bounded"]').click()
        check("browser.reload-bounds",page.locator("#node-bound-high-1").input_value()=="2" and page.locator("#node-op-0").input_value()=="sqrt")
        snapshot=store.read()
        page.locator('[data-tab="preview"]').click();page.locator("#virtual-0").fill("09 00")
        with page.expect_response(lambda r:r.url.endswith("/api/preview")) as pr:
            page.locator('#preview-form button[type="submit"]').click()
        result=pr.value.json();stages=[x["stage"] for x in result["trace"]]
        check("browser.decode-sqrt-clamp-cast",result["result"]["value"]=="2" and "loss.clamp" in {i["code"] for i in result["issues"]} and stages.index("graph:sqrt")<stages.index("graph:clamp")<stages.index("transform:cast"),preview=result)
        check("sqlite.preview-readonly",store.read()==snapshot)
        check("browser.loss-message-readable","before=3; bounds=[1, 2]; after=2; branch=high" in page.locator("#preview-result").inner_text() and "[object Object]" not in page.locator("#preview-result").inner_text())
        page.locator("#preview-result h2").wait_for();page.screenshot(path=str(E/"p3cb-preview.png"),full_page=True)
        page.locator('[data-tab="publication"]').click()
        page.locator("#submission-id").fill("p3cb-ui");page.locator("#submission-stream").fill("p3cb-offline")
        page.locator("#submission-by").fill("proposer");page.locator("#submission-mapping").select_option("pressure-direct-mapping")
        with page.expect_response(lambda r:r.url.endswith("/api/submissions") and r.request.method=="POST") as ex:
            page.locator('#submission-form button[type="submit"]').click()
        record=ex.value.json();check("browser.export-closure",ex.value.status==200 and record["preflightFindings"]==[],record=record)
        bundle=Path(record["path"]);v=java("mapping","validate",bundle);check("java.independent-validation",v["accepted"])
        with tempfile.TemporaryDirectory(prefix="p3cb-keys-") as kd:
            keys=Path(kd);identity=registry/"identity";identity.mkdir(parents=True,exist_ok=True)
            public=[java("identity","keygen",principal,"--out",keys) for principal in ["proposer","approver"]]
            (identity/"authorized-keys.jsonl").write_text("".join(json.dumps(v)+"\n" for v in public))
            policy={"version":"1.0.0","default":"deny","rules":[{"id":"p3cb-"+action,"principal":who,"action":action,"target":"mapping-publication","kind":"mapping-release","ref":"p3cb-offline"} for action,who in [("publish","proposer"),("approve","approver")]]}
            (identity/"activation-policy.json").write_text(json.dumps(policy))
            approval=java("mapping","approve",registry,bundle,"p3cb-approval","--by","proposer","--by-key",keys/"proposer.key","--approved-by","approver","--approved-by-key",keys/"approver.key")
            check("java.two-key-approval",approval.get("kind")!="mapping-refusal")
            release=java("mapping","publish",registry,bundle,"p3cb-release","1.0.0","--approval","p3cb-approval")
            check("java.publish-without-activation",release.get("kind")!="mapping-refusal" and release["activation"]=="not-performed")
        page.locator('[data-submission-refresh="p3cb-ui"]').wait_for()
        with page.expect_response(lambda r:r.url.endswith("/api/submission-refresh")) as rr:page.locator('[data-submission-refresh="p3cb-ui"]').click()
        check("browser.published-status",rr.value.json()["publicationState"]=="published")
        check("browser.no-errors-or-outbound",not errors and all(u.startswith(origin) for u in requests),errors=errors)
        browser.close()
    http.shutdown();http.server_close();thread.join()
    for script,args,name in [("test_p3cb.py",[],"new-tests"),("test_a07.py",["--report",str(E/"a07.json")],"a07"),("test_p7.py",["--report",str(E/"regression.json")],"regression")]:
        p=subprocess.run([sys.executable,"-B",R/"scripts"/script,*args],capture_output=True,text=True,timeout=1200)
        (E/(name+"-runner.log")).write_text(p.stdout+p.stderr)
        check("tests."+name,p.returncode==0,returncode=p.returncode)
    report["passed"]=True;save()
if __name__=="__main__":
    try:main()
    except Exception:report["error"]=traceback.format_exc();save();raise
    finally:
        with tarfile.open("/evidence/runtime-evidence.tar","w") as t:t.add(E,arcname=".")
