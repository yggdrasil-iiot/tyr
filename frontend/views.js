/* Explicit A07 source views. No IO, reverse transform or write execution. */
function viewChainIds(id) {
 const ids=[],seen=new Set();
 while(id){if(seen.has(id)||ids.length>=17)throw Error("view.cycle / view.depth");seen.add(id);ids.push(id);
 const d=state.sources.find(r=>r.definition.id===id)?.definition;if(!d)throw Error("view.reference-missing");id=d.viewOf?.id;}
 return ids;
}
const refsBeforeViews=refsFor,inputsBeforeViews=previewSources;
refsFor=function(ids){return refsBeforeViews([...new Set(ids.flatMap(viewChainIds))]);};
previewSources=function(binding){return [...new Set(inputsBeforeViews(binding).map(id=>viewChainIds(id).at(-1)))];};
const sourceBeforeViews=sourceView;
sourceView=function(){
 const d=editing?.kind==='source'?state.sources.find(r=>r.definition.id===editing.id)?.definition:null;
 if(d?.viewOf){tab='views';viewView();return;}sourceBeforeViews();
};
function viewView(){
 document.querySelectorAll('[data-tab]').forEach(b=>b.classList.toggle('active',b.dataset.tab==='views'));
 const row=editing?.kind==='source'?state.sources.find(r=>r.definition.id===editing.id):null,d=row?.definition?.viewOf?row.definition:null;
 const candidates=state.sources.filter(r=>r.definition.sourceKind!=='constant'&&r.definition.sourceKind!=='external-value'&&r.definition.sourceKind!=='solution-tag'&&r.definition.accessMode!=='write'&&r.definition.status==='ready'&&r.definition.id!==d?.id);
 shell('14 / 명시적 alias·전체 워드·비트 view','원본 접근·디코딩 snapshot과 부모 버전을 고정합니다. alias는 부모 값, bit는 디코딩된 정수의 LSB=0 비트입니다. 입력은 원본 한 번만 제공하며 시각·품질도 공유합니다. 16/32/64비트 정수 워드의 16단계 이내 읽기 view만 지원합니다.',
 '<form id="view-form"><div class="fields">'+field('view-id','view 소스 ID',d?.id||'','text',true)+field('view-version','정의 버전',d?.version||'1.0.0','text',true)+field('view-label','현장 신호명',row?.label||'','text',true)+select('view-parent','부모 소스 · 버전 고정',candidates.map(r=>[r.definition.id,r.definition.id+'@'+r.definition.version+' · '+r.definition.rawAddressText]),d?.viewOf.id)+select('view-kind','해석 관계',[['alias','alias · 부모 값 그대로'],['bit','bit view · LSB 기준']],d?.view.kind||'alias')+field('view-bit','bit index · 0부터 시작',d?.view.bitIndex??0,'number')+select('view-status','작성 상태',[['draft','초안'],['ready','정의 완료 · 검사 필요']],d?.status||'draft')+select('view-origin','근거 구분',[['synthetic','가상 자료'],['field','현장 선언']],row?.origin||'synthetic')+area('view-note','alias/view 관계의 근거',row?.note||'')+'</div><p id="view-parent-summary"></p><p>부모 수정 시 기존 view snapshot의 불일치를 보존하고 검토·발행을 차단합니다. 부모를 재선택해 근거와 매핑을 함께 검토하세요. view는 쓰기 목적지가 될 수 없습니다.</p><button type="submit">alias/view 정의 저장</button></form>',
 records(state.sources.filter(r=>r.definition.viewOf),'source',r=>r.definition.view.kind+' → '+r.definition.viewOf.id+'@'+r.definition.viewOf.version+' · '+r.definition.rawAddressText));
 if(d)$('view-id').readOnly=true;
 const hint=()=>{const p=state.sources.find(r=>r.definition.id===val('view-parent'))?.definition;$('view-bit').closest('label').hidden=val('view-kind')!=='bit';$('view-parent-summary').textContent=p?JSON.stringify({parent:ref(p),equipment:p.equipmentInstanceId,access:p.access,raw:p.rawRepresentation,unit:p.unit,view:p.view||null}):'부모를 선택하세요.';};
 $('view-kind').onchange=hint;$('view-parent').onchange=hint;hint();
 $('view-form').onsubmit=async event=>{
  event.preventDefault();try{
   if(!v2Mode())throw Error('명시적 view는 2.0 작성본에서 사용하세요.');
   const parent=state.sources.find(r=>r.definition.id===val('view-parent'))?.definition;if(!parent)throw Error('부모 소스가 필요합니다.');
   const id=val('view-id'),kind=val('view-kind'),def=structuredClone(parent);
   delete def.fixedArray;def.kind='source-definition';def.schemaVersion='2.10.0';def.id=id;def.version=val('view-version');def.sourceKind='plc';def.accessMode='read';def.status=val('view-status');def.viewOf=ref(parent);def.view=kind==='bit'?{kind,bitIndex:num('view-bit')}:{kind};
   if(kind==='bit')def.unit={status:'not-applicable'};
   def.evidenceRefs=[{artifactId:'manual-'+id,locator:{kind:'text-line',line:1}}];
   const next=structuredClone(state);upsert(next.sources,{definition:def,label:val('view-label'),note:val('view-note'),origin:val('view-origin'),capturedAt:new Date().toISOString()},def.id);await save(next);
  }catch(e){message(e.message,true);}
 };
}
const renderBeforeViews=render;
render=function(){if(tab==='views')viewView();else renderBeforeViews();};
const stageBeforeViews=previewStageValue;
previewStageValue=function(s){return s.stage.startsWith('view:')?previewValue({value:s.value,valueType:s.valueType}):stageBeforeViews(s);};

const infoBeforeViews=valueInfo;
valueInfo=function(v){
 const info=infoBeforeViews(v);if(info&&v?.kind==='source'){
  const chain=viewChainIds(v.sourceRef.id).map(id=>state.sources.find(r=>r.definition.id===id).definition);
  if(chain[0].viewOf){if(chain.some(d=>d.view?.kind==='bit'))info.type='Boolean';info.address+=' · '+chain.map(d=>d.id+'@'+d.version+(d.view?.kind==='bit'?'[bit '+d.view.bitIndex+']':'')).join(' → ');}
 }return info;
};
