"""Synthetic multi-signal maps; never accesses PLCs. Creates a separate sample DB."""
import argparse
import copy
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"backend"))
import server

def unit(code):
    return {"status":"not-applicable"} if code is None else {"status":"known","code":code}
def base(kind,id):return {"kind":kind,"schemaVersion":"1.1.0","id":id,"version":"1.0.0"}
MEMBERS=[
 ("actual-speed","actualSpeed","measurement","Double","rpm","0","3000","모터 축 실제 회전 속도. 목표값과 구분한다."),
 ("target-speed","targetSpeed","setpoint","Double","rpm","0","3000","모터 축에 요구한 목표 회전 속도."),
 ("state","operatingState","status","String",None,None,None,"운전 상태: stopped/running/fault. 현장별 코드는 매핑에서 해석한다."),
 ("alarm-active","alarmActive","status","Boolean",None,None,None,"현재 활성 알람 존재 여부. 알람 코드와 별개."),
 ("alarm-code","alarmCode","status","Int32","1","0","65535","현재 알람의 식별 코드. 0은 알람 없음."),
 ("torque","actualTorque","measurement","Double","N.m","-500","500","모터 축 실제 토크. 속도와 다른 물리량."),
 ("temperature","windingTemperature","measurement","Double","Cel","-40","180","모터 권선 온도."),
 ("cycle-count","cycleCount","status","Int32","1","0","2147483647","완료한 운전 사이클 수. Int32 초과 시 오류.")
]
PROFILES={"ab":"ab-logix-symbol-v1","ua":"s7-1500-opcua-v1","db":"s7-300-db-v1","melsec":"melsec-device-v1"}
LABELS={
"ab":["ActualSpeed","SpeedSetpoint","Status","Alarm","AlarmNo","PV","WindingTemp","Cycles"],
"ua":["IstDrehzahl","SollDrehzahl","DriveMode","Status","FaultNumber","TorqueActual","MotorTempK","CycleCounter"],
"db":["PV","SP","MachineState","AlarmActive","AlarmCode","TorquePV","TempPV","TotalCycles"],
"melsec":["速度実績","速度指令","運転状態","異常あり","異常コード","トルク実績","巻線温度","完了回数"]}
SYMBOLS=["Drive.ActualSpeed","Drive.SpeedSetpoint","Drive.StatusWord","Drive.AlarmActive","Drive.AlarmCode","Drive.TorquePV","Drive.WindingTemp","Drive.Cycles"]
UA_IDS=["Motor.N_ACT","Motor.N_CMD","Motor.Mode","Motor.Alarm","Motor.FaultCode","Motor.Torque","Motor.TempK","Motor.Cycles"]
DB_OFFSETS=[20,24,40,42,44,48,52,56]
DEVICES=[1000,2000,3000,3001,3002,4000,5000,6000]
TYPES={
"ab":["Float32","Float32","UInt16","Boolean","UInt16","Float32","Float32","UInt32"],
"ua":["Float64","Float64","UInt16","Boolean","UInt16","UInt32","Float64","UInt32"],
"db":["Int16","Int16","UInt16","UInt16","UInt16","Int16","Float32","UInt32"],
"melsec":["UInt16","UInt16","UInt16","UInt16","UInt16","Int16","Int16","UInt32"]}
ENUMS={"ab":[0,1,2],"ua":[10,20,30],"db":[0,4,8],"melsec":[0,1,9]}
def create():
    w=copy.deepcopy(server.EMPTY)
    model={**base("semantic-definition","motor-drive"),"members":[]}
    for id,name,role,typ,u,low,high,desc in MEMBERS:
        model["members"].append({"memberId":id,"name":name,"semanticId":"urn:tyr:concept:motor-"+id,"description":desc,
            "valueType":typ,"unit":unit(u),"role":role,"range":None if low is None else {"low":low,"high":high}})
    w["semantics"].append(model)
    for plc,profile in PROFILES.items():
        equip="line-a-motor-"+plc;connection="logical-"+plc
        w["equipment"].append({"id":equip,"label":{"ab":"조립 이송 모터 · AB","ua":"검사 이송 모터 · S7-1500","db":"포장 이송 모터 · S7-300","melsec":"배출 이송 모터 · MELSEC"}[plc]})
        w["connections"].append({"id":connection,"label":"가상 "+plc.upper(),"equipmentInstanceId":equip,"accessProfileRef":profile})
        mapping={**base("mapping-set","motor-object-"+plc),"equipmentInstanceId":equip,"semanticDefinitionRef":{"id":"motor-drive","version":"1.0.0"},"mappings":[]}
        for i,member in enumerate(model["members"]):
            id=plc+"-"+member["memberId"];typ=TYPES[plc][i]
            units=member["unit"];stage="already-engineered";prefix=[]
            if plc=="ua" and i in (0,1):
                units=unit("1/s");prefix=[{"op":"unit-convert","from":"1/s","to":"rpm"}]
            if plc=="ua" and i==5:
                units=unit("mN.m");prefix=[{"op":"unit-convert","from":"mN.m","to":"N.m"}]
            if plc=="ua" and i==6:
                units=unit("K");prefix=[{"op":"unit-convert","from":"K","to":"Cel"}]
            if plc in ("db","melsec") and (i in (0,1,5) or (plc=="melsec" and i==6)):
                stage="raw";units={"status":"unknown"};prefix=[{"op":"linear","factor":"0.1","offset":"0"}]
            if i==2:
                prefix=[{"op":"enum-map","entries":[{"raw":str(n),"value":v} for n,v in zip(ENUMS[plc],["stopped","running","fault"])],"onUnknown":"bad-quality"}]
            if plc=="ab":
                access={"kind":"symbol","symbolPath":SYMBOLS[i]};raw={"mode":"typed","valueType":typ};address=SYMBOLS[i]
            elif plc=="ua":
                access={"kind":"opcua-node","namespaceUri":"urn:tyr:sample:s7-1500","identifierType":"string","identifier":UA_IDS[i]};raw={"mode":"typed","valueType":typ};address="nsu=urn:tyr:sample:s7-1500;s="+UA_IDS[i]
            elif plc=="db":
                length=server.contracts.WIDTH[typ]
                access={"kind":"db-offset","dbNumber":10,"byteOffset":DB_OFFSETS[i],"byteLength":length,"bitOffset":0 if i==3 else None}
                raw={"mode":"bytes","valueType":typ,"byteOrder":"big","wordOrder":"high-first"}
                address="DB10.DB"+("W" if length==2 else "D")+str(DB_OFFSETS[i])+(".0" if i==3 else "")
            else:
                count=server.contracts.WIDTH[typ]//2
                access={"kind":"device-register","deviceArea":"D","addressIndex":DEVICES[i],"addressUnit":"word16","wordCount":count,"bitOffset":0 if i==3 else None}
                raw={"mode":"bytes","valueType":typ,"byteOrder":"little","wordOrder":"low-first"};address="D"+str(DEVICES[i])+(".0" if i==3 else "")
            evidence=[{"artifactId":"manual-"+id,"locator":{"kind":"text-line","line":1}}]
            definition={**base("source-definition",id),"equipmentInstanceId":equip,"connectionProfileRef":connection,
                "accessProfileRef":profile,"status":"ready","rawAddressText":address,"addressRadix":10 if plc=="melsec" else None,
                "access":access,"rawRepresentation":raw,"inputStage":stage,"unit":units,"evidenceRefs":evidence,"viewOf":None}
            note="Synthetic motor memory map. "+LABELS[plc][i]+" -> "+member["semanticId"]+". "+str(prefix)
            w["sources"].append({"definition":definition,"label":LABELS[plc][i],"note":note,"origin":"synthetic","capturedAt":"2026-10-17T00:00:00Z"})
            transform=prefix+[{"op":"cast","to":member["valueType"],"overflow":"error","rounding":"exact"}]
            mapping["mappings"].append({"mappingId":id+"-binding","sourceRef":{"id":id,"version":"1.0.0"},"targetMemberId":member["memberId"],
               "transform":transform,"outputUnit":member["unit"],"invalidValuePolicy":"bad-quality","evidenceRefs":evidence})
        w["mappings"].append(mapping)
    return w
def main():
    p=argparse.ArgumentParser();p.add_argument("--db",type=Path,default=ROOT/"build/p2/realistic.sqlite3");p.add_argument("--write-fixture",action="store_true");a=p.parse_args()
    state=create();server.check_state(state);findings=server.findings_for(state)
    if findings:raise ValueError(findings)
    store=server.Store(a.db);saved=store.read()
    if any(saved["workspace"].values()):raise ValueError("Sample database is not empty; choose another --db. Existing data preserved.")
    store.save(saved["revision"],state)
    if a.write_fixture:
        folder=ROOT/"fixtures/realistic";folder.mkdir(exist_ok=True);server.contracts.save(folder/"workspace.json",state)
    print("Saved 4 PLCs, 32 sources, 8 properties, 4 object mappings:",a.db)
if __name__=="__main__":main()
