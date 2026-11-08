"""2.27 impact rule: the forseti stage-2 rule that judges quality incidents against the visits an attribution rule of the same
package produces.

Tyr authors the rule and the incident binding profile it names and checks both before export with the codes Bifrost's
ImpactRules and IncidentBindingProfile use: the attribution rule resolves, every incident scope path is a hierarchy node that
is a station of that rule or below one, the profile is an evidence-artifact 1.1.0 Tyr can read, and work-record retention is
at least the attribution horizon. Whether the incident schema supports each kind is the job's check. Approval stays with Bifrost.
"""
import json
from semantic_lifecycle import require
import validate_contracts as vc
import attribution_rule as ar
KIND='impact-rule'
VERSION='2.27.0'
PROFILE='0.1.0'
PREFIX='incident-binding-'
MEDIA='application/vnd.forseti.incident-binding+json'
SCHEMA_ID='urn:forseti:schema:incident:1.0.0'
FIELDS={'profileVersion','topic','format','kinds','equipmentRefBasis'}

def incident_profile(raw,code='impact.binding-profile'):
 """Profile 0.1.0 from its bytes: exactly the five fields, the constants, a non-empty topic, distinct non-empty kinds. Read as
 Bifrost's reader reads it: a UTF-8 BOM is skipped, duplicate keys and any decoder failure (deep nesting included) are the code."""
 try:b=json.loads(raw,object_pairs_hook=vc.pairs)
 except (UnicodeDecodeError,ValueError,RecursionError) as e:raise ValueError(code) from e
 require(ar.names(b)==FIELDS and b['profileVersion']==PROFILE and ar.text(b,'topic') and b['equipmentRefBasis']=='isa95-path',code)
 f=b['format'];require(ar.names(f)=={'schemaId','schemaSha256'} and f['schemaId']==SCHEMA_ID and ar.digest_form(f['schemaSha256']),code)
 ar.strings(b['kinds'],code)
 return b
def check(r,docs,read):
 """One rule, the spec's impact.* codes in Bifrost's order; the first failure stops it."""
 a=ar.find(docs,ar.KIND,r['attributionRuleRef']);require(a is not None,'impact.attribution-missing')
 h=ar.find(docs,'equipment-hierarchy',a['equipmentRef']);known=set(ar.paths(h).values()) if h is not None else set();stations=list(a['stations'])
 for s in r['incidentScope']:require(s in known and ar.within(stations,s),'impact.scope-containment')
 e=ar.find(docs,'evidence-artifact',r['incidentBindingRef']);require(e is not None and e['schemaVersion']=='1.1.0','impact.binding-unresolved')
 require(e['id'].startswith(PREFIX) and e['file']['mediaType']==MEDIA,'impact.binding-profile')
 incident_profile(read(e['file']['path']),'impact.binding-profile')
 require(a['temporal']['horizonMs']<=r['retention']['workRecordsMs'],'impact.retention-order')
def validate(docs,read):
 """docs: every document in one package; read(path) returns a data file's bytes. Attribution rules are validated first."""
 docs=list(docs)
 for r in docs:
  if r.get('kind')==KIND:check(r,docs,read)
