"""Explicit immutable row/common recipes and CAS scenario storage."""
import copy,json
import record_mappings as rm,record_broadcast as rb,mapping_templates as mt,logical_structures as ls,record_authoring as ra,broadcast_preview as bp
from template_authoring import snapshot,find,now

def compose(store,req,Conflict):
 required={'revision','id','version','label','equipmentInstanceId','resultSchema','output','selection','authoredBy','reason','note','origin','templateRef','modelRef','memberBindings','slotBindings','templateId','templateVersion','commonPolicy','rowErrorPolicy'};rm.require(set(req)==required,'broadcast.compose-request');w=copy.deepcopy(snapshot(store,req['revision'],Conflict)['workspace']);new_template=None;new_model=None;source_docs={(s['definition']['id'],s['definition']['version']):s['definition'] for s in w['sources']};fs={f['fieldId']:f for f in req['resultSchema']['fields']};commons={};fields=[];common_bindings=[]
 if req['templateRef'] is None:
  model=copy.deepcopy(find(w['semantics'],req['modelRef']['id'],req['modelRef']['version']));model.update(id='broadcast-model-'+mt.digest([req['templateId'],req['templateVersion']])[:24],version='1.0.0');by={ls.path_key(b['memberPath']):b for b in req['memberBindings']};layout=ls.layout(model);rm.require(set(by)==set(layout['leaves']) and len(by)==len(req['memberBindings']),'broadcast.members-incomplete');slots=[];inputs={};mapping_rows=[]
  for i,(key,leaf) in enumerate(layout['leaves'].items(),1):
   b=by[key];rm.require(set(b)=={'memberPath','input','transform'},'broadcast.member');v=b['input'];token=mt.digest(v)
   if token not in inputs:
    sid='input-'+str(i);inputs[token]=sid
    if v.get('kind')=='field':
     rm.require(set(v)=={'kind','fieldId','nullPolicy','defaultValue'} and v['fieldId'] in fs,'broadcast.field');f=fs[v['fieldId']];ref=dict(id='record-field-'+f['fieldId']+'-'+str(i),version='1.0.0');sig=dict(rawRepresentation={'valueType':f['valueType']},unit=f['unit'],inputStage=f['inputStage'],fixedArray=None);label=f['name'];fields.append(dict(slotId=sid,fieldId=f['fieldId'],nullPolicy=v['nullPolicy'],defaultValue=v['defaultValue']))
    else:
     rm.require(v.get('kind')=='common' and set(v)=={'kind','sourceRef'},'broadcast.common');s=source_docs.get((v['sourceRef']['id'],v['sourceRef']['version']));rm.require(s is not None,'broadcast.source-missing');ref={'id':s['id'],'version':s['version']};sig=mt.signature(s);label=s['id'];commons[(s['id'],s['version'])]=copy.deepcopy(s);common_bindings.append(dict(slotId=sid,sourceRef=mt.pin(s)))
    slots.append(dict(slotId=sid,label=label,sourceRef=ref,signature=sig))
   sid=inputs[token];ref=next(s['sourceRef'] for s in slots if s['slotId']==sid);mapping_rows.append(dict(mappingId='member-'+str(i),memberPath=leaf['memberPath'],valueRef=dict(kind='source',sourceRef=ref),transform=copy.deepcopy(b['transform']),outputUnit=leaf['member']['unit'],invalidValuePolicy='bad-quality',evidenceRefs=[]))
  target=dict(kind='target-instance',schemaVersion='2.0.0',id='broadcast-target-prototype',version='1.0.0',equipmentInstanceId=req['equipmentInstanceId'],label=req['label'],semanticDefinitionRef={'id':model['id'],'version':model['version']},evidenceRefs=[]);mapping=dict(kind='mapping-set',schemaVersion='2.12.0' if model['schemaVersion']=='2.12.0' else '2.2.0',id='broadcast-prototype',version='1.0.0',equipmentInstanceId=req['equipmentInstanceId'],targetInstanceRef={'id':target['id'],'version':target['version']},mappings=mapping_rows);versions=[t for t in w.get('mappingTemplates',[]) if t['id']==req['templateId']];previous=max(versions,key=lambda t:tuple(map(int,t['version'].split('.')))) if versions else None
  t=dict(kind='mapping-template',schemaVersion='2.19.0',id=req['templateId'],version=req['templateVersion'],label=req['label']+' · 배열 템플릿',description=req['note'],reason=req['reason'],authoredBy=req['authoredBy'],authoredAt=now(),previousTemplateRef=None if previous is None else mt.pin(previous),slots=slots,model=mt.clean(model),target=target,graphs=[],mapping=mapping);mt.template_check(t);new_template=t;new_model=t['model']
 else:
  t=find(w.get('mappingTemplates',[]),req['templateRef']['id'],req['templateRef']['version']);rm.require(mt.pin(t)==req['templateRef'],'record.template-pin')
  for b in req['slotBindings']:
   v=b['input'];sid=b['slotId']
   if v['kind']=='field':fields.append(dict(slotId=sid,fieldId=v['fieldId'],nullPolicy=v['nullPolicy'],defaultValue=v['defaultValue']))
   else:
    rm.require(v['kind']=='common','broadcast.common');s=source_docs.get((v['sourceRef']['id'],v['sourceRef']['version']));rm.require(s is not None,'broadcast.source-missing');commons[(s['id'],s['version'])]=copy.deepcopy(s);common_bindings.append(dict(slotId=sid,sourceRef=mt.pin(s)))
 old=[r for r in w.get('recordMappings',[]) if r['id']==req['id']];previous=max(old,key=lambda r:tuple(map(int,r['version'].split('.')))) if old else None
 r=dict(kind='record-mapping',schemaVersion=rb.VERSION,id=req['id'],version=req['version'],label=req['label'],equipmentInstanceId=req['equipmentInstanceId'],templateRef=mt.pin(t),semanticDefinitionRef={'id':t['model']['id'],'version':t['model']['version']},previousMappingRef=None if previous is None else rm.pin(previous),resultSchema=copy.deepcopy(req['resultSchema']),bindings=fields,commonBindings=common_bindings,commonSources=list(commons.values()),commonPolicy=req['commonPolicy'],rowErrorPolicy=req['rowErrorPolicy'],output=req['output'],selection=req['selection'],authoredBy=req['authoredBy'],authoredAt=now(),reason=req['reason'],provenance=dict(origin=req['origin'],capturedAt=now(),note=req['note']),evidenceRefs=[]);r['evidenceRefs']=[dict(artifactId=rm.evidence_id(r),locator=dict(kind='text-line',line=1))];return ra.plan(store,dict(revision=req['revision'],draft=dict(record=r,template=new_template,model=new_model)),Conflict)[0]

def save_scenario(store,req,Conflict):
 rm.require(set(req)=={'revision','id','scenarioRevision','mappingRef','snapshot','commonSamples','evaluatedAt'},'broadcast.scenario-request');snap=snapshot(store,req['revision'],Conflict);r=find(snap['workspace'].get('recordMappings',[]),req['mappingRef']['id'],req['mappingRef']['version']);rm.require(rm.pin(r)==req['mappingRef'],'broadcast.scenario-pin');bp.run(snap['workspace'],r['id'],r['version'],req['snapshot'],req['commonSamples'],req['revision'],req['evaluatedAt']);rm.require(isinstance(req['id'],str) and 1<=len(req['id'])<=128 and type(req['scenarioRevision']) is int and req['scenarioRevision']>=0,'broadcast.scenario-id')
 with store.connect() as c:
  c.execute('BEGIN IMMEDIATE');current=c.execute('SELECT revision FROM workspace WHERE id=1').fetchone()[0]
  if current!=req['revision']:raise Conflict('작성본이 바뀌었습니다.')
  c.execute('CREATE TABLE IF NOT EXISTS record_scenarios (id TEXT PRIMARY KEY,revision INTEGER NOT NULL,body TEXT NOT NULL)');old=c.execute('SELECT revision,body FROM record_scenarios WHERE id=?',(req['id'],)).fetchone()
  if old is not None:
   previous=json.loads(old[1]);rm.require(previous.get('kind')=='broadcast-scenario' and previous.get('mappingRef')==req['mappingRef'],'broadcast.scenario-owner: use a different ID for another mapping/version')
  if (old[0] if old else 0)!=req['scenarioRevision']:raise Conflict('가상 입력이 다른 창에서 변경됐습니다.')
  record=dict(kind='broadcast-scenario',schemaVersion=rb.VERSION,id=req['id'],scenarioRevision=req['scenarioRevision']+1,workspaceRevision=req['revision'],workspaceSha256=mt.digest(snap['workspace']),mappingRef=req['mappingRef'],snapshot=req['snapshot'],commonSamples=req['commonSamples'],evaluatedAt=req['evaluatedAt']);rm.require(not list(__import__('validate_contracts').schema_validator('broadcast-scenario',rb.VERSION).iter_errors(record)),'broadcast.scenario-schema');c.execute('INSERT INTO record_scenarios VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,body=excluded.body',(req['id'],record['scenarioRevision'],json.dumps(record,ensure_ascii=False)));return record
