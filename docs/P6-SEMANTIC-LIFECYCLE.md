# P6 의미 URI 개정·폐기

이 기능은 기존 URI의 의미 불변 계약을 유지하면서 관리 이력을 추가한다. 대상은 구성된 한 Bifrost registry의 모든 보존 릴리스다. 장치 접속·외부 SQL·쓰기 실행·운영 활성화는 없다. 합성 fixture로 검증하며 현장 의미 정답과 운영 정책 승인은 별도 PoV다.

## 계약과 상태

신규 `2.18.0/semantic-lifecycle` 문서는 URI별 revision 1~256의 불변 이벤트다. ID/version, semanticId, action, previousEvent의 ID/version/canonical SHA256, 의미 signatureSha256, label/description, reason, authoredBy/authoredAt, replacementSemanticId를 고정한다. 전체 이벤트 한도 1,024개다. 기존 계약 파일은 수정하지 않는다. wire bundle은 전체 선행 이벤트와 모든 관리 대상 의미 정의를 포함하며 proposal만 2.18로 올린다. 신 기능을 모르는 구 Bifrost는 거부한다.

- 기존 URI는 이벤트 없이 active revision 0이다.
- revise는 표시 이름·설명·개정 사유를 갱신하고 현재 active/deprecated 상태를 유지한다. 기존 semantic-definition을 덮어쓰지 않는다. 18 화면이 관리 메타데이터를 표시한다.
- deprecate는 active에서만 허용한다. 대체 URI는 명시적으로 존재해야 하며 선택 사항이다. 기존 매핑은 계속 승인 가능하고 영향 목록에 남는다.
- retire는 deprecated에서만 허용한다. retired는 종단 상태다. 해당 URI와 구조/구조 배열 조상 URI를 사용하는 새 읽기·쓰기 매핑의 승인·발행을 거부한다.
- 역할·타입·단위·구조·shape가 달라지면 기존 URI 개정으로 처리할 수 없다. 새 URI를 정의하고 사용 중단 권고 시 대체 URI를 명시한다. 대체 관계는 alias나 단위 변환 또는 자동 재매핑이 아니다.
- 선행 이벤트 해시·연속 revision·같은 이벤트 ID의 본문 충돌·시간 역행·알 수 없는 URI·자기/순환 대체·폐기된 대체 URI·상태 전이를 독립 Python/Java가 검증한다. 같은 불변 이벤트 재전송은 중복 제거하며 fork는 거부한다. 시간은 알려진 offset과 최대 6자리 소수를 사용한다.

canonical SHA는 기존 정렬 키·UTF-8·compact JSON 규칙이다. signature는 기존 logical structure와 전역 의미 카탈로그의 role/valueType/unit 및 구조 멤버/shape 계약을 사용한다. 숫자·단위·계수의 현장 의미가 맞다는 증거가 되지는 않는다.

## 작성·저장·영향 확인

workspace 2.0에 선택적 `semanticLifecycles` 배열을 추가한다. 기존 SQLite workspace JSON 행에 CAS 트랜잭션으로 저장하므로 기존 테이블·스키마·이전 행을 자동 이전하거나 재작성하지 않는다. 저장 이후 이벤트 수정·삭제를 거부한다. 폐기로 인해 남은 매핑은 수정할 수 있도록 로컬 초안으로 저장하되 `lifecycle.retired-binding`을 표시한다. 제출된 매핑에 같은 문제가 있으면 Bifrost가 거부한다.

18 화면과 `GET /api/semantic-lifecycle`은 URI별 작성본/발행본 상태·개정 사유·작성자·시각·선행 해시와 영향을 표시한다. 매핑/쓰기 정의 ID·버전, binding ID, 설비·객체·멤버 경로를 구분한다. nested structure/structure array의 조상 URI도 집계한다. 이벤트별 원본 발행 릴리스도 별도 목록으로 고정하여 lifecycle-only 릴리스까지 추적한다. 발행 영향에는 release ID/version/SHA 및 currentHead 여부를 표시하여 과거 릴리스와 현재 head를 구분한다. 여러 의미 조상이 같은 binding에 영향을 주면 URI별 별도 관계로 표시한다.

`POST /api/semantic-lifecycle-apply`는 요청 revision을 검사하고 이력을 append한다. Bifrost에 이미 발행된 선행 이력은 검증 후 작업공간에 명시적으로 포함된 URI에 한해 가져온다. 대체 URI와 관련 체인이 현재 작업공간에서 정의되지 않으면 저장을 거부한다. 조회 중 registry와 로컬 이력이 충돌하면 성공으로 숨기지 않는다. 불변 로컬 branch의 충돌은 덮어쓰지 않고 별도 작업공간에서 발행된 체인을 기준으로 다시 작성한다. 자동 branch rebase와 registry-only 의미 정의 편집은 후속이다.

## Bifrost 승인·발행 경계

13 화면의 기존 immutable submission/서명 승인/파일 릴리스 경로를 재사용한다. 매핑을 선택하면 관련 소스·그래프·근거와 함께 모든 관리 의미 정의 및 선행 이벤트를 고정한다. 개정 이력이 있으면 매핑을 선택하지 않고 lifecycle-only 제안도 제출할 수 있다. 이 경우 매핑과 쓰기 정의는 포함하지 않는다. 이력이 없는 구 작업공간의 빈 제안은 허용하지 않는다.

Týr의 작성자 필드는 선언 메타데이터다. 승인 권위는 등록 키와 두 확인자를 요구하는 Bifrost 서명이다. 이벤트 본문·제안·파일 묶음·변경 diff가 기존 승인 해시에 묶인다. approve/publish/recover가 기존 registry lock 안에서 모든 보존 이력과 다시 병합 검증한다. 승인 뒤 다른 스트림이 URI를 폐기한 경우에도 발행 시 재검사하여 오래된 매핑을 거부한다. 구 bundle에서 lifecycle 문서를 생략해도 registry의 폐기 정책을 우회할 수 없다.

`java -jar bifrost-gates.jar mapping lifecycle <registry>`는 검증된 전체 이력·URI 상태·읽기/쓰기 영향과 canonical catalogSha256을 반환한다. 기존 `mapping catalog` 2.16 응답 계약은 유지한다. 서명·파일 무결성 오류, 미복구 transaction은 정상적인 빈 이력으로 처리하지 않는다. 구 릴리스와 head가 없는 보존 릴리스도 삭제하지 않는다.

폐기는 앞으로 제출하는 매핑 계약을 차단한다. 다른 스트림의 기존 head나 현장 실행 상태를 소급해서 제거하지 않는다. 현재 head의 남은 사용처를 영향 목록에서 검토한 뒤 각 스트림의 명시적 후속 릴리스로 정리한다. lifecycle-only 릴리스도 운영 활성화를 수행하지 않으며 runtime mapping registry를 대체하지 않는다.

## 검증과 후속

합성 mixed source fixture는 기존 PLC·상수·솔루션 태그·외부 값과 읽기/쓰기 정의를 보존하고 revise/deprecate 체인을 추가한다. 음성 검사에는 retirement binding, fork/gap/hash tamper, signature drift, replacement cycle/retired target, stale CAS와 승인 후 전역 상태 변경을 포함한다. nested/array 영향은 기존 구조 fixture로 검증한다. network-none harness는 기존 DB read-only 보존, 브라우저 작성·저장·reload·영향 조회·제출, 실제 Java key/서명 승인·발행, lifecycle-only 폐기, 구 bundle 우회 거부를 수행한다.

실제 URI 소유권·개정/폐기 권한 조직, 적절한 폐기 유예 기간, 대체 의미 정답, 실제 소비자 inventory, 현장 변경 검토 시간, vendor native/export 정답은 현장 PoV다. registry 간 federation·외부 anchor·IAM 제품 연동·운영 활성화·일반 ontology/version migration은 이번 완료 범위가 아니다.
