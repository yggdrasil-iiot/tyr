"""A14 real OS network namespace acceptance. No socket patches or browser routes."""
import base64,copy,hashlib,json,os,shutil,socket,sqlite3,subprocess,sys,tempfile,threading,traceback,zipfile,io,tarfile
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
E=Path("/work/evidence");E.mkdir(parents=True,exist_ok=True)
R=Path("/work/tyr");R.mkdir(parents=True,exist_ok=True)
INPUT=Path("/input/tyr")
report={"scope":"A14 isolated Linux container; not host-wide Windows isolation or field PoV","checks":[],"execution":"excluded","passed":False}
def save(name,value): (E/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def check(id,ok,**evidence):
    print(id,bool(ok),flush=True)
    report["checks"].append(dict(id=id,passed=bool(ok),**evidence));save("a14-results.json",report)
    assert ok,(id,evidence)
def cmd(args,timeout=120):
    p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=timeout)
    return {"returncode":p.returncode,"stdout":p.stdout,"stderr":p.stderr}
def java(*args):
    x=cmd(["java","-jar",JAR,*args]);doc=json.loads(x["stdout"]);save("java-%02d.json"%len(list(E.glob("java-*.json"))),doc)
    assert x["returncode"] in (0,1),x
    return doc
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(path):
    with sqlite3.connect(path) as c:
        return {name:c.execute('SELECT * FROM "'+name+'" ORDER BY rowid').fetchall() for (name,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")}
def main():
    shutil.copyfile("/input/package.tar","/tmp/a14-package.tar")
    with tarfile.open("/tmp/a14-package.tar") as archive:archive.extractall("/work",filter="data")
    jar=R.parent/"bifrost/gates/target/bifrost-gates.jar"
    global JAR;JAR=jar
    product={str(p.relative_to(R)):digest(p) for name in ["backend","frontend","contracts","fixtures","scripts"] for p in (R/name).rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    report["inputSha256"]=product;report["jarSha256"]=digest(jar)
    sys.path[:0]=[str(R/"backend"),str(R/"scripts")]
    import server,publication
    from jsonschema import FormatChecker
    from jsonschema.exceptions import FormatError
    fmt=FormatChecker()
    fmt.check("2026-10-18T00:00:00Z","date-time")
    try:fmt.check("yesterday","date-time")
    except FormatError:check("dependency.date-time-format-enabled",True)
    else:check("dependency.date-time-format-enabled",False)
    fmt.check("urn:tyr:concept:a14.test","uri")
    try:fmt.check("not a uri","uri")
    except FormatError:check("dependency.uri-format-enabled",True)
    else:check("dependency.uri-format-enabled",False)


    from playwright.sync_api import sync_playwright
    net={x:cmd(["ip","-j",*x.split()]) for x in ["link show","address show","route show","-6 route show"]}
    net["resolv.conf"]=Path("/etc/resolv.conf").read_text();net["namespace"]=os.readlink("/proc/self/ns/net")
    save("a14-network.json",net)
    links=json.loads(net["link show"]["stdout"])
    check("os.loopback-only",len(links)==1 and links[0]["ifname"]=="lo" and json.loads(net["route show"]["stdout"])==[] and json.loads(net["-6 route show"]["stdout"])==[],namespace=net["namespace"])
    check("os.dns-loopback",all(line.split()[1]=="127.0.0.1" for line in net["resolv.conf"].splitlines() if line.startswith("nameserver")) and "nameserver 127.0.0.1" in net["resolv.conf"])
    report["versions"]={x:cmd(a) for x,a in {"python":[sys.executable,"--version"],"java":["java","-version"],"chromium":["chromium","--version"],"packages":[sys.executable,"-m","pip","freeze"]}.items()}
    for af,host,kind in [(socket.AF_INET,"192.0.2.1","tcp4"),(socket.AF_INET6,"2001:db8::1","tcp6"),(socket.AF_INET,"192.0.2.1","udp4"),(socket.AF_INET,"8.8.8.8","dns-udp")]:
        with socket.socket(af,socket.SOCK_DGRAM if kind.startswith(("udp","dns")) else socket.SOCK_STREAM) as s:
            s.settimeout(2)
            try:
                if s.type==socket.SOCK_DGRAM:s.sendto(b"A14-denied-probe",(host,53 if kind=="dns-udp" else 443))
                else:s.connect((host,443))
            except OSError as e:check("python.deny."+kind,e.errno==101,error=str(e),errno=e.errno)
            else:check("python.deny."+kind,False)
    # Open the old SQLite clone without rewriting existing bodies or revisions.
    shutil.copy2("/input/seed.sqlite3",E/"legacy.sqlite3")
    legacy=E/"legacy.sqlite3";old=rows(legacy);oldBytes=digest(legacy);server.Store(legacy)
    check("sqlite.legacy-open",rows(legacy)==old and digest(legacy)==oldBytes,sha256=oldBytes,tableCounts={k:len(v) for k,v in old.items()})
    # Use independent fixed oracle fixture for browser authoring and publication.
    store=server.Store(E/"editor.sqlite3");store.migrate(0,{})
    fixture=json.loads((R/"fixtures/a07/workspace.json").read_text());store.save(1,fixture)
    registry=E/"registry";adapter=publication.Adapter(jar,registry)
    http=server.make_server(store,0,jar,registry);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
    origin="http://127.0.0.1:"+str(http.server_port)
    def api(path="/api/workspace",body=None,method=None):
        with urlopen(Request(origin+path,data=json.dumps(body).encode() if body is not None else None,headers={"X-Tyr-Editor":"1","Content-Type":"application/json"},method=method or ("POST" if body is not None else "GET")),timeout=90) as response:return json.load(response)
    check("python.localhost",api()["workspace"]==fixture,origin=origin)
    # Real JVM sockets and HTTP positive control; no SecurityManager or Java proxy.
    probe=E/"NetworkProbe.java"
    probe.write_text("""import java.net.*;import java.io.*;
public class NetworkProbe {
 public static void main(String[] a)throws Exception {
  for(String h:new String[]{"192.0.2.1","2001:db8::1"}) {
   try(Socket s=new Socket()){s.connect(new InetSocketAddress(h,443),1500);throw new AssertionError("external TCP succeeded");}
   catch(IOException e){System.out.println("DENIED "+h+" "+e);}
  }
  try(DatagramSocket s=new DatagramSocket()){s.send(new DatagramPacket(new byte[]{1},1,InetAddress.getByName("8.8.8.8"),53));throw new AssertionError("external UDP succeeded");}
  catch(IOException e){System.out.println("DENIED UDP "+e);}
  HttpURLConnection c=(HttpURLConnection)new URI(a[0]+"/api/workspace").toURL().openConnection();
  if(c.getResponseCode()!=200)throw new AssertionError("loopback failed");
  System.out.println("LOCALHOST 200");
 }
}
""")
    compilation=cmd(["javac",probe]);check("java.probe-compile",compilation["returncode"]==0,**compilation)
    jp=cmd(["java","-cp",E,"NetworkProbe",origin]);save("a14-java-network.json",jp)
    check("java.deny-and-localhost",jp["returncode"]==0 and jp["stdout"].count("DENIED")==3 and "LOCALHOST 200" in jp["stdout"],**jp)
    requests=[];failures=[];errors=[];responses=[];previews=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path="/usr/bin/chromium",headless=True,args=["--no-sandbox"],env={**os.environ,"HTTP_PROXY":"","HTTPS_PROXY":"","ALL_PROXY":"","NO_PROXY":""})
        context=browser.new_context(viewport={"width":1360,"height":1000},record_har_path=str(E/"a14-browser.har"))
        page=context.new_page();page.set_default_timeout(90000)
        context.on("request",lambda r:requests.append({"method":r.method,"url":r.url}))
        context.on("requestfailed",lambda r:failures.append({"url":r.url,"failure":r.failure}))
        page.on("pageerror",lambda e:errors.append(str(e)))
        def dialog(d):
            if d.type=="beforeunload":d.accept()
            else:errors.append("Unexpected dialog: "+d.type);d.dismiss()
        page.on("dialog",dialog)
        def response(r):
            if r.url.startswith(origin+"/api/"):responses.append({"url":r.url,"status":r.status})
        page.on("response",response)
        for host in ["192.0.2.1","[2001:db8::1]","a14-network-probe.invalid"]:
            probe_page=context.new_page()
            try:probe_page.goto("http://"+host+":443/",timeout=10000)
            except Exception as e:check("browser.deny."+host,"ERR_" in str(e),error=str(e))
            else:check("browser.deny."+host,False)
            finally:probe_page.close()
        print("browser.goto-localhost",flush=True)
        page.goto(origin);page.locator("#counts strong").first.wait_for();page.locator('[data-tab="views"]').click()
        page.locator("#view-id").fill("a14-ui-alias");page.locator("#view-label").fill("A14 isolated browser authored alias")
        page.locator("#view-parent").select_option("a07-melsec-alarm")
        page.locator("#view-status").select_option("ready")
        page.locator("#view-note").fill("Synthetic A14 offline acceptance. Explicit alias of alarm bit; no device IO.")
        with page.expect_response(lambda r:r.url==origin+"/api/workspace" and r.request.method=="PUT") as saved:
            page.locator('#view-form button[type="submit"]').click()
        check("browser.author-save",saved.value.status==200 and saved.value.json()["revision"]==3)
        page.locator("#revision").filter(has_text="저장 revision 3").wait_for()
        page.locator('[data-edit="source"][data-id="a14-ui-alias"]').wait_for()
        page.locator('[data-tab="views"]').click()
        page.locator('[data-edit="source"][data-id="a07-melsec-alarm-alias"]').click()
        page.locator("#view-parent").select_option("a14-ui-alias")
        page.locator("#view-note").fill("Synthetic A14: mapped alarm alias now depends on browser-authored alias.")
        with page.expect_response(lambda r:r.url==origin+"/api/workspace" and r.request.method=="PUT") as linked:
            page.locator('#view-form button[type="submit"]').click()
        check("browser.dependency-evidence-refusal",linked.value.status==422 and "evidence-incomplete" in str(linked.value.json()),response=linked.value.json())
        check("sqlite.refusal-atomic",store.read()["revision"]==3)
        page.locator("#view-parent").select_option("a07-melsec-alarm")
        page.locator("#view-note").fill("Synthetic A14 existing view edited; original parent and dependency evidence preserved.")
        with page.expect_response(lambda r:r.url==origin+"/api/workspace" and r.request.method=="PUT") as edited:
            page.locator('#view-form button[type="submit"]').click()
        edited_body=edited.value.json()
        check("browser.edit-existing-view",edited.value.status==200 and edited_body.get("revision")==4,status=edited.value.status,error=edited_body.get("error"))

        page.locator("#revision").filter(has_text="저장 revision 4").wait_for()
        page.locator('[data-tab="mappings"]').click()
        page.locator('[data-edit="mapping"][data-id="a07-melsec-mapping"]').click()
        page.locator("#bind-source-3").select_option(json.dumps(["source","a14-ui-alias"],separators=(",",":")))
        with page.expect_response(lambda r:r.url==origin+"/api/workspace" and r.request.method=="PUT") as mapped:
            page.locator('#mapping-form button[type="submit"]').click()
        mapped_body=mapped.value.json()
        check("browser.link-authored-view",mapped.value.status==200 and mapped_body.get("revision")==5,status=mapped.value.status,error=mapped_body.get("error"))

        page.locator("#revision").filter(has_text="저장 revision 5").wait_for()
        print("browser.reload-start",flush=True)
        page.reload(wait_until="domcontentloaded");page.locator("#counts strong").first.wait_for()
        print("browser.reload-ready",flush=True)
        page.locator('[data-tab="views"]').click()
        page.locator('[data-edit="source"][data-id="a14-ui-alias"]').wait_for()
        page.locator('[data-tab="comparison"]').click()
        check("browser.reload-persisted","a14-ui-alias" in page.locator("body").inner_text() or any(r["definition"]["id"]=="a14-ui-alias" for r in api()["workspace"]["sources"]))
        snapshot=store.read()
        check("sqlite.reopen-authored",server.Store(store.path).read()==snapshot and snapshot["revision"]==5)
        page.locator('[data-tab="preview"]').click()
        page.locator("#preview-binding").select_option(json.dumps(["a07-melsec-mapping","melsec-alarm"],separators=(",",":")))
        page.locator("#virtual-0").fill("05 80")
        with page.expect_response(lambda r:r.url.endswith("/api/preview")) as pr:
            page.locator('#preview-form button[type="submit"]').click()
        p=pr.value.json();check("browser.preview",p["result"]["value"] is True and p["quality"]=="good" and any(x["stage"]=="view:bit" for x in p["trace"]))
        check("sqlite.preview-readonly",store.read()==snapshot)
        page.locator("#preview-result h2").wait_for();page.screenshot(path=str(E/"a14-preview.png"),full_page=True)
        page.locator('[data-tab="publication"]').click()
        page.locator("#submission-id").fill("a14-ui-submission");page.locator("#submission-stream").fill("a14-offline-line");page.locator("#submission-by").fill("proposer")
        page.locator("#submission-mapping").select_option("a07-melsec-mapping")
        with page.expect_response(lambda r:r.url.endswith("/api/submissions") and r.request.method=="POST") as ex:
            page.locator('#submission-form button[type="submit"]').click()
        record=ex.value.json();check("browser.submission",ex.value.status==200 and record["preflightFindings"]==[],bundleSha256=record["bundleSha256"])
        bundle=Path(record["path"])
        proposal=json.loads((bundle/"proposal.json").read_text())
        check("publication.authored-view-included",any(f["id"]=="a14-ui-alias" for f in proposal["files"]))
        validation=java("mapping","validate",bundle)
        check("java.receiver",validation["accepted"] and validation["bundleSha256"]==record["bundleSha256"])
        # Both keys are ephemeral, outside SQLite/registry/report. Only public registration remains.
        with tempfile.TemporaryDirectory(prefix="a14-keys-") as kd:
            keys=Path(kd);identity=registry/"identity";identity.mkdir(parents=True,exist_ok=True)
            public=[]
            for principal in ["proposer","approver"]:
                v=java("identity","keygen",principal,"--out",keys);public.append(v)
            (identity/"authorized-keys.jsonl").write_text("".join(json.dumps(v)+"\n" for v in public))
            policy={"version":"1.0.0","default":"deny","rules":[{"id":"a14-"+action,"principal":who,"action":action,"target":"mapping-publication","kind":"mapping-release","ref":"a14-offline-line"} for action,who in [("publish","proposer"),("approve","approver")]]}
            (identity/"activation-policy.json").write_text(json.dumps(policy))
            approval=java("mapping","approve",registry,bundle,"a14-approval","--by","proposer","--by-key",keys/"proposer.key","--approved-by","approver","--approved-by-key",keys/"approver.key")
            check("java.two-key-approval",approval.get("kind")!="mapping-refusal",kind=approval.get("kind"))
            release=java("mapping","publish",registry,bundle,"a14-release","1.0.0","--approval","a14-approval")
            check("java.publish",release.get("kind")!="mapping-refusal",kind=release.get("kind"))
        check("keys.deleted",not keys.exists())
        page.locator('[data-submission-refresh="a14-ui-submission"]').wait_for()
        with page.expect_response(lambda r:r.url.endswith("/api/submission-refresh")) as rr:
            page.locator('[data-submission-refresh="a14-ui-submission"]').click()
        refreshed=rr.value.json()
        check("browser.published-status",refreshed["publicationState"]=="published" and refreshed["publication"]["release"]["id"]=="a14-release")
        released=refreshed["publication"]["release"]
        release_dirs=[p.parent for p in registry.rglob("release.json") if json.loads(p.read_text()).get("id")=="a14-release"]
        check("release.directory",len(release_dirs)==1)
        release_root=release_dirs[0]
        release_files=released["files"]
        check("release.file-hashes",all(digest(release_root/f["path"])==f["sha256"] for f in release_files),files=len(release_files))
        page.locator("#submission-records").get_by_text("a14-release@1.0.0",exact=True).wait_for()
        page.screenshot(path=str(E/"a14-publication.png"),full_page=True)
        with page.expect_download() as download:page.locator('[data-submission-download="a14-ui-submission"]').click()
        download.value.save_as(str(E/"a14-submission.zip"))
        with zipfile.ZipFile(E/"a14-submission.zip") as z:
            pins=publication.file_pins(bundle)
            check("browser.zip-download",set(z.namelist())==set(pins) and all(hashlib.sha256(z.read(n)).hexdigest()==h for n,h in pins.items()),files=len(pins))
        page.reload(wait_until="domcontentloaded");page.locator("#counts strong").first.wait_for();page.locator('[data-tab="publication"]').click();page.locator("#submission-records").get_by_text("a14-release@1.0.0",exact=True).wait_for()
        check("browser.published-reload",True)
        context.close();browser.close()
    check("browser.no-script-errors",not errors,errors=errors)
    expected={"http://192.0.2.1:443/","http://[2001:db8::1]:443/","http://a14-network-probe.invalid:443/"}
    check("browser.only-loopback-success",all(x["url"].startswith(origin+"/") or x["url"] in expected for x in requests) and {x["url"] for x in failures}==expected,requests=len(requests),failed=failures)
    save("a14-browser.json",{"requests":requests,"failures":failures,"errors":errors,"responses":responses})
    http.shutdown();http.server_close();thread.join()
    check("sqlite.final-reopen",server.Store(store.path).read()==snapshot and rows(legacy)==old)
    for path in ["/api/sql","/api/write","/api/plc/read","/api/execute"]:
        # Existing tests cover route refusal; no such route is invoked against a device.
        check("scope.no-route."+path,path not in [r["url"].removeprefix(origin) for r in requests])
    after={str(p.relative_to(R)):digest(p) for name in ["backend","frontend","contracts","fixtures","scripts"] for p in (R/name).rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    check("product.inputs-unchanged",product==after)
    # Existing regression oracles run under the same OS isolation; guard remains supplemental only.
    for script,args,name in [("test_a07.py",["--report",str(E/"a14-a07.json")],"a14-a07"),("test_p7.py",["--report",str(E/"a14-regression.json")],"a14-regression")]:
        p=cmd([sys.executable,"-B",R/"scripts"/script,*args],timeout=1200)
        logfile=E/(name+".log")
        if logfile.exists():shutil.copy2(logfile,E/(name+"-tests.log"))
        logfile.write_text(p["stdout"]+p["stderr"])
        check("regression."+name,p["returncode"]==0)
    report["passed"]=True;report["fieldPoV"]="not-performed";report["legacyRowsPreserved"]=True;save("a14-results.json",report)
if __name__=="__main__":
    try:main()
    except Exception:
        report["error"]=traceback.format_exc();save("a14-results.json",report);raise
    finally:
        # Local disk is the tested storage. Export once; Windows/9p is not the hot path.
        with tarfile.open("/evidence/runtime-evidence.tar","w") as archive:archive.add(E,arcname=".")

