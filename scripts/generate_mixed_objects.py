import sys,copy,json,tempfile,shutil
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'scripts'),str(R/'backend')]
import server,mixed_object_authoring as ma,record_fields as rf,record_mappings as rm,template_authoring as ta,publication,logical_preview

def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def seed():
 w=server.contracts.load(R/'fixtures/record-mappings/workspace.json');old=server.contracts.load(R/'fixtures/p4b/workspace.json');wanted={'mixed-plc-pressure','mixed-baseline','mixed-external-reference','mixed-line-code'}
 for row in old['sources']:
  if row['definition']['id'] not in wanted:continue
  row=copy.deepcopy(row);row['definition']['equipmentInstanceId']='record-line-b';w['sources'].append(row)
 w['connections']=[dict(c,equipmentInstanceId='record-line-b') for c in old['connections']]
 members=[]
 for id,typ,unit,role in [('actual','Double','kPa','measurement'),('target','Double','kPa','setpoint'),('baseline','Double','kPa','setpoint'),('external','Double','kPa','measurement'),('line_code','String',None,'status')]:members.append(dict(memberId=id,name=id,semanticId='urn:tyr:concept:combined.'+id,description='Synthetic combined object '+id,valueType=typ,unit=dict(status='known',code=unit) if unit else dict(status='not-applicable'),role=role,range=None))
 w['semantics'].append(dict(kind='semantic-definition',schemaVersion='2.2.0',id='combined-model',version='1.0.0',members=members));return w

def request(w):
 r=w['recordMappings'][1];bindings=[]
 for id,source,factor in [('actual','mixed-plc-pressure','0.1'),('target',None,'0.1'),('baseline','mixed-baseline','1'),('external','mixed-external-reference','1'),('line_code','mixed-line-code','1')]:
  value=dict(kind='record-field',recordMappingRef=rm.pin(r),fieldId='target',nullPolicy='reject',defaultValue=None) if source is None else dict(kind='source',sourceRef=dict(id=source,version='1.0.0'));tr=[]
  if factor!='1':tr.append(dict(op='linear',factor=factor,offset='0'))
  tr.append(dict(op='cast',to='String' if id=='line_code' else 'Double',overflow='error',rounding='half-even'));bindings.append(dict(memberPath=[dict(kind='member',memberId=id)],input=value,transform=tr))
 return dict(revision=2,modelRef=dict(id='combined-model',version='1.0.0'),equipmentInstanceId='record-line-b',applicationId='combined-pump',label='PLC·레코드·상수·외부 값 통합 객체',templateId='combined-pump-kit',templateVersion='1.0.0',authoredBy='fixture-author',reason='Synthetic mixed object acceptance',note='Offline declarations and virtual samples only',memberBindings=bindings,temporalPolicy=None)

def generate():
 out=R/'fixtures/mixed-objects';out.mkdir(exist_ok=True);ta.now=lambda:'2026-10-18T00:00:00Z'
 with tempfile.TemporaryDirectory() as tmp:
  st=server.Store(Path(tmp)/'editor.sqlite3');st.migrate(0,{});w=seed();st.save(1,w);save(out/'before.json',w);req=request(w);save(out/'request.json',req);plan=ma.compose(st,req,server.Conflict,server.build_package);assert plan['valid'],plan;result=ma.apply(st,dict(revision=2,draft=plan['draft'],planSha256=plan['planSha256']),server.Conflict,server.build_package);w=result['saved']['workspace'];save(out/'workspace.json',w);source=next(x['definition'] for x in w['sources'] if x['definition'].get('recordField'));samples={'mixed-plc-pressure':{'bytesHex':'b004'},source['id']:{'resultSet':server.contracts.load(R/'fixtures/record-mappings/snapshot.json')},'mixed-external-reference':{'typedValue':'101'}};save(out/'samples.json',samples);report=logical_preview.run(w,dict(id='reuse-combined-pump-target',version='1.0.0'),samples,3);assert report['quality']=='good',report;save(out/'preview.json',report);save(out/'oracle.json',dict(actual='120',target='95',baseline='100',external='101',line_code='LINE-A'));print('values',report['result'])
  _,_,errors=publication.build(w,out/'bundle','combined-fixture','combined-line','proposer',None,['reuse-combined-pump-mapping'],False,server.build_package);assert not errors,errors;shutil.copytree(out/'bundle',R.parent/'bifrost/core/src/test/resources/mapping-fixtures/mixed-objects')
if __name__=='__main__':generate()
