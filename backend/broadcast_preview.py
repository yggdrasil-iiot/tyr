"""Virtual fan-out: one declared common frame reused across every bounded row."""
import copy,json
from datetime import datetime,timezone
import record_mappings as rm,record_broadcast as rb,mapping_templates as mt,record_preview as rp,preview,sample_quality as sq,logical_structures as ls

def scope(w,r,a):
 return dict(workspaceVersion='2.0.0',equipment=[e for e in w['equipment'] if e['id']==r['equipmentInstanceId']],connections=[],sources=[dict(definition=s,note=r['provenance']['note'],origin=r['provenance']['origin'],capturedAt=r['provenance']['capturedAt']) for s in a['sourceSnapshots']],semantics=[a['generated'][0]],targets=[a['generated'][1]],graphs=[d for d in a['generated'] if d['kind']=='value-graph'],mappings=[a['generated'][-1]])

def run(w,id,version,snapshot,common_samples,revision,evaluated_at):
 snapshot=copy.deepcopy(snapshot);common_samples=copy.deepcopy(common_samples)
 rm.check_workspace(w);rs=[r for r in w.get('recordMappings',[]) if r['id']==id and r['version']==version];rm.require(len(rs)==1,'record.mapping-missing');r=rs[0];rm.require(r['schemaVersion']==rb.VERSION,'broadcast.contract-required');t=next(t for t in w['mappingTemplates'] if mt.pin(t)==r['templateRef']);rm.schema('virtual-result-set',snapshot);rm.require(snapshot['resultSetRef']==rm.pin(r['resultSchema']),'record.snapshot-pin');rm.timestamp(evaluated_at)
 a=rm.compile(r,t);base=scope(w,r,a);mapping=base['mappings'][0];fs=rm.fields(r);issues=[];trace=[];reports=[];preserved=[];rows=[];keys=set();outputs=[];omitted=[]
 def issue(code,detail='',**kw):return dict(code=code,severity='error',detail=str(detail),**kw)
 common_ids={s['id'] for s in r['commonSources']};required={s['id'] for s in r['commonSources'] if s.get('sourceKind')!='constant'}
 rm.require(isinstance(common_samples,dict) and set(common_samples)<=required,'broadcast.common-inputs')
 # Snapshot once; all rows receive identical immutable values, timestamps and quality.
 frame=copy.deepcopy(common_samples);db_id='broadcast-db-frame';rm.require(db_id not in common_ids,'broadcast.reserved-source-id')
 fake=copy.deepcopy(a['sourceSnapshots'][0]);fake['id']=db_id;base['sources'].append(dict(definition=fake,note='Virtual result-set clock',origin='synthetic',capturedAt=snapshot['capturedAt']))
 frame[db_id]=dict(value={'typedValue':'0'},sourceTimestamp=snapshot['capturedAt'],serverTimestamp=snapshot['capturedAt'],quality=snapshot['quality'],sequence=None)
 b={'temporalPolicy':rb.policy(r)};raw,time_trace,time_issues,temporal=sq.assess(base,b,frame,{'at':evaluated_at,'triggerSequence':None},sorted(required|{db_id}));trace.extend(time_trace);issues.extend(time_issues);base['sources']=base['sources'][:-1]
 for id_,value in frame.items():
  if id_!=db_id and isinstance(value,dict) and value.get('sequence') is not None:issues.append(issue('broadcast.sequence-unsupported',id_))
 common_reports=[]
 # Independently decode common slots even when the result set has zero rows.
 for slot_binding in r['commonBindings']:
  sid=slot_binding['sourceRef']['id'];slot=next(s for s in t['slots'] if s['slotId']==slot_binding['slotId']);s=next(s for s in r['commonSources'] if s['id']==sid);sc=copy.deepcopy(base);leaf=next(iter(ls.layout(sc['semantics'][0])['leaves'].values()));member=ls.resolve(sc['semantics'][0],leaf['memberPath']);member.update(valueType=slot['signature']['rawRepresentation']['valueType'],unit=slot['signature']['unit']);bind=copy.deepcopy(mapping['mappings'][0]);bind.update(memberPath=leaf['memberPath'],valueRef={'kind':'source','sourceRef':{'id':sid,'version':s['version']}},transform=[],outputUnit=s['unit']);bind.pop('temporalPolicy',None);sc['mappings'][0]['mappings']=[bind];p=preview.run(sc,mapping['id'],bind['mappingId'],{sid:raw[sid]} if sid in raw else {},revision);common_reports.append(dict(slotId=slot_binding['slotId'],sourceRef=slot_binding['sourceRef'],preview=p));issues.extend(dict(i,scope='common') for i in p['issues'])
 for bind in mapping['mappings']:
  if set(sq.source_ids(base,bind))<=common_ids:
   p=preview.run(base,mapping['id'],bind['mappingId'],{k:v for k,v in raw.items() if k in set(sq.source_ids(base,bind))},revision);issues.extend(dict(i,scope='common-transform') for i in p['issues']);common_reports.append(dict(memberPath=bind['memberPath'],preview=p))
 trace.append(dict(stage='broadcast:common-frame',inputSha256=mt.digest(common_samples),mode=r['commonPolicy']['mode'],evaluatedAt=evaluated_at,sourcePins=[b['sourceRef'] for b in r['commonBindings']],atomicSnapshot=False))
 for index,row in enumerate(snapshot['rows']):
  row_issues=[];key=[row.get(k) for k in r['resultSchema']['keyFields']]
  if any(not isinstance(k,str) or not k or len(k)>256 for k in key):issues.append(issue('record.key-value',key,inputRowIndex=index))
  token=json.dumps(key,ensure_ascii=False,separators=(',',':')).encode('utf-8')
  if token in keys:issues.append(issue('record.duplicate-key',key,inputRowIndex=index))
  keys.add(token)
  for f in fs.values():
   value=row.get(f['fieldId'])
   if value is None:
    if not f['nullable']:row_issues.append(issue('record.required-field',f['fieldId']))
   else:
    try:rp.cell(f,value)
    except ValueError as e:row_issues.append(issue(str(e),f['fieldId']))
  extra={k:v for k,v in row.items() if k not in fs}
  if extra:
   if r['resultSchema']['unknownFields']=='reject':row_issues.append(issue('record.unknown-fields',sorted(extra)))
   else:preserved.append(dict(inputRowIndex=index,fields=copy.deepcopy(extra)))
  rows.append(dict(key=key,token=token,inputRowIndex=index,values=row,issues=row_issues))
 rows.sort(key=lambda row:row['token'])
 if r['selection']['kind']=='key':rows=[row for row in rows if row['key']==r['selection']['key']]
 if len(rows)>r['output']['maxRows']:issues.append(issue('record.max-rows',r['output']['maxRows']))
 if not rows and r['output']['zeroPolicy']=='reject':issues.append(issue('record.zero-rows'))
 trace.append(dict(stage='broadcast:select',selectedRows=len(rows),order=r['output']['order'],rowErrorPolicy=r['rowErrorPolicy']))
 global_bad=any(i['severity']=='error' for i in issues)
 if not global_bad:
  for row in rows:
   a=rm.compile(r,t,row['key']);sc=scope(w,r,a);m=sc['mappings'][0];bindings={b['slotId']:b for b in a['bindings']};samples=copy.deepcopy({k:v for k,v in raw.items() if k in common_ids});row_issues=list(row['issues']);members=[];values={}
   for b in r['bindings']:
    value=row['values'].get(b['fieldId'])
    if value is None:
     if b['nullPolicy']=='default':value=b['defaultValue'];row_issues.append(dict(code='record.default-used',severity='warning',fieldId=b['fieldId'],value=value))
     else:row_issues.append(issue('record.null-input',b['fieldId']))
    samples[bindings[b['slotId']]['sourceRef']['id']]={'typedValue':value}
   if not any(i['severity']=='error' for i in row_issues):
    for b in m['mappings']:
     result=preview.run(sc,m['id'],b['mappingId'],{k:v for k,v in samples.items() if k in set(sq.source_ids(sc,b))},revision);values[ls.path_key(b['memberPath'])]=None if result['result'] is None else result['result']['value'];members.append(dict(memberPath=b['memberPath'],preview=result));row_issues.extend(result['issues'])
     # A transform using only common inputs must never be hidden by row omission.
     ids=set(sq.source_ids(sc,b))
     if ids<=common_ids and any(i['severity']=='error' for i in result['issues']):global_bad=True;issues.extend(dict(i,scope='common') for i in result['issues'])
   bad=any(i['severity']=='error' for i in row_issues);value=ls.assemble(sc['semantics'][0],values) if values else None;identity=dict(key=row['key'],sha256=mt.digest(row['key']),inputRowIndex=row['inputRowIndex']);reports.append(dict(identity=identity,quality='bad' if bad else 'uncertain' if row_issues or time_issues else 'good',result=None if bad else value,partialResult=value,members=members,issues=row_issues,commonInputSha256=mt.digest(common_samples)))
   if bad:omitted.append(identity)
   else:outputs.append(value)
   issues.extend(dict(i,recordKey=row['key'],scope='record') for i in row_issues)
 row_bad=bool(omitted);valid=not global_bad and (not row_bad or r['rowErrorPolicy']=='omit-invalid');quality='bad' if not valid else 'uncertain' if issues else 'good'
 return dict(kind='broadcast-preview',schemaVersion=rb.VERSION,revision=revision,mappingRef=rm.pin(r),templateRef=r['templateRef'],resultSetRef=rm.pin(r['resultSchema']),inputSha256=mt.digest(snapshot),commonInputSha256=mt.digest(common_samples),commonPolicy=r['commonPolicy'],rowErrorPolicy=r['rowErrorPolicy'],evaluatedAt=evaluated_at,result=outputs if valid else None,partialResults=outputs,records=reports,commonInputs=common_reports,omittedRecords=omitted,selectedRows=len(rows),outputRows=len(outputs) if valid else 0,valid=valid,quality=quality,issues=issues,trace=trace,preservedFields=preserved,persisted=False,atomicSnapshot=False,deviceCommunication='excluded',externalSQL='excluded',writeExecution='excluded')
