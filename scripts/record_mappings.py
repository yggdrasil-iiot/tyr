"""Bounded offline result-set -> existing canonical mapping template contracts."""
import copy,json,tempfile,shutil
from pathlib import Path
import validate_contracts as vc,mapping_templates as mt,mixed_sources
from semantic_lifecycle import require,timestamp,digest
VERSION='2.20.0'
def pin(d):return dict(id=d['id'],version=d['version'],sha256=digest(d))
def schema(kind,d):require(not list(vc.schema_validator(kind,VERSION).iter_errors(d)),'record.schema:'+kind)
def evidence_id(r):return 'record-'+r['id']+'-'+r['version'].replace('.','-')
def fields(r):return {f['fieldId']:f for f in r['resultSchema']['fields']}
def basic(r,t):
 require(not list(vc.schema_validator('record-mapping',r['schemaVersion']).iter_errors(r)),'record.schema:record-mapping');timestamp(r['authoredAt']);timestamp(r['provenance']['capturedAt']);mt.template_check(t)
 require(r['templateRef']==mt.pin(t),'record.template-pin');require(r['semanticDefinitionRef']=={'id':t['model']['id'],'version':t['model']['version']},'record.model-ref')
 require(all(int(x)<=2147483647 for x in r['version'].split('.')),'record.version')
 rs=r['resultSchema'];fs=fields(r);require(len(fs)==len(rs['fields']),'record.field-duplicate');require(len(set(rs['keyFields']))==len(rs['keyFields']) and all(k in fs and fs[k]['valueType']=='String' and not fs[k]['nullable'] for k in rs['keyFields']),'record.key-contract')
 q=rs['query'];require((q['language']=='none' and q['text'] is None) or (q['language']!='none' and isinstance(q['text'],str) and q['text'].strip()),'record.query-metadata')
 slots={s['slotId']:s for s in t['slots']};common=r.get('commonBindings',[]);all_bindings=r['bindings']+common;require({b['slotId'] for b in all_bindings}==set(slots) and len(all_bindings)==len(slots),'record.slot-bindings')
 if r['schemaVersion']=='2.22.0':
  import record_broadcast as rb
  rb.basic(r,t)
 for b in r['bindings']:
  require(b['fieldId'] in fs,'record.field-missing');f=fs[b['fieldId']];signature=dict(rawRepresentation={'valueType':f['valueType']},unit=f['unit'],inputStage=f['inputStage'],fixedArray=None);require(slots[b['slotId']]['signature']==signature,'record.slot-signature:'+b['slotId']);require((b['nullPolicy']=='reject' and b['defaultValue'] is None) or (b['nullPolicy']=='default' and f['nullable'] and b['defaultValue'] is not None),'record.null-policy')
 out=r['output'];require((out['mode']=='object' and out['zeroPolicy'] in ('reject','null') and out['manyPolicy']=='reject' and out['maxRows']==1) or (out['mode']=='array' and out['zeroPolicy'] in ('reject','empty') and out['manyPolicy']=='all'),'record.cardinality-contract')
 sel=r['selection'];require((sel['kind']=='all' and not sel['key']) or (sel['kind']=='key' and len(sel['key'])==len(rs['keyFields'])),'record.selection-contract')
 require(r['evidenceRefs']==[{'artifactId':evidence_id(r),'locator':{'kind':'text-line','line':1}}],'record.evidence-contract')
 for b in r['bindings']:
  if b['nullPolicy']=='default':
   f=fs[b['fieldId']];v=b['defaultValue'];typ=f['valueType']
   if typ=='String':require(isinstance(v,str),'record.default-type')
   elif typ=='Boolean':require(type(v) is bool,'record.default-type')
   else:
    d=mixed_sources.numeric(v);require((typ=='Int32' and d==d.to_integral_value() and -2147483648<=d<=2147483647) or (typ=='Double' and abs(d)<=mixed_sources.numeric('1.7976931348623157e308')),'record.default-range')
 return r

def compile(r,t,identity=None):
 basic(r,t);app_id='record-'+digest([r['id'],r['version'],identity])[:24];sources=[];bindings=[];fs=fields(r)
 for b in r['bindings']:
  f=fs[b['fieldId']];id=app_id+'-'+b['slotId'];source=dict(kind='source-definition',schemaVersion='2.7.0',id=id,version='1.0.0',equipmentInstanceId=r['equipmentInstanceId'],connectionProfileRef=None,accessProfileRef='external-value-v1',sourceKind='external-value',accessMode='read',status='ready',rawAddressText=r['resultSchema']['valueKey']+'.'+f['fieldId'],addressRadix=None,access=dict(kind='external-value',providerRef=r['resultSchema']['providerRef'],valueKey=r['resultSchema']['valueKey']+'.'+f['fieldId'],expressionLanguage='none',expression=None),rawRepresentation={'mode':'typed','valueType':f['valueType']},inputStage=f['inputStage'],unit=copy.deepcopy(f['unit']),evidenceRefs=copy.deepcopy(r['evidenceRefs']),viewOf=None);sources.append(source);bindings.append(dict(slotId=b['slotId'],sourceRef=dict(id=id,version='1.0.0')))
 for b in r.get('commonBindings',[]):bindings.append(dict(slotId=b['slotId'],sourceRef={k:b['sourceRef'][k] for k in ('id','version')}))
 sources.extend(copy.deepcopy(r.get('commonSources',[])))
 a=dict(kind='template-application',schemaVersion='2.19.0',id='application-'+app_id+'-r1',version='1.0.0',applicationId=app_id,revision=1,previousApplicationRef=None,templateRef=mt.pin(t),equipmentInstanceId=r['equipmentInstanceId'],targetLabel=r['label'],bindings=bindings,sourceSnapshots=sources,generated=[{},{},{}],authoredBy=r['authoredBy'],authoredAt=r['authoredAt']);a['generated']=mt.materialize(t,a)
 return a

def histories(documents):
 docs=list(documents);ts,_=mt.histories([d for d in docs if d.get('kind') in mt.KINDS]);templates={(t['id'],t['version']):t for vs in ts.values() for t in vs};unique={};rs_signatures={};common_pins={}
 for r in docs:
  if r.get('kind')!='record-mapping':continue
  k=(r['id'],r['version']);require(k not in unique or unique[k]==r,'record.history-conflict');unique[k]=r
 require(len(unique)<=128,'record.history-limit');groups={}
 for r in unique.values():
  require(not list(vc.schema_validator('record-mapping',r['schemaVersion']).iter_errors(r)),'record.schema:record-mapping');ref=r['templateRef'];t=templates.get((ref['id'],ref['version']));require(t is not None,'record.template-missing');basic(r,t);groups.setdefault(r['id'],[]).append(r);key=(r['resultSchema']['id'],r['resultSchema']['version']);h=digest(r['resultSchema']);require(key not in rs_signatures or rs_signatures[key]==h,'record.result-schema-conflict');rs_signatures[key]=h
 for r in unique.values():
  for source in r.get('commonSources',[]):
   k=(source['id'],source['version']);require(k not in common_pins or common_pins[k]==source,'broadcast.source-history-conflict');common_pins[k]=source
 for versions in groups.values():
  require(len(versions)<=32,'record.version-limit');versions.sort(key=lambda r:tuple(map(int,r['version'].split('.'))));previous=None
  for r in versions:require(r['previousMappingRef']==(None if previous is None else pin(previous)),'record.version-chain');require(previous is None or r['equipmentInstanceId']==previous['equipmentInstanceId'],'record.equipment-change');previous=r
 return templates,groups

def validate(documents,history=(),root=None):
 docs=list(documents);templates,groups=histories(list(history)+docs);models={(d['id'],d['version']):d for d in docs if d['kind']=='semantic-definition'}
 for r in docs:
  if r['kind']!='record-mapping':continue
  t=templates[(r['templateRef']['id'],r['templateRef']['version'])];
  if r['schemaVersion']=='2.22.0':
   import record_broadcast as rb
   rb.source_pins(r,docs)
  ref=r['semanticDefinitionRef'];require(mt.clean(models.get((ref['id'],ref['version']),{}))==t['model'],'record.semantic-pin')
  a=compile(r,t)
  if root is not None:
   import p3a_contracts as p3
   with tempfile.TemporaryDirectory(prefix='tyr-record-static-') as tmp:
    folder=Path(tmp);entries=[]
    for i,d in enumerate(a['sourceSnapshots']+a['generated']):
     name='derived/'+str(i)+'.json';(folder/'derived').mkdir(exist_ok=True);vc.save(folder/name,d);entries.append(dict(path=name,kind=d['kind'],id=d['id'],version=d['version'],sha256=vc.hashed(folder/name)))
    ev_ids={x['artifactId'] for s in a['sourceSnapshots'] for x in s['evidenceRefs']}
    for i,d in enumerate(x for x in docs if x['kind']=='evidence-artifact' and x['id'] in ev_ids):
     name='derived/evidence-'+str(i)+'.json';vc.save(folder/name,d);entries.append(dict(path=name,kind=d['kind'],id=d['id'],version=d['version'],sha256=vc.hashed(folder/name)));dest=folder/d['file']['path'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(vc.safe(Path(root),d['file']['path']),dest)
    vc.save(folder/'proposal.json',dict(kind='mapping-proposal',schemaVersion='2.7.0',id='record-static',version='1.0.0',baseRelease=None,files=entries));errors,_=p3.validate_package(folder);require(not errors,'record.derived-invalid:'+','.join(x['ruleCode'] for x in errors[:8]))
 return templates,groups

def governance(documents):
 docs=list(documents)
 if not any(d.get('kind')=='record-mapping' for d in docs):return []
 templates,_=histories(docs);out=[]
 for r in docs:
  if r['kind']=='record-mapping':
   derived=compile(r,templates[(r['templateRef']['id'],r['templateRef']['version'])])['generated'];derived[-1]['id']='record-'+r['id']+'-'+r['version'];out.extend(derived)
 return out

def workspace_docs(w):return w.get('recordMappings',[])+w.get('mappingTemplates',[])+w.get('templateApplications',[])+w['semantics']+[s['definition'] for s in w['sources']]
def check_workspace(w):
 records=w.get('recordMappings',[]);require(isinstance(records,list) and len(records)<=128,'record.workspace-limit');require(len({(r.get('id'),r.get('version')) for r in records})==len(records),'record.duplicate')
 if not records:return
 validate(workspace_docs(w))
 require(all(r['equipmentInstanceId'] in {e['id'] for e in w['equipment']} for r in records),'record.equipment')
def check_transition(before,after):
 new={(r['id'],r['version']):r for r in after.get('recordMappings',[])}
 for r in before.get('recordMappings',[]):require(new.get((r['id'],r['version']))==r,'record.history-immutable')

def build(w,folder,proposal):
 records=w.get('recordMappings',[])
 if not records:return
 proposal['schemaVersion']='2.22.0' if any(r['schemaVersion']=='2.22.0' for r in records) else VERSION;(folder/'records').mkdir(exist_ok=True);(folder/'record-evidence').mkdir(exist_ok=True)
 def emit(path,d):vc.save(folder/path,d);proposal['files'].append(dict(path=path,kind=d['kind'],id=d['id'],version=d['version'],sha256=vc.hashed(folder/path)))
 for i,r in enumerate(records):
  path='record-evidence/'+r['id']+'-'+r['version']+'.txt';(folder/path).write_text(json.dumps(dict(declaredBy=r['authoredBy'],reason=r['reason'],resultSchema=r['resultSchema'],note=r['provenance']['note']),ensure_ascii=False,sort_keys=True)+'\n',encoding='utf-8',newline='\n');ev=dict(kind='evidence-artifact',schemaVersion='1.0.0',id=evidence_id(r),version=r['version'],origin=r['provenance']['origin'],file=dict(path=path,sha256=vc.hashed(folder/path),mediaType='text/plain'),capturedAt=r['provenance']['capturedAt'],product=None,scope=[r['equipmentInstanceId']]);emit('records/evidence-'+str(i)+'.json',ev);emit('records/'+str(i)+'.json',r)
