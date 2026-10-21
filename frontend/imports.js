
/* P4-A file-first authoring. Raw files stay local; no device client. */
let importDraft=null,importRequest=null;
const hintBeforeImport=ruleHint,sourceViewBeforeImport=sourceView;
ruleHint=function(rule){return ({"import.unresolved":"가져온 자료에 미해석 항목이 남아 있습니다. 10 파일 가져오기에서 원문과 해석 오류를 확인하세요.","source.not-ready":"가져온 정의는 초안입니다. 원본과 접근 필드·디코딩 가정을 검토한 뒤 정의 완료로 바꾸세요."})[rule]||hintBeforeImport(rule);};
sourceView=function(){
 sourceViewBeforeImport();
 const row=editing?.kind==="source"?state.sources.find(s=>s.definition.id===editing.id):null;
 if(row?.importRef){const batch=state.imports.find(b=>b.id===row.importRef.batchId),ob=batch.observations.find(o=>o.id===row.importRef.observationId);
 document.querySelector("#source-form").insertAdjacentHTML("afterbegin",'<section><h3>가져온 원본 근거</h3><p>'+esc(batch.filename)+' · '+esc(batch.id)+' · SHA-256 <code>'+esc(batch.sha256)+'</code></p>'+importObservation(ob)+'</section>');}
};
const renderBeforeImport=render,draftBeforeImport=draftSource;
draftSource=function(){
 const row=draftBeforeImport(),old=state.sources.find(x=>x.definition.id===row.definition.id);
 if(old?.importRef){row.importRef=structuredClone(old.importRef);row.definition.evidenceRefs=structuredClone(old.definition.evidenceRefs);}
 return row;
};
function importObservation(o){
 return '<details><summary>'+esc(o.id)+' · '+esc(o.draft?.rawAddressText||'미해석')+' · '+esc(o.issues.join(', ')||'초안 검토 필요')+'</summary><p>원본 위치 <code>'+esc(JSON.stringify(o.locator))+'</code></p><p>해석 경로 <code>'+esc(JSON.stringify(o.derivation))+'</code></p><pre>'+esc(JSON.stringify({originalColumns:o.originalColumns,raw:o.raw,template:o.template,assumptions:o.assumptions,draft:o.draft},null,2))+'</pre></details>';
}
function importView(){
 if(!v2Mode())return migrationView();
 const batches=state.imports||[];
 $('view').innerHTML='<p class="step">10 / 파일에서 접근 정의 초안 만들기</p><p>원본 파일과 미해석 항목을 보존합니다. 엑셀 첫 행은 열 이름입니다. 설정 JSON은 tyr-config-v1 교환 형식입니다. 가져오기는 승인 또는 장치 접속을 수행하지 않습니다.</p><section class="card"><div id="import-fields" class="fields">'+
 field('import-id','가져오기 ID','field-'+Date.now(),'text',true)+select('import-equipment','소속 설비',state.equipment.map(e=>[e.id,e.label]))+
 select('import-format','파일 형식',[['xlsx','Excel .xlsx'],['tyr-config-json-v1','Týr 설정 JSON v1']],'xlsx')+
 '<label>원본 파일 (최대 512 KiB)<input type="file" id="import-file" accept=".xlsx,.json"></label>'+
 area('import-columns','엑셀 열 대응 JSON · 원본 이름 → 표준 이름','{}')+
 select('import-origin','자료 출처',[['field','현장 자료'],['synthetic','가상 자료']],'field')+
 '</div><details><summary>지원 열과 템플릿·alias 작성 규칙</summary><p>id, kind(source/template/alias), profile, address, type, unit, stage, byteOrder, wordOrder, width, namespaceUri, identifierType, label.</p><p>template: base, stride, count 및 address의 {offset}/{index}; overrides는 인덱스별 JSON. alias: target에 source 또는 전개한 template ID. MELSEC D1000 / S7 DB1.DBB0 / AB Motor.Speed / OPC UA는 address와 namespaceUri를 별도 명시합니다. type은 UInt16/Int32/Float32 등의 계약 타입입니다.</p><p>모르는 열·수식·지원하지 않는 주소식은 미해석으로 남깁니다. PDF·.xls·벤더 전용 설정 형식은 아직 지원하지 않습니다.</p></details><button id="import-preview">파일 해석 미리보기</button><div id="import-review"></div></section>'+
 '<section class="card"><h2>보존한 가져오기 · '+batches.length+'건</h2>'+batches.map((b,i)=>'<details><summary>'+esc(b.filename)+' · '+esc(b.id)+' · '+b.observations.length+'개 관측</summary><p>SHA-256 <code>'+esc(b.sha256)+'</code></p><p>'+esc(b.fileIssue||'원본 보존됨')+'</p><button data-import-download="'+i+'">원본 파일 내려받기</button>'+b.observations.map(importObservation).join('')+'</details>').join('')+'</section>';
 $('import-preview').onclick=async()=>{
  if(busy||conflict)return;
  busy=true;$('import-preview').disabled=true;
  try{
   const file=$('import-file').files[0];if(!file||file.size>524288)throw Error('512 KiB 이하 파일을 선택하세요.');
   const bytes=new Uint8Array(await file.arrayBuffer());let binary='';for(const b of bytes)binary+=String.fromCharCode(b);
   importRequest={id:val('import-id'),filename:file.name,format:val('import-format'),equipmentInstanceId:val('import-equipment'),capturedAt:new Date().toISOString(),origin:val('import-origin'),bytesBase64:btoa(binary),columnMap:JSON.parse(val('import-columns')||'{}')};
   const pinnedRequest=structuredClone(importRequest),pinnedRevision=revision;
   const response=await fetch('/api/import-preview',{method:'POST',headers:{'Content-Type':'application/json','X-Tyr-Editor':'1'},body:JSON.stringify({revision:pinnedRevision,request:pinnedRequest})});const result=await response.json();if(!response.ok)throw Error(result.error);
   importDraft=result.batch;
   $('import-review').innerHTML='<h2>해석 결과 · '+importDraft.observations.length+'개</h2><p>'+esc(importDraft.fileIssue||'선택한 항목만 draft로 채택합니다. 원본과 모든 미해석 항목은 함께 보존합니다.')+'</p><p>SHA-256 <code>'+esc(importDraft.sha256)+'</code></p>'+
    importDraft.observations.map(o=>'<article>'+(o.draft?'<label><input type="checkbox" data-import-select="'+esc(o.id)+'" '+(!o.issues.length?'checked':'')+'> 초안 채택 · '+esc(o.draft.id)+'</label>':'<p>채택 불가 · 미해석 보존</p>')+importObservation(o)+'</article>').join('')+'<button id="import-apply">원본 보존 및 선택 초안 저장</button>';
   $('import-apply').onclick=async()=>{
    if(busy||conflict)return;
    busy=true;$('import-apply').disabled=true;
    try{
     const selected=[...document.querySelectorAll('[data-import-select]:checked')].map(e=>e.dataset.importSelect);
     const response=await fetch('/api/import-apply',{method:'POST',headers:{'Content-Type':'application/json','X-Tyr-Editor':'1'},body:JSON.stringify({revision:pinnedRevision,request:pinnedRequest,selected})});const result=await response.json();if(!response.ok){if(response.status===409)conflict=true;throw Error(result.error);}
     display(result);dirty=false;importDraft=null;render();message('원본과 미해석 항목을 보존하고 선택한 접근 정의를 초안으로 저장했습니다.');
    }catch(e){message(e.message,true);if($('import-apply'))$('import-apply').disabled=false;}finally{busy=false;}
   };
   message('파일을 해석했습니다. 아직 SQLite는 변경하지 않았습니다.');
  }catch(e){message(e.message,true);}finally{busy=false;if($('import-preview'))$('import-preview').disabled=false;}
 };
 document.querySelectorAll('[data-import-download]').forEach(button=>button.onclick=()=>{
  const b=batches[Number(button.dataset.importDownload)],raw=Uint8Array.from(atob(b.bytesBase64),c=>c.charCodeAt(0)),url=URL.createObjectURL(new Blob([raw],{type:'application/octet-stream'})),a=document.createElement('a');a.href=url;a.download=b.filename;a.click();URL.revokeObjectURL(url);
 });
}
render=function(){if(tab==='imports'){document.querySelectorAll('[data-tab]').forEach(b=>b.classList.toggle('active',b.dataset.tab===tab));importView();}else renderBeforeImport();};
if(state)render();

/* P4-A B: original observations remain immutable; explicit review and three-way merge. */
let workflowMeta=null,workflowMerge=null,workflowMergeRequest=null;
const importViewBeforeWorkflow=importView;
async function workflowPost(path,payload,saveResult=true){
 if(busy||conflict)throw Error('다른 작업이 진행 중입니다.');
 busy=true;
 try{
  const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Tyr-Editor':'1'},body:JSON.stringify(payload)}),result=await response.json();
  if(!response.ok){if(response.status===409)conflict=true;throw Error(result.error);}
  if(saveResult){display(result);dirty=false;workflowMerge=null;render();message('원본 근거와 검토/병합 기록을 함께 저장했습니다. 채택·병합한 접근 정의를 초안으로 검토하세요.');}
  return result;
 }finally{busy=false;}
}
function workflowDecisionContext(){
 const b=state.imports.find(b=>b.id===$('workflow-batch').value),o=b?.observations.find(o=>o.id===$('workflow-observation').value);
 const meta=workflowMeta?.batches.find(x=>x.id===b?.id)?.observations.find(x=>x.id===o?.id);
 if(!o||!meta||workflowMeta.revision!==revision)throw Error('최신 관측 검토 정보를 다시 여세요.');
 return {b,o,meta};
}
function workflowShowObservation(){
 try{
 const {b,o,meta}=workflowDecisionContext(),d=meta.effectiveDraft||{};
 const locked=!!b.reconciliation||state.imports.some(x=>x.reconciliation?.previousBatchRef.id===b.id);
 $('workflow-review-save').disabled=locked;
 $('workflow-adopt').disabled=locked||!meta.effectiveDraft||state.sources.some(row=>row.importRef?.batchId===b.id&&row.importRef?.observationId===o.id);
 $('workflow-record-key').value=meta.recordKey||o.id;
 $('workflow-decision').value=meta.latestReview?.decision||'resolve-source';
 const draft=structuredClone(d);if(draft.kind){draft.id='imp-'+b.id+'-'+$('workflow-record-key').value;draft.status='draft';draft.version='1.0.0';draft.equipmentInstanceId=b.equipmentInstanceId;draft.evidenceRefs=o.derivation.map(locator=>({artifactId:'import-'+b.id,locator}));}
 $('workflow-source').value=JSON.stringify(draft,null,2);
 $('workflow-template').innerHTML=options(state.sources.filter(row=>row.definition.equipmentInstanceId===b.equipmentInstanceId&&(row.definition.sourceKind||'plc')==='plc'&&(row.definition.accessMode||'read')==='read'&&!row.definition.viewOf).map(row=>[row.definition.id,row.definition.id+' · '+row.definition.rawAddressText]),'');
 $('workflow-observation-detail').innerHTML=importObservation(o)+'<p>현재 상태: '+esc(meta.latestReview?.decision||(o.issues.length||!o.draft?'미해석 · 해결 필요':'parser 초안'))+'</p><details><summary>보존한 검토 이력</summary><pre>'+esc(JSON.stringify((b.reviews||[]).filter(q=>q.observationId===o.id),null,2))+'</pre></details>';
 }catch(e){message(e.message,true);}
}
function workflowBatchChange(){
 const b=state.imports.find(b=>b.id===$('workflow-batch').value);$('workflow-observation').innerHTML=options((b?.observations||[]).map(o=>[o.id,o.id+' · '+(o.raw?.id||'ID 미확인')+' · '+(o.issues.join(', ')||'초안')]),b?.observations[0]?.id);
 if(b?.observations.length)workflowShowObservation();
}
async function workflowFileRequest(){
 const file=$('import-file').files[0];if(!file||file.size>524288)throw Error('상단에서 512 KiB 이하 새 파일을 선택하세요.');
 const bytes=new Uint8Array(await file.arrayBuffer());let text='';for(const x of bytes)text+=String.fromCharCode(x);
 return {id:val('import-id'),filename:file.name,format:val('import-format'),equipmentInstanceId:val('import-equipment'),capturedAt:new Date().toISOString(),origin:val('import-origin'),bytesBase64:btoa(text),columnMap:JSON.parse(val('import-columns')||'{}')};
}
function workflowShowMerge(result){
 workflowMerge=result;
 $('workflow-merge-result').innerHTML='<h3>3방향 비교 · 저장하지 않음</h3><p>이전 가져오기 / 현재 작성본 / 새 파일을 필드 단위로 비교합니다. access와 rawRepresentation 같은 객체는 하나의 필드로 취급합니다. 사라진 소스는 보존하며, 충돌 선택 없이는 병합할 수 없습니다.</p><p>비교 SHA <code>'+esc(result.plan.planSha256)+'</code></p>'+result.plan.actions.map((a,i)=>'<article class="card" data-merge-action="'+i+'"><h3>'+esc(a.recordKey)+' · '+esc(a.classification)+'</h3><p>안정된 소스 ID <code>'+esc(a.sourceId)+'</code></p>'+select('merge-mode-'+i,'처리',a.classification==='removed'?[['retain','현재 소스 보존']]:['new','excluded'].includes(a.classification)?[['skip','원문만 보존'],['apply','새 초안 채택']]:[['apply','비교 결과 적용'],['retain','현재 정의 전체 유지']],['new','excluded'].includes(a.classification)?'skip':a.classification==='removed'?'retain':'apply')+'<p>현재 '+esc(a.ours?.rawAddressText||'없음')+' → 새 파일 '+esc(a.incoming?.rawAddressText||'없음')+' · '+esc(a.incoming?.rawRepresentation?.valueType||a.ours?.rawRepresentation?.valueType||'미해석')+' / '+esc(unitValue(a.incoming?.unit||a.ours?.unit))+'</p><details><summary>비교 원본 전체</summary><pre>'+esc(JSON.stringify({base:a.base,ours:a.ours,incoming:a.incoming},null,2))+'</pre></details><div class="table-scroll"><table><thead><tr><th>필드</th><th>이전 가져오기</th><th>현재 작성본</th><th>새 파일</th><th>병합 선택</th></tr></thead><tbody>'+a.fields.map((f,j)=>JSON.stringify(f.base)===JSON.stringify(f.ours)&&JSON.stringify(f.base)===JSON.stringify(f.incoming)?'':'<tr><td>'+esc(f.field)+(f.conflict?' · 충돌':'')+'</td><td><pre>'+esc(JSON.stringify(f.base))+'</pre></td><td><pre>'+esc(JSON.stringify(f.ours))+'</pre></td><td><pre>'+esc(JSON.stringify(f.incoming))+'</pre></td><td>'+(f.conflict?select('merge-field-'+i+'-'+j,'충돌 해결',[['ours','현재 작성본'],['incoming','새 파일']],''):esc(f.suggested))+'</td></tr>').join('')+'</tbody></table></div></article>').join('')+'<button type="button" id="workflow-merge-apply">선택한 병합 결과 저장</button>';
 $('workflow-merge-apply').onclick=async()=>{
 try{
 const choices={};result.plan.actions.forEach((a,i)=>{const fields={},mode=val('merge-mode-'+i);a.fields.forEach((f,j)=>{if(f.conflict&&mode==='apply'){const x=$('merge-field-'+i+'-'+j).value;if(!x)throw Error(a.recordKey+' / '+f.field+' 충돌을 선택하세요.');fields[f.field]=x;}});choices[a.key]={mode,fields};});
 await workflowPost('/api/import-merge-apply',{...workflowMergeRequest,planSha256:result.plan.planSha256,choices,reviewer:val('workflow-reviewer'),reason:val('workflow-reason'),reviewedAt:new Date().toISOString()});
 }catch(e){message(e.message,true);}
 };
}
importView=function(){
 importViewBeforeWorkflow();
 if(!(state.imports||[]).length)return;
 const batches=state.imports.map(b=>[b.id,b.id+' · '+b.filename]);
 $('view').insertAdjacentHTML('beforeend','<section class="card"><h2>미해석 항목 해결과 검토 이력</h2><p>원본·parser 관측·오류는 보존합니다. 비소스 제외에는 근거와 검토자가 필요하며, 접근 정의 해석은 읽기 정의 초안으로만 채택합니다. 이미 병합에 사용한 배치의 검토는 고정됩니다.</p><div class="fields">'+select('workflow-batch','검토할 배치',batches,batches[0][0])+select('workflow-observation','관측',[],'')+select('workflow-decision','결정',[['resolve-source','명시적 접근 정의로 해결'],['exclude-non-source','비소스 항목으로 제외']],'resolve-source')+field('workflow-record-key','안정된 record ID','')+field('workflow-reviewer','검토자','')+field('workflow-reason','검토/병합 근거','')+'</div><div id="workflow-observation-detail"></div><div class="fields">'+select('workflow-template','편집용 틀 · 명시적으로 선택',[],'')+'</div><button type="button" class="secondary" id="workflow-template-copy">기존 접근 정의를 편집용 틀로 복사</button><p>해석되지 않은 정의는 비워 둡니다. 틀 복사는 해석 정답이 아니며 주소·타입·단위·폭을 직접 검토해야 합니다.</p>'+area('workflow-source','명시적 접근 정의 JSON · 원본의 주소식/수식은 실행하지 않음','{}')+'<button type="button" id="workflow-review-save">해결 결정 저장</button> <button type="button" class="secondary" id="workflow-adopt">해결한 접근 정의 초안 채택</button></section><section class="card"><h2>재가져오기 충돌·병합</h2><p>상단의 새 파일·가져오기 ID·열 대응을 사용하거나, 먼저 원문만 저장하고 해결한 배치를 선택하세요. 원본과 이전 버전은 보존하며 canonical 소스 ID와 매핑 참조를 유지합니다.</p><div class="fields">'+select('workflow-previous','이전 가져오기 기준',batches,batches[0][0])+select('workflow-incoming','이미 보존하고 검토한 새 배치 · 선택 사항',[['','상단의 새 파일 사용'],...batches],'')+'</div><button type="button" id="workflow-merge-preview">재가져오기 3방향 비교</button><div id="workflow-merge-result"></div></section>');
 $('workflow-batch').onchange=workflowBatchChange;$('workflow-observation').onchange=workflowShowObservation;
 $('workflow-template-copy').onclick=()=>{
 try{
 const {b,o}=workflowDecisionContext(),row=state.sources.find(row=>row.definition.id===$('workflow-template').value);if(!row)throw Error('편집용 틀을 명시적으로 선택하세요.');
 const draft=structuredClone(row.definition);draft.id='imp-'+b.id+'-'+$('workflow-record-key').value;draft.status='draft';draft.version='1.0.0';draft.equipmentInstanceId=b.equipmentInstanceId;draft.evidenceRefs=o.derivation.map(locator=>({artifactId:'import-'+b.id,locator}));
 $('workflow-source').value=JSON.stringify(draft,null,2);dirty=true;message('편집용 틀을 복사했습니다. 이 관측의 주소·타입·단위·폭을 직접 검토하세요.');
 }catch(e){message(e.message,true);}
 };
 $('workflow-review-save').onclick=async()=>{
 try{
 const {b,o,meta}=workflowDecisionContext(),decision=val('workflow-decision'),recordKey=decision==='resolve-source'?val('workflow-record-key'):null;
 const source=decision==='resolve-source'?JSON.parse($('workflow-source').value):null;
 if(source){source.id='imp-'+b.id+'-'+recordKey;source.status='draft';source.version='1.0.0';source.equipmentInstanceId=b.equipmentInstanceId;source.evidenceRefs=o.derivation.map(locator=>({artifactId:'import-'+b.id,locator}));}
 await workflowPost('/api/import-review',{revision,batchId:b.id,review:{observationId:o.id,observationSha256:meta.observationSha256,previousReviewSha256:meta.previousReviewSha256,decision,recordKey,source,reviewer:val('workflow-reviewer'),reason:val('workflow-reason'),reviewedAt:new Date().toISOString()}});
 }catch(e){message(e.message,true);}
 };
 $('workflow-adopt').onclick=async()=>{try{const {b,o}=workflowDecisionContext();await workflowPost('/api/import-adopt-reviewed',{revision,batchId:b.id,selected:[o.id]});}catch(e){message(e.message,true);}};
 $('workflow-merge-preview').onclick=async()=>{try{
 const incoming=$('workflow-incoming').value;
 workflowMergeRequest={revision,previousBatchId:val('workflow-previous'),...(incoming?{batchId:incoming}:{request:await workflowFileRequest()})};
 const result=await workflowPost('/api/import-merge-preview',workflowMergeRequest,false);workflowShowMerge(result);
 }catch(e){message(e.message,true);}};
 fetch('/api/import-workflow').then(r=>r.json()).then(meta=>{if(!$('workflow-batch'))return;workflowMeta=meta;workflowBatchChange();}).catch(e=>message(e.message,true));
};
