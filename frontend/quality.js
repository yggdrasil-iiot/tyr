/* P3-D virtual DataValue policies and explicitly saved test scenarios. */
const policyFieldsD=(i,m)=>{
 const p=m?.temporalPolicy;
 return '<div class="temporal-policy"><h4>가상 시간·품질 정책</h4>'+select('time-enabled-'+i,'시간·품질 검증',[['off','값 검증만 · 기존 동작'],['on','명시적 시간·품질 정책']],p?'on':'off')+
 '<div id="time-fields-'+i+'" '+(p?'':'hidden')+' class="fields">'+
 select('time-basis-'+i,'검사할 시각',[['source','sourceTimestamp'],['server','serverTimestamp']],p?.timestampBasis||'source')+
 field('time-age-'+i,'허용 age (ms)',p?.maxAgeMs??1000,'number',true)+field('time-skew-'+i,'허용 skew (ms)',p?.maxSkewMs??100,'number',true)+
 select('time-uncertain-'+i,'uncertain 입력',[['propagate','uncertain 전파'],['reject','결과 거부']],p?.uncertainInput||'propagate')+
 select('time-assembly-'+i,'가상 조립 방식',[['latest','선택된 입력 묶음'],['trigger-sequence','trigger와 같은 sequence']],p?.assembly||'latest')+
 '<p>필수 입력 결측·bad·stale·미래 시각·skew 초과는 결과를 거부합니다. 동시 snapshot을 보장하지 않습니다.</p></div></div>';
};
const oldOperationsD=rowOperations;
rowOperations=function(i,member,mapping){return oldOperationsD(i,member,mapping)+policyFieldsD(i,mapping);};
document.addEventListener('change',e=>{
 if(e.target.id.startsWith('time-enabled-'))$('time-fields-'+e.target.id.slice('time-enabled-'.length)).hidden=e.target.value!=='on';
});
const oldCollectD=collectObjectMapping;
collectObjectMapping=function(){
 const result=oldCollectD();if(!v2Mode())return result;
 const previous=state.mappings.find(m=>m.id===result.id);
 let enabled=false;
 const target=state.targets.find(t=>t.id===result.targetInstanceRef.id),model=state.semantics.find(s=>s.id===target.semanticDefinitionRef.id);
 modelLeaves(model).forEach((member,i)=>{
 const b=result.mappings.find(b=>memberPathKey(b.memberPath)===memberPathKey(member._path));
 if(b&&val('time-enabled-'+i)==='on'){
 enabled=true;b.temporalPolicy={timestampBasis:val('time-basis-'+i),maxAgeMs:num('time-age-'+i),maxSkewMs:num('time-skew-'+i),uncertainInput:val('time-uncertain-'+i),missingInput:'reject',badInput:'propagate',assembly:val('time-assembly-'+i)};
 }
 });
 if(enabled||previous?.schemaVersion==='2.3.0')result.schemaVersion='2.3.0';
 return result;
};
function selectedBindingD(){
 const [mid,bid]=JSON.parse(val('preview-binding'));
 return {mid,bid,binding:state.mappings.find(m=>m.id===mid).mappings.find(b=>b.mappingId===bid)};
}
function withTemporalRequest(mid,bid,samples){
 const b=state.mappings.find(m=>m.id===mid).mappings.find(b=>b.mappingId===bid);
 if(!b.temporalPolicy)return {};
 previewSources(b).forEach((id,i)=>{
 if(Object.hasOwn(samples,id))samples[id]={value:samples[id],quality:val('virtual-quality-'+i),sourceTimestamp:val('virtual-source-time-'+i)||null,serverTimestamp:val('virtual-server-time-'+i)||null,sequence:val('virtual-sequence-'+i)||null};
 });
 return {evaluationContext:{at:val('evaluation-at'),triggerSequence:val('evaluation-sequence')||null}};
}
function collectRequestD(){
 const {mid,bid,binding}=selectedBindingD(),samples={};
 previewSources(binding).forEach((id,i)=>{
 const d=state.sources.find(s=>s.definition.id===id).definition,text=virtualInputTextB(id,i);
 if(text!=='')samples[id]=virtualSamplePayloadE(d,text);
 });
 return {revision,mappingSetId:mid,mappingId:bid,samples,...withTemporalRequest(mid,bid,samples)};
}
let scenarioRowsD=[],scenarioWorkspaceHashD='',scenarioWorkspaceRevisionD=-1;
function invalidateTemporalD(){$('preview-result').innerHTML='<p>시간·품질 입력이 변경됐습니다. 다시 미리보세요.</p>';}
function enhancePreviewD(){
 const {binding}=selectedBindingD(),p=binding.temporalPolicy;
 $('evaluation-fields-d')?.remove();
 if(p){
 const defaultAt='2026-10-17T10:00:00Z';
 $('preview-inputs').insertAdjacentHTML('beforebegin','<div id="evaluation-fields-d" class="fields"><h3>명시적 가상 기준</h3>'+field('evaluation-at','평가 기준 시각 (offset 필수)',defaultAt,'text',true)+field('evaluation-sequence','가상 trigger sequence (선택)','')+'<p>'+esc(p.timestampBasis+'Timestamp · age ≤ '+p.maxAgeMs+' ms · skew ≤ '+p.maxSkewMs+' ms · '+p.assembly)+' · 실제 수집 시각과 동시성 검증이 아닙니다.</p></div>');
 document.querySelectorAll('#preview-inputs .sample-input').forEach((el,i)=>{
 el.insertAdjacentHTML('beforeend',select('virtual-quality-'+i,'입력 품질',[['good','good'],['uncertain','uncertain'],['bad','bad']],'good')+
 field('virtual-source-time-'+i,'sourceTimestamp (비우면 미확인)',defaultAt)+field('virtual-server-time-'+i,'serverTimestamp (비우면 미확인)',defaultAt)+field('virtual-sequence-'+i,'입력 sequence (선택)',''));
 });
 $('evaluation-fields-d').oninput=invalidateTemporalD;
 }
 $('scenario-save-d').disabled=!p;
}
async function scenarioListD(){
 const response=await fetch('/api/scenarios'),r=await response.json();
 if(!response.ok)throw Error(r.error);
 scenarioRowsD=r.scenarios.filter(x=>x.scenario.kind==='preview-scenario');scenarioWorkspaceHashD=r.workspaceSha256;scenarioWorkspaceRevisionD=r.workspaceRevision;
 const picker=$('scenario-picker-d');if(picker)picker.innerHTML=options(scenarioRowsD.map(row=>[row.scenario.id,row.scenario.label+' · '+row.scenario.id+(row.stale?' · 작성본 변경됨':'')]),'');
}
const oldPreviewViewD=previewView;
previewView=function(){
 oldPreviewViewD();if(!val('preview-binding'))return;
 $('preview-form').insertAdjacentHTML('afterend','<section class="scenario-panel"><h3>가상 검증 시나리오</h3><p>입력·기준 시각을 별도 SQLite에 명시적으로 저장합니다. 실행 결과는 저장하지 않습니다. 작성본 hash가 바뀌면 이전 시나리오 재사용을 차단합니다.</p><div class="fields">'+field('scenario-id-d','시나리오 ID','')+field('scenario-label-d','시나리오 설명','')+select('scenario-picker-d','저장한 시나리오',[],'')+'</div><button type="button" id="scenario-save-d">가상 시나리오 저장</button> <button type="button" class="secondary" id="scenario-load-d">시나리오 불러오기</button> <button type="button" class="secondary" id="scenario-refresh-d">시나리오 목록 갱신</button></section>');
 const change=$('preview-binding').onchange;
 $('preview-binding').onchange=()=>{change();enhancePreviewD();};
 enhancePreviewD();scenarioListD().catch(e=>message(e.message,true));
 $('scenario-refresh-d').onclick=()=>scenarioListD().catch(e=>message(e.message,true));
 $('scenario-save-d').onclick=async()=>{
 if(busy||conflict)return;
 try{
 if(scenarioWorkspaceRevisionD!==revision)throw Error('작성본 revision이 다릅니다. 최신 작성본과 시나리오 목록을 다시 여세요.');
 const req=collectRequestD();if(!req.evaluationContext)throw Error('객체 매핑에서 시간·품질 정책을 먼저 저장하세요.');
 const map=state.mappings.find(m=>m.id===req.mappingSetId),old=scenarioRowsD.find(r=>r.scenario.id===val('scenario-id-d'));
 const scenario={kind:'preview-scenario',schemaVersion:previewSources(selectedBindingD().binding).some(id=>state.sources.find(r=>r.definition.id===id)?.definition.recordField)?'2.21.0':['2.4.0','2.12.0'].includes(map.schemaVersion)?'2.4.0':'2.3.0',id:val('scenario-id-d'),version:old?.scenario.version||'1.0.0',label:val('scenario-label-d'),mappingSetRef:ref(map),mappingId:req.mappingId,workspaceSha256:scenarioWorkspaceHashD,evaluationContext:req.evaluationContext,samples:req.samples};
 busy=true;const response=await fetch('/api/scenarios',{method:'POST',headers:{'Content-Type':'application/json','X-Tyr-Editor':'1'},body:JSON.stringify({workspaceRevision:revision,scenarioRevision:old?.scenarioRevision||0,scenario})}),r=await response.json();
 if(!response.ok)throw Error(r.error);
 await scenarioListD();message('가상 시나리오를 별도로 저장했습니다. 작성본 revision은 '+revision+'입니다.');
 }catch(e){message(e.message,true);}finally{busy=false;}
 };
 $('scenario-load-d').onclick=()=>{
 try{
 const row=scenarioRowsD.find(r=>r.scenario.id===val('scenario-picker-d'));if(!row)throw Error('저장한 시나리오를 선택하세요.');
 if(row.stale||scenarioWorkspaceRevisionD!==revision)throw Error('작성본이 달라졌습니다. 이 시나리오는 이전 정의의 검증 자료입니다.');
 const s=row.scenario;
 $('preview-binding').value=JSON.stringify([s.mappingSetRef.id,s.mappingId]);$('preview-binding').onchange();
 $('evaluation-at').value=s.evaluationContext.at;$('evaluation-sequence').value=s.evaluationContext.triggerSequence||'';
 previewSources(selectedBindingD().binding).forEach((id,i)=>{
 const sample=s.samples[id];$('virtual-'+i).value=sample?(sample.value?.bytesHex??(sample.value?.resultSet?JSON.stringify(sample.value.resultSet):sample.value?.typedValues?JSON.stringify(sample.value.typedValues):String(sample.value?.typedValue??''))):'';
 if(sample){$('virtual-quality-'+i).value=sample.quality;$('virtual-source-time-'+i).value=sample.sourceTimestamp||'';$('virtual-server-time-'+i).value=sample.serverTimestamp||'';$('virtual-sequence-'+i).value=sample.sequence||'';}
 });
 $('scenario-id-d').value=s.id;$('scenario-label-d').value=s.label;invalidateTemporalD();message('가상 시나리오를 불러왔습니다. 미리보기로 재평가하세요.');
 }catch(e){message(e.message,true);}
 };
};
const oldShowPreviewD=showPreview;
showPreview=function(r){
 oldShowPreviewD(r);
 if(!r.temporal)return;
 document.querySelector('#preview-result details').insertAdjacentHTML('beforeend','<p>가상 평가 기준 <code>'+esc(r.evaluationSha256)+'</code></p>');
 const t=r.temporal;
 $('preview-result').insertAdjacentHTML('afterbegin','<section><h3>가상 시간·품질 조립 · '+esc(t.assemblyQuality)+'</h3><p>기준 '+esc(t.evaluationContext?.at)+' · '+esc(t.policy.timestampBasis)+'Timestamp · skew '+esc(t.skewMs??'미확인')+' ms</p><p>원자적 snapshot 보장 없음 · 결과 품질 '+esc(r.dataValue.quality)+'</p>'+t.inputs.map(row=>'<p><strong>'+esc(row.sourceId)+'</strong><br>'+esc(row.quality??'missing')+' · age '+esc(row.ageMs??'미확인')+' ms · sequence '+esc(row.sequence??'미확인')+'<br>source '+esc(row.sourceTimestamp??'미확인')+'<br>server '+esc(row.serverTimestamp??'미확인')+'</p>').join('')+'</section>');
};
if(state)render();
