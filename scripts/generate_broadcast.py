import sys,copy,json,tempfile,shutil
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'backend'),str(R/'scripts')]
import server,broadcast_authoring as ba,broadcast_preview as bp,record_mappings as rm,template_authoring as ta,publication

def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def generate():
 out=R/'fixtures/broadcast';out.mkdir(exist_ok=True);rm.require(not (out/'bundle').exists(),'Generated bundle already exists; preserve the fixture and use a new output directory');ta.now=lambda:'2026-10-18T00:00:00Z';ba.now=ta.now
 w=server.contracts.load(R/'fixtures/mixed-objects/before.json');req=server.contracts.load(R/'fixtures/mixed-objects/request.json');record=w['recordMappings'][0];members=[]
 for b in req['memberBindings']:
  v=b['input'];v=dict(kind='field',fieldId=v['fieldId'],nullPolicy=v['nullPolicy'],defaultValue=v['defaultValue']) if v['kind']=='record-field' else dict(kind='common',sourceRef=v['sourceRef']);members.append(dict(memberPath=b['memberPath'],input=v,transform=b['transform']))
 req=dict(revision=2,id='broadcast-pumps',version='1.0.0',label='레코드별 목표 + 공통 PLC·상수·외부 값',equipmentInstanceId='record-line-b',resultSchema=copy.deepcopy(record['resultSchema']),output=dict(mode='array',zeroPolicy='empty',manyPolicy='all',maxRows=16,order='canonical-key-utf8'),selection=dict(kind='all',key=[]),authoredBy='fixture-author',reason='Synthetic bounded broadcast',note='Offline only; common values supplied once',origin='synthetic',templateRef=None,modelRef=dict(id='combined-model',version='1.0.0'),memberBindings=members,slotBindings=[],templateId='broadcast-pump-kit',templateVersion='1.0.0',commonPolicy=dict(mode='single-virtual-frame',maxAgeMs=1000,maxSkewMs=500,uncertainInput='propagate'),rowErrorPolicy='reject-all')
 save(out/'before.json',w);save(out/'request.json',req)
 with tempfile.TemporaryDirectory() as tmp:
  st=server.Store(Path(tmp)/'editor.sqlite3');st.migrate(0,{});st.save(1,w);p=ba.compose(st,req,server.Conflict);result=__import__('record_authoring').apply(st,dict(revision=2,draft=p['draft'],planSha256=p['planSha256']),server.Conflict);w=result['saved']['workspace'];save(out/'workspace.json',w);r=w['recordMappings'][-1];snapshot=server.contracts.load(R/'fixtures/record-mappings/snapshot.json');snapshot['resultSetRef']=rm.pin(r['resultSchema']);save(out/'snapshot.json',snapshot);samples={id:dict(value=value,sourceTimestamp=snapshot['capturedAt'],serverTimestamp=snapshot['capturedAt'],quality='good',sequence=None) for id,value in [('mixed-plc-pressure',dict(bytesHex='b004')),('mixed-external-reference',dict(typedValue='101'))]};save(out/'common-samples.json',samples);p=bp.run(w,r['id'],r['version'],snapshot,samples,3,'2026-10-18T00:00:00.500Z');save(out/'preview.json',p);assert p['valid'],p;save(out/'static-projection.json',rm.compile(r,w['mappingTemplates'][-1]));publication.build(w,out/'bundle','broadcast-fixture','broadcast-line','proposer',None,['record:'+r['id']+'@'+r['version']],False,server.build_package)
 dest=R.parent/'bifrost/core/src/test/resources/mapping-fixtures/broadcast';shutil.copytree(out/'bundle',dest,dirs_exist_ok=True)
 print('Broadcast fixture:',p['result'])
if __name__=='__main__':generate()
