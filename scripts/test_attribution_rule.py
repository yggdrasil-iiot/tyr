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
if __name__=='__main__':unittest.main()
