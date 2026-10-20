"""P3-A UI/storage acceptance with temporary SQLite and local HTTP only."""
import copy,json,sys,tempfile,threading,unittest,sqlite3
from contextlib import closing
from unittest.mock import patch
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"backend"))
import server
def sample():
    root=ROOT/"fixtures/p3a/two-motors"
    p=server.contracts.load(root/"proposal.json");docs=[server.contracts.load(root/e["path"]) for e in p["files"]]
    state={"workspaceVersion":"2.0.0","equipment":[{"id":"line-a-motor-melsec","label":"Line A"}],"connections":[{"id":"logical-melsec","label":"MELSEC","equipmentInstanceId":"line-a-motor-melsec","accessProfileRef":"melsec-device-v1"}],"sources":[],"semantics":[],"targets":[],"graphs":[],"mappings":[]}
    # P2 manual evidence uses a fixed artifact naming convention.
    def refs(x):
        if isinstance(x,dict):
            return {k:("manual-"+v[3:] if k=="artifactId" and v.startswith("ev-") else refs(v)) for k,v in x.items()}
        if isinstance(x,list):return [refs(v) for v in x]
        return x
    for original in docs:
        d=refs(original)
        if d["kind"]=="source-definition":state["sources"].append({"definition":d,"note":"Synthetic "+d["rawAddressText"],"label":d["id"],"origin":"synthetic","capturedAt":"2026-10-17T00:00:00Z"})
        elif d["kind"]=="semantic-definition":state["semantics"].append(d)
        elif d["kind"]=="target-instance":state["targets"].append(d)
        elif d["kind"]=="value-graph":state["graphs"].append(d)
        elif d["kind"]=="mapping-set":state["mappings"].append(d)
    return state
class Storage(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/"editor.sqlite3";self.store=server.Store(self.path)
    def tearDown(self):self.tmp.cleanup()
    def start(self):
        self.store.migrate(0,{})
        return self.store.save(1,sample())
    def test_two_objects_graph_restart(self):
        result=self.start();self.assertEqual(result["findings"],[])
        result=server.Store(self.path).read();self.assertEqual(result["workspace"],sample());self.assertEqual(result["revision"],2)
    def test_migrate_32_preserve_backup(self):
        legacy=server.contracts.load(ROOT/"fixtures/realistic/workspace.json");self.store.save(0,legacy)
        ids=server.contracts.load(ROOT/"fixtures/p3a/migration-assignments.json")
        result=self.store.migrate(1,ids);self.assertEqual(result["revision"],2);self.assertEqual(len(result["workspace"]["targets"]),4)
        self.assertEqual(result["workspace"]["sources"],legacy["sources"]);self.assertEqual(result["workspace"]["semantics"],legacy["semantics"])
        backup=Path(result["migration"]["backup"]);self.assertTrue(backup.exists())
        with closing(sqlite3.connect(backup)) as c:rev,body=c.execute("SELECT revision,body FROM workspace").fetchone()
        self.assertEqual(rev,1);self.assertEqual(json.loads(body),legacy)
        reopened=server.Store(self.path).read();self.assertEqual(reopened["migration"]["assignments"],ids)
        self.assertEqual(len(reopened["workspace"]["mappings"]),4)
    def test_invalid_migration_no_backup_no_change(self):
        self.store.save(0,server.contracts.load(ROOT/"fixtures/realistic/workspace.json"))
        with self.assertRaises(server.Invalid):self.store.migrate(1,{})
        self.assertEqual(self.store.read()["revision"],1);self.assertFalse(self.path.with_suffix(".sqlite3.backups").exists())
    def test_duplicate_assignment_rejected(self):
        w=server.contracts.load(ROOT/"fixtures/realistic/workspace.json");self.store.save(0,w)
        with self.assertRaises(server.Invalid):self.store.migrate(1,{m["id"]:"same" for m in w["mappings"]})
        self.assertEqual(self.store.read()["revision"],1)
    def test_stale_migration_no_side_effect(self):
        self.store.save(0,copy.deepcopy(server.EMPTY))
        with self.assertRaises(server.Conflict):self.store.migrate(0,{})
        self.assertFalse(self.path.with_suffix(".sqlite3.backups").exists())
    def test_repeated_migration_rejected(self):
        self.store.migrate(0,{})
        with self.assertRaises(server.Invalid):self.store.migrate(1,{})
        self.assertEqual(len(list(self.path.with_suffix(".sqlite3.backups").glob("*.sqlite3"))),1)
    def test_upgrade_requires_migration_and_downgrade_rejected(self):
        with self.assertRaises(server.Invalid):self.store.save(0,sample())
        self.start()
        with self.assertRaises(server.Invalid):self.store.save(2,copy.deepcopy(server.EMPTY))
    def test_cycle_rejected_atomically(self):
        self.start();w=sample();w["graphs"][0]["nodes"][0]["inputs"]["low"]={"kind":"node","nodeId":"result"}
        with self.assertRaises(server.Invalid):self.store.save(2,w)
        self.assertEqual(self.store.read()["revision"],2);self.assertEqual(self.store.read()["workspace"],sample())
    def test_bad_type_rejected(self):
        self.start();w=sample();w["sources"][0]["definition"]["rawRepresentation"]["valueType"]="Int16"
        with self.assertRaises(server.Invalid):self.store.save(2,w)
    def test_duplicate_target_binding_rejected(self):
        self.start();w=sample();m=copy.deepcopy(w["mappings"][0]);m["id"]="second-set"
        for b in m["mappings"]:b["mappingId"]+="-duplicate"
        w["mappings"].append(m)
        with self.assertRaises(server.Invalid):self.store.save(2,w)
    def test_cross_equipment_graph_rejected(self):
        self.start();w=sample();w["graphs"][0]["equipmentInstanceId"]="missing"
        with self.assertRaises(server.Invalid):self.store.save(2,w)
    def test_missing_node_rejected(self):
        self.start();w=sample();w["mappings"][0]["mappings"][1]["valueRef"]["nodeId"]="missing"
        with self.assertRaises(server.Invalid):self.store.save(2,w)
    def test_edit_object_label_preserves_graph(self):
        self.start();w=sample();w["targets"][0]["label"]="Renamed"
        result=self.store.save(2,w);self.assertEqual(result["workspace"]["graphs"],sample()["graphs"])
        self.assertEqual(server.Store(self.path).read()["workspace"]["targets"][0]["id"],"motor-a")
    def test_edit_graph_and_reload(self):
        self.start();w=sample();g=w["graphs"][0]
        g["nodes"][0]["inputs"]["low"],g["nodes"][0]["inputs"]["high"]=g["nodes"][0]["inputs"]["high"],g["nodes"][0]["inputs"]["low"]
        self.store.save(2,w);self.assertEqual(server.Store(self.path).read()["workspace"]["graphs"],w["graphs"])
    def test_conflict_preserves_v2(self):
        self.start()
        with self.assertRaises(server.Conflict):self.store.save(1,sample())
        self.assertEqual(self.store.read()["revision"],2)
    def test_target_draft_saved_with_coverage(self):
        self.start();w=sample();w["mappings"].pop()
        result=self.store.save(2,w);self.assertIn("mapping.incomplete-object",{f["ruleCode"] for f in result["findings"]})
    def test_backup_failure_rolls_back(self):
        original=sqlite3.connect
        def failing(path,*args,**kwargs):
            if ".backups" in str(path):raise sqlite3.OperationalError("simulated backup failure")
            return original(path,*args,**kwargs)
        with patch.object(sqlite3,"connect",side_effect=failing):
            with self.assertRaises(server.Invalid):self.store.migrate(0,{})
        self.assertEqual(self.store.read()["revision"],0)
        self.assertIsNone(self.store.read()["migration"])
        self.assertEqual(self.store.read()["workspace"],server.EMPTY)
class API(Storage):
    def setUp(self):
        super().setUp();self.http=server.make_server(self.store,0);self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()
        self.url="http://127.0.0.1:"+str(self.http.server_port)
    def tearDown(self):
        self.http.shutdown();self.http.server_close();self.thread.join();super().tearDown()
    def request(self,path,body=None,headers=None):
        return urlopen(Request(self.url+path,data=None if body is None else json.dumps(body).encode(),method="GET" if body is None else "POST",headers=headers or {"Content-Type":"application/json","X-Tyr-Editor":"1"}))
    def test_migration_then_put_get(self):
        with self.request("/api/migrate",{"revision":0,"assignments":{}}) as response:self.assertEqual(json.load(response)["revision"],1)
        req=Request(self.url+"/api/workspace",data=json.dumps({"revision":1,"workspace":sample()}).encode(),method="PUT",headers={"Content-Type":"application/json","X-Tyr-Editor":"1"})
        with urlopen(req) as response:self.assertEqual(json.load(response)["revision"],2)
        with self.request("/api/workspace") as response:self.assertEqual(json.load(response)["workspace"],sample())
    def test_migration_foreign_origin_denied(self):
        with self.assertRaises(HTTPError) as e:self.request("/api/migrate",{"revision":0,"assignments":{}},{"Content-Type":"application/json","X-Tyr-Editor":"1","Origin":"https://other.example"})
        self.assertEqual(e.exception.code,403);self.assertEqual(self.store.read()["revision"],0)
    def test_assets_available(self):
        for path in ("/","/app.js","/v2.js","/style.css"):
            with self.request(path) as response:self.assertEqual(response.status,200)
if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--report",type=Path);args=p.parse_args()
    # Storage/API subclass inheritance deliberately exercises persistence with and without a running local HTTP server.
    suite=unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]);result=unittest.TextTestRunner(verbosity=2).run(suite)
    if args.report:
        inputs=[Path(__file__),ROOT/"backend/server.py",ROOT/"backend/workspace_v2.py",*(ROOT/"frontend").glob("*"),*(ROOT/"contracts").rglob("*.json")]
        report={"scope":"P3-A 2.0 SQLite/HTTP migration and graph authoring; no device communication","total":result.testsRun,"passed":result.testsRun-len(result.failures)-len(result.errors),"failures":[str(x) for x in result.failures],"errors":[str(x) for x in result.errors],"sha256":{str(p.relative_to(ROOT)).replace(chr(92),"/"):server.contracts.hashed(p) for p in inputs if p.is_file()}}
        server.contracts.save(args.report,report)
    sys.exit(not result.wasSuccessful())
