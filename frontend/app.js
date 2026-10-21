/* P2 local editor; only same-origin authoring API calls. */
"use strict";
const $ = id => document.getElementById(id);
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const profiles = {"ab-logix-symbol-v1":["AB Logix · 심볼","symbol"],"s7-1500-opcua-v1":["S7-1500 · OPC UA","opcua-node"],"s7-300-db-v1":["S7-300 · DB 오프셋","db-offset"],"melsec-device-v1":["MELSEC · 디바이스","device-register"]};
let state, revision, tab = "workflow", editing = null, busy = false, dirty = false, conflict = false;
const options = (items, selected, placeholder = "선택하세요") => '<option value="">'+esc(placeholder)+'</option>'+items.map(([v,l]) => '<option value="'+esc(v)+'"'+(String(v)===String(selected)?" selected":"")+">"+esc(l)+"</option>").join("");
const select = (id, label, items, value, required = true) => '<label for="'+esc(id)+'">'+esc(label)+'<select id="'+id+'" aria-label="'+esc(label)+'" '+(required?"required":"")+">"+options(items,value,required?"선택하세요":"미확인 / 해당 없음")+"</select></label>";
const field = (id,label,value="",type="text",required=false) => '<label for="'+esc(id)+'">'+esc(label)+'<input id="'+id+'" aria-label="'+esc(label)+'" type="'+type+'" value="'+esc(value)+'" '+(required?"required":"")+' '+(type==="number"?'step="1"':"")+"></label>";
const area = (id,label,value="") => '<label class="full" for="'+esc(id)+'">'+esc(label)+'<textarea id="'+id+'" aria-label="'+esc(label)+'" required>'+esc(value)+"</textarea></label>";
const val = id => $(id).value.trim();
const num = id => val(id)===""?null:Number(val(id));
const unit = id => val(id)==="unknown"?{status:"unknown"}:val(id)==="not-applicable"?{status:"not-applicable"}:{status:"known",code:val(id)};
const unitOptions = ["rpm","1/s","Cel","K","N.m","mN.m","1","Pa","kPa","bar","unknown","not-applicable"].map(x=>[x,{"unknown":"미확인","not-applicable":"해당 없음"}[x]||x]);
const unitValue = u => u?.status==="known"?u.code:(u?.status||"unknown");
const ref = d => ({id:d.id,version:d.version});
const base = (kind,id) => {const list=kind==="source-definition"?state.sources.map(r=>r.definition):kind==="semantic-definition"?state.semantics:state.mappings;return {kind,schemaVersion:"1.1.0",id,version:list.find(d=>d.id===id)?.version||"1.0.0"};};
function message(text,error=false){$("message").textContent=text;$("message").className=error?"error":"";}
async function request(method, body){
  const response=await fetch("/api/workspace",{method,headers:{"Content-Type":"application/json","X-Tyr-Editor":"1"},...(body?{body:JSON.stringify(body)}:{})});
  const result=await response.json();
  if(!response.ok){if(response.status===409)conflict=true;throw new Error(result.error||"저장 실패");}
  return result;
}
function ruleHint(rule){return ({"mapping.input-unit-unknown-preserved":"원시 단위 미확인 상태를 보존했습니다. 현장 근거로 단위를 확인하세요.","workspace.empty":"접근 정의를 작성하세요.","workspace.no-mapping":"소스와 공통 의미를 연결하세요.","source.draft":"미확인 값을 확인한 뒤 정의 완료로 변경하세요.","source.incomplete":"접근 필드·타입·바이트 순서의 미확인 값을 확인하세요.","mapping.source-not-ready":"연결된 소스가 초안입니다.","mapping.type":"변환 결과 타입과 의미의 타입을 맞추세요.","mapping.unit":"매핑 단위와 의미 단위가 다릅니다. 매핑을 재검토하세요.","mapping.unit-conversion-required":"입력과 결과의 단위가 다릅니다. 명시적 단위 변환이 필요합니다.","mapping.incomplete-object":"해당 객체 프로퍼티가 아직 연결되지 않았습니다.","transform.unit-source":"입력 단위와 단위 변환의 시작 단위가 다릅니다.","transform.unit-target":"변환 결과 단위를 정준 단위와 맞추세요.","mapping.double-transform":"이미 공학값인 입력에 스케일을 중복 적용했습니다.","mapping.duplicate":"한 설비의 같은 의미에 중복 연결이 있습니다.","semantic.identity-conflict":"같은 의미 ID의 역할·타입·단위가 충돌합니다.","semantic.unit":"정준 단위를 확정하세요.","source.width":"저장 길이와 원시 타입의 크기를 맞추세요.","semantic.range":"하한과 상한을 확인하세요."})[rule]||"정의와 참조를 확인하세요.";}
function display(result){state=result.workspace;revision=result.revision;$("revision").textContent="저장 revision "+revision;
 $("counts").innerHTML=["equipment","connections","sources","semantics","mappings"].map((k,i)=>["설비","논리 연결","접근 정의","공통 의미","매핑"][i]+" <strong>"+state[k].length+"</strong>").join("<br>");
 $("validation-count").textContent=result.findings.length?"· "+result.findings.length+"건":"· 형식 확인 완료";
 $("findings").innerHTML=result.findings.length?result.findings.map(x=>"<li><code>"+esc(x.ruleCode)+"</code> "+esc(ruleHint(x.ruleCode))+" · "+esc(x.path||"")+"</li>").join(""):"<li>현재 작성본에서 차단 항목을 찾지 못했습니다. 승인된 릴리스는 아닙니다.</li>";
}
async function save(next){
 if(busy||conflict){if(conflict)message("충돌 상태입니다. 작성 내용을 보관한 뒤 최신 저장본을 다시 여세요.",true);return false;}
 busy=true;document.querySelectorAll("form input,form select,form textarea,button[type=submit]").forEach(b=>b.disabled=true);
 try{const result=await request("PUT",{revision,workspace:next});display(result);dirty=false;editing=null;render();message("로컬에 저장했습니다. revision "+revision);return true;}
 catch(e){message(e.message,true);return false;}
 finally{busy=false;document.querySelectorAll("form input,form select,form textarea,button[type=submit]").forEach(b=>b.disabled=false);}
}
function upsert(list,item,id=item.id){const i=list.findIndex(x=>(x.definition?.id||x.id)===id);const kind=item.definition?"source":item.kind==="semantic-definition"?"semantic":item.kind==="mapping-set"?"mapping":item.kind==="target-instance"?"target":item.kind==="value-graph"?"graph":item.accessProfileRef?"connection":"equipment";if(i>=0&&(editing?.id!==id||editing?.kind!==kind))throw Error("이미 사용 중인 ID입니다. 저장된 항목을 선택해 편집하세요.");if(i<0)list.push(item);else list[i]=item;}
function records(items,kind,summary){return items.length?items.map(d=>{const id=d.definition?.id||d.id;return '<button class="record" data-edit="'+kind+'" data-id="'+esc(id)+'">'+esc(id)+"<small>"+esc(summary(d))+"</small></button>";}).join(""):'<p class="empty">아직 작성한 항목이 없습니다.</p>';}
function shell(title,description,form,list){$("view").innerHTML='<p class="step">'+title+'</p><p>'+description+'</p><div class="grid"><section class="card">'+form+'</section><section class="card"><h2>저장된 정의</h2><p class="hint">항목을 선택하면 편집할 수 있습니다.</p>'+list+'<button class="secondary" data-new="1">새로 작성</button></section></div>';}
function contextView(){
 const e=editing?.kind==="equipment"?state.equipment.find(d=>d.id===editing.id):null,c=editing?.kind==="connection"?state.connections.find(d=>d.id===editing.id):null;
 shell("01 / 설비와 논리 연결","설비 문맥과 PLC 접근 방식의 논리적 연결을 등록합니다.",
 '<h2>설비</h2><form id="equipment-form"><div class="fields">'+field("equipment-id","설비 ID",e?.id||"","text",true)+field("equipment-label","표시 이름",e?.label||"","text",true)+'</div><button type="submit">설비 저장</button></form><h2 class="section-label">논리 연결</h2><form id="connection-form"><div class="fields">'+field("connection-id","연결 ID",c?.id||"","text",true)+field("connection-label","표시 이름",c?.label||"","text",true)+select("connection-equipment","소속 설비",state.equipment.map(d=>[d.id,d.label+" · "+d.id]),c?.equipmentInstanceId)+select("connection-profile","접근 방식",Object.entries(profiles).map(([id,v])=>[id,v[0]]),c?.accessProfileRef)+'</div><button type="submit">논리 연결 저장</button></form>',
 records(state.equipment,"equipment",d=>d.label)+records(state.connections,"connection",d=>profiles[d.accessProfileRef][0]+" · "+d.equipmentInstanceId));
 if(e)$("equipment-id").readOnly=true;if(c)$("connection-id").readOnly=true;
}
function accessFields(profile,access={},raw={}){
 const kind=profiles[profile]?.[1];let html="";
 if(kind==="symbol")html=field("symbolPath","심볼 경로",access.symbolPath||"");
 if(kind==="opcua-node")html=field("namespaceUri","Namespace URI",access.namespaceUri||"")+select("identifierType","식별자 종류",["string","numeric","guid","opaque"].map(x=>[x,x]),access.identifierType||"string")+field("identifier","NodeId 식별자",access.identifier??"");
 if(kind==="db-offset")html=field("dbNumber","DB 번호",access.dbNumber??"","number")+field("byteOffset","바이트 오프셋",access.byteOffset??"","number")+field("byteLength","바이트 길이",access.byteLength??"","number")+field("bitOffset","비트 오프셋 (선택)",access.bitOffset??"","number");
 if(kind==="device-register")html=field("deviceArea","디바이스 영역",access.deviceArea||"")+field("addressIndex","주소 인덱스 (10진 정수)",access.addressIndex??"","number")+select("addressRadix","원문 주소 진법",[[8,"8진"],[10,"10진"],[16,"16진"]],raw.radix,false)+field("wordCount","워드 수 (16비트)",access.wordCount??"","number")+field("bitOffset","비트 오프셋 (선택)",access.bitOffset??"","number");
 const bytes=["device-register","db-offset"].includes(kind);
 html+='<p class="hint full">원시 표현: '+(bytes?"바이트 · 저장 타입과 순서를 명시합니다.":"Typed 값 · 바이트 순서를 적용하지 않습니다.")+'</p>';
 html+=select("rawType","원시 값 타입",["Int16","UInt16","Int32","UInt32","Int64","Float32","Float64","Boolean"].map(x=>[x,x]),raw.valueType,false);
 if(bytes)html+=select("byteOrder","워드 내 바이트 순서",[["little","Little endian"],["big","Big endian"]],raw.byteOrder,false)+select("wordOrder","워드 순서",[["low-first","낮은 워드 먼저"],["high-first","높은 워드 먼저"]],raw.wordOrder,false);
 return html;
}
function sourceView(){
 const row=editing?.kind==="source"?state.sources.find(x=>x.definition.id===editing.id):null,d=row?.definition;
 const profile=d?.accessProfileRef||"ab-logix-symbol-v1";
 shell("02 / PLC 접근 정의","접근 방식은 있는 그대로 보존하고 상위 의미는 다음 단계에서 연결합니다.",
 '<h2>'+(d?"접근 정의 편집":"새 접근 정의")+'</h2><form id="source-form"><div class="fields">'+field("source-id","소스 ID",d?.id||"","text",true)+field("source-label","현장 신호명",row?.label||d?.id||"","text",true)+select("source-profile","접근 방식",Object.entries(profiles).map(([id,v])=>[id,v[0]]),profile)+select("source-connection","논리 연결",state.connections.filter(c=>c.accessProfileRef===profile).map(c=>[c.id,c.label+" · "+c.equipmentInstanceId]),d?.connectionProfileRef)+select("source-status","작성 상태",[["draft","초안 · 미확인 값 허용"],["ready","정의 완료 · 제출 전 검사"]],d?.status||"draft")+field("rawAddressText","원문 접근 표기",d?.rawAddressText||"미확인","text",true)+'<div id="access-fields" class="fields full">'+accessFields(profile,d?.access,{...d?.rawRepresentation,radix:d?.addressRadix})+"</div>"+select("inputStage","입력 값 단계",[["raw","원시값 · 변환 전"],["already-engineered","이미 공학값으로 변환됨"]],d?.inputStage||"raw")+select("source-unit","입력 단위",unitOptions,unitValue(d?.unit))+select("evidence-origin","근거 구분",[["field","현장 수동 선언"],["synthetic","가상 검증 자료"]],row?.origin||"field")+area("source-note","수동 선언 근거 · 문서 위치 / 판단 이유",row?.note||"")+'</div><button type="submit">접근 정의 저장</button></form>',
 records(state.sources,"source",r=>(r.label||r.definition.id)+" · "+profiles[r.definition.accessProfileRef][0]+" · "+r.definition.rawAddressText+" · "+r.definition.status));
 if(d)$("source-id").readOnly=true;
 $("source-profile").onchange=()=>{$("access-fields").innerHTML=accessFields(val("source-profile"));$("source-connection").innerHTML=options(state.connections.filter(c=>c.accessProfileRef===val("source-profile")).map(c=>[c.id,c.label+" · "+c.equipmentInstanceId]),"");};
}
function semanticView(){
 const d=editing?.kind==="semantic"?state.semantics.find(x=>x.id===editing.id):null;
 const memberId=editing&&Object.hasOwn(editing,"memberId")?editing.memberId:d?.members[0]?.memberId;
 const m=d?.members.find(x=>x.memberId===memberId);
 shell("03 / 공통 의미 객체","하나의 객체에 여러 프로퍼티를 정의합니다. 각 프로퍼티는 별도 의미 ID·역할·타입·단위를 가집니다.",
 '<h2>객체와 프로퍼티</h2><form id="semantic-form"><div class="fields">'+field("semantic-id","객체 정의 ID",d?.id||"","text",true)+(d?select("member-picker","편집할 프로퍼티",[["__new__","＋ 새 프로퍼티"],...d.members.map(x=>[x.memberId,x.name+" · "+x.memberId])],m?.memberId||"__new__"):"")+
 field("member-id","프로퍼티 ID",m?.memberId||"","text",true)+field("semantic-name","프로퍼티 이름",m?.name||"","text",true)+field("semantic-uri","의미 ID (URI)",m?.semanticId||"urn:tyr:concept:","text",true)+select("semantic-role","역할",[["measurement","측정값"],["setpoint","목표값"],["status","상태 / 알람"]],m?.role||"measurement")+select("semantic-type","결과 값 타입",["Double","Int32","Boolean","String"].map(x=>[x,x]),m?.valueType||"Double")+select("semantic-unit","정준 단위",unitOptions,unitValue(m?.unit))+field("range-low","하한 (선택)",m?.range?.low??"")+field("range-high","상한 (선택)",m?.range?.high??"")+area("semantic-description","의미와 측정 문맥 설명",m?.description||"")+'</div><button type="submit">프로퍼티 저장</button></form>'+
 (d?'<h3>객체 프로퍼티 '+d.members.length+'개</h3>'+d.members.map(x=>'<div class="member-summary"><strong>'+esc(x.name)+'</strong> <code>'+esc(x.memberId)+'</code><small>'+esc(x.role)+" · "+esc(x.valueType)+" · "+esc(unitValue(x.unit))+'<br>'+esc(x.semanticId)+'</small></div>').join(""):""),
 '<label>기존 객체·의미 검색<input id="semantic-search" placeholder="객체, 프로퍼티 이름, 의미 ID"></label><div id="semantic-list">'+semanticRecords(state.semantics)+'</div>');
 if(d)$("semantic-id").readOnly=true;if(m)$("member-id").readOnly=true;
 if($("member-picker"))$("member-picker").onchange=()=>{if(dirty&&!confirm("저장하지 않은 프로퍼티 입력을 버리고 선택을 바꿀까요?")){$("member-picker").value=m?.memberId||"__new__";return;}editing={kind:"semantic",id:d.id,memberId:val("member-picker")==="__new__"?null:val("member-picker")};dirty=false;render();};
 $("semantic-search").oninput=()=>{$("semantic-list").innerHTML=semanticRecords(state.semantics.filter(x=>JSON.stringify(x).toLowerCase().includes(val("semantic-search").toLowerCase())));};
}
function semanticRecords(rows){return records(rows,"semantic",d=>d.members.length+"개 프로퍼티 · "+d.members.map(x=>x.name).join(", "));}
const conversions={"Pa|kPa":["0.001","0"],"kPa|Pa":["1000","0"],"bar|Pa":["100000","0"],"Pa|bar":["0.00001","0"],"bar|kPa":["100","0"],"kPa|bar":["0.01","0"],"1/s|rpm":["60","0"],"mN.m|N.m":["0.001","0"],"K|Cel":["1","-273.15"]};
function transformText(ts){return ts.map(t=>t.op==="linear"?"× "+t.factor+" + "+t.offset:t.op==="unit-convert"?t.from+" → "+t.to+" (× "+conversions[t.from+"|"+t.to]?.[0]+" + "+conversions[t.from+"|"+t.to]?.[1]+")":t.op==="cast"?"cast "+t.to:t.op==="enum-map"?"enum "+t.entries.map(e=>e.raw+"="+e.value).join(", "):"bit["+t.index+"]").join(" → ");}
function memberModel(){return state.semantics.find(x=>x.id===val("mapping-semantic"));}
function rowOperations(i,member,mapping){
 const ts=mapping?.transform||[],ops=ts.filter(t=>t.op!=="cast"),structured=!mapping||(ts.length===1&&ts[0].op==="cast")||(ts.length===2&&ts[0].op!=="cast"&&ts[1].op==="cast"),op=structured?(ops[0]?.op||"cast"):"advanced",t=ops[0],cast=ts.find(t=>t.op==="cast");
 return select("operation-"+i,"해석 / 변환",[["cast","타입 변환만"],["linear","원시값 스케일"],["unit-convert","명시적 단위 변환"],["enum-map","상태 코드 → 의미"],["bit-select","워드에서 비트 선택"],["advanced","전체 변환 목록 (JSON)"]],op)+
 '<div id="op-fields-'+i+'">'+operationFields(i,op,t,ts)+'</div>'+select("rounding-"+i,"반올림",[["exact","Exact"],["half-even","Half even"]],cast?.rounding||"exact");
}
function operationFields(i,op,t,ts){
 if(op==="linear")return field("factor-"+i,"계수",t?.factor||"1")+field("offset-"+i,"오프셋",t?.offset||"0");
 if(op==="unit-convert")return '<p class="hint">입력 단위에서 해당 프로퍼티의 정준 단위로 변환합니다. 1/s→rpm, mN.m→N.m, K→Cel 지원.</p>';
 if(op==="enum-map")return area("enum-"+i,"코드=의미 · 한 줄에 하나",t?.entries.map(e=>e.raw+"="+e.value).join("\n")||"0=stopped\n1=running\n2=fault");
 if(op==="bit-select")return field("bit-"+i,"비트 위치",t?.index??0,"number",true);
 if(op==="advanced")return area("pipeline-"+i,"전체 변환 목록 JSON",JSON.stringify(ts||[],null,2));
 return '<p class="hint">공통 의미의 결과 타입으로 변환합니다.</p>';
}
function mappingRows(model,equipment,existing){
 return model.members.map((member,i)=>{
 const mapping=existing?.mappings.find(m=>m.targetMemberId===member.memberId);
 const sources=state.sources.filter(r=>r.definition.equipmentInstanceId===equipment);
 return '<article class="binding-row" data-member="'+esc(member.memberId)+'"><div><h3>'+esc(member.name)+'</h3><p><code>'+esc(member.memberId)+'</code><br>'+esc(member.role)+' · '+esc(member.valueType)+' · '+esc(unitValue(member.unit))+'</p><small>'+esc(member.semanticId)+'</small></div><div>'+select("bind-source-"+i,"소스 / 현장 신호",sources.map(r=>[r.definition.id,(r.label||r.definition.id)+" · "+r.definition.rawAddressText]),mapping?.sourceRef.id,false)+'<p id="source-info-'+i+'" class="hint"></p></div><div>'+rowOperations(i,member,mapping)+'</div></article>';
 }).join("");
}
function wireMappingRows(model){
 model.members.forEach((member,i)=>{
  const show=()=>{const row=state.sources.find(r=>r.definition.id===val("bind-source-"+i));$("source-info-"+i).textContent=row?row.definition.rawRepresentation.valueType+" / "+unitValue(row.definition.unit)+" / "+row.definition.inputStage:"미매핑 · 초안으로 보관할 수 있습니다.";};
  $("bind-source-"+i).onchange=show;show();
  $("operation-"+i).onchange=()=>{$("op-fields-"+i).innerHTML=operationFields(i,val("operation-"+i));};
 });
}
function mappingView(){
 const d=editing?.kind==="mapping"?state.mappings.find(x=>x.id===editing.id):null;
 $("view").innerHTML='<p class="step">04 / 객체의 프로퍼티별 매핑</p><p>주소가 떨어져 있어도 하나의 객체를 구성할 수 있습니다. 각 행은 해당 프로퍼티의 소스·타입·변환을 독립적으로 보존합니다.</p><section class="card"><form id="mapping-form"><div class="fields">'+field("mapping-id","객체 매핑 ID",d?.id||"","text",true)+select("mapping-equipment","설비 인스턴스",state.equipment.map(e=>[e.id,e.label]),d?.equipmentInstanceId)+select("mapping-semantic","공통 의미 객체",state.semantics.map(s=>[s.id,s.id+" · "+s.members.length+"개 프로퍼티"]),d?.semanticDefinitionRef.id)+'</div><div id="binding-rows"></div><button type="submit">객체 매핑 저장</button></form></section><section class="card records-panel"><h2>저장된 객체 매핑</h2>'+records(state.mappings,"mapping",x=>x.equipmentInstanceId+" → "+x.semanticDefinitionRef.id+" · "+x.mappings.length+"개 프로퍼티")+'<button class="secondary" data-new="1">새로 작성</button></section>';
 if(d)$("mapping-id").readOnly=true;
 const show=()=>{const model=memberModel(),equipment=val("mapping-equipment");$("binding-rows").innerHTML=model&&equipment?mappingRows(model,equipment,d&&d.equipmentInstanceId===equipment&&d.semanticDefinitionRef.id===model.id?d:null):'<p class="hint">설비와 의미 객체를 선택하세요.</p>';if(model&&equipment)wireMappingRows(model);};
 let previousEquipment=val("mapping-equipment"),previousModel=val("mapping-semantic");
 const change=event=>{const populated=Array.from(document.querySelectorAll(".binding-row select[id^='bind-source-']")).some(x=>x.value);
 if(populated&&!confirm("설비나 의미 객체를 바꾸면 현재 매핑 행을 다시 구성합니다. 계속할까요?")){event.target.value=event.target.id==="mapping-equipment"?previousEquipment:previousModel;return;}
 show();previousEquipment=val("mapping-equipment");previousModel=val("mapping-semantic");dirty=true;};
 $("mapping-equipment").onchange=change;$("mapping-semantic").onchange=change;show();
}
function collectObjectMapping(){
 const model=memberModel(),equipment=val("mapping-equipment");
 if(!model||!equipment)throw Error("설비와 의미 객체를 선택하세요.");
 const mappings=[];
 model.members.forEach((member,i)=>{
  const source=state.sources.find(r=>r.definition.id===val("bind-source-"+i))?.definition;
  if(!source)return;
  const op=val("operation-"+i);let ts=[];
  if(op==="linear")ts.push({op,factor:val("factor-"+i),offset:val("offset-"+i)});
  if(op==="unit-convert"){const from=source.unit.code,to=member.unit.code;if(!conversions[from+"|"+to])throw Error(member.name+": 지원하는 단위 변환 쌍을 선택하세요.");ts.push({op,from,to});}
  if(op==="bit-select")ts.push({op,index:num("bit-"+i)});
  if(op==="enum-map"){const entries=val("enum-"+i).split("\n").filter(x=>x.trim()).map(line=>{const split=line.indexOf("=");if(split<1)throw Error("코드=의미 형식으로 입력하세요.");return {raw:line.slice(0,split).trim(),value:line.slice(split+1).trim()};});ts.push({op,entries,onUnknown:"bad-quality"});}
  if(op==="advanced")ts=JSON.parse(val("pipeline-"+i));else ts.push({op:"cast",to:member.valueType,rounding:val("rounding-"+i),overflow:"error"});
  const previous=editing?.kind==="mapping"?state.mappings.find(d=>d.id===editing.id)?.mappings.find(m=>m.targetMemberId===member.memberId):null;
  mappings.push({mappingId:previous?.mappingId||val("mapping-id")+"-"+member.memberId,sourceRef:ref(source),targetMemberId:member.memberId,transform:ts,outputUnit:member.unit,invalidValuePolicy:"bad-quality",evidenceRefs:source.evidenceRefs});
 });
 if(!mappings.length)throw Error("하나 이상의 프로퍼티를 연결하세요.");
 return {...base("mapping-set",val("mapping-id")),schemaVersion:"1.1.0",equipmentInstanceId:equipment,semanticDefinitionRef:ref(model),mappings};
}
function comparisonView(){
 const models=state.semantics;
 $("view").innerHTML='<p class="step">05 / 메모리맵과 정준 의미 비교</p><p>현장 이름·접근 정의·입력 단위·변환을 정준 프로퍼티와 함께 비교합니다. 표시 이름은 의미의 식별 키로 사용하지 않습니다.</p><section class="card"><div class="fields">'+select("compare-model","의미 객체",models.map(m=>[m.id,m.id]),models.find(m=>m.members.length>1)?.id||models[0]?.id)+select("compare-equipment","표시 설비",[["all","모든 설비"],...state.equipment.map(e=>[e.id,e.label])],"all")+'<label>신호 검색<input id="compare-search" placeholder="이름, 의미, 주소, PLC"></label></div><div id="comparison"></div></section>';
 const show=()=>{
 const model=models.find(m=>m.id===val("compare-model"));if(!model){$("comparison").innerHTML="<p>의미 객체를 먼저 작성하세요.</p>";return;}
 const allMaps=state.mappings.filter(m=>m.semanticDefinitionRef.id===model.id&&m.semanticDefinitionRef.version===model.version);
 const maps=allMaps.filter(m=>val("compare-equipment")==="all"||m.equipmentInstanceId===val("compare-equipment"));
 const sourceMap=new Map(state.sources.map(r=>[r.definition.id,r]));
 const all=[];
 for(const map of allMaps)for(const binding of map.mappings){const source=sourceMap.get(binding.sourceRef.id),member=model.members.find(m=>m.memberId===binding.targetMemberId);if(source&&member)all.push({map,binding,source,member});}
 const byName=new Map();for(const r of all){const name=r.source.label||r.source.definition.id;if(!byName.has(name))byName.set(name,new Set());byName.get(name).add(r.member.semanticId);}
 const query=val("compare-search").toLowerCase();
 const rows=all.filter(r=>maps.some(m=>m.id===r.map.id)&&JSON.stringify(r).toLowerCase().includes(query));
 let html='<h2 class="section-label">객체 프로퍼티 × 설비의 주소</h2><div class="table-scroll"><table class="'+(maps.length===1?'single-equipment':'')+'"><thead><tr><th>정준 프로퍼티</th>'+maps.map(m=>'<th>'+esc(m.equipmentInstanceId)+'</th>').join("")+'</tr></thead><tbody>';
 for(const member of model.members){
 const rr=rows.filter(r=>r.member.memberId===member.memberId);if(query&&!rr.length)continue;
 html+='<tr><th>'+esc(member.name)+'<small>'+esc(member.role)+' · '+esc(unitValue(member.unit))+'</small></th>';
 for(const map of maps){const r=rr.find(r=>r.map.id===map.id);html+='<td>'+(r?'<strong>'+esc(r.source.label||r.source.definition.id)+'</strong><code>'+esc(r.source.definition.rawAddressText)+'</code><small>'+esc(transformText(r.binding.transform))+'</small>':'<span class="hint">—</span>')+'</td>';}
 html+='</tr>';
 }
 html+='</tbody></table></div><h2 class="section-label">신호별 이름·단위·스케일 비교 · '+rows.length+'개</h2><div class="table-scroll"><table><thead><tr><th>PLC / 현장 이름</th><th>접근 · 원시 타입</th><th>입력 단위 / 단계</th><th>변환</th><th>정준 의미 · 결과</th><th>이름 관계</th></tr></thead><tbody>';
 for(const r of rows){const d=r.source.definition,label=r.source.label||d.id,otherNames=new Set(all.filter(x=>x.member.semanticId===r.member.semanticId).map(x=>x.source.label||x.source.definition.id));
 html+='<tr><td>'+esc(profiles[d.accessProfileRef][0])+'<strong>'+esc(label)+'</strong></td><td><code>'+esc(d.rawAddressText)+'</code>'+esc(d.rawRepresentation.valueType)+'</td><td>'+esc(unitValue(d.unit))+'<small>'+esc(d.inputStage)+'</small></td><td>'+esc(transformText(r.binding.transform))+'</td><td>'+esc(r.member.name)+'<small>'+esc(r.member.semanticId)+'</small>'+esc(r.member.valueType)+' / '+esc(unitValue(r.member.unit))+'</td><td>'+(otherNames.size>1?'<span class="badge">다른 이름 · 같은 의미</span>':"")+(byName.get(label).size>1?'<span class="badge collision">같은 이름 · 다른 의미</span>':"")+'</td></tr>';
 }
 $("comparison").innerHTML=html+'</tbody></table></div>';
 };
 $("compare-model").onchange=show;$("compare-equipment").onchange=show;$("compare-search").oninput=show;show();
}
function render(){if(tab==="workflow")return;document.querySelectorAll("[data-tab]").forEach(b=>b.classList.toggle("active",b.dataset.tab===tab));({context:contextView,sources:sourceView,semantics:semanticView,mappings:mappingView,comparison:comparisonView}[tab])();}
function draftSource(){
 const profile=val("source-profile"),kind=profiles[profile][1],c=state.connections.find(c=>c.id===val("source-connection"));if(!c)throw Error("논리 연결을 먼저 선택하세요.");
 let access={kind},bytes=["db-offset","device-register"].includes(kind);
 if(kind==="symbol")access.symbolPath=val("symbolPath")||null;
 if(kind==="opcua-node"){const t=val("identifierType");access={kind,namespaceUri:val("namespaceUri")||null,identifierType:t,identifier:val("identifier")===""?null:t==="numeric"?Number(val("identifier")):val("identifier")};}
 if(kind==="db-offset")access={kind,dbNumber:num("dbNumber"),byteOffset:num("byteOffset"),byteLength:num("byteLength"),bitOffset:num("bitOffset")};
 if(kind==="device-register")access={kind,deviceArea:val("deviceArea")||null,addressIndex:num("addressIndex"),addressUnit:"word16",wordCount:num("wordCount"),bitOffset:num("bitOffset")};
 const id=val("source-id"),evidenceRefs=[{artifactId:"manual-"+id,locator:{kind:"text-line",line:1}}];
 return {definition:{...base("source-definition",id),equipmentInstanceId:c.equipmentInstanceId,connectionProfileRef:c.id,accessProfileRef:profile,status:val("source-status"),rawAddressText:val("rawAddressText"),addressRadix:kind==="device-register"?num("addressRadix"):null,access,
 rawRepresentation:bytes?{mode:"bytes",valueType:val("rawType")||null,byteOrder:val("byteOrder")||null,wordOrder:val("wordOrder")||null}:{mode:"typed",valueType:val("rawType")||null},
 inputStage:val("inputStage"),unit:unit("source-unit"),evidenceRefs,viewOf:null},label:val("source-label"),note:val("source-note"),origin:val("evidence-origin"),capturedAt:new Date().toISOString()};
}
document.addEventListener("submit",async event=>{
 event.preventDefault();const next=structuredClone(state);
 try{
 switch(event.target.id){
 case "equipment-form":upsert(next.equipment,{id:val("equipment-id"),label:val("equipment-label")});break;
 case "connection-form":upsert(next.connections,{id:val("connection-id"),label:val("connection-label"),equipmentInstanceId:val("connection-equipment"),accessProfileRef:val("connection-profile")});break;
 case "source-form":{const row=draftSource();upsert(next.sources,row,row.definition.id);break;}
 case "semantic-form":{
 const id=val("semantic-id"),memberId=val("member-id"),low=val("range-low"),high=val("range-high");
 if(Boolean(low)!==Boolean(high))throw Error("범위는 하한과 상한을 함께 입력하세요.");
 const previous=next.semantics.find(d=>d.id===id),members=structuredClone(previous?.members||[]);
 if(previous&&editing?.id!==id)throw Error("기존 객체를 선택해 프로퍼티를 추가하세요.");
 const index=members.findIndex(m=>m.memberId===memberId);
 if(index>=0&&editing?.memberId!==memberId&&Object.hasOwn(editing||{},"memberId"))throw Error("이미 있는 프로퍼티 ID입니다.");
 const member={memberId,name:val("semantic-name"),semanticId:val("semantic-uri"),description:val("semantic-description"),valueType:val("semantic-type"),unit:unit("semantic-unit"),role:val("semantic-role"),range:low?{low,high}:null};
 if(index<0)members.push(member);else members[index]=member;
 upsert(next.semantics,{...base("semantic-definition",id),schemaVersion:members.some(m=>["Pa","kPa","bar"].includes(m.unit.code))?"2.2.0":(previous?.schemaVersion||"1.1.0"),members});break;
 }
 case "mapping-form":upsert(next.mappings,collectObjectMapping());break;
 default:return;
 }
 await save(next);
 }catch(e){message(e.message,true);}
});
document.addEventListener("input",event=>{if(event.target.closest("form")&&!["preview-form","logical-preview-form"].includes(event.target.closest("form").id)&&event.target.id!=="member-picker"&&event.target.id!=="array-probe-e")dirty=true;});
document.addEventListener("click",event=>{
 const button=event.target.closest("button");if(!state||!button||busy)return;
 if(button.dataset.tab||button.dataset.edit||button.dataset.new){
 if(dirty&&!confirm("저장하지 않은 입력이 있습니다. 화면을 이동할까요?"))return;
 dirty=false;message("");
 if(button.dataset.tab){tab=button.dataset.tab;editing=null;}
 if(button.dataset.edit)editing={kind:button.dataset.edit,id:button.dataset.id};
 if(button.dataset.new)editing=null;
 render();
 }
});
$("reload").onclick=async()=>{if(dirty&&!confirm("저장하지 않은 입력을 버리고 최신 저장본을 열까요?"))return;try{display(await request("GET"));dirty=false;conflict=false;editing=null;render();message("최신 저장본을 열었습니다.");}catch(e){message(e.message,true);}};
window.addEventListener("beforeunload",event=>{if(dirty){event.preventDefault();event.returnValue="";}});
request("GET").then(result=>{display(result);render();}).catch(e=>message(e.message,true));
