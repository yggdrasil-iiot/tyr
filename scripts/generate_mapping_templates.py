"""Regenerate synthetic template fixtures; no device IO."""
import sys,json,copy,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'scripts')]
import server,template_authoring as ta,mapping_templates as mt,publication

def generate():
 out=ROOT/'fixtures/mapping-templates';out.mkdir(exist_ok=True)
 ta.now=lambda:'2026-10-18T03:00:00Z'
 with tempfile.TemporaryDirectory() as tmp:
  store=server.Store(Path(tmp)/'editor.sqlite3');store.migrate(0,{});w=json.loads((ROOT/'fixtures/cross-graph/workspace.json').read_text(encoding='utf-8'));store.save(1,w)
  templates={}
  for profile,name in [('ab','pressure-kit')]:
   t=ta.capture(store,dict(revision=store.read()['revision'],mappingSetId='arithmetic-mapping-'+profile,templateId=name,version='1.0.0',label='압력 계산 표준 '+profile,description='합성 메모리맵의 공통 의미·그래프·정책',reason='오프라인 재사용 검증',authoredBy='fixture-author'),server.Conflict)['template'];ta.save_template(store,dict(revision=store.read()['revision'],template=t),server.Conflict);templates[profile]=t
  for profile in ['ab','ua','db','melsec']:
   original='ab';t=templates[original]
   req=dict(revision=store.read()['revision'],templateRef=mt.pin(t),applicationId='pump-'+profile,equipmentInstanceId='line-a-motor-'+profile,targetLabel='재사용 압력 객체 '+profile,bindings=[dict(slotId=s['slotId'],sourceRef=dict(id=s['sourceRef']['id'].replace('-'+original+'-','-'+profile+'-'),version='1.0.0')) for s in t['slots']],authoredBy='fixture-author')
   result,_=ta.plan(store,req,server.Conflict,server.build_package);assert result['valid'],result['findings'];ta.apply(store,dict(req,planSha256=result['planSha256']),server.Conflict,server.build_package)
  t=templates['ab'];t2=copy.deepcopy(t);t2.update(version='1.1.0',previousTemplateRef=mt.pin(t),reason='압력 차 대신 합산으로 변경하는 합성 영향 검증')
  changed=False
  for g in t2['graphs']:
   for n in g['nodes']:
    if n.get('op')=='subtract' and not changed:n['op']='add';changed=True
  assert changed;ta.save_template(store,dict(revision=store.read()['revision'],template=t2),server.Conflict)
  (out/'before-update.json').write_text(json.dumps(store.read()['workspace'],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  previous=[a for a in store.read()['workspace']['templateApplications'] if a['applicationId']=='pump-ua'][-1]
  req=dict(revision=store.read()['revision'],templateRef=mt.pin(t2),applicationId='pump-ua',equipmentInstanceId=previous['equipmentInstanceId'],targetLabel=previous['targetLabel'],bindings=previous['bindings'],authoredBy='fixture-author');result,_=ta.plan(store,req,server.Conflict,server.build_package);assert result['valid'],result['findings'];ta.apply(store,dict(req,planSha256=result['planSha256']),server.Conflict,server.build_package)
  w=store.read()['workspace'];(out/'workspace.json').write_text(json.dumps(w,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  (out/'cases.json').write_text(json.dumps(dict(samples={'actual':150,'target':50,'gain':2},expectedQuotient={'pump-ab':50,'pump-ua':100,'pump-db':50,'pump-melsec':50},template='pressure-kit',slotBoundary='decoded-type-unit-stage',fieldPoV='pending'),indent=2)+'\n',encoding='utf-8')
  publication.build(w,out/'bundle','template-fixture','template-fixture','fixture-author',None,['reuse-pump-'+p+'-mapping' for p in ['ab','ua','db','melsec']],False,server.build_package)
  dest=ROOT.parent/'bifrost/core/src/test/resources/mapping-fixtures/mapping-templates';shutil.copytree(out/'bundle',dest)
  print('generated',len(w['mappingTemplates']),'templates',len(w['templateApplications']),'applications; revision',store.read()['revision'])
if __name__=='__main__':generate()
