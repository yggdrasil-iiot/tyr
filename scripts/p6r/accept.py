"""Logical structures browser/SQLite/CLI acceptance under existing offline image."""
import copy,hashlib,json,os,shutil,subprocess,sys,tempfile,threading,traceback,tarfile
from pathlib import Path
E=Path("/work/evidence");E.mkdir(parents=True,exist_ok=True)
R=Path("/work/tyr");report={"checks":[],"passed":False,"fieldPoV":"not-performed","deviceCommunication":"excluded","externalSQL":"excluded","writeExecution":"excluded"}
def save(): (E/"p6r-results.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
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
    w=server.contracts.load(R/"fixtures/p4ab/local-workspace.json")
    w["sources"]=[row for row in w["sources"] if not row["definition"]["id"].endswith("-unresolved")]
    w["imports"][0]["adoptions"]=[a for a in w["imports"][0]["adoptions"] if not a["sourceId"].endswith("-unresolved")]
    store.save(1,w)
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
        page.locator('[data-tab="imports"]').click()
        page.locator("#workflow-source").wait_for()
        def metadata_ready():
            page.locator("#workflow-observation option").filter(has_text="unresolved").wait_for(state="attached")
        metadata_ready()
        bad=next(o for o in w["imports"][0]["observations"] if o["raw"].get("id")=="unresolved")
        page.locator("#workflow-observation").select_option(bad["id"])
        page.locator("#workflow-reviewer").fill("browser-reviewer");page.locator("#workflow-reason").fill("Explicit independent synthetic address D4000; preserve original pointer text")
        template=next(row["definition"] for row in w["sources"] if row["definition"]["accessProfileRef"]=="melsec-device-v1")
        page.locator("#workflow-template").select_option(template["id"]);page.locator("#workflow-template-copy").click()
        check("browser.explicit-template-copy",json.loads(page.locator("#workflow-source").input_value())["rawAddressText"]==template["rawAddressText"])
        explicit=server.contracts.load(R/"fixtures/p4ab/resolve-review.json")["source"]
        page.locator("#workflow-source").fill(json.dumps(explicit));page.locator("#workflow-record-key").fill("unresolved")
        with page.expect_response(lambda r:r.url.endswith("/api/import-review")) as reviewed:
            page.locator("#workflow-review-save").click()
        check("browser.explicit-resolution-save",reviewed.value.status==200,response=reviewed.value.json())
        page.locator("#revision").filter(has_text="저장 revision 3").wait_for()
        check("sqlite.original-observations-unchanged",store.read()["workspace"]["imports"][0]["observations"]==w["imports"][0]["observations"])
        metadata_ready();page.locator("#workflow-observation").select_option(bad["id"])
        with page.expect_response(lambda r:r.url.endswith("/api/import-adopt-reviewed")) as adopted:page.locator("#workflow-adopt").click()
        check("browser.adopt-reviewed-draft",adopted.value.status==200,response=adopted.value.json())
        page.locator("#revision").filter(has_text="저장 revision 4").wait_for()
        now=store.read()["workspace"];adopted_source=next(row for row in now["sources"] if row["definition"]["id"].endswith("-unresolved"))
        check("sqlite.resolved-source-is-draft",adopted_source["definition"]["status"]=="draft" and len(now["imports"][0]["reviews"])==3)
        incoming=server.contracts.load(R/"fixtures/p4ab/incoming-request.json")
        import base64
        file=E/"incoming.json";file.write_bytes(base64.b64decode(incoming["bytesBase64"]))
        page.locator("#import-id").fill("review-next");page.locator("#import-format").select_option("tyr-config-json-v1");page.locator("#import-equipment").select_option("import-line")
        page.locator("#import-origin").select_option("synthetic");page.locator("#import-file").set_input_files(str(file))
        page.locator("#workflow-reviewer").fill("browser-reviewer");page.locator("#workflow-reason").fill("Retain local pressure override and manual D4000, accept other file changes and preserve removed DB source")
        snapshot=store.read()
        with page.expect_response(lambda r:r.url.endswith("/api/import-merge-preview")) as compared:page.locator("#workflow-merge-preview").click()
        comparison=compared.value.json();check("browser.three-way-preview",compared.value.status==200 and not comparison["persisted"],comparison=comparison)
        check("sqlite.preview-readonly",store.read()==snapshot)
        actions=comparison["plan"]["actions"]
        check("browser.conflicts-and-removal-visible",any(a["classification"]=="conflict" for a in actions) and any(a["classification"]=="removed" for a in actions) and "Local speed label" in page.locator("#workflow-merge-result").inner_text())
        for i,a in enumerate(actions):
            for j,f in enumerate(a["fields"]):
                if f["conflict"]:page.locator("#merge-field-"+str(i)+"-"+str(j)).select_option("ours")
            if a["classification"]=="new":page.locator("#merge-mode-"+str(i)).select_option("apply")
            if a["recordKey"]=="unresolved":page.locator("#merge-mode-"+str(i)).select_option("retain")
        page.locator("body").press("Control+Home");page.screenshot(path=str(E/"p4ab-merge.png"),full_page=True)
        with page.expect_response(lambda r:r.url.endswith("/api/import-merge-apply")) as merged:page.locator("#workflow-merge-apply").click()
        check("browser.explicit-merge-save",merged.value.status==200,response=merged.value.json())
        page.locator("#revision").filter(has_text="저장 revision 5").wait_for()
        result=store.read()["workspace"]
        by_suffix=lambda suffix:next(row for row in result["sources"] if row["definition"]["id"].endswith(suffix))
        check("sqlite.stable-canonical-id",by_suffix("-speed-ab")["definition"]["id"]=="imp-review-base-speed-ab" and by_suffix("-speed-ab")["definition"]["rawAddressText"]=="Motor.ActualSpeedV2" and by_suffix("-speed-ab")["label"]=="Local speed label")
        check("sqlite.explicit-whole-source-retain",by_suffix("-unresolved")["definition"]["rawAddressText"]=="D4000")
        check("sqlite.conflict-and-note-preserved",by_suffix("-pressure-ua")["definition"]["rawAddressText"]=="Line.LocalPressure" and by_suffix("-pressure-ua")["note"]=="Local engineering note must survive")
        check("sqlite.removed-retained-template-alias-updated",by_suffix("-pressure-db")["importRef"]["batchId"]=="review-base" and by_suffix("-alias")["definition"]["access"]["addressIndex"]==5999)
        check("sqlite.reopen-history",server.Store(store.path).read()==store.read() and result["imports"][0]["bytesBase64"]==w["imports"][0]["bytesBase64"] and result["imports"][1]["reconciliation"]["choices"])
        page.reload();page.locator("#counts strong").first.wait_for();page.locator('[data-tab="imports"]').click()
        check("browser.history-reopen","review-next" in page.locator("#workflow-previous").inner_text() and "review-base" in page.locator("#workflow-previous").inner_text())
        page.locator('[data-tab="sources"]').click();page.locator('[data-edit="source"][data-id="imp-review-base-speed-ab"]').click()
        page.locator("#source-status").select_option("ready")
        with page.expect_response(lambda r:r.url==origin+"/api/workspace" and r.request.method=="PUT") as ready:page.locator('#source-form button[type="submit"]').click()
        check("browser.reconfirm-merged-source",ready.value.status==200,response=ready.value.json())
        page.locator("#revision").filter(has_text="저장 revision 6").wait_for()
        page.locator('[data-tab="preview"]').click();page.locator('input[id^="virtual-"]').first.fill("1500")
        with page.expect_response(lambda r:r.url.endswith("/api/preview")) as virtual:page.locator('#preview-form button[type="submit"]').click()
        check("browser.canonical-preview-after-merge",virtual.value.json()["result"]["value"]=="1500")
        page.locator('[data-tab="publication"]').click()
        page.locator("#submission-id").fill("p4ab-ui");page.locator("#submission-stream").fill("p4ab-offline")
        page.locator("#submission-by").fill("proposer");page.locator("#submission-mapping").select_option("import-speed-mapping")
        with page.expect_response(lambda r:r.url.endswith("/api/submissions") and r.request.method=="POST") as ex:
            page.locator('#submission-form button[type="submit"]').click()
        record=ex.value.json();check("browser.export-closure",ex.value.status==200 and record["preflightFindings"]==[],record=record)
        bundle=Path(record["path"]);v=java("mapping","validate",bundle);check("java.independent-validation",v["accepted"])
        with tempfile.TemporaryDirectory(prefix="p4ab-keys-") as kd:
            keys=Path(kd);identity=registry/"identity";identity.mkdir(parents=True,exist_ok=True)
            public=[java("identity","keygen",principal,"--out",keys) for principal in ["proposer","approver"]]
            (identity/"authorized-keys.jsonl").write_text("".join(json.dumps(v)+"\n" for v in public))
            policy={"version":"1.0.0","default":"deny","rules":[{"id":"p4ab-"+action,"principal":who,"action":action,"target":"mapping-publication","kind":"mapping-release","ref":"p4ab-offline"} for action,who in [("publish","proposer"),("approve","approver")]]}
            (identity/"activation-policy.json").write_text(json.dumps(policy))
            approval=java("mapping","approve",registry,bundle,"p4ab-approval","--by","proposer","--by-key",keys/"proposer.key","--approved-by","approver","--approved-by-key",keys/"approver.key")
            check("java.two-key-approval",approval.get("kind")!="mapping-refusal")
            release=java("mapping","publish",registry,bundle,"p4ab-release","1.0.0","--approval","p4ab-approval")
            check("java.publish-without-activation",release.get("kind")!="mapping-refusal" and release["activation"]=="not-performed")
        page.locator('[data-submission-refresh="p4ab-ui"]').wait_for()
        with page.expect_response(lambda r:r.url.endswith("/api/submission-refresh")) as rr:page.locator('[data-submission-refresh="p4ab-ui"]').click()
        check("browser.published-status",rr.value.json()["publicationState"]=="published")
        maintenance_snapshot=store.read()
        with page.expect_response(lambda r:r.url.endswith('/api/submission-maintenance')) as mp:page.locator('#maintenance-preview').click()
        healthy=mp.value.json();check('browser.integrity-healthy',mp.value.status==200 and all(i['state']=='verified' for i in healthy['integrity']))
        orphan=bundle.parent/('orphan-'+'a'*32);orphan.mkdir();(orphan/'partial').write_text('retain interrupted output');os.utime(orphan,(0,0))
        with page.expect_response(lambda r:r.url.endswith('/api/submission-maintenance')) as mp:page.locator('#maintenance-preview').click()
        check('browser.gc-preview-readonly',len(mp.value.json()['candidates'])==1 and orphan.exists())
        with page.expect_response(lambda r:r.url.endswith('/api/submission-maintenance')) as mq:page.locator('#maintenance-quarantine').click()
        check('browser.gc-quarantine',mq.value.status==200 and not orphan.exists() and list(bundle.parent.glob('quarantine/*/'+orphan.name+'/partial')))
        check('sqlite.maintenance-preserves-workspace',server.Store(store.path).read()==maintenance_snapshot)
        file=bundle/'submission.json';original=file.read_bytes();file.write_text('{')
        with page.expect_response(lambda r:r.url.endswith('/api/submission-maintenance')) as mc:page.locator('#maintenance-preview').click()
        check('browser.corruption-visible',mc.value.json()['integrity'][0]['state']=='corrupt' and page.locator('#maintenance-quarantine').is_disabled())
        file.write_bytes(original)
        head=java('mapping','status',registry,'p4ab-offline')['head'];transaction=registry/'mappings/transactions';transaction.mkdir(exist_ok=True)
        intent={'kind':'mapping-publication-intent','version':1,'streamId':'p4ab-offline','id':head['id'],'releaseVersion':head['version'],'sha256':head['sha256'],'staging':'.staging-interrupted','baseRelease':None}
        import uuid
        (transaction/(str(uuid.uuid4())+'.json')).write_text(json.dumps(intent))
        recovered=java('mapping','recover',registry);check('java.cli-recovery',len(recovered['actions'])==1)
        check('java.cli-recovery-idempotent',java('mapping','recover',registry)['actions']==[])
        stage=registry/'mappings/.staging-old';stage.mkdir();(stage/'partial').write_text('preserve');os.utime(stage,(0,0))
        gp=java('mapping','gc',registry,3600);check('java.cli-gc-dryrun',gp['dryRun'] and len(gp['candidates'])==1 and stage.exists())
        swept=java('mapping','gc',registry,3600,'--quarantine',gp['planSha256']);check('java.cli-gc-quarantine',swept['action']=='quarantine' and not stage.exists())
        check('java.cli-history-preserved',java('mapping','status',registry,'p4ab-offline')['head']==head)
        page.screenshot(path=str(E/'p6r-maintenance.png'),full_page=True)
        check("browser.no-errors-or-outbound",not errors and all(u.startswith(origin) for u in requests),errors=errors)
        browser.close()
    http.shutdown();http.server_close();thread.join()
    suites=[("test_p6_recovery.py",[],"recovery-tests"),("test_p4ab.py",[],"new-tests"),("test_p3fb.py",[],"graph-candidate-regression"),("test_p3eb.py",[],"logical-structure-regression"),("test_p3cb.py",[],"bounded-math-regression"),("test_a07.py",["--report",str(E/"a07.json")],"a07"),("test_p7.py",["--report",str(E/"regression.json")],"regression")]
    if os.environ.get("TYR_P6R_UI_ONLY")=="1":suites=[("test_p6_recovery.py",[],"recovery-tests"),]
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
