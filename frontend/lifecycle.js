/* Governance drafts are immutable records; only Bifrost approves and publishes them. */
let lifecycleData=null;
async function lifecycleView(){
 if(!v2Mode())return migrationView();
 $('view').innerHTML='<p class="step">18 / 의미 URI 개정·폐기</p><p>URI의 역할·타입·단위·구조는 고정합니다. 설명 개정은 revise, 사용 중단 권고는 deprecate, 폐기는 retire로 기록합니다. 의미가 달라지면 공통 의미에서 새 URI를 정의하고 대체 URI를 명시하세요. 자동 재매핑은 수행하지 않습니다. active → deprecated → retired 순서로 관리하며, 사용 중단 권고 후에만 폐기할 수 있습니다. 폐기는 새 승인·발행을 차단하며 이미 가동 중인 설비를 변경하지 않습니다.</p><section class="card"><form id="lifecycle-form"><div class="fields"><div id="lifecycle-picker"></div>'+select('lifecycle-action','변경 종류',[['revise','설명 개정'],['deprecate','사용 중단 권고'],['retire','폐기']],'revise')+field('lifecycle-label','개정 표시 이름','','text',true)+field('lifecycle-author','작성자','','text',true)+'</div><label>개정 설명<textarea id="lifecycle-description" rows="3"></textarea></label><label>변경 사유<textarea id="lifecycle-reason" required rows="3"></textarea></label><div id="lifecycle-replacement-picker"></div><button type="submit">불변 이력으로 로컬 저장</button></form><p>저장은 승인·발행이 아닙니다. 13 화면에서 매핑과 함께 제출하고 Bifrost의 별도 서명 승인을 받으세요. 다른 작업공간에서 선행 개정이 발행되면 충돌을 해결한 새 작업공간으로 다시 제출해야 합니다.</p></section><section class="card" id="lifecycle-details">이력을 조회합니다.</section>';
 try{
  lifecycleData=await expressionApi('/api/semantic-lifecycle');if(tab!=='lifecycle')return;
  $('lifecycle-picker').innerHTML=select('lifecycle-uri','대상 URI',lifecycleData.entries.filter(e=>e.editable).map(e=>[e.semanticId,e.semanticId+' · '+e.state+' · r'+e.revision]),'');
  $('lifecycle-replacement-picker').innerHTML=select('lifecycle-replacement','대체 URI (선택)',lifecycleData.entries.filter(e=>e.editable&&e.state!=='retired').map(e=>[e.semanticId,e.semanticId]),'',false);
  $('lifecycle-uri').addEventListener('change',lifecycleSelection);lifecycleSelection();
  $('lifecycle-action').addEventListener('change',lifecycleSelection);
  $('lifecycle-details').innerHTML='<h2>변경 이력과 영향받는 매핑</h2><p>로컬 revision '+lifecycleData.workspaceRevision+' · '+(lifecycleData.published?'Bifrost 검증된 발행 이력 연결':'Bifrost 미연결 · 로컬 초안만 표시')+'</p>'+lifecycleData.entries.map(e=>{
   const published=lifecycleData.published?.entries.find(p=>p.semanticId===e.semanticId);const h=e.history[e.history.length-1];
   return '<article><h3>'+esc(e.semanticId)+'</h3><p>작성본 '+esc(e.state)+' / r'+e.revision+' · 발행본 '+esc(published?published.state+' / r'+published.revision:'미발행')+' · 대체 '+esc(e.replacementSemanticId||'없음')+'</p>'+(h?'<p>'+esc(h.label)+' · '+esc(h.description)+'</p>':'')+'<p>로컬 영향 '+e.localImpacts.length+'개 · 발행 이력 영향 '+e.publishedImpacts.length+'개 (현재 head '+e.publishedImpacts.filter(i=>i.currentHead).length+'개)</p><table><thead><tr><th>구분</th><th>설비 / 객체</th><th>매핑 / 멤버</th><th>상태</th></tr></thead><tbody>'+[...e.localImpacts.map(i=>({...i,local:true})),...e.publishedImpacts].map(i=>'<tr><td>'+esc(i.kind)+'</td><td>'+esc(i.equipmentInstanceId+' / '+i.targetInstanceId)+'</td><td>'+esc(i.id+' / '+i.bindingId)+'<br>'+esc(JSON.stringify(i.memberPath))+'</td><td>'+esc(i.local?'로컬 초안':i.currentHead?'현재 발행 head':'과거 릴리스')+'</td></tr>').join('')+'</tbody></table><details><summary>개정 사유·작성자·시각·선행 해시 전체 이력</summary><pre>'+esc(JSON.stringify(e.history,null,2))+'</pre></details><details><summary>Bifrost 발행 릴리스 · 이벤트별 원본 해시</summary><pre>'+esc(JSON.stringify(e.publishedEventOrigins,null,2))+'</pre></details></article>';
  }).join('');
 }catch(e){$('lifecycle-details').textContent=e.message;message(e.message,true);}
}
function lifecycleSelection(){
 const e=lifecycleData?.entries.find(e=>e.semanticId===val('lifecycle-uri'));const h=e?.history[e.history.length-1];
 const allowed=!e?[]:e.state==='active'?['revise','deprecate']:e.state==='deprecated'?['revise','retire']:[];
 for(const o of $('lifecycle-action').options)o.disabled=!allowed.includes(o.value);
 if(!allowed.includes(val('lifecycle-action')))$('lifecycle-action').value=allowed[0]||'';
 document.querySelector('#lifecycle-form button[type=submit]').disabled=!e||e.state==='retired';
 $('lifecycle-label').value=h?.label||e?.semanticId||'';$('lifecycle-description').value=h?.description||'';
 $('lifecycle-replacement').value=e?.replacementSemanticId||'';$('lifecycle-replacement').disabled=val('lifecycle-action')!=='deprecate';
}
const renderBeforeLifecycle=render;
render=function(){if(tab==='lifecycle'){document.querySelectorAll('[data-tab]').forEach(b=>b.classList.toggle('active',b.dataset.tab===tab));lifecycleView();}else renderBeforeLifecycle();};
document.addEventListener('submit',async event=>{
 if(event.target.id!=='lifecycle-form')return;event.preventDefault();if(busy||conflict)return;busy=true;
 try{
  const result=await expressionApi('/api/semantic-lifecycle-apply',{revision,semanticId:val('lifecycle-uri'),action:val('lifecycle-action'),replacementSemanticId:val('lifecycle-replacement')||null,label:val('lifecycle-label'),description:$('lifecycle-description').value,reason:$('lifecycle-reason').value,authoredBy:val('lifecycle-author')});
  display(result.saved);dirty=false;await lifecycleView();message('URI 개정 이력을 저장했습니다. 검토·제출에서 승인·발행 상태를 별도로 확인하세요.');
 }catch(e){message(e.message,true);}finally{busy=false;}
});
