/* File/CLI exchange; no keys, approval execution or runtime activation in this UI. */
let submissionRows=[], maintenancePlan=null;
const publicationStateLabels={exported:'파일 저장됨','awaiting-approval':'승인 대기',approved:'서명 승인됨',published:'릴리스 발행됨','receiver-refused':'수신 검사 거부','base-conflict':'기준 릴리스 충돌'};
async function publicationApi(path,body){
 const response=await fetch(path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json','X-Tyr-Editor':'1'}:{},...(body?{body:JSON.stringify(body)}:{})});
 const data=await response.json();if(!response.ok)throw Error(data.error||'제출 요청 실패');return data;
}
async function loadPublication(){
 try{
  const data=await publicationApi('/api/submissions');if(tab!=='publication')return;
  submissionRows=data.submissions;
  $('publication-connection').textContent=data.configured?'Bifrost CLI 연결됨 · 파일 검증/승인 상태 조회만 사용':'Bifrost CLI 미설정 · 파일 제출본 생성/다운로드 가능';
  $('submission-records').innerHTML=data.submissions.length?data.submissions.map(r=>'<article class="card"><h3>'+esc(r.id)+' · '+esc(publicationStateLabels[r.publicationState||'exported']||r.publicationState)+'</h3>'+(r.publication?.release?'<p>현재 스트림 릴리스 <strong>'+esc(r.publication.release.id+'@'+r.publication.release.version)+'</strong></p>':'')+'<p>스트림 '+esc(r.streamId)+' · 작성 revision '+r.workspaceRevision+(r.stale?' · 현재 작성본과 다름':' · 현재 작성본과 동일')+'</p><p>제안 <code>'+esc(r.proposalSha256)+'</code><br>전체 묶음 <code>'+esc(r.bundleSha256)+'</code></p><p>승인 권위 Bifrost / 운영 활성화 수행 안 함 / SQL·쓰기 실행 제외</p><p>승인·발행 조회: '+esc(r.observedAt||'아직 조회하지 않음')+'</p><button type="button" data-submission-refresh="'+esc(r.id)+'">Bifrost 재검증·승인/발행 상태 조회</button> <button type="button" class="secondary" data-submission-download="'+esc(r.id)+'">제출 ZIP 다운로드</button><details><summary>검사·승인·릴리스 근거</summary><pre>'+esc(JSON.stringify(r,null,2))+'</pre></details></article>').join(''):'<p>저장한 제출본이 없습니다.</p>';
 }catch(e){message(e.message,true);}
}
function publicationView(){
 if(!v2Mode())return migrationView();
 $('view').innerHTML='<p class="step">13 / Bifrost 제출·릴리스</p><p>선택한 객체 매핑과 의존 정의·원본 근거를 파일 묶음으로 고정합니다. Tyr 검토와 Bifrost 검증·서명 승인·릴리스 발행은 별개입니다. 릴리스 발행은 운영 활성화가 아닙니다.</p><p id="publication-connection"></p><section class="card"><h2>불변 제출본 생성</h2><form id="submission-form"><div class="fields">'+field('submission-id','새 제출본 ID','','text',true)+field('submission-stream','안정된 릴리스 스트림 ID','','text',true)+field('submission-by','제안자 ID · 승인 시 등록 키와 일치해야 함','','text',true)+select('submission-mapping','제출할 객체 매핑 · 복수 선택 가능',state.mappings.map(m=>[m.id,m.id]),'')+select('submission-writes','해당 객체의 쓰기 정의 포함 · 실행 제외',[['no','읽기 매핑만'],['yes','읽기 매핑 + 별도 쓰기 정의']],'no')+'</div><p>같은 스트림의 후속 제출은 새 제출본 ID를 사용합니다. 미확인 정의는 원문과 함께 남고 Bifrost에서 거부됩니다. 현재 저장본만 내보냅니다. URI 개정 이력이 있으면 매핑을 선택하지 않고 개정 이력만 제출할 수 있습니다. 이 경우에도 모든 관리 대상 의미 정의와 전체 선행 이력을 고정합니다.</p><button type="submit">제출 파일 묶음 저장</button></form></section><section><h2>검증·승인·발행 상태</h2><p>승인/발행은 별도 Bifrost CLI에서 등록 키·권한과 두 확인자로 수행합니다. 이 화면에 개인 키를 입력하거나 실행 권한을 부여하지 않습니다.</p><div id="submission-records"></div></section><section class="card"><h2>전역 의미 카탈로그</h2><p>보존된 모든 스트림 릴리스와 현재 작성본의 semantic URI를 비교합니다. 같은 URI의 타입·단위·역할과 구조 계약이 같아야 합니다. 이름만으로 의미를 합치지 않습니다. 현장 의미 정답은 별도 검토가 필요합니다.</p><button type="button" id="catalog-preview">의미 카탈로그 조회·작성본 비교</button><div id="catalog-summary"></div><pre id="catalog-result"></pre></section><section class="card"><h2>제출 파일 무결성·임시 파일 정리</h2><p>저장된 제출본은 보존합니다. 24시간이 지난 고아 폴더만 계획 확인 후 격리하며 영구 삭제하지 않습니다. Bifrost 복구·GC는 별도 CLI에서 수행합니다.</p><button type="button" id="maintenance-preview">무결성 검사·GC 사전 조회</button> <button type="button" id="maintenance-quarantine" disabled>조회한 고아 폴더 격리</button><pre id="maintenance-result"></pre></section>';
 $('submission-mapping').required=!state.semanticLifecycles?.length;$('submission-mapping').multiple=true;$('submission-mapping').size=Math.min(6,Math.max(2,state.mappings.length));$('submission-mapping').querySelector('option[value=""]')?.remove();$('submission-mapping').selectedIndex=-1;
 loadPublication();
}
const renderBeforePublication=render;
render=function(){if(tab==='publication'){document.querySelectorAll('[data-tab]').forEach(b=>b.classList.toggle('active',b.dataset.tab===tab));publicationView();}else renderBeforePublication();};
document.addEventListener('submit',async event=>{
 if(event.target.id!=='submission-form')return;event.preventDefault();if(busy||conflict)return;busy=true;
 try{
  await publicationApi('/api/submissions',{revision,id:val('submission-id'),streamId:val('submission-stream'),proposedBy:val('submission-by'),mappingSetIds:[...$('submission-mapping').selectedOptions].map(o=>o.value).filter(Boolean),includeWrites:val('submission-writes')==='yes'});
  dirty=false;await loadPublication();message('불변 제출본과 근거 파일을 저장했습니다. Bifrost 승인은 별도입니다.');
 }catch(e){message(e.message,true);}finally{busy=false;}
});
document.addEventListener('click',async event=>{
 const b=event.target.closest('button');if(!b||busy)return;
 const id=b.dataset.submissionRefresh||b.dataset.submissionDownload;if(!id)return;busy=true;
 try{
  if(b.dataset.submissionRefresh){
   const row=submissionRows.find(r=>r.id===id);await publicationApi('/api/submission-refresh',{id,submissionRevision:row.submissionRevision});await loadPublication();message('Bifrost가 수신 경계에서 다시 검사했습니다. 승인·발행·활성화를 구분하세요.');
  }else{
   const data=await publicationApi('/api/submission-download',{id});const bytes=Uint8Array.from(atob(data.bytesBase64),c=>c.charCodeAt(0));const url=URL.createObjectURL(new Blob([bytes],{type:'application/zip'}));const a=document.createElement('a');a.href=url;a.download=data.filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
 }catch(e){message(e.message,true);}finally{busy=false;}
});

document.addEventListener('click',async event=>{
 const id=event.target.closest('button')?.id;if(!['maintenance-preview','maintenance-quarantine'].includes(id)||busy)return;busy=true;
 try{
  const body={graceSeconds:86400};if(id==='maintenance-quarantine')body.planSha256=maintenancePlan?.planSha256;
  const result=await publicationApi('/api/submission-maintenance',body);maintenancePlan=result;
  $('maintenance-result').textContent=JSON.stringify(result,null,2);
  $('maintenance-quarantine').disabled=!result.dryRun||!result.candidates.length||result.integrity.some(i=>i.state!=='verified');
  message(result.dryRun?'무결성 검사와 격리 후보 조회를 완료했습니다.':'고아 폴더를 격리했습니다.');
 }catch(e){maintenancePlan=null;$('maintenance-quarantine').disabled=true;message(e.message,true);}finally{busy=false;}
});

const catalogLabels={'workspace-conflict':'작성본 내부 충돌','registry-unavailable':'레지스트리 미조회','registry-conflict':'보존 릴리스와 충돌',compatible:'계약 일치',new:'신규 URI'};
document.addEventListener('click',async event=>{
 if(event.target.closest('button')?.id!=='catalog-preview'||busy)return;busy=true;
 try{
  const data=await publicationApi('/api/semantic-catalog');
  $('catalog-summary').innerHTML='<p>작성 revision '+data.workspaceRevision+' · 보존 릴리스 '+(data.catalog?.releases.length??'미조회')+' · 레지스트리 전체 '+(data.catalog?(data.catalog.compatible?'계약 일치':'과거 계약 충돌'):'미설정')+'</p>'+data.entries.map(e=>'<article><strong>'+esc(e.semanticId)+'</strong> · '+esc(catalogLabels[e.status])+'<p>'+e.variants.map(v=>esc(v.signature.valueType)+' / '+esc(v.signature.unit?.code||v.signature.unit?.status||'구조')+' / '+esc(v.signature.role||'구조')+' · '+v.occurrences.map(o=>esc(o.definitionId+'@'+o.definitionVersion+' / '+o.memberId+' / '+o.label)).join(', ')).join('<br>')+'</p></article>').join('');
  if(data.catalog)$('catalog-summary').innerHTML+='<details><summary>보존 카탈로그 전체 · '+data.catalog.entries.length+' URI · 정의·릴리스 근거</summary>'+data.catalog.entries.map(e=>'<article><h3>'+esc(e.semanticId)+(e.compatible?'':' · 과거 계약 충돌')+'</h3>'+e.variants.map(v=>'<pre>'+esc(JSON.stringify(v.signature,null,2))+'</pre><ul>'+v.occurrences.map(o=>'<li>'+esc(o.streamId+' / '+o.releaseId+'@'+o.releaseVersion+' / '+o.definitionId+'@'+o.definitionVersion+' / '+o.definitionPath.join('.')+' / '+o.label)+'<br><code>'+esc(o.releaseSha256)+'</code></li>').join('')+'</ul>').join('')+'</article>').join('')+'</details>';
  $('catalog-result').textContent=JSON.stringify(data,null,2);message('의미 계약·원본 릴리스 근거를 조회했습니다. 물리적 의미 동등성은 별도 검토하세요.');
 }catch(e){$('catalog-summary').textContent='카탈로그 조회 실패 · 승인 가능으로 판단하지 않습니다.';$('catalog-result').textContent='';message(e.message,true);}finally{busy=false;}
});
