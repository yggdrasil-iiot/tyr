"""Join fresh P7 executable evidence to A01-A16; gaps never count as passes."""
import json,re,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
R=Path(__file__).resolve().parents[1]
V=R/"docs/verification"
def load(p):return json.loads(p.read_text(encoding="utf-8"))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    run=load(V/"p7-validation.json");assert not run["failed"] and run["inputsUnchanged"]
    assert run["network"]["unexpectedAttempts"]==[]
    xmls=[V/"p7-bifrost-core.xml",V/"p7-bifrost-gates.xml"]
    assert "BUILD SUCCESS" in (V/"bifrost-p7-tests.log").read_text(encoding="utf-8-sig")
    java=[]
    for p in xmls:
        x=ET.parse(p).getroot();assert int(x.get("failures","0"))==int(x.get("errors","0"))==int(x.get("skipped","0"))==0
        for c in x.findall("testcase"):java.append({"id":"java:"+c.get("name"),"passed":True})
    assert len(java)==47,len(java)
    missing=load(V/"p7-release-missing.json");assert missing["rejected"] and missing["copyAndOriginalHeadUnchanged"]
    results=run["results"]+java+[{"id":"probe:A12-release-file-missing","passed":True}]
    specs=[
      ("A01","네 접근의 공통 의미 수렴","canonical:four-way-convergence|test_four_profiles_same_meaning_restart","pass","네 PLC 표현과 개별 접근 보존"),
      ("A02","다른 PLC의 같은 주소","valid:same-address-other-plc|canonical:equipment-instances-preserved","pass","설비/연결 문맥이 다른 소스 유지"),
      ("A03","다른 이름·같은 의미 / 같은 이름·다른 의미","governance:rename-preserves-meaning|governance:same-name-different-concept|coexisting-same-label","pass","명시적 의미 ID로 수렴·구분"),
      ("A04","주소 변경","governance:address-change|test_oracle_address_A04","pass","의미 유지와 전이 영향 재검토"),
      ("A05","스케일 변경","governance:scale-change|test_oracle_read_scale_A05|test_oracle_write_scale_A05","pass","타입이 같아도 읽기/쓰기 변환 영향 표시"),
      ("A06","진법·단위·타입 미확인","ready-unknown-radix|unknown-unit|test_draft_null_saved|test_declared_unknown_unit","pass","초안 보존, 제출/수신 검증 차단"),
      ("A07","전체 워드·비트 view","test_duplicate_active_sources_A07|test_legacy_explicit_view|test_alias_chain_locators","partial","alias import·legacy 진단은 검증. 신규 2.x word/bit view 작성·발행 미지원"),
      ("A08","이미 변환된 태그","double-scaling|test_missing_stage_not_confirmed|test_solution_tag_is_typed_virtual","pass","단계 미확인·이중 변환 근거/거부"),
      ("A09","파일·상속·참조 누락","missing-source-ref|evidence-not-present|test_missing_alias|test_template_missing_param","pass","bounded template/alias 범위의 누락 표시. 실제 vendor 상속은 PoV"),
      ("A10","독립 기준값","canonical:speed-|test_p3b.Oracles|test_p3c.Oracles|test_p3d.Oracles|loss:","pass","값·타입·단위·품질·손실의 저장된 oracle"),
      ("A11","검사·승인 뒤 파일 변경","test_source_and_evidence_tamper|java:modifiedAfterApprovalDenies|java:evidenceTamperDenies","pass","이전 결과/승인 재사용 거부"),
      ("A12","릴리스 일부 누락·변조","probe:A12-release-file-missing|java:releaseBytesTamperDetected|java:releaseManifestTamperDetected|java:failedStagingPreservesPreviousHead","pass","Bifrost 파일 소비 검증·HEAD 보존. 운영 적용 제외"),
      ("A13","동일 자료 재처리","test_pure_repeat|test_unknown_order_preserved","pass","고정 입력·프로파일의 동일 결과"),
      ("A14","네트워크 차단","test_p5.Diff.test_no_network_or_query|governance:communication-out-of-scope-contract","partial","Python 외부 접속 차단/negative control 및 loopback API 통과. Java·브라우저 OS 전체 격리 미수행"),
      ("A15","미지원 행·속성","observation-count|test_opaque_preserved|test_unresolved_adoption_blocked|test_duplicate_ids_not_adopted","pass","미해석·원문 보존 및 처리 상태"),
      ("A16","동시 수정·오래된 기준","test_revision_conflict|test_stale_save_atomic|test_HTTP_stale|java:staleBaseApprovalDeniesAfterNewRelease","pass","SQLite revision과 발행 base 충돌, 덮어쓰기 거부")
    ]
    rows=[]
    for id,title,pattern,status,detail in specs:
        refs=[x for x in results if re.search(pattern,x["id"])]
        assert refs and all(x["passed"] for x in refs),(id,refs)
        rows.append({"id":id,"test":title,"status":status,"detail":detail,"executedTestIds":[x["id"] for x in refs]})
    assert len(rows)==16 and sum(x["status"]=="pass" for x in rows)==14
    pins=run["sha256"]
    assert all(sha(R/p)==h for p,h in pins.items() if p.startswith(("contracts/","fixtures/","backend/")))
    ui=load(V/"p7-ui-observation.json");assert not ui["consoleErrors"] and all(ui["checks"].values())
    sql=load(V/"p7-sqlite.json");assert sql["originalPreserved"] and all(x["unchanged"] for x in sql["auxiliaryTables"].values())
    report={"scope":"bounded offline fixture acceptance; not field PoV","criteria":rows,"summary":{"pass":14,"partial":2,"fieldPoV":"not-performed"},"pythonAndP1":{"total":run["total"],"passed":run["passed"]},"java":{"total":len(java),"passed":len(java),"reportSha256":{p.name:sha(p) for p in xmls}},"compatibility":{"contractFixtureBackendPinsUnchanged":True,"sqlite":sql},"network":run["network"],"execution":run["execution"],"uiChecks":ui["checks"],"excluded":run["excluded"],"evidenceSha256":{p.name:sha(p) for p in [V/"p7-validation.json",V/"bifrost-p7-tests.log",V/"p7-sqlite.json",V/"p7-ui-observation.json",V/"p7-release-missing.json"]}}
    (V/"p7-acceptance.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    table="\n".join("| "+x["id"]+" | "+x["test"]+" | "+x["status"]+" | "+x["detail"]+" |" for x in rows)
    doc="# P7 오프라인 수용 결과\n\nA01~A16 중 14개 충족, A07·A14 부분 충족이다. 실제 현장 PoV는 미수행이다. 각 시험 ID는 [수용 기록](p7-acceptance.json)에 연결했다. 부분 충족을 전체 지원 성공으로 계산하지 않는다.\n\n| ID | 시험 | 판정 | 근거·범위 |\n|---|---|---|---|\n"+table+"\n\n## 실행 근거\n\n- 기존 P1~P6: "+str(run["passed"])+"/"+str(run["total"])+" 통과. [개별 결과·입력 hash](p7-validation.json), [log](p7-validation.log).\n- Bifrost mapping 수용 회귀: 47/47 통과, Maven offline BUILD SUCCESS. [log](bifrost-p7-tests.log). 기존 전체 reactor 회귀 기록은 P6 결과를 참조하며 P7에서 전체 reactor를 재실행했다고 주장하지 않는다.\n- Python 외부 connect/connect_ex/DNS 차단 및 거부 negative control. loopback HTTP 허용. PC 전체 방화벽/Java/브라우저 격리는 미수행.\n- [화면 관찰](p7-ui-observation.json): 네 PLC 접근·객체·그래프·매핑·이름/의미/단위/스케일 비교·가져오기 근거/미해석·읽기쓰기·검토·릴리스 조회. 가상 9600 → 150, 상수 110, subtract → 40, cast Double/kPa/good. 미리보기 revision 40 유지.\n- [SQLite](p7-sqlite.json): 원본 P6 revision 39 보존, 복제본 설비 표시 이름만 저장해 40으로 재조회. migrations·시나리오 4·기준본 1·검토 2·제출 1의 전체 행 동일.\n\n## 최초 오류와 재실행\n\n최초 실행은 unittest 544개 중 543개 성공·로컬 HTTP 연결 중단 WinError 10053 한 건과 P1 105개 성공이었다. 최초 [JSON](p7-initial-validation.json)·[log](p7-initial-validation.log)를 보존했다. 제품·계약·fixture 변경 없이 실패 시험만 격리 재실행해 성공했다. 통합 runner에서 누락된 별도 P3-A CLI 52개도 추가 실행해 52/52를 확인했다. 최종 701개는 최초 성공 543 + 격리 재실행 1 + P1 105 + P3-A 52의 중복 없는 합계다. 단일 실행에서 701개가 모두 성공했다고 주장하지 않는다. [P3-A 결과](p7-p3a.json), [CLI log](p7-p3a.log). resume는 기존 코드 hash가 달라지면 runner 자체를 제외하고 거부한다.\n\n## 패턴 카탈로그 해석\n\n[p7-patterns.json](p7-patterns.json)의 current 14/14·gap-probe 8/8·planned 34는 기존 1.x/P2 카탈로그의 역사적 시험 분류다. gap 재현과 planned를 지원 성공으로 세지 않는다. 이후 P3~P6의 구현은 이번 701개 경로의 개별 회귀 ID로 평가한다. 이 오래된 카탈로그 숫자를 현재 지원률로 사용하지 않는다. native/nested 구조·추가 vendor 형식은 계속 후속이다.\n\n## 화면 결함과 수정\n\n짧은 화면에서 고정 사이드바 하단 10~13 메뉴가 viewport 밖으로 밀려 마우스 클릭할 수 없었다. 데스크톱 사이드바를 세로 스크롤 가능하게 보완하고 최종 브라우저에서 하단 메뉴 클릭을 재확인했다. CSS 수정 후 화면 관찰은 별도 증거이며 최초 회귀 실행의 입력 SHA와 최종 CSS SHA를 구분한다. 계약·backend·fixture는 수정하지 않았다.\n\n## 현장 PoV\n\n실제 파일·버전·개정본·독립 담당자·holdout 설비가 필요하다. 정답 대비 수렴/오매핑/누락/손실과 import·수정·문의·재검토 전체 시간을 측정한다. [절차·필요 자료](../P7-OFFLINE-ACCEPTANCE.md)를 따른다. 현장 정확도·시간 절감률·전체 vendor 지원·운영 활성화는 이번 결과로 주장하지 않는다.\n"
    doc+="\n\n![최종 화면: 스크롤 가능한 메뉴와 기존 릴리스/변경 작성본 구분](p7-offline.png)\n\n[최종 artifact hash·버전](p7-final-artifacts.json).\n"
    (V/"P7-RESULTS.md").write_text(doc,encoding="utf-8")
    print(json.dumps(report["summary"]))
if __name__=="__main__":main()
