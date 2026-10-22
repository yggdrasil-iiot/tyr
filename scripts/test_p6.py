"""P6 adapter/API and independently executed Bifrost receiver seam."""
import argparse,base64,copy,io,json,os,sys,tempfile,threading,unittest,zipfile,shutil
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request,urlopen
from urllib.error import HTTPError
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/"backend"),str(R/"scripts")]
import server,publication as pub,p3a_contracts as p3,sample_quality as sq
JAR=R.parent/"bifrost/gates/target/bifrost-gates.jar"
def java_code(text):
    """Java source with comments removed and string/char literals kept, so a comment saying "no python" is not a call."""
    out,i,n=[],0,len(text)
    while i<n:
        if text.startswith("//",i):i=text.find("\n",i);i=n if i<0 else i;continue
        if text.startswith("/*",i):j=text.find("*/",i+2);i=n if j<0 else j+2;out.append(" ");continue
        if text[i] in "\"'":
            q,j=text[i],i+1
            while j<n and text[j]!=q:j+=2 if text[j]=="\\" else 1
            out.append(text[i:j+1]);i=j+1;continue
        out.append(text[i]);i+=1
    return "".join(out)
def load():return server.contracts.load(R/"fixtures/p4b/workspace.json")
def request_export(id="first",stream="mixed-line",revision=2):return {"revision":revision,"id":id,"streamId":stream,"proposedBy":"proposer","mappingSetIds":["mixed-tank-mapping"],"includeWrites":True}
class Adapter(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=server.Store(Path(self.tmp.name)/"editor.sqlite3");self.store.migrate(0,{});self.w=load();self.store.save(1,self.w);self.adapter=pub.Adapter()
    def tearDown(self):self.tmp.cleanup()
    def export(self,request=None):return pub.export(self.store,request or request_export(),server.Conflict,server.build_package,self.adapter)
    def test_old_contracts_immutable(self):
        report=server.contracts.load(R/"docs/verification/p5-validation.json");old={p:h for p,h in report["sha256"].items() if p.startswith("contracts/")};self.assertEqual(len(old),56)
        for p,h in old.items():self.assertEqual(server.contracts.hashed(R/p),h,p)
    def test_additive_table_preserves_workspace(self):
        before=self.store.read();server.Store(self.store.path);self.assertEqual(before,self.store.read());self.assertEqual(pub.listing(self.store,self.adapter)["submissions"],[])
    def test_export_no_workspace_mutation(self):
        before=self.store.read();r=self.export();self.assertEqual(before,self.store.read());self.assertEqual(r["preflightFindings"],[])
    def test_export_absolute_path_from_relative_DB(self):
        with patch.object(self.store,"path",Path(os.path.relpath(self.store.path))):
            r=self.export();self.assertTrue(Path(r["path"]).is_absolute());self.assertTrue(Path(r["path"]).is_dir())
    def test_export_schema(self):
        r=self.export();folder=Path(r["path"]);pub.schema("mapping-submission",server.contracts.load(folder/"submission.json"));self.assertEqual(p3.validate_package(folder)[0],[])
    def test_context_preserved(self):
        r=self.export();d=server.contracts.load(Path(r["path"])/"submission.json");self.assertEqual(d["context"],{k:self.w[k] for k in ("equipment","connections")})
    def test_zip_roundtrip(self):
        r=self.export();data=pub.download(self.store,r["id"]);files=pub.file_pins(Path(r["path"]))
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(data["bytesBase64"]))) as z:self.assertEqual(set(z.namelist()),set(files))
    def test_reopen(self):
        self.export();r=pub.listing(server.Store(self.store.path),self.adapter)["submissions"][0];self.assertEqual(r["submissionRevision"],1)
    def test_duplicate_id_conflict(self):
        self.export()
        with self.assertRaises(server.Conflict):self.export()
    def test_stale_revision_conflict(self):
        with self.assertRaises(server.Conflict):self.export(request_export(revision=1))
    def test_bad_stream(self):
        with self.assertRaises(ValueError):self.export(request_export(stream="../outside"))
    def test_unknown_mapping(self):
        q=request_export();q["mappingSetIds"]=["missing"]
        with self.assertRaises(ValueError):self.export(q)
    def test_explicit_write_bool(self):
        q=request_export();q["includeWrites"]="yes"
        with self.assertRaises(ValueError):self.export(q)
    def test_source_and_evidence_tamper(self):
        r=self.export();p=Path(r["path"])/"data/manual-0.txt";p.write_text("tampered")
        with self.assertRaises(ValueError):pub.download(self.store,r["id"])
    def test_read_only_scope_excludes_write_definitions(self):
        q=request_export();q["includeWrites"]=False;r=self.export(q);p=server.contracts.load(Path(r["path"])/"proposal.json")
        self.assertNotIn("write-definition",{e["kind"] for e in p["files"]});self.assertFalse(r["preflightFindings"])
    def test_other_workspace_drafts_excluded(self):
        w=copy.deepcopy(self.w);extra=copy.deepcopy(w["sources"][0]);extra["definition"]["id"]="unrelated-draft";extra["definition"]["status"]="draft";extra["definition"]["evidenceRefs"]=[{"artifactId":"manual-unrelated-draft","locator":{"kind":"text-line","line":1}}];w["sources"].append(extra);self.store.save(2,w)
        r=self.export(request_export(revision=3));self.assertFalse(r["preflightFindings"])
    def test_workspace_edit_marks_submission_stale(self):
        self.export();w=copy.deepcopy(self.w);w["sources"][0]["note"]="Changed";self.store.save(2,w);self.assertTrue(pub.listing(self.store,self.adapter)["submissions"][0]["stale"])
    def test_no_cli_configuration(self):
        r=self.export()
        with self.assertRaises(ValueError):pub.refresh(self.store,{"id":r["id"],"submissionRevision":1},server.Conflict,self.adapter)
    def test_export_never_invokes_approval(self):
        with patch("subprocess.run",side_effect=AssertionError("CLI approval forbidden")):self.export()
    def test_declared_unknown_unit_preserved_and_refused_by_preflight(self):
        w=copy.deepcopy(self.w);w["sources"][2]["definition"]["unit"]={"status":"unknown"};self.store.save(2,w)
        r=self.export(request_export(revision=3));self.assertTrue(r["preflightFindings"])
    def test_refresh_revision_conflict(self):
        r=self.export()
        with self.assertRaises(server.Conflict):pub.refresh(self.store,{"id":r["id"],"submissionRevision":0},server.Conflict,self.adapter)
class API(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=server.Store(Path(self.tmp.name)/"db.sqlite3");self.store.migrate(0,{});self.store.save(1,load());self.http=server.make_server(self.store,0);self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):self.http.shutdown();self.http.server_close();self.thread.join();self.tmp.cleanup()
    def request(self,path,body=None,origin=None):
        headers={"Content-Type":"application/json","X-Tyr-Editor":"1"}
        if origin:headers["Origin"]=origin
        with urlopen(Request("http://127.0.0.1:"+str(self.http.server_port)+path,data=json.dumps(body).encode() if body is not None else None,headers=headers,method="POST" if body is not None else "GET")) as r:return json.load(r)
    def test_list_and_export(self):
        self.assertFalse(self.request("/api/submissions")["configured"]);self.request("/api/submissions",request_export());self.assertEqual(len(self.request("/api/submissions")["submissions"]),1);self.assertEqual(self.store.read()["revision"],2)
    def test_download(self):
        self.request("/api/submissions",request_export());self.assertEqual(self.request("/api/submission-download",{"id":"first"})["filename"],"first.zip")
    def test_origin(self):
        with self.assertRaises(HTTPError) as e:self.request("/api/submissions",request_export(),"https://evil.invalid")
        self.assertEqual(e.exception.code,403)
    def test_no_execute_or_approve(self):
        for path in ("/api/approve","/api/publish","/api/sql","/api/write","/api/plc/read","/api/execute"):
            with self.assertRaises(HTTPError) as e:self.request(path,{})
            self.assertEqual(e.exception.code,404)
class Receiver(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.adapter=pub.Adapter(JAR,Path(self.tmp.name)/"registry")
    def tearDown(self):self.tmp.cleanup()
    def test_shared_schema_copies(self):
        other=R.parent/"bifrost/core/src/main/resources/mapping-contracts"
        for p in (R/"contracts").rglob("*.schema.json"):self.assertEqual(p.read_bytes(),(other/p.relative_to(R/"contracts")).read_bytes())
    def test_no_shared_source(self):
        files=sorted((R.parent/"bifrost/core/src/main/java/dev/krillin/bifrost/core/mapping").glob("*.java"))
        self.assertTrue(files,"no Bifrost mapping sources: this check needs a sibling Bifrost checkout")
        for p in files:
            code=java_code(p.read_text(encoding="utf-8")).lower()
            for banned in ("processbuilder","runtime.getruntime","python"):self.assertNotIn(banned,code,p.name)
    def test_java_manifest_matches_python(self):
        folder=R/"fixtures/p6/valid";r=self.adapter.call("validate",folder);pub.schema("mapping-validation",r)
        self.assertTrue(r["accepted"],r["findings"]);self.assertEqual(r["bundleSha256"],pub.manifest_digest(pub.file_pins(folder)))
    def test_cli_validation_readonly(self):
        folder=R/"fixtures/p6/valid";before=pub.file_pins(folder);self.adapter.call("validate",folder);self.assertEqual(before,pub.file_pins(folder))
    def test_current_registry_status_no_activation(self):
        s=self.adapter.status("mixed-line");self.assertIsNone(s["head"]);self.assertEqual(s["activation"],"not-performed")
    def test_real_adapter_refresh(self):
        store=server.Store(Path(self.tmp.name)/"db.sqlite3");store.migrate(0,{});store.save(1,load());r=pub.export(store,request_export(),server.Conflict,server.build_package,self.adapter)
        refreshed=pub.refresh(store,{"id":r["id"],"submissionRevision":1},server.Conflict,self.adapter);self.assertTrue(refreshed["validation"]["accepted"]);self.assertEqual(refreshed["publicationState"],"awaiting-approval");self.assertEqual(store.read()["revision"],2)
def valid_receiver(name):
    def test(self):
        folder=R/"fixtures/p6"/name;self.assertEqual(p3.validate_package(folder)[0],[])
        r=self.adapter.call("validate",folder);self.assertTrue(r["accepted"],r)
    return test
for name in ("ab","ua","db","p3d","p3e","p3f"):setattr(Receiver,"test_compat_"+name,valid_receiver(name))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--report",type=Path);a=p.parse_args();r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if a.report:
        files=[*(R/"contracts").rglob("*.json"),*(R/"backend").glob("*.py"),*(R/"frontend").glob("*"),*(R/"fixtures/p6").rglob("*"),Path(__file__)]
        server.contracts.save(a.report,{"total":r.testsRun,"passed":r.testsRun-len(r.failures)-len(r.errors),"failures":[str(x) for x in r.failures],"errors":[str(x) for x in r.errors],"sha256":{str(p.relative_to(R)).replace(chr(92),"/"):server.contracts.hashed(p) for p in files if p.is_file()}})
    sys.exit(not r.wasSuccessful())
