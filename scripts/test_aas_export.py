"""AAS v3.1 ConceptDescription export: SDK-verified, round-trips, refuses what it cannot project faithfully."""
import copy,hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'backend'),str(R/'scripts')]
from aas_core3_1 import jsonization,verification
import aas_export as ax,validate_contracts as vc

SCALAR=R/'fixtures/a07/wire/semantics/0.json'
NESTED=R/'fixtures/p3eb/nested-model.json'
def doc(path=NESTED):return copy.deepcopy(vc.load(path))
def write(d,folder):
    p=Path(folder)/'definition.json';p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8',newline='\n');return p
def cds(files):return {c['id']:c for c in json.loads(files[ax.ENVIRONMENT])['conceptDescriptions']}
def iec(cd):return cd['embeddedDataSpecifications'][0]['dataSpecificationContent']
def ext(cd):return {e['name']:e['value'] for e in cd['extensions']}

class Export(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
 def run_export(self,d,language='en'):return ax.export(write(d,self.tmp.name),language)
 def refused(self,d,code,language='en'):
  with self.assertRaises(ax.Refused) as e:self.run_export(d,language)
  self.assertTrue(str(e.exception).startswith(code),str(e.exception))

 def test_scalar_definition_is_one_concept_per_member_and_verifies(self):
  files=ax.export(SCALAR,'en');c=cds(files);d=doc(SCALAR)
  self.assertEqual(list(c),[m['semanticId'] for m in d['members']])
  env=jsonization.environment_from_jsonable(json.loads(files[ax.ENVIRONMENT]))
  self.assertEqual(list(verification.verify(env)),[])
  self.assertEqual(jsonization.to_jsonable(env),json.loads(files[ax.ENVIRONMENT]))
  word=c['urn:tyr:concept:a07.word']
  self.assertEqual(iec(word)['preferredName'],[{'language':'en','text':'word'}])
  self.assertEqual(iec(word)['definition'],[{'language':'en','text':'Synthetic status word'}])
  self.assertNotIn('dataType',iec(word));self.assertNotIn('unit',iec(word))
  self.assertEqual(ext(word),{'tyr:valueType':'Int32','tyr:unitStatus':'not-applicable','tyr:role':'status'})
  self.assertEqual(iec(c['urn:tyr:concept:a07.running'])['dataType'],'BOOLEAN')

 def test_structure_arrays_keep_members_shape_and_bounds(self):
  c=cds(ax.export(NESTED,'en'))
  self.assertEqual(list(c),['urn:fixture:racks','urn:fixture:slots','urn:fixture:value'])
  self.assertEqual(ext(c['urn:fixture:slots']),{'tyr:valueType':'StructureArray','tyr:members':'["urn:fixture:value"]','tyr:shape':'[2, 2]','tyr:lowerBounds':'[1, 3]'})
  self.assertNotIn('dataType',iec(c['urn:fixture:racks']))
  value=c['urn:fixture:value'];self.assertEqual((iec(value)['dataType'],iec(value)['unit']),('REAL_MEASURE','kPa'))

 def test_range_is_kept_as_decimal_extensions(self):
  d=doc();d['members'][0]['members'][0]['members'][0]['range']={'low':'-1.5','high':'250'}
  e={x['name']:x for x in cds(self.run_export(d))['urn:fixture:value']['extensions']}
  self.assertEqual([(e[k]['valueType'],e[k]['value']) for k in ('tyr:range.low','tyr:range.high')],[('xs:decimal','-1.5'),('xs:decimal','250')])

 def test_numeric_without_a_known_unit_gets_no_measure_type(self):
  for status in ('unknown','not-applicable'):
   with self.subTest(status=status):
    d=doc();d['members'][0]['members'][0]['members'][0]['unit']={'status':status}
    value=cds(self.run_export(d))['urn:fixture:value']
    self.assertNotIn('dataType',iec(value));self.assertNotIn('unit',iec(value));self.assertEqual(ext(value)['tyr:unitStatus'],status)

 def test_known_unit_integer_is_an_integer_measure(self):
  d=doc(SCALAR);d['members'][0]['unit']={'status':'known','code':'rpm'};d['members'][0]['role']='measurement'
  word=cds(self.run_export(d))['urn:tyr:concept:a07.word'];self.assertEqual((iec(word)['dataType'],iec(word)['unit']),('INTEGER_MEASURE','rpm'))

 def test_a_reused_identical_concept_is_written_once(self):
  d=doc(SCALAR);twin=copy.deepcopy(d['members'][0]);twin['memberId']='word-twin';d['members'].append(twin)
  self.assertEqual(len(cds(self.run_export(d))),5)

 def test_conflicting_definitions_of_one_concept_are_refused(self):
  for field,value in (('description','Another meaning'),('valueType','Double'),('role','measurement'),('unit',{'status':'unknown'})):
   with self.subTest(field=field):
    d=doc(SCALAR);twin=copy.deepcopy(d['members'][0]);twin['memberId']='word-twin';twin[field]=value;d['members'].append(twin)
    self.refused(d,'aas.semantic-conflict:urn:tyr:concept:a07.word')

 def test_language_is_stated_and_must_be_english(self):
  self.assertEqual(iec(cds(ax.export(SCALAR,'en-GB'))['urn:tyr:concept:a07.word'])['definition'][0]['language'],'en-GB')
  self.refused(doc(SCALAR),'aas.language-not-english','ko')
  self.refused(doc(SCALAR),'aas.language-not-english','de-DE')
  self.refused(doc(SCALAR),'aas.language-invalid','english please')

 def test_input_that_fails_its_contract_is_refused(self):
  d=doc();d['members'][0]['semanticId']='0173-1#02-AAO677#002';self.refused(d,'aas.input-schema')
  d=doc(SCALAR);del d['members'][0]['role'];self.refused(d,'aas.input-schema')
  d=doc(SCALAR);d['kind']='mapping-set';self.refused(d,'aas.input-kind')

 def test_sdk_verification_failures_are_refused(self):
  d=doc(SCALAR);d['members'][0]['name']='x'*256;self.refused(d,'aas.verify')

 def test_output_is_deterministic_and_the_statement_pins_both_ends(self):
  a=ax.export(NESTED,'en');b=ax.export(NESTED,'en');self.assertEqual(a,b)
  s=json.loads(a[ax.PROVENANCE])
  self.assertEqual((s['_type'],s['predicateType']),('https://in-toto.io/Statement/v1','https://slsa.dev/provenance/v1'))
  self.assertEqual(s['subject'],[{'name':ax.ENVIRONMENT,'digest':{'sha256':hashlib.sha256(a[ax.ENVIRONMENT].encode('utf-8')).hexdigest()}}])
  dep=s['predicate']['buildDefinition']['resolvedDependencies'][0]
  self.assertEqual(dep['digest']['sha256'],hashlib.sha256(NESTED.read_bytes()).hexdigest())
  self.assertEqual(dep['annotations'],{'kind':'semantic-definition','schemaVersion':'2.12.0','id':'nested','version':'1.0.0'})
  self.assertEqual(s['predicate']['runDetails']['builder']['version']['aas-core3.1'],'1.0.0')
  self.assertNotIn('approv',a[ax.PROVENANCE].lower())

class Cli(unittest.TestCase):
 def cli(self,*args):return subprocess.run([sys.executable,'-B',str(R/'scripts/aas_export.py'),*map(str,args)],capture_output=True,text=True,timeout=120)
 def test_writes_both_files(self):
  with tempfile.TemporaryDirectory() as t:
   p=self.cli(NESTED,'--language','en','--out',Path(t)/'out');self.assertEqual(p.returncode,0,p.stderr)
   self.assertEqual(sorted(f.name for f in (Path(t)/'out').iterdir()),[ax.ENVIRONMENT,ax.PROVENANCE])
   self.assertEqual((Path(t)/'out'/ax.ENVIRONMENT).read_bytes(),ax.export(NESTED,'en')[ax.ENVIRONMENT].encode('utf-8'))
 def test_a_refusal_writes_nothing(self):
  with tempfile.TemporaryDirectory() as t:
   p=self.cli(NESTED,'--language','ko','--out',Path(t)/'out')
   self.assertEqual((p.returncode,p.stderr.strip()),(3,'refused: aas.language-not-english'));self.assertFalse((Path(t)/'out').exists())
 def test_the_language_has_no_default(self):
  with tempfile.TemporaryDirectory() as t:self.assertEqual(self.cli(NESTED,'--out',Path(t)/'out').returncode,2)

if __name__=='__main__':unittest.main()
