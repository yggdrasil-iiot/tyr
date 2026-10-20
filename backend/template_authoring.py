"""Template authoring, binding assistance, read-only plans and explicit atomic updates."""
import copy,tempfile,json
from pathlib import Path
from datetime import datetime,timezone
import mapping_templates as mt
import publication,graph_reuse,change_review,preview,source_views

def now():return datetime.now(timezone.utc).isoformat()
def find(items,id,version=None):
 found=[d for d in items if d['id']==id and (version is None or d['version']==version)];mt.require(len(found)==1,'template.reference-missing');return found[0]
def snapshot(store,revision,Conflict):
 mt.require(type(revision) is int,'template.revision');s=store.read()
 if s['revision']!=revision:raise Conflict('작성본이 바뀌었습니다. 최신 저장본에서 다시 비교하세요.')
 mt.require(s['workspace'].get('workspaceVersion')=='2.0.0','먼저 객체 식별 마이그레이션을 완료하세요.');return s

def capture(store,req,Conflict):
 mt.require(set(req)=={'revision','mappingSetId','templateId','version','label','description','reason','authoredBy'},'template.request');w=snapshot(store,req['revision'],Conflict)['workspace'];m=find(w['mappings'],req['mappingSetId']);target=find(w['targets'],**dict(id=m['targetInstanceRef']['id'],version=m['targetInstanceRef']['version']));model=find(w['semantics'],target['semanticDefinitionRef']['id'],target['semanticDefinitionRef']['version']);graphs={};refs=set()
 def visit(v):
  if isinstance(v,dict):
   for k,x in v.items():
    if k=='sourceRef':refs.add((x['id'],x['version']))
    elif k=='graphRef':
     key=(x['id'],x['version'])
     if key not in graphs:graphs[key]=copy.deepcopy(find(w['graphs'],*key));visit(graphs[key])
    else:visit(x)
  elif isinstance(v,list):
   for x in v:visit(x)
 visit(m);slots=[]
 for i,ref in enumerate(sorted(refs),1):
  row=next((s for s in w['sources'] if (s['definition']['id'],s['definition']['version'])==ref),None);mt.require(row is not None,'template.source-missing');s=row['definition'];slots.append(dict(slotId='input-'+str(i),label=row.get('label') or s['id'],sourceRef=dict(id=ref[0],version=ref[1]),signature=mt.signature(s,{(r['definition']['id'],r['definition']['version']):r['definition'] for r in w['sources']})))
 versions=[t for t in w.get('mappingTemplates',[]) if t['id']==req['templateId']];previous=max(versions,key=lambda t:tuple(map(int,t['version'].split('.')))) if versions else None
 t=dict(kind='mapping-template',schemaVersion='2.19.0',id=req['templateId'],version=req['version'],label=req['label'],description=req['description'],reason=req['reason'],authoredBy=req['authoredBy'],authoredAt=now(),previousTemplateRef=None if previous is None else mt.pin(previous),slots=slots,model=mt.clean(model),target=mt.clean(target),graphs=[mt.clean(graphs[k]) for k in sorted(graphs)],mapping=mt.clean(m));mt.template_check(t)
 return dict(template=t,slotCount=len(slots),graphCount=len(graphs),outputCount=len(m['mappings']),persisted=False)

def save_template(store,req,Conflict):
 mt.require(set(req)=={'revision','template'},'template.request');w=copy.deepcopy(snapshot(store,req['revision'],Conflict)['workspace']);t=copy.deepcopy(req['template']);mt.template_check(t)
 mt.require(not any((d['id'],d['version'])==(t['id'],t['version']) for d in w.get('mappingTemplates',[])),'이미 저장한 버전입니다. 새 버전을 사용하세요.')
 w.setdefault('mappingTemplates',[]).append(t);mt.histories(w['mappingTemplates']+w.get('templateApplications',[]));return dict(saved=store.save(req['revision'],w),templatePin=mt.pin(t))

def candidates(w,t,equipment):
 result=[];source_docs={(r['definition']['id'],r['definition']['version']):r['definition'] for r in w['sources']}
 for slot in t['slots']:
  rows=[];tokens=set(slot['label'].lower().replace('-',' ').replace('_',' ').split())
  for row in w['sources']:
   s=row['definition']
   if s['equipmentInstanceId']!=equipment:continue
   differences=[k for k in slot['signature'] if mt.signature(s,source_docs)[k]!=slot['signature'][k]]
   if s['status']!='ready':differences.append('status')
   root=source_views.chain(s,source_docs)[-1];label=row.get('label') or s['id'];score=len(tokens & set((label+' '+s['id']).lower().replace('-',' ').replace('_',' ').split()))
   rows.append(dict(sourceRef=dict(id=s['id'],version=s['version']),label=label,address=s.get('rawAddressText') or str(s['access']),profile=s['accessProfileRef'],sampleSourceRef=dict(id=root['id'],version=root['version']),rawRepresentation=copy.deepcopy(root['rawRepresentation']),compatible=not differences,reasons=differences,score=score,signature=mt.signature(s,{(r['definition']['id'],r['definition']['version']):r['definition'] for r in w['sources']})))
  for candidate in rows:
   original=source_docs[(candidate['sourceRef']['id'],candidate['sourceRef']['version'])]
   if original.get('recordField'):candidate['recordField']=copy.deepcopy(original['recordField'])
  rows.sort(key=lambda r:(not r['compatible'],-r['score'],r['sourceRef']['id']));compatible=[r for r in rows if r['compatible']];recommendation=compatible[0]['sourceRef'] if compatible and (len(compatible)==1 or compatible[0]['score']>compatible[1]['score']) else None
  result.append(dict(slot=slot,candidates=rows,recommendation=recommendation))
 return result

def listing(store):
 snap=store.read();w=snap['workspace'];templates,apps=mt.histories(w.get('mappingTemplates',[])+w.get('templateApplications',[]));out=[]
 for id,versions in apps.items():
  a=versions[-1];latest=templates[a['templateRef']['id']][-1];old=find(templates[a['templateRef']['id']],a['templateRef']['id'],a['templateRef']['version']);changes=[dict(path=p,before=x,after=y,change=mode) for p,x,y,mode in change_review.leaves(old,latest) if p not in ('/authoredAt','/reason','/version','/previousTemplateRef')]
  out.append(dict(application=a,history=versions,latestTemplateRef=mt.pin(latest),updateAvailable=a['templateRef']!=mt.pin(latest),changes=changes))
 records=[]
 for r in w.get('recordMappings',[]):
  versions=templates[r['templateRef']['id']];latest=versions[-1];old=find(versions,r['templateRef']['id'],r['templateRef']['version']);changes=[dict(path=p,before=x,after=y,change=mode) for p,x,y,mode in change_review.leaves(old,latest) if p not in ('/authoredAt','/reason','/version','/previousTemplateRef')];records.append(dict(record=r,latestTemplateRef=mt.pin(latest),updateAvailable=r['templateRef']!=mt.pin(latest),changes=changes))
 return dict(kind='mapping-template-workspace',revision=snap['revision'],templates=w.get('mappingTemplates',[]),templatePins=[mt.pin(t) for t in w.get('mappingTemplates',[])],applications=out,recordApplications=records,execution='excluded',approvalAuthority='bifrost')

def binding_choices(store,req,Conflict):
 mt.require(set(req)=={'revision','templateRef','equipmentInstanceId'},'template.request');w=snapshot(store,req['revision'],Conflict)['workspace'];t=find(w.get('mappingTemplates',[]),req['templateRef']['id'],req['templateRef']['version']);mt.require(mt.pin(t)==req['templateRef'],'template.pin-mismatch');return dict(slots=candidates(w,t,req['equipmentInstanceId']))

def plan(store,req,Conflict,build_package):
 required={'revision','templateRef','applicationId','equipmentInstanceId','targetLabel','bindings','authoredBy'};mt.require(set(req) in (required,required|{'slotSamples'},required|{'planSha256'}),'template.request');snap=snapshot(store,req['revision'],Conflict);w=copy.deepcopy(snap['workspace']);t=find(w.get('mappingTemplates',[]),req['templateRef']['id'],req['templateRef']['version']);mt.require(mt.pin(t)==req['templateRef'],'template.pin-mismatch');mt.require(req['equipmentInstanceId'] in {e['id'] for e in w['equipment']},'template.equipment-missing')
 old=[a for a in w.get('templateApplications',[]) if a['applicationId']==req['applicationId']];previous=max(old,key=lambda a:a['revision']) if old else None;n=1 if previous is None else previous['revision']+1
 source_docs={(r['definition']['id'],r['definition']['version']):r['definition'] for r in w['sources']};bound=mt.source_closure([b['sourceRef'] for b in req['bindings']],source_docs);sources=[]
 for id,version in sorted(bound):sources.append(copy.deepcopy(find([r['definition'] for r in w['sources']],id,version)))
 a=dict(kind='template-application',schemaVersion='2.19.0',id='application-'+req['applicationId']+'-r'+str(n),version='1.0.0',applicationId=req['applicationId'],revision=n,previousApplicationRef=None if previous is None else mt.pin(previous),templateRef=mt.pin(t),equipmentInstanceId=req['equipmentInstanceId'],targetLabel=req['targetLabel'],bindings=copy.deepcopy(req['bindings']),sourceSnapshots=sources,generated=[{},{},{}],authoredBy=req['authoredBy'],authoredAt=now());a['generated']=mt.materialize(t,a)
 w.setdefault('templateApplications',[]).append(a)
 sections={'semantic-definition':'semantics','target-instance':'targets','value-graph':'graphs','mapping-set':'mappings'}
 for d in a['generated']:
  section=sections[d['kind']];existing=next((r for r in w[section] if r['id']==d['id']),None)
  mt.require(existing is None or previous is not None and any(g['id']==d['id'] and g==existing for g in previous['generated']),'template.output-collision')
  w[section]=[r for r in w[section] if r['id']!=d['id']]+[copy.deepcopy(d)]
 # Historical graph/model IDs are generation-specific and remain pinned for existing graph consumers.
 mt.check_workspace(w)
 with tempfile.TemporaryDirectory(prefix='tyr-template-plan-') as tmp:
  _,_,findings=publication.build(w,Path(tmp)/'bundle','template-preflight','template-preflight','template-author',None,[a['generated'][-1]['id']],False,build_package)
 try:
  import server
  server.check_state(w)
 except ValueError as e:findings.append({'ruleCode':'template.workspace-conflict','path':req['applicationId'],'detail':str(e)})
 blocking=[f for f in findings if f['ruleCode']!='mapping.input-unit-unknown-preserved'];changes=[]
 olddocs={} if previous is None else {d['id']:d for d in previous['generated']};newdocs={d['id']:d for d in a['generated']}
 for id in sorted(set(olddocs)|set(newdocs)):
  for path,x,y,mode in change_review.leaves(olddocs.get(id),newdocs.get(id)):changes.append(dict(artifactId=id,path=path,before=x,after=y,change=mode))
 data=dict(revision=req['revision'],templateRef=mt.pin(t),applicationId=a['applicationId'],applicationRevision=n,equipmentInstanceId=a['equipmentInstanceId'],targetLabel=a['targetLabel'],bindings=a['bindings'],previousApplicationRef=a['previousApplicationRef'],generated=a['generated']);token=mt.digest(data);previews=[]
 if 'slotSamples' in req:
  samples={};by={s['slotId']:s for s in t['slots']}
  for b in a['bindings']:
   text=req['slotSamples'].get(b['slotId'])
   if text is None or text=='':continue
   source=find(a['sourceSnapshots'],b['sourceRef']['id'],b['sourceRef']['version']);root=source_views.chain(source,{(s['id'],s['version']):s for s in a['sourceSnapshots']})[-1];raw=root['rawRepresentation'];value=text
   if not root.get('recordField') and raw['mode']=='typed' and raw['valueType']=='Boolean':mt.require(text in ('true','false'),'가상 Boolean은 true/false를 사용하세요.');value=text=='true'
   if by[b['slotId']]['signature']['fixedArray'] is not None:raise ValueError('배열 가상 입력은 저장 후 09 화면에서 확인하세요.')
   sample={'resultSet':json.loads(text)} if root.get('recordField') else {'typedValue' if raw['mode']=='typed' else 'bytesHex':value};mt.require(root['id'] not in samples or samples[root['id']]==sample,'같은 view 부모 소스에는 같은 가상 입력을 지정하세요.');samples[root['id']]=sample
  for binding in a['generated'][-1]['mappings']:
   import sample_quality
   ids=sample_quality.source_ids(w,binding);p=preview.run(w,a['generated'][-1]['id'],binding['mappingId'],{k:v for k,v in samples.items() if k in ids},req['revision']);previews.append(dict(mappingId=binding['mappingId'],memberPath=binding['memberPath'],preview=p))
 return dict(kind='mapping-template-plan',valid=not blocking,planSha256=token,application=a,changes=changes,findings=findings,previews=previews,persisted=False),w

def apply(store,req,Conflict,build_package):
 mt.require('planSha256' in req,'먼저 적용 전 비교를 실행하세요.');result,w=plan(store,req,Conflict,build_package);mt.require(result['valid'],'템플릿 적용 검증 오류를 먼저 해결하세요.');mt.require(req['planSha256']==result['planSha256'],'비교 결과가 바뀌었습니다. 다시 미리보세요.');return dict(saved=store.save(req['revision'],w),application=result['application'])
