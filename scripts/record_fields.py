"""Pinned raw record fields as ordinary read-only canonical sources. No IO."""
import copy
import record_mappings as rm,mapping_templates as mt,validate_contracts as vc
from semantic_lifecycle import require

def is_field(s):return s.get('schemaVersion')=='2.21.0' or 'recordField' in s

def validate(documents):
 docs=list(documents);records={(r['id'],r['version']):r for r in docs if r.get('kind')=='record-mapping'}
 for s in docs:
  if s.get('kind')!='source-definition' or not is_field(s):continue
  require(s.get('schemaVersion')=='2.21.0' and not list(vc.schema_validator('source-definition','2.21.0').iter_errors(s)),'record-field.schema');b=s['recordField'];ref=b['recordMappingRef'];r=records.get((ref['id'],ref['version']));require(r is not None,'record-field.record-missing');require(ref==rm.pin(r),'record-field.record-pin');require(r['output']['mode']=='object' and r['output']['maxRows']==1,'record-field.object-required');require(s['equipmentInstanceId']==r['equipmentInstanceId'],'record-field.equipment');f=rm.fields(r).get(b['fieldId']);require(f is not None,'record-field.field-missing');require(s['rawRepresentation']==dict(mode='typed',valueType=f['valueType']) and s['unit']==f['unit'] and s['inputStage']==f['inputStage'],'record-field.signature');require(s['access']==dict(kind='external-value',providerRef=r['resultSchema']['providerRef'],valueKey=r['resultSchema']['valueKey']+'.'+f['fieldId'],expressionLanguage='none',expression=None),'record-field.provider');require((b['nullPolicy']=='reject' and b['defaultValue'] is None) or (b['nullPolicy']=='default' and f['nullable'] and b['defaultValue'] is not None),'record-field.null-policy')
  if b['nullPolicy']=='default':
   # Defaults on fields unused by the record template still require the same primitive range checks.
   from decimal import Decimal
   import mixed_sources
   v=b['defaultValue'];typ=f['valueType']
   if typ=='String':require(isinstance(v,str),'record-field.default-type')
   elif typ=='Boolean':require(type(v) is bool,'record-field.default-type')
   else:
    d=mixed_sources.numeric(v);require((typ=='Int32' and d==d.to_integral_value() and -2147483648<=d<=2147483647) or (typ=='Double' and abs(d)<=Decimal('1.7976931348623157e308')),'record-field.default-range')
 return records

def check_workspace(w):validate([r['definition'] for r in w['sources']]+rm.workspace_docs(w))

def transition(before,after):
 now={(r['definition']['id'],r['definition']['version']):r['definition'] for r in after['sources']}
 for row in before['sources']:
  s=row['definition']
  if is_field(s):require(now.get((s['id'],s['version']))==s,'record-field.definition-immutable')

def history(documents,prior):
 pinned={(s['id'],s['version']):s for s in prior if s.get('kind')=='source-definition' and is_field(s)}
 for s in documents:
  if s.get('kind')=='source-definition' and (s['id'],s['version']) in pinned:require(s==pinned[(s['id'],s['version'])],'record-field.history-conflict')

def create(w,id,ref,field_id,null_policy='reject',default_value=None):
 records={(r['id'],r['version']):r for r in w.get('recordMappings',[])};r=records.get((ref['id'],ref['version']));require(r is not None and rm.pin(r)==ref,'record-field.record-pin');f=rm.fields(r).get(field_id);require(f is not None,'record-field.field-missing')
 s=dict(kind='source-definition',schemaVersion='2.21.0',id=id,version='1.0.0',equipmentInstanceId=r['equipmentInstanceId'],sourceKind='external-value',accessMode='read',status='ready',connectionProfileRef=None,accessProfileRef='external-value-v1',rawAddressText='record:'+r['id']+'@'+r['version']+'/'+field_id,addressRadix=None,access=dict(kind='external-value',providerRef=r['resultSchema']['providerRef'],valueKey=r['resultSchema']['valueKey']+'.'+field_id,expressionLanguage='none',expression=None),rawRepresentation=dict(mode='typed',valueType=f['valueType']),inputStage=f['inputStage'],unit=copy.deepcopy(f['unit']),evidenceRefs=[dict(artifactId='manual-'+id,locator=dict(kind='text-line',line=1))],viewOf=None,recordField=dict(recordMappingRef=ref,fieldId=field_id,nullPolicy=null_policy,defaultValue=default_value));validate([s]+rm.workspace_docs(w));return s
