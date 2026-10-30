# AAS ConceptDescription 내보내기

## 목적과 범위

`scripts/aas_export.py`는 외부 AAS 도구가 Tyr의 의미 정의를 읽을 수 있도록 단일 Tyr `semantic-definition` 파일을 AAS v3.1 ConceptDescription으로 바꾼다.

고정 표준 및 SDK는 다음과 같다.
- IDTA-01001 v3.1(메타모델) 및 IDTA-01003-a v3.1(IEC 61360 데이터 명세)
- Python SDK `aas-core3.1==1.0.0`(MIT)

이들은 `requirements-aas.txt`에 고정되어 있다. 내보내기 도구는 다른 SDK 버전이 들어오면 실행을 거부한다(`aas.sdk-version`).

출력물은 호출자가 지정한 디렉터리에 쓰는 인접한 두 파일이다. 매핑 번들이나 제안에 추가하지 않으며, Tyr나 Bifrost 계약을 변경하지 않는다. Bifrost에는 새 의존성이 생기지 않는다.

사용법:
`python scripts/aas_export.py <semantic-definition.json> --language en --out <dir>`

## 필드 매핑 규칙

중첩 멤버를 순서대로 순회하며 고유한 `semanticId`마다 ConceptDescription 하나를 생성한다. ConceptDescription의 `id`는 `semanticId`다.

IEC 61360 필드(`DataSpecificationIec61360`, 템플릿 참조 `https://admin-shell.io/DataSpecificationTemplates/DataSpecificationIEC61360/3/0`):
- `name` -> `preferredName`
- `description` -> `definition`
- 단위 상태가 `known`이면 단위 코드를 `unit`으로 옮긴다.

`dataType`:
- `Boolean` -> `BOOLEAN`
- `String` -> `STRING`
- 단위가 알려진 경우에만 `Double` -> `REAL_MEASURE`, `Int32` -> `INTEGER_MEASURE`
- 알려진 단위가 없는 숫자 멤버는 `dataType`을 지정하지 않는다. AASc-3a-009 제약이 측정 유형에 단위를 요구하며 이를 개수로 부르면 추측이 되기 때문이다.

IEC 61360에 필드가 없는 항목은 ConceptDescription 확장에 옮긴다.
- `tyr:valueType`
- `tyr:unitStatus`(`known`, `not-applicable`, `unknown`)
- `tyr:role`
- `tyr:range.low`, `tyr:range.high`(`xs:decimal`)
- `Structure` 및 `StructureArray`의 경우 `tyr:members`(자식 semanticId들의 JSON 배열), `tyr:shape`, `tyr:lowerBounds`

설명 문구는 작성자가 정의에 직접 쓴 문구다. 사전 내용(IEC CDD, ECLASS)은 찾아보거나 복사하지 않는다. ECLASS는 `docs/P1-GOVERNANCE-CRITERIA.md`의 식별자 전용 규칙을 따른다.

## 언어 요건

`--language`는 필수 옵션이며 기본값이 없다. 정의의 이름과 설명 문구 언어를 명시하며, 내보내기 도구는 언어를 감지하지 않는다.

AASc-002 및 AASc-3a-008 제약은 기본 이름과 정의를 영어로 요구한다. 영어가 아닌 태그(`ko`, `de-DE`)는 `aas.language-not-english`로 거부하고, 유효하지 않은 BCP 47 태그는 `aas.language-invalid`로 거부한다. `en`, `en-GB` 같은 태그는 받아들여서 입력값 그대로 쓴다.

## 거부 조건

거부 시 종료 코드 3(exit 3)으로 종료하며 표준 오류에 `refused: <code>`를 출력하고 아무 파일도 쓰지 않는다.
- `aas.input-unreadable`: 입력 파일을 읽을 수 없을 때 거부한다.
- `aas.input-kind`: semantic-definition 형식이 아닐 때 거부한다.
- `aas.input-schema`: 자체 schemaVersion 기준 Tyr 계약 검증에 실패할 때 거부한다(1.0.0, 1.1.0, 2.2.0, 2.12.0 버전을 읽는다).
- `aas.semantic-conflict:<semanticId>`: 두 멤버가 하나의 semanticId를 공유하지만 서로 다른 ConceptDescription(다른 설명, 유형, 역할, 단위, 범위)을 생성할 때 거부한다. 완전히 동일한 재사용은 한 번만 쓴다.
- `aas.verify:<path>: <cause>`: SDK의 `verification.verify`가 오류(예: IEC 61360 허용 길이를 초과한 이름)를 보고할 때 거부한다.

검증을 마친 뒤 내보내기 도구는 SDK로 자신의 출력을 다시 읽어 동일한 JSON인지 대조한다(`aas.round-trip`).

## 출처 파일과 테스트

출력 파일 구성:
- `aas-environment.json`: 오직 `conceptDescriptions`만 담은 AAS `Environment`를 저장한다.
- `aas-environment.provenance.json`: 서술 유형(predicate type)이 SLSA Provenance v1인 서명되지 않은 in-toto Statement v1 명세다. 주어(Subject)는 `aas-environment.json`과 SHA-256 값이다. `resolvedDependencies`에는 입력 파일 이름, 원본 바이트의 SHA-256 값, 그리고 kind, schemaVersion, id, version이 들어간다. `externalParameters`에는 language가 들어간다. 빌더(Builder)는 `urn:tyr:aas-export`이며 `aas-core3.1`, IDTA-01001, IDTA-01003-a 버전을 명시한다.

이 파일은 내보내기 출처를 기록한다. 승인이 아니며, 승인은 Bifrost에 남는다. 타임스탬프를 기록하지 않으므로 같은 입력과 언어는 바이트 단위까지 같은 파일을 만든다.

`scripts/test_aas_export.py`에 있는 14개 테스트는 `scripts/ci_run.py`로 실행한다. 스칼라, 중첩 구조 배열, 범위, 단위, 정수 측정, 동일 재사용, 충돌, 언어, 입력 계약, SDK 검증 실패, 결정론과 두 요약값(digest), CLI를 검사한다.
