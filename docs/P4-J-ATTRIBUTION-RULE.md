# P4-J 귀속·영향 규칙(attribution rule, impact rule)

## 범위
이 문서는 forseti 인도 계획(delivery plan)의 2단계를 규정한다. forseti는 스트림 처리 작업(stream-processing job)이며, 여기서 작성하는 규칙들의 소비자이다. forseti 설계 문서의 인도 계획 2행에 적힌 사양은 다음과 같다. 대상 시스템은 Tyr이며, 작업 범위는 "두 종류와 두 프로필 모두의 작성, 픽스처, CI 내 Bifrost 인수 시험(authoring for both kinds and both profiles, fixtures, Bifrost acceptance test in CI)"이다. 이 단계의 완료 관문(gate)은 "Tyr가 제작한 번들을 Bifrost가 승인함"이다.

본 작업에 앞서 작은 forseti 사양 수정 사항 하나가 별도 풀 리퀘스트(yggdrasil-iiot/forseti#3)로 먼저 반영되었다. 픽스처의 도구(tool) 레벨은 `WORKUNIT_11`이며, 스테이션은 `WORKCELL_6`이다. 아울러 Bifrost의 추가 정규식 패턴 거부 기준들이 사양에 기록되었다.

단일 계약 버전인 `2.27.0`에는 두 가지 문서 종류가 정의된다.
- `attribution-rule`: 1단계 규칙이다. 스테이션과 도구별로 거버넌스된 공정 멤버를 MES 점유(occupancy) 정보와 결합하여 방문(visits)을 생성한다.
- `impact-rule`: 2단계 규칙이다. 동일 패키지의 귀속 규칙이 생성하는 방문과 대조하여 품질 인시던트(quality incidents)를 판정한다.

두 규칙 문서는 모두 선언형 문서이다. 내부에는 SQL 문이나 스크립트가 전혀 들어가지 않는다.

Tyr는 두 종류(`attribution-rule`, `impact-rule`), 두 바인딩 프로필(`occupancy-binding`, `incident-binding`), 그리고 `plc-stamped` 규칙에 필요한 타입 지정 `String` 소스를 모두 작성한다. 승인 권한은 기존 2키 매핑 릴리스 체계를 유지하는 Bifrost에 머무른다. Tyr에는 승인 권한이 없으며, 작성한 파일들을 Bifrost의 `mapping` 관문으로 제출한다.

forseti는 이 규칙들의 소비자이며 이벤트 스키마도 forseti가 보관한다. `format.schemaSha256` 값이 forseti의 내장 스키마와 일치하는지 확인하는 일은 forseti가 작업을 시작할 때 확인하는 기동 시점 검사(`binding.schema-mismatch`) 대상이며, Tyr나 Bifrost의 검사 대상이 아니다.

Tyr는 forseti가 작업 시작 시점이나 실행 시점에 직접 확인해야 하는 항목들을 검증한다고 주장하지 않는다. Tyr가 검증 범위에 두지 않는 사항은 다음과 같다.
- `format.schemaSha256`이 forseti의 내장 스키마와 일치하는지 확인하는 검사
- 인시던트 스키마가 `kinds[]` 목록의 각 항목을 지원하는지 확인하는 검사
- 원격 측정(telemetry) 데이터가 식별자와 측정값을 단일 메시지에 함께 싣고 있는지 확인하는 검사
- 브로커에 토픽이 실제로 준비되어 있는지, 혹은 데이터 발행자가 정해진 어휘를 준수하는지 확인하는 검사
- 스캔 주기가 `coverage.expectedPeriodMs`와 일치하는지 확인하는 검사
- Bad 품질, 방문, 수정, 영향과 결부된 일체의 런타임 동작
- 프로필의 `scope`를 규칙의 스테이션 목록과 비교하는 검사(Tyr도 Bifrost도 비교하지 않는다)

## 계약 2.27.0
Bifrost에서 바이트 단위로 동일하게 `contracts/2.27.0/` 디렉터리로 복사한 스키마 파일 다섯 개를 사용한다.
- `attribution-rule.schema.json`: 신규 종류 `attribution-rule`을 정의한다.
- `impact-rule.schema.json`: 신규 종류 `impact-rule`을 정의한다.
- `source-definition.schema.json`: 제어기의 유닛 ID와 방문 ID를 `String`으로 발행할 수 있도록 재발행한 2.7.0 `plc` 소스 스키마이다. 2.7.0 소스는 여전히 `String`을 선언할 수 없다.
- `common.schema.json`: 새로운 `$id`를 지정하고, 파일 항목 종류 열거형(enum)에 두 신규 종류(`attribution-rule`, `impact-rule`)를 추가하며, 타입 지정 소스의 값 타입 목록에 `String`을 추가한 2.26.0 사본이다.
- `mapping-proposal.schema.json`: `$id`와 `schemaVersion` 두 버전 상수를 모두 `2.27.0`으로 지정한 2.26.0 사본이다.

봉투 검사 규칙인 `rule.envelope`에 따라, 2.27.0 소스 정의를 포함하여 `schemaVersion`이 `2.27.0`인 문서는 오직 2.27.0 제안서 안에서만 이동한다. 이를 지키지 않은 패키지는 `rule.envelope` 거부 코드로 거부된다. 반면 2.26.0 명령 링크(`command-binding`)는 2.27.0 제안서에 담겨 전달될 수 있다. 명령 링크 봉투 규칙인 `command-binding.envelope`에서 2.26.0 제안서와 2.27.0 제안서를 모두 유효한 상위 제안서로 받아들이기 때문이다.

기존 시험인 `test_p6`(`Receiver.test_shared_schema_copies`)는 인접한 Bifrost 체크아웃 디렉터리(`../bifrost`)와 비교하여 이들 복사본의 바이트 일치를 확인한다.

## 문자열 소스와 PLC 소스 폼
PLC 소스 폼은 타입 지정 접근 프로필(예를 들어 OPC UA를 거쳐 접근하는 S7-1500)에 한하여 `String`을 원시 값 타입(raw value type)으로 제공한다. 바이트 주소 지정 프로필은 기존 목록을 유지하며, 바이트 주소 지정 프로필의 코덱 옵션인 "String (codec)" 또한 바뀌지 않고 그대로 유지된다. 관련 코드는 `frontend/app.js`의 `accessFields`에 있다.

원시 값 타입이 `String`으로 지정되면 폼은 소스를 `schemaVersion` `2.27.0`으로 작성한다. `String` 이외의 다른 모든 타입은 이전과 마찬가지로 `2.7.0`으로 작성한다. 관련 코드는 `frontend/mixed.js`의 `draftSource`에 있다.

이렇게 작성된 소스를 저장하는 백엔드 경로는 `PUT /api/workspace` 요청 수신에서 출발하여 `server.check_state`를 거치고, 스키마 검사(`validate_schema`)와 계약 검증 함수 `validate_contracts.source_rules`로 이어진다. 여기서 2.27.0 소스는 기존 2.7.0 소스 규칙으로 검사한다.

1.x 레거시 작업공간은 2.7.0 소스와 2.10.0 소스를 거부하듯이 2.27.0 소스도 거부한다.

패키지 빌더는 패키지 안에 2.27.0 소스가 하나라도 있으면 `rule.envelope` 요구 조건에 맞추어, 내부에 규칙 문서가 없는 경우에도 2.27.0 제안서(`mapping-proposal`)를 작성한다.

`plc-stamped` 픽스처의 식별자 소스들은 폼이 생성하는 모양과 완전히 동일한 형태(동일한 키, 동일한 `evidenceRefs`)로 작성된다.

## 바인딩 프로필
설계 결정(사양 Decision 4)에 따라 각 바인딩 프로필은 번들 안에서 `evidence-artifact` `1.1.0`의 데이터 파일로 들어간다.

`occupancy-binding` 프로필 아티팩트의 ID 접두사는 `occupancy-binding-`이며, `file.mediaType`은 `application/vnd.forseti.occupancy-binding+json`, `format.schemaId`는 `urn:forseti:schema:occupancy:1.0.0`이다. 프로필 데이터 파일 내부에는 정확히 아래 필드들만 들어가며, 모든 필드는 필수 항목이다.
- `profileVersion`: 상수 `0.1.0`이다.
- `topic`: 대상 메시지 토픽 문자열이다.
- `format`: `schemaId`와 `schemaSha256`으로 구성된 객체이다.
- `identity`: `scheme`(상수 `mes-unit-id`)과 단위 식별자를 판별하는 정규식 문자열인 `pattern`으로 구성된 객체이다.
- `enter`: `bizStep` 필드를 담은 객체이다.
- `leave`: `bizStep` 필드를 담은 객체이다.
- `correction`: `errorDeclaration`(상수 `reissue-same-event-id`)과 오류 사유 목록인 `reasons`로 구성된 객체이다.
- `timestampBasis`: 상수 `eventTime`이다.
- `sources`: 문자열 배열(`sources[]`)이다.

`correction.reasons`는 비어 있지 않은 목록이어야 하며, 중복이 없는 고유한 값들로 채워져야 한다. 각 값은 두 가지 EPCIS 오류 사유인 `urn:epcglobal:cbv:er:did_not_occur`와 `urn:epcglobal:cbv:er:incorrect_data` 중에서만 선택할 수 있다. `sources[]` 역시 비어 있지 않은 목록이어야 하며, 중복 없는 고유한 문자열들로 구성되어야 한다.

`incident-binding` 프로필 아티팩트의 ID 접두사는 `incident-binding-`이며, `file.mediaType`은 `application/vnd.forseti.incident-binding+json`, `format.schemaId`는 `urn:forseti:schema:incident:1.0.0`이다. 프로필 데이터 파일 내부 필드는 다음과 같다.
- `profileVersion`: 상수 `0.1.0`이다.
- `topic`: 대상 메시지 토픽 문자열이다.
- `format`: `schemaId`와 `schemaSha256`으로 구성된 객체이다.
- `kinds`: 비어 있지 않고 중복 없는 고유한 문자열 배열(`kinds[]`)이다. Bifrost는 이 배열이 비어 있지 않고 중복이 없다는 점만 검사한다.
- `equipmentRefBasis`: 상수 `isa95-path`이다.

아티팩트의 `scope`는 프로필이 포괄하는 스테이션 ID(설비 인스턴스 ID) 목록으로 지정된다. `format.schemaSha256`은 64자의 소문자 16진수 문자열이어야 한다. 이 값은 forseti의 스키마가 확정되는 3단계 전까지 픽스처 안에서 자리표시자 역할을 한다.

`identity.pattern` 정규식은 유닛 ID 전체와 일치해야 한다. 구문 검사에서는 Java와 ECMA-262 공통 문법만 받아들인다. 구문 검사에서 통과되는 문법 요소는 다음과 같다.
- 리터럴 문자
- 임의의 한 문자와 일치하는 점(`.`)
- 범위 표기와 부정 표기가 있는 브래킷 클래스(`[...]`, `[^...]`)
- 수량자인 `*`, `+`, `?`, `{m}`, `{m,}`, `{m,n}`
- 대안(선택) 연산자인 파이프(`|`)
- 비캡처 그룹인 `(?:…)`
- 알파벳과 숫자가 아닌 ASCII 문자 앞에 붙은 역슬래시(`\`)

반면 다음 구문 요소들은 거부된다.
- 시작 앵커와 끝 앵커(`^`, `$`)
- 전방 탐색과 후방 탐색을 아우르는 룩어라운드(lookaround)
- 역참조(backreferences)
- 정규식 플래그(flags)
- 캡처 그룹과 이름 있는 캡처 그룹
- 단축 문자 클래스(shorthand classes)
- 게으른 수량자(lazy quantifiers)와 소유격 수량자(possessive quantifiers)
- 단독으로 쓰인 여는 중괄호(`{`)

Bifrost는 선행 풀 리퀘스트(forseti#3) 사양에 기록된 바와 같이 다음 항목들을 추가로 거부하며, Tyr 역시 이와 동일하게 거부한다.
- 32단계를 초과하여 깊게 중첩된 비캡처 그룹
- 패턴 문자열 안에 직접 작성된 UTF-16 서로게이트 코드 유닛(이에 따라 모든 보조 문자가 거부됨)
- 2147483647을 초과하는 반복 상한값
- 브래킷 클래스 내부에서 시작 문자가 끝 문자보다 큰 역전된 범위

반복 범위에 지정된 선행 0은 Java가 계산하는 방식대로 처리한다. 예를 들어 선행 0이 4,500개 붙어 있는 반복 상한값도 정상 범위 내의 숫자라면 유효한 구문으로 받아들인다.

프로필에 추가 필드가 들어가거나, 필수 필드에 빈 값이 들어가거나, 지원하지 않는 정규식 문법이 사용되면 `attribution.binding-profile` 또는 `impact.binding-profile` 거부 코드가 발생하면서 검증이 실패한다.

외부에서 바이트 형태로 가져오는 읽기 바인딩(read binding)이나 서버 인증서와 달리, Tyr는 바인딩 프로필을 직접 작성한다. 작업공간 모델은 `occupancyBindings`와 `incidentBindings` 레코드를 저장하며, 각각 최대 64개까지 허용한다. 이 레코드들은 편집기 스키마인 `editor-contracts/1.0.0/occupancy-binding.schema.json`과 `incident-binding.schema.json`으로 검사한다. 편집기 스키마에 정의된 레코드 필드는 `id`, `version`, `label`, `origin`, `capturedAt`, `reviewer`, `product`, `scope`, `profile`이다.

`profile` 객체는 `vc.save`를 거쳐 `data/occupancy-binding-<n>.json` 또는 `data/incident-binding-<n>.json` 파일로 기록된다. 저장 시에는 2칸 들여쓰기와 LF 줄바꿈을 적용하고 마지막 줄 끝에 개행을 넣는다. 그리고 `evidence-artifact` 래퍼는 이렇게 기록된 파일 바이트의 SHA-256 해시를 고정한다. 편집기 스키마에서 `profile` 필드를 단순 객체(`type: object`)로 남겨 둔 것은 설계 결정이다. 필드 검증 규칙은 한 곳, 즉 Bifrost가 읽는 파일 바이트와 같은 바이트를 읽는 Tyr의 파서에만 있어야 한다.

작업공간 수준에서 발생하는 Tyr 자체의 검증 코드(사양 코드가 아닌 Tyr 내부 코드)는 다음과 같다.
- `occupancy-binding.schema`: 편집기 스키마 검증에 실패할 때 발생한다.
- `occupancy-binding.duplicate`: 중복된 바인딩 레코드가 있을 때 발생한다.
- `occupancy-binding.scope`: `scope`에 지정된 식별자가 작업공간 설비를 가리키지 않을 때 발생한다.
- `occupancy-binding.limit`: 레코드 개수가 64개 제한을 초과할 때 발생한다.
- `occupancy-binding.version-required`: 레코드 내용이 변경되었는데 새 버전을 지정하지 않았을 때 발생한다.

`incident-binding`에도 동일한 의미를 나타내는 다섯 가지 코드(`incident-binding.schema`, `incident-binding.duplicate`, `incident-binding.scope`, `incident-binding.limit`, `incident-binding.version-required`)가 적용된다.

작업공간의 모든 작성 프로필은 규칙의 참조 여부와 관계없이 Tyr의 프로필 파서로도 읽으며, 실패한 프로필은 사양 코드(`attribution.binding-profile` 또는 `impact.binding-profile`)로 거부하고, Bifrost는 규칙이 참조할 때만 프로필을 읽는다.

Tyr는 Bifrost의 리더가 파일 바이트를 읽는 방식과 동일한 절차로 프로필을 파싱한다. 바이트 맨 앞의 UTF-8 BOM은 건너뛰고, JSON 내부에 중복된 키가 있으면 거부하며, 깊은 중첩 구조가 입력되어도 프로세스 비정상 종료 없이 정해진 프로필 거부 코드를 내며 안전하게 처리를 중단한다.

## Tyr 검사

Tyr는 forseti 사양에 정의된 거부 코드를 써서 규칙을 검사한다. 이 거부 코드는 Bifrost의 검증기가 쓰는 거부 코드와 완전히 같다. 검사는 첫 실패 지점에서 즉시 멈춘다. 패키지 검증 단계(`p3a_contracts.validate_package`)는 이 실패를 단일 지적 항목 `{ruleCode, path}` 형태로 바꾼다. 여기서 `ruleCode`는 사양의 거부 코드이며, `path`에는 거부된 문서의 종류가 들어간다. 내보내기 전 작업공간을 검사할 때와 패키지 자체를 단독으로 검사할 때 모두 같은 검사 로직을 돌린다.

설비 계층 구조 자체가 올바르지 않으면 계층 구조 자체의 `hierarchy.*` 거부 코드가 먼저 남고, 뒤따르는 규칙 검사는 아예 실행하지 않는다. 즉, 설비 계층 구조의 무결성이 입증된 다음에만 귀속 및 영향 규칙 검사 단계로 넘어간다.

Tyr가 검사하는 열한 개 `attribution.*` 거부 코드와 판정 기준은 다음과 같다.

- `attribution.hierarchy-missing`: `equipmentRef`가 가리키는 설비 계층 구조 문서가 패키지 안에 없을 때 나온다. 규칙에 지정된 참조 식별자가 패키지 안의 설비 계층 구조 파일과 연결되지 않으면 검사를 더 진행할 수 없다.
- `attribution.station-unresolved`: `stations[]`에 기재된 경로가 설비 계층 구조 경로가 아닐 때 나온다. 모든 스테이션 경로는 루트 노드에서 시작해야 하며 각 하위 단계를 `:` 기호로 잇는다. 설비 계층 구조 트리에서 찾을 수 없는 경로가 하나라도 들어가면 이 코드로 거부한다.
- `attribution.station-nested`: 한 스테이션이 다른 스테이션의 조상 노드로 드러나 스테이션 사이에 계층 중첩이 생길 때 나온다.
- `attribution.member-unresolved`: 멤버와 매핑 세트 사이의 연결이 어긋났을 때 나온다. 세부 거부 조건은 다음과 같다.
  - 멤버의 `mappingId`가 소속 매핑 세트 안에 없을 때.
  - 멤버에 적힌 `metric` 또는 `semanticId`가 매핑 세트의 정의와 다를 때.
  - 매핑의 `memberPath`가 정확히 한 단계의 `member` 경로로 끝나지 않을 때.
  - 하나의 시맨틱 정의 안에 속한 리프 멤버 둘이 서로 같은 `name`을 쓸 때.
  - `opcua-node` 식별자 문자열이 `.` + `metric` 형태로 끝나지 않을 때.
  - `members[]` 목록이 완전히 비어 있을 때.
  - 동일한 `mappingId`가 `members[]` 안에 두 번 이상 중복 기재되었을 때.
  - 둘 이상의 멤버 항목이 동일한 설비 경로와 `metric` 조합으로 풀릴 때.
  여기서 `metric`은 매핑이 도달하는 시맨틱 리프의 `name`과 바이트 단위까지 정확히 같아야 한다. 이 값은 Muninn이 Sparkplug 메트릭 이름으로 발행하는 값이다.
- `attribution.member-equipment`: 멤버가 속한 설비가 유효한 공정 범위 밖에 놓였을 때 나온다. 각 멤버는 소속 매핑 세트의 `equipmentInstanceId`를 설비 계층 경로로 풀어 확인한다. 이 경로가 `stations` 목록에 든 스테이션 그 자체이거나, 그 스테이션 아래에 딸린 하위 설비(도구)가 아니면 이 코드로 거부한다.
- `attribution.activity-member`: `activity[]` 항목에 지정된 활동 멤버 정의가 어긋났을 때 나온다. 활동 항목이 멤버를 가리키지 않거나, Boolean 데이터 타입이 아닌 멤버를 지정하거나, 다른 설비에 속한 멤버를 지정하거나, 스테이션이나 스테이션 하위 설비가 아닌 곳을 가리킬 때 발생한다. 한 설비에 둘 이상의 활동 항목을 지정할 때도 이 코드가 나온다. 반면 활동 항목을 아예 두지 않은 설비는 정상으로 허용한다.
- `attribution.binding-unresolved`: `occupancyBindingRef`가 패키지 안에 든 evidence-artifact 1.1.0 문서를 가리키지 못할 때 나온다. 참조가 누락되었거나 문서 형식이 맞지 않으면 이 코드를 낸다.
- `attribution.binding-profile`: 점유 프로필 내용이 사양에 맞지 않을 때 나온다. 접두사, 미디어 타입, 필수 필드 구성, 상수 정의, 정규식 패턴 구조가 틀렸거나, 바이트 형식이 손상되어 내용을 온전히 읽어 들이지 못할 때 나타난다.
- `attribution.identity-member`: `plc-stamped` 모드에서 식별 멤버 지정이 어긋났을 때 나온다. 식별 항목의 `unitMemberRef` 또는 `visitMemberRef`가 `String` 타입 멤버가 아니거나, `presentMemberRef`가 `Boolean` 타입 멤버가 아닐 때 발생한다. 참조가 멤버를 가리키지 못하거나 다른 설비의 멤버를 가리킬 때도 발생한다. 아울러 하나의 `mappingId`가 두 역할을 맡는 경우, 곧 활동 멤버이면서 동시에 식별 멤버로 쓰이거나 두 개 이상의 식별 참조에 동시에 지정될 때도 이 코드로 거부한다.
- `attribution.identity-equipment`: `plc-stamped` 모드에서 식별 항목들이 설비들을 일대일로 온전히 포괄하지 못할 때 나온다. 활동 멤버나 측정 멤버가 하나라도 지정된 설비는 반드시 단 하나의 식별 항목과 짝을 이루어야 한다. 필요한 설비 항목이 빠졌거나, 동일한 설비 항목이 둘 이상 중복되었거나, 활동 멤버와 측정 멤버가 둘 다 없는 설비에 식별 항목을 지정했을 때 이 코드가 나온다.
- `attribution.temporal-order`: 시간 순서 제약 조건 부등식이 어긋날 때 나온다. 시간 매개변수 사이에 `outOfOrdernessMs ≤ allowedLatenessMs ≤ horizonMs` 관계가 반드시 성립해야 하며, 이 순서가 무너지면 검사에서 거부한다.

단일 역할 규칙(One-role rule)을 엄격하게 적용한다. `members[]`의 각 항목은 오직 하나의 역할만 맡는다. `activity[].memberRef`에 지정된 항목은 활동 멤버가 되고, `plc-stamped` 식별 항목에 지정된 항목은 식별 멤버가 되며, 그 밖의 모든 항목은 측정 멤버가 된다. 하나의 멤버 항목이 여러 역할을 겸하거나 모호하게 쓰이는 구성은 일절 허용하지 않는다.

영향 규칙 검사에서 쓰이는 다섯 개 `impact.*` 거부 코드와 판정 기준은 다음과 같다.

- `impact.attribution-missing`: `attributionRuleRef`가 가리키는 귀속 규칙 문서가 동일한 패키지 안에 없을 때 나온다.
- `impact.scope-containment`: `incidentScope`에 적힌 경로가 설비 계층 노드가 아니거나, 귀속 규칙에 명시된 스테이션 또는 그 스테이션 하위 설비가 아닐 때 나온다.
- `impact.binding-unresolved`: `incidentBindingRef`가 패키지 안에 든 evidence-artifact 1.1.0 문서를 가리키지 못할 때 나온다.
- `impact.binding-profile`: 인시던트 프로필 내용이 사양에 맞지 않을 때 나온다. 접두사, 미디어 타입, 필수 필드 구성이 틀렸거나 바이트 형식이 손상되어 온전히 읽어 들이지 못할 때 나타난다.
- `impact.retention-order`: 보존 기간 순서가 어긋났을 때 나온다. 귀속 규칙의 `horizonMs` 값이 영향 규칙의 `retention.workRecordsMs` 값보다 크면 이 코드로 거부한다.

`rule.envelope` 거부 코드는 2.27.0 제안서 밖에서 2.27.0 문서가 나타날 때 부여된다.

귀속 검사와 영향 검사는 순차로 이어진다. 따라서 패키지 하나에 `attribution.*` 지적과 `impact.*` 지적이 함께 담길 수 있다. 반면 Bifrost는 번들을 검증할 때 첫 번째 실패 지점에서 즉시 멈추고 거부 코드 하나만 보고한다. 양쪽 검증기가 기대하는 거부 코드는 서로 완전히 같다.

작업공간 수준에서는 Tyr 자체 검사 코드를 쓴다. 귀속 규칙이 64개를 넘으면 `attribution-rule.limit`, 스키마 검증이 실패하면 `attribution-rule: schema validation failed`(Tyr는 2.27.0 규칙만 작성한다), 식별자가 중복되면 `attribution-rule: duplicate id`를 낸다. 영향 규칙에도 같은 기준으로 `impact-rule.limit`, `impact-rule: schema validation failed`, `impact-rule: duplicate id` 세 코드를 쓴다.

Tyr는 다음을 Bifrost에 맡긴다. 2키 영수증 승인, in-toto/DSSE 증명(attestation), 릴리스 파일 생성과 헤드 서명, 활성화 정책 관리, 제출 컨텍스트 검사는 모두 Bifrost가 도맡는다. 아울러 `binding.schema-mismatch` 여부와 인시던트 스키마가 각 종류를 온전히 뒷받침하는지 따지는 판단은 forseti에 맡긴다.

## 발행

패키지 빌더는 작성된 규칙을 `attribution-rules/<n>.json` 및 `impact-rules/<n>.json` 경로에 쓴다. 규칙이 있으면 제안서 버전을 2.27.0으로 지정하며, 규칙 없이 2.27.0 소스만 있어도 2.27.0으로 맞춘다.

발행 범위(`backend/publication.py`)는 다음 조건으로 정한다. 귀속 규칙은 소속 멤버가 읽어 들이는 모든 매핑 세트가 발행 대상으로 함께 선택되었을 때만 발행에 들어간다. 필요한 매핑 세트가 하나라도 빠지면 귀속 규칙은 발행 목록에서 제외된다. 영향 규칙은 자신이 가리키는 귀속 규칙과 항상 함께 묶여 발행된다. 가리키는 귀속 규칙이 발행되지 않으면 영향 규칙도 함께 빠진다. 프로필 문서는 각 규칙의 참조 관계(`occupancyBindingRef`, `incidentBindingRef`)를 따라 패키지에 들어온다. 설비 계층 구조는 매핑 세트나 규칙 선택 여부와 관계없이 언제나 패키지 발행 목록에 들어간다.

테스트 픽스처는 `line2` 스트림을 발행한다. 저장소에 커밋되어 관리되는 번들인 `fixtures/attribution-rule/bundle/`(39개 파일)과 `fixtures/attribution-rule/plc-stamped-bundle/`(59개 파일)은 두 픽스처 작업공간(`workspace.json`, `plc-stamped-workspace.json`)을 빌드한 결과물이다. 시험 단계에서는 이들 작업공간을 다시 빌드한 뒤 기존 파일과 바이트 단위로 대조하여 내용이 완전히 일치하는지 확인한다.

## 작성 화면

연결 단계 안에는 "귀속·영향 규칙" 탭이 마련되어 있다. 백엔드 API 라우트는 `GET /api/attribution-rule`, `POST /api/attribution-rule-plan`, `POST /api/attribution-rule-apply` 세 갈래로 나뉜다.

화면 목록에는 규칙에서 지정할 수 있는 멤버 목록(매핑 세트, `mappingId`, 설비 경로, metric, `semanticId`, 데이터 타입), 설비 계층 구조 트리, 인용 가능한 evidence 문서 목록을 빠짐없이 표시한다. 사용자가 편집하는 현재 프로필과 규칙은 JSON 블록 형태로 화면에 나타나며, 직접 수정할 수 있다.

`POST /api/attribution-rule-plan`은 편집된 블록에 패키지 검증과 동일한 검사를 실행하고 요청의 리비전과 네 섹션의 다이제스트인 `planSha256`과 함께 결과를 반환한다. `POST /api/attribution-rule-apply`는 요청에 `planSha256`을 요구하며, 빠져 있으면 `attribution-rule.plan-required`로 거부하고 계획 이후 블록이 변경되어 수신한 요청의 다이제스트와 일치하지 않으면 `attribution-rule.plan-changed`로 거부한다. 저장 자체가 전체 작업공간 검사(및 버전 전이)를 다시 실행하므로 검사를 통과하지 못한 작업공간을 결코 저장하지 않으며, 형식이 잘못된 요청은 `attribution-rule.plan-request`로 거부한다.

작업공간에 규칙을 저장하는 일은 작성 행위일 뿐이며 승인 권한은 Bifrost에 머무른다. 목록 응답(`GET /api/attribution-rule`)에는 `approvalAuthority: bifrost` 필드가 담겨 승인 권한이 Bifrost에 있음을 명확하게 알린다.

## Bifrost와의 경계

Tyr와 Bifrost 사이에는 공유 코드가 전혀 없다. Tyr는 Bifrost나 forseti의 코드를 단 한 줄도 임포트하지 않는다. Bifrost의 `AttributionRules`, `ImpactRules`, `OccupancyBindingProfile`, `IncidentBindingProfile` 검증기는 Tyr와 완전히 동일한 스키마 바이트를 읽어 들여 독립으로 유효성을 검증한다.

완료 관문은 Bifrost의 `gates mapping approve` 명령이다. 커밋된 두 번들 모두 로컬 환경과 Tyr CI에서 승인되어 `line2` 스트림의 승인 영수증과 DSSE 증명을 받는다. CI 작업에서는 인접 체크아웃 디렉터리에서 Bifrost gates jar 파일을 직접 빌드하여 이 관문을 실행한다.

패리티 매트릭스는 거부 코드별로 번들을 하나씩 변형하여 만든 26개 행으로 구성된다. 각 행마다 Bifrost의 jar(`mapping validate`)가 지정된 바로 그 거부 코드로 거부하는지 확인하고, Tyr 또한 동일한 코드를 보고하는지 대조한다.

매트릭스에는 다음 검증 항목이 포함된다.
- 두 프로필 모두에서 나타나는 JSON 키 중복 검사
- 두 프로필 모두에서 10,000단계 깊이로 이어지는 중첩 구조 검사
- 정수 반복 한계값 검사: Java `int` 최대 범위를 넘어서는 한계값, `2^32` 초과 한계값, `long` 범위를 넘어서는 한계값 검사

아울러 양쪽이 완전히 동일하게 판단하는 경계 사례들을 함께 검증한다. Tyr가 발행한 번들을 2.26.0 제안서로 낮추었을 때 양쪽 검증기가 모두 `rule.envelope` 코드로 거부한다. 또한 양쪽이 모두 정상으로 받아들이는 네 허용 사례를 검증한다.
- 반복 한계값이 정확히 `2147483647`인 경우
- 반복 한계값 앞자리에 0이 4,500개 붙어 표기된 경우
- 두 프로필 파일 앞에 각각 UTF-8 BOM 바이트가 붙어 있는 두 경우

Bifrost 자체의 1단계 픽스처(`attribution-impact`, `attribution-plc-stamped`)는 동일한 두 형태를 직접 손으로 작성한 데이터이다. Tyr가 빌드한 번들 사본을 Bifrost 쪽에 들여놓는 작업은 후속 과제로 남겨둔다.

## 시험

`scripts/test_attribution_rule.py` 파일에는 총 102개의 시험이 들어 있다.
- `Contract`: 2개 시험
- `StringSource`: 7개 시험
- `OccupancyProfile`: 10개 시험
- `Pattern`: 7개 시험
- `BindingProfiles`: 4개 시험
- `AttributionRule`: 39개 시험
- `Publication`: 5개 시험
- `PlcStamped`: 18개 시험
- `Parity`: 2개 시험
- `Approval`: 3개 시험
- `Authoring`: 5개 시험

`scripts/test_impact_rule.py` 파일에는 총 23개의 시험이 들어 있다.
- `IncidentProfile`: 9개 시험
- `ImpactRule`: 14개 시험

각 시험 클래스가 입증하는 핵심 내용은 다음과 같다.
- `Contract`: 스키마 바이트 복사본이 원본과 정확히 일치함을 입증한다.
- `StringSource`: 타입이 지정된 String 소스와 입력 폼 구조가 올바름을 입증한다.
- `OccupancyProfile`, `IncidentProfile`, `Pattern`: 프로필 파서들과 정규식 패턴 서브셋 파싱 기능이 정확함을 입증한다.
- `BindingProfiles`: evidence artifact 형식으로 작성된 프로필 문서가 올바르게 구성됨을 입증한다.
- `AttributionRule`, `ImpactRule`: 사양에 정의된 모든 거부 코드가 각 조건에서 빠짐없이 발생함을 입증한다.
- `Publication`: 발행 범위 규칙과, 커밋된 번들이 작업공간의 빌드 결과와 같음을 입증한다.
- `PlcStamped`: 식별 검사 조건들과 두 번째 커밋 번들의 구조를 입증한다.
- `Parity`: Bifrost jar 매트릭스와 Tyr 검증 결과가 26개 행에서 완전히 일치함을 입증한다.
- `Approval`: Bifrost 승인 게이트 연동을 거쳐 승인 영수증이 온전히 발급됨을 입증한다.
- `Authoring`: 작성 화면 API의 목록·계획·저장 절차를 입증한다.

결함 주입(Fault injection) 시험 8건을 직접 실행하고 실패한 시험 수를 기록했다.

| 번호 | 결함 주입 내용 | 실패한 시험 내역 |
|---|---|---|
| 1 | `publication.py`에서 귀속 규칙 발행 범위 줄 제거 | `Publication` 시험 2개 실패 (모듈 전체에서는 `PlcStamped` 번들 시험을 포함하여 총 3개 시험 실패) |
| 2 | `rule.envelope` 거부 로직 비활성화 | `StringSource.test_a_2_27_source_needs_a_2_27_proposal` 및 Parity envelope 시험 2개 실패 |
| 3 | `plc-stamped` 식별 블록 제거 | `PlcStamped` 시험 10개와 패리티 행 2개(`identity-member`, `identity-equipment`) 실패 |
| 4 | `quantifier()`의 한계값 검사 제거 | `Pattern.test_quantifier_bounds_follow_java` 시험과 패리티 행 `binding-profile-bound-above-int` 실패 (`2^32` 초과 및 `long` 초과 행은 파이썬 컴파일 시점의 `OverflowError`로 계속 거부) |
| 5 | 중복 키 훅(`object_pairs_hook=vc.pairs`) 제거 | 중복 키 단위 시험 2개와 패리티 행 2개 실패 |
| 6 | 파서의 예외 절에서 `RecursionError` 처리 제거 | 깊은 중첩 단위 시험 2개와 패리티 행 2개가 거부 대신 비정상 종료(크래시)로 끝남 |
| 7 | 바이트 입력 대신 `raw.decode('utf-8')` 파싱 | BOM 단위 시험 2개와 BOM 허용 사례 2개 실패 |
| 8 | 선행 0 제거 로직 제외 | `Pattern.test_leading_zeros_are_javas_value` 시험과 4,500개 선행 0 허용 사례 실패 |
