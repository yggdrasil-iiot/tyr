
/* P4-B source metadata and direction definitions; no IO execution. */
Object.assign(profiles,{'constant-v1':['상수 정의','constant'],'solution-tag-v1':['솔루션 태그','solution-tag'],'external-value-v1':['외부 값','external-value']});
let mixedKindDraft='plc';
const sourceBeforeMixed=sourceView,draftBeforeMixed=draftSource,contextBeforeMixed=contextView;
const modeOptions=[['read','읽기'],['write','쓰기 정의 전용'],['read-write','읽기·쓰기 정의']];
const sourceKindOptions=[['plc','PLC'],['constant','상수'],['solution-tag','솔루션 태그'],['external-value','외부 값 · 실행 제외']];
contextView=function(){contextBeforeMixed();for(const o of [...$('connection-profile').options])if(o.value&&!['ab-logix-symbol-v1','s7-1500-opcua-v1','s7-300-db-v1','melsec-device-v1'].includes(o.value))o.remove();};
sourceView=function(){
 const row=editing?.kind==='source'?state.sources.find(r=>r.definition.id===editing.id):null,d=row?.definition,kind=d?.sourceKind|| (row?'plc':mixedKindDraft);
 if(kind==='plc'){
  sourceBeforeMixed();
  for(const o of [...$('source-profile').options])if(o.value&&['constant-v1','solution-tag-v1','external-value-v1'].includes(o.value))o.remove();
  $('source-form').insertAdjacentHTML('afterbegin','<div class="fields">'+select('mixed-source-kind','소스 종류',sourceKindOptions,'plc')+select('mixed-source-mode','접근 방향 · 실행 권한 아님',modeOptions,d?.accessMode||'read')+'</div>');
 }else{
  const a=d?.access||{};
  let access=kind==='constant'?area('mixed-value','상수 값 · 숫자는 십진수 문자열, Boolean은 true/false',a.value===undefined?'0':String(a.value)):
   kind==='solution-tag'?field('mixed-instance','솔루션 인스턴스 ID',a.solutionInstanceRef||'solution-a','text',true)+field('mixed-solution','솔루션 이름',a.solutionName||'Synthetic HMI','text',true)+field('mixed-solution-version','솔루션 버전',a.solutionVersion||'1.0','text',true)+field('mixed-tag','태그 경로',a.tagPath||'Tank.Setpoint','text',true):
   field('mixed-provider','외부 제공자 참조 ID',a.providerRef||'provider-a','text',true)+field('mixed-key','값 키',a.valueKey||'pressure.reference','text',true)+select('mixed-language','보존할 표현식 종류',[['none','표현식 없음'],['opaque','미해석 원문'],['sql','SQL 원문 · 실행 제외']],a.expressionLanguage||'none')+area('mixed-expression','표현식 원문 · 실행하지 않음',a.expression||'');
  shell('02 / 혼합 소스 정의','상수는 정의값을 사용합니다. 솔루션 태그·외부 값은 가상 Typed 입력만 사용하며 솔루션 접속과 SQL을 실행하지 않습니다.','<h2>소스 정의</h2><form id="source-form"><div class="fields">'+select('mixed-source-kind','소스 종류',sourceKindOptions,kind)+field('source-id','소스 ID',d?.id||'','text',true)+field('source-label','현장 신호명',row?.label||'','text',true)+select('mixed-equipment','소속 설비',state.equipment.map(e=>[e.id,e.label]),d?.equipmentInstanceId)+select('mixed-source-mode','접근 방향 · 실행 권한 아님',kind==='solution-tag'?modeOptions:[modeOptions[0]],d?.accessMode||'read')+select('source-status','작성 상태',[['draft','초안'],['ready','정의 완료 · 제출 전 검사']],d?.status||'draft')+access+select('mixed-type','값 타입',['Double','Int32','Boolean','String'].map(t=>[t,t]),d?.rawRepresentation.valueType||'Double')+select('inputStage','입력 값 단계',[['raw','원시값'],['already-engineered','공학값']],d?.inputStage||'already-engineered')+select('source-unit','입력 단위',unitOptions,unitValue(d?.unit)||'kPa')+select('evidence-origin','근거 구분',[['field','현장 선언'],['synthetic','가상 자료']],row?.origin||'synthetic')+area('source-note','정의·출처·검토 근거',row?.note||'')+'</div><button type="submit">접근 정의 저장</button></form>',records(state.sources,'source',r=>(r.label||r.definition.id)+' · '+profiles[r.definition.accessProfileRef][0]+' · '+r.definition.rawAddressText+' · '+(r.definition.accessMode||'read')));
  if(d)$('source-id').readOnly=true;
 }
 $('mixed-source-kind').onchange=()=>{mixedKindDraft=val('mixed-source-kind');if(row&&mixedKindDraft!==kind){message('기존 정의의 종류 변경은 새 소스 ID로 작성하세요.',true);$('mixed-source-kind').value=kind;return;}sourceView();dirty=true;};
};
draftSource=function(){
 const kind=$('mixed-source-kind')?val('mixed-source-kind'):'plc';
 if(kind==='plc'){const r=draftBeforeMixed();r.definition={...r.definition,schemaVersion:'2.7.0',sourceKind:'plc',accessMode:val('mixed-source-mode')||'read'};return r;}
 const id=val('source-id'),old=state.sources.find(r=>r.definition.id===id),type=val('mixed-type'),mode=val('mixed-source-mode');
 let access,address,profile;
 if(kind==='constant'){const text=type==='String'?$('mixed-value').value:val('mixed-value');if(type==='Boolean'&&!['true','false'].includes(text))throw Error('Boolean 상수는 true 또는 false로 입력하세요.');access={kind,value:type==='Boolean'?text==='true':text};address='constant:'+id;profile='constant-v1';}
 else if(kind==='solution-tag'){access={kind,solutionInstanceRef:val('mixed-instance'),solutionName:$('mixed-solution').value,solutionVersion:$('mixed-solution-version').value,tagPath:$('mixed-tag').value};address=access.solutionInstanceRef+':'+access.tagPath;profile='solution-tag-v1';}
 else{access={kind,providerRef:val('mixed-provider'),valueKey:$('mixed-key').value,expressionLanguage:val('mixed-language'),expression:$('mixed-expression').value===''?null:$('mixed-expression').value};address=access.providerRef+':'+access.valueKey;profile='external-value-v1';}
 return {definition:{kind:'source-definition',schemaVersion:'2.7.0',id,version:old?.definition.version||'1.0.0',equipmentInstanceId:val('mixed-equipment'),connectionProfileRef:null,accessProfileRef:profile,sourceKind:kind,accessMode:mode,status:val('source-status'),rawAddressText:address,addressRadix:null,access,rawRepresentation:{mode:'typed',valueType:type},inputStage:val('inputStage'),unit:unit('source-unit'),evidenceRefs:[{artifactId:'manual-'+id,locator:{kind:'text-line',line:1}}],viewOf:null},label:val('source-label'),note:val('source-note'),origin:val('evidence-origin'),capturedAt:new Date().toISOString()};
};
const stageBeforeMixed=previewStageValue;
previewStageValue=function(s){return s.stage==="constant-definition"?String(s.detail.definitionValue):stageBeforeMixed(s);};
const optionsBeforeMixed=valueOptions,inputsBeforeMixed=previewSources,previewBeforeMixed=previewView;
valueOptions=function(e){return optionsBeforeMixed(e).filter(([key])=>{const [kind,id]=JSON.parse(key);return kind!=='source'||state.sources.find(r=>r.definition.id===id)?.definition.accessMode!=='write';});};
previewSources=function(b){return inputsBeforeMixed(b).filter(id=>state.sources.find(r=>r.definition.id===id)?.definition.sourceKind!=='constant');};
previewView=function(){
 previewBeforeMixed();
 const show=()=>{
  if(!$('preview-binding')?.value)return;
  const [mid,bid]=JSON.parse(val('preview-binding')),b=state.mappings.find(m=>m.id===mid).mappings.find(b=>b.mappingId===bid),ids=inputsBeforeMixed(b),mixed=state.sources.filter(r=>ids.includes(r.definition.id)&&r.definition.sourceKind&&r.definition.sourceKind!=='plc');
  $('mixed-preview-info')?.remove();
  $('preview-inputs').insertAdjacentHTML('beforebegin','<section id="mixed-preview-info"><h3>읽기 방향 · 소스 → 공통 의미</h3><p>쓰기 정의는 별도이며 자동 역변환·SQL·쓰기 실행을 하지 않습니다.</p>'+mixed.map(r=>'<details><summary>'+esc(r.label||r.definition.id)+' · '+esc(r.definition.sourceKind)+'</summary><pre>'+esc(JSON.stringify(r.definition.access,null,2))+'</pre></details>').join('')+'</section>');
 };
 const old=$('preview-binding').onchange;$('preview-binding').onchange=()=>{old?.();show();};show();
};
function writeView(){
 if(!v2Mode())return migrationView();
 const d=editing?.kind==='write'?state.writes?.find(w=>w.id===editing.id):null;
 const choices=state.targets.flatMap(t=>{const sem=state.semantics.find(s=>s.id===t.semanticDefinitionRef.id);return sem.members.filter(m=>!['Structure','StructureArray'].includes(m.valueType)).map(m=>[JSON.stringify([t.id,m.memberId]),t.label+' / '+m.name+' · '+m.valueType+' / '+unitValue(m.unit)]);});
 const dst=state.sources.filter(r=>['write','read-write'].includes(r.definition.accessMode)&&['plc','solution-tag'].includes(r.definition.sourceKind));
 shell('11 / 읽기·쓰기 정의','읽기는 06 객체 매핑에서 소스 → 의미로 작성합니다. 여기서는 의미 → 목적지의 변환을 별도로 선언합니다. 정의 저장은 실행 권한이나 장치 쓰기를 뜻하지 않습니다.','<h2>쓰기 방향 정의 · 실행 제외</h2><form id="write-definition-form"><div class="fields">'+field('write-id','쓰기 정의 ID',d?.id||'','text',true)+select('write-member','보낼 객체 프로퍼티',choices,d?JSON.stringify([d.targetInstanceRef.id,d.memberPath[0].memberId]):'')+select('write-destination','쓰기 목적지',dst.map(r=>[r.definition.id,(r.label||r.definition.id)+' · '+r.definition.rawAddressText+' · '+r.definition.rawRepresentation.valueType+' / '+unitValue(r.definition.unit)]),d?.destinationRef.id)+area('write-transform','쓰기 방향 변환 JSON · 자동 역변환 없음',JSON.stringify(d?.transform||[],null,2))+'</div><p>linear/unit-convert/cast만 허용합니다. 목적지 원시 타입·단위에 맞춰 명시하세요. 범위·반올림은 선언만 검증하며 값을 전송하거나 직렬화하지 않습니다.</p><button type="submit">쓰기 정의 저장 · 실행하지 않음</button></form>',records(state.writes||[],'write',w=>w.targetInstanceRef.id+'/'+w.memberPath[0].memberId+' → '+w.destinationRef.id+' · execution excluded'));
 if(d)$('write-id').readOnly=true;
}
const renderBeforeMixed=render;
render=function(){if(tab==='writes'){document.querySelectorAll('[data-tab]').forEach(b=>b.classList.toggle('active',b.dataset.tab===tab));writeView();}else renderBeforeMixed();};
document.addEventListener('submit',async event=>{
 if(event.target.id!=='write-definition-form')return;event.preventDefault();if(busy||conflict)return;
 try{
  const [tid,mid]=JSON.parse(val('write-member')),target=state.targets.find(t=>t.id===tid),dst=state.sources.find(r=>r.definition.id===val('write-destination')).definition,id=val('write-id'),old=state.writes?.find(w=>w.id===id);
  if(old&&(editing?.kind!=='write'||editing.id!==id))throw Error('기존 쓰기 정의를 선택해 편집하세요.');
  const refs=[...new Map([...target.evidenceRefs,...dst.evidenceRefs].map(r=>[JSON.stringify(r),r])).values()];
  const d={kind:'write-definition',schemaVersion:'2.7.0',id,version:old?.version||'1.0.0',equipmentInstanceId:target.equipmentInstanceId,targetInstanceRef:ref(target),memberPath:[{kind:'member',memberId:mid}],destinationRef:ref(dst),transform:JSON.parse(val('write-transform')),execution:'excluded',invalidValuePolicy:'reject',evidenceRefs:refs};
  const next=structuredClone(state);next.writes??=[];const i=next.writes.findIndex(w=>w.id===id);if(i<0)next.writes.push(d);else next.writes[i]=d;await save(next);
 }catch(e){message(e.message,true);}
});
if(state)render();
