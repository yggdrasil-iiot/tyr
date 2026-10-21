"""Independent schema preparation and unchanged publication/SQLite contracts."""
import copy,json,sys,tempfile,unittest,sqlite3,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'scripts'),str(R/'backend')]
import server,result_schemas as rs,mapping_templates as mt,record_mappings as rm,broadcast_authoring as ba,record_authoring as ra,broadcast_preview as bp,publication
F=R/'fixtures/workflow'
def load(n):return server.contracts.load(F/n)
def state():return load('before.json')
def definition():return load('definition.json')
def seed(st):st.migrate(0,{});st.save(1,state())
def store_schema(st,d=None,revision=2):
 d=definition() if d is None else d;p,_=rs.plan(st,dict(revision=revision,definition=d),server.Conflict);return rs.apply(st,dict(revision=revision,definition=d,planSha256=p['planSha256']),server.Conflict)
class Workflow(unittest.TestCase):
 def test_independent_schema_no_mapping_or_template(self):
  with tempfile.TemporaryDirectory() as t:
   st=server.Store(Path(t)/'editor.sqlite3');seed(st);before=st.read();p,_=rs.plan(st,dict(revision=2,definition=definition()),server.Conflict);self.assertEqual(st.read(),before);saved=store_schema(st);w=saved['saved']['workspace'];self.assertEqual(w.get('recordMappings',[]),[]);self.assertEqual(w.get('mappingTemplates',[]),[]);self.assertEqual(len(w['resultSchemas']),1);self.assertEqual(rs.listing(st)['schemas'][0]['origin'],'catalog')
 def test_catalog_then_array_preview_and_release_closure(self):
  with tempfile.TemporaryDirectory() as t:
   st=server.Store(Path(t)/'editor.sqlite3');seed(st);store_schema(st);p=ba.compose(st,load('request.json'),server.Conflict);saved=ra.apply(st,dict(revision=3,draft=p['draft'],planSha256=p['planSha256']),server.Conflict);w=saved['saved']['workspace'];r=w['recordMappings'][0];s=server.contracts.load(R/'fixtures/broadcast/snapshot.json');s['resultSetRef']=rm.pin(r['resultSchema']);v=server.contracts.load(R/'fixtures/broadcast/common-samples.json');p=bp.run(w,r['id'],r['version'],s,v,4,'2026-10-18T00:00:00.500Z');self.assertEqual([x['target'] for x in p['result']],['90','95']);folder=Path(t)/'bundle';_,_,errors=publication.build(w,folder,'workflow','workflow-line','proposer',None,['record:'+r['id']+'@'+r['version']],False,server.build_package);self.assertEqual(errors,[]);proposal=server.contracts.load(folder/'proposal.json');self.assertEqual(proposal['schemaVersion'],'2.22.0');self.assertFalse(any(e['kind']=='result-schema-definition' for e in proposal['files']))
 def test_schema_shape_key_and_query_rejections(self):
  for kind in ['duplicate','key-type','key-null','missing-key','query','oversize']:
   with self.subTest(kind=kind):
    s=copy.deepcopy(definition()['resultSchema'])
    if kind=='duplicate':s['fields'].append(copy.deepcopy(s['fields'][0]))
    if kind=='key-type':s['fields'][0]['valueType']='Int32'
    if kind=='key-null':s['fields'][0]['nullable']=True
    if kind=='missing-key':s['keyFields']=['missing']
    if kind=='query':s['query']={'language':'none','text':'SELECT 1'}
    if kind=='oversize':s['fields']*=9
    self.assertRaises(ValueError,rs.validate,s)
 def test_CAS_tamper_and_reopen(self):
  with tempfile.TemporaryDirectory() as t:
   st=server.Store(Path(t)/'editor.sqlite3');seed(st);before=st.read();p,_=rs.plan(st,dict(revision=2,definition=definition()),server.Conflict);self.assertRaises(ValueError,rs.apply,st,dict(revision=2,definition=definition(),planSha256='0'*64),server.Conflict);self.assertEqual(st.read(),before);store_schema(st);self.assertRaises(server.Conflict,store_schema,st);self.assertEqual(server.Store(st.path).read()['workspace']['resultSchemas'],[definition()])
 def test_existing_schema_cannot_change_or_be_deleted(self):
  with tempfile.TemporaryDirectory() as t:
   st=server.Store(Path(t)/'editor.sqlite3');seed(st);store_schema(st)
   for change in ['edit','delete']:
    w=st.read()['workspace']
    if change=='edit':w['resultSchemas'][0]['label']='changed'
    else:w['resultSchemas']=[]
    self.assertRaisesRegex(ValueError,'result-schema.history-immutable',st.save,3,w)
 def test_new_version_chain_and_usage(self):
  with tempfile.TemporaryDirectory() as t:
   st=server.Store(Path(t)/'editor.sqlite3');seed(st);store_schema(st);d=definition();d.update(version='1.0.1',previousSchemaRef=mt.pin(definition()));d['resultSchema']['version']='1.0.1';d['resultSchema']['fields'][1]['name']='Updated display';store_schema(st,d,3);self.assertEqual(len(rs.listing(st)['definitions']),2);self.assertEqual(rs.listing(st)['schemas'][0]['resultSchema'],definition()['resultSchema'])
 def test_bad_previous_pin_and_identity(self):
  w=state();d=definition();d['previousSchemaRef']=mt.pin(d);w['resultSchemas']=[d];self.assertRaisesRegex(ValueError,'version-chain',rs.check,w);d=definition();d['resultSchema']['version']='2.0.0';w['resultSchemas']=[d];self.assertRaisesRegex(ValueError,'identity',rs.check,w)
 def test_inline_collision_and_legacy_discovery(self):
  w=server.contracts.load(R/'fixtures/broadcast/workspace.json');d=definition();old=w['recordMappings'][0]['resultSchema'];d.update(id=old['id'],version=old['version'],resultSchema=copy.deepcopy(old));d['resultSchema']['fields'][1]['name']='changed';w['resultSchemas']=[d];self.assertRaisesRegex(ValueError,'inline-conflict',rs.check,w)
 def test_unused_catalog_does_not_change_old_wire_package(self):
  with tempfile.TemporaryDirectory() as t:
   old=server.contracts.load(R/'fixtures/broadcast/workspace.json');new=copy.deepcopy(old);new['resultSchemas']=[definition()];a=Path(t)/'a';b=Path(t)/'b';a.mkdir();b.mkdir();server.build_package(old,a);server.build_package(new,b);self.assertEqual({p.relative_to(a).as_posix():p.read_bytes() for p in a.rglob('*') if p.is_file()},{p.relative_to(b).as_posix():p.read_bytes() for p in b.rglob('*') if p.is_file()})
 def test_old_sqlite_read_does_not_migrate(self):
  with tempfile.TemporaryDirectory() as t:
   st=server.Store(Path(t)/'editor.sqlite3');seed(st)
   with st.connect() as c:before=list(c.iterdump())
   rs.listing(st)
   with st.connect() as c:self.assertEqual(before,list(c.iterdump()))
 def test_catalog_storage_uses_existing_tables_only(self):
  with tempfile.TemporaryDirectory() as t:
   st=server.Store(Path(t)/'editor.sqlite3');seed(st)
   with st.connect() as c:before=list(c.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name"))
   store_schema(st)
   with st.connect() as c:self.assertEqual(before,list(c.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name")))
 def test_all_legacy_navigation_entries_preserved(self):
  import re
  s=(R/'frontend/index.html').read_text(encoding='utf-8');tabs=re.findall(r'<button data-tab="([^"]+)"',s);self.assertEqual(len(tabs),23);self.assertEqual(len(set(tabs)),23);self.assertEqual(len(re.findall('data-workflow-group=',s)),5)
 def test_baseline_files_byte_identical(self):
  pins=server.contracts.load(R/'docs/verification/workflow-baseline-pins.json');self.assertEqual([n for n,h in pins.items() if hashlib.sha256((R/n).read_bytes()).hexdigest()!=h],[])
if __name__=='__main__':unittest.main(verbosity=2)
