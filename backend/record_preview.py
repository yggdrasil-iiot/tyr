"""Read-only finite virtual result-set preview; never connects to a provider."""
import copy,json
from datetime import datetime,timezone
import record_mappings as rm,mapping_templates as mt,preview,sample_quality,logical_structures as ls,mixed_sources

def cell(field,value):
 typ=field['valueType']
 if typ=='String':rm.require(isinstance(value,str) and len(value)<=4096,'record.cell-string')
 elif typ=='Boolean':rm.require(type(value) is bool,'record.cell-boolean')
 else:
  d=mixed_sources.numeric(value)
  if typ=='Int32':rm.require(d==d.to_integral_value() and -2147483648<=d<=2147483647,'record.cell-int32')
  else:rm.require(abs(d)<=mixed_sources.numeric('1.7976931348623157e308'),'record.cell-double')
 return value

def run(w,id,version,snapshot,revision,evaluated_at=None):
 records=[r for r in w.get('recordMappings',[]) if r['id']==id and r['version']==version];rm.require(len(records)==1,'record.mapping-missing');r=records[0];rm.require(r['schemaVersion']=='2.20.0','broadcast.use-broadcast-preview');rm.check_workspace(w);t=next(t for t in w['mappingTemplates'] if mt.pin(t)==r['templateRef']);rm.schema('virtual-result-set',snapshot);rm.require(snapshot['resultSetRef']==rm.pin(r['resultSchema']),'record.snapshot-pin');at=evaluated_at or datetime.now(timezone.utc).isoformat();rm.timestamp(at);captured=rm.timestamp(snapshot['capturedAt']);issues=[];trace=[];preserved=[];rows=[];keys=set();fs=rm.fields(r)
 def issue(code,detail,**extra):issues.append(dict(code=code,severity='error',detail=str(detail),**extra))
 if captured>rm.timestamp(at):issue('record.future-snapshot',snapshot['capturedAt'])
 if snapshot['quality']=='bad':issue('record.bad-snapshot-quality','bad')
 for index,row in enumerate(snapshot['rows']):
  key=[]
  for f in fs.values():
   v=row.get(f['fieldId'])
   if v is None:
    if not f['nullable']:issue('record.required-field',f['fieldId'],inputRowIndex=index)
   else:
    try:cell(f,v)
    except ValueError as e:issue(str(e),f['fieldId'],inputRowIndex=index)
  for k in r['resultSchema']['keyFields']:
   v=row.get(k)
   if not isinstance(v,str) or not v or len(v)>256:issue('record.key-value',k,inputRowIndex=index)
   key.append(v)
  token=json.dumps(key,ensure_ascii=False,separators=(',',':')).encode('utf-8')
  if token in keys:issue('record.duplicate-key',key,inputRowIndex=index)
  keys.add(token);extras={k:v for k,v in row.items() if k not in fs}
  if extras:
   if r['resultSchema']['unknownFields']=='reject':issue('record.unknown-fields',sorted(extras),inputRowIndex=index)
   else:preserved.append(dict(inputRowIndex=index,fields=copy.deepcopy(extras)))
  rows.append(dict(key=key,token=token,inputRowIndex=index,values=row))
 trace.append(dict(stage='record:validate',inputRows=len(rows),keyFields=r['resultSchema']['keyFields'],preservedFields=preserved))
 rows.sort(key=lambda x:x['token'])
 if r['selection']['kind']=='key':rows=[row for row in rows if row['key']==r['selection']['key']]
 trace.append(dict(stage='record:select',selection=r['selection'],selectedRows=len(rows),order=r['output']['order']))
 if not rows and r['output']['zeroPolicy']=='reject':issue('record.zero-rows','선택 결과가 없습니다.')
 if r['output']['mode']=='object' and len(rows)>1:issue('record.many-rows','객체에는 하나의 레코드만 연결할 수 있습니다.')
 if len(rows)>r['output']['maxRows']:issue('record.max-rows',r['output']['maxRows'])
 outputs=[];reports=[];uncertain=snapshot['quality']=='uncertain'
 if not issues:
  for row in rows:
   a=rm.compile(r,t,row['key']);model=a['generated'][0];target=a['generated'][1];mapping=a['generated'][-1];sources=a['sourceSnapshots'];bound={b['slotId']:b for b in a['bindings']};samples={};defaults=[];row_issues=[]
   for b in r['bindings']:
    value=row['values'].get(b['fieldId']);f=fs[b['fieldId']]
    if value is None:
     if b['nullPolicy']=='default':
      value=b['defaultValue'];defaults.append(dict(code='record.default-used',severity='warning',fieldId=b['fieldId'],slotId=b['slotId'],value=value))
      try:cell(f,value)
      except ValueError as e:row_issues.append(dict(code=str(e),severity='error',fieldId=f['fieldId']))
     else:row_issues.append(dict(code='record.null-input',severity='error',fieldId=b['fieldId']))
    samples[bound[b['slotId']]['sourceRef']['id']]={'typedValue':value}
   scope=dict(workspaceVersion='2.0.0',equipment=[e for e in w['equipment'] if e['id']==r['equipmentInstanceId']],connections=[],sources=[dict(definition=s,note=r['provenance']['note'],origin=r['provenance']['origin'],capturedAt=r['provenance']['capturedAt']) for s in sources],semantics=[model],targets=[target],graphs=[g for g in a['generated'] if g['kind']=='value-graph'],mappings=[mapping]);values={};members=[]
   if not row_issues:
    for b in mapping['mappings']:
     ids=sample_quality.source_ids(scope,b);available={k:v for k,v in samples.items() if k in ids};evaluation=None
     if 'temporalPolicy' in b:
      available={k:dict(value=v,sourceTimestamp=snapshot['capturedAt'],serverTimestamp=snapshot['capturedAt'],quality=snapshot['quality'],sequence=None) for k,v in available.items()};evaluation={'at':at,'triggerSequence':None}
     result=preview.run(scope,mapping['id'],b['mappingId'],available,revision,evaluation);values[ls.path_key(b['memberPath'])]=None if result['result'] is None else result['result']['value'];members.append(dict(memberPath=b['memberPath'],preview=result));row_issues.extend(result['issues'])
   row_issues=defaults+row_issues;bad=any(i['severity']=='error' for i in row_issues);partial=ls.assemble(model,values) if values else None;quality='bad' if bad else 'uncertain' if row_issues or snapshot['quality']=='uncertain' else 'good';uncertain|=quality=='uncertain';identity=dict(key=row['key'],sha256=mt.digest(row['key']),inputRowIndex=row['inputRowIndex']);reports.append(dict(identity=identity,quality=quality,result=None if bad else partial,partialResult=partial,fieldBindings=[dict(binding=b,value=row['values'].get(b['fieldId'])) for b in r['bindings']],members=members,issues=row_issues));outputs.append(partial)
   issues.extend(dict(i,recordKey=row['key']) for i in row_issues)
 bad=any(i['severity']=='error' for i in issues);result=None if bad else (outputs[0] if outputs else None) if r['output']['mode']=='object' else outputs
 return dict(kind='record-preview',schemaVersion='2.20.0',revision=revision,mappingRef=rm.pin(r),templateRef=r['templateRef'],resultSetRef=rm.pin(r['resultSchema']),inputSha256=mt.digest(snapshot),capturedAt=snapshot['capturedAt'],evaluatedAt=at,quality='bad' if bad else 'uncertain' if uncertain or issues else 'good',valid=not bad,empty=not rows,result=result,partialResults=outputs,records=reports,trace=trace,issues=issues,preservedFields=preserved,persisted=False,atomicSnapshot=False,deviceCommunication='excluded',externalSQL='excluded',writeExecution='excluded')
