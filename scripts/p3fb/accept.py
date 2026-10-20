"""Logical structures browser/SQLite/CLI acceptance under existing offline image."""
import copy,hashlib,json,os,shutil,subprocess,sys,tempfile,threading,traceback,tarfile
from pathlib import Path
E=Path("/work/evidence");E.mkdir(parents=True,exist_ok=True)
R=Path("/work/tyr");report={"checks":[],"passed":False,"fieldPoV":"not-performed","deviceCommunication":"excluded","externalSQL":"excluded","writeExecution":"excluded"}
def save(): (E/"p3fb-results.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
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
    w=server.contracts.load(R/"fixtures/p3fb/timed-workspace.json");store.save(1,w)
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
        page.locator('[data-edit="graph"][data-id="bounded-pressure"]').click()
        check("browser.graph-candidate-reload",page.locator("#node-candidates-3").input_value()=="n:scaled-up, n:converted-down, n:difference")
        page.locator("#node-candidates-3").fill("")
        for value in ["n:scaled-up","n:converted-down","n:difference"]:
            page.locator("#candidate-picker-3").select_option(value);page.locator("#candidate-add-3").click()
        check("browser.author-candidate-list","Decimal / kPa" in page.locator("#candidate-summary-3").inner_text())
        page.locator("#node-policy-3").select_option("default-candidate")
        page.locator("#node-default-3").fill("2")
        with page.expect_response(lambda r:r.url==origin+"/api/workspace" and r.request.method=="PUT") as saved:
            page.locator('#graph-form button[type="submit"]').click()
        check("browser.save-graph-candidates",saved.value.status==200,response=saved.value.json())
        page.locator("#revision").filter(has_text="저장 revision 3").wait_for()
        stored=store.read()
        check("sqlite.graph-candidate-roundtrip",stored["workspace"]["graphs"][0]["schemaVersion"]=="2.13.0" and server.Store(store.path).read()==stored)
        page.reload();page.locator("#counts strong").first.wait_for()
        page.locator('[data-tab="graphs"]').click();page.locator('[data-edit="graph"][data-id="bounded-pressure"]').click()
        check("browser.graph-candidate-reopen","n:difference" in page.locator("#node-candidates-3").input_value() and page.locator("#node-default-3").input_value()=="2")
        page.locator('[data-tab="preview"]').click()
        samples=server.contracts.load(R/"fixtures/p3fb/samples.json")
        def source_row(id):return page.locator('.sample-input[data-source="'+id+'"]')
        for id,v in samples.items():source_row(id).locator('[id^="virtual-"]:not([id^="virtual-quality"]):not([id^="virtual-source-time"]):not([id^="virtual-server-time"]):not([id^="virtual-sequence"])').first.fill(v["bytesHex"])
        def value(id,text):source_row(id).locator('input[id^="virtual-"]').first.fill(text)
        def evaluate():
            with page.expect_response(lambda r:r.url.endswith("/api/preview")) as pr:page.locator('#preview-form button[type="submit"]').click()
            check("http.preview-ok",pr.value.status==200);return pr.value.json()
        first=evaluate()
        check("browser.normalized-graph",first["result"]["value"]=="100" and first["quality"]=="good" and any(t["stage"]=="graph:linear" for t in first["trace"]))
        value("selector-index","0100")
        second=evaluate()
        check("browser.equal-value-origin-change",second["result"]["value"]=="100" and second["selections"][-1]["sourceChanged"] and second["selections"][-1]["candidateRef"]["nodeId"]=="converted-down")
        check("browser.selected-input-metadata",second["selections"][-1]["selectedInputDataValues"][0]["sourceId"]=="pressure-down" and "not-evaluated" in page.locator("#preview-result").inner_text())
        source_row("pressure-up").locator('[id^="virtual-quality-"]').select_option("bad")
        check("browser.unselected-bad-ignored",evaluate()["result"]["value"]=="100")
        value("selector-index","0200");bad=evaluate()
        check("browser.derived-selected-bad",bad["result"] is None and any(i["code"]=="quality.bad-input" for i in bad["issues"]) and bad["selectionValueValidated"] is False)
        source_row("pressure-up").locator('[id^="virtual-quality-"]').select_option("good")
        source_row("pressure-down").locator('[id^="virtual-source-time-"]').fill("2000-01-01T00:00:00Z")
        stale=evaluate();check("browser.selected-stale",stale["result"] is None and any(i["code"]=="time.stale-input" for i in stale["issues"]))
        source_row("pressure-down").locator('[id^="virtual-source-time-"]').fill("2026-10-17T09:59:59Z")
        skew=evaluate();check("browser.selected-skew",skew["result"] is None and any(i["code"]=="time.skew-exceeded" for i in skew["issues"]))
        source_row("pressure-down").locator('[id^="virtual-source-time-"]').fill("2026-10-17T10:00:00Z")
        value("selector-index","0900");default=evaluate()
        check("browser.default-graph-result",default["result"]["value"]=="0" and default["selections"][-1]["defaultUsed"])
        page.locator("#scenario-id-d").fill("p3fb-virtual");page.locator("#scenario-label-d").fill("Finite graph candidates offline")
        with page.expect_response(lambda r:r.url.endswith("/api/scenarios") and r.request.method=="POST") as scenario:
            page.locator("#scenario-save-d").click()
        check("sqlite.virtual-scenario-save",scenario.value.status==200 and server.Store(store.path).scenarios()["scenarios"][0]["scenario"]["samples"]["selector-index"]["value"]["bytesHex"]=="0900")
        check("sqlite.preview-readonly",store.read()==stored)
        page.locator("body").press("Control+Home");page.screenshot(path=str(E/"p3fb-preview.png"),full_page=True)
        page.locator('[data-tab="publication"]').click()
        page.locator("#submission-id").fill("p3fb-ui");page.locator("#submission-stream").fill("p3fb-offline")
        page.locator("#submission-by").fill("proposer");page.locator("#submission-mapping").select_option("bounded-pressure-mapping")
        with page.expect_response(lambda r:r.url.endswith("/api/submissions") and r.request.method=="POST") as ex:
            page.locator('#submission-form button[type="submit"]').click()
        record=ex.value.json();check("browser.export-closure",ex.value.status==200 and record["preflightFindings"]==[],record=record)
        bundle=Path(record["path"]);v=java("mapping","validate",bundle);check("java.independent-validation",v["accepted"])
        with tempfile.TemporaryDirectory(prefix="p3fb-keys-") as kd:
            keys=Path(kd);identity=registry/"identity";identity.mkdir(parents=True,exist_ok=True)
            public=[java("identity","keygen",principal,"--out",keys) for principal in ["proposer","approver"]]
            (identity/"authorized-keys.jsonl").write_text("".join(json.dumps(v)+"\n" for v in public))
            policy={"version":"1.0.0","default":"deny","rules":[{"id":"p3fb-"+action,"principal":who,"action":action,"target":"mapping-publication","kind":"mapping-release","ref":"p3fb-offline"} for action,who in [("publish","proposer"),("approve","approver")]]}
            (identity/"activation-policy.json").write_text(json.dumps(policy))
            approval=java("mapping","approve",registry,bundle,"p3fb-approval","--by","proposer","--by-key",keys/"proposer.key","--approved-by","approver","--approved-by-key",keys/"approver.key")
            check("java.two-key-approval",approval.get("kind")!="mapping-refusal")
            release=java("mapping","publish",registry,bundle,"p3fb-release","1.0.0","--approval","p3fb-approval")
            check("java.publish-without-activation",release.get("kind")!="mapping-refusal" and release["activation"]=="not-performed")
        page.locator('[data-submission-refresh="p3fb-ui"]').wait_for()
        with page.expect_response(lambda r:r.url.endswith("/api/submission-refresh")) as rr:page.locator('[data-submission-refresh="p3fb-ui"]').click()
        check("browser.published-status",rr.value.json()["publicationState"]=="published")
        check("browser.no-errors-or-outbound",not errors and all(u.startswith(origin) for u in requests),errors=errors)
        browser.close()
    http.shutdown();http.server_close();thread.join()
    suites=[("test_p3fb.py",[],"new-tests"),("test_p3eb.py",[],"logical-structure-regression"),("test_p3cb.py",[],"bounded-math-regression"),("test_a07.py",["--report",str(E/"a07.json")],"a07"),("test_p7.py",["--report",str(E/"regression.json")],"regression")]
    if os.environ.get("TYR_P3FB_UI_ONLY")=="1":suites=[]
    report["regressionScope"]="separate-full-run" if not suites else "full"
    for script,args,name in suites:
        p=subprocess.run([sys.executable,"-B",R/"scripts"/script,*args],capture_output=True,text=True,timeout=1200)
        (E/(name+"-runner.log")).write_text(p.stdout+p.stderr)
        check("tests."+name,p.returncode==0,returncode=p.returncode)
    report["passed"]=True;save()
if __name__=="__main__":
    try:main()
    except Exception:report["error"]=traceback.format_exc();save();raise
    finally:
        with tarfile.open("/evidence/runtime-evidence.tar","w") as t:t.add(E,arcname=".")
