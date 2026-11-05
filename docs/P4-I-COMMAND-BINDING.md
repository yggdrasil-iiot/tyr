# P4-I 명령 링크(command binding)

## 범위
`command-binding`은 거버넌스된 멤버 하나의 read binding에서 같은 설비의 OPC UA Method 하나로 이어지는 링크이다. Tyr는 링크를 작성하며, 승인 권한은 Bifrost(기존 2키 매핑 릴리스)에 머무른다. Tyr에는 승인 권한이 없다.

read binding은 Vor read-binding 프로필 버전 `0.1.0`이다. Tyr는 이 프로필을 작성하거나 편집하지 않는다. 프로필 바이트는 데이터 에지 시운전 시점에 생성되어 변경 없이 Tyr로 들어오며, 일반 `evidence-artifact`(`schemaVersion` `1.1.0`)로 보관된다. 프로필의 12개 필드 가운데 4개는 Tyr 모델에 없는 데이터 에지 배포 사실이다. 즉 `group`과 `edge`(Muninn이 명령줄 인수로 받음), `governedDefinitionRef`(Muninn이 검증하는 거버넌스 정의)이며, `streamId`는 내보내기 시점에만 확정된다. Tyr에 이 필드들의 입력 양식을 두면 뒤 단계의 어떤 구성요소도 비교하지 않는 배포 사실의 두 번째 수기 복사본이 될 뿐이다.

시운전 시점에 프로필을 생성하는 작업(예: Muninn 이용)은 별도의 후속 단계이다. 그때까지는 작업자가 프로필을 직접 준비하여 가져오며, 현재 픽스처 프로필은 합성(synthetic) 데이터이다.

Tyr는 자체 문서에서 도출할 수 있는 모든 프로필 필드를 대조하여 불일치 시 거절하며, `group`, `edge`, `governedDefinitionRef`는 주어진 값 그대로 받아들인다. 현재 어떤 구성요소도 `governedDefinitionRef`와 배포된 정의를 비교하지 않는다. Bifrost가 승인 시점에 이를 검증할지, 사양에서 미검증으로 선언할지는 별도로 결정한다.

## 계약 2.25.0
Bifrost에서 바이트 단위로 동일하게 `contracts/2.25.0/` 디렉터리로 복사한 계약을 사용한다.
- `command-binding.schema.json`: 새 종류 `command-binding`을 정의한다. 필드는 `kind`, `schemaVersion`(`2.25.0`), `id`, `version`, `equipmentRef`(설비 계층의 `id`, `version`, `equipmentInstanceId`), `readBindingRef`(read binding의 evidence-artifact `id`, `version`), `command`(Sparkplug 명령 노드의 `group`, `edge`), `method`(`objectNodeId`, `nsu=<uri>;s=<id>` 형식의 `methodNodeId`, `{name, type, unit}` 목록인 `inputs`), `evidenceRefs`이다.
- `common.schema.json`: `$id`를 갱신하고 파일 항목 종류 enum에 `command-binding`을 추가한 2.24.0 사본이다. 다른 변경 사항은 없으며 시험에서 이를 확인한다.
- `mapping-proposal.schema.json`: `$id`와 `schemaVersion` 상수를 2.25.0으로 설정한 2.24.0 사본이다.

링크에는 Method 시그니처(입력 이름, 타입, 단위)가 포함된다. 허용 범위(최솟값, 최댓값)는 각 에지의 명령 정책(command policy)에 남는다.

## 계약 2.26.0과 서버 인증서

계약 2.26.0은 Bifrost에서 바이트 단위로 그대로 `contracts/2.26.0/`(`command-binding`, `common`, `mapping-proposal`)에 복사된다. `common`과 `mapping-proposal`은 버전 문자열만 2.25.0과 다르다. `command-binding`에는 필수 필드인 `endpointRef: {applicationUri, certificates: [{thumbprintSha1, certificateRef: {id, version}}]}`가 추가된다. `thumbprintSha1`은 인증서 DER의 SHA-1 값인 소문자 16진수 40자리이며, `certificates` 목록은 1개에서 8개 항목을 담는다. 후임 인증서를 추가하고 전임 인증서를 제거하는 릴리스를 거쳐 겹침 구간을 두는 서버 인증서 교체가 이 목록으로 허용된다. Bifrost와 Heimdall은 명령 시점에 `endpointRef`가 없는 모든 링크(모든 2.25.0 링크)를 `command.link.endpoint`(`missing`)로 거절한다. Tyr는 2.26.0 링크만 작성한다. 작업공간에서 `schemaVersion`이 `2.26.0`이 아니거나 2.26.0 스키마 검증에 실패한(예: `endpointRef` 누락) `commandBindings` 항목은 거절된다(`command-binding: schema validation failed`). 패키지 빌더는 링크가 있으면 제안서 `schemaVersion`을 2.26.0으로 설정한다(이전에는 2.25.0이었다).

서버 인증서 가져오기에서는 작업공간 키 `serverCertificates`에 최대 256개 레코드를 보관한다. 편집기 스키마는 `editor-contracts/1.0.0/server-certificate-import.schema.json`이며, `id`, `version`, `label`, `bytesBase64`, `sha256`, `origin`(`synthetic` 또는 `field`), `capturedAt`, `reviewer`, `product`, `scope`(서버가 담당하는 설비인 1~256개의 고유 설비 ID) 필드가 정의되어 있다. 인증서는 최대 16 KiB 크기의 DER로 저장된다. `backend/server_certificates.py`에서 다음 항목을 검사한다:
- 스키마 형식(`server-certificate.schema`)
- 중복 `id`(`server-certificate.duplicate`)
- Base64(`server-certificate.bytes`)
- 크기 한도(`server-certificate.limit`)
- 바이트의 SHA-256(`server-certificate.digest`)
- DER 형식의 정확히 단 하나의 X.509 인증서 바이트(`server-certificate.der`)
- 정확히 단 하나의 subjectAltName URI(없거나 둘 이상이면 거절)(`server-certificate.san-uri`)
- 작업공간 설비와 일치하는 모든 `scope` 항목(`server-certificate.equipment`)
- 변경된 기존 레코드의 새 버전 요구(`server-certificate.version-required`)

파싱에는 `cffi`, `pycparser`와 함께 `requirements-contracts.txt`에 추가된 `cryptography` 패키지와 Tyr 자체 코드인 `scripts/server_certificate.py`를 사용한다. 여기서 DER의 SHA-1 지문(소문자 16진수)과 단 하나의 subjectAltName URI를 도출한다. 이 값은 Bifrost가 발행 시점에 다시 도출하고 Heimdall이 실제 OPC UA 세션과 대조하는 값이다. DER은 다시 인코딩되지 않으며, 바이트는 인증서 자체의 DER 인코딩과 같아야 한다.

가져오기 단계인 `POST /api/server-certificate-import`는 선택한 파일(DER 또는 PEM)의 `{bytesBase64}`를 받는다. PEM은 정확히 단 하나의 `CERTIFICATE` 블록만 받아들이며, base64 본문을 DER로 디코딩한다(블록이 둘이거나, 다른 블록 타입이거나, DER 뒤에 남은 바이트가 있으면 `server-certificate.der`로 거절한다). 이 요청은 DER(`bytesBase64`), `sha256`, `thumbprintSha1`, `applicationUri`를 반환하며 아무것도 저장하지 않는다.

패키지 빌더는 DER을 변경 없이 그대로 `data/server-certificate-<n>.der`에 작성하고 `evidence/server-certificate-<n>.json`(evidence-artifact `schemaVersion` `1.1.0`, `id` = `server-certificate-` + 레코드 `id`, 미디어 타입 `application/pkix-cert`, `scope` = 레코드의 `scope`)으로 감싼다.

## read binding 가져오기
작업공간 키 `readBindings`에 최대 256개 레코드를 허용한다. 편집기 스키마 `editor-contracts/1.0.0/read-binding-import.schema.json`에는 `id`, `version`, `label`, `bytesBase64`, `sha256`, `origin`(`synthetic` 또는 `field`), `capturedAt`, `reviewer`, `product` 필드가 정의되어 있다. 프로필 바이트 크기는 최대 64 KiB이다.

`backend/read_bindings.py`는 다음 검사를 적용한다.
- 스키마 형식(`read-binding.schema`)
- 중복 `id`(`read-binding.duplicate`)
- Base64 인코딩(`read-binding.bytes`)
- 바이트 크기 한도(`read-binding.limit`)
- 바이트의 SHA-256(`read-binding.digest`)
- 바이트의 프로필 0.1.0 파싱 여부(`read-binding.profile`)
- 프로필의 `equipmentInstanceId`가 작업공간 설비인지 여부(`read-binding.equipment`)
- 기존 레코드 변경 시 새 버전 지정 필수(`read-binding.version-required`)

패키지 빌더는 가져온 바이트를 그대로 `data/read-binding-<n>.json`에 작성하고 `evidence/read-binding-<n>.json`으로 감싼다. 이때 `id`는 `read-binding-` 뒤에 레코드 `id`를 붙인 값이고, 미디어 타입은 `application/json`이며, 범위(scope)는 프로필의 `equipmentInstanceId`이다. Vor와 Bifrost가 고정(pin)하는 해시는 가져온 바이트의 해시이며, 어떤 구성요소도 바이트를 다시 직렬화하지 않는다.

프로필 0.1.0은 Tyr 자체 코드(`scripts/command_binding.py`)로 파싱한다. 필드는 정확히 `profileVersion`, `streamId`, `mappingSetRef`, `mappingId`, `equipmentInstanceId`, `semanticId`, `group`, `edge`, `device`, `metric`, `governedDefinitionRef`, `projection`의 12개이며, `projection` 값은 반드시 `identity`여야 한다.

## Tyr 검사
Tyr는 `scripts/command_binding.py`에 검사 규칙을 구현하며, 규칙을 위반한 산출물에는 다음 거절 코드를 반환한다. 패키지 검사기(`p3a_contracts.validate_package`)가 이 규칙을 실행하므로 작업공간 검사와 패키지 단독 검증에 동일한 규칙을 온전히 적용한다.

가져온 각 프로필과 패키지의 대조 규칙(Vor가 읽을 때 적용하는 규칙과 동일):
- `command-binding.unresolved`: 매핑 세트(`mappingSetRef`)나 매핑(`mappingId`)이 패키지에 없거나, 링크가 지정한 프로필을 0.1.0으로 읽을 수 없을 때 반환한다.
- `command-binding.device-path`: 매핑 세트의 설비가 프로필의 `equipmentInstanceId`와 다르거나, `device`가 설비의 ISA-95 계층 경로(루트부터 `:`로 연결한 문자열이며 Muninn이 발행하는 Sparkplug 디바이스 id)와 일치하지 않을 때 반환한다.
- `read-binding.member-path`: 매핑이 정확히 하나의 시맨틱 멤버를 작성하지 않을 때 반환한다.
- `read-binding.target-equipment`: 매핑 세트의 타깃 인스턴스가 다른 설비에 속할 때 반환한다.
- `read-binding.semantic-id`: `semanticId`가 멤버의 `semanticId`와 다를 때 반환한다.
- `read-binding.metric`: `metric`이 멤버의 `name`과 다를 때 반환한다.
- `read-binding.source-node`: 매핑 소스가 OPC UA 노드가 아니거나 그 식별자가 `.` + `metric`으로 끝나지 않을 때 반환한다 (Muninn은 노드 식별자의 마지막 세그먼트로 메트릭 이름을 지정한다).
- `read-binding.output-unit`: 매핑 출력 단위가 멤버의 단위와 다를 때 반환한다.

링크 자체 검사 규칙(Bifrost 발행 검사 코드와 동일):
- `command-binding.unresolved`: 계층, read binding의 evidence-artifact(`schemaVersion` `1.1.0`), 설비 노드를 찾을 수 없을 때 반환한다.
- `command-binding.device-path`: 프로필의 설비가 링크의 설비와 다르거나, 프로필의 `device`가 링크 설비의 계층 경로와 다를 때 반환한다.
- `command-binding.inputs`: `inputs`가 비어 있지 않은 이름, `Double` 타입, 링크 자체의 계약 버전 공통 스키마에 나열된 UCUM 코드가 있는 단 하나의 입력이 아닐 때 반환한다.
- `command-binding.endpoint`: 나열된 `certificateRef`가 `schemaVersion` `1.1.0`, id 접두사 `server-certificate-`, 미디어 타입 `application/pkix-cert`인 evidence-artifact로 확인되지 않거나, 파일 파싱에 실패하거나, SHA-1이 `thumbprintSha1`과 일치하지 않거나, subjectAltName URI가 링크의 `applicationUri`와 일치하지 않거나, 인증서가 중복으로 나열되었을 때 반환한다.
- `command-binding.envelope`: `schemaVersion`이 `2.26.0`이 아닌 제안서에 2.26.0 문서가 포함되었을 때 반환한다.
- `command-binding.duplicate`: 두 링크가 read binding의 `device`와 `methodNodeId`를 공유할 때 반환한다.

작업공간 검사 단계에서는 스키마 형식 오류와 중복된 링크 `id`도 차단한다.

## 발행
작업공간 키 `commandBindings`에 최대 256개 링크를 허용한다. 빌더는 `command-bindings/<n>.json`을 작성하고 제안서 `schemaVersion`을 2.26.0으로 설정한다. 링크가 없는 패키지는 이전 버전을 유지한다.

링크는 read binding이 읽는 매핑 세트와 함께만 발행된다. 이때 `readBindingRef`를 따라 read binding의 evidence-artifact와 데이터 파일이 제출물에 함께 실린다. `readBindingRef`와 마찬가지로, `certificateRef`를 따라 지정된 각 서버 인증서 산출물과 DER 파일이 제출물에 함께 실린다.

내보내기 단계에서 발행 대상 프로필의 `streamId`가 내보내기 스트림과 다르면 `read-binding.stream` 코드로 거절한다. 아무 파일도 작성하지 않으며 가져온 바이트는 그대로 유지된다. 다른 스트림에는 시운전에서 새로 만든 프로필을 가져와야 한다.

2.24.0 제안서는 새 종류를 나열할 수 없어 스키마 검증에 실패한다. 2.26.0 링크를 담은 2.25.0 제안서는 `command-binding.envelope`로 거절된다. 2.21 레코드 필드 검사와 2.22 브로드캐스트 봉투 검사는 2.25.0과 2.26.0을 받아들인다.

## 작성 화면
Tyr의 연결 단계에는 명령 링크 화면(프런트엔드 `frontend/command-binding.js`, 백엔드 `backend/command_binding_authoring.py`)이 있다. 승인은 Bifrost가 한다.
API로는 목록을 조회하는 `GET /api/command-binding`, 요청을 검증하는 `POST /api/command-binding-plan`, 저장을 처리하는 `POST /api/command-binding-apply`가 있다.

- plan과 apply에는 작업공간 리비전을 담으며, 오래된 리비전은 충돌로 거절하고 검증된 plan과 다른 요청은 `command-binding.plan-changed`로 저장을 거절한다.
- 목록에는 가져온 read binding마다 evidence-artifact `id`(`read-binding-` + 레코드 `id`), 버전, 출처, 검토자, 바이트에서 디코딩한 프로필 텍스트, SHA-256, 작업공간 대조 결과(`ok` 또는 거절 코드)를 표시한다.
- 링크, 설비 계층구조와 설비, 2.26.0 공통 스키마의 UCUM 단위, 링크가 인용할 수 있는 근거 자료 목록도 함께 표시한다.
- 프로필 가져오기는 선택한 `.json` 파일(최대 64 KiB)을 읽어 바이트와 SHA-256을 원본 그대로 저장하며, 기존 레코드를 바꿀 때는 새 버전이 필요하다.
- 각 링크에서 운영자는 read binding과 별개로 Method가 속한 설비를 선택하며, 프로필의 설비와 다르면 `command-binding.device-path`로 검증을 거절한다.
- 계층 참조는 작업공간의 설비 계층에서 채우고 입력 형식은 `Double`이며, 허용 범위(최솟값, 최댓값)는 각 에지의 명령 정책에 둔다.
- 작성 화면(`frontend/command-binding.js`, `backend/command_binding_authoring.py`)의 계획(plan) 및 적용(apply) 요청에는 `readBindings`, `commandBindings`와 함께 `serverCertificates`가 실린다. 목록에는 각 인증서의 `evidence-artifact` `id`(`server-certificate-` + 레코드 `id`), 버전, 출처, 검토자, 범위(`scope`), DER SHA-256과 도출된 `applicationUri` 및 SHA-1 지문(`thumbprintSha1`)이 표시된다.
- 인증서 가져오기는 가져오기 단계에서 DER 또는 PEM 파일을 읽어 도출된 값을 표시한다.
- 각 링크에는 가져온 인증서를 하나 이상(교체 중에는 둘) 지정한다. 지정한 인증서 값으로 `applicationUri`와 `thumbprintSha1`을 채우며, 검증 시점에 DER 바이트와 다시 대조한다.

## Bifrost와의 경계
두 시스템 사이에 공유 코드는 없다. Bifrost는 2.25.0·2.26.0 스키마의 바이트 단위 동일 사본과 자체 구현체(`CommandBindings`, `ReadBindingProfile`, `ServerCertificates`)를 유지하며 동일한 번들을 독립 검증한다. 명령 시점에 `gates command approve`와 Heimdall이 발행된 릴리스에서 링크를 확인한다.

## 시험
`scripts/test_command_binding.py`에는 52개 시험(`CommandBinding` 32개, `Endpoint` 15개, `Authoring` 5개)이 있다. 픽스처 작업공간에는 설비 `synthetic-site`, `line1`, `mixer1`, `mixer2`, 믹서당 하나의 OPC UA 소스, 타깃, 매핑 세트, ISA-95 계층, 변경 없는 Bifrost의 `vor-read` 픽스처 프로필 바이트를 가져온 두 read binding, 두 링크(`mixer1-set-temperature`, `mixer2-set-temperature`)가 있다. 여기에 서버 인증서 `sim`(Bifrost의 `vor-read` 픽스처 `server-certificate-sim.der`의 DER 바이트, SAN URI `urn:bifrost:opcua:sim-server`, 범위 `line1`)을 추가하였으며 두 링크에 모두 이 인증서를 지정한다.

`fixtures/command-binding/bundle/`은 스트림 `line1`용으로 빌드한 발행 산출물이다. 한 시험에서는 작업공간에서 번들을 다시 빌드하여 바이트를 대조한다. 다른 시험에서는 번들을 Bifrost의 사본(`core/src/test/resources/mapping-fixtures/command-binding`, Bifrost의 `MappingTyrCommandBindingTest`가 실행)과 바이트 단위로 대조하고 Bifrost의 `gates mapping validate`를 실행한다. 바이트 일치 시험에서는 탭으로 들여쓴 프로필을 가져와 동일한 바이트와 해시로 패키징하는지 확인한다.

모든 거절 코드마다 전용 시험이 있다. 새 시험에서는 픽스처 인증서가 Bifrost의 바이트와 일치하며 링크 값을 도출하는지, DER을 변경하지 않고 `application/pkix-cert`로 패키징하는지, DER과 PEM 가져오기가 동일한 DER을 생성하는지 확인한다. 또한 가져오기 거절(PEM 블록 2개, 인증서가 아닌 바이트, 뒤따르는 바이트, 잘못된 PEM 블록 유형, SAN URI 없음, SAN URI 2개, 크기 초과)과 모든 `server-certificate.*` 코드의 작업공간 거절을 확인한다. `endpointRef`가 없거나 2.25.0 버전인 링크는 작성하지 않는다. 잘못된 지문, 잘못된 `applicationUri`, 알 수 없는 인증서, 두 번 나열된 인증서, 다른 서버의 인증서, 서버 인증서가 아닌 산출물 참조에는 `command-binding.endpoint` 거절을 확인한다. 한 서버의 인증서 둘이 겹치는 교체 중첩은 받아들여 발행한다. 바뀐 DER은 패키지 검사만으로 거절한다. 2.26.0 스키마가 2.25.0 스키마와 오직 `endpointRef`로만 다른 점과, 2.26.0 링크를 담은 2.25.0 제안서를 `command-binding.envelope`로 거절하는 점도 검증한다. 시험용 인증서는 시험 안에서 `cryptography`로 생성한다.

`Authoring` 클래스의 5개 시험에서는 목록(프로필 텍스트, SHA-256, `ok` 대조 결과와 각 인증서에서 도출한 지문, `applicationUri`, 범위), `device`가 대조되지 않는 프로필의 계획 거절(`command-binding.device-path`), 적용 저장 및 비우기(`serverCertificates` 포함), 오래된 리비전, 계획 후 변경된 요청(`command-binding.plan-changed`), 버전 없는 프로필 변경(`read-binding.version-required`) 및 버전 없는 인증서 변경(`server-certificate.version-required`), 가져오기 단계를 포함한 HTTP 경로를 검사한다.

이전 결함 주입에서는 대조를 제거하면 7개 시험이 실패하고, 다시 직렬화하는 작성기는 바이트 일치 시험에서 실패하며(픽스처 프로필 자체는 직렬화기 형식과 일치하므로 단독으로는 차이를 드러내지 못한다), 스트림 검사를 제거하면 스트림 시험이 실패한다. 계획의 버전 규칙을 제거하면 버전 변경을 검사하는 마지막 시험이 실패한다. 수동으로 진행한 결함 주입에서는 엔드포인트 검사를 제거하면 7개 시험이 실패하고, 봉투 규칙을 제거하면 봉투 시험이 실패한다.
