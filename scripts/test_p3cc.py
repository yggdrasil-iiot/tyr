"""Bounded scalar add/multiply/divide: independent numeric oracles and governance seams."""
import copy,json,sys,tempfile,threading,unittest
from decimal import Decimal,localcontext,ROUND_DOWN
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/"backend"),str(R/"scripts")]
import server,preview,sample_quality as sq,p3a_contracts as p3,bounded_arithmetic as a,publication as pub
F=R/'fixtures/p3cc'
def load(name='workspace'):return server.contracts.load(F/(name+'.json'))
def codes(v):return {i['code'] for i in v['issues']}
def binding(w,profile,member):return next(b for b in next(m for m in w['mappings'] if m['id']=='arithmetic-mapping-'+profile)['mappings'] if b['mappingId']==profile+'-'+member)
def run(w,profile='ab',member='ratio',samples=None,evaluation=None):
 b=binding(w,profile,member);available=load('samples') if samples is None else samples;used=sq.source_ids(w,b);inputs={id:available[id] for id in used if id in available};return preview.run(w,'arithmetic-mapping-'+profile,profile+'-'+member,inputs,2,evaluation)
class Arithmetic(unittest.TestCase):
 def test_four_profiles_and_all_operations(self):
  w=load();server.check_state(w);self.assertEqual(server.findings_for(w),[])
  for profile in ['ab','ua','db','melsec']:
   for member,value in load('expected')['nominal'].items():
    with self.subTest(profile=profile,member=member):
     v=run(w,profile,member);self.assertEqual(v['result']['value'],value);self.assertEqual(v['quality'],'good');self.assertFalse(v['losses'])
 def test_decimal_division_oracles_and_final_cast(self):
  w=load();s=load('samples');s['structure-ab-actual']={'typedValue':'1'};s['structure-ab-target']={'typedValue':'3'};v=run(w,samples=s);oracle=load('expected')['divisionThird'];step=next(t for t in v['trace'] if t['stage']=='graph:divide');self.assertEqual(step['value'],oracle['graphValue']);self.assertEqual(v['result']['value'],oracle['finalValue']);self.assertEqual(len(v['losses']),2);self.assertEqual(v['quality'],'uncertain');self.assertIn('loss.precision',codes(v))
 def test_exact_final_cast_refuses_precision_loss(self):
  w=load();binding(w,'ab','ratio')['transform'][0]['rounding']='exact';s=load('samples');s['structure-ab-actual']={'typedValue':'1'};s['structure-ab-target']={'typedValue':'3'};v=run(w,samples=s);self.assertIsNone(v['result']);self.assertIn('value.inexact',codes(v));self.assertIn('loss.precision',codes(v))
 def test_zero_and_negative_zero_rejected(self):
  for zero in [Decimal('0'),Decimal('-0')]:
   with self.assertRaisesRegex(ValueError,'value.divide-zero'):a.calculate('divide',Decimal(1),zero,34,'half-even')
  w=load();s=load('samples');s['structure-ab-target']={'typedValue':'0'};v=run(w,samples=s);self.assertIsNone(v['result']);self.assertEqual(v['quality'],'bad');self.assertIn('value.divide-zero',codes(v))
 def test_named_left_right_ignore_json_order(self):
  w=load();n=w['graphs'][0]['nodes'][3];n['inputs']={'right':n['inputs']['right'],'left':n['inputs']['left']};self.assertEqual(run(w)['result']['value'],'3')
 def test_exact_arithmetic_and_signed_values(self):
  for op,left,right,expected,approx in [('add','-10','3','-7',False),('multiply','-2','3','-6',False),('divide','2','4','0.5',False),('divide','2','3','0.6666666666666666666666666666666667',True)]:
   value,loss=a.calculate(op,Decimal(left),Decimal(right),34 if op=='divide' else None,'half-even' if op=='divide' else None);self.assertEqual(value,Decimal(expected));self.assertEqual(loss,approx)
 def test_context_is_fixed_and_restored(self):
  with localcontext() as ctx:
   ctx.prec=3;ctx.rounding=ROUND_DOWN;v,approx=a.calculate('divide',Decimal(2),Decimal(3),34,'half-even');self.assertEqual(str(v),'0.6666666666666666666666666666666667');self.assertTrue(approx);self.assertEqual(ctx.prec,3);self.assertEqual(ctx.rounding,ROUND_DOWN)
 def test_supported_unit_rules(self):
  u=lambda code:{'status':'known','code':code}
  for op,left,right,out in [('add','kPa','kPa','kPa'),('add','rpm','rpm','rpm'),('multiply','1','bar','bar'),('multiply','bar','1','bar'),('multiply','1','1','1'),('divide','bar','1','bar'),('divide','bar','bar','1'),('divide','N.m','N.m','1'),('divide','1','1','1')]:self.assertEqual(a.unit_for(op,u(left),u(right)),u(out))
 def test_unsupported_unit_rules(self):
  u=lambda code:{'status':'known','code':code}
  for op,left,right in [('add','kPa','bar'),('multiply','kPa','kPa'),('divide','1','bar'),('divide','Pa','kPa'),('add','Cel','Cel'),('multiply','K','1'),('divide','K','K')]:self.assertRaises(ValueError,a.unit_for,op,u(left),u(right))
  for unit in [{'status':'unknown'},{'status':'not-applicable'}]:self.assertRaises(ValueError,a.unit_for,'multiply',u('1'),unit)
 def test_policy_refuses_precision_or_rounding_changes(self):
  for precision,rounding in [(33,'half-even'),(35,'half-even'),(34,'exact'),(None,None)]:self.assertRaises(ValueError,a.calculate,'divide',Decimal(1),Decimal(3),precision,rounding)
 def test_numeric_limit_does_not_silently_round_addition(self):
  self.assertRaisesRegex(ValueError,'value.numeric-limit',a.calculate,'add',Decimal('1e5000'),Decimal(1))
 def test_non_numeric_nonfinite_and_unknown_op_refused(self):
  for value in [True,1,Decimal('NaN'),Decimal('Infinity')]:self.assertRaises(ValueError,a.calculate,'add',value,Decimal(1))
  self.assertRaises(ValueError,a.calculate,'eval',Decimal(1),Decimal(1))
 def test_missing_input_is_bad(self):
  v=run(load(),samples={});self.assertIsNone(v['result']);self.assertIn('sample.missing',codes(v))
 def test_type_and_output_unit_static_and_preview(self):
  for kind in ['type','unit']:
   w=load()
   if kind=='type':next(s for s in w['sources'] if s['definition']['id']=='arithmetic-ab-gain')['definition']['rawRepresentation']['valueType']='Boolean'
   else:w['graphs'][0]['nodes'][3]['unit']={'status':'known','code':'kPa'}
   rule='graph.input-type' if kind=='type' else 'graph.output-unit';self.assertIn(rule,{e['ruleCode'] for e in server.findings_for(w)});samples=load('samples');samples['arithmetic-ab-gain']={'typedValue':True} if kind=='type' else samples['arithmetic-ab-gain'];self.assertIn(rule,codes(run(w,member='scaled' if kind=='type' else 'ratio',samples=samples)))
 def test_absolute_temperature_and_unknown_unit_static(self):
  for unit in [{'status':'known','code':'Cel'},{'status':'known','code':'K'},{'status':'unknown'}]:
   w=load();next(s for s in w['sources'] if s['definition']['id']=='structure-ab-actual')['definition']['unit']=unit;self.assertIn('graph.input-unit',{e['ruleCode'] for e in server.findings_for(w)});self.assertIn('graph.input-unit',codes(run(w)))
 def test_no_implicit_pressure_conversion_or_dimension_product(self):
  for change in ['conversion','product']:
   w=load()
   if change=='conversion':next(s for s in w['sources'] if s['definition']['id']=='structure-ab-target')['definition']['unit']={'status':'known','code':'bar'}
   else:w['graphs'][0]['nodes'][1]['inputs']['right']=copy.deepcopy(w['graphs'][0]['nodes'][0]['inputs']['right'])
   self.assertIn('graph.input-unit',{e['ruleCode'] for e in server.findings_for(w)})
 def test_legacy_graph_versions_refuse_new_nodes(self):
  for version in ['2.0.0','2.2.0','2.5.0','2.11.0','2.13.0']:
   w=load();w['graphs'][0]['schemaVersion']=version;self.assertTrue(p3.schema_errors('value-graph',w['graphs'][0]));self.assertIn('arithmetic.schema-version',codes(run(w)))
 def test_schema_ports_policy_and_arbitrary_text_refused(self):
  for mutation in [lambda n:n.update(precision=35),lambda n:n.update(rounding='floor'),lambda n:n.update(expression='__import__("os")'),lambda n:n['inputs'].update(other=n['inputs']['left'])]:
   g=copy.deepcopy(load()['graphs'][0]);mutation(g['nodes'][2]);self.assertTrue(p3.schema_errors('value-graph',g))
 def test_cycle_and_evidence_refused(self):
  for kind,rule in [('cycle','graph.cycle'),('evidence','graph.evidence-incomplete')]:
   w=load();n=w['graphs'][0]['nodes'][0]
   if kind=='cycle':n['inputs']['left']={'kind':'node','nodeId':'quotient'}
   else:n['evidenceRefs']=n['evidenceRefs'][:1]
   self.assertIn(rule,{e['ruleCode'] for e in server.findings_for(w)})
 def test_lazy_selector_does_not_execute_divide_zero_candidate(self):
  w=load();g=w['graphs'][0];gain={'kind':'source','sourceRef':{'id':'arithmetic-ab-gain','version':'1.0.0'}};g['nodes'].append({'nodeId':'selected','op':'bounded-selector','inputs':{'index':gain,'candidate0':{'kind':'node','nodeId':'sum'},'candidate1':{'kind':'node','nodeId':'quotient'}},'outOfRange':'reject','valueType':'Decimal','unit':{'status':'known','code':'kPa'},'evidenceRefs':copy.deepcopy(g['nodes'][1]['evidenceRefs'])});binding(w,'ab','quotient')['valueRef']['nodeId']='selected';server.check_state(w);s=load('samples');s['arithmetic-ab-gain']={'typedValue':'0'};v=run(w,member='quotient',samples=s);self.assertEqual(v['result']['value'],'200');self.assertNotIn('value.divide-zero',codes(v));self.assertFalse(any(t['stage']=='graph:divide' for t in v['trace']))
 def test_temporal_bad_stale_skew_blocks_arithmetic(self):
  w=load();m=w['mappings'][0];m['schemaVersion']='2.3.0';binding(w,'ab','ratio')['temporalPolicy']=server.contracts.load(R/'fixtures/p3d/workspace.json')['mappings'][0]['mappings'][0]['temporalPolicy'];server.check_state(w)
  raw=load('samples');s={id:{'value':raw[id],'quality':'good','sourceTimestamp':'2026-10-17T09:59:59.500Z','serverTimestamp':'2026-10-17T10:00:00Z','sequence':None} for id in ['structure-ab-actual','structure-ab-target']};ev={'at':'2026-10-17T10:00:00Z','triggerSequence':None};self.assertEqual(run(w,samples=s,evaluation=ev)['result']['value'],'3')
  for kind,code in [('bad','quality.bad-input'),('stale','time.stale-input'),('skew','time.skew-exceeded')]:
   changed=copy.deepcopy(s)
   if kind=='bad':changed['structure-ab-actual']['quality']='bad'
   else:changed['structure-ab-target']['sourceTimestamp']='2026-10-17T09:59:58Z' if kind=='stale' else '2026-10-17T09:59:59.800Z'
   v=run(w,samples=changed,evaluation=ev);self.assertIsNone(v['result']);self.assertIn(code,codes(v));self.assertFalse(any(t['stage']=='graph:divide' for t in v['trace']))
 def test_preview_readonly_and_units_trace(self):
  w=load();before=copy.deepcopy(w);v=run(w,member='quotient');self.assertEqual(w,before);self.assertFalse(v['persisted']);self.assertEqual(v['requiredSources'],['arithmetic-ab-gain','structure-ab-actual','structure-ab-target']);self.assertEqual([t['stage'] for t in v['trace'] if t['stage'].startswith('graph:')],['graph:add','graph:multiply','graph:divide'])
 def test_old_contracts_fixtures_and_evaluation_contract_preserved(self):
  old=server.contracts.load(R/'docs/verification/p7eval-validation.json')
  for name,h in old['sha256'].items():
   if name.startswith(('contracts/','fixtures/','evaluation-contracts/')):self.assertEqual(server.contracts.hashed(R/name),h,name)
class Storage(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.store=server.Store(Path(self.tmp.name)/'editor.sqlite3');self.store.migrate(0,{});self.store.save(1,server.contracts.load(R/'fixtures/p3cb/workspace.json'));self.old=self.store.read()
 def tearDown(self):self.tmp.cleanup()
 def test_existing_rows_open_unchanged(self):self.assertEqual(server.Store(self.store.path).read(),self.old)
 def test_new_graph_roundtrip_and_reopen(self):
  self.store.save(2,load());self.assertEqual(self.store.read()['workspace'],load());self.assertEqual(server.Store(self.store.path).read(),self.store.read())
 def test_invalid_graph_save_atomic(self):
  w=load();w['graphs'][0]['nodes'][2]['precision']=35;self.assertRaises(server.Invalid,self.store.save,2,w);self.assertEqual(self.store.read(),self.old)
 def test_stale_revision_preserves_old(self):self.assertRaises(server.Conflict,self.store.save,1,load());self.assertEqual(self.store.read(),self.old)
 def test_selected_scope_publication_closure(self):
  self.store.save(2,load());r=pub.export(self.store,{'revision':3,'id':'arithmetic-submit','streamId':'mixed-line','proposedBy':'proposer','mappingSetIds':['arithmetic-mapping-ab'],'includeWrites':False},server.Conflict,server.build_package,pub.Adapter());self.assertEqual(r['preflightFindings'],[]);p=server.contracts.load(Path(r['path'])/'proposal.json');self.assertEqual(sum(e['kind']=='source-definition' for e in p['files']),3);self.assertEqual(sum(e['kind']=='value-graph' for e in p['files']),1)
if __name__=='__main__':unittest.main(verbosity=2)
