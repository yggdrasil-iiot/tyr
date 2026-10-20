/* P3-E B canonical logical models: explicit leaves, never vendor native layout. */
const collectBeforeStructures=collectObjectMapping;
collectObjectMapping=function(){
 const result=collectBeforeStructures();if(!v2Mode())return result;
 const t=state.targets.find(t=>t.id===result.targetInstanceRef.id),model=state.semantics.find(s=>s.id===t.semanticDefinitionRef.id);
 if(model.schemaVersion==="2.12.0")result.schemaVersion="2.12.0";
 return result;
};
const semanticBeforeStructures=semanticView;
semanticView=function(){
 const d=editing?.kind==="semantic"?state.semantics.find(s=>s.id===editing.id):null;
 if(d?.schemaVersion==="2.12.0")return structuresView();
 semanticBeforeStructures();
};
function structureDefinitionPaths(nodes,path=[]){
 return nodes.flatMap(n=>[{path:[...path,n.memberId],node:n},...(["Structure","StructureArray"].includes(n.valueType)?structureDefinitionPaths(n.members,[...path,n.memberId]):[])]);
}
function structuresView(){
 if(!v2Mode())return migrationView();
 const d=editing?.kind==="semantic"?state.semantics.find(s=>s.id===editing.id):null;
 const initial=d?.members||[{memberId:"process",name:"공정",semanticId:"urn:tyr:concept:process",description:"논리 구조 · 물리적 바이트 배치 없음",valueType:"Structure",members:[{memberId:"actual",name:"실제값",semanticId:"urn:tyr:concept:process.actual",description:"소스별 단위·스케일을 명시적으로 매핑",valueType:"Double",unit:{status:"known",code:"1"},role:"measurement",range:null}]}];
 shell("15 / 논리 구조·중첩·구조 배열","각 말단 프로퍼티를 객체 매핑에서 소스/그래프에 매핑합니다. 고정 shape·lowerBounds는 논리 인덱스이며 PLC UDT/DB packing·alignment·stride를 추정하지 않습니다. 최대 깊이 8, 정의 노드 256, 확장 말단 256개입니다.",
 '<form id="structure-model-form"><div class="fields">'+field("structure-id","의미 모델 ID",d?.id||"","text",true)+field("structure-version","모델 버전",d?.version||"1.0.0","text",true)+'</div>'+area("structure-members","논리 members JSON · 편집/검토",JSON.stringify(initial,null,2))+
 '<details open><summary>구조·배열·프로퍼티 추가</summary><div class="fields">'+select("structure-parent","추가할 부모",[])+field("structure-member-id","새 멤버 ID","value","text",true)+field("structure-member-name","표시 이름","값","text",true)+field("structure-semantic-id","정준 의미 URI","urn:tyr:concept:value","text",true)+select("structure-node-type","종류",[["Double","수치 Double"],["Int32","정수 Int32"],["Boolean","상태 Boolean"],["String","문자열"],["Structure","중첩 구조"],["StructureArray","고정 구조 배열"]],"Double")+select("structure-node-unit","말단 단위",unitOptions,"1")+select("structure-node-role","말단 역할",[["measurement","measurement"],["status","status"],["setpoint","setpoint"]],"measurement")+field("structure-shape","배열 shape (JSON)","[2]","text")+field("structure-lower","배열 lowerBounds (JSON)","[1]","text")+'</div><button type="button" id="structure-add">멤버 추가</button></details><button type="button" class="secondary" id="structure-tree-refresh">트리 확인</button> <button type="submit">논리 모델 저장</button></form><section id="structure-tree"></section>'+
 '<h2>객체 전체 가상 미리보기</h2><form id="logical-preview-form">'+select("logical-target","대상 객체",state.targets.map(t=>[t.id,t.label+" · "+t.id]))+area("logical-samples","가상 입력 JSON · 소스 ID별 bytesHex/typedValue/typedValues","{}")+area("logical-evaluation","시간·품질 평가 기준 JSON · 없으면 null","null")+'<p>09의 말단별 미리보기와 같은 디코더·cast·시간/품질 규칙을 사용합니다. 하나라도 bad/미매핑이면 전체 result는 null, 진단용 partialResult는 별도로 표시합니다. 동시 snapshot 및 프로퍼티 간 skew를 보장하지 않습니다.</p><button type="submit">객체 조립 미리보기 · 저장하지 않음</button></form><section id="logical-preview-result"></section>',
 records(state.semantics.filter(s=>s.schemaVersion==="2.12.0"),"semantic",m=>modelLeaves(m).length+"개 말단 · 논리 모델"));
 if(d)$("structure-id").readOnly=true;
 function tree(){
  const members=JSON.parse($("structure-members").value),paths=structureDefinitionPaths(members);
  $("structure-parent").innerHTML=[["[]","최상위"],...paths.filter(p=>["Structure","StructureArray"].includes(p.node.valueType)).map(p=>[JSON.stringify(p.path),p.path.join(" / ")])].map(([v,label])=>'<option value="'+esc(v)+'">'+esc(label)+'</option>').join("");
  let leaves;try{leaves=modelLeaves({schemaVersion:"2.12.0",members});}catch(e){$("structure-tree").textContent=e.message;return;}
  $("structure-tree").innerHTML='<h3>확장된 말단 경로 · '+leaves.length+'개</h3><div class="table-scroll"><table><thead><tr><th>경로 · 배열 인덱스</th><th>의미 URI</th><th>타입 · 단위</th></tr></thead><tbody>'+leaves.map(m=>'<tr><td><code>'+esc(m._label)+'</code></td><td>'+esc(m.semanticId)+'</td><td>'+esc(m.valueType)+" / "+esc(unitValue(m.unit))+'</td></tr>').join("")+'</tbody></table></div>';
 }
 $("structure-tree-refresh").onclick=()=>{try{tree();}catch(e){message(e.message,true);}};
 $("structure-add").onclick=()=>{
  try{
   const members=JSON.parse($("structure-members").value),path=JSON.parse(val("structure-parent"));let nodes=members;
   for(const id of path){const n=nodes.find(n=>n.memberId===id);if(!n?.members)throw Error("부모 구조가 없습니다.");nodes=n.members;}
   const valueType=val("structure-node-type"),id=val("structure-member-id");
   if(nodes.some(n=>n.memberId===id))throw Error("같은 부모에 중복 멤버 ID가 있습니다.");
   const n={memberId:id,name:val("structure-member-name"),semanticId:val("structure-semantic-id"),description:"명시적 논리 멤버 · native 배치 미검증",valueType};
   if(["Structure","StructureArray"].includes(valueType)){n.members=[];if(valueType==="StructureArray"){n.shape=JSON.parse(val("structure-shape"));n.lowerBounds=JSON.parse(val("structure-lower"));}}
   else Object.assign(n,{unit:unit("structure-node-unit"),role:val("structure-node-role"),range:null});
   nodes.push(n);$("structure-members").value=JSON.stringify(members,null,2);dirty=true;tree();
  }catch(e){message(e.message,true);}
 };
 function sampleDefaults(){
  const target=state.targets.find(t=>t.id===val("logical-target"));if(!target)return;
  const ids=new Set(state.mappings.filter(m=>m.targetInstanceRef.id===target.id).flatMap(m=>m.mappings.flatMap(b=>previewSources(b))));
  const samples={};
  for(const id of ids){
   const s=state.sources.find(s=>s.definition.id===id)?.definition;if(!s)continue;
   samples[id]=s.rawRepresentation.mode==="typed"?(s.fixedArray?{typedValues:Array(previewWidth(s)).fill("0")}:{typedValue:s.rawRepresentation.valueType==="Boolean"?false:s.rawRepresentation.valueType==="String"?"":"0"}):{bytesHex:"00".repeat(previewWidth(s))};
  }
  $("logical-samples").value=JSON.stringify(samples,null,2);
 }
 $("logical-target").onchange=sampleDefaults;tree();sampleDefaults();
}
const renderBeforeStructures=render;
render=function(){
 if(tab==="structures"){document.querySelectorAll("[data-tab]").forEach(b=>b.classList.toggle("active",b.dataset.tab===tab));structuresView();}
 else renderBeforeStructures();
};
document.addEventListener("submit",async e=>{
 if(!["structure-model-form","logical-preview-form"].includes(e.target.id))return;
 e.preventDefault();if(busy||conflict)return;
 try{
  if(e.target.id==="structure-model-form"){
   const model={kind:"semantic-definition",schemaVersion:"2.12.0",id:val("structure-id"),version:val("structure-version"),members:JSON.parse($("structure-members").value)};
   modelLeaves(model);const next=structuredClone(state);upsert(next.semantics,model);await save(next);
  }else{
   busy=true;
   const t=state.targets.find(t=>t.id===val("logical-target"));if(!t)throw Error("대상 객체가 없습니다.");
   const evaluation=JSON.parse($("logical-evaluation").value);
   const body={revision,targetInstanceRef:ref(t),samples:JSON.parse($("logical-samples").value),...(evaluation===null?{}:{evaluationContext:evaluation})};
   const response=await fetch("/api/logical-preview",{method:"POST",headers:{"Content-Type":"application/json","X-Tyr-Editor":"1"},body:JSON.stringify(body)}),result=await response.json();
   if(!response.ok)throw Error(result.error);
   $("logical-preview-result").innerHTML='<h2>조립 결과 · '+esc(result.quality)+'</h2><h3>전체 result</h3><pre>'+esc(JSON.stringify(result.result,null,2))+'</pre><details><summary>진단용 partialResult · 배열 shape/하한 · 오류</summary><pre>'+esc(JSON.stringify({partialResult:result.partialResult,arrays:result.arrays,issues:result.issues},null,2))+'</pre></details>'+result.members.map(m=>'<details><summary>'+esc(m.label)+' · '+esc(m.report.quality)+'</summary><pre>'+esc(JSON.stringify(m.report,null,2))+'</pre></details>').join("");
  }
 }catch(err){message(err.message,true);}finally{busy=false;}
});
