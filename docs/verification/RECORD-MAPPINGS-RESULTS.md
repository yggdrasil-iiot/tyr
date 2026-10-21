# 레코드·결과 집합 오프라인 수용 검증

2026-10-18. 실제 현장 PoV는 미수행이다. 장치 통신·외부 SQL·쓰기 실행·runtime 활성화는 제외했다.

## 최종 실행

- 신규 Python 레코드 검증: **30/30**. `build/record-mappings/python-final-records.log`. 스키마·필드/단위/입력 단계·변환/cast 손실·0/1/N·최대 행·명시적 선택·복합/중복/누락 키·NULL/default·원본 열 보존·품질/미래 시각·기존 temporalPolicy·URI 폐기 영향·템플릿 pin/개정·SQLite CAS/불변 이력/재개방·독립 CLI·기존 파일 SHA. Preview에서 socket/SQLite provider 호출을 금지한 검사 포함.
- Java 고유 검증: **202/202** = 기존 Publication133 + 최종 package66(CrossGraph18/RecordMappings15/SemanticLifecycle18/Templates13/Gate2) + LogicalStructure3. 반복 실행한 클래스는 중복 합산하지 않았다. `build/record-mappings/java-logs/`의 Maven 로그와 JUnit XML. 신규15개는 독립 투영 oracle, record-only, 재해시 변조9종, 파일 무결성, registry fork, 두 키 서명 승인/발행, 의미 폐기/영향을 포함한다.
- 최종 브라우저·HTTP·SQLite·독립 Java 연계: **33/33**. `build/record-mappings/20261018-140126-7d8e8ea9/record-results.json`. 입력 변경/변조 plan·stale CAS·읽기 전용 compose/preview·불변 레코드 저장·시나리오 별도 저장/재개방·키 순서·단위/스케일/cast/손실·0건 array/object·중복/NULL/bad 품질·모델에서 필드 초안·신규 템플릿 원자 저장·기존19 사용처·13 제출/실제 서명 승인/불변 릴리스/상태 refresh. `docker-inspect-before.json`: network=none, cap-drop=ALL, readonly 입력 archive/driver/seed. 브라우저 요청은 localhost origin만, JS 오류0, evidence 내 private key0.
- Python·fixture 고유 **1,137/1,137** = 기존 unit406 + 기존 P7 fixture701 + 최종 records30. `build/record-mappings/20261018-135503-72a1760b/record-results.json`의16개 suite 모두 통과, `regression.json` 701/701. 그 실행의 records29는 이후 사용처 검사까지 추가한 최종 records30으로 대체하여 합산했고 반복 unit은 중복 계산하지 않았다.

## 계약과 바이너리 보존

`docs/verification/record-mappings-baseline-pins.json`의 기존 **797파일**(contracts84=83schema+README, fixtures710, evaluation1, editor2) SHA를 유지했다. 기존 계약 파일은 수정하지 않고2.20의4개 schema만 추가했다. 현재87개 schema의 Týr↔Bifrost resource 사본 및 최종 JAR entry bytes가 같다. Java mapping compiled class bytes와 JAR도 일치한다.

최종 `bifrost-gates.jar` SHA256: `084654260d8a4d7e49bc39a762d19af6191fd08a7eb40b9e56638f647b828efe`. 최종 browser driver가 사용한 JAR SHA도 같다. 이전 demo/DB를 변경하지 않았다. 별도 `build/record-mappings-ui/editor.sqlite3` revision4와 signed registry/불변 제출본을 복제하여 **http://127.0.0.1:59788/**에서 실행했다. Docker 내부 경로인 로컬 제출본 handle만 재배치했고 workspace revision/body는 동일하게 보존했다. `relocations.json`에 경로/원본 SHA 기록, private key는 복제하지 않았다.

## 검증 fixture의 해석

의미 모델·결과 스키마는 합성이다. `oracle.json`의 명목 공학값과 정확한 최종 IEEE cast 값을 분리했다. 수치 기대값은 고정 선언이며 preview 결과로 덮어쓰지 않는다. `static-projections.json`은 Python wire 투영을 Java가 독립 재생성하여 비교하는 언어 간 oracle이며 실제 현장 의미 정답을 인증하지 않는다.

역순2행은 키 순서로 배열을 구성하고, 같은 템플릿을 다른 설비의 key-selected object로 재사용한다. 123450Pa→123.45kPa의 Double cast는 binary64 손실을 uncertain으로 드러낸다. nullable 기본값은 원본 NULL을 숨기지 않는다. 오류가 난 행의 일부 진단을 보존하되 최종 결과 전체를 차단한다. 가상 행은 Bifrost release에 포함하지 않는다.

## 사전 실패와 수정

초기 Python 검증에서 record build 호출 누락으로 빈 record-only proposal이 생성되는 문제와 개정 테스트의 evidence ID 누락을 수정했다. 새 JS 작성 폼의 삼항식 구문 오류를 수정했다. 추가 검증의 lifecycle action/temporal schema 오류는 테스트 선언을 바로잡았다. 초기 UI driver의 접힌 JSON 상세 및 신규 작성 시 필수 작성자/근거/설비 입력 누락은 실제 폼 제약을 우회하지 않고 입력 흐름을 수정했다. 각 최초 로그와 실패 컨테이너 결과는 고유 build 폴더에 남겼으며 최종 통과와 합산하지 않았다.

## 현장 PoV 및 후속 범위

미완료: 실제 DB 키 안정성·중복/NULL 의미·단위/계수 정답·vendor/provider export·조회 시각과 PLC 시각의 정합성·권한/소비자 계약·작업자 작성/검토 시간과 오류율. actual SQL/DB connection/네이티브 DB 타입 전체/join/group/무한 stream/운영 활성화는 구현하지 않았다. 가상 snapshot의 capturedAt/quality는 DB atomic transaction 인증이 아니다.
