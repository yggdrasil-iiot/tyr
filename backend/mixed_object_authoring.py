"""Atomic mixed-object recipes using existing canonical templates and applications."""
import copy
import record_fields as rf,record_mappings as rm,mapping_templates as mt,template_authoring as ta,logical_structures as ls
class Snapshot:
 def __init__(self,w,revision):self.w=w;self.revision=revision
 def read(self):return dict(workspace=self.w,revision=self.revision)

def prepare(store,req,Conflict,build_package):
 mt.require(set(req)=={'revision','draft'} or set(req)=={'revision','draft','planSha256'},'mixed-object.plan-request');w=copy.deepcopy(ta.snapshot(store,req['revision'],Conflict)['workspace']);d=req['draft'];mt.require(set(d)=={'template','sources','application'},'mixed-object.draft')
 for row in d['sources']:
  s=row['definition'];mt.require(rf.is_field(s),'mixed-object.record-source-only');mt.require(not any(x['definition']['id']==s['id'] for x in w['sources']),'mixed-object.source-collision');w['sources'].append(copy.deepcopy(row))
 t=d['template'];mt.template_check(t);mt.require(not any(x['id']==t['id'] and x['version']==t['version'] for x in w.get('mappingTemplates',[])),'mixed-object.template-exists');w.setdefault('mappingTemplates',[]).append(copy.deepcopy(t));rf.check_workspace(w)
 app=d['application'];mt.require(app['templateRef']==mt.pin(t) and app['revision']==req['revision'],'mixed-object.application-pin');result,after=ta.plan(Snapshot(w,req['revision']),app,Conflict,build_package);return result,after

def compose(store,req,Conflict,build_package):
 required={'revision','modelRef','equipmentInstanceId','applicationId','label','templateId','templateVersion','authoredBy','reason','note','memberBindings','temporalPolicy'};mt.require(set(req)==required,'mixed-object.compose-request');w=copy.deepcopy(ta.snapshot(store,req['revision'],Conflict)['workspace']);model=ta.find(w['semantics'],req['modelRef']['id'],req['modelRef']['version']);layout=ls.layout(model);bindings={ls.path_key(x['memberPath']):x for x in req['memberBindings']};mt.require(len(bindings)==len(req['memberBindings']) and set(bindings)==set(layout['leaves']),'mixed-object.members-incomplete');new=[];ev={};mapping=[]
 for key,leaf in layout['leaves'].items():
  b=bindings[key];mt.require(set(b)=={'memberPath','input','transform'},'mixed-object.member');value=copy.deepcopy(b['input'])
  if value['kind']=='record-field':
   mt.require(set(value)=={'kind','recordMappingRef','fieldId','nullPolicy','defaultValue'},'mixed-object.field-input');id='record-field-'+mt.digest(value)[:24];s=rf.create(w,id,value['recordMappingRef'],value['fieldId'],value['nullPolicy'],value['defaultValue']);row=next((r for r in w['sources'] if r['definition']['id']==id),None)
   if row is None:
    row=dict(definition=s,label=s['rawAddressText'],origin='synthetic',note=req['note'],capturedAt=ta.now());w['sources'].append(row);new.append(copy.deepcopy(row))
   else:mt.require(row['definition']==s,'mixed-object.source-collision')
   value=dict(kind='source',sourceRef=dict(id=id,version=s['version']))
  mt.require(value['kind'] in ('source','graph'),'mixed-object.input-kind');mapping.append(dict(mappingId='member-'+mt.digest(leaf['memberPath'])[:12],memberPath=leaf['memberPath'],valueRef=value,transform=copy.deepcopy(b['transform']),outputUnit=leaf['member']['unit'],invalidValuePolicy='bad-quality',evidenceRefs=[]))
  if req['temporalPolicy'] is not None:mapping[-1]['temporalPolicy']=copy.deepcopy(req['temporalPolicy'])
 target=dict(kind='target-instance',schemaVersion='2.0.0',id='mixed-object-prototype-target',version='1.0.0',equipmentInstanceId=req['equipmentInstanceId'],label=req['label'],semanticDefinitionRef=req['modelRef'],evidenceRefs=[]);m=dict(kind='mapping-set',schemaVersion='2.12.0' if model['schemaVersion']=='2.12.0' else '2.3.0' if req['temporalPolicy'] is not None else '2.2.0',id='mixed-object-prototype-mapping',version='1.0.0',equipmentInstanceId=req['equipmentInstanceId'],targetInstanceRef=dict(id=target['id'],version=target['version']),mappings=mapping);mt.require(not any(x['id']==m['id'] for x in w['mappings']) and not any(x['id']==target['id'] for x in w['targets']),'mixed-object.prototype-collision');w['targets'].append(target);w['mappings'].append(m)
 template=ta.capture(Snapshot(w,req['revision']),dict(revision=req['revision'],mappingSetId=m['id'],templateId=req['templateId'],version=req['templateVersion'],label=req['label'],description=req['note'],reason=req['reason'],authoredBy=req['authoredBy']),Conflict)['template'];slots=[dict(slotId=s['slotId'],sourceRef=s['sourceRef']) for s in template['slots']];app=dict(revision=req['revision'],templateRef=mt.pin(template),applicationId=req['applicationId'],equipmentInstanceId=req['equipmentInstanceId'],targetLabel=req['label'],bindings=slots,authoredBy=req['authoredBy']);draft=dict(template=template,sources=new,application=app);return plan(store,dict(revision=req['revision'],draft=draft),Conflict,build_package)

def plan(store,req,Conflict,build_package):
 result,w=prepare(store,req,Conflict,build_package);return dict(kind='mixed-object-plan',revision=req['revision'],draft=req['draft'],planSha256=mt.digest(dict(revision=req['revision'],draft=req['draft'],canonicalPlan=result['planSha256'])),valid=result['valid'],findings=result['findings'],application=result['application'],persisted=False)

def apply(store,req,Conflict,build_package):
 mt.require('planSha256' in req,'mixed-object.plan-required');result,w=prepare(store,req,Conflict,build_package);token=mt.digest(dict(revision=req['revision'],draft=req['draft'],canonicalPlan=result['planSha256']));mt.require(result['valid'] and token==req['planSha256'],'mixed-object.plan-changed');return dict(saved=store.save(req['revision'],w),application=result['application'])
