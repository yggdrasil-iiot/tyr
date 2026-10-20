"""Numeric literal oracles and backward-compatible, atomic authoring persistence."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'backend'),str(R/'scripts')]
import server,expression_literals as e,expression_authoring as a,bounded_expression as old,preview,sample_quality as sq
EQUIP='line-a-motor-ab'
def base():return server.contracts.load(R/'fixtures/p3cc/workspace.json')
def compile(text,w=None):return e.compile_graph(base() if w is None else w,text,'literal-test',EQUIP)
def req(text,revision=2):return dict(revision=revision,graphId='literal-test',equipmentInstanceId=EQUIP,expression=text,compilerVersion='1.1.0')
def evaluate(text,samples=None):
 state,c=a.prepare({'workspace':base()},req(text));server.check_state(state)
 b=next(b for m in state['mappings'] if m['id']=='arithmetic-mapping-ab' for b in m['mappings'] if b['mappingId']=='ab-quotient');b['valueRef']={'kind':'graph','graphRef':{'id':'literal-test','version':'1.0.0'},'nodeId':'expr-result'}
 b['evidenceRefs']=c['graph']['nodes'][-1]['evidenceRefs'];server.check_state(state)
 available=server.contracts.load(R/'fixtures/p3cc/samples.json') if samples is None else samples
 return preview.run(state,'arithmetic-mapping-ab','ab-quotient',{k:v for k,v in available.items() if k in sq.source_ids(state,b)},2),state,c,b
class Compile(unittest.TestCase):
 def test_four_profile_fixture_contracts_and_oracles(self):
  w=server.contracts.load(R/'fixtures/expression-literals/workspace.json');server.check_state(w);self.assertEqual(server.findings_for(w),[])
  samples=server.contracts.load(R/'fixtures/p3cc/samples.json')
  for p in ['ab','ua','db','melsec']:
   b=next(b for m in w['mappings'] if m['id']=='arithmetic-mapping-'+p for b in m['mappings'] if b['mappingId']==p+'-sum')
   v=preview.run(w,'arithmetic-mapping-'+p,p+'-sum',{k:v for k,v in samples.items() if k in sq.source_ids(w,b)},0);self.assertEqual(v['result']['value'],'53');self.assertEqual(v['quality'],'good')
 def test_decimal_factor_independent_oracle(self):
  v,w,c,b=evaluate('[structure-ab-actual] * 0.1');self.assertEqual(v['result']['value'],'15');self.assertEqual(c['output']['unit']['code'],'kPa');self.assertEqual(len(sq.source_ids(w,b)),1)
 def test_explicit_unit_addition_oracle(self):self.assertEqual(evaluate('[structure-ab-actual] + quantity(3, "kPa")')[0]['result']['value'],'153')
 def test_signed_literals_and_parentheses(self):self.assertEqual(evaluate('[structure-ab-actual] * (-0.5) + quantity(+100, "kPa")')[0]['result']['value'],'25')
 def test_bare_number_does_not_guess_pressure_unit(self):self.assertRaisesRegex(ValueError,'graph.input-unit',compile,'[structure-ab-actual] + 3')
 def test_no_implicit_unit_conversion(self):self.assertRaisesRegex(ValueError,'graph.input-unit',compile,'[structure-ab-actual] + quantity(3, "bar")')
 def test_reject_code_strings_dynamic_units_unary_sources(self):
  for text in ['quantity(3, "psi")','quantity(3, [unit])','quantity([arithmetic-ab-gain], "1")','"3"','eval(3)','- [structure-ab-actual]','quantity(3, "kPa\\x")','1e2','01','NaN','quantity(3,"kPa",4)']:
   with self.subTest(text=text):self.assertRaises(ValueError,compile,text)
 def test_old_compiler_still_refuses_literals(self):self.assertRaises(ValueError,old.compile_graph,base(),'1','literal-test',EQUIP)
 def test_deterministic_graph_id_and_canonical_literal_reuse(self):
  c=compile('1.00 + 1');self.assertEqual(len(c['generatedSources']),1);self.assertEqual(len(c['literalOrigins']),2);self.assertEqual(c['graph'],compile('1.00 + 1')['graph']);self.assertEqual(c['sourceContextSha256'],compile('1.00 + 1')['sourceContextSha256'])
 def test_long_decimal_not_rounded_by_ambient_context(self):
  n='0.123456789012345678901234567890123456789';self.assertEqual(compile(n)['generatedSources'][0]['definition']['access']['value'],n)
 def test_signed_zero_canonical(self):self.assertEqual(compile('-0.000')['generatedSources'][0]['definition']['access']['value'],'0')
 def test_origins_cover_literal_source_text(self):
  c=compile('[structure-ab-actual]*(-0.5)+quantity(100,"kPa")');self.assertEqual([c['expression'][o['start']:o['end']] for o in c['literalOrigins']],['(-0.5)','quantity(100,"kPa")'])
 def test_generation_uses_existing_wire_and_evidence(self):
  c=compile('quantity(3,"kPa")');d=c['generatedSources'][0];self.assertEqual(d['origin'],'synthetic');self.assertEqual(d['definition']['schemaVersion'],'2.7.0');self.assertEqual(c['graph']['schemaVersion'],'2.15.0');self.assertIn('3 kPa',d['label']);self.assertTrue(d['capturedAt'].endswith('Z'))
 def test_root_constant_and_precision_loss(self):
  c=compile('quantity(3,"kPa")');self.assertEqual(c['graph']['nodes'][0]['op'],'identity')
  v=evaluate('[structure-ab-actual] / 3',{'structure-ab-actual':{'typedValue':'1'}})[0];self.assertEqual(next(t['value'] for t in v['trace'] if t['stage']=='graph:divide'),'0.3333333333333333333333333333333333');self.assertEqual(len(v['losses']),2)
 def test_zero_and_missing_runtime(self):
  self.assertIn('value.divide-zero',{i['code'] for i in evaluate('[structure-ab-actual] / 0')[0]['issues']});self.assertIsNone(evaluate('[structure-ab-actual] * 0.1',{})[0]['result'])
 def test_limit(self):self.assertRaises(ValueError,compile,'9'*65)
class Persistence(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.store=server.Store(Path(self.tmp.name)/'editor.sqlite3');self.store.migrate(0,{});self.store.save(1,base())
 def tearDown(self):self.tmp.cleanup()
 def call(self,text,apply=False):return a.response(self.store,req(text,self.store.read()['revision']),server.Conflict,server.check_state,apply)
 def test_compile_does_not_persist_generated_sources(self):
  snap=self.store.read();self.call('[structure-ab-actual]*0.1');self.assertEqual(self.store.read(),snap);self.assertEqual(a.listing(self.store)['recipes'],[])
 def test_atomic_save_reopen_and_same_literal_reuse(self):
  self.call('[structure-ab-actual]*0.1',True);snap=self.store.read();rows=copy.deepcopy(snap['workspace']['sources']);self.call('[structure-ab-actual] * 0.10',True);self.assertEqual(self.store.read()['workspace']['sources'],rows);recipes=a.listing(server.Store(self.store.path))['recipes'];self.assertEqual(recipes[0]['state'],'current');self.assertEqual(len(recipes[0]['history']),2)
 def test_changed_literal_retains_old_source_and_recipe(self):
  self.call('[structure-ab-actual]*0.1',True);before=self.store.read()['workspace']['sources'];self.call('[structure-ab-actual]*0.2',True);after=self.store.read()['workspace']['sources'];self.assertEqual(after[:-1],before);self.assertEqual(len(a.listing(self.store)['recipes'][0]['history']),2)
 def test_manual_constant_change_stale_and_collision_refused(self):
  self.call('[structure-ab-actual]*0.1',True);snap=self.store.read();w=snap['workspace'];w['sources'][-1]['definition']['access']['value']='0.9';self.store.save(snap['revision'],w);self.assertEqual(a.listing(self.store)['recipes'][0]['state'],'stale');before=self.store.read();self.assertRaisesRegex(ValueError,'literal-collision',self.call,'[structure-ab-actual]*0.1',True);self.assertEqual(before,self.store.read())
 def test_transaction_failure_rolls_back_sources_graph_recipe(self):
  snap=self.store.read()
  with patch.object(a,'insert',side_effect=ValueError('fault')):self.assertRaisesRegex(ValueError,'fault',self.call,'[structure-ab-actual]*0.1',True)
  self.assertEqual(self.store.read(),snap);self.assertEqual(a.listing(self.store)['recipes'],[])
 def test_version_1_recipe_still_loads_and_compiles(self):
  q=req('[structure-ab-actual]');q.pop('compilerVersion');r=a.response(self.store,q,server.Conflict,server.check_state,True);self.assertEqual(r['compilation']['compilerVersion'],'1.0.0');self.call('[structure-ab-actual]*0.1',True);hist=a.listing(self.store)['recipes'][0]['history'];self.assertEqual([h['compilation']['compilerVersion'] for h in hist],['1.1.0','1.0.0'])
 def test_invalid_version_refused(self):
  q=req('1');q['compilerVersion']='9.0.0';self.assertRaisesRegex(ValueError,'Unsupported',a.prepare,{'workspace':base()},q)
if __name__=='__main__':unittest.main(verbosity=2)
