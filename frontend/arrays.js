/* P3-E bounded fixed scalar arrays. No native structure or dynamic indexing. */
function arrayBufferLengthE(d){const f=d.fixedArray;return (f.range.endExclusive-f.range.start)*(f.strideUnit==='word16'?2:1);}
function virtualSamplePayloadE(d,text){
 if(d.fixedArray&&d.rawRepresentation.mode==='typed'){
 const values=JSON.parse(text);
 if(!Array.isArray(values))throw Error('Typed 배열은 평면 JSON 목록으로 입력하세요.');
 if(values.some(v=>typeof v==='number'))throw Error('정확한 수치 입력을 위해 Typed 배열 숫자는 "100"처럼 문자열로 입력하세요.');
 return {typedValues:values};
 }
 return d.rawRepresentation.mode==='bytes'?{bytesHex:text}:{typedValue:d.rawRepresentation.valueType==='Boolean'?(text==='true'?true:text==='false'?false:text):text};
}
const oldSourceViewE=sourceView;
sourceView=function(){
 oldSourceViewE();
 const d=editing?.kind==='source'?state.sources.find(r=>r.definition.id===editing.id)?.definition:null,f=d?.fixedArray;
 const kind=profiles[val('source-profile')]?.[1],typed=['symbol','opcua-node'].includes(kind),word=kind==='device-register';
 const start=typed?0:Number(val(word?'addressIndex':'byteOffset')||0);
 const width=({Int16:2,UInt16:2,Int32:4,UInt32:4,Int64:8,Float32:4,Float64:8,Boolean:1})[val('rawType')]||2,step=typed?1:word?Math.ceil(width/2):width;
 const defaults={shape:[4],lowerBounds:[0],strides:[step],strideUnit:typed?'element':word?'word16':'byte',range:{start,endExclusive:start+4*step}};
 const layout=f||defaults;
 document.querySelector('#source-form button[type="submit"]').insertAdjacentHTML('beforebegin','<section class="array-definition"><h3>고정 scalar 배열</h3>'+select('array-enabled-e','배열 정의',[['off','단일 scalar'],['on','고정 배열 · 명시적 요소 선택']],f?'on':'off')+
 '<div id="array-fields-e" '+(f?'':'hidden')+'><div class="fields">'+field('array-shape-e','shape (JSON)',JSON.stringify(layout.shape),'text',true)+field('array-lower-e','시작 인덱스 lowerBounds (JSON)',JSON.stringify(layout.lowerBounds),'text',true)+field('array-strides-e','축별 strides (JSON)',JSON.stringify(layout.strides),'text',true)+select('array-unit-e','stride 좌표 단위',[['byte','byte · DB'],['word16','word16 · register'],['element','element · Typed slots']],layout.strideUnit)+field('array-start-e','저장 범위 start (포함)',layout.range.start,'number',true)+field('array-end-e','저장 범위 endExclusive',layout.range.endExclusive,'number',true)+'</div><p>접근 주소와 타입/폭은 첫 요소를 정의합니다. start는 첫 주소(typed는 0)이고 버퍼는 범위 전체를 포함합니다. shape·하한·stride의 축 순서를 맞추세요. 패딩은 명시적으로 남깁니다.</p>'+field('array-probe-e','검사할 요소 indices (JSON)',JSON.stringify(layout.lowerBounds))+'<button type="button" id="array-probe-button-e" class="secondary">저장한 배열 인덱스 검사</button><p>저장된 정의 기준 주소·범위 검사입니다. 실제 장치를 읽지 않습니다.</p><pre id="array-probe-result-e"></pre></div></section>');
 $('array-enabled-e').onchange=()=>{$('array-fields-e').hidden=val('array-enabled-e')!=='on';dirty=true;};
 $('array-probe-button-e').onclick=async()=>{
 try{
 const source=state.sources.find(r=>r.definition.id===val('source-id'))?.definition;
 if(!source?.fixedArray)throw Error('배열 정의를 먼저 저장하고 다시 선택하세요.');
 const response=await fetch('/api/array-index',{method:'POST',headers:{'Content-Type':'application/json','X-Tyr-Editor':'1'},body:JSON.stringify({revision,sourceRef:ref(source),indices:JSON.parse(val('array-probe-e'))})}),r=await response.json();
 if(!response.ok)throw Error(r.error);
 $('array-probe-result-e').textContent=JSON.stringify(r,null,2);message(r.quality==='good'?'요소 주소와 저장 범위를 확인했습니다.':'배열 인덱스가 범위를 벗어났거나 정의가 잘못됐습니다.',r.quality!=='good');
 }catch(e){message(e.message,true);}
 };
};
const oldDraftSourceE=draftSource;
draftSource=function(){
 const row=oldDraftSourceE(),d=row.definition;
 if(val('array-enabled-e')==='on'){
 d.schemaVersion='2.4.0';d.fixedArray={shape:JSON.parse(val('array-shape-e')),lowerBounds:JSON.parse(val('array-lower-e')),strides:JSON.parse(val('array-strides-e')),strideUnit:val('array-unit-e'),range:{start:num('array-start-e'),endExclusive:num('array-end-e')}};
 }else if(state.sources.find(r=>r.definition.id===d.id)?.definition.schemaVersion==='2.4.0')d.schemaVersion='2.4.0';
 return row;
};
const oldGraphAddressE=graphAddress;
graphAddress=function(graph,nodeId,seen=new Set()){
 const n=graph.nodes.find(n=>n.nodeId===nodeId);
 if(n?.op==='array-element'){
 if(seen.has(nodeId))return '순환';
 const next=new Set(seen);next.add(nodeId);const ep=n.inputs.value;
 const label=ep?.kind==='source'?state.sources.find(r=>r.definition.id===ep.sourceRef.id)?.definition.rawAddressText:ep?graphAddress(graph,ep.nodeId,next):'미확인';
 return label+' / indices '+JSON.stringify(n.indices);
 }
 return oldGraphAddressE(graph,nodeId,seen);
};
const oldValueInfoE=valueInfo;
valueInfo=function(v){
 const info=oldValueInfoE(v);
 if(v?.kind==='source'&&info){
 const d=state.sources.find(r=>r.definition.id===v.sourceRef.id).definition;
 if(d.fixedArray){info.type='FixedArray<'+d.rawRepresentation.valueType+'>';info.address+=' · shape '+JSON.stringify(d.fixedArray.shape)+' · lower '+JSON.stringify(d.fixedArray.lowerBounds)+' · strides '+JSON.stringify(d.fixedArray.strides)+' '+d.fixedArray.strideUnit;}
 }
 return info;
};
const oldValueOptionsE=valueOptions;
valueOptions=function(equipment){
 return oldValueOptionsE(equipment).filter(([text])=>{
 const [kind,id,node]=JSON.parse(text);
 return kind==='source'?!state.sources.find(r=>r.definition.id===id).definition.fixedArray:state.graphs.find(g=>g.id===id).nodes.find(n=>n.nodeId===node).valueType!=='FixedArray';
 });
};
const oldCollectMappingE=collectObjectMapping;
collectObjectMapping=function(){
 const result=oldCollectMappingE();if(!v2Mode())return result;
 if(state.mappings.find(m=>m.id===result.id)?.schemaVersion==='2.4.0'||result.mappings.some(b=>valueInfo(b.valueRef)?.sources.some(id=>state.sources.find(r=>r.definition.id===id)?.definition.fixedArray)))result.schemaVersion='2.4.0';
 return result;
};
const oldShowPreviewE=showPreview;
showPreview=function(r){
 oldShowPreviewE(r);
 const selected=r.trace.filter(t=>t.stage==='array-index'||t.stage==='graph:array-element');
 if(selected.length)$('preview-result').insertAdjacentHTML('afterbegin','<section><h3>배열 요소 선택</h3>'+selected.filter(t=>t.stage==='array-index').map(t=>'<p><strong>'+esc(t.identity)+'</strong><br>indices '+esc(JSON.stringify(t.detail.indices))+' → '+esc(t.detail.resolvedAddress)+'<br>offset '+esc(t.detail.offset)+' '+esc(t.detail.strideUnit)+' · shape '+esc(JSON.stringify(t.detail.shape))+'<br>허용 인덱스 '+esc(JSON.stringify(t.detail.lowerBounds))+' ~ '+esc(JSON.stringify(t.detail.upperBounds))+'</p>').join('')+'</section>');
};
if(state)render();
