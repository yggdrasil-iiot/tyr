/* P3-A 2.0 object/graph authoring, no device access. */
function memberPathKey(p){return JSON.stringify(p.map(x=>x.kind==="member"?["member",x.memberId]:["index",x.indices]));}
function memberPathLabel(p){let out="";for(const x of p){if(x.kind==="index")out+="["+x.indices.join(",")+"]";else if(/^[a-z][a-z0-9_-]*$/.test(x.memberId))out+=(out?".":"")+x.memberId;else out+="["+JSON.stringify(x.memberId)+"]";}return out;}
function modelLeaves(model){
 if(model.schemaVersion!=="2.12.0")return model.members.map(n=>({...n,_path:[{kind:"member",memberId:n.memberId}],_label:n.memberId}));
 const out=[];
 function walk(nodes,paths,depth){
  if(depth>8)throw Error("structure.depth");
  for(const n of nodes){
   const next=paths.map(p=>[...p,{kind:"member",memberId:n.memberId}]);
   if(n.valueType==="Structure")walk(n.members,next,depth+1);
   else if(n.valueType==="StructureArray"){
    if(n.shape.length!==n.lowerBounds.length||n.shape.reduce((a,b)=>a*b,1)>256)throw Error("structure.array-range");
    let indices=[[]];n.shape.forEach((s,k)=>{indices=indices.flatMap(ix=>Array.from({length:s},(_,i)=>[...ix,n.lowerBounds[k]+i]));});
    const expanded=next.flatMap(p=>indices.map(indices=>[...p,{kind:"index",indices}]));
    if(expanded.length>256)throw Error("structure.size");
    walk(n.members,expanded,depth+1);
   }else for(const p of next){if(out.length>=256)throw Error("structure.size");out.push({...n,_path:p,_label:memberPathLabel(p)});}
  }
 }
 walk(model.members,[[]],1);return out;
}
function memberForPath(model,path){return modelLeaves(model).find(m=>memberPathKey(m._path)===memberPathKey(path));}
const v2Mode=()=>state?.workspaceVersion==="2.0.0";
let refsFor=(ids)=>{const seen=new Map();for(const id of ids){const s=state.sources.find(r=>r.definition.id===id)?.definition;for(const e of s?.evidenceRefs||[])seen.set(JSON.stringify(e),e);}return [...seen.values()];};
function validateGraphDependencies(candidate){
 const graphs=[...state.graphs.filter(g=>g.id!==candidate.id),candidate],by=new Map(graphs.map(g=>[g.id+'@'+g.version,g])),done=new Set(),active=new Set();
 function visit(g,path){const key=g.id+'@'+g.version;if(active.has(key))throw Error('graph.dependency-cycle · '+[...path,key].join(' → '));if(done.has(key))return;if(path.length>=32)throw Error('graph.dependency-depth');active.add(key);
 for(const n of g.nodes)for(const e of Object.values(n.inputs)){if(e.kind!=='graph')continue;const parent=by.get(e.graphRef.id+'@'+e.graphRef.version);if(!parent)throw Error('reference.missing');if(parent.equipmentInstanceId!==g.equipmentInstanceId)throw Error('value.equipment');if(!parent.nodes.some(n=>n.nodeId===e.nodeId))throw Error('graph.node-missing');visit(parent,[...path,key]);}
 active.delete(key);done.add(key);}
 for(const g of graphs)visit(g,[]);
}
function graphSources(graph,nodeId,visiting=new Set()){
 const key=graph.id+'@'+graph.version+'/'+nodeId;if(visiting.has(key))return [];
 const n=graph.nodes.find(n=>n.nodeId===nodeId);if(!n)return [];
 const seen=new Set(visiting);seen.add(key);
 return [...new Set(Object.values(n.inputs).flatMap(e=>{if(e.kind==='source')return [e.sourceRef.id];const g=e.kind==='graph'?state.graphs.find(g=>g.id===e.graphRef.id&&g.version===e.graphRef.version):graph;return g?graphSources(g,e.nodeId,seen):[];}))];
}
function graphAddress(graph,nodeId,seen=new Set()){
 if(!graph)return "참조 없음";const key=graph.id+"@"+graph.version+"/"+nodeId;if(seen.has(key))return "순환";const n=graph.nodes.find(n=>n.nodeId===nodeId);if(!n)return "미확인 노드";
 const next=new Set(seen);next.add(key);
 const label=e=>!e?"미확인":e.kind==="source"?(state.sources.find(s=>s.definition.id===e.sourceRef.id)?.definition.rawAddressText||e.sourceRef.id):e.kind==="graph"?(e.graphRef.id+"@"+e.graphRef.version+"/"+e.nodeId+" → "+graphAddress(state.graphs.find(g=>g.id===e.graphRef.id&&g.version===e.graphRef.version),e.nodeId,next)):graphAddress(graph,e.nodeId,next);
 if(n.op==="bounded-selector")return "selector ["+Object.keys(n.inputs).filter(k=>k.startsWith("candidate")).sort((a,b)=>Number(a.slice(9))-Number(b.slice(9))).map(k=>k.slice(9)+": "+label(n.inputs[k])).join(" | ")+"]";
 return n.op==="decode-u32-words"?"low "+label(n.inputs.low)+" · high "+label(n.inputs.high):["subtract","add","multiply","divide"].includes(n.op)?"("+label(n.inputs.left)+" "+({subtract:"−",add:"+",multiply:"×",divide:"÷"}[n.op])+" "+label(n.inputs.right)+")":n.op==="linear"?"("+label(n.inputs.value)+" × "+n.factor+" + "+n.offset+")":n.op==="unit-convert"?label(n.inputs.value)+" "+n.from+" → "+n.to:label(n.inputs.value);
}
function valueInfo(v){
 if(v?.kind==="source"){const row=state.sources.find(r=>r.definition.id===v.sourceRef.id);return row?{name:row.label||row.definition.id,address:row.definition.rawAddressText,type:row.definition.rawRepresentation.valueType,unit:row.definition.unit,stage:row.definition.inputStage,sources:[row.definition.id]}:null;}
 const graph=state.graphs?.find(g=>g.id===v?.graphRef?.id),node=graph?.nodes.find(n=>n.nodeId===v.nodeId);if(!node)return null;
 const ids=graphSources(graph,node.nodeId);
 return {name:graph.id+" / "+node.nodeId,address:graphAddress(graph,node.nodeId),type:node.valueType,unit:node.unit,stage:"graph result",sources:ids};
}
function selectedValue(text){if(!text)return null;const [kind,id,nodeId]=JSON.parse(text);return kind==="source"?{kind,sourceRef:ref(state.sources.find(r=>r.definition.id===id).definition)}:{kind:"graph",graphRef:ref(state.graphs.find(g=>g.id===id)),nodeId};}
function valueOptions(equipment){
 return [...state.sources.filter(r=>r.definition.equipmentInstanceId===equipment).map(r=>[JSON.stringify(["source",r.definition.id]),"소스 · "+(r.label||r.definition.id)+" · "+r.definition.rawAddressText]),
 ...state.graphs.filter(g=>g.equipmentInstanceId===equipment).flatMap(g=>g.nodes.map(n=>[JSON.stringify(["graph",g.id,n.nodeId]),"그래프 · "+g.id+" / "+n.nodeId+" · "+n.valueType]))];
}
function valueKey(v){return !v?"":v.kind==="source"?JSON.stringify(["source",v.sourceRef.id]):JSON.stringify(["graph",v.graphRef.id,v.nodeId]);}
function migrationView(){
 if(v2Mode()){shell("작성본 이전 기록","2.0 작성본입니다. 이전 전 SQLite 백업과 객체 ID 배정을 확인할 수 있습니다.","<p>현재 revision "+revision+"</p>",'<p>이전 revision: '+esc(window.migrationInfo?.revision)+'</p><p>백업 파일<br><code>'+esc(window.migrationInfo?.backup)+'</code></p><h3>매핑별 객체 ID</h3>'+Object.entries(window.migrationInfo?.assignments||{}).map(([map,id])=>'<p><code>'+esc(map)+'</code> → <strong>'+esc(id)+'</strong></p>').join(''));return;}
 shell("1.x → 2.0 작성본 이전","기존 매핑마다 안정된 객체 ID를 지정합니다. 이전 전에 SQLite 백업을 생성하며 원래 접근 정의·의미·변환은 보존합니다.",
 '<form id="migration-form">'+state.mappings.map((m,i)=>field("migrate-"+i,m.id+" · "+m.equipmentInstanceId,"object-"+m.id,"text",true)).join("")+'<button type="submit">백업하고 2.0으로 이전</button></form>',
 '<p>설비 ID와 객체 ID는 별도입니다. 다른 객체에는 서로 다른 ID를 지정하세요. 빈 작성본도 2.0으로 시작할 수 있습니다.</p>');
}
function targetView(){
 if(!v2Mode())return migrationView();
 const d=editing?.kind==="target"?state.targets.find(x=>x.id===editing.id):null;
 shell("04 / 객체 인스턴스","같은 설비 안에 여러 객체를 등록하고 같은 의미 모델을 재사용합니다. 표시 이름을 바꾸어도 객체 ID는 유지됩니다.",
 '<form id="target-form"><div class="fields">'+field("target-id","안정된 객체 ID",d?.id||"","text",true)+field("target-label","표시 이름",d?.label||"","text",true)+select("target-equipment","소속 설비",state.equipment.map(e=>[e.id,e.label]),d?.equipmentInstanceId)+select("target-model","의미 모델",state.semantics.map(s=>[s.id,s.id]),d?.semanticDefinitionRef.id)+select("target-evidence","근거 소스",state.sources.map(s=>[s.definition.id,s.definition.id]),d?.evidenceRefs?.[0]?.artifactId?.replace(/^manual-/,""))+'</div><button type="submit">객체 저장</button></form>',
 records(state.targets,"target",t=>t.label+" · "+t.equipmentInstanceId+" → "+t.semanticDefinitionRef.id));
 if(d){$("target-id").readOnly=true;$("target-equipment").disabled=true;$("target-model").disabled=true;}
}
let graphDraft=[];
function externalNode(text){const e=endpoint(text);return state.graphs.find(g=>g.id===e.graphRef.id&&g.version===e.graphRef.version)?.nodes.find(n=>n.nodeId===e.nodeId);}
function endpointKey(e){return !e?"":e.kind==="source"?"s:"+e.sourceRef.id:e.kind==="graph"?"g:"+[e.graphRef.id,e.graphRef.version,e.nodeId].join("|"):"n:"+e.nodeId;}
function endpoint(text){if(text.startsWith("g:")){const [id,version,nodeId]=text.slice(2).split("|");return {kind:"graph",graphRef:{id,version},nodeId};}return text.startsWith("s:")?{kind:"source",sourceRef:ref(state.sources.find(s=>s.definition.id===text.slice(2)).definition)}:{kind:"node",nodeId:text.slice(2)};}
function graphNodeCards(){
 const equipment=val("graph-equipment");
 const choices=[...state.sources.filter(s=>s.definition.equipmentInstanceId===equipment).map(s=>["s:"+s.definition.id,s.definition.rawAddressText+" · "+s.definition.id]),...graphDraft.map(n=>["n:"+n.nodeId,"노드 · "+n.nodeId]),...state.graphs.filter(g=>g.id!==val("graph-id")&&g.equipmentInstanceId===equipment).flatMap(g=>g.nodes.filter(n=>n.valueType!=="FixedArray").map(n=>["g:"+[g.id,g.version,n.nodeId].join("|"),"외부 그래프 · "+g.id+"@"+g.version+" / "+n.nodeId+" · "+n.valueType+" / "+unitValue(n.unit)]))];
 $("graph-nodes").innerHTML=graphDraft.map((n,i)=>'<article class="graph-node"><h3>노드 '+(i+1)+'</h3><div class="fields">'+field("node-id-"+i,"노드 ID",n.nodeId,"text",true)+select("node-op-"+i,"연산",[["add","left + right · 같은 선형 단위"],["multiply","left × right · 한 입력은 무차원"],["divide","left ÷ right · 34자리 half-even"],["sqrt","무차원 제곱근 · 34자리 half-even"],["clamp","같은 단위의 범위 제한"],["decode-u32-words","두 UInt16 → UInt32"],["identity","입력 전달"],["subtract","left − right · 차압"],["linear","입력 스케일 × factor + offset"],["unit-convert","입력 단위 변환"],["array-element","고정 배열 요소 선택"],["bounded-selector","유한 소스·그래프 후보 선택"]],n.op)+
 (n.op==="bounded-selector"?select("node-index-"+i,"현재 인덱스 소스 · 0부터",choices.filter(x=>x[0].startsWith("s:")),endpointKey(n.inputs.index))+select("node-previousIndex-"+i,"이전 인덱스 소스 · 선택 사항",[["","비교 안 함"],...choices.filter(x=>x[0].startsWith("s:"))],endpointKey(n.inputs.previousIndex))+field("node-candidates-"+i,"후보 · 소스 ID, n:노드ID, g:그래프ID|버전|노드ID · 쉼표 순서",Object.keys(n.inputs).filter(k=>k.startsWith("candidate")).sort((a,b)=>Number(a.slice(9))-Number(b.slice(9))).map(k=>n.inputs[k].kind==="source"?n.inputs[k].sourceRef.id:endpointKey(n.inputs[k])).join(", "),"text",true)+select("node-policy-"+i,"범위 초과 정책",[["reject","오류로 차단"],["default-candidate","명시한 기본 후보 사용"]],n.outOfRange||"reject")+field("node-default-"+i,"기본 후보 인덱스",n.defaultCandidate??0,"number"):["subtract","add","multiply","divide"].includes(n.op)?select("node-left-"+i,"left · 왼쪽 입력",choices,endpointKey(n.inputs.left))+select("node-right-"+i,"right · 오른쪽 입력",choices,endpointKey(n.inputs.right)):n.op==="decode-u32-words"?select("node-low-"+i,"low · 하위 워드",choices,endpointKey(n.inputs.low))+select("node-high-"+i,"high · 상위 워드",choices,endpointKey(n.inputs.high)):select("node-value-"+i,"입력",choices,endpointKey(n.inputs.value)))+
 (n.op==="divide"?"<p>분모 0은 오류입니다. 유효숫자 34자리 half-even, 비정확한 결과는 loss.precision으로 표시합니다.</p>":n.op==="clamp"?field("node-bound-low-"+i,"하한 · 입력과 같은 단위",n.low??"0","text",true)+field("node-bound-high-"+i,"상한 · 입력과 같은 단위",n.high??"100","text",true):n.op==="sqrt"?"<p>무차원 1 전용 · 유효숫자 34자리 · half-even. 근사 손실은 미리보기에 표시됩니다.</p>":n.op==="array-element"?field("node-indices-"+i,"요소 indices (JSON)",JSON.stringify(n.indices||[0]),"text",true):n.op==="linear"?field("node-factor-"+i,"factor (정확한 십진수)",n.factor??"1","text",true)+field("node-offset-"+i,"offset",n.offset??"0","text",true):n.op==="unit-convert"?select("node-from-"+i,"입력 단위",unitOptions.filter(x=>!["unknown","not-applicable"].includes(x[0])),n.from||"bar")+select("node-to-"+i,"변환 단위",unitOptions.filter(x=>!["unknown","not-applicable"].includes(x[0])),n.to||"kPa"):"")+select("node-type-"+i,"출력 타입",(["subtract","add","multiply","divide","linear","unit-convert","sqrt","clamp"].includes(n.op)?["Decimal"]:n.op==="decode-u32-words"?["UInt32"]:n.op==="array-element"?["UInt16","UInt32","Int16","Int32","Int64","Float32","Float64","Boolean"]:["UInt16","UInt32","Int16","Int32","Int64","Float32","Float64","Double","Boolean","String","Decimal","FixedArray"]).map(x=>[x,x]),n.valueType)+select("node-unit-"+i,"출력 단위",unitOptions,unitValue(n.unit))+'</div><button type="button" class="secondary" data-remove-node="'+i+'">노드 제거</button></article>').join("");
 graphDraft.forEach((n,i)=>{
 if(n.op!=="bounded-selector")return;
 const card=$("node-candidates-"+i).closest("article");
 card.insertAdjacentHTML("beforeend",'<div class="fields">'+select("candidate-picker-"+i,"추가할 후보 · 소스·현재/외부 그래프 출력",choices.filter(x=>x[0]!=="n:"+n.nodeId).map(([key,label])=>{const d=key.startsWith("g:")?externalNode(key):key.startsWith("n:")?graphDraft.find(v=>v.nodeId===key.slice(2)):state.sources.find(v=>v.definition.id===key.slice(2))?.definition;return [key,label+" · "+(d?.valueType||d?.rawRepresentation?.valueType||"?")+" / "+unitValue(d?.unit)];}),"")+'</div><button type="button" class="secondary" id="candidate-add-'+i+'">후보 목록 끝에 추가</button><div id="candidate-summary-'+i+'"></div>');
 const summary=()=>{const tokens=$("node-candidates-"+i).value.split(",").map(v=>v.trim()).filter(Boolean);$("candidate-summary-"+i).innerHTML='<p>모든 후보는 selector 출력 '+esc($("node-type-"+i).value)+' / '+esc($("node-unit-"+i).value)+'와 일치해야 합니다.</p><ol start="0">'+tokens.map(t=>{const d=t.startsWith("g:")?externalNode(t):t.startsWith("n:")?graphDraft.find(v=>v.nodeId===t.slice(2)):state.sources.find(v=>v.definition.id===t.replace(/^s:/,""))?.definition;return '<li>'+esc(t)+' · '+esc(d?.valueType||d?.rawRepresentation?.valueType||"미확인")+' / '+esc(d?unitValue(d.unit):"미확인")+'</li>';}).join("")+'</ol>';};
 $("candidate-add-"+i).onclick=()=>{const value=$("candidate-picker-"+i).value;if(!value)return;const field=$("node-candidates-"+i);if(field.value.split(",").filter(v=>v.trim()).length>=32){message("후보는 최대 32개입니다.",true);return;}field.value+=(field.value.trim()?", ":"")+value;dirty=true;summary();};
 $("node-candidates-"+i).oninput=summary;summary();
 });
 graphDraft.forEach((n,i)=>{$("node-op-"+i).onchange=()=>{const nodes=readGraphNodes(false);nodes[i].op=val("node-op-"+i);nodes[i].inputs={};nodes[i].valueType=nodes[i].op==="array-element"?"UInt16":["subtract","add","multiply","divide","linear","unit-convert","sqrt","clamp"].includes(nodes[i].op)?"Decimal":"UInt32";graphDraft=nodes;graphNodeCards();dirty=true;};});
}
function readGraphNodes(strict=true){
 return graphDraft.map((n,i)=>{
 const op=val("node-op-"+i),names=op==="bounded-selector"?["index","previousIndex"]:["subtract","add","multiply","divide"].includes(op)?["left","right"]:op==="decode-u32-words"?["low","high"]:["value"],inputs={};
 for(const name of names){const el=$("node-"+name+"-"+i),text=el?.value||"";if(!text&&strict&&name!=="previousIndex")throw Error("노드 입력을 선택하세요.");if(text)inputs[name]=endpoint(text);}
 if(op==="bounded-selector"){const ids=($("node-candidates-"+i)?.value||"").split(",").map(x=>x.trim()).filter(Boolean);ids.forEach((id,j)=>{if(id.startsWith("g:")){inputs["candidate"+j]=endpoint(id);}else if(id.startsWith("n:")){inputs["candidate"+j]={kind:"node",nodeId:id.slice(2)};}else{const sid=id.startsWith("s:")?id.slice(2):id,s=state.sources.find(s=>s.definition.id===sid);if(!s)throw Error("후보 소스 없음: "+sid);inputs["candidate"+j]={kind:"source",sourceRef:ref(s.definition)};}});}
 return {nodeId:val("node-id-"+i),op,inputs,...(op==="bounded-selector"?{outOfRange:$("node-policy-"+i)?.value||"reject",...($("node-policy-"+i)?.value==="default-candidate"?{defaultCandidate:Number($("node-default-"+i)?.value||0)}:{})}:{}),...(["sqrt","divide"].includes(op)?{precision:34,rounding:"half-even"}:op==="clamp"?{low:$("node-bound-low-"+i)?.value||"0",high:$("node-bound-high-"+i)?.value||"100"}:op==="array-element"?{indices:JSON.parse($("node-indices-"+i)?.value||"[0]")}:op==="linear"?{factor:$("node-factor-"+i)?val("node-factor-"+i):"1",offset:$("node-offset-"+i)?val("node-offset-"+i):"0"}:op==="unit-convert"?{from:$("node-from-"+i)?val("node-from-"+i):"bar",to:$("node-to-"+i)?val("node-to-"+i):"kPa"}:{}),valueType:val("node-type-"+i),unit:unit("node-unit-"+i),evidenceRefs:[]};
 });
}
function graphView(){
 if(!v2Mode())return migrationView();
 const d=editing?.kind==="graph"?state.graphs.find(g=>g.id===editing.id):null;
 graphDraft=structuredClone(d?.nodes||[{nodeId:"counter",op:"decode-u32-words",inputs:{},valueType:"UInt32",unit:{status:"known",code:"1"},evidenceRefs:[]}]);
 shell("05 / 여러 주소 → 하나의 값","low/high 조합과 차압(left − right), 입력별 스케일·단위 변환, 고정 배열 요소와 유한 후보 선택을 작성합니다. selector는 0부터 시작하는 정수 인덱스와 최대 32개 scalar 소스·현재 그래프 노드·외부 그래프 결과 후보를 사용합니다. 후보 필드에는 소스 ID, n:노드ID, g:그래프ID|버전|노드ID를 순서대로 입력합니다. 각 노드 카드에서 후보의 타입·단위를 확인하고, 미리보기에서 선택 경로와 출처 변경을 확인합니다. 기본 후보는 범위 초과 시에만 적용하며 선택된 입력 오류를 대신하지 않습니다. 새 덧셈은 같은 선형 단위, 곱셈은 한 입력이 무차원 1인 경우, 나눗셈은 무차원 분모 또는 같은 단위의 비율만 지원합니다. Cel/K·복합 차원·임의 식은 제외합니다. 차압은 Pa/kPa/bar 또는 무차원 1의 같은 단위끼리 계산합니다. sqrt는 무차원 값만 허용하고 34자리 half-even 근사 손실을 표시합니다. clamp는 같은 단위의 하한·상한을 사용하며 값이 잘리면 loss.clamp를 표시합니다. 다른 그래프의 scalar 결과를 ID·버전·노드로 고정해 재사용할 수 있습니다. 같은 설비만 허용하며 그래프 간 순환·없는 결과·타입/단위/근거 오류를 저장 시 거부합니다. 전체 의존 그래프 깊이는 32, 노드 경로는 128까지입니다. 동일 시점 읽기는 보장하지 않습니다.",
 '<form id="graph-form"><div class="fields">'+field("graph-id","그래프 ID",d?.id||"","text",true)+select("graph-equipment","소속 설비",state.equipment.map(e=>[e.id,e.label]),d?.equipmentInstanceId)+'</div><div id="graph-nodes"></div><button type="button" class="secondary" id="add-node">노드 추가</button> <button type="submit">그래프 저장</button></form>',
 records(state.graphs,"graph",g=>g.equipmentInstanceId+" · "+g.nodes.map(n=>n.nodeId+" ["+n.op+"]").join(", ")));
 if(d)$("graph-id").readOnly=true;
 graphNodeCards();
 $("add-node").onclick=()=>{graphDraft=readGraphNodes(false);let i=graphDraft.length+1;while(graphDraft.some(n=>n.nodeId==="node-"+i))i++;graphDraft.push({nodeId:"node-"+i,op:"identity",inputs:{},valueType:"UInt32",unit:{status:"known",code:"1"},evidenceRefs:[]});graphNodeCards();dirty=true;};
 $("graph-nodes").onclick=e=>{const b=e.target.closest("[data-remove-node]");if(!b)return;graphDraft=readGraphNodes(false);graphDraft.splice(Number(b.dataset.removeNode),1);graphNodeCards();dirty=true;};
 $("graph-equipment").onchange=()=>{graphDraft=readGraphNodes(false).map(n=>({...n,inputs:{}}));graphNodeCards();dirty=true;};
}
const legacyMappingView=mappingView,legacyCollectMapping=collectObjectMapping,legacyComparisonView=comparisonView;
mappingView=function(){
 if(!v2Mode())return legacyMappingView();
 const d=editing?.kind==="mapping"?state.mappings.find(m=>m.id===editing.id):null;
 $("view").innerHTML='<p class="step">06 / 객체별 매핑</p><section class="card"><form id="mapping-form"><div class="fields">'+field("mapping-id","매핑 ID",d?.id||"","text",true)+select("mapping-target","대상 객체",state.targets.map(t=>[t.id,t.label+" · "+t.id+" / "+t.equipmentInstanceId]),d?.targetInstanceRef.id)+'</div><div id="binding-rows"></div><button type="submit">객체 매핑 저장</button></form></section><section class="card records-panel">'+records(state.mappings,"mapping",m=>m.equipmentInstanceId+" / "+m.targetInstanceRef.id+" · "+m.mappings.length+"개")+'<button class="secondary" data-new="1">새로 작성</button></section>';
 if(d)$("mapping-id").readOnly=true;
 const show=()=>{
 const target=state.targets.find(t=>t.id===val("mapping-target")),model=state.semantics.find(s=>s.id===target?.semanticDefinitionRef.id);
 if(!model){$("binding-rows").innerHTML="<p>대상 객체를 먼저 등록하세요.</p>";return;}
 $("binding-rows").innerHTML=modelLeaves(model).map((member,i)=>{
 const m=d?.targetInstanceRef.id===target.id?d.mappings.find(m=>memberPathKey(m.memberPath)===memberPathKey(member._path)):null;
 return '<article class="binding-row"><div><h3>'+esc(member._label)+" · "+esc(member.name)+'</h3><code>'+esc(member.semanticId)+'</code><p>'+esc(member.valueType)+" · "+esc(unitValue(member.unit))+'</p></div><div>'+select("bind-source-"+i,"소스 또는 그래프 결과",valueOptions(target.equipmentInstanceId),valueKey(m?.valueRef),false)+'<p id="source-info-'+i+'"></p></div><div>'+rowOperations(i,member,m)+'</div></article>';
 }).join("");
 modelLeaves(model).forEach((m,i)=>{const showInfo=()=>{const info=valueInfo(selectedValue(val("bind-source-"+i)));$("source-info-"+i).textContent=info?info.address+" · "+info.type+" / "+unitValue(info.unit):"미매핑";};$("bind-source-"+i).onchange=showInfo;showInfo();$("operation-"+i).onchange=()=>{$("op-fields-"+i).innerHTML=operationFields(i,val("operation-"+i));};});
 };
 let previous=val("mapping-target");
 $("mapping-target").onchange=()=>{const populated=[...document.querySelectorAll("[id^=bind-source-]")].some(e=>e.value);if(populated&&!confirm("대상 객체를 바꾸면 입력한 매핑 행이 다시 구성됩니다. 계속할까요?")){$("mapping-target").value=previous;return;}previous=val("mapping-target");show();dirty=true;};show();
};
collectObjectMapping=function(){
 if(!v2Mode())return legacyCollectMapping();
 const target=state.targets.find(t=>t.id===val("mapping-target")),model=state.semantics.find(s=>s.id===target?.semanticDefinitionRef.id);
 if(!model)throw Error("대상 객체를 선택하세요.");
 const previous=state.mappings.find(m=>m.id===val("mapping-id")),mappings=[],usedIds=new Set(state.mappings.flatMap(m=>m.mappings.map(b=>b.mappingId)));
 modelLeaves(model).forEach((member,i)=>{
 const v=selectedValue(val("bind-source-"+i));if(!v)return;
 const info=valueInfo(v),op=val("operation-"+i);let ts=[];
 if(op==="linear")ts.push({op,factor:val("factor-"+i),offset:val("offset-"+i)});
 if(op==="unit-convert"){const from=info.unit.code,to=member.unit.code;if(!conversions[from+"|"+to])throw Error("지원하는 단위 변환 쌍을 선택하세요.");ts.push({op,from,to});}
 if(op==="bit-select")ts.push({op,index:num("bit-"+i)});
 if(op==="enum-map"){const entries=val("enum-"+i).split("\n").filter(x=>x.trim()).map(line=>{const split=line.indexOf("=");if(split<1)throw Error("코드=의미 형식으로 입력하세요.");return {raw:line.slice(0,split).trim(),value:line.slice(split+1).trim()};});ts.push({op,entries,onUnknown:"bad-quality"});}
 if(op==="advanced")ts=JSON.parse(val("pipeline-"+i));else ts.push({op:"cast",to:member.valueType,rounding:val("rounding-"+i),overflow:"error"});
 const old=previous?.mappings.find(m=>memberPathKey(m.memberPath)===memberPathKey(member._path));
 let bindingId=old?.mappingId;
 if(!bindingId){if(model.schemaVersion==="2.12.0"){let seq=1;while(usedIds.has(val("mapping-id")+"-leaf-"+seq))seq++;bindingId=val("mapping-id")+"-leaf-"+seq;usedIds.add(bindingId);}else bindingId=val("mapping-id")+"-"+member.memberId;}
 mappings.push({mappingId:bindingId,valueRef:v,memberPath:member._path,transform:ts,outputUnit:member.unit,invalidValuePolicy:"bad-quality",evidenceRefs:refsFor(info.sources)});
 });
 if(!mappings.length)throw Error("하나 이상의 프로퍼티를 연결하세요.");
 return {kind:"mapping-set",schemaVersion:"2.2.0",id:val("mapping-id"),version:previous?.version||"1.0.0",equipmentInstanceId:target.equipmentInstanceId,targetInstanceRef:ref(target),mappings};
};
comparisonView=function(){
 if(!v2Mode())return legacyComparisonView();
 $("view").innerHTML='<p class="step">07 / 객체와 그래프 조회</p><section class="card"><div class="fields">'+select("compare-model","의미 모델",[["all","모든 모델"],...state.semantics.map(s=>[s.id,s.id])],"all")+select("compare-equipment","표시 설비",[["all","모든 설비"],...state.equipment.map(e=>[e.id,e.label])],"all")+'<label>검색<input id="compare-search" placeholder="객체, 현장 이름, 의미, 주소"></label></div><div id="comparison"></div></section>';
 const show=()=>{
 const all=[];
 for(const map of state.mappings){const target=state.targets.find(t=>t.id===map.targetInstanceRef.id),model=state.semantics.find(s=>s.id===target.semanticDefinitionRef.id);for(const binding of map.mappings){const info=valueInfo(binding.valueRef),member=memberForPath(model,binding.memberPath);all.push({map,target,model,binding,info,member});}}
 const names=new Map();for(const r of all){if(!names.has(r.info?.name))names.set(r.info?.name,new Set());names.get(r.info?.name).add(r.member.semanticId);}
 const query=val("compare-search").toLowerCase(),rows=all.filter(r=>(val("compare-equipment")==="all"||r.map.equipmentInstanceId===val("compare-equipment"))&&(val("compare-model")==="all"||r.model.id===val("compare-model"))&&JSON.stringify(r).toLowerCase().includes(query));
 $("comparison").innerHTML='<p>'+rows.length+'개 바인딩 · 이름은 식별 키가 아닙니다.</p><div class="table-scroll"><table><thead><tr><th>설비 / 객체 ID</th><th>프로퍼티 / 정준 의미</th><th>현장 소스 / 그래프</th><th>입력 → 정준 단위</th><th>변환</th><th>이름 관계</th></tr></thead><tbody>'+rows.map(r=>{
 const alias=new Set(all.filter(x=>x.member.semanticId===r.member.semanticId).map(x=>x.info?.name)).size>1,collision=names.get(r.info?.name)?.size>1;
 return '<tr><td>'+esc(r.map.equipmentInstanceId)+'<strong>'+esc(r.target.label)+'</strong><code>'+esc(r.target.id)+'</code></td><td>'+esc(r.member._label)+" · "+esc(r.member.name)+'<small>'+esc(r.member.semanticId)+'<br>'+esc(r.member.role)+" · "+esc(r.member.valueType)+'</small></td><td>'+esc(r.info?.name)+'<code>'+esc(r.info?.address)+'</code><small>'+esc(r.info?.type)+" · "+esc(r.info?.stage)+'</small></td><td>'+esc(unitValue(r.info?.unit))+" → "+esc(unitValue(r.member.unit))+'</td><td>'+esc(transformText(r.binding.transform))+'</td><td>'+(alias?'<span class="badge">다른 이름 · 같은 의미</span>':"")+(collision?'<span class="badge collision">같은 이름 · 다른 의미</span>':"")+'</td></tr>';
 }).join("")+'</tbody></table></div>';
 };$("compare-equipment").onchange=show;$("compare-model").onchange=show;$("compare-search").oninput=show;show();
};
const oldDisplay=display;
display=function(result){window.migrationInfo=result.migration;oldDisplay(result);if(v2Mode())$("counts").innerHTML+="<br>객체 <strong>"+state.targets.length+"</strong><br>그래프 <strong>"+state.graphs.length+"</strong>";};
const oldRender=render;
render=function(){if(["targets","graphs","migration"].includes(tab)){document.querySelectorAll("[data-tab]").forEach(b=>b.classList.toggle("active",b.dataset.tab===tab));({targets:targetView,graphs:graphView,migration:migrationView}[tab])();}else oldRender();};
document.addEventListener("submit",async event=>{
 if(!["target-form","graph-form","migration-form"].includes(event.target.id))return;
 event.preventDefault();if(busy||conflict)return;
 try{
 if(event.target.id==="migration-form"){
 const assignments=Object.fromEntries(state.mappings.map((m,i)=>[m.id,val("migrate-"+i)]));
 busy=true;const response=await fetch("/api/migrate",{method:"POST",headers:{"Content-Type":"application/json","X-Tyr-Editor":"1"},body:JSON.stringify({revision,assignments})});const result=await response.json();if(!response.ok){if(response.status===409)conflict=true;throw Error(result.error);}
 display(result);dirty=false;editing=null;render();message("백업 후 2.0으로 이전했습니다.");return;
 }
 const next=structuredClone(state);
 if(event.target.id==="target-form"){
 const model=state.semantics.find(s=>s.id===val("target-model")),source=state.sources.find(s=>s.definition.id===val("target-evidence"))?.definition;
 if(!source||source.equipmentInstanceId!==val("target-equipment"))throw Error("소속 설비의 근거 소스를 선택하세요.");
 upsert(next.targets,{kind:"target-instance",schemaVersion:"2.0.0",id:val("target-id"),version:state.targets.find(t=>t.id===val("target-id"))?.version||"1.0.0",equipmentInstanceId:val("target-equipment"),label:val("target-label"),semanticDefinitionRef:ref(model),evidenceRefs:source.evidenceRefs});
 }else{
 const nodes=readGraphNodes(),graph={kind:"value-graph",schemaVersion:nodes.some(n=>Object.values(n.inputs).some(e=>e.kind==="graph"))||state.graphs.find(g=>g.id===val("graph-id"))?.schemaVersion==="2.17.0"?"2.17.0":nodes.some(n=>["add","multiply","divide"].includes(n.op))||state.graphs.find(g=>g.id===val("graph-id"))?.schemaVersion==="2.15.0"?"2.15.0":nodes.some(n=>n.op==="bounded-selector"&&Object.entries(n.inputs).some(([k,e])=>k.startsWith("candidate")&&e.kind==="node"))||state.graphs.find(g=>g.id===val("graph-id"))?.schemaVersion==="2.13.0"?"2.13.0":nodes.some(n=>["sqrt","clamp"].includes(n.op))||state.graphs.find(g=>g.id===val("graph-id"))?.schemaVersion==="2.11.0"?"2.11.0":"2.5.0",id:val("graph-id"),version:state.graphs.find(g=>g.id===val("graph-id"))?.version||"1.0.0",equipmentInstanceId:val("graph-equipment"),nodes};
 validateGraphDependencies(graph);
 for(const n of nodes)n.evidenceRefs=refsFor(graphSources(graph,n.nodeId));
 upsert(next.graphs,graph);
 }
 await save(next);
 }catch(e){message(e.message,true);}finally{busy=false;}
});

if(state)request("GET").then(r=>{display(r);render();}).catch(e=>message(e.message,true));
