"""Tyr P2 local authoring server. No PLC client or outbound requests."""
from contextlib import contextmanager, closing
import argparse
import copy
import hashlib
import json
import re
import sqlite3
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_contracts as contracts
import workspace_v2 as v2
import preview
import sample_quality
import fixed_arrays
import import_files
import import_workflow
import mixed_sources
import change_review
import publication
import semantic_catalog
import semantic_lifecycle
import lifecycle_authoring
import template_authoring
import mapping_templates
import record_mappings
import record_authoring
import result_schemas
import record_preview
import broadcast_authoring
import broadcast_preview
import mixed_object_authoring
import expression_authoring
import pov_evaluation

EMPTY = {"equipment": [], "connections": [], "sources": [], "semantics": [], "mappings": []}
ID = re.compile(r"^[a-z][a-z0-9._/-]*$")
MAX_BODY = 2 * 1024 * 1024

class Invalid(ValueError):
    pass

class Conflict(Exception):
    pass

def require(condition, message):
    if not condition:
        raise Invalid(message)

def exact(value, keys, label):
    require(isinstance(value, dict) and set(value) == set(keys), label + ": unexpected/missing fields")

def identifier(value):
    return isinstance(value, str) and bool(ID.fullmatch(value))

def schema(doc, kind):
    errors = v2.p3.schema_errors(kind,doc) if kind=="semantic-definition" and doc.get("schemaVersion")=="2.12.0" else contracts.validate_schema(kind, doc)
    require(not errors, kind + ": " + "; ".join(str(getattr(e, "message", e)) for e in errors[:3]))

def check_state(state):
    exact(state, EMPTY, "workspace")
    for key in EMPTY:
        require(isinstance(state[key], list) and len(state[key]) <= 1000, key + ": expected list (max 1000)")
    equipment = {}
    for row in state["equipment"]:
        exact(row, ("id", "label"), "equipment")
        require(identifier(row["id"]) and isinstance(row["label"], str) and bool(row["label"].strip()), "equipment: invalid id/label")
        require(row["id"] not in equipment, "equipment: duplicate id")
        equipment[row["id"]] = row
    connections = {}
    for row in state["connections"]:
        exact(row, ("id", "label", "equipmentInstanceId", "accessProfileRef"), "connection")
        require(identifier(row["id"]) and isinstance(row["label"], str) and bool(row["label"].strip()), "connection: invalid id/label")
        require(row["equipmentInstanceId"] in equipment, "connection: missing equipment")
        require(row["accessProfileRef"] in contracts.PROFILES, "connection: unknown access profile")
        require(row["id"] not in connections, "connection: duplicate id")
        connections[row["id"]] = row
    sources = {}
    for row in state["sources"]:
        require(isinstance(row,dict) and set(row) in (set(("definition","note","origin","capturedAt")),set(("definition","note","origin","capturedAt","label"))), "source editor record: unexpected/missing fields")
        if "label" in row:require(isinstance(row["label"],str) and bool(row["label"].strip()),"source: field label required")
        require(isinstance(row["note"], str) and bool(row["note"].strip()), "source: manual evidence note required")
        require(row["origin"] in ("field", "synthetic"), "source: evidence origin required")
        d = row["definition"]
        schema(d, "source-definition")
        require(d["viewOf"] is None or d.get("schemaVersion")=="2.10.0", "P2 authoring supports direct sources only")
        require(d["id"] not in sources, "source: duplicate id")
        if mixed_sources.nonplc(d):
            require(d["equipmentInstanceId"] in equipment and d["connectionProfileRef"] is None,"source: non-PLC context mismatch")
        else:
            c = connections.get(d["connectionProfileRef"])
            require(c is not None, "source: missing logical connection")
            require(c["equipmentInstanceId"] == d["equipmentInstanceId"] and c["accessProfileRef"] == d["accessProfileRef"], "source: connection context/profile mismatch")
            require(d["access"]["kind"] == contracts.PROFILES[d["accessProfileRef"]], "source: access profile mismatch")
        expected = [{"artifactId": "manual-" + d["id"], "locator": {"kind": "text-line", "line": 1}}]
        require(d["evidenceRefs"] == expected, "source: manual evidence reference mismatch")
        sources[d["id"]] = d
    semantics = {}
    for d in state["semantics"]:
        schema(d, "semantic-definition")

        require(d["id"] not in semantics, "semantic: duplicate id")
        semantics[d["id"]] = d
    for d in state["mappings"]:
        schema(d, "mapping-set")

        require(d["equipmentInstanceId"] in equipment, "mapping: missing equipment")
        ref = d["semanticDefinitionRef"]
        require(ref["id"] in semantics and semantics[ref["id"]]["version"] == ref["version"], "mapping: missing semantic version")
        for m in d["mappings"]:
            ops = [t["op"] for t in m["transform"]]
            allowed={"linear","cast","bit-select","enum-map","unit-convert"}
            require(all(op in allowed for op in ops), "Unsupported editor transform")
            ref = m["sourceRef"]
            require(ref["id"] in sources and sources[ref["id"]]["version"] == ref["version"], "mapping: missing source version")
            source = sources[ref["id"]]
            require(source["equipmentInstanceId"] == d["equipmentInstanceId"], "mapping: cross-equipment binding")
            require(m["evidenceRefs"] == source["evidenceRefs"], "mapping: evidence mismatch")
    ids = [d["id"] for d in state["mappings"]]
    require(len(ids) == len(set(ids)), "mapping: duplicate id")
    return state

def build_package(state, folder):
    entries = []
    def document(path, doc):
        contracts.save(folder / path, doc)
        entries.append({"path": path, "kind": doc["kind"], "id": doc["id"], "version": doc["version"], "sha256": contracts.hashed(folder / path)})
    for directory in ("data", "evidence", "sources", "semantics", "mappings"):
        (folder / directory).mkdir(parents=True, exist_ok=True)
    for i, row in enumerate(state["sources"]):
        d = row["definition"]
        path = "data/manual-" + str(i) + ".txt"
        (folder / path).write_text((("Field label: "+row["label"]+"\n") if "label" in row else "")+row["note"] + "\n", encoding="utf-8", newline="\n")
        ev = {"kind": "evidence-artifact", "schemaVersion": "1.0.0", "id": "manual-" + d["id"], "version": d["version"],
              "origin": row["origin"], "file": {"path": path, "sha256": contracts.hashed(folder / path), "mediaType": "text/plain"},
              "capturedAt": row["capturedAt"], "product": None, "scope": [d["equipmentInstanceId"]]}
        schema(ev, "evidence-artifact")
        document("evidence/" + str(i) + ".json", ev)
        document("sources/" + str(i) + ".json", d)
    for kind, docs in (("semantics", state["semantics"]), ("mappings", state["mappings"])):
        for i, d in enumerate(docs):
            document(kind + "/" + str(i) + ".json", d)
    p = {"kind": "mapping-proposal", "schemaVersion": "1.1.0", "id": "local-workspace", "version": "1.0.0", "baseRelease": None, "files": entries}
    schema(p, "mapping-proposal")
    contracts.save(folder / "proposal.json", p)

def findings_for(state):
    if not state["sources"]:
        return [{"ruleCode": "workspace.empty", "path": None}]
    with tempfile.TemporaryDirectory(prefix="tyr-editor-") as tmp:
        folder = Path(tmp)
        build_package(state, folder)
        findings = contracts.validate_package(folder)
    if not state["mappings"]:
        findings.append({"ruleCode": "workspace.no-mapping", "path": None})
    models={d["id"]:d for d in state["semantics"]}
    for mapping in state["mappings"]:
        required={m["memberId"] for m in models[mapping["semanticDefinitionRef"]["id"]]["members"]}
        mapped={m["targetMemberId"] for m in mapping["mappings"]}
        for missing in sorted(required-mapped):
            findings.append({"ruleCode":"mapping.incomplete-object","path":mapping["id"]+"/"+missing})
    for row in state["sources"]:
        if row["definition"]["status"] == "draft":
            findings.append({"ruleCode": "source.draft", "path": row["definition"]["id"]})
    return findings

legacy_check_state=check_state
legacy_build_package=build_package
legacy_findings_for=findings_for

def check_state(state):
    if "workspaceVersion" in state:
        require(v2.is_v2(state), "Unsupported workspaceVersion")
        try:return v2.check(state,legacy_check_state,legacy_build_package)
        except ValueError as e:raise Invalid(str(e)) from e
    result=legacy_check_state(state)
    require(not any(r["definition"].get("schemaVersion") in ("2.7.0","2.10.0") for r in state["sources"]),"Mixed/access-mode sources require the 2.0 authoring workspace")
    require(not any("fixedArray" in r["definition"] for r in state["sources"]),"Fixed arrays require the 2.0 authoring workspace")
    return result

def build_package(state,folder):
    return v2.build(state,folder,legacy_build_package) if v2.is_v2(state) else legacy_build_package(state,folder)

def findings_for(state):
    return v2.findings(state,legacy_build_package) if v2.is_v2(state) else legacy_findings_for(state)

class Store:
    def __init__(self, db):
        self.path = Path(db)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as c:
            c.execute("CREATE TABLE IF NOT EXISTS workspace (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, body TEXT NOT NULL, updated_at TEXT NOT NULL)")
            c.execute("CREATE TABLE IF NOT EXISTS migrations (revision INTEGER PRIMARY KEY, backup TEXT NOT NULL, assignments TEXT NOT NULL, created_at TEXT NOT NULL)")
            change_review.init(c)
            publication.init(c)
            c.execute("CREATE TABLE IF NOT EXISTS preview_scenarios (id TEXT PRIMARY KEY, revision INTEGER NOT NULL, body TEXT NOT NULL, updated_at TEXT NOT NULL)")
            c.execute("INSERT OR IGNORE INTO workspace VALUES (1,0,?,?)", (json.dumps(EMPTY), datetime.now(timezone.utc).isoformat()))
    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            with connection:
                yield connection
        finally:
            connection.close()
    def read(self):
        with self.connect() as c:
            revision, body, at = c.execute("SELECT revision, body, updated_at FROM workspace WHERE id=1").fetchone()
        state = json.loads(body)
        with self.connect() as c:
            migration=c.execute("SELECT revision,backup,assignments,created_at FROM migrations ORDER BY revision DESC LIMIT 1").fetchone()
        return {"revision": revision, "workspace": state, "updatedAt": at, "findings": findings_for(state), "migration": ({"revision":migration[0],"backup":migration[1],"assignments":json.loads(migration[2]),"createdAt":migration[3]} if migration else None)}
    def save(self, revision, state, expression_recipe=None):
        require(type(revision) is int and revision >= 0, "revision: expected nonnegative integer")
        check_state(state)
        findings = findings_for(state)
        at = datetime.now(timezone.utc).isoformat()
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            current_revision,current_body=c.execute("SELECT revision,body FROM workspace WHERE id=1").fetchone()
            if current_revision!=revision:raise Conflict("다른 창에서 변경했습니다. 최신 저장본을 다시 여세요.")
            require(v2.is_v2(json.loads(current_body))==v2.is_v2(state), "버전 변경은 백업이 포함된 마이그레이션을 사용하세요.")
            semantic_lifecycle.check_transition(json.loads(current_body),state)
            mapping_templates.check_transition(json.loads(current_body),state)
            record_mappings.check_transition(json.loads(current_body),state)
            __import__("record_fields").transition(json.loads(current_body),state)
            result_schemas.transition(json.loads(current_body),state)
            try:import_workflow.check_transition(json.loads(current_body),state)
            except ValueError as e:raise Invalid(str(e)) from e
            cursor = c.execute("UPDATE workspace SET revision=revision+1,body=?,updated_at=? WHERE id=1 AND revision=?",
                               (json.dumps(state, ensure_ascii=False, allow_nan=False), at, revision))
            if cursor.rowcount != 1:
                raise Conflict("다른 창에서 변경했습니다. 작성 내용을 복사한 뒤 최신 저장본을 다시 여세요.")
            if expression_recipe is not None:expression_authoring.insert(c,expression_recipe,state,revision+1)
        return {"revision": revision + 1, "workspace": state, "updatedAt": at, "findings": findings}

    def scenarios(self):
        with self.connect() as c:
            revision,body=c.execute("SELECT revision,body FROM workspace WHERE id=1").fetchone()
            rows=c.execute("SELECT revision,body,updated_at FROM preview_scenarios ORDER BY id").fetchall()
        digest=sample_quality.digest(json.loads(body))
        return {"workspaceRevision":revision,"workspaceSha256":digest,"scenarios":[{"scenarioRevision":r,"scenario":json.loads(b),"updatedAt":at,"stale":json.loads(b)["workspaceSha256"]!=digest} for r,b,at in rows]}

    def save_scenario(self,workspace_revision,scenario_revision,doc):
        require(type(workspace_revision) is int and workspace_revision>=0 and type(scenario_revision) is int and scenario_revision>=0,"Invalid scenario revision")
        at=datetime.now(timezone.utc).isoformat()
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            revision,body=c.execute("SELECT revision,body FROM workspace WHERE id=1").fetchone()
            if revision!=workspace_revision:raise Conflict("작성본이 변경됐습니다. 최신 저장본을 다시 여세요.")
            sample_quality.check_scenario(doc,json.loads(body))
            row=c.execute("SELECT revision FROM preview_scenarios WHERE id=?",(doc["id"],)).fetchone()
            actual=row[0] if row else 0
            if actual!=scenario_revision:raise Conflict("가상 시나리오가 변경됐습니다. 목록을 다시 불러오세요.")
            if row is None:
                require(c.execute("SELECT COUNT(*) FROM preview_scenarios").fetchone()[0]<100,"At most 100 virtual scenarios")
                c.execute("INSERT INTO preview_scenarios VALUES (?,?,?,?)",(doc["id"],1,json.dumps(doc,ensure_ascii=False,allow_nan=False),at))
            else:
                c.execute("UPDATE preview_scenarios SET revision=revision+1,body=?,updated_at=? WHERE id=?",(json.dumps(doc,ensure_ascii=False,allow_nan=False),at,doc["id"]))
        return {"workspaceRevision":revision,"scenarioRevision":actual+1,"scenario":doc,"updatedAt":at,"stale":False}

    def migrate(self,revision,assignments):
        require(type(revision) is int and revision>=0 and isinstance(assignments,dict), "Invalid migration request")
        at=datetime.now(timezone.utc).isoformat()
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            current,body=c.execute("SELECT revision,body FROM workspace WHERE id=1").fetchone()
            if current!=revision:raise Conflict("다른 창에서 변경했습니다. 최신 저장본을 다시 여세요.")
            old=json.loads(body)
            require(not v2.is_v2(old), "이미 2.0 작성본입니다.")
            legacy_check_state(old)
            try:new=v2.upgrade(old,assignments)
            except ValueError as e:raise Invalid(str(e)) from e
            check_state(new)
            try:
                backup_dir=self.path.with_suffix(self.path.suffix+".backups");backup_dir.mkdir(exist_ok=True)
                backup=backup_dir/("revision-"+str(revision)+"-"+uuid.uuid4().hex+".sqlite3")
                # Snapshot committed state while the current writer holds its reservation.
                with closing(sqlite3.connect(self.path)) as source:
                    with closing(sqlite3.connect(backup)) as destination:source.backup(destination)
            except (OSError,sqlite3.Error) as e:
                raise Invalid("백업 생성에 실패해 이전하지 않았습니다. 백업 경로와 파일 권한을 확인하세요.") from e
            c.execute("UPDATE workspace SET revision=revision+1,body=?,updated_at=? WHERE id=1",(json.dumps(new,ensure_ascii=False,allow_nan=False),at))
            c.execute("INSERT INTO migrations VALUES (?,?,?,?)",(revision+1,str(backup),json.dumps(assignments),at))
        return self.read()

def make_server(store, port=8765, bifrost_jar=None, mapping_registry=None):
    publication_adapter=publication.Adapter(bifrost_jar,mapping_registry)
    class Handler(BaseHTTPRequestHandler):
        def origin_ok(self):
            host = self.headers.get("Host", "")
            allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            origin = self.headers.get("Origin")
            return host in allowed and (origin is None or origin in {"http://" + x for x in allowed})
        def reply(self, code, body, content_type="application/json; charset=utf-8"):
            if isinstance(body, (dict, list)):
                body = json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8")
            elif isinstance(body, str):
                body = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)
        def do_GET(self):
            if not self.origin_ok():
                return self.reply(403, {"error": "Local origin required"})
            try:
                if self.path == "/api/result-schemas":return self.reply(200,result_schemas.listing(store))
                if self.path == "/api/records":return self.reply(200,record_authoring.listing(store))
                if self.path == "/api/workspace":
                    return self.reply(200, store.read())
                if self.path == "/api/import-workflow":
                    snap=store.read()
                    return self.reply(200,{"revision":snap["revision"],"batches":[{"id":b["id"],"unresolved":import_workflow.unresolved(b),"observations":[{"id":o["id"],"observationSha256":import_workflow.digest(o),"previousReviewSha256":import_workflow.digest(import_workflow.latest(b,o)) if import_workflow.latest(b,o) else None,"recordKey":import_workflow.key(b,o),"latestReview":import_workflow.latest(b,o),"effectiveDraft":import_workflow.materialize(b,o)} for o in b["observations"]]} for b in snap["workspace"].get("imports",[])]})
                if self.path == "/api/scenarios":return self.reply(200,store.scenarios())
                if self.path == "/api/review-baselines":return self.reply(200,change_review.baselines(store))
                if self.path == "/api/reviews":return self.reply(200,change_review.reviews(store))
                if self.path == "/api/mapping-templates":return self.reply(200,template_authoring.listing(store))
                if self.path == "/api/semantic-lifecycle":return self.reply(200,lifecycle_authoring.report(store,publication_adapter))
                if self.path == "/api/expressions":return self.reply(200,expression_authoring.listing(store))
                if self.path == "/api/semantic-catalog":return self.reply(200,semantic_catalog.report(store,publication_adapter))
                if self.path == "/api/submissions":return self.reply(200,publication.listing(store,publication_adapter))
                assets = {"/empty-start.js": ("empty-start.js","text/javascript; charset=utf-8"),"/operator-ux.js": ("operator-ux.js","text/javascript; charset=utf-8"), "/workflow.js": ("workflow.js","text/javascript; charset=utf-8"),"/result-schemas.js": ("result-schemas.js","text/javascript; charset=utf-8"),"/broadcast.js": ("broadcast.js","text/javascript; charset=utf-8"),"/mixed-objects.js": ("mixed-objects.js","text/javascript; charset=utf-8"),"/records.js": ("records.js","text/javascript; charset=utf-8"),"/templates.js": ("templates.js","text/javascript; charset=utf-8"),"/lifecycle.js": ("lifecycle.js","text/javascript; charset=utf-8"),"/expressions.js": ("expressions.js","text/javascript; charset=utf-8"),"/pov.js": ("pov.js","text/javascript; charset=utf-8"),"/structures.js": ("structures.js","text/javascript; charset=utf-8"),"/views.js": ("views.js","text/javascript; charset=utf-8"),"/publication.js": ("publication.js","text/javascript; charset=utf-8"),"/review.js": ("review.js", "text/javascript; charset=utf-8"),"/mixed.js": ("mixed.js", "text/javascript; charset=utf-8"),"/imports.js": ("imports.js", "text/javascript; charset=utf-8"),"/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8"), "/v2.js": ("v2.js", "text/javascript; charset=utf-8"), "/preview.js": ("preview.js", "text/javascript; charset=utf-8"), "/quality.js": ("quality.js", "text/javascript; charset=utf-8"), "/arrays.js": ("arrays.js", "text/javascript; charset=utf-8"), "/style.css": ("style.css", "text/css; charset=utf-8")}
                if self.path in assets:
                    name, mime = assets[self.path]
                    return self.reply(200, (ROOT / "frontend" / name).read_bytes(), mime)
                return self.reply(404, {"error": "Not found"})
            except (Invalid, ValueError) as e:
                return self.reply(422, {"error": str(e)})
        def do_PUT(self):
            if not self.origin_ok() or self.headers.get("X-Tyr-Editor") != "1":
                return self.reply(403, {"error": "Local editor request required"})
            if self.path not in ("/api/result-schema-plan","/api/result-schema-apply","/api/broadcast-compose","/api/broadcast-preview","/api/broadcast-scenarios","/api/mixed-object-compose","/api/mixed-object-apply","/api/record-compose","/api/record-plan","/api/record-apply","/api/record-preview","/api/record-scenarios","/api/template-capture","/api/template-save","/api/template-choices","/api/template-plan","/api/template-apply","/api/semantic-lifecycle-apply","/api/expression-compile","/api/expression-apply","/api/workspace","/api/migrate","/api/preview","/api/logical-preview","/api/scenarios","/api/array-index","/api/import-review","/api/import-adopt-reviewed","/api/import-merge-preview","/api/import-merge-apply","/api/import-preview","/api/import-apply","/api/review-baselines","/api/review-diff","/api/reviews","/api/submissions","/api/submission-refresh","/api/submission-download","/api/submission-maintenance","/api/pov-template","/api/pov-evaluate"):
                return self.reply(404, {"error": "Not found"})
            try:
                length = int(self.headers.get("Content-Length", "-1"))
                require(0 <= length <= MAX_BODY, "Request must be <= 2 MiB")
                require(self.headers.get("Content-Type", "").split(";")[0] == "application/json", "JSON required")
                raw = self.rfile.read(length).decode("utf-8")
                value = json.loads(raw, object_pairs_hook=contracts.pairs, parse_constant=lambda x: (_ for _ in ()).throw(Invalid("Nonfinite JSON")))
                if self.path == "/api/result-schema-plan":return self.reply(200,result_schemas.plan(store,value,Conflict)[0])
                if self.path == "/api/result-schema-apply":return self.reply(200,result_schemas.apply(store,value,Conflict))
                if self.path == "/api/broadcast-compose":return self.reply(200,broadcast_authoring.compose(store,value,Conflict))
                if self.path == "/api/broadcast-scenarios":return self.reply(200,broadcast_authoring.save_scenario(store,value,Conflict))
                if self.path == "/api/broadcast-preview":
                    exact(value,("revision","id","version","snapshot","commonSamples","evaluatedAt"),"broadcast preview request")
                    snap=record_authoring.snapshot(store,value['revision'],Conflict)
                    return self.reply(200,broadcast_preview.run(snap['workspace'],value['id'],value['version'],value['snapshot'],value['commonSamples'],snap['revision'],value['evaluatedAt']))
                if self.path == "/api/mixed-object-compose":return self.reply(200,mixed_object_authoring.compose(store,value,Conflict,build_package))
                if self.path == "/api/mixed-object-apply":return self.reply(200,mixed_object_authoring.apply(store,value,Conflict,build_package))
                if self.path == "/api/record-compose":return self.reply(200,record_authoring.compose(store,value,Conflict))
                if self.path == "/api/record-plan":return self.reply(200,record_authoring.plan(store,value,Conflict)[0])
                if self.path == "/api/record-apply":return self.reply(200,record_authoring.apply(store,value,Conflict))
                if self.path == "/api/record-scenarios":return self.reply(200,record_authoring.save_scenario(store,value,Conflict))
                if self.path == "/api/record-preview":
                    exact(value,("revision","id","version","snapshot","evaluatedAt"),"record preview request")
                    snap=record_authoring.snapshot(store,value['revision'],Conflict)
                    return self.reply(200,record_preview.run(snap['workspace'],value['id'],value['version'],value['snapshot'],snap['revision'],value['evaluatedAt']))
                if self.path == "/api/template-capture":return self.reply(200,template_authoring.capture(store,value,Conflict))
                if self.path == "/api/template-save":return self.reply(200,template_authoring.save_template(store,value,Conflict))
                if self.path == "/api/template-choices":return self.reply(200,template_authoring.binding_choices(store,value,Conflict))
                if self.path == "/api/template-plan":return self.reply(200,template_authoring.plan(store,value,Conflict,build_package)[0])
                if self.path == "/api/template-apply":return self.reply(200,template_authoring.apply(store,value,Conflict,build_package))
                if self.path == "/api/semantic-lifecycle-apply":return self.reply(200,lifecycle_authoring.apply(store,value,Conflict,publication_adapter))
                if self.path in ("/api/expression-compile","/api/expression-apply"):
                    return self.reply(200,expression_authoring.response(store,value,Conflict,check_state,self.path=="/api/expression-apply"))
                if self.path in ("/api/pov-template","/api/pov-evaluate"):
                    exact(value,("revision","mappingSetIds") if self.path=="/api/pov-template" else ("revision","pack"),"evaluation request")
                    require(type(value["revision"]) is int,"Invalid revision")
                    snap=store.read()
                    if value["revision"]!=snap["revision"]:raise Conflict("작성본이 변경됐습니다. 평가 입력을 다시 확인하세요.")
                    if self.path=="/api/pov-template":return self.reply(200,dict(pov_evaluation.template(snap["workspace"],value["mappingSetIds"]),revision=snap["revision"],persisted=False))
                    return self.reply(200,pov_evaluation.evaluate(snap["workspace"],value["pack"],snap["revision"]))
                if self.path=="/api/submissions":return self.reply(200,publication.export(store,value,Conflict,build_package,publication_adapter))
                if self.path=="/api/submission-refresh":return self.reply(200,publication.refresh(store,value,Conflict,publication_adapter))
                if self.path=="/api/submission-maintenance":return self.reply(200,publication.maintenance(store,value))
                if self.path=="/api/submission-download":
                    exact(value,("id",),"submission download")
                    return self.reply(200,publication.download(store,value["id"]))
                if self.path=="/api/review-baselines":return self.reply(200,change_review.baseline(store,value,Conflict))
                if self.path=="/api/review-diff":return self.reply(200,change_review.assessment(store,value,Conflict,findings_for))
                if self.path=="/api/reviews":return self.reply(200,change_review.save_review(store,value,Conflict))
                if self.path in ("/api/import-review","/api/import-adopt-reviewed","/api/import-merge-preview","/api/import-merge-apply"):
                    snap=store.read()
                    require(type(value.get("revision")) is int,"Invalid revision")
                    if value["revision"]!=snap["revision"]:raise Conflict("작성본이 변경됐습니다. 검토/병합을 다시 미리보세요.")
                    require(v2.is_v2(snap["workspace"]),"2.0 workspace required")
                    state=snap["workspace"]
                    if self.path=="/api/import-review":
                        exact(value,("revision","batchId","review"),"review request")
                        next_state=import_workflow.review(state,value["batchId"],value["review"])
                        return self.reply(200,store.save(snap["revision"],next_state))
                    if self.path=="/api/import-adopt-reviewed":
                        exact(value,("revision","batchId","selected"),"adoption request")
                        next_state=import_workflow.adopt(state,value["batchId"],value["selected"])
                        return self.reply(200,store.save(snap["revision"],next_state))
                    expected=("revision","previousBatchId")+ (("batchId",) if "batchId" in value else ("request",))
                    if self.path=="/api/import-merge-apply":expected+=("planSha256","choices","reviewer","reason","reviewedAt")
                    exact(value,expected,"merge request")
                    old=next((b for b in state.get("imports",[]) if b["id"]==value["previousBatchId"]),None)
                    require(old is not None,"Previous batch missing")
                    if "batchId" in value:
                        new=next((b for b in state.get("imports",[]) if b["id"]==value["batchId"]),None);require(new is not None,"Incoming batch missing")
                    else:
                        new=import_files.parse(value["request"],state)
                        require(not any(b["id"]==new["id"] for b in state.get("imports",[])),"Incoming batch ID already exists")
                    ids={e["sourceId"] for e in import_workflow.previous_entries(old,state["sources"])}
                    ours=[r for r in state["sources"] if r["definition"]["id"] in ids]
                    plan=import_workflow.plan(old,new,ours,import_workflow.digest(state))
                    if self.path=="/api/import-merge-preview":
                        return self.reply(200,{"revision":snap["revision"],"batch":new,"plan":plan,"persisted":False,"deviceCommunication":"excluded"})
                    require(value["planSha256"]==plan["planSha256"],"merge.plan-stale")
                    next_state=import_workflow.apply(state,new,plan,value["choices"],value)
                    return self.reply(200,store.save(snap["revision"],next_state))
                if self.path in ("/api/import-preview","/api/import-apply"):
                    exact(value,("revision","request")+(("selected",) if self.path=="/api/import-apply" else ()),"import request")
                    require(type(value["revision"]) is int and value["revision"]>=0,"Invalid revision")
                    snap=store.read()
                    if snap["revision"]!=value["revision"]:raise Conflict("작성본이 변경됐습니다. 다시 가져오세요.")
                    require(v2.is_v2(snap["workspace"]),"2.0 workspace required")
                    batch=import_files.parse(value["request"],snap["workspace"])
                    if self.path=="/api/import-preview":return self.reply(200,{"revision":snap["revision"],"batch":batch,"persisted":False,"deviceCommunication":"excluded"})
                    next_state=import_files.adopt(snap["workspace"],batch,value["selected"])
                    return self.reply(200,store.save(snap["revision"],next_state))
                if self.path=="/api/array-index":
                    exact(value,("revision","sourceRef","indices"),"array-index request")
                    require(type(value["revision"]) is int and value["revision"]>=0,"Invalid revision")
                    exact(value["sourceRef"],("id","version"),"sourceRef")
                    snapshot=store.read()
                    if snapshot["revision"]!=value["revision"]:raise Conflict("작성본이 변경됐습니다. 최신 저장본을 다시 여세요.")
                    matches=[r["definition"] for r in snapshot["workspace"]["sources"] if {"id":r["definition"]["id"],"version":r["definition"]["version"]}==value["sourceRef"]]
                    require(len(matches)==1,"Array source reference missing")
                    try:
                        detail=fixed_arrays.index(matches[0],value["indices"])
                        return self.reply(200,{"revision":snapshot["revision"],"quality":"good","layout":detail,"issues":[],"persisted":False,"deviceCommunication":"excluded"})
                    except fixed_arrays.ArrayError as e:
                        return self.reply(200,{"revision":snapshot["revision"],"quality":"bad","layout":None,"issues":[{"code":e.code,"detail":e.detail}],"persisted":False,"deviceCommunication":"excluded"})
                if self.path=="/api/scenarios":
                    exact(value,("workspaceRevision","scenarioRevision","scenario"),"scenario request")
                    return self.reply(200,store.save_scenario(value["workspaceRevision"],value["scenarioRevision"],value["scenario"]))
                if self.path=="/api/logical-preview":
                    import logical_preview
                    exact(value,("revision","targetInstanceRef","samples")+(("evaluationContext",) if "evaluationContext" in value else ()),"logical preview request")
                    require(type(value["revision"]) is int and value["revision"]>=0,"Invalid revision")
                    exact(value["targetInstanceRef"],("id","version"),"targetInstanceRef")
                    require(isinstance(value["samples"],dict) and len(value["samples"])<=256,"samples: expected object (max 256)")
                    snapshot=store.read()
                    if snapshot["revision"]!=value["revision"]:raise Conflict("작성본이 변경됐습니다.")
                    return self.reply(200,logical_preview.run(snapshot["workspace"],value["targetInstanceRef"],value["samples"],snapshot["revision"],value.get("evaluationContext")))
                if self.path=="/api/preview":
                    exact(value,("revision","mappingSetId","mappingId","samples")+(("evaluationContext",) if "evaluationContext" in value else ()),"preview request")
                    require(type(value["revision"]) is int and value["revision"]>=0,"Invalid revision")
                    snapshot=store.read()
                    if snapshot["revision"]!=value["revision"]:raise Conflict("작성본이 변경됐습니다. 최신 저장본을 열고 다시 미리보세요.")
                    return self.reply(200,preview.run(snapshot["workspace"],value["mappingSetId"],value["mappingId"],value["samples"],snapshot["revision"],value.get("evaluationContext")))
                if self.path=="/api/migrate":
                    exact(value,("revision","assignments"),"migration request")
                    return self.reply(200,store.migrate(value["revision"],value["assignments"]))
                exact(value, ("revision", "workspace"), "request")
                return self.reply(200, store.save(value["revision"], value["workspace"]))
            except Conflict as e:
                return self.reply(409, {"error": str(e)})
            except (Invalid, ValueError, TypeError, KeyError, UnicodeError, RecursionError) as e:
                return self.reply(422, {"error": str(e)})
        do_POST=do_PUT
        def log_message(self, fmt, *args):
            pass
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=0)
    p.add_argument("--db", type=Path, default=ROOT / "build" / "p2" / "workspace.sqlite3")
    p.add_argument("--bifrost-jar",type=Path)
    p.add_argument("--mapping-registry",type=Path)
    args = p.parse_args()
    server = make_server(Store(args.db), args.port,args.bifrost_jar,args.mapping_registry)
    print(f"Tyr editor: http://127.0.0.1:{server.server_port}  DB: {args.db}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
