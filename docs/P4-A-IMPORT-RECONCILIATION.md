# P4-A B 미해석 해결과 재가져오기 병합

## 범위와 재사용

현장 파일 없이 XLSX 및 tyr-config-v1 합성 자료로 검증한다. 기존 bounded parser·columnMap·템플릿/alias·원본 bytes/hash·locator·접근 정의 편집·SQLite JSON/CAS·P5 검토·P6 제출 closure를 재사용한다. 신규 범위는 2.14 import-batch의 검토 이력·채택 기준·3방향 병합 기록, 해결/채택/비교/충돌 선택 화면, 저장 전이 보호, 독립 Java 검증이다. parser는 원본을 재해석하여 관측과 비교하며, 미해석 주소식·수식·SQL을 실행하지 않는다.

기존 2.6 계약/fixture를 변경하지 않는다. 처음 검토 또는 reviewed 채택을 할 때 해당 batch만 2.14로 명시적으로 승격하며 원본·관측·contextConnections는 유지한다. workspaceVersion 2.0, SQLite 테이블·기존 migration/CAS/시나리오는 재사용한다. 2.14를 모르는 이전 편집기/게이트의 쓰기 지원을 가정하지 않는다.

## 검토 계약

2.14는 기존 import-batch 필드에 reviews, adoptions, reconciliation을 더한다. 원본 observations의 raw/originalColumns/issues/draft/derivation은 변경하지 않는다.

reviews는 observationId·observationSha256·previousReviewSha256, reviewer·reason·reviewedAt을 필수로 기록한다. 같은 관측에 대한 후속 결정은 직전 결정 hash를 연결한다. reviewer는 작성 시점 선언이며 Bifrost의 암호학적 승인 주체 인증과 다르다.

resolve-source는 명시적 recordKey와 완전한 PLC 읽기 source-definition을 제공한다. ID는 imp-{batchId}-{recordKey}, version 1.0.0, status draft로 고정하고 설비·논리 연결·원본 locator를 검증한다. unknown 단위·불완전 decoding 가정·쓰기 소스·다른 설비·view 참조를 해결 완료로 만들지 않는다. 원문 수식의 cached value를 자동 채택하지 않고 검토자가 주소/타입/단위/표현을 명시한다.

exclude-non-source는 검토자·사유와 함께 비소스 항목으로 분류한다. 원본과 issues는 남고 유효 미해석 집계에서 제외한다. 이미 채택한 소스를 제외 결정으로 삭제할 수 없다. fileIssue 전체를 무시하는 결정은 없으며 수정된 지원 파일을 별도 가져와야 한다.

해석되지 않은 source JSON은 비워 두며 기존 정의의 틀 복사는 사용자가 명시적으로 선택한다. 자동으로 다른 신호의 주소/타입을 해석 정답처럼 채우지 않는다. 해결 결정 저장과 접근 정의 채택은 별도 동작이다. 새 채택은 draft이며 정의 완료/의미 검토/승인은 기존 경로를 따른다. 채택된 imported 기준을 소급 변경하는 해석 변경은 허용하지 않는다. 해당 현재 정의는 02에서 검토하고 새 배치 재가져오기로 진행한다. 채택 전의 해석 정정과 채택 후 같은 해석의 근거 보충은 hash chain으로 남긴다. 재가져오기 기준으로 사용한 batch와 reconciliation은 고정된다.

## 안정된 식별과 3방향 비교

행 번호·순서 대신 원문의 안정된 id 또는 검토자가 명시한 recordKey로 대응한다. 템플릿 전개 instance ID와 alias ID도 같은 기준이다. ID 누락/중복은 추측해서 합치지 않고 미해석·모호성으로 남긴다.

비교 기준은 이전 채택의 imported projection, 현재 작성본은 ours snapshot, 새 파일은 incoming이다. legacy 2.6은 원래 draft/importRef에서 기준을 도출한다. 2.14 adoptions는 그 당시 imported 기준과 canonical sourceId를 보존하므로 재가져오기 이후의 로컬 override를 구분한다. 기존 소스 ID·버전·매핑 sourceRef를 유지한다.

definition의 schemaVersion/access/rawRepresentation/inputStage/unit 등과 label을 top-level 필드별로 비교한다. access와 rawRepresentation 내부는 각각 하나의 원자 필드다. absent와 null을 구분한다. 한쪽만 바뀌면 그 변경을 제안하고, 양쪽에서 같은 값으로 바뀌면 합친다. 양쪽에서 다르게 바뀐 필드는 충돌로 두고 ours/incoming 선택을 모두 요구한다. 비충돌 필드를 임의 선택으로 덮어쓰지 않는다.

매칭된 소스에는 현재 정의 전체 유지(retain)도 제공한다. 이 경우 충돌 필드별 선택 없이 ours를 결과로 보존하며, incoming 기준과 명시적 유지 결정을 감사 기록에 남긴다. 새 소스는 adopt/skip을 선택한다. 새 파일에서 사라진 소스는 retain만 허용하며 자동 삭제하지 않는다. 제거 항목의 기준을 tombstone adoption으로 보존해 다시 나타나도 같은 canonical ID로 연결한다.

미해석 새 파일은 병합할 수 없다. 원문만 저장한 뒤 해결/비소스 분류하고 그 배치를 incoming으로 선택하여 다시 비교할 수 있다. plan에는 previousBatchRef/previousBatchSha256, workspaceSha256, ours snapshot, action/field 비교, planSha256을 고정한다. 저장 요청은 최신 revision에서 비교를 다시 계산하고 hash·선택의 완전성을 확인하여 원자적으로 적용한다.

## 저장과 근거

채택/병합한 접근 정의는 draft로 내려 재검토한다. 로컬 note는 보존하고 label은 비교 정책을 따른다. source importRef는 새 관측으로 연결한다. 제거하여 보존한 소스의 importRef는 원래 관측을 유지한다. 원본 batch는 남는다.

현재 source의 원본 근거와 의존하는 target/graph/mapping/write-definition의 evidenceRefs에 새 근거를 추가하여 기존 근거 closure를 유지한다. 그래프 타입/단위 등 다른 계약을 깨는 조합은 저장 검증에서 원자적으로 거부한다. 무효 계약을 억지로 유효하게 바꾸거나 매핑 의미를 자동 재승인하지 않는다.

2.14 원본/관측, 기존 reviews/adoptions prefix, 이미 저장한 reconciliation은 일반 workspace PUT에도 보호한다. CAS 트랜잭션에서 원본 교체·이력 삭제/축소를 거부한다. legacy 2.6은 이전 저장 동작을 유지하며 새로운 workflow 사용을 명시적으로 선택한다. DB를 여는 것만으로 body/revision을 재작성하지 않는다.

해시는 tagged-json-v1: object key를 Unicode code point 순서로 정렬하고, null/boolean/string/number/array/object에 구분 tag를 붙이며 숫자는 정규화한 십진 문자열로 표현한다. JSON은 공백 없이 UTF-8, ASCII escaping 없이 직렬화한다. boolean과 숫자를 구별하고 Unicode·숫자 표현의 구현 차이를 fixture로 독립 검증한다. 기존 workspace/P6 hash 규칙을 교체하지 않는다.

## 화면과 API

10 파일 가져오기에 검토 batch/관측 선택, 원문·미해석·검토 이력, 명시적 source JSON/recordKey·검토자·사유, 해결 저장·초안 채택을 추가한다. 병합 화면은 이전 batch와 상단 새 파일 또는 이미 보존/검토한 incoming batch를 선택한다. 변경 필드·충돌·새/제거 항목, 현재/새 주소·타입·단위, 원본 비교 snapshot과 명시적 처리 선택을 표시한다.

- GET /api/import-workflow: 현재 revision과 관측/직전 결정 hash, effective draft. 읽기 전용.
- POST /api/import-review: 해결/제외 결정과 원본·직전 결정 hash.
- POST /api/import-adopt-reviewed: 해석된 관측의 별도 draft 채택.
- POST /api/import-merge-preview: revision·previousBatchId + request 또는 보존한 batchId. 읽기 전용.
- POST /api/import-merge-apply: 동일 입력 + planSha256·choices·검토 metadata. 재계산 후 CAS 저장.

기존 Host/Origin/X-Tyr-Editor·2 MiB 요청·1.9 MB workspace·512 KiB 파일·16 batches·256 관측/채택 한도를 유지한다. 비교 action은 최대 512개다. 대량 history 보관/GC는 후속이다.

## Bifrost 계약 경계

제안 envelope는 기존 2.6/2.7을 유지하고 새 import-batch 2.14를 함께 싣는다. 재가져오기 감사 기록과 previousBatchRef, 원본 artifact/관측을 제출 closure에 포함한다. active source를 유지한 경우에도 관련 reconciliation 기록을 포함해 미해석이나 조작된 계획이 숨겨지지 않게 한다.

Java는 JSON/schema 데이터만 받아 검토 hash chain·source 형태/연결/근거·완전성, 이전 batch hash, 3방향 action/field 계산·choices·results·adoptions를 독립 검사한다. Týr 코드를 import/호출하지 않는다. 기존 batch의 원문 parser replay는 Týr가 수행하며, Java가 vendor parser 해석 정확성을 인증한다고 주장하지 않는다. schema의 교차 버전 참조는 번들 내부 version/file만 허용하며 원격 조회하지 않는다. 최종 승인은 기존 별도 Ed25519 주체의 Bifrost 승인/파일 발행이고 운영 활성화는 하지 않는다.

## 합성 검증과 현장 PoV

[fixture 안내](P4-A-B-FIXTURES.md) · [수용 결과](verification/P4-A-B-RESULTS.md). 네 PLC 프로파일·템플릿/alias·수동 주소 해결·비소스 분류, row reorder, 비충돌 병합·충돌 선택·현재 정의 유지, 제거/재등장, 원본/이력 조작·CAS 충돌·기존 2.6 발행을 검증한다.

실제 vendor 설정 문법·현장 XLSX layout/헤더/타입명·PDF/.xls·UDT 상속/cross-file alias, record ID 안정성, 비소스 분류와 수동 해석의 독립 정답, 병합 검토 시간/오매핑률은 현장 자료와 담당자 PoV가 필요하다. 같은 이름/타입/단위만으로 의미 동등성을 자동 확정하지 않는다. 실제 장치 통신·외부 SQL·쓰기 실행은 계속 제외한다.
