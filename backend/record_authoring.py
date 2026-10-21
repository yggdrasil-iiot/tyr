"""CAS authoring/scenarios for offline row projections."""
import copy,json
from datetime import datetime,timezone
import record_mappings as rm,mapping_templates as mt,record_preview,logical_structures as ls
from template_authoring import snapshot,find,now

def listing(store):
 s=store.read();w=s['workspace'];return dict(revision=s['revision'],records=w.get('recordMappings',[]),recordPins=[dict(mappingRef=rm.pin(r),resultSetRef=rm.pin(r['resultSchema'])) for r in w.get('recordMappings',[])],templates=[dict(template=t,pin=mt.pin(t)) for t in w.get('mappingTemplates',[])],scenarios=scenarios(store),execution='excluded')
def compose(store,req,Conflict):
 required={'revision','id','version','label','equipmentInstanceId','resultSchema','output','selection','authoredBy','reason','note','origin','templateRef','modelRef','memberBindings','slotBindings','templateId','templateVersion'};rm.require(set(req)==required,'record.compose-request');w=copy.deepcopy(snapshot(store,req['revision'],Conflict)['workspace']);new_template=None;new_model=None
 if req['templateRef'] is None:
  source=find(w['semantics'],req['modelRef']['id'],req['modelRef']['version']);model=copy.deepcopy(source);model.update(id='records-model-'+mt.digest([req['templateId'],req['templateVersion']])[:24],version='1.0.0');layout=ls.layout(model);fs={f['fieldId']:f for f in req['resultSchema']['fields']};by={ls.path_key(b['memberPath']):b for b in req['memberBindings']};rm.require(set(by)==set(layout['leaves']) and len(by)==len(req['memberBindings']),'record.members-incomplete');used=sorted({b['fieldId'] for b in by.values()});rm.require(set(used)<=set(fs),'record.field-missing');slots=[];slot_fields={}
  for i,id in enumerate(used,1):
   f=fs[id];sid='input-'+str(i);slot_fields[id]=sid;slots.append(dict(slotId=sid,label=f['name'],sourceRef=dict(id='record-field-'+id,version='1.0.0'),signature=dict(rawRepresentation={'valueType':f['valueType']},unit=f['unit'],inputStage=f['inputStage'],fixedArray=None)))
  target=dict(kind='target-instance',schemaVersion='2.0.0',id='record-target-prototype',version='1.0.0',equipmentInstanceId=req['equipmentInstanceId'],label=req['label'],semanticDefinitionRef=dict(id=model['id'],version=model['version']),evidenceRefs=[])
  mapping=dict(kind='mapping-set',schemaVersion='2.12.0' if model['schemaVersion']=='2.12.0' else '2.2.0',id='record-mapping-prototype',version='1.0.0',equipmentInstanceId=req['equipmentInstanceId'],targetInstanceRef={'id':target['id'],'version':target['version']},mappings=[])
  for key,leaf in layout['leaves'].items():
   b=by[key];rm.require(set(b)=={'memberPath','fieldId','transform'},'record.member-binding');field=b['fieldId'];mapping['mappings'].append(dict(mappingId='field-'+mt.digest(leaf['memberPath'])[:12],memberPath=leaf['memberPath'],valueRef=dict(kind='source',sourceRef=dict(id='record-field-'+field,version='1.0.0')),transform=copy.deepcopy(b['transform']),outputUnit=leaf['member']['unit'],invalidValuePolicy='bad-quality',evidenceRefs=[]))
  versions=[t for t in w.get('mappingTemplates',[]) if t['id']==req['templateId']];previous=max(versions,key=lambda t:tuple(map(int,t['version'].split('.')))) if versions else None
  new_template=dict(kind='mapping-template',schemaVersion='2.19.0',id=req['templateId'],version=req['templateVersion'],label=req['label']+' · 레코드 템플릿',description=req['note'],reason=req['reason'],authoredBy=req['authoredBy'],authoredAt=now(),previousTemplateRef=None if previous is None else mt.pin(previous),slots=slots,model=mt.clean(model),target=target,graphs=[],mapping=mapping);mt.template_check(new_template);new_model=copy.deepcopy(new_template['model']);t=new_template;policies={b['fieldId']:b for b in req['slotBindings']};bindings=[dict(slotId=slot_fields[id],fieldId=id,nullPolicy=policies.get(id,{}).get('nullPolicy','reject'),defaultValue=policies.get(id,{}).get('defaultValue')) for id in used]
 else:
  t=find(w.get('mappingTemplates',[]),req['templateRef']['id'],req['templateRef']['version']);rm.require(mt.pin(t)==req['templateRef'],'record.template-pin');bindings=copy.deepcopy(req['slotBindings'])
 old=[r for r in w.get('recordMappings',[]) if r['id']==req['id']];previous=max(old,key=lambda r:tuple(map(int,r['version'].split('.')))) if old else None
 r=dict(kind='record-mapping',schemaVersion='2.20.0',id=req['id'],version=req['version'],label=req['label'],equipmentInstanceId=req['equipmentInstanceId'],templateRef=mt.pin(t),semanticDefinitionRef=dict(id=t['model']['id'],version=t['model']['version']),previousMappingRef=None if previous is None else rm.pin(previous),resultSchema=copy.deepcopy(req['resultSchema']),bindings=bindings,output=copy.deepcopy(req['output']),selection=copy.deepcopy(req['selection']),authoredBy=req['authoredBy'],authoredAt=now(),reason=req['reason'],provenance=dict(origin=req['origin'],capturedAt=now(),note=req['note']),evidenceRefs=[]);r['evidenceRefs']=[dict(artifactId=rm.evidence_id(r),locator=dict(kind='text-line',line=1))];draft=dict(record=r,template=new_template,model=new_model);return plan(store,dict(revision=req['revision'],draft=draft),Conflict)[0]

def plan(store,req,Conflict):
 rm.require(set(req) in ({'revision','draft'},{'revision','draft','planSha256'}),'record.plan-request');w=copy.deepcopy(snapshot(store,req['revision'],Conflict)['workspace']);d=req['draft'];rm.require(isinstance(d,dict) and set(d)=={'record','template','model'},'record.draft');r=d['record']
 if d['template'] is not None:
  rm.require(d['model']==d['template']['model'],'record.draft-model');w.setdefault('mappingTemplates',[]).append(copy.deepcopy(d['template']));w['semantics'].append(copy.deepcopy(d['model']))
 rm.require(not any(x['id']==r['id'] and x['version']==r['version'] for x in w.get('recordMappings',[])),'record.version-exists');w.setdefault('recordMappings',[]).append(copy.deepcopy(r))
 import server
 server.check_state(w);findings=server.findings_for(w);own=[x for x in findings if x['ruleCode'].startswith('record.')];rm.require(not own,'record.plan-invalid');return dict(kind='record-authoring-plan',revision=req['revision'],draft=d,planSha256=mt.digest({'revision':req['revision'],'draft':d}),valid=True,findings=own,persisted=False),w

def apply(store,req,Conflict):
 rm.require('planSha256' in req,'먼저 필드 매핑을 검증하세요.');p,w=plan(store,req,Conflict);rm.require(req['planSha256']==p['planSha256'],'record.plan-changed');return dict(saved=store.save(req['revision'],w),record=req['draft']['record'])

def scenarios(store):
 with store.connect() as c:
  if not c.execute("SELECT 1 FROM sqlite_master WHERE name='record_scenarios'").fetchone():return []
  return [json.loads(row[0]) for row in c.execute('SELECT body FROM record_scenarios ORDER BY id')]

def save_scenario(store,req,Conflict):
 rm.require(set(req)=={'revision','id','scenarioRevision','mappingRef','snapshot'},'record.scenario-request');s=snapshot(store,req['revision'],Conflict);r=find(s['workspace'].get('recordMappings',[]),req['mappingRef']['id'],req['mappingRef']['version']);rm.require(rm.pin(r)==req['mappingRef'],'record.scenario-pin');rm.schema('virtual-result-set',req['snapshot']);rm.require(req['snapshot']['resultSetRef']==rm.pin(r['resultSchema']),'record.snapshot-pin');rm.require(isinstance(req['id'],str) and 1<=len(req['id'])<=128 and type(req['scenarioRevision']) is int and req['scenarioRevision']>=0,'record.scenario-id')
 with store.connect() as c:
  c.execute('BEGIN IMMEDIATE');current=c.execute('SELECT revision FROM workspace WHERE id=1').fetchone()[0]
  if current!=req['revision']:raise Conflict('작성본이 바뀌었습니다.')
  c.execute('CREATE TABLE IF NOT EXISTS record_scenarios (id TEXT PRIMARY KEY,revision INTEGER NOT NULL,body TEXT NOT NULL)');old=c.execute('SELECT revision FROM record_scenarios WHERE id=?',(req['id'],)).fetchone()
  if (old[0] if old else 0)!=req['scenarioRevision']:raise Conflict('가상 결과 집합이 다른 창에서 변경됐습니다.')
  record=dict(id=req['id'],scenarioRevision=req['scenarioRevision']+1,workspaceRevision=req['revision'],mappingRef=req['mappingRef'],snapshot=req['snapshot']);c.execute('INSERT INTO record_scenarios VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,body=excluded.body',(req['id'],record['scenarioRevision'],json.dumps(record,ensure_ascii=False)));return record
