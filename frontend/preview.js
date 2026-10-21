/* P3-B virtual inputs. Never persisted or sent to PLCs. */
const oldAccessFieldsB=accessFields,oldSourceViewB=sourceView,oldDraftSourceB=draftSource;
accessFields=function(profile,access={},raw={}){
 let html=oldAccessFieldsB(profile,access,raw);
 if(!["device-register","db-offset"].includes(profiles[profile]?.[1]))return html;
 html=html.replace('<option value="Boolean"','<option value="String"'+(raw.valueType==="String"?' selected':'')+'>String (codec)</option><option value="Boolean"');
 html+='<h3 class="full">원시 해석 옵션</h3>'+select("source-codec","Codec",[["numeric","숫자 / Boolean"],["bcd16","BCD16 → Int32"],["ascii-fixed","고정 ASCII → String"],["s7-date-time","S7 DATE_AND_TIME → UTC 문자열"]],raw.codec?.kind||"numeric")+
 field("codec-length","ASCII 고정 바이트 수",raw.codec?.length||6,"number")+select("codec-termination","ASCII 종료 방식",[["fixed","전체 고정 길이"],["nul","NUL 종료"]],raw.codec?.termination||"nul")+
 select("codec-timezone","S7 원문 시간대",[["unresolved","미확인 · 해석 차단"],["UTC","UTC"],["Asia/Seoul","Asia/Seoul"]],raw.codec?.timezone||"unresolved")+
 select("bit-coordinate","비트 접근 좌표",[["decoded-value","디코딩한 정수의 bit"],["native-byte","원본 바이트의 bit"]],raw.bitCoordinate?.kind||"decoded-value")+field("bit-byte-index","원본 바이트 index",raw.bitCoordinate?.byteIndex||0,"number");
 if(profiles[profile][1]==="device-register")html+=select("address-unit-b","주소 단위",[["word16","16-bit word"],["bit","Native bit · 한 비트"]],access.addressUnit||"word16");
 return html;
};
function wireCodecFields(){
 if(!$("source-codec"))return;
 const visible=()=>{const codec=val("source-codec"),native=$("address-unit-b")&&val("address-unit-b")==="bit",bit=$("bitOffset")&&val("bitOffset")!=="";
 for(const id of ["codec-length","codec-termination"])$(id).closest("label").hidden=codec!=="ascii-fixed";
 $("codec-timezone").closest("label").hidden=codec!=="s7-date-time";
 $("bit-coordinate").closest("label").hidden=native||!bit;
 $("bit-byte-index").closest("label").hidden=native||!bit||val("bit-coordinate")!=="native-byte";
 if($("wordCount"))$("wordCount").closest("label").hidden=native;
 if($("bitOffset"))$("bitOffset").closest("label").hidden=native;
 };
 $("source-codec").onchange=()=>{
 const codec=val("source-codec");
 if(codec==="ascii-fixed"||codec==="s7-date-time"){$("rawType").value="String";$("byteOrder").value="big";$("wordOrder").value="high-first";}
 else if(codec==="bcd16"||val("rawType")==="String")$("rawType").value="UInt16";
 if(codec!=="numeric")$("inputStage").value="raw";
 visible();
 };
 if($("address-unit-b"))$("address-unit-b").onchange=()=>{
 if(val("address-unit-b")==="bit"){$("source-codec").value="numeric";$("rawType").value="Boolean";$("byteOrder").value="big";$("wordOrder").value="high-first";$("source-unit").value="not-applicable";$("bitOffset").value="";if(!["M","X","Y","L","S","B"].includes(val("deviceArea")))$("deviceArea").value="M";}
 visible();
 };
 if($("bitOffset"))$("bitOffset").oninput=visible;
 $("bit-coordinate").onchange=visible;
 $("rawType").onchange=()=>{if(val("rawType")==="String"&&val("source-codec")==="numeric"){$("source-codec").value="ascii-fixed";$("source-codec").onchange();}visible();};
 visible();
}
sourceView=function(){oldSourceViewB();wireCodecFields();const change=$("source-profile").onchange;$("source-profile").onchange=()=>{change();wireCodecFields();};};
draftSource=function(){
 const row=oldDraftSourceB(),d=row.definition;
 if(["Pa","kPa","bar"].includes(d.unit.code)||state.sources.find(r=>r.definition.id===d.id)?.definition.schemaVersion==="2.2.0")d.schemaVersion="2.2.0";
 if(!$("source-codec"))return row;
 const kind=val("source-codec"),raw=d.rawRepresentation;
 if(kind==="bcd16")raw.codec={kind};
 if(kind==="ascii-fixed")raw.codec={kind,length:num("codec-length"),termination:val("codec-termination")};
 if(kind==="s7-date-time")raw.codec={kind,timezone:val("codec-timezone")==="unresolved"?null:val("codec-timezone")};
 if($("address-unit-b")&&val("address-unit-b")==="bit"){d.access.addressUnit="bit";delete d.access.wordCount;d.access.bitCount=1;}
 if(d.access.bitOffset!==null)raw.bitCoordinate=val("bit-coordinate")==="decoded-value"?{kind:"decoded-value"}:{kind:"native-byte",byteIndex:num("bit-byte-index")};
 if(kind!=="numeric"||raw.bitCoordinate||d.access.addressUnit==="bit")d.schemaVersion=d.schemaVersion==="2.2.0"?"2.2.0":"2.1.0";
 else if(state.sources.find(s=>s.definition.id===d.id)?.definition.schemaVersion==="2.1.0")d.schemaVersion=d.schemaVersion==="2.2.0"?"2.2.0":"2.1.0";
 return row;
};
const virtualSamples=new Map();
function virtualInputTextB(id,i){const d=state.sources.find(r=>r.definition.id===id).definition;return d.rawRepresentation.mode==="typed"&&d.rawRepresentation.valueType==="String"?$("virtual-"+i).value:val("virtual-"+i);}
function previewSources(binding){
 const v=binding.valueRef||{kind:"source",sourceRef:binding.sourceRef};
 if(v.kind==="source")return [v.sourceRef.id];
 const graph=state.graphs.find(g=>g.id===v.graphRef.id&&g.version===v.graphRef.version);
 return graphSources(graph,v.nodeId);
}
const previewWidth=d=>d.fixedArray?(d.fixedArray.range.endExclusive-d.fixedArray.range.start)*(d.fixedArray.strideUnit==="word16"?2:1):d.rawRepresentation.codec?.kind==="ascii-fixed"?d.rawRepresentation.codec.length:d.rawRepresentation.codec?.kind==="s7-date-time"?8:({Int16:2,UInt16:2,Int32:4,UInt32:4,Int64:8,Float32:4,Float64:8,Boolean:1})[d.rawRepresentation.valueType];
function previewView(){
 const choices=state.mappings.flatMap(m=>m.mappings.map(b=>[JSON.stringify([m.id,b.mappingId]),m.id+" / "+(m.targetInstanceRef?.id||m.equipmentInstanceId)+" / "+(b.memberPath?memberPathLabel(b.memberPath):b.targetMemberId)]));
 $("view").innerHTML='<p class="step">09 / 가상 값 미리보기</p><p>입력 바이트 → 디코딩 → low/high·다중 입력 파생 그래프 → 단위·스케일 → 최종 cast를 확인합니다. 미리보기는 DB를 변경하지 않습니다. 가상 검증 입력은 시나리오 저장 버튼으로 별도 보관할 수 있으며 실제 장치에 접속하지 않습니다.</p><section class="card"><form id="preview-form">'+select("preview-binding","미리볼 프로퍼티 매핑",choices,choices[0]?.[0])+'<div id="preview-inputs" class="fields"></div><button type="submit">가상 입력으로 미리보기</button></form></section><section class="card records-panel" id="preview-result"><p>매핑을 선택하고 가상 입력을 넣으세요.</p></section>';
 const show=()=>{
 const [mid,bid]=JSON.parse(val("preview-binding")),binding=state.mappings.find(m=>m.id===mid).mappings.find(b=>b.mappingId===bid),ids=previewSources(binding);
 const saved=virtualSamples.get(val("preview-binding"))||{};
 $("preview-inputs").innerHTML=ids.map((id,i)=>{const d=state.sources.find(s=>s.definition.id===id).definition,typed=d.rawRepresentation.mode==="typed",width=previewWidth(d);
 const initial=saved[id]??(typed?(d.fixedArray?JSON.stringify(Array(width||1).fill(d.rawRepresentation.valueType==="Boolean"?false:"0")):d.rawRepresentation.valueType==="Boolean"?"false":"0"):Array(width||1).fill("00").join(" "));
 return '<div class="sample-input" data-source="'+esc(id)+'"><h3>'+esc(id)+'</h3><code>'+esc(d.rawAddressText)+'</code><p>'+esc((d.fixedArray?"FixedArray "+JSON.stringify(d.fixedArray.shape)+" / ":"")+d.rawRepresentation.valueType)+' · '+esc(unitValue(d.unit))+' · '+(typed?"Typed 입력":width+" bytes / "+esc(d.rawRepresentation.byteOrder)+" / "+esc(d.rawRepresentation.wordOrder))+'</p>'+field("virtual-"+i,typed?(d.fixedArray?"Typed 배열 slots (평면 JSON · 숫자는 문자열)":"Typed 값 (수치는 문자열로 처리)"):"가상 바이트 HEX",initial)+'</div>';
 }).join("");$("preview-result").innerHTML="<p>입력을 변경한 뒤 다시 미리보세요.</p>";
 };
 if(choices.length){
 $("preview-inputs").oninput=()=>{const [mid,bid]=JSON.parse(val("preview-binding")),b=state.mappings.find(m=>m.id===mid).mappings.find(b=>b.mappingId===bid);virtualSamples.set(val("preview-binding"),Object.fromEntries(previewSources(b).map((id,i)=>[id,virtualInputTextB(id,i)])));$("preview-result").innerHTML="<p>입력이 변경됐습니다. 다시 미리보세요.</p>";};
 $("preview-binding").onchange=show;show();}else $("preview-inputs").innerHTML="<p>먼저 객체 프로퍼티를 매핑하세요.</p>";
}
function previewValue(row){return row?.valueType==="String"?JSON.stringify(row.value):String(row?.value??"—");}
function previewStageValue(s){
 if(s.error)return s.error;
 if(s.stage==="array-input")return "shape "+JSON.stringify(s.detail.layout.shape)+" / "+s.detail.layout.elementCount+" elements";
 if(s.stage==="array-index")return JSON.stringify(s.detail.indices)+" → "+s.detail.resolvedAddress;
 if(s.valueType==="FixedArray")return "고정 배열 버퍼 전달";
 if(Object.hasOwn(s,"value"))return previewValue(s);
 if(s.stage==="evaluation-context")return s.detail?.evaluationContext?.at||"미확인";
 if(s.stage==="input-time-quality")return (s.detail.quality||"missing")+" / age "+(s.detail.ageMs??"미확인")+" ms";
 if(s.stage==="assembly-time-quality")return s.detail.assemblyQuality+" / skew "+(s.detail.skewMs??"미확인")+" ms";
 return s.detail?.bytesHex||"—";
}
function showPreview(r){
 $("preview-result").innerHTML='<h2>결과 · '+esc(r.quality)+'</h2><p>작성본 revision '+r.revision+' · 가상 입력 · 저장하지 않음</p><div class="preview-value"><code>'+esc(r.result?previewValue(r.result):"결과 없음 · 오류")+'</code><small>'+(r.result?esc(r.result.valueType)+" / "+esc(unitValue(r.result.unit)):"실패한 단계와 입력은 아래에서 확인하세요.")+'</small></div>'+
 (r.selections?.length?'<h3>선택된 출처</h3><p>선택 경로의 값 유효성은 최종 품질을 확인하세요.</p>'+r.selections.map(s=>'<p><strong>'+esc(s.sourceRef?.id||(s.candidateRef?.kind==="graph"?s.candidateRef.graphRef.id+"@"+s.candidateRef.graphRef.version+"/"+s.candidateRef.nodeId:"노드 "+s.candidateRef?.nodeId))+'</strong> · 요청 '+s.requestedIndex+' → 후보 '+s.selectedIndex+' / '+s.candidateCount+' · 기본값 '+(s.defaultUsed?'사용':'미사용')+' · 선택 입력 '+esc((s.selectedSourceRefs||[]).map(r=>r.id).join(', '))+' · 정의 SHA '+esc(s.definitionSha256||'')+' · 출처 변경 '+(s.sourceChanged===null?'비교 없음':s.sourceChanged?'있음':'없음')+'</p><div class="candidate-summary table-scroll"><table><thead><tr><th>후보</th><th>소스 / 그래프 출력</th><th>타입 / 단위</th><th>시간·품질 평가</th></tr></thead><tbody>'+(s.candidates||[]).map(c=>'<tr><td>'+c.index+(c.selected?' · 선택':'')+'</td><td>'+esc(c.candidateRef.kind==="source"?c.candidateRef.sourceRef.id:c.candidateRef.kind==="graph"?c.candidateRef.graphRef.id+"@"+c.candidateRef.graphRef.version+"/"+c.candidateRef.nodeId:c.candidateRef.nodeId)+'</td><td>'+esc(c.valueType)+' / '+esc(unitValue(c.unit))+'</td><td>'+esc(c.timeQualityAssessment)+'</td></tr>').join("")+'</tbody></table></div><details><summary>선택 입력의 시각·품질과 출처 정의</summary><pre>'+esc(JSON.stringify({selectedInputs:s.selectedInputDataValues||[],selectedSources:s.selectedSourceRefs,previous:s.previousCandidate,previousLineageMode:s.previousLineageMode,candidates:s.candidates},null,2))+'</pre></details>').join(""):"")+
   '<h3>오류·경고·변환 손실 · '+r.issues.length+'건</h3><ul>'+r.issues.map(i=>'<li class="'+(i.severity==="error"?"preview-error":"")+'"><strong>'+esc(i.severity)+'</strong> <code>'+esc(i.code)+'</code> · '+esc(i.stage)+'<p>'+esc(i.detail)+'</p></li>').join("")+'</ul>'+
 '<h3>처리 흐름</h3><div class="preview-stages">'+r.trace.filter(s=>s.stage!=="transform-input"&&s.stage!=="byte-layout").map(s=>'<article class="preview-stage '+(s.status==="error"?'preview-error':'')+'"><small>'+s.index+' · '+esc(s.stage)+'</small><strong>'+esc(s.identity)+'</strong><code>'+esc(previewStageValue(s))+'</code><small>'+esc((s.valueType||"")+(s.unit?" / "+unitValue(s.unit):""))+'</small>'+(s.stage==="graph:sqrt"?'<small>precision '+esc(s.detail.precision)+' · half-even · approximate '+esc(s.detail.approximate)+'</small>':s.stage==="graph:clamp"?'<small>['+esc(s.detail.low)+', '+esc(s.detail.high)+'] · '+esc(s.detail.branch)+'</small>':s.stage==="graph:subtract"?'<small>left '+esc(s.detail.inputs.left.value)+' '+esc(unitValue(s.detail.inputs.left.unit))+' − right '+esc(s.detail.inputs.right.value)+' '+esc(unitValue(s.detail.inputs.right.unit))+'</small>':"")+'</article>').join("")+'</div><h3>단계별 상세</h3><div class="table-scroll"><table><thead><tr><th>단계</th><th>소스 / 연산</th><th>값 · 정확한 수치 표현</th><th>타입 / 단위</th><th>입력·해석 근거 / 오류</th></tr></thead><tbody>'+r.trace.map(s=>'<tr class="'+(s.status==="error"?"preview-error":"")+'"><td>'+s.index+'<br>'+esc(s.stage)+'</td><td>'+esc(s.identity)+'</td><td><code>'+esc(Object.hasOwn(s,"value")?previewValue(s):"—")+'</code></td><td>'+esc(s.valueType||"")+'<small>'+esc(s.unit?unitValue(s.unit):"")+'</small></td><td><pre>'+esc(s.error||JSON.stringify(s.detail||{},null,2))+'</pre></td></tr>').join("")+'</tbody></table></div><details><summary>검증 기준 해시</summary><p>작성본 <code>'+esc(r.workspaceSha256)+'</code></p><p>가상 입력 <code>'+esc(r.sampleSha256)+'</code></p></details>';
}
const renderBeforePreview=render;
render=function(){if(tab==="preview"){document.querySelectorAll("[data-tab]").forEach(b=>b.classList.toggle("active",b.dataset.tab===tab));previewView();}else renderBeforePreview();};
document.addEventListener("submit",async event=>{
 if(event.target.id!=="preview-form")return;event.preventDefault();if(busy||conflict)return;
 const key=val("preview-binding");if(!key)return;
 const [mid,bid]=JSON.parse(key),binding=state.mappings.find(m=>m.id===mid).mappings.find(b=>b.mappingId===bid),samples={},cache={};
 try{previewSources(binding).forEach((id,i)=>{
 const d=state.sources.find(s=>s.definition.id===id).definition,text=virtualInputTextB(id,i);cache[id]=text;
 if(text!=="")samples[id]=virtualSamplePayloadE(d,text);
 });}catch(e){message(e.message,true);return;}
 virtualSamples.set(key,cache);
 busy=true;document.querySelectorAll("#preview-form input,#preview-form select,#preview-form button").forEach(e=>e.disabled=true);
 try{
 const temporalRequest=typeof withTemporalRequest==="function"?withTemporalRequest(mid,bid,samples):{};
 const response=await fetch("/api/preview",{method:"POST",headers:{"Content-Type":"application/json","X-Tyr-Editor":"1"},body:JSON.stringify({revision,mappingSetId:mid,mappingId:bid,samples,...temporalRequest})}),result=await response.json();
 if(!response.ok){if(response.status===409)conflict=true;throw Error(result.error);}
 if(result.revision!==revision)throw Error("작성본이 변경됐습니다. 최신 매핑으로 다시 미리보세요.");
 showPreview(result);message("가상 입력으로 계산했습니다. 작성본과 SQLite는 변경하지 않았습니다.");
 }catch(e){message(e.message,true);}finally{busy=false;document.querySelectorAll("#preview-form input,#preview-form select,#preview-form button").forEach(e=>e.disabled=false);}
});
if(state)render();
