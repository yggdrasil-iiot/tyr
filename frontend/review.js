/* Immutable local review; no approval or execution authority. */
let reviewBaselineId='',reviewTargets=[],reviewDiff=null,reviewGeneration=0;
async function reviewApi(path,body){
 const response=await fetch(path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json','X-Tyr-Editor':'1'}:{},...(body?{body:JSON.stringify(body)}:{})});
 const data=await response.json();if(!response.ok){if(response.status===409)reviewDiff=null;throw Error(data.error||'검토 요청 실패');}return data;
}
function reviewJson(v){return '<pre>'+esc(JSON.stringify(v,null,2))+'</pre>';}
async function loadReview(){
 const generation=++reviewGeneration;
 try{
  const [baselines,reviews]=await Promise.all([reviewApi('/api/review-baselines'),reviewApi('/api/reviews')]);
  if(tab!=='review'||generation!==reviewGeneration)return;
  if(reviews.workspaceRevision!==revision){message('작성본이 변경됐습니다. 최신 저장본을 다시 열어주세요.',true);return;}
  reviewTargets=reviews.targets;
  $('review-baseline').innerHTML=baselines.baselines.map(b=>'<option value="'+esc(b.id)+'">'+esc(b.label+' · '+b.id+' · revision '+b.workspaceRevision)+'</option>').join('');
  if(baselines.baselines.some(b=>b.id===reviewBaselineId))$('review-baseline').value=reviewBaselineId;
  $('review-target').innerHTML=reviewTargets.filter(t=>t.evidenceRefs.length).map(t=>'<option value="'+esc(t.key)+'">'+esc(t.key+' · '+t.reviewStatus)+'</option>').join('');
  $('review-records').innerHTML=reviews.records.length?reviews.records.map(({record:r,currentStatus,superseded})=>'<article class="card"><strong>'+esc(currentStatus)+(superseded?' · 후속 검토 있음':' · 최신 검토')+' · '+esc(r.id)+'</strong><p>'+esc(r.targetKey)+'<br>'+esc(r.by+' · '+r.at)+'</p><p>'+esc(r.rationale)+'</p><details><summary>검토 당시 해시·근거</summary>'+reviewJson(r)+'</details></article>').join(''):'<p>저장된 담당자 검토 기록이 없습니다.</p>';
  $('review-status-p5').textContent='관측·대응: 정의와 근거에 보존 / 담당자 검토: 별도 기록 / 승인: 요청 안 함 / 실장치 확인: 수행 안 함';
  $('review-baseline').onchange=()=>{reviewBaselineId=val('review-baseline');reviewDiff=null;$('review-diff').innerHTML='<p>기준이 바뀌었습니다. 다시 비교하세요.</p>';};
  $('review-target').onchange=showReviewTarget;showReviewTarget();
 }catch(e){message(e.message,true);}
}
function showReviewTarget(){
 const t=reviewTargets.find(t=>t.key===val('review-target'));
 if(t)$('review-target-hash').innerHTML='<p>대상 '+esc(t.targetSha256)+'<br>의존 정의 '+esc(t.dependencySha256)+'</p><details><summary>근거 및 의존 정의 '+Object.keys(t.dependencies).length+'개</summary>'+reviewJson(t)+'</details>';
}
function reviewView(){
 $('view').innerHTML='<p class="step">12 / 변경과 담당자 검토</p><p>불변 기준본과 현재 저장본을 비교합니다. 검토는 로컬 확인자의 선언이며 인증·Bifrost 승인·실장치 확인을 대신하지 않습니다.</p><p id="review-status-p5"></p><section class="card"><h2>비교 기준본</h2><form id="baseline-form-p5"><div class="fields">'+field('baseline-id','새 기준본 ID','','text',true)+field('baseline-label','기준 설명','','text',true)+'</div><button type="submit">현재 저장본을 불변 기준으로 저장</button></form>'+select('review-baseline','저장된 비교 기준',[],'')+'<button type="button" id="review-compare">현재 저장본과 비교</button></section><section id="review-diff" class="card"><p>기준본을 선택하고 비교하세요. 저장하지 않은 편집 내용은 비교하지 않습니다.</p></section><section class="card"><h2>담당자 검토 기록 · 승인 아님</h2><form id="change-review-form"><div class="fields">'+field('review-id','새 검토 기록 ID','','text',true)+select('review-target','검토 대상',[],'')+select('review-decision','검토 판단',[['reviewed','확인함'],['needs-review','재검토 필요'],['disputed','이견 있음']],'reviewed')+field('review-by','확인자 ID · 로컬 선언','','text',true)+area('review-rationale','판단 사유·확인한 근거','')+'</div><div id="review-target-hash"></div><p>대상과 의존 정의의 근거를 기록합니다. 변경 후 기존 기록을 보존하고 재검토 상태로 표시합니다.</p><button type="submit">현재 비교·해시에 검토 기록 저장</button></form></section><section><h2>검토 이력</h2><div id="review-records"></div></section>';
 $('review-compare').onclick=async()=>{
  try{
   if(!val('review-baseline'))throw Error('비교 기준본을 먼저 저장하세요.');
   reviewBaselineId=val('review-baseline');reviewDiff=await reviewApi('/api/review-diff',{revision,baselineId:reviewBaselineId});
   const d=reviewDiff;
   $('review-diff').innerHTML='<h2>변경 '+d.changes.length+'건 · 영향 대상 '+d.affected.length+'개</h2><p>이름과 stable ID·접근·변환·의미 변경을 구분합니다. 원문 변경은 해석 정의 변경과 별도입니다. 불완전 정보와 정의 충돌은 진단에서 구분합니다. 표시 변경도 해시가 달라지므로 기존 확인 기록은 보수적으로 재검토합니다.</p><div class="table-scroll"><table><thead><tr><th>대상 / 변경 필드</th><th>분류</th><th>이전</th><th>현재</th></tr></thead><tbody>'+d.changes.map(c=>'<tr><td>'+esc(c.key)+'<br>'+esc(c.path)+'</td><td>'+esc(c.category+' / '+c.change)+'<br>'+(c.reviewRequired?'재검토 대상':'표시 변경')+'</td><td>'+reviewJson(c.before)+'</td><td>'+reviewJson(c.after)+'</td></tr>').join('')+'</tbody></table></div><details open><summary>직접 변경 및 의존 정의의 전이 영향</summary>'+d.affected.map(a=>'<p><strong>'+esc(a.key)+'</strong> · '+(a.direct?'직접 변경':'의존 정의 변경')+'<br>'+esc(a.causes.join(', '))+'</p>').join('')+'</details><details><summary>미완성·충돌·alias/view·관측 진단</summary>'+reviewJson(d.diagnostics)+'</details><details><summary>비교 해시</summary>'+reviewJson({baseline:d.baselineSha256,current:d.workspaceSha256})+'</details>';
  }catch(e){reviewDiff=null;message(e.message,true);}
 };loadReview();
}
const renderBeforeP5=render;
render=function(){if(tab==='review'){document.querySelectorAll('[data-tab]').forEach(b=>b.classList.toggle('active',b.dataset.tab===tab));reviewDiff=null;reviewView();}else renderBeforeP5();};
document.addEventListener('submit',async event=>{
 if(!['baseline-form-p5','change-review-form'].includes(event.target.id))return;
 event.preventDefault();if(busy||conflict)return;busy=true;
 try{
  if(event.target.id==='baseline-form-p5'){
   const b=await reviewApi('/api/review-baselines',{revision,id:val('baseline-id'),label:val('baseline-label')});reviewBaselineId=b.id;dirty=false;await loadReview();message('불변 기준본을 저장했습니다. 작성본 revision은 변경하지 않았습니다.');
  }else{
   if(!reviewDiff||reviewDiff.workspaceRevision!==revision||reviewDiff.baselineId!==val('review-baseline'))throw Error('현재 기준으로 먼저 비교하세요.');
   const t=reviewTargets.find(t=>t.key===val('review-target'));if(!t)throw Error('근거가 있는 검토 대상을 선택하세요.');
   const record={kind:'change-review',schemaVersion:'2.8.0',id:val('review-id'),baselineId:reviewDiff.baselineId,baselineSha256:reviewDiff.baselineSha256,workspaceSha256:reviewDiff.workspaceSha256,targetKey:t.key,targetSha256:t.targetSha256,dependencySha256:t.dependencySha256,decision:val('review-decision'),by:val('review-by'),at:new Date().toISOString(),rationale:val('review-rationale'),evidenceRefs:t.evidenceRefs,approval:'not-requested',deviceVerification:'not-performed'};
   await reviewApi('/api/reviews',{revision,record});dirty=false;await loadReview();message('담당자 검토 기록을 추가했습니다. 승인·실장치 확인은 별도입니다.');
  }
 }catch(e){message(e.message,true);}finally{busy=false;}
});
