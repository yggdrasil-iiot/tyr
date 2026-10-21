
"""P4-B mixed source and write-direction definitions. No runtime IO."""
import copy,json,re
from decimal import Decimal,InvalidOperation
NUMERIC={'Int16','UInt16','Int32','UInt32','Int64','Float32','Float64','Double','Decimal'}
LIMITS={'Int16':(-32768,32767),'UInt16':(0,65535),'Int32':(-2147483648,2147483647),'UInt32':(0,4294967295),'Int64':(-9223372036854775808,9223372036854775807)}
def kind(s):return s.get('sourceKind','plc')
def mode(s):return s.get('accessMode','read')
def nonplc(s):return kind(s)!='plc'
def numeric(v):
 if isinstance(v,bool) or not isinstance(v,str) or len(v)>256 or not re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]{1,4})?',v):raise ValueError('constant.numeric')
 d=Decimal(v)
 if not d.is_finite() or abs(d.as_tuple().exponent)>1000:raise ValueError('constant.numeric')
 return d
def rules(s):
 import validate_contracts as vc
 if s.get('schemaVersion')!='2.7.0':return []
 if kind(s)=='plc':
  d=copy.deepcopy(s);d.pop('sourceKind');d.pop('accessMode');d['schemaVersion']='2.4.0';return vc.source_rules(d)
 out=[]
 if s['status']=='ready' and s['unit']['status']=='unknown':out.append('source.unit-unconfirmed')
 if kind(s)=='external-value':
  a=s['access']
  if a['expressionLanguage']=='none' and a['expression'] is not None:out.append('source.expression-mode')
  if a['expressionLanguage']!='none' and (not isinstance(a['expression'],str) or not a['expression'].strip()):out.append('source.expression-required')
 if kind(s)=='constant':
  v=s['access']['value'];typ=s['rawRepresentation']['valueType']
  try:
   if typ=='Boolean':
    if type(v) is not bool:raise ValueError('constant.boolean')
   elif typ=='String':
    if not isinstance(v,str) or len(v)>4096:raise ValueError('constant.string')
   else:
    d=numeric(v)
    if typ in LIMITS and (d!=d.to_integral_value() or not LIMITS[typ][0]<=d<=LIMITS[typ][1]):raise ValueError('constant.range')
    if typ in ('Double','Float64') and abs(d)>Decimal('1.7976931348623157e308'):raise ValueError('constant.range')
    if typ=='Float32' and abs(d)>Decimal('3.4028234663852886e38'):raise ValueError('constant.range')
  except (ValueError,InvalidOperation) as e:out.append(str(e))
 return out
def validate_writes(docs,add):
 import validate_contracts as vc
 targets=set();destinations=set()
 def get(k,r):return docs.get((k,r['id'],r['version']))
 for d in docs.values():
  if d['kind']!='write-definition':continue
  path='write-definition:'+d['id'];t=get('target-instance',d['targetInstanceRef']);src=get('source-definition',d['destinationRef'])
  if not t or not src:add('write.reference',path);continue
  sem=get('semantic-definition',t['semanticDefinitionRef']);mid=d['memberPath'][0]['memberId'];member=next((m for m in sem['members'] if m['memberId']==mid),None) if sem else None
  if not member:add('write.member',path);continue
  if member['valueType'] in ('Structure','StructureArray'):add('write.logical-structure-unsupported',path);continue
  if t['equipmentInstanceId']!=d['equipmentInstanceId'] or src['equipmentInstanceId']!=d['equipmentInstanceId']:add('write.equipment',path)
  if mode(src) not in ('write','read-write') or kind(src) not in ('plc','solution-tag'):add('write.destination-readonly',path)
  if src.get('fixedArray') or src['rawRepresentation'].get('codec'):add('write.destination-unsupported',path)
  if src['status']!='ready':add('write.source-not-ready',path)
  required={json.dumps(x,sort_keys=True) for x in src['evidenceRefs']+t['evidenceRefs']}
  if not required<={json.dumps(x,sort_keys=True) for x in d['evidenceRefs']}:add('write.evidence-incomplete',path)
  location={'solutionInstanceRef':src['access']['solutionInstanceRef'],'tagPath':src['access']['tagPath']} if kind(src)=='solution-tag' else src['access']
  targetkey=(t['id'],t['version'],mid);destkey=(src['equipmentInstanceId'],src['connectionProfileRef'],src['accessProfileRef'],json.dumps(location,sort_keys=True))
  if targetkey in targets:add('write.duplicate-member',path)
  if destkey in destinations:add('write.duplicate-destination',path)
  targets.add(targetkey);destinations.add(destkey)
  typ,unit=member['valueType'],member['unit']
  for tr in d['transform']:
   if tr['op']=='linear':
    if typ not in NUMERIC:add('write.transform-type',path)
    typ='Decimal'
   elif tr['op']=='unit-convert':
    if typ not in NUMERIC or unit!={'status':'known','code':tr['from']} or (tr['from'],tr['to']) not in vc.UNIT_CONVERSIONS:add('write.transform-unit',path)
    typ='Decimal';unit={'status':'known','code':tr['to']}
   elif tr['op']=='cast':
    dest=tr['to']
    if (dest in NUMERIC and typ not in NUMERIC) or (dest not in NUMERIC and typ!=dest):add('write.transform-type',path)
    typ=dest
  if typ!=src['rawRepresentation']['valueType']:add('write.output-type',path)
  if unit!=src['unit'] or unit['status']=='unknown':add('write.output-unit',path)
