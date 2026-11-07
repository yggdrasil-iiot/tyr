"""2.27 impact rule: the incident binding profile, every impact.* refusal, closure with the attribution rule."""
import sys,copy,json,tempfile,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'backend'),str(R/'scripts')]
import server,publication,attribution_rule as ar,impact_rule as ir
from test_attribution_rule import load,w,package,publish,repinned,SETS
PROFILE={'profileVersion':'0.1.0','topic':'mfg.incidents','format':{'schemaId':'urn:forseti:schema:incident:1.0.0','schemaSha256':'0'*63+'2'},'kinds':['tool-check-failed','gauge-drift'],'equipmentRefBasis':'isa95-path'}
def raw(profile):return (json.dumps(profile,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def changed(f):
 p=copy.deepcopy(PROFILE);f(p);return raw(p)
def impacted(f,state=None):
 state=w() if state is None else state;f(state['impactRules'][0]);return state
class IncidentProfile(unittest.TestCase):
 """Spec 217-224 read with Tyr's own parser at the strictness of Bifrost's IncidentBindingProfile."""
 def test_accepted(self):self.assertEqual(ir.incident_profile(raw(PROFILE))['kinds'],['tool-check-failed','gauge-drift'])
 def refused(self,raw_bytes,code='impact.binding-profile'):self.assertRaisesRegex(ValueError,code,ir.incident_profile,raw_bytes)
 def test_field_set(self):
  self.refused(changed(lambda p:p.update(note='x')));self.refused(changed(lambda p:p.pop('kinds')));self.refused(b'not json');self.refused(b'null');self.refused(changed(lambda p:p['format'].update(extra=1)))
 def test_constants_and_empty_values(self):
  self.refused(changed(lambda p:p.update(profileVersion='0.2.0')));self.refused(changed(lambda p:p.update(topic='')));self.refused(changed(lambda p:p.update(equipmentRefBasis='sparkplug-device')))
  self.refused(changed(lambda p:p['format'].update(schemaId='urn:forseti:schema:occupancy:1.0.0')))
 def test_digest_form(self):
  self.refused(changed(lambda p:p['format'].update(schemaSha256='0'*63)));self.refused(changed(lambda p:p['format'].update(schemaSha256='G'*64)));self.refused(changed(lambda p:p['format'].update(schemaSha256=2)))
 def test_kinds(self):
  self.refused(changed(lambda p:p.update(kinds=[])));self.refused(changed(lambda p:p.update(kinds=['gauge-drift','gauge-drift'])));self.refused(changed(lambda p:p.update(kinds=['gauge-drift',''])));self.refused(changed(lambda p:p.update(kinds='gauge-drift')))
  ir.incident_profile(changed(lambda p:p.update(kinds=['any-name-the-job-may-refuse-later'])))   # spec 224: Bifrost checks distinct non-empty names only
 def test_other_code_is_the_callers(self):self.assertRaisesRegex(ValueError,'incident-binding.profile',ir.incident_profile,b'{}','incident-binding.profile')
 def test_duplicate_json_keys_are_refused(self):   # Bifrost's MappingJson reads with STRICT_DUPLICATE_DETECTION
  self.refused(raw(PROFILE).replace(b'"topic": "mfg.incidents"',b'"topic": "ignored", "topic": "mfg.incidents"'))
 def test_utf8_bom_is_accepted_as_bifrost_accepts_it(self):self.assertEqual(ir.incident_profile(b'\xef\xbb\xbf'+raw(PROFILE))['topic'],'mfg.incidents')
 def test_deep_nesting_is_refused_not_a_crash(self):self.refused(b'['*10000+b'0'+b']'*10000);self.refused(b'['*1500+b'0'+b']'*1500)
if __name__=='__main__':unittest.main()
