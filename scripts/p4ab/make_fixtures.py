from pathlib import Path
import copy,json,base64,sys
r=Path.cwd();sys.path[:0]=[str(r/"backend"),str(r/"scripts")]
import server,import_files as imp,import_workflow as wf
f=r/"fixtures/p4ab";f.mkdir(exist_ok=True)
load=lambda p:server.contracts.load(p)
save=lambda n,d:server.contracts.save(f/(n+".json"),d)
context=load(r/"fixtures/p4a/context.json")
original=load(r/"fixtures/p4a/settings-request.json")
orig=json.loads(base64.b64decode(original["bytesBase64"]))
records=copy.deepcopy(orig["records"][:4])
records += [{"id":"unresolved","kind":"source","profile":"melsec-device-v1","address":"D{POINTER}","type":"UInt16","unit":"kPa","stage":"raw","byteOrder":"little","wordOrder":"low-first","width":1},
 {"id":"pump","kind":"template","profile":"melsec-device-v1","address":"D{offset}","base":5000,"stride":2,"count":2,"type":"UInt16","unit":"kPa","stage":"raw","byteOrder":"little","wordOrder":"low-first","width":1},
 {"id":"alias","kind":"alias","target":"pump-1"}]
doc={"format":"tyr-config-v1","records":records,"vendorMetadata":{"opaque":"preserve exactly"}}
def request(id,doc):return {**original,"id":id,"filename":id+".json","bytesBase64":base64.b64encode(json.dumps(doc,ensure_ascii=False).encode()).decode()}
q=request("review-base",doc);batch=imp.parse(q,context)
valid=[o["id"] for o in batch["observations"] if o["draft"] and not o["issues"]]
w=imp.adopt(context,batch,valid)
save("base-request",q);save("original-workspace",w)
bad=next(o for o in batch["observations"] if o["raw"].get("id")=="unresolved")
d=copy.deepcopy(next(o["draft"] for o in batch["observations"] if o["raw"].get("id")=="pump-0"))
d.update(id="imp-review-base-unresolved",rawAddressText="D4000",evidenceRefs=wf.refs(batch,bad));d["access"]["addressIndex"]=4000
meta={"reviewer":"offline-reviewer","reason":"Synthetic engineering correction; explicit D4000 from independent fixture oracle","reviewedAt":"2026-10-18T00:00:00Z"}
review={"observationId":bad["id"],"observationSha256":wf.digest(bad),"previousReviewSha256":None,"decision":"resolve-source","recordKey":"unresolved","source":d,**meta}
w=wf.review(w,batch["id"],review);save("resolve-review",review)
opaque=batch["observations"][-1];exclude={"observationId":opaque["id"],"observationSha256":wf.digest(opaque),"previousReviewSha256":None,"decision":"exclude-non-source","recordKey":None,"source":None,**{**meta,"reason":"Non-signal vendor metadata; preserved original bytes and claims"}}
w=wf.review(w,batch["id"],exclude);w=wf.adopt(w,batch["id"],[bad["id"]]);save("exclude-review",exclude)
for row in w["sources"]:row["definition"]["status"]="ready"
# Reuse an existing canonical model shape, retaining stable old source references.
src=w["sources"][0]["definition"];prior=load(r/"fixtures/p3c/workspace.json")
sem=copy.deepcopy(prior["semantics"][0]);sem.update(id="import-speed-model");sem["members"]=sem["members"][:1];sem["members"][0].update(memberId="speed",semanticId="urn:tyr:concept:motor.actual-speed",name="Actual speed",unit={"status":"known","code":"rpm"},range=None)
target=copy.deepcopy(prior["targets"][0]);target.update(id="import-motor",equipmentInstanceId="import-line",semanticDefinitionRef={"id":sem["id"],"version":sem["version"]},evidenceRefs=src["evidenceRefs"])
mapping=copy.deepcopy(prior["mappings"][0]);mapping.update(id="import-speed-mapping",equipmentInstanceId="import-line",targetInstanceRef={"id":target["id"],"version":target["version"]});mapping["mappings"]=mapping["mappings"][:1]
binding=mapping["mappings"][0];binding.update(mappingId="speed-binding",valueRef={"kind":"source","sourceRef":{"id":src["id"],"version":src["version"]}},memberPath=[{"kind":"member","memberId":"speed"}],evidenceRefs=src["evidenceRefs"],outputUnit={"status":"known","code":"rpm"})
w["semantics"]=[sem];w["targets"]=[target];w["mappings"]=[mapping]
server.check_state(w);save("reviewed-workspace",w)
local=copy.deepcopy(w);local["sources"][0]["label"]="Local speed label"
ua=next(row for row in local["sources"] if row["definition"]["accessProfileRef"]=="s7-1500-opcua-v1")
ua["definition"]["rawAddressText"]="Line.LocalPressure";ua["definition"]["access"]["identifier"]="Line.LocalPressure";ua["note"]="Local engineering note must survive"
incoming=copy.deepcopy(doc);incoming.pop("vendorMetadata")
incoming["records"]=[incoming["records"][5],incoming["records"][3],incoming["records"][0],incoming["records"][1],incoming["records"][4],incoming["records"][6]]
incoming["records"][2]["address"]="Motor.ActualSpeedV2"
incoming["records"][3]["address"]="Line.IncomingPressure"
incoming["records"][4]["address"]="D4001"
incoming["records"][0]["overrides"]={"1":{"address":"D5999"}}
incoming["records"].append({"id":"new-signal","kind":"source","profile":"melsec-device-v1","address":"D7000","type":"UInt16","unit":"kPa","stage":"raw","byteOrder":"little","wordOrder":"low-first","width":1})
new_q=request("review-next",incoming);new=imp.parse(new_q,local)
save("local-workspace",local);save("incoming-request",new_q);save("review-metadata",meta)
old=local["imports"][0];ids={e["sourceId"] for e in wf.previous_entries(old,local["sources"])};ours=[row for row in local["sources"] if row["definition"]["id"] in ids]
plan=wf.plan(old,new,ours,wf.digest(local))
choices={a["key"]:{"mode":"retain" if a["classification"]=="removed" else "apply","fields":{f["field"]:"ours" for f in a["fields"] if f["conflict"]}} for a in plan["actions"]}
merged=wf.apply(local,new,plan,choices,meta);server.check_state(merged)
save("merge-plan",plan);save("merge-choices",choices);save("merged-workspace",merged)
for row in merged["sources"]:row["definition"]["status"]="ready"
server.check_state(merged);save("publication-workspace",merged)
save("expected",{"stableSourceId":src["id"],"speedAddress":"Motor.ActualSpeedV2","speedLabel":"Local speed label","pressureAddress":"Line.LocalPressure","retainedDbId":next(row["definition"]["id"] for row in local["sources"] if row["definition"]["accessProfileRef"]=="s7-300-db-v1"),"classifications":{a["recordKey"]:a["classification"] for a in plan["actions"]}})
print("fixture scenarios ready",len(batch["observations"]),len(w["sources"]),len(merged["sources"]))
