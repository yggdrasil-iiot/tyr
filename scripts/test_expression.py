"""Independent numeric oracles, authoring/compiler limits, atomic local recipe persistence."""
import copy,json,sys,tempfile,unittest,threading,sqlite3
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request,urlopen
from urllib.error import HTTPError
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'backend'),str(R/'scripts')]
import server,bounded_expression as e,expression_authoring as a,preview,sample_quality as sq

def load(n='workspace'):return server.contracts.load(R/'fixtures/expression'/(n+'.json'))
def base():return server.contracts.load(R/'fixtures/p3cc/workspace.json')
def expression(profile='ab'):return load('cases')['profiles'][profile]['expression']
def request(text=None,id='formula-new'):return {'revision':2,'graphId':id,'equipmentInstanceId':'line-a-motor-ab','expression':text or expression()}
def compile(w=None,text=None):return e.compile_graph(base() if w is None else w,expression() if text is None else text,'formula-new','line-a-motor-ab')
def evaluate(text,samples=None):
 w=base();compiled=compile(w,text);w['graphs'].append(compiled['graph']);b=next(b for m in w['mappings'] if m['id']=='arithmetic-mapping-ab' for b in m['mappings'] if b['mappingId']=='ab-quotient');b['valueRef']={'kind':'graph','graphRef':{'id':'formula-new','version':'1.0.0'},'nodeId':'expr-result'}
 server.check_state(w);available=server.contracts.load(R/'fixtures/p3cc/samples.json') if samples is None else samples;return preview.run(w,'arithmetic-mapping-ab','ab-quotient',{k:v for k,v in available.items() if k in sq.source_ids(w,b)},2)
class Compile(unittest.TestCase):
 def test_four_profiles_existing_contract_and_independent_oracle(self):
  w=load();server.check_state(w);self.assertEqual(server.findings_for(w),[])
  for p,case in load('cases')['profiles'].items():
   c=e.compile_graph(base(),case['expression'],case['graphId'],case['equipmentInstanceId']);self.assertEqual(c['graph'],next(g for g in w['graphs'] if g['id']==case['graphId']));self.assertEqual([n['op'] for n in c['graph']['nodes']],case['expectedOps'])
   b=next(b for m in w['mappings'] if m['id']=='arithmetic-mapping-'+p for b in m['mappings'] if b['mappingId']==p+'-quotient');available=server.contracts.load(R/'fixtures/p3cc/samples.json');v=preview.run(w,'arithmetic-mapping-'+p,p+'-quotient',{k:v for k,v in available.items() if k in sq.source_ids(w,b)},2);self.assertEqual(v['result']['value'],case['expectedNominal'])
 def test_precedence_parentheses_and_named_ports(self):
  self.assertEqual(evaluate('[structure-ab-actual] - [structure-ab-target] * [arithmetic-ab-gain]')['result']['value'],'50')
  self.assertEqual(evaluate('([structure-ab-actual] - [structure-ab-target]) * [arithmetic-ab-gain]')['result']['value'],'200')
 def test_left_association(self):self.assertEqual(evaluate('[structure-ab-actual] / [arithmetic-ab-gain] / [arithmetic-ab-gain]')['result']['value'],'37.5')
 def test_decimal_division_and_final_cast_loss(self):
  samples={'structure-ab-actual':{'typedValue':'1'},'structure-ab-target':{'typedValue':'0'},'arithmetic-ab-gain':{'typedValue':'3'}};v=evaluate(expression(),samples);self.assertEqual(next(t for t in v['trace'] if t['stage']=='graph:divide')['value'],load('cases')['divisionThird']);self.assertEqual(len(v['losses']),2)
 def test_zero_is_runtime_error_not_static_guessed(self):
  c=compile();self.assertEqual(c['output']['valueType'],'Decimal');v=evaluate(expression(),{'structure-ab-actual':{'typedValue':'1'},'structure-ab-target':{'typedValue':'0'},'arithmetic-ab-gain':{'typedValue':'0'}});self.assertIsNone(v['result']);self.assertIn('value.divide-zero',{x['code'] for x in v['issues']})
 def test_missing_quality_and_time_are_existing_preview_policy(self):
  v=evaluate(expression(),{});self.assertIsNone(v['result']);self.assertEqual(v['quality'],'bad')
 def test_functions_and_signed_decimal_constants(self):
  self.assertEqual(evaluate('clamp(linear([structure-ab-actual],-0.5,100),-10,20)')['result']['value'],'20')
  c=compile(text='sqrt([arithmetic-ab-gain])');self.assertEqual(c['graph']['nodes'][0]['precision'],34);self.assertEqual(c['output']['unit']['code'],'1')
 def test_identity_scalar(self):
  c=compile(text='[structure-ab-actual]');self.assertEqual(c['graph']['nodes'][0]['op'],'identity');self.assertEqual(c['output']['valueType'],'UInt16')
 def test_output_evidence_and_origins_are_deterministic(self):
  c=compile();self.assertEqual(c,compile());self.assertEqual(c['graph']['nodes'][-1]['nodeId'],'expr-result');self.assertTrue(all(n['evidenceRefs'] for n in c['graph']['nodes']));self.assertTrue(all(0<=o['start']<o['end']<=len(c['expression']) for o in c['origins']));self.assertEqual(sq.digest(c['graph']),c['graphSha256'])
 def test_parenthesized_source_ranges_are_complete(self):
  c=compile();root=c['origins'][-1];self.assertEqual(c['expression'][root['start']:root['end']],c['expression']);first=c['origins'][0];self.assertEqual(c['expression'][first['start']:first['end']],'([structure-ab-actual] - [structure-ab-target])')
  text='(([structure-ab-actual]))';c=compile(text=text);self.assertEqual(c['expression'][c['origins'][0]['start']:c['origins'][0]['end']],text)
 def test_unsupported_or_executable_syntax_refused(self):
  for text in ['__import__("os")','eval([structure-ab-actual])','[structure-ab-actual]; SELECT 1','[structure-ab-actual] ** [arithmetic-ab-gain]','[structure-ab-actual].value','[structure-ab-actual] + 1','- [structure-ab-actual]','[structure-ab-actual] # comment','{other-graph}','[structure-ab-actual][0]']:
   with self.subTest(text=text):self.assertRaises(ValueError,compile,text=text)
 def test_malformed_functions_and_decimal_grammar(self):
  for text in ['sqrt()','sqrt([arithmetic-ab-gain],1)','clamp([structure-ab-actual],10,1)','clamp([structure-ab-actual],01,10)','linear([structure-ab-actual],1e2,0)','linear([structure-ab-actual],NaN,0)','linear([structure-ab-actual],1,0,1)']:
   with self.subTest(text=text):self.assertRaises(ValueError,compile,text=text)
 def test_unit_dimension_temperature_and_type_refusal(self):
  for text in ['[structure-ab-actual]*[structure-ab-target]','[arithmetic-ab-gain]/[structure-ab-target]','sqrt([structure-ab-actual])']:
   self.assertRaisesRegex(ValueError,'graph.input-unit',compile,text=text)
  for field,value in [('unit',{'status':'known','code':'Cel'}),('unit',{'status':'unknown'}),('rawRepresentation',{'valueType':'Boolean'})]:
   w=base();w['sources'][0]['definition'][field]=value;self.assertRaises(ValueError,compile,w)
 def test_explicit_missing_ambiguous_and_cross_equipment_refs(self):
  self.assertRaisesRegex(ValueError,'source-missing',compile,text='[not-present]');self.assertRaisesRegex(ValueError,'value.equipment',compile,text='[structure-ua-actual]')
  w=base();w['sources'].append(copy.deepcopy(w['sources'][0]));self.assertRaisesRegex(ValueError,'ambiguous',compile,w)
 def test_ready_readable_and_already_engineered_rules(self):
  for key,value in [('status','draft'),('accessMode','write')]:
   w=base();w['sources'][0]['definition'][key]=value;self.assertRaisesRegex(ValueError,'not-readable',compile,w)
  w=base();w['sources'][0]['definition']['inputStage']='already-engineered';self.assertRaisesRegex(ValueError,'double-transform',compile,w,text='linear([structure-ab-actual],2,0)')
 def test_length_tokens_depth_nodes_and_decimal_limits(self):
  for text in ['', ' '*4097,'('*34+'[structure-ab-actual]'+')'*34,'+'.join(['[structure-ab-actual]']*66),'linear([structure-ab-actual],'+('9'*65)+',0)', '('*260+'[structure-ab-actual]'+')'*260]:self.assertRaises(ValueError,compile,text=text)
 def test_view_parent_in_source_context(self):
  w=server.contracts.load(R/'fixtures/a07/workspace.json');src=next(s['definition'] for s in w['sources'] if s['definition'].get('viewOf'));ctx=e.context(w,[src['id']],src['equipmentInstanceId']);self.assertIn(src['viewOf']['id'],[s['id'] for s in ctx['sources']])
 def test_view_parent_readiness_cannot_be_hidden_by_alias(self):
  w=base();parent=w['sources'][0]['definition'];alias=copy.deepcopy(w['sources'][0]);alias['definition'].update(id='alias-word',schemaVersion='2.10.0',sourceKind='plc',accessMode='read',viewOf={'id':parent['id'],'version':parent['version']},view={'kind':'alias'});w['sources'].append(alias);parent['status']='draft';self.assertRaisesRegex(ValueError,'source-not-readable',compile,w,text='[alias-word]')
 def test_compiled_graph_size_is_bounded(self):
  w=base();w['sources'][0]['definition']['evidenceRefs']=[{'artifactId':'manual-structure-ab-actual','locator':{'kind':'text-line','line':i}} for i in range(1,257)]
  self.assertRaisesRegex(ValueError,'graph-size',compile,w,text='+'.join(['[structure-ab-actual]']*64))
class Persistence(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.store=server.Store(Path(self.tmp.name)/'editor.sqlite3');self.store.migrate(0,{});self.store.save(1,base())
 def tearDown(self):self.tmp.cleanup()
 def response(self,req=None,apply=False):return a.response(self.store,request() if req is None else req,server.Conflict,server.check_state,apply)
 def test_compile_and_listing_do_not_migrate_or_write(self):
  with self.store.connect() as db:before=list(db.iterdump())
  self.response();self.assertEqual(a.listing(self.store)['recipes'],[])
  with self.store.connect() as db:self.assertEqual(before,list(db.iterdump()))
 def test_atomic_save_history_and_reopen(self):
  r=self.response(apply=True);self.assertTrue(r['persisted']);self.assertEqual(r['saved']['revision'],3);self.assertEqual(a.listing(server.Store(self.store.path))['recipes'][0]['state'],'current')
  q=request('[structure-ab-actual]-[structure-ab-target]');q['revision']=3;self.response(q,True);rows=a.listing(self.store)['recipes'];self.assertEqual(len(rows[0]['history']),2);self.assertEqual(rows[0]['history'][-1]['compilation']['expression'],expression())
 def test_stale_revision_refuses_without_recipe_or_workspace_change(self):
  before=self.store.read();q=request();q['revision']=1
  with self.assertRaises(server.Conflict):self.response(q,True)
  self.assertEqual(self.store.read(),before);self.assertFalse(a.listing(self.store)['recipes'])
 def test_manual_graph_replacement_and_equipment_move_refused(self):
  self.assertRaisesRegex(ValueError,'Manual graph',self.response,request(id='arithmetic-ab'),True);self.response(apply=True);q=request();q.update(revision=3,equipmentInstanceId='line-a-motor-ua',expression='[structure-ua-actual]');self.assertRaisesRegex(ValueError,'equipment',self.response,q,True)
 def test_rollback_includes_lazy_table_and_workspace_update(self):
  before=self.store.read();original=a.insert
  def fail(*args):original(*args);raise ValueError('injected after recipe insertion')
  with patch.object(a,'insert',fail):self.assertRaisesRegex(ValueError,'injected',self.response,apply=True)
  self.assertEqual(self.store.read(),before)
  with self.store.connect() as db:self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='expression_recipes'").fetchone())
 def test_manual_graph_edit_marks_stale_and_explicit_recompile_restores(self):
  self.response(apply=True);snap=self.store.read();g=next(g for g in snap['workspace']['graphs'] if g['id']=='formula-new');g['nodes'][0]['op']='add';self.store.save(3,snap['workspace']);self.assertEqual(a.listing(self.store)['recipes'][0]['state'],'stale');q=request();q['revision']=4;self.response(q,True);self.assertEqual(a.listing(self.store)['recipes'][0]['state'],'current')
 def test_source_and_connection_context_changes_mark_stale(self):
  self.response(apply=True);snap=self.store.read();snap['workspace']['sources'][0]['definition']['rawAddressText']='changed evidence spelling';self.store.save(3,snap['workspace']);self.assertEqual(a.listing(self.store)['recipes'][0]['state'],'stale');snap=self.store.read();snap['workspace']['sources'][0]['definition']['rawAddressText']=base()['sources'][0]['definition']['rawAddressText'];snap['workspace']['connections'][0]['label']='changed logical connection';self.store.save(4,snap['workspace']);self.assertEqual(a.listing(self.store)['recipes'][0]['state'],'stale')
 def test_unrelated_source_edit_does_not_mark_stale(self):
  self.response(apply=True);snap=self.store.read();s=next(s for s in snap['workspace']['sources'] if s['definition']['id']=='structure-ua-actual');s['definition']['rawAddressText']='unrelated';self.store.save(3,snap['workspace']);self.assertEqual(a.listing(self.store)['recipes'][0]['state'],'current')
 def test_deleted_graph_keeps_recipe_history(self):
  self.response(apply=True);snap=self.store.read();snap['workspace']['graphs']=[g for g in snap['workspace']['graphs'] if g['id']!='formula-new'];self.store.save(3,snap['workspace']);self.assertEqual(a.listing(self.store)['recipes'][0]['state'],'missing-graph');self.assertEqual(len(a.listing(self.store)['recipes'][0]['history']),1)
 def test_oversized_history_fault_refuses_write_without_dropping_rows(self):
  with self.store.connect() as db:
   db.execute('CREATE TABLE expression_recipes(graph_id TEXT,revision INTEGER,body TEXT,PRIMARY KEY(graph_id,revision))');db.execute('INSERT INTO expression_recipes VALUES (?,?,?)',('retained',1,'x'*(16*1024*1024)))
  before=self.store.read();self.assertRaisesRegex(ValueError,'history exceeds',self.response,apply=True);self.assertEqual(self.store.read(),before)
  with self.store.connect() as db:self.assertEqual(db.execute('SELECT length(body) FROM expression_recipes').fetchone()[0],16*1024*1024)
 def test_http_origin_stale_compile_apply_and_bad_request(self):
  http=server.make_server(self.store,0);th=threading.Thread(target=http.serve_forever,daemon=True);th.start();origin='http://127.0.0.1:'+str(http.server_port)
  def post(path,q,foreign=False):return urlopen(Request(origin+path,data=json.dumps(q).encode(),headers={'Content-Type':'application/json','X-Tyr-Editor':'1','Origin':'http://outside.invalid' if foreign else origin}))
  try:
   with post('/api/expression-compile',request()) as r:self.assertFalse(json.load(r)['persisted'])
   with post('/api/expression-apply',request()) as r:self.assertTrue(json.load(r)['persisted'])
   with self.assertRaises(HTTPError) as err:post('/api/expression-apply',request())
   self.assertEqual(err.exception.code,409)
   with self.assertRaises(HTTPError) as err:post('/api/expression-compile',request(),True)
   self.assertEqual(err.exception.code,403)
   with self.assertRaises(HTTPError) as err:post('/api/expression-compile',{'revision':3})
   self.assertEqual(err.exception.code,422)
  finally:http.shutdown();http.server_close();th.join()
if __name__=='__main__':unittest.main()
