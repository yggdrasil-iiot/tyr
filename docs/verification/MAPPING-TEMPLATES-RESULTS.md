# 매핑 템플릿·적용본 검증

2026-10-18. 현장 PoV 미수행. 장치 통신·외부 SQL·쓰기 실행·runtime 활성화 제외.

## 최종 산출물

[설계](../P6-MAPPING-TEMPLATES.md) · [합성 fixture](../../fixtures/mapping-templates/README.md) · [이전 파일 pin](mapping-templates-baseline-pins.json) · [JAR/스키마 무결성](mapping-templates-artifact-integrity.json).

기존 canonical 파일80개(스키마79+README), fixture619개, 평가 계약1개, local editor 계약2개: 합계702개 SHA 보존. 현재 스키마83개는 독립 Java resource 사본 및 최종 JAR과 byte 동일. 매핑 클래스16개도 빌드 class와 JAR이 동일하다. JAR SHA256 `43def6b8b1c3735401df279809f62b5ea7a13766abbf857a6de3420833847e8c`.

## 검사 범위

- 새 Python 템플릿 검사24개 통과: 네 PLC 공통 슬롯의 수치 정답·버전 고정·선택적 갱신·부모 소스 closure·해석 타입·구 소비자 유지·생성물/소스/이력 변조 거부·SQLite 원자성/재개방·독립 wire CLI.
- Java 고유187개: 기존 MappingPublicationTest133개는 전체 실행에서 통과. 최종 package 집중 실행의 LogicalStructure3 + CrossGraph18 + Lifecycle18 + Templates13 + Gate2 =54개 통과. 이 두 범위는 겹치지 않는다. 전체 실행의 새 테스트 실패를 최종 집중 재실행으로 수정한 것이며, 단일 명령187개 성공으로 표현하지 않는다.
- 최종 외부 네트워크 차단 브라우저/HTTP/SQLite/실제 Java 연계34개 통과. [고정 입력·결과 JSON](mapping-template-results.json). 구현·계약·fixture·검사 스크립트 SHA가 현재 파일과 일치함을 재확인했다. network none / localhost만 사용하며 개인키가 evidence에 없음을 검사했다.
- 최종 Python 고유1,107개 통과: unit406개(신규24+기존382) + P7 fixture701개. [전체 Python 실행의 고정 입력/결과](mapping-templates-python-results.json) · [P7 701 결과](mapping-templates-p7-regression.json) · [최종 요약](mapping-templates-summary.json). Python 실행의 backend/contracts/fixtures/editor/evaluation 및 JAR pin은 현재 파일과 동일하다. 화면/미리보기 race 보완 이후의 최종 frontend/driver는 별도 UI34 실행에서 현재 파일 SHA 일치를 확인했다. 반복 실행은 고유 수치에 더하지 않는다.

## 실수·수정·중단 기록

원시 표현 전체를 슬롯 signature에 묶은 최초 자료는 decoded-type 경계로 교체하여 하나의 템플릿을 네 PLC가 공유하도록 했다. 초기 raw 자료는 build/mapping-templates/initial-raw-slot-*에 보존했다. 원래 바인딩 ID가 여러 적용본에서 충돌한 문제는 적용본 prefix + memberPath 해시로 수정했다.

초기 Java 시험 fixture의 proposer 불일치와 schema 오류 기대값을 수정했다. 전체 Java 실행의 provenance 생략 control은 존재하지 않는 proposal 2.17을 지정하여 실패했다. 실제 구 envelope 2.0으로 수정한 최종 집중 실행에서, 로컬 수신은 성공하지만 registry 승인은 provenance-required로 거부됨을 확인했다. Maven target에 남은 초기 fixture 파일 mappingTemplates/2.json은 source inventory와 비교하여 별도 build 위치로 보존했고 최종 resource 목록69개 SHA를 맞췄다.

초기 브라우저 시험은 저장 후 비동기 카드 갱신 대기와 접힌 details의 가시성 조건 때문에 실패했다. 제품에는 조회/검증/저장 진행 상태, 낡은 비교 무효화와 최신 revision 화면 표식을 추가했으며 시험은 최신 화면과 실제 펼친 비호환 사유를 확인하도록 수정했다. 대체된 이전 Python 컨테이너와 Java 검사 한 실행은 자원 중복을 줄이기 위해 명시적으로 중단했다. 중단/실패 실행을 통과 수치에 더하지 않는다.

최종 호환성 보완에서는 기존 already-engineered 입력 단계, BCD16 Int32·native bit/bit view Boolean·FixedArray의 해석 타입, 직접 슬롯에 없는 view 부모 pin을 추가했다. 최초 view fixture가 잘못된 새 enum(engineering) 때문에 거부된 기록을 보존하고 실제 기존 명칭으로 수정했다. view fixture는 슬롯1개/소스 snapshot3개 및 부모 워드 HEX 00 80 → true를 검증한다.

원시 Java 로그: build/mapping-templates/java-logs. [최종 package54 실행](mapping-templates-effective-types-tests.log) · [기존 Publication133 통과 및 새 control 실패가 포함된 전체 실행](mapping-templates-final-all-tests.log). 각 격리 run 폴더에는 입력 archive/driver hash, Docker network none·read-only seed 설정, 요청/결과와 screenshot, 재개방 가능한 SQLite와 공개키만 포함한 서명 registry를 보존한다. 개인키는 임시 디렉터리에서만 생성하고 evidence에 남기지 않는다.

## 현장 PoV

실제 문서/설정의 슬롯 의미 정답·단위/계수·운전 정책·native/export 해석, 추천 오매핑률/누락, 전체 작성/두 번째 설비 적용/개정 검토 시간, 작업자 이해도/편의성과 실제 소비자 inventory는 미검증이다. 합성 성공이 이 항목을 대신하지 않는다.


## 화면 QA와 시연

슬롯 후보/가상 입력과 저장 버튼, Boolean view의 해석 타입·부모 워드/HEX 입력·true 결과, Bifrost 발행 상태 화면을 직접 확인했다. [입력 슬롯](mapping-templates-slots.png) · [view 부모와 결과](mapping-templates-view-parent.png) · [발행 상태](mapping-templates-publication.png).

localhost:59787, 별도 build/mapping-templates-ui/editor.sqlite3 revision6. 검증된 합성 run 20261018-124900-46c1862e의 SQLite 백업·불변 제출·공개키만 포함한 registry를 복제했다. canonical workspace 행은 그대로이며 로컬 submission 경로 핸들만 이동했고 relocation.json에 기록했다. 최종 JAR로 copied submission을 다시 검증하여 published/accepted 상태를 확인했다. 기존 DB·registry·서버는 변경하지 않았다. 사유/작성자·슬롯 라벨·호환 후보·추천 채우기·기존 연결 복원·전후 diff·응답 도중 가상 값 변경 시 재비교·비교 완료 전 저장 차단을 제공하지만 실제 작업자 편의성의 정량 검증은 현장 PoV다.
