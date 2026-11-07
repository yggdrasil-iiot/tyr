"""2.27 attribution and impact rules: byte-identical contract copies, the typed String source and the PLC form, authored
binding profiles, every attribution.* refusal, publication closure, receiver parity per refusal code, Bifrost approval."""
import sys,copy,json,shutil,subprocess,tempfile,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'backend'),str(R/'scripts')]
import server,publication
FIX=R/'fixtures/attribution-rule'
BUNDLE=FIX/'bundle'
PLC_BUNDLE=FIX/'plc-stamped-bundle'
JAR=R.parent/'bifrost/gates/target/bifrost-gates.jar'
SETS=('station1-mapping','station2-mapping','nutrunner1-mapping','nutrunner2-mapping')
def load(p):return server.contracts.load(R/p)
def w():return load('fixtures/attribution-rule/workspace.json')
def plc():return load('fixtures/attribution-rule/plc-stamped-workspace.json')
def ruled(f,state=None):
 state=w() if state is None else state;f(state['attributionRules'][0]);return state
def profiled(f,section='occupancyBindings',state=None):
 state=w() if state is None else state;f(state[section][0]);return state
def package(state,folder):
 server.build_package(state,folder);return load(folder/'proposal.json')
def publish(state,folder,sets=SETS,stream='line2',id='attribution-fixture'):
 _,_,findings=publication.build(state,folder,id,stream,'proposer',None,list(sets),False,server.build_package)
 return load(folder/'proposal.json'),findings
def tree(root):return {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
def repinned(root):
 """Re-pin a mutated package: every evidence file digest, every proposal entry digest, the submission's proposal digest."""
 p=load(root/'proposal.json')
 for e in p['files']:
  if e['kind']=='evidence-artifact':
   a=load(root/e['path']);a['file']['sha256']=server.contracts.hashed(root/a['file']['path']);server.contracts.save(root/e['path'],a)
  e['sha256']=server.contracts.hashed(root/e['path'])
 server.contracts.save(root/'proposal.json',p)
 if (root/'submission.json').is_file():
  s=load(root/'submission.json');s['proposalSha256']=server.contracts.hashed(root/'proposal.json');server.contracts.save(root/'submission.json',s)
 return root
class Contract(unittest.TestCase):
 """Contract 2.27.0 is Bifrost's, byte for byte (test_p6 proves the bytes); here: what it adds to 2.26.0."""
 def test_2_27_schemas_extend_2_26_only_where_intended(self):
  old,new=((R/'contracts'/v/'mapping-proposal.schema.json').read_text(encoding='utf-8') for v in ('2.26.0','2.27.0'))
  self.assertEqual(old.replace('2.26.0','2.27.0'),new)
  old,new=(load('contracts/'+v+'/common.schema.json')['$defs'] for v in ('2.26.0','2.27.0'))
  self.assertEqual(new['fileEntry']['properties']['kind']['enum'],old['fileEntry']['properties']['kind']['enum']+['attribution-rule','impact-rule'])
  typed=lambda d:next(b for b in d['rawRepresentation']['oneOf'] if b['properties']['mode']['const']=='typed')['properties']['valueType']['anyOf'][0]['enum']
  self.assertEqual(typed(new),typed(old)+['String'])
  self.assertEqual({k for k in old if old[k]!=new[k]},{'fileEntry','rawRepresentation'})
  for kind in ('attribution-rule','impact-rule'):
   s=load('contracts/2.27.0/'+kind+'.schema.json');self.assertEqual(s['properties']['kind']['const'],kind);self.assertEqual(s['properties']['schemaVersion']['const'],'2.27.0');self.assertFalse(s['additionalProperties'])
 def test_2_27_source_definition_is_the_2_7_plc_source(self):
  old=next(b for b in load('contracts/2.7.0/source-definition.schema.json')['oneOf'] if b['properties']['sourceKind']['const']=='plc');new=load('contracts/2.27.0/source-definition.schema.json')
  self.assertEqual(new['properties']['schemaVersion'],{'const':'2.27.0'});self.assertEqual(set(new['properties']),set(old['properties']));self.assertEqual(new['required'],old['required'])
  base=load('fixtures/command-binding/bundle/sources/0.json')   # a 2.7.0 plc OPC UA source
  string=dict(base,schemaVersion='2.27.0',rawRepresentation={'mode':'typed','valueType':'String'})
  self.assertEqual(server.v2.p3.schema_errors('source-definition',string),[])
  self.assertNotEqual(server.v2.p3.schema_errors('source-definition',dict(base,rawRepresentation={'mode':'typed','valueType':'String'})),[])   # 2.7.0 still cannot declare String
  self.assertEqual(server.contracts.validate_schema('source-definition',string),[])
def string_source(state,id='station1-unit',equipment='station1',connection='sim-opcua-station1',node='Line2/Station1.UnitId',value_type='String',note=None):
 """A typed OPC UA source record exactly as the PLC form writes it (app.js draftSource + mixed.js plc branch, Task 4): 2.27.0 for a
 String raw type, 2.7.0 for every other raw type; capturedAt fixed."""
 d={'kind':'source-definition','schemaVersion':'2.27.0' if value_type=='String' else '2.7.0','id':id,'version':'1.0.0','equipmentInstanceId':equipment,'connectionProfileRef':connection,'accessProfileRef':'s7-1500-opcua-v1','status':'ready',
    'rawAddressText':'nsu=urn:bifrost:opcua:sim;s='+node,'addressRadix':None,'access':{'kind':'opcua-node','namespaceUri':'urn:bifrost:opcua:sim','identifierType':'string','identifier':node},
    'rawRepresentation':{'mode':'typed','valueType':value_type},'inputStage':'already-engineered','unit':{'status':'not-applicable'},'evidenceRefs':[{'artifactId':'manual-'+id,'locator':{'kind':'text-line','line':1}}],'viewOf':None,'sourceKind':'plc','accessMode':'read'}
 state['sources'].append({'definition':d,'label':id,'note':note or (node+', '+value_type),'origin':'synthetic','capturedAt':'2026-11-07T00:00:00Z'});return state
class StringSource(unittest.TestCase):
 """Spec row 1: the 2.27.0 common schema adds String to typed sources; a 2.27.0 document travels only in a 2.27.0 proposal."""
 def base(self):
  state=load('fixtures/command-binding/workspace.json');del state['commandBindings'],state['readBindings'],state['serverCertificates'];return state
 def test_a_2_27_string_source_is_accepted_and_packaged_at_2_27(self):
  state=string_source(self.base(),'mixer1-unit','mixer1','sim-opcua','Line1/Mixer1.UnitId');server.check_state(state)
  self.assertEqual([f for f in server.findings_for(state) if f['ruleCode']!='mapping.incomplete-object'],[])
  with tempfile.TemporaryDirectory() as t:
   p=package(state,Path(t));self.assertEqual(p['schemaVersion'],'2.27.0')
   src=next(load(Path(t)/e['path']) for e in p['files'] if e['id']=='mixer1-unit');self.assertEqual((src['schemaVersion'],src['rawRepresentation']),('2.27.0',{'mode':'typed','valueType':'String'}))
 def test_a_2_7_source_cannot_declare_string(self):
  state=string_source(self.base(),'mixer1-unit','mixer1','sim-opcua','Line1/Mixer1.UnitId');state['sources'][-1]['definition']['schemaVersion']='2.7.0'
  self.assertRaisesRegex(ValueError,'source-definition',server.check_state,state)
 def test_a_2_27_source_needs_a_2_27_proposal(self):
  state=string_source(self.base(),'mixer1-unit','mixer1','sim-opcua','Line1/Mixer1.UnitId')
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);package(state,root);p=load(root/'proposal.json');p['schemaVersion']='2.26.0';server.contracts.save(root/'proposal.json',p)
   self.assertEqual([e['ruleCode'] for e in server.v2.p3.validate_package(root)[0]],['rule.envelope'])
 def test_a_2_26_command_binding_rides_in_a_2_27_proposal(self):
  state=string_source(load('fixtures/command-binding/workspace.json'),'mixer1-unit','mixer1','sim-opcua','Line1/Mixer1.UnitId');server.check_state(state)
  with tempfile.TemporaryDirectory() as t:
   p=package(state,Path(t));self.assertEqual(p['schemaVersion'],'2.27.0');self.assertEqual(server.v2.p3.validate_package(Path(t))[0],[])
 def test_legacy_workspace_refuses_a_2_27_source(self):
  state=load('fixtures/realistic/workspace.json');self.assertNotIn('workspaceVersion',state)   # the committed 1.x workspace with an OPC UA connection (logical-ua)
  string_source(state,'line-a-unit','line-a-motor-ua','logical-ua','LineA/Motor.UnitId')
  self.assertRaisesRegex(ValueError,'2.0 authoring workspace',server.check_state,state)
if __name__=='__main__':unittest.main()
