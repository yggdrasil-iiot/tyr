"""Offline interruption, quarantine and integrity faults. No device or external SQL."""
import json,os,sys,tempfile,unittest,threading,subprocess
from pathlib import Path
from unittest.mock import patch
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/"backend"),str(R/"scripts")]
import server,publication as pub
from test_p6 import request_export,load
class Recovery(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=server.Store(Path(self.tmp.name)/"editor.sqlite3");self.store.migrate(0,{});self.store.save(1,load());self.before=self.store.read()
    def tearDown(self):self.tmp.cleanup()
    def export(self,id="first"):return pub.export(self.store,request_export(id),server.Conflict,server.build_package,pub.Adapter())
    def plan(self):return pub.maintenance(self.store,{"graceSeconds":3600})
    def orphan(self):
        root=self.store.path.with_suffix(".submissions");root.mkdir(exist_ok=True);p=root/("orphan-"+"a"*32);p.mkdir();(p/"partial").write_text("partial");os.utime(p,(0,0));return p
    def execute(self,p):return pub.maintenance(self.store,{"graceSeconds":3600,"planSha256":p["planSha256"]})
    def test_each_export_crash_window(self):
        for point,committed in [("bundle-built",False),("row-inserted",False),("row-committed",True)]:
            with self.subTest(point=point):
                with patch.object(pub,"_fault",side_effect=lambda p:(_ for _ in ()).throw(RuntimeError("crash")) if p==point else None):
                    with self.assertRaises(RuntimeError):self.export(point)
                reopened=server.Store(self.store.path);self.assertEqual(reopened.read(),self.before)
                rows=pub.listing(reopened,pub.Adapter())["submissions"];self.assertEqual(any(r["id"]==point for r in rows),committed)
                if committed:self.assertIn("bytesBase64",pub.download(reopened,point))
    def test_actual_process_death_rolls_back_sqlite(self):
        code="""import os,sys;from pathlib import Path;sys.path[:0]=[str(Path(sys.argv[1])/'backend'),str(Path(sys.argv[1])/'scripts')];import server,publication as p;from test_p6 import request_export;p._fault=lambda point:os._exit(77) if point=='row-inserted' else None;p.export(server.Store(Path(sys.argv[2])),request_export(),server.Conflict,server.build_package,p.Adapter())"""
        r=subprocess.run([sys.executable,"-B","-c",code,str(R),str(self.store.path)],capture_output=True);self.assertEqual(r.returncode,77,r.stderr);self.assertEqual(self.store.read(),self.before);self.assertEqual(pub.listing(self.store,pub.Adapter())["submissions"],[])
        self.export();self.assertIn("bytesBase64",pub.download(self.store,"first"))
    def test_quarantine_preserves_references_and_workspace(self):
        row=self.export();orphan=self.orphan();plan=self.plan();self.assertEqual(len(plan["candidates"]),1);self.assertTrue(orphan.exists());self.execute(plan);self.assertFalse(orphan.exists());self.assertTrue(list(orphan.parent.glob("quarantine/*/"+orphan.name)));self.assertEqual(self.store.read(),self.before);self.assertEqual(self.plan()["candidates"],[]);pub.download(self.store,row["id"])
    def test_stale_content_plan_refused(self):
        orphan=self.orphan();p=self.plan();(orphan/"partial").write_text("changed");self.assertRaises(ValueError,self.execute,p);self.assertTrue(orphan.exists())
    def test_new_root_changes_plan(self):
        self.orphan();p=self.plan();self.export();self.assertRaises(ValueError,self.execute,p)
    def test_recent_or_unknown_preserved(self):
        orphan=self.orphan();os.utime(orphan,None);unknown=orphan.parent/"unknown";unknown.mkdir();os.utime(unknown,(0,0));self.assertEqual(self.plan()["candidates"],[]);self.assertTrue(unknown.exists())
    def test_corrupt_submission_blocks_gc_and_download(self):
        r=self.export();self.orphan();(Path(r["path"])/"submission.json").write_text("{");p=self.plan();self.assertEqual(p["integrity"][0]["state"],"corrupt");self.assertRaises(ValueError,self.execute,p);self.assertRaises(ValueError,pub.download,self.store,r["id"])
    def test_missing_submission_blocks_gc(self):
        r=self.export();(Path(r["path"])/"submission.json").unlink();p=self.plan();self.assertEqual(p["integrity"][0]["state"],"corrupt");self.assertRaises(ValueError,self.execute,p)
    def test_extra_file_blocks_integrity(self):
        r=self.export();(Path(r["path"])/"unexpected").write_text("extra");self.assertEqual(self.plan()["integrity"][0]["state"],"corrupt")
    def test_symlink_refused(self):
        orphan=self.orphan();outside=Path(self.tmp.name)/"outside";outside.write_text("keep")
        try:(orphan/"link").symlink_to(outside)
        except OSError:self.skipTest("host disallows symlinks; isolated Linux run required")
        os.utime(orphan,(0,0)) # Creating the symlink updates directory mtime; make it GC-eligible again.
        self.assertRaises(ValueError,self.plan);self.assertEqual(outside.read_text(),"keep")
    def test_quarantine_interruption_preserves_files(self):
        orphan=self.orphan();plan=self.plan()
        with patch.object(pub,"_fault",side_effect=RuntimeError("crash")):self.assertRaises(RuntimeError,self.execute,plan)
        self.assertEqual(self.plan()["candidates"],[]);self.assertTrue(list(orphan.parent.glob("quarantine/*/"+orphan.name+"/partial")));self.assertEqual(self.store.read(),self.before)
    def test_invalid_requests(self):
        for q in [{"graceSeconds":0},{"graceSeconds":True},{"graceSeconds":3600,"path":"../"},{"graceSeconds":3600,"planSha256":"bad"}]:self.assertRaises(ValueError,pub.maintenance,self.store,q)
    def test_existing_schema_and_fixtures_preserved(self):
        baseline=server.contracts.load(R/"docs/verification/p4ab-full-acceptance.json")["inputSha256"]
        for path,h in baseline.items():
            if path.startswith(("contracts/","fixtures/")):self.assertEqual(server.contracts.hashed(R/path),h,path)
if __name__=="__main__":unittest.main(verbosity=2)
