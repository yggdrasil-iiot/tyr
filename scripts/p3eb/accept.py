"""Logical structures browser/SQLite/CLI acceptance under existing offline image."""
import copy,hashlib,json,os,shutil,subprocess,sys,tempfile,threading,traceback,tarfile
from pathlib import Path
E=Path("/work/evidence");E.mkdir(parents=True,exist_ok=True)
R=Path("/work/tyr");report={"checks":[],"passed":False,"fieldPoV":"not-performed","deviceCommunication":"excluded","externalSQL":"excluded","writeExecution":"excluded"}
def save(): (E/"p3eb-results.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
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
    w=server.contracts.load(R/"fixtures/p3eb/workspace.json");store.save(1,w)
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
        page.locator('[data-tab="structures"]').click()
        page.locator("#structure-id").fill("ui-logical")
        members=json.loads(page.locator("#structure-members").input_value())
        members[0]["members"][0]["unit"]={"status":"known","code":"kPa"}
        members[0]["members"][0]["semanticId"]="urn:tyr:concept:pressure.actual"
        page.locator("#structure-members").fill(json.dumps(members))
        page.locator("#structure-tree-refresh").click()
        def add(parent,id,kind,uri,role="measurement"):
            page.locator("#structure-parent").select_option(json.dumps(parent,separators=(",",":")))
            page.locator("#structure-member-id").fill(id);page.locator("#structure-member-name").fill(id)
            page.locator("#structure-semantic-id").fill(uri);page.locator("#structure-node-type").select_option(kind)
            page.locator("#structure-node-unit").select_option("kPa");page.locator("#structure-node-role").select_option(role)
            page.locator("#structure-add").click()
        add([],"modules","StructureArray","urn:tyr:concept:ui.modules")
        add(["modules"],"pressure","Structure","urn:tyr:concept:skid.module.pressure")
        add(["modules","pressure"],"actual","Double","urn:tyr:concept:pressure.actual")
        add(["modules","pressure"],"target","Double","urn:tyr:concept:pressure.target","setpoint")
        check("browser.expanded-tree","modules[1].pressure.actual" in page.locator("#structure-tree").inner_text() and "modules[2].pressure.actual" in page.locator("#structure-tree").inner_text())
        with page.expect_response(lambda r:r.url==origin+"/api/workspace" and r.request.method=="PUT") as saved:
            page.locator('#structure-model-form button[type="submit"]').click()
        check("browser.author-nested-array-model",saved.value.status==200,response=saved.value.json())
        page.locator("#revision").filter(has_text="저장 revision 3").wait_for()
        page.locator('[data-tab="targets"]').click()
        page.locator("#target-id").fill("ui-logical-skid");page.locator("#target-label").fill("Offline logical skid")
        page.locator("#target-equipment").select_option("line-a-motor-melsec")
        page.locator("#target-model").select_option("ui-logical");page.locator("#target-evidence").select_option("structure-melsec-actual")
        with page.expect_response(lambda r:r.url==origin+"/api/workspace" and r.request.method=="PUT") as ts:
            page.locator('#target-form button[type="submit"]').click()
        check("browser.author-target",ts.value.status==200)
        page.locator("#revision").filter(has_text="저장 revision 4").wait_for()
        page.locator('[data-tab="mappings"]').click()
        page.locator("#mapping-id").fill("ui-logical-mapping");page.locator("#mapping-target").select_option("ui-logical-skid")
        choices=[["source","structure-melsec-actual"],["graph","structure-melsec-graph","first"],["graph","structure-melsec-graph","first-target"],["graph","structure-melsec-graph","last"],["graph","structure-melsec-graph","last-target"]]
        paths=["process.actual","modules[1].pressure.actual","modules[1].pressure.target","modules[2].pressure.actual","modules[2].pressure.target"]
        def row(path):return page.locator(".binding-row").filter(has=page.locator("h3",has_text=path+" ·")).first
        for path,choice in zip(paths,choices):row(path).locator('[id^="bind-source-"]').select_option(json.dumps(choice,separators=(",",":")))
        def actual(doc,index):
            return next(b for b in doc["mappings"] if b["memberPath"]==[{"kind":"member","memberId":"modules"},{"kind":"index","indices":[index]},{"kind":"member","memberId":"pressure"},{"kind":"member","memberId":"actual"}])
        with page.expect_response(lambda r:r.url==origin+"/api/workspace" and r.request.method=="PUT") as mapped:
            page.locator('#mapping-form button[type="submit"]').click()
        check("browser.map-distinct-indices",mapped.value.status==200,response=mapped.value.json())
        page.locator("#revision").filter(has_text="저장 revision 5").wait_for()
        mapdoc=next(m for m in store.read()["workspace"]["mappings"] if m["id"]=="ui-logical-mapping")
        check("sqlite.full-paths-roundtrip",mapdoc["schemaVersion"]=="2.12.0" and len({json.dumps(b["memberPath"],sort_keys=True) for b in mapdoc["mappings"]})==5 and server.Store(store.path).read()==store.read())
        page.reload();page.locator("#counts strong").first.wait_for()
        page.locator('[data-tab="mappings"]').click();page.locator('[data-edit="mapping"][data-id="ui-logical-mapping"]').click()
        check("browser.reload-leaf-selections",row("modules[1].pressure.actual").locator('[id^="bind-source-"]').input_value()!=row("modules[2].pressure.actual").locator('[id^="bind-source-"]').input_value())
        # Existing quality-policy wrapper must preserve index-specific rows too.
        row("modules[2].pressure.actual").locator('[id^="time-enabled-"]').select_option("on")
        row("modules[2].pressure.actual").locator('[id^="time-age-"]').fill("1234")
        with page.expect_response(lambda r:r.url==origin+"/api/workspace" and r.request.method=="PUT") as timed:
            page.locator('#mapping-form button[type="submit"]').click()
        check("browser.index-specific-temporal-save",timed.value.status==200)
        page.locator("#revision").filter(has_text="저장 revision 6").wait_for()
        mapped_doc=next(m for m in store.read()["workspace"]["mappings"] if m["id"]=="ui-logical-mapping")
        check("sqlite.temporal-policy-not-conflated",actual(mapped_doc,2)["temporalPolicy"]["maxAgeMs"]==1234 and "temporalPolicy" not in actual(mapped_doc,1))
        page.locator('[data-edit="mapping"][data-id="ui-logical-mapping"]').click()
        row("modules[2].pressure.actual").locator('[id^="time-enabled-"]').select_option("off")
        with page.expect_response(lambda r:r.url==origin+"/api/workspace" and r.request.method=="PUT") as untimed:
            page.locator('#mapping-form button[type="submit"]').click()
        check("browser.restore-value-only-policy",untimed.value.status==200)
        page.locator("#revision").filter(has_text="저장 revision 7").wait_for()
        snapshot=store.read()
        page.locator('[data-tab="structures"]').click()
        page.locator('[data-edit="semantic"][data-id="ui-logical"]').click()
        check("browser.reload-model-tree","modules[2].pressure.target" in page.locator("#structure-tree").inner_text() and page.locator("#structure-id").input_value()=="ui-logical")
        page.locator("#logical-target").select_option("ui-logical-skid")
        samples=server.contracts.load(R/"fixtures/p3eb/samples.json");page.locator("#logical-samples").fill(json.dumps(samples))
        with page.expect_response(lambda r:r.url.endswith("/api/logical-preview")) as pr:
            page.locator('#logical-preview-form button[type="submit"]').click()
        result=pr.value.json()
        expected={"process":{"actual":"150"},"modules":[{"pressure":{"actual":"100","target":"110"}},{"pressure":{"actual":"220","target":"210"}}]}
        check("browser.complete-object-oracle",result["result"]==expected and result["quality"]=="good" and not result["atomicSnapshot"],preview=result)
        check("sqlite.preview-readonly",store.read()==snapshot)
        page.locator("#logical-preview-result h2").wait_for();page.locator("body").press("Control+Home");page.screenshot(path=str(E/"p3eb-preview.png"),full_page=True)
        page.locator('[data-tab="preview"]').click()
        page.locator("#preview-binding").select_option(json.dumps(["ui-logical-mapping",actual(mapped_doc,2)["mappingId"]],separators=(",",":")))
        sample=samples["array-pressures-melsec"]
        page.locator("#virtual-0").fill(sample["bytesHex"])
        with page.expect_response(lambda r:r.url.endswith("/api/preview")) as leaf:
            page.locator('#preview-form button[type="submit"]').click()
        check("browser.leaf-decoding-cast",leaf.value.json()["result"]["value"]=="220")
        page.locator('[data-tab="publication"]').click()
        page.locator("#submission-id").fill("p3eb-ui");page.locator("#submission-stream").fill("p3eb-offline")
        page.locator("#submission-by").fill("proposer");page.locator("#submission-mapping").select_option("ui-logical-mapping")
        with page.expect_response(lambda r:r.url.endswith("/api/submissions") and r.request.method=="POST") as ex:
            page.locator('#submission-form button[type="submit"]').click()
        record=ex.value.json();check("browser.export-closure",ex.value.status==200 and record["preflightFindings"]==[],record=record)
        bundle=Path(record["path"]);v=java("mapping","validate",bundle);check("java.independent-validation",v["accepted"])
        with tempfile.TemporaryDirectory(prefix="p3eb-keys-") as kd:
            keys=Path(kd);identity=registry/"identity";identity.mkdir(parents=True,exist_ok=True)
            public=[java("identity","keygen",principal,"--out",keys) for principal in ["proposer","approver"]]
            (identity/"authorized-keys.jsonl").write_text("".join(json.dumps(v)+"\n" for v in public))
            policy={"version":"1.0.0","default":"deny","rules":[{"id":"p3eb-"+action,"principal":who,"action":action,"target":"mapping-publication","kind":"mapping-release","ref":"p3eb-offline"} for action,who in [("publish","proposer"),("approve","approver")]]}
            (identity/"activation-policy.json").write_text(json.dumps(policy))
            approval=java("mapping","approve",registry,bundle,"p3eb-approval","--by","proposer","--by-key",keys/"proposer.key","--approved-by","approver","--approved-by-key",keys/"approver.key")
            check("java.two-key-approval",approval.get("kind")!="mapping-refusal")
            release=java("mapping","publish",registry,bundle,"p3eb-release","1.0.0","--approval","p3eb-approval")
            check("java.publish-without-activation",release.get("kind")!="mapping-refusal" and release["activation"]=="not-performed")
        page.locator('[data-submission-refresh="p3eb-ui"]').wait_for()
        with page.expect_response(lambda r:r.url.endswith("/api/submission-refresh")) as rr:page.locator('[data-submission-refresh="p3eb-ui"]').click()
        check("browser.published-status",rr.value.json()["publicationState"]=="published")
        check("browser.no-errors-or-outbound",not errors and all(u.startswith(origin) for u in requests),errors=errors)
        browser.close()
    http.shutdown();http.server_close();thread.join()
    suites=[("test_p3eb.py",[],"new-tests"),("test_p3cb.py",[],"bounded-math-regression"),("test_a07.py",["--report",str(E/"a07.json")],"a07"),("test_p7.py",["--report",str(E/"regression.json")],"regression")]
    if os.environ.get("TYR_P3EB_UI_ONLY")=="1":suites=[]
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
