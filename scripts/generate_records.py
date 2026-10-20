"""Deterministic offline record contract/fixture, no SQL/provider calls."""
import sys,copy,json,tempfile,shutil
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'scripts'),str(R/'backend')]
import server,record_authoring as ra,record_mappings as rm,record_preview as rp,mapping_templates as mt,publication

def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def seed():
 model=dict(kind='semantic-definition',schemaVersion='2.2.0',id='record-pressure-model',version='1.0.0',members=[])
 for id,typ,unit,role in [('asset','String','not-applicable','status'),('pressure','Double','kPa','measurement'),('target','Double','kPa','setpoint'),('running','Boolean','not-applicable','status')]:model['members'].append(dict(memberId=id,name=id,semanticId='urn:tyr:concept:record.'+id,description='Synthetic record '+id,valueType=typ,unit={'status':'not-applicable'} if unit=='not-applicable' else {'status':'known','code':unit},role=role,range=None))
 return dict(workspaceVersion='2.0.0',equipment=[dict(id='record-line-a',label='합성 설비 A'),dict(id='record-line-b',label='합성 설비 B')],connections=[],sources=[],semantics=[model],targets=[],graphs=[],mappings=[])
def recipe():
 fs=[]
 for id,typ,u,stage,nullable in [('asset','String','not-applicable','already-engineered',False),('pressure','Double','Pa','raw',True),('target','Int32','kPa','raw',False),('running','Boolean','not-applicable','already-engineered',False)]:fs.append(dict(fieldId=id,name=id,valueType=typ,unit={'status':'not-applicable'} if u=='not-applicable' else {'status':'known','code':u},inputStage=stage,nullable=nullable))
 members=[]
 for f in fs:
  tr=[]
  if f['fieldId']=='pressure':tr.append(dict(op='unit-convert',**{'from':'Pa','to':'kPa'}))
  if f['fieldId']=='target':tr.append(dict(op='linear',factor='0.1',offset='0'))
  tr.append(dict(op='cast',to='Double' if f['fieldId'] in ('pressure','target') else f['valueType'],overflow='error',rounding='half-even'));members.append(dict(memberPath=[dict(kind='member',memberId=f['fieldId'])],fieldId=f['fieldId'],transform=tr))
 return dict(revision=2,id='pressure-records',version='1.0.0',label='설비별 압력 결과 집합',equipmentInstanceId='record-line-a',resultSchema=dict(id='pressure-result',version='1.0.0',providerRef='virtual-db',valueKey='asset-pressure',query=dict(language='sql',text='SELECT asset, pressure, target, running FROM declared_view'),fields=fs,keyFields=['asset'],unknownFields='preserve'),output=dict(mode='array',zeroPolicy='empty',manyPolicy='all',maxRows=16,order='canonical-key-utf8'),selection=dict(kind='all',key=[]),authoredBy='fixture-author',reason='가상 결과 집합 수용 검증',note='합성 선언. 실제 DB/schema 정답 아님.',origin='synthetic',templateRef=None,modelRef=dict(id='record-pressure-model',version='1.0.0'),memberBindings=members,slotBindings=[dict(fieldId='pressure',nullPolicy='default',defaultValue='0')],templateId='pressure-record-template',templateVersion='1.0.0')
def generate():
 out=R/'fixtures/record-mappings';out.mkdir(exist_ok=True);ra.now=lambda:'2026-10-18T00:00:00Z'
 with tempfile.TemporaryDirectory() as tmp:
  store=server.Store(Path(tmp)/'editor.sqlite3');store.migrate(0,{});store.save(1,seed());req=recipe();plan=ra.compose(store,req,server.Conflict);ra.apply(store,dict(revision=2,draft=plan['draft'],planSha256=plan['planSha256']),server.Conflict);w=store.read()['workspace'];record=w['recordMappings'][0]
  req=copy.deepcopy(req);req.update(revision=3,id='pressure-object',equipmentInstanceId='record-line-b',templateRef=record['templateRef'],modelRef=None,memberBindings=[],slotBindings=record['bindings'],output=dict(mode='object',zeroPolicy='null',manyPolicy='reject',maxRows=1,order='canonical-key-utf8'),selection=dict(kind='key',key=['A-002']));plan=ra.compose(store,req,server.Conflict);ra.apply(store,dict(revision=3,draft=plan['draft'],planSha256=plan['planSha256']),server.Conflict);w=store.read()['workspace'];save(out/'workspace.json',w);save(out/'recipe.json',recipe())
  snapshot=dict(kind='virtual-result-set',schemaVersion='2.20.0',resultSetRef=rm.pin(record['resultSchema']),capturedAt='2026-10-18T00:00:00Z',quality='good',rows=[dict(asset='A-002',pressure='123450',target='950',running=True,unmapped_note='원본 보존'),dict(asset='A-001',pressure='100000',target='900',running=False)]);save(out/'snapshot.json',snapshot);save(out/'oracle.json',dict(array=[dict(asset='A-001',pressure='100.0',target='90.0',running=False),dict(asset='A-002',pressure='123.45',target='95.0',running=True)],object=dict(asset='A-002',pressure='123.45',target='95.0',running=True),zeroArray=[],zeroObject=None))
  for r in w['recordMappings']:
   report=rp.run(w,r['id'],r['version'],snapshot,4,'2026-10-18T00:00:01Z');assert report['valid'],report;save(out/(r['id']+'-preview.json'),report)
  nominal=server.contracts.load(out/'oracle.json');save(out/'oracle.json',dict(nominalEngineeringValues=nominal,finalArray=[dict(asset='A-001',pressure='100',target='90',running=False),dict(asset='A-002',pressure='123.4500000000000028421709430404007434844970703125',target='95',running=True)],finalObject=dict(asset='A-002',pressure='123.4500000000000028421709430404007434844970703125',target='95',running=True),expectedQuality='uncertain',reason='Final Double cast reports exact binary64 values and precision loss.'));save(out/'static-projections.json',[rm.compile(r,next(t for t in w['mappingTemplates'] if mt.pin(t)==r['templateRef'])) for r in w['recordMappings']]);(R.parent/'bifrost/core/src/test/resources/record-static-projections.json').write_bytes((out/'static-projections.json').read_bytes())
  publication.build(w,out/'bundle','record-fixture','record-line','proposer',None,['record:'+r['id']+'@'+r['version'] for r in w['recordMappings']],False,server.build_package);shutil.copytree(out/'bundle',R.parent/'bifrost/core/src/test/resources/mapping-fixtures/record-mappings');print('record fixtures: 2 projections, 1 shared template, 0 provider calls')
if __name__=='__main__':generate()
