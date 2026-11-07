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
class ImpactRule(unittest.TestCase):
 """Spec 156-188 on the occupancy-join workspace."""
 def refused(self,state,code):self.assertRaisesRegex(ValueError,code,server.check_state,state)
 def test_accepted_with_its_attribution_rule(self):
  state=w();server.check_state(state);self.assertEqual(server.findings_for(state),[])
 def test_attribution_missing(self):self.refused(impacted(lambda r:r['attributionRuleRef'].update(version='9.9.9')),'impact.attribution-missing')
 def test_scope_must_be_in_the_hierarchy(self):self.refused(impacted(lambda r:r['incidentScope'].__setitem__(0,'synthetic-site:line2:station1:nutrunner9')),'impact.scope-containment')
 def test_scope_must_be_under_an_attribution_station(self):self.refused(impacted(lambda r:r['incidentScope'].__setitem__(0,'synthetic-site:line2')),'impact.scope-containment')
 def test_a_station_itself_is_in_scope(self):server.check_state(impacted(lambda r:r.update(incidentScope=['synthetic-site:line2:station1'])))
 def test_duplicate_or_empty_scope_is_a_schema_refusal(self):
  self.refused(impacted(lambda r:r['incidentScope'].append(r['incidentScope'][0])),'impact-rule: schema validation failed');self.refused(impacted(lambda r:r.update(incidentScope=[])),'impact-rule: schema validation failed')
 def test_binding_unresolved(self):
  self.refused(impacted(lambda r:r['incidentBindingRef'].update(version='9.9.9')),'impact.binding-unresolved')
  self.refused(impacted(lambda r:r['incidentBindingRef'].update(id='manual-nutrunner1-torque')),'impact.binding-unresolved')   # an artifact, but 1.0.0
 def test_binding_artifact_must_carry_the_prefix_and_media_type(self):self.refused(impacted(lambda r:r['incidentBindingRef'].update(id='occupancy-binding-line2')),'impact.binding-profile')
 def test_binding_profile_refused_on_the_package_alone(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);package(w(),root);(root/'data/incident-binding-0.json').write_bytes(b'{}\n');repinned(root)
   self.assertIn('impact.binding-profile',[x['ruleCode'] for x in server.v2.p3.validate_package(root)[0]])
 def test_retention_order(self):
  self.refused(impacted(lambda r:r['retention'].update(workRecordsMs=3600000)),'impact.retention-order')
  server.check_state(impacted(lambda r:r['retention'].update(workRecordsMs=86400000)))   # equal to the horizon is accepted
 def test_retention_above_90_days_is_a_schema_refusal(self):self.refused(impacted(lambda r:r['retention'].update(workRecordsMs=7776000001)),'impact-rule: schema validation failed')
 def test_duplicate_id(self):
  state=w();state['impactRules'].append(copy.deepcopy(state['impactRules'][0]));self.refused(state,'impact-rule: duplicate id')
 def test_older_version_is_not_written(self):self.refused(impacted(lambda r:r.update(schemaVersion='2.26.0')),'impact-rule: schema validation failed')
 def test_package_without_the_attribution_rule(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);p=package(w(),root);p['files']=[e for e in p['files'] if e['kind']!=ar.KIND];server.contracts.save(root/'proposal.json',p)
   self.assertIn('impact.attribution-missing',[x['ruleCode'] for x in server.v2.p3.validate_package(root)[0]])
if __name__=='__main__':unittest.main()
