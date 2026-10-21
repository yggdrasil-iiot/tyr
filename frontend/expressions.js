/* Authoring-only syntax. Bifrost receives an existing 2.15 DAG, never expression text. */
let expressionRows=[],expressionCompilation=null;
async function expressionApi(path,body){
 const r=await fetch(path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json','X-Tyr-Editor':'1'}:{},...(body?{body:JSON.stringify(body)}:{})});const d=await r.json();if(!r.ok){if(r.status===409)conflict=true;throw Error(d.error||'수식 요청 실패');}return d;
}
function expressionView(){
 if(!v2Mode())return migrationView();expressionCompilation=null;
 $('view').innerHTML='<p class="step">17 / 제한 수식 → 값 그래프</p><p>소스 ID는 [소스ID]로 명시합니다. + − * /, 괄호, sqrt(식), clamp(식,하한,상한), linear(식,계수,오프셋)을 지원합니다. 곱셈·나눗셈은 기존 제한 단위 규칙을 적용하며 단위 자동 변환·일반 차원 추론·온도 delta·다른 그래프 참조는 제외합니다. 1.1에서는 숫자는 무차원 상수이며 quantity(3, &quot;kPa&quot;)로 단위를 명시합니다. 상수는 기존 2.7 정의로 함께 저장하고 원문 위치·출처를 보존합니다. 이전 1.0 원문은 기존 규칙을 유지합니다. 수식은 실행 코드가 아니라 기존 2.15 그래프로 변환하는 작성 입력입니다.</p><section class="card"><form id="expression-form"><div class="fields">'+field('expression-id','수식 그래프 ID','','text',true)+select('expression-version','컴파일 규칙',[['1.1.0','1.1 숫자·단위 상수'],['1.0.0','1.0 기존 규칙']],'1.1.0')+select('expression-equipment','소속 설비',state.equipment.map(e=>[e.id,e.label]),'')+'</div><label for="expression-text">수식 원문</label><textarea id="expression-text" rows="5" maxlength="4096" required></textarea><p>예: ([pressure-up] - [pressure-down]) / [gain]. 최대 4096자·512 토큰·64 연산·괄호/함수 중첩 32단계. 분모 0과 변환 손실은 09 미리보기에서 검증합니다.</p><button type="submit">컴파일·타입·단위 확인</button> <button type="button" id="expression-apply" disabled>다시 컴파일하고 그래프·수식 함께 저장</button></form><div id="expression-summary"></div><details><summary>컴파일된 정의·원문 위치·소스 pin</summary><pre id="expression-result"></pre></details></section><section class="card"><h2>저장된 수식·최신 정의 비교</h2><p>그래프를 수동 편집하거나 소스/논리 연결이 바뀌면 stale로 표시합니다. 명시적으로 재컴파일해 저장하기 전에는 과거 원문을 최신 그래프의 설명으로 사용하지 마세요. 수식 이력은 로컬 작성 근거이며 Bifrost에는 그래프와 기존 근거만 제출합니다.</p><div id="expression-records"></div></section><section class="card"><h2>명시적 소스 ID</h2>'+state.sources.map(s=>'<p><code>['+esc(s.definition.id)+']</code> · '+esc(s.definition.equipmentInstanceId)+' · '+esc(s.definition.unit.code||s.definition.unit.status)+'</p>').join('')+'</section>';
 loadExpressions();
 for(const id of ['expression-id','expression-equipment','expression-text','expression-version'])$(id).addEventListener('input',()=>{dirty=true;expressionCompilation=null;$('expression-apply').disabled=true;$('expression-summary').textContent='';});
}
async function loadExpressions(){
 try{const data=await expressionApi('/api/expressions');if(tab!=='expressions')return;expressionRows=data.recipes;$('expression-records').innerHTML=data.recipes.length?data.recipes.map(r=>'<article><h3>'+esc(r.graphId)+' · '+esc(r.state)+'</h3><pre>'+esc(r.compilation.expression)+'</pre><p>저장 revision '+r.savedRevision+' · 이력 '+r.history.length+'개 · 출력 expr-result / '+esc(r.compilation.output.valueType)+' / '+esc(r.compilation.output.unit.code)+'</p><button type="button" data-expression-edit="'+esc(r.graphId)+'">원문 다시 열기</button><details><summary>컴파일·소스 pin·전체 작성 이력</summary><pre>'+esc(JSON.stringify(r,null,2))+'</pre></details></article>').join(''):'<p>저장한 수식이 없습니다.</p>';}catch(e){message(e.message,true);}
}
const renderBeforeExpressions=render;
render=function(){if(tab==='expressions'){document.querySelectorAll('[data-tab]').forEach(b=>b.classList.toggle('active',b.dataset.tab===tab));expressionView();}else renderBeforeExpressions();};
async function compileExpression(apply){
 if(busy||conflict)return;busy=true;$('expression-apply').disabled=true;
 try{
  const body={revision,graphId:val('expression-id'),equipmentInstanceId:val('expression-equipment'),expression:$('expression-text').value,compilerVersion:val('expression-version')};
  const data=await expressionApi(apply?'/api/expression-apply':'/api/expression-compile',body);expressionCompilation=data;
  if(apply){display(data.saved);dirty=false;await loadExpressions();message('수식 원문과 그래프를 함께 저장했습니다. 객체 매핑에서 expr-result를 매핑하고 검증에서 가상 입력을 확인하세요.');}else message('컴파일한 그래프와 단위·근거를 확인한 뒤 저장하세요.');
  const c=data.compilation;const literals=(c.literalOrigins||[]).map(o=>'<li><code>'+esc(c.expression.slice(o.start,o.end))+'</code> → '+esc(o.value)+' / '+esc(o.unit)+' · <code>'+esc(o.sourceId)+'</code></li>').join('');$('expression-summary').innerHTML=(literals?'<h3>명시적 상수 · synthetic 작성 근거</h3><ul>'+literals+'</ul>':'')+'<h3>컴파일 결과 · '+esc(c.output.valueType)+' / '+esc(c.output.unit.code)+'</h3><ol>'+c.graph.nodes.map(n=>{const o=c.origins.find(o=>o.nodeId===n.nodeId);return '<li><strong>'+esc(n.nodeId)+' · '+esc(n.op)+'</strong> → '+esc(n.valueType)+' / '+esc(n.unit.code)+'<p><code>'+esc(c.expression.slice(o.start,o.end))+'</code></p>'+(n.op==='divide'||n.op==='sqrt'?'<p>유효숫자 34자리 · half-even · 실제 손실은 09 미리보기에서 확인</p>':'')+'</li>';}).join('')+'</ol><p>출력 expr-result를 06 객체 매핑에서 명시적으로 연결하세요.</p>';
  $('expression-result').textContent=JSON.stringify(data.compilation,null,2);$('expression-apply').disabled=false;
 }catch(e){expressionCompilation=null;$('expression-summary').textContent='컴파일 실패 · 저장하지 않았습니다.';$('expression-result').textContent=e.message;message(e.message,true);}finally{busy=false;}
}
document.addEventListener('submit',event=>{if(event.target.id==='expression-form'){event.preventDefault();compileExpression(false);}});
document.addEventListener('click',event=>{
 const b=event.target.closest('button');if(!b||busy)return;
 if(b.id==='expression-apply'){compileExpression(true);return;}
 if(b.dataset.expressionEdit){const r=expressionRows.find(x=>x.graphId===b.dataset.expressionEdit);$('expression-version').value=r.compilation.compilerVersion;$('expression-id').value=r.graphId;$('expression-equipment').value=r.compilation.graph.equipmentInstanceId;$('expression-text').value=r.compilation.expression;expressionCompilation=null;$('expression-apply').disabled=true;$('expression-summary').textContent='';$('expression-result').textContent='저장된 원문을 다시 컴파일해 현재 소스와 비교하세요.';dirty=false;}
});
