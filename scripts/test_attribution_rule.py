"""2.27 attribution and impact rules: byte-identical contract copies, the typed String source and the PLC form, authored
binding profiles, every attribution.* refusal, publication closure, receiver parity per refusal code, Bifrost approval."""
import sys,copy,json,shutil,subprocess,tempfile,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'backend'),str(R/'scripts')]
import server,publication,binding_profiles as bp,attribution_rule as ar,impact_rule as ir
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
import contextlib
@contextlib.contextmanager
def urllib_served(case):
 """The frontend as the server serves it (test_http_routes precedent): yields get(path) -> bytes."""
 import threading,urllib.request
 tmp=tempfile.TemporaryDirectory();store=server.Store(Path(tmp.name)/'db.sqlite3');store.migrate(0,{})
 http=server.make_server(store,0);threading.Thread(target=http.serve_forever,daemon=True).start()
 try:
  base='http://127.0.0.1:'+str(http.server_address[1])
  def get(path):
   with urllib.request.urlopen(base+path) as r:return r.read()
  yield get
 finally:http.shutdown();http.server_close();tmp.cleanup()
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
 def test_plc_source_form_offers_string_for_typed_access_and_writes_2_27(self):
  app=(R/'frontend/app.js').read_text(encoding='utf-8');mixed=(R/'frontend/mixed.js').read_text(encoding='utf-8')
  line=next(l for l in app.splitlines() if 'select("rawType"' in l)
  self.assertIn('bytes?["Int16","UInt16","Int32","UInt32","Int64","Float32","Float64","Boolean"]:["Int16","UInt16","Int32","UInt32","Int64","Float32","Float64","Boolean","String"]',line)
  plc=next(l for l in mixed.splitlines() if "if(kind==='plc'){const r=draftBeforeMixed()" in l)
  self.assertIn("schemaVersion:r.definition.rawRepresentation?.valueType==='String'?'2.27.0':'2.7.0'",plc)
  with urllib_served(self) as get:self.assertIn(b'"String"]',get('/app.js'));self.assertIn(b"'2.27.0':'2.7.0'",get('/mixed.js'))
PROFILE={'profileVersion':'0.1.0','topic':'mfg.occupancy','format':{'schemaId':'urn:forseti:schema:occupancy:1.0.0','schemaSha256':'0'*63+'1'},
         'identity':{'scheme':'mes-unit-id','pattern':'[A-Z0-9]{17}'},'enter':{'bizStep':'urn:epcglobal:cbv:bizstep:arriving'},'leave':{'bizStep':'urn:epcglobal:cbv:bizstep:departing'},
         'correction':{'errorDeclaration':'reissue-same-event-id','reasons':['urn:epcglobal:cbv:er:did_not_occur','urn:epcglobal:cbv:er:incorrect_data']},'timestampBasis':'eventTime','sources':['mes-line2']}
def raw(profile):return (json.dumps(profile,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def changed(f):
 p=copy.deepcopy(PROFILE);f(p);return raw(p)
class OccupancyProfile(unittest.TestCase):
 """Spec 206-215, 224-226 read with Tyr's own parser at the strictness of Bifrost's OccupancyBindingProfile."""
 def test_accepted(self):self.assertEqual(ar.occupancy_profile(raw(PROFILE))['topic'],'mfg.occupancy')
 def refused(self,raw_bytes,code='attribution.binding-profile'):self.assertRaisesRegex(ValueError,code,ar.occupancy_profile,raw_bytes)
 def test_field_set(self):
  self.refused(changed(lambda p:p.update(note='x')));self.refused(changed(lambda p:p.pop('sources')));self.refused(b'not json');self.refused(b'[]')
  self.refused(changed(lambda p:p['format'].update(extra=1)));self.refused(changed(lambda p:p['identity'].pop('pattern')));self.refused(changed(lambda p:p['enter'].update(disposition='x')))
 def test_constants_and_empty_values(self):
  self.refused(changed(lambda p:p.update(profileVersion='0.2.0')));self.refused(changed(lambda p:p.update(timestampBasis='recordTime')));self.refused(changed(lambda p:p.update(topic='')))
  self.refused(changed(lambda p:p['format'].update(schemaId='urn:forseti:schema:occupancy:1.1.0')));self.refused(changed(lambda p:p['identity'].update(scheme='gs1-sgtin')))
  self.refused(changed(lambda p:p['enter'].update(bizStep='')));self.refused(changed(lambda p:p['correction'].update(errorDeclaration='new-event-id')))
 def test_digest_form(self):
  self.refused(changed(lambda p:p['format'].update(schemaSha256='0'*64+'0')));self.refused(changed(lambda p:p['format'].update(schemaSha256='A'*64)));self.refused(changed(lambda p:p['format'].update(schemaSha256=1)))
 def test_reasons_and_sources(self):
  self.refused(changed(lambda p:p['correction'].update(reasons=[])));self.refused(changed(lambda p:p['correction'].update(reasons=['urn:epcglobal:cbv:er:did_not_occur']*2)))
  self.refused(changed(lambda p:p['correction'].update(reasons=['urn:epcglobal:cbv:er:other'])));ar.occupancy_profile(changed(lambda p:p['correction'].update(reasons=['urn:epcglobal:cbv:er:incorrect_data'])))
  self.refused(changed(lambda p:p.update(sources=[])));self.refused(changed(lambda p:p.update(sources=['a','a'])));self.refused(changed(lambda p:p.update(sources=['a',''])));self.refused(changed(lambda p:p.update(sources='mes')))
 def test_other_code_is_the_callers(self):self.assertRaisesRegex(ValueError,'occupancy-binding.profile',ar.occupancy_profile,b'{}','occupancy-binding.profile')
 def test_duplicate_json_keys_are_refused(self):   # Bifrost's MappingJson reads with STRICT_DUPLICATE_DETECTION; Python's json would keep the last value
  self.refused(raw(PROFILE).replace(b'"topic": "mfg.occupancy"',b'"topic": "ignored", "topic": "mfg.occupancy"'))
 def test_utf8_bom_is_accepted_as_bifrost_accepts_it(self):self.assertEqual(ar.occupancy_profile(b'\xef\xbb\xbf'+raw(PROFILE))['topic'],'mfg.occupancy')   # Jackson's byte reader skips it; json.loads on bytes detects utf-8-sig
 def test_deep_nesting_is_refused_not_a_crash(self):   # Jackson's 1,000-level limit makes it a reader exception in Bifrost; Python raises RecursionError, mapped to the code
  self.refused(b'['*10000+b'0'+b']'*10000);self.refused(b'['*1500+b'0'+b']'*1500)
 def test_enter_equal_to_leave_is_accepted_as_bifrost_accepts_it(self):ar.occupancy_profile(changed(lambda p:p['leave'].update(bizStep=p['enter']['bizStep'])))   # Open point 1
class Pattern(unittest.TestCase):
 """Spec 225 plus Bifrost's extra limits (forseti spec PR of Task 1): the syntax common to Java and ECMA-262, nothing else."""
 def test_accepted(self):
  for p in ('[A-Z0-9]{17}','VIN-[0-9]{6}','(?:A|B)[0-9]+','a.c','x*y+z?','[^-]{1,3}','\\-\\.\\+','[a\\]b]','(?:(?:a))','a{2}','a{2,}','[0-9A-Fa-f]{32}','(?:a+)+'):self.assertTrue(ar.pattern_accepted(p),p)
 def test_refused(self):
  for p in ('','^A$','(A)','(?<n>A)','(?=A)','(?!A)','\\d+','\\w','\\p{Lu}','[[:alpha:]]','A*?','A++','A{','A{2,1}','A{,3}','\\1','(?i)A','[a&&[b]]','[]','[a','a)','(?:a','\\','\\A','a{2}{3}','a**','[z-a]'):self.assertFalse(ar.pattern_accepted(p),p)
 def test_surrogates_and_supplementary_characters_are_refused(self):
  self.assertFalse(ar.pattern_accepted('A\U0001F600'));self.assertFalse(ar.pattern_accepted('A\ud83d'))   # Java reads a pair as one code point, ECMA-262 as two
 def test_group_depth_is_bounded(self):
  self.assertTrue(ar.pattern_accepted('(?:'*ar.MAX_DEPTH+'a'+')'*ar.MAX_DEPTH));self.assertFalse(ar.pattern_accepted('(?:'*(ar.MAX_DEPTH+1)+'a'+')'*(ar.MAX_DEPTH+1)))
 def test_quantifier_bounds_follow_java(self):
  for p in ('a{2147483647}','a{0,2147483647}','a{2147483647,}'):self.assertTrue(ar.pattern_accepted(p),p)
  # Java Pattern.compile: "Illegal repetition range" above Integer.MAX_VALUE; Python's re alone would accept the first and fourth and raise OverflowError on the others
  for p in ('a{2147483648}','a{4294967296}','a{99999999999999999999}','a{1,2147483648}','a{2147483648,}','a{1,99999999999999999999}','a{99999999999999999999,1}'):self.assertFalse(ar.pattern_accepted(p),p)
 def test_leading_zeros_are_javas_value(self):
  # Bifrost does not parse {m}; Pattern.compile accumulates leading zeros, so 4,500 zeros before a 1 are a valid repetition of 1;
  # Python's int() and re would refuse more than 4,300 digits, so Tyr strips the zeros first (no new length cap: Open point 4)
  for p in ('a{0001}','a{00,0002}','a{'+'0'*4500+'1}','a{'+'0'*4500+'1,'+'0'*4500+'2}'):self.assertTrue(ar.pattern_accepted(p),p[:24])
  for p in ('a{'+'0'*4500+'1,0}','a{'+'9'*4500+'}'):self.assertFalse(ar.pattern_accepted(p),p[:24])   # inverted range; a bound no engine holds
 def test_profile_with_a_refused_pattern(self):self.assertRaisesRegex(ValueError,'attribution.binding-profile',ar.occupancy_profile,changed(lambda p:p['identity'].update(pattern='^[A-Z]+$')))
def record(profile,id='line2',scope=('mixer1','mixer2'),version='1.0.0'):
 return {'id':id,'version':version,'label':'Line 2 binding','origin':'synthetic','capturedAt':'2026-11-07T00:00:00Z','reviewer':'fixture-reviewer','product':None,'scope':list(scope),'profile':copy.deepcopy(profile)}
class BindingProfiles(unittest.TestCase):
 """Authored profiles: a workspace record whose profile object Tyr serializes; the artifact wrapper pins those bytes."""
 def base(self):
  state=load('fixtures/command-binding/workspace.json');del state['commandBindings'],state['readBindings'],state['serverCertificates']
  state['occupancyBindings']=[record(PROFILE)];state['incidentBindings']=[record({'profileVersion':'0.1.0','topic':'mfg.incidents','format':{'schemaId':'urn:forseti:schema:incident:1.0.0','schemaSha256':'0'*63+'2'},'kinds':['tool-check-failed'],'equipmentRefBasis':'isa95-path'})];return state
 def refused(self,state,code):self.assertRaisesRegex(ValueError,code,server.check_state,state)
 def test_packaged_as_evidence_artifacts_with_the_spec_prefix_and_media_type(self):
  state=self.base();server.check_state(state)
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);p=package(state,root)
   for prefix,media,data in ((ar.PREFIX,ar.MEDIA,'data/occupancy-binding-0.json'),(ir.PREFIX,ir.MEDIA,'data/incident-binding-0.json')):
    art=next(load(root/e['path']) for e in p['files'] if e['id']==prefix+'line2')
    self.assertEqual((art['schemaVersion'],art['file']['path'],art['file']['mediaType'],art['scope'],art['origin']),('1.1.0',data,media,['mixer1','mixer2'],'synthetic'))
    self.assertEqual(art['file']['sha256'],server.contracts.hashed(root/data))
   self.assertEqual((root/'data/occupancy-binding-0.json').read_bytes(),raw(PROFILE))   # vc.save bytes: indent 2, LF, final newline
   self.assertEqual(p['schemaVersion'],'2.23.0')   # a profile alone is an evidence artifact and raises no envelope: base() dropped the links, so the hierarchy's 2.23.0 (workspace_v2.build lines 63-68) stands
 def test_record_refusals(self):
  self.refused(profiled(lambda r:r.update(note='x'),state=self.base()),'occupancy-binding.schema')
  self.refused(profiled(lambda r:r.update(scope=[]),state=self.base()),'occupancy-binding.schema')
  self.refused(profiled(lambda r:r.update(scope=['mixer9']),state=self.base()),'occupancy-binding.scope')
  state=self.base();state['occupancyBindings'].append(record(PROFILE));self.refused(state,'occupancy-binding.duplicate')
  state=self.base();state['incidentBindings'].append(record(state['incidentBindings'][0]['profile']));self.refused(state,'incident-binding.duplicate')
  self.refused(profiled(lambda r:r['profile'].update(timestampBasis='recordTime'),state=self.base()),'attribution.binding-profile')
  self.refused(profiled(lambda r:r['profile']['identity'].update(pattern='^A$'),state=self.base()),'attribution.binding-profile')
  self.refused(profiled(lambda r:r['profile'].update(kinds=[]),'incidentBindings',self.base()),'impact.binding-profile')
  state=self.base();state['occupancyBindings']='x';self.refused(state,'occupancy-binding.limit')
 def test_changed_profile_needs_a_new_version(self):
  before=self.base();after=profiled(lambda r:r['profile'].update(topic='mfg.occupancy.v2'),state=self.base())
  self.assertRaisesRegex(ValueError,'occupancy-binding.version-required',bp.transition,before,after)
  after['occupancyBindings'][0]['version']='1.1.0';bp.transition(before,after)
  after=profiled(lambda r:r.update(scope=['mixer1']),'incidentBindings',self.base());self.assertRaisesRegex(ValueError,'incident-binding.version-required',bp.transition,before,after)
 def test_without_profiles_unchanged(self):
  state=self.base();del state['occupancyBindings'],state['incidentBindings'];server.check_state(state)
  with tempfile.TemporaryDirectory() as t:self.assertFalse(any(e['id'].startswith((ar.PREFIX,ir.PREFIX)) for e in package(state,Path(t))['files']))
if __name__=='__main__':unittest.main()
