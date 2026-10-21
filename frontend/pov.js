/* Independent evaluation input stays a local artifact, outside approval and SQLite mutation. */
let povPackText='',povLastReport=null;
function povView(){
 if(!v2Mode())return migrationView();
 $('view').innerHTML='<p class="step">16 / 독립 정답·오프라인 평가 준비</p><p class="card"><strong>현장 PoV 미인증</strong> · 합성 결과는 현장 정확도·시간 절감 실적이 아닙니다. 정답은 담당자가 별도로 작성하고 조정용·평가용·미사용 설비를 구분하세요. 평가 선언의 독립성은 이 도구가 인증하지 않습니다.</p><section class="card"><h2>평가 입력</h2>'+select('pov-scope','평가할 객체 매핑',state.mappings.map(m=>[m.id,m.id]),'')+'<button id="pov-template" type="button">기대값이 빈 정답 양식 만들기</button><p>양식은 객체·멤버 경로만 제공합니다. 아래 실제 정의 목록의 hash는 검토용이며 의미 정답을 자동으로 채우지 않습니다.</p><details><summary>실제 정의 목록 · 독립 정답과 별도</summary><pre id="pov-inventory"></pre></details><label>독립 정답 JSON 파일<input id="pov-file" type="file" accept=".json,application/json"></label><label>평가 pack JSON<textarea id="pov-pack" rows="18" spellcheck="false"></textarea></label><button id="pov-evaluate" type="button">현재 저장본과 읽기 전용 평가</button> <button id="pov-save-pack" class="secondary" type="button">입력 JSON 저장</button></section><section class="card"><h2>항목별 판정·분모·시간</h2><div id="pov-summary"></div><div id="pov-cases"></div><button id="pov-download" class="secondary" type="button" disabled>평가 결과 JSON 저장</button><details><summary>결과·입력 hash·가상 단계별 trace</summary><pre id="pov-result"></pre></details></section>';
 $('pov-scope').multiple=true;$('pov-scope').size=Math.min(6,Math.max(2,state.mappings.length));$('pov-scope').querySelector('option[value=""]')?.remove();$('pov-scope').selectedIndex=-1;
 $('pov-pack').value=povPackText;
 $('pov-pack').oninput=()=>{povPackText=$('pov-pack').value;povLastReport=null;$('pov-download').disabled=true;$('pov-summary').textContent='평가 입력 변경됨 · 다시 평가하세요.';$('pov-cases').innerHTML='';$('pov-result').textContent='';};
 $('pov-file').onchange=async()=>{try{const file=$('pov-file').files[0];if(!file)return;if(file.size>1024*1024)throw Error('평가 파일은 1 MiB 이하만 허용합니다.');const text=await file.text();JSON.parse(text);$('pov-pack').value=text;$('pov-pack').dispatchEvent(new Event('input'));}catch(e){message(e.message,true);}};
}
function povDownload(data,name){const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function povShow(report){
 povLastReport=report;$('pov-download').disabled=false;
 const labels={calibration:'조정용 · 평가 실적 제외',evaluation:'평가용',heldout:'미사용 설비'};
 $('pov-summary').innerHTML='<p><strong>'+esc(report.evidenceClass)+' · 현장 PoV 미인증</strong> · 저장 revision '+report.revision+(report.baselineWorkspaceChanged?' · 정답 작성 기준본과 현재 작성본이 다름':'')+'</p>'+Object.entries(report.metrics).map(([split,m])=>'<article><h3>'+labels[split]+'</h3><p>기준 항목 '+m.oracleCases+' · 전체 확인 '+m.counts['verified-fixture']+' · 누락 '+m.counts.missing+' · 미검토 '+m.counts.unreviewed+' · 의미 불일치 '+m.counts['meaning-mismatch']+' · 정의 차이 '+m.counts['definition-difference']+' · 샘플 불일치 '+m.counts['sample-mismatch']+' · 부분 '+m.counts.partial+' · 중복 '+m.counts.ambiguous+'</p><p>가상 샘플 '+m.evaluatedSamples+' / '+m.plannedSamples+' · 값/진단 불일치 '+m.sampleMismatches+' · 손실 진단 확인 '+m.lossChecks+' · 손실 진단 불일치 '+m.lossDiagnosticMismatches+'</p><p>기준 항목 확인율 '+(m.verifiedPercent===null?'미측정':esc(m.verifiedPercent)+'%')+' · 완료 시간 비교 '+m.time.completePairs+'쌍 · 수작업 '+m.time.manualSeconds+'초 / 도구 '+m.time.toolSeconds+'초 · 선언된 절감률 '+(m.time.savingPercent===null?'미측정':esc(m.time.savingPercent)+'%')+' · 순서 교차 '+(m.time.counterbalanced?'있음':'없음')+'</p></article>').join('')+'<p>정답 검토 범위 '+report.coverage.reviewedUnambiguousIdentities+' / '+report.coverage.uniqueActualIdentities+'개 객체 멤버 · 정답이 없는 추가 매핑 '+report.unexpectedMappings.length+'개는 별도 미평가입니다. 정의 hash 차이는 구조적 차이이며 의미 오류로 자동 단정하지 않습니다.</p>';
 $('pov-cases').innerHTML='<div class="table-scroll"><table><thead><tr><th>기준 항목 · 객체 · 전체 경로</th><th>판정</th><th>독립 근거</th></tr></thead><tbody>'+report.cases.map(c=>'<tr><td>'+esc(c.caseId)+'<br>'+esc(c.identity.equipmentInstanceId+' / '+c.identity.targetInstanceRef.id+'@'+c.identity.targetInstanceRef.version)+'<br><code>'+esc(memberPathLabel(c.identity.memberPath))+'</code></td><td>'+esc(c.status)+'</td><td>'+esc(c.oracleEvidence||'미작성')+'</td></tr>').join('')+'</tbody></table></div>';
 $('pov-result').textContent=JSON.stringify(report,null,2);
}
const renderBeforePov=render;render=function(){if(tab==='pov'){document.querySelectorAll('[data-tab]').forEach(b=>b.classList.toggle('active',b.dataset.tab===tab));povView();}else renderBeforePov();};
document.addEventListener('click',async event=>{
 const id=event.target.closest('button')?.id;if(!['pov-template','pov-evaluate','pov-save-pack','pov-download'].includes(id)||busy)return;busy=true;
 try{
  if(id==='pov-template'){
   const mappingSetIds=[...$('pov-scope').selectedOptions].map(o=>o.value);const data=await publicationApi('/api/pov-template',{revision,mappingSetIds});povPackText=JSON.stringify(data.pack,null,2);$('pov-pack').value=povPackText;$('pov-pack').dispatchEvent(new Event('input'));$('pov-inventory').textContent=JSON.stringify(data.inventory,null,2);message('기대값이 빈 독립 정답 양식을 만들었습니다.');
  }else if(id==='pov-evaluate'){const report=await publicationApi('/api/pov-evaluate',{revision,pack:JSON.parse($('pov-pack').value)});povShow(report);message('읽기 전용 평가를 완료했습니다. 현장 PoV 인증은 별도입니다.');}
  else if(id==='pov-save-pack')povDownload(JSON.parse($('pov-pack').value),'tyr-evaluation-pack.json');
  else if(povLastReport)povDownload(povLastReport,'tyr-evaluation-report.json');
 }catch(e){povLastReport=null;$('pov-download').disabled=true;message(e.message,true);}finally{busy=false;}
});
