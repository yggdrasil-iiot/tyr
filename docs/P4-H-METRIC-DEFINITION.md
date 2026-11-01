# P4-H 파생 지표 정의

## 범위
Tyr는 승인을 마친 단일 레코드 매핑 산출물을 바탕으로 단일 파생 지표를 작성한다. 지표 승인 권한은 Bifrost에 두며, Bifrost는 기존에 마련된 두 키 매핑 릴리스 절차로 승인을 확정한다. Tyr 자체에는 승인 권한을 두지 않는다.

하류 엔진이 실행된 계산이 승인된 정의와 일치함을 증명했을 때에만 결과 열에 파생 지표의 의미 핀을 부여한다. 이 문서에서는 파생 지표 작성 계약과 Tyr의 검사 규칙을 규정한다. 하류 증명 작업은 별도 작업으로 분리한다.

파생 지표는 Tyr 독자 규격 대신 오픈 표준인 Apache Ossie(인큐베이팅 단계, 이전 명칭 Open Semantic Interchange, OSI, 라이선스 Apache-2.0, 저장소 `apache/ossie`) 형식으로 작성한다. 핵심 명세 버전은 DRAFT 상태인 `0.2.0.dev0`이다. 업스트림 커밋 `48da55a07e4e8c3a11a662b14727557f6342536d`의 다음 세 파일을 기준으로 삼는다.
- `core-spec/spec.md`: SHA-256 해시값 `a28fafb4fb1755ee3b942f419ea47cbd35a7e1e021e05b1b174b2db43bc54ef3`
- `core-spec/spec.yaml`: SHA-256 해시값 `0ebe54e7981e62abea3478b5fc27d96162dd499be8bbded3d2e6069e817486e1`
- `core-spec/expression_language.md`: SHA-256 해시값 `36847784351f70402a13a65b15a496c351765b7b94d785d16aaf6bd863b591ff`

이후 판 Ossie 규격은 새로운 계약 버전을 정의하여 반영한다.

설계 결정은 다음과 같다.
- 시간 윈도는 `grain.groupBy`에 명시하는 레코드 매핑의 사전 버킷화 문자열 키(예: `bucket`)로 지정한다. 계약에 타임스탬프 값 유형이 정의되지 않았고 Ossie 지표 수준 명세에도 윈도 필드가 없기 때문이다. 윈도 경계(시작 시각과 종료 시각)를 검증하는 작업은 본 계약 범위 밖으로 둔다.
- 단일 지표는 단일 레코드 매핑(단일 데이터셋)만을 읽는다. 여러 데이터셋을 넘나드는 지표는 본 계약 범위 밖으로 둔다.
- 유료 표준이면서 공개 URI 네임스페이스가 없는 ISO 22400 KPI 번호는 식별자로 쓰지 않는다. `semanticId`에는 프로젝트 자체 URI(예: `urn:yggdrasil:metric:running-availability`)를 부여한다.

## 계약 2.24.0
새로운 전역 계약 버전 디렉터리 `contracts/2.24.0/`에 다음 세 파일을 정의한다.
- `metric-definition.schema.json`: 새 kind `metric-definition`을 선언한다.
- `common.schema.json`: 2.23.0 판 사본에서 `$id`를 갱신하고, 파일 항목 kind 열거형 끝에 `metric-definition`을 추가하며, 단위 코드 목록 끝에 UCUM 단위 코드 `%`를 추가한다.
- `mapping-proposal.schema.json`: 2.23.0 판 사본에서 `$id`와 `schemaVersion` 상수를 2.24.0으로 갱신한다.

모든 필드는 필수이며, 추가 속성은 허용하지 않고 차단한다. 스키마에 정의된 필드는 다음과 같다.
- `kind`: 문자열 상수 `metric-definition`이다.
- `schemaVersion`: 문자열 상수 "2.24.0"이다.
- `id`: 지표 식별자다.
- `version`: 지표 버전이다.
- `label`: 사람이 읽는 지표 이름이다.
- `semanticId`: URI 형식으로 작성하는 의미 식별자다.
- `description`: 지표 설명이다.
- `dataset.recordMappingRef`: 참조 대상 레코드 매핑의 id와 version이다.
- `inputs`: 1개 이상 32개 이하의 고유한 필드 id 목록이다. 일반 SQL 식별자로 쓰이도록 정규 표현식 패턴 `^[a-z][a-z0-9_]{0,63}$`을 강제한다.
- `grain.groupBy`: 0개 이상 4개 이하의 고유한 필드 id 목록이다.
- `result.valueType`: 결과 값 유형이며, 문자열 상수 `Double`이다.
- `result.unit`: `common.schema.json`의 공통 단위 정의(`$defs/unit`)다.
- `ossie.specVersion`: 문자열 상수 `0.2.0.dev0`이다.
- `ossie.metric`: Ossie 지표 객체다.
- `evidenceRefs`: 0개 이상 64개 이하의 근거 참조 목록이다.

`ossie.metric` 필드는 명세에 기술된 원본 Ossie 지표 객체를 그대로 담는다.
- 필수 필드로 `name`과 `expression.sql`을 지정한다.
- 선택 필드로 `description`과 문자열 형태인 `ai_context`를 둘 수 있다.
- `expression.dialects`와 `custom_extensions`는 스키마 검사에서 차단한다. 하류 증명 단계는 단일 엔진만을 사용하므로, 제2의 방언은 검증 주체 없이 남겨지는 텍스트에 불과하기 때문이다.

결과 단위는 `semantic-definition` 구성원이 아니라 지표 자체에 직접 선언한다. 따라서 `semantic-definition` 계약은 새로운 버전으로 올리지 않는다.

## Tyr 검사
Tyr는 `scripts/metric_definition.py`에 검사 규칙을 구현하며, 규칙을 위반한 산출물에는 다음 거절 코드를 반환한다.
- `metric.dataset-missing`: `dataset.recordMappingRef`에 지정된 레코드 매핑이 패키지나 작업공간에 없을 때 반환한다.
- `metric.input-missing`: `inputs`에 지정된 입력 필드가 참조 대상 레코드 매핑의 `resultSchema.fields` 필드 id 목록에 들어 있지 않을 때 반환한다.
- `metric.grain-input`: `grain.groupBy`에 지정된 그레인 키가 `inputs` 목록에 들어 있지 않을 때 반환한다.
- `metric.grain-key`: 그레인 키로 지정된 필드가 null을 허용하지 않는 `String` 유형이 아닐 때 반환한다.
- `metric.input-unreferenced`: 입력 필드가 `expression.sql` 본문과 `grain.groupBy` 어디에도 나타나지 않을 때 반환한다. Tyr는 SQL 문법을 파싱하지 않는다. 작은따옴표로 둘러싸인 문자열 리터럴을 텍스트에서 먼저 지운 뒤 남은 본문에서 식별자를 읽어 대조한다. 따라서 리터럴 안쪽에 적힌 식별자 이름은 참조로 인정하지 않는다.
- `metric.unit-unconfirmed`: 결과 단위 상태가 `known`으로 확정되지 않았을 때 반환한다.
- `metric.duplicate-name`: 둘 이상의 지표가 동일한 Ossie 지표 이름(`ossie.metric.name`)을 지정했을 때 반환한다.

작업공간 검사 단계에서는 스키마 형식 오류와 중복된 지표 `id`도 차단한다. 패키지 검사기(`p3a_contracts.validate_package`)는 작업공간 없이 패키지를 검증할 때에도 동일한 규칙을 온전히 적용한다.

## 발행
작업공간 루트에 `metricDefinitions` 키를 마련하여 최대 64개까지 지표 정의를 등록한다. 패키지 빌더는 개별 지표를 `metrics/<n>.json` 경로에 파일로 작성하고, 제안서의 `schemaVersion` 값을 2.24.0으로 지정한다.

지표 계산의 원천인 레코드 매핑을 산출물로 선택했을 때에만 그 지표를 묶어 발행한다. 지표는 자신이 참조하는 데이터셋 없이 단독으로 발행되지 않는다.

2.23.0 제안서 스키마는 새 kind인 `metric-definition`을 선언하지 않았으므로, 2.23.0 제안서에 지표를 담으면 스키마 오류가 발생한다. 2.21 레코드 필드 검사와 2.22 브로드캐스트 엔벨로프 검사는 2.24.0 제안서를 그대로 통과시킨다. 지표를 포함하지 않는 패키지는 기존처럼 2.23.0 버전을 유지한다.

## 하류 판정과의 경계
Tyr와 Bifrost는 SQL 텍스트를 검토하여 승인할 뿐, 어느 쪽도 쿼리를 직접 실행하지 않는다. 실제로 실행된 쿼리가 사전에 승인된 표현식과 일치하는지는 하류 파이프라인에서 버전을 고정한 SQL 엔진을 써서 바인딩된 계획(bound plan)을 비교하여 판정한다.

Bifrost는 Tyr와 코드를 공유하지 않는다. Bifrost는 자체 구현 코드(`MetricDefinitions`)와 바이트 단위로 일치하는 2.24.0 스키마 사본을 별도로 보관하여 동일한 번들을 독립으로 검증한다.

## 시험
시험 슈트는 `scripts/test_metric_definition.py`에 21개 테스트로 작성한다.

시험에 사용하는 픽스처는 다음과 같다.
- `fixtures/metric-definition/record-mapping.json`: 기존 픽스처는 수정하지 않고 브로드캐스트 픽스처 `broadcast-pumps`의 사본에 `String` 키 필드 `bucket`을 추가하여 만든 레코드 매핑 `availability-samples`다.
- `fixtures/metric-definition/metric.json`: 지표 식별자 `running-availability`, Ossie 이름 `availability_pct`, SQL 표현식 `100.0 * COUNT(*) FILTER (WHERE running) / COUNT(*)`, 그레인 키 `asset`, `bucket`, 단위 `%`를 지정한 지표 정의다.
- `fixtures/metric-definition/bundle/`: 위 작업공간을 바탕으로 생성한 발행 빌드 산출물이다. 테스트 항목 가운데 하나는 작업공간에서 번들을 다시 빌드하여 바이트 단위 일치를 검증하고, 다른 테스트 항목은 이 번들을 Bifrost가 보관하는 사본과 바이트 단위로 정확히 대조한다.

모든 거절 코드마다 전용 테스트 항목을 배정한다. 결함 주입(fault injection) 시험에서는 각 검사 규칙을 한 번에 하나씩 끈 채 테스트를 실행하였으며, 규칙을 끌 때마다 시험 묶음이 빠짐없이 실패하여 차단 효력을 확인했다.
