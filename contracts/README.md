# Týr 데이터 계약 1.0.0

규범 파일은 1.0.0/*.schema.json이다. JSON Schema Draft 2020-12를 사용한다. common은 공통 정의이며 나머지 10개는 문서 종류별 스키마다.

| 문서 종류 | 역할 |
|---|---|
| evidence-artifact | 원본 파일·해시·확보 시점·범위 |
| source-observation | 출처별 원문 주장·추출 상태 |
| source-definition | 설비·접근·원시 표현·근거 |
| semantic-definition | 공통 의미·결과 타입·단위 |
| mapping-set | 소스와 의미 연결·변환 |
| review-record | 특정 문서 해시에 대한 로컬 확인 |
| observation-bundle | 관측·증거와 처리 건수 |
| mapping-proposal | 제출 파일·ID·버전·바이트 해시 |
| validation-report | 특정 proposal 해시에 대한 결과 |
| mapping-release | proposal과 고정 파일 목록·로컬 승인 기록 |

## 형식과 관계 검증

스키마는 필드·종류·문법을 검증한다. scripts/validate_contracts.py는 참조, ready 완전성, 타입·길이, 결과 단위·타입, 검토 해시, 묶음 바이트 해시 등 파일 간 규칙을 추가 검증한다. 이는 P1 계약 시험 도구이며 Bifrost 승인 구현이 아니다.

draft의 null은 초안 저장에 허용된다. ready의 필수 null은 패키지 검증에서 source.incomplete로 거부된다. semantic 결과 단위 unknown도 제출 패키지에서 거부된다. 원시값의 단위 미확인은 매핑이 결과 단위를 명시하면 보존할 수 있다.

accessProfileRef 네 값은 P0에서 확정한 대상 표현의 버전 ID다. P1 검사는 기본 구조·타입·길이까지만 확인한다. 실제 CPU의 메모리 범위·심볼 존재·OPC UA 접근 권한·MELSEC 프레임 가능성은 검사하지 않는다. 프로파일의 의미를 바꾸면 계약 버전 또는 프로파일 버전을 바꾼다.

## 바이트와 참조

문서 참조는 kind/id/version을 사용하고 proposal.files가 해당 파일과 sha256을 고정한다. sourceRef와 semanticDefinitionRef는 해당 kind의 id/version으로 해석한다. evidenceRefs는 단일 패키지 안의 고유 artifactId와 위치를 사용한다.

원본 파일은 evidence-artifact.file.path/sha256으로 고정된다. review.target은 대상 문서 해시를 고정한다. proposal은 자기 자신을 files에 포함하지 않는다. release는 proposalSha256과 동일한 files 목록을 고정하며 자기 해시를 포함하지 않는다.

검증 스크립트는 JSON의 중복 키를 거부하고 패키지 밖 경로와 외부 schema retrieval을 허용하지 않는다. 별도의 HTTP 서버나 PLC client를 만들지 않는다.

## 변환 규칙

linear는 수치 입력만 허용하며 중간 타입을 Decimal로 본다. 결과로 사용하려면 명시적 cast가 필요하다. cast는 결과 타입과 overflow/rounding 규칙을 갖는다. bit-select는 정수 입력 범위를 검사한다. enum-map은 수치 코드의 중복·미정의 처리를 검사한다.

P1은 변환 계약과 타입 흐름을 검사하고 독립 oracle로 예시 값을 확인한다. 일반 preview/decoder 실행 엔진, 단위 차원의 완전한 분석, 물리적 측정 위치의 동등성, PLC 내부 로직 검증은 구현하지 않는다.

## 계약 경계

Týr는 초안과 제안을 만들고 Bifrost가 이후 검증·승인·발행한다. Mímir의 local IRI는 의미 후보이며 확정 의미가 아니다. Muninn은 후속 승인 매핑 소비자다. 같은 스키마와 fixture를 독립 구현에서 검증할 수 있지만 앱 간 코드 의존을 만들지 않는다.

기존 UDT로 투영하면 접근·단위·role·변환·근거·검토 기록이 사라진다. 이 투영을 전체 계약으로 사용하거나 기존 UDT 게이트 PASS를 매핑 승인으로 사용하지 않는다.

## 변경 규칙

계약 1.0.0은 P1 검토 기준본이다. 새 필드·타입·연산·프로파일 도입은 스키마 버전 변경과 fixture를 동반한다. 기존 정의 내용 변경은 문서 version을 올린다. 화면 편집 revision은 wire version과 별도다. 이름이 같아도 주소·스케일·단위가 달라지면 별도 변경 검토 대상이다.

## P1에서 해석하지 않는 참조

connectionProfileRef와 equipmentInstanceId는 논리 식별자이며 P1은 매핑 양측의 설비 ID 일치만 검사한다. 실제 연결 프로파일의 존재·rack/slot·인증·장치 설정은 P2의 작성 컨텍스트와 P6 수신 검증에서 추가한다. P1의 reference.missing은 패키지 안 source·semantic·review 대상 문서 참조에 대한 검사다.

## 정준 의미와 거버넌스 평가 보완

[정준 모델 검증 기준](../docs/P1-GOVERNANCE-CRITERIA.md)을 따른다. semanticId가 개념을 식별하며 role·valueType·unit의 충돌은 semantic.identity-conflict로 거부한다. name·주소는 의미 ID가 아니고 설비 인스턴스는 유지한다.

새 governance-assessment 계약은 정준 bindings, 표본 valueOutcomes, projectionLosses, changeAssessments와 분석한 proposalSha256을 명시한다. 스키마는 추가 속성을 금지한다. 승인 결과가 아닌 오프라인 진단이며 원본 proposal의 불변성을 바꾸지 않는다. 1.0.0은 아직 P1 검토본이고 이 문서 종류 추가로 기존 문서 형식은 바뀌지 않는다.

scripts/governance_checks.py는 제한된 표본 실행과 의존 정의 비교를 수행한다. 수치 정밀도·반올림 손실, legacy UDT 부분 투영 손실, 의미·역할·단위·타입·범위·스케일·주소·디코딩·근거 변경을 평가한다. 실제 장치 통신은 완료 조건에서 제외한다.

## 1.1.0과 객체 매핑 확장

현재 작성 화면은 1.0.0·1.1.0을 읽고 신규/편집 정의는 1.1.0으로 작성한다. 기존 1.0.0 스키마는 보존했다.

다중 members[]/mappings[]는 기존 계약으로 표현할 수 있다. 새 1.1.0은 1/s·mN.m·K 단위와 unit-convert를 추가한다. 허용 변환은 1/s→rpm (×60), mN.m→N.m (×0.001), K→Cel (−273.15)이다. 시작 단위·끝 단위·허용 쌍과 변환 누락을 검증한다.

[객체 매핑과 샘플](../docs/OBJECT-MAPPING.md)에 프로퍼티별 분산 주소·이름 충돌·단위 차이·부분 객체 정책을 명시했다. 변환 정의 저장과 오프라인 표본 검증까지 제공하며 실제 Bifrost 수신·승인은 P6이다.

## 매핑 패턴 확장 제안

[지원 매트릭스](../docs/MAPPING-SUPPORT-MATRIX.md)와 [설계서 확장 결정](../DESIGN.md)을 참조한다. 현재 1.0.0/1.1.0 계약은 변경하지 않았다. 다중 입력·객체 인스턴스·codec 등 제안은 다음 계약 개정 대상이다. fixtures/mapping-patterns의 fixtureSpecVersion은 제품 wire 버전이 아니다.

## 2.0.0 P3-A 작성 계약

[계약 설명](../docs/P3-A-CONTRACT.md). common·mapping-proposal·mapping-set·target-instance·value-graph 5개 Schema를 추가했다. 소스/의미/근거는 1.0/1.1을 재사용한다. 기존 P1/1.x 문서 경로는 2.0 문서 혼합을 거부하며 p3a_contracts.py가 파일 경계를 검증한다. 별도 2.0 workspace는 화면·SQLite에서 수용한다. 2.0 release/승인/소비자 실행은 아직 지원하지 않는다.

## 2.0 화면·SQLite 수용

[2.0 작성기](../docs/P3-A-WORKSPACE.md)에서 target-instance·value-graph·mapping-set을 수용한다. 1.x 문서 검증 경로와 분리하며 별도 workspaceVersion과 명시적 마이그레이션을 사용한다. 기존 P1 게이트·승인/release 계약은 자동 확장하지 않는다.

## 2.1.0 원시 해석 정의

common·source-definition 두 Schema를 추가했다. workspace/value-graph/mapping-set은 2.0을 유지하며 2.1 소스를 참조할 수 있다. native bit(bitCount=1), bitCoordinate, BCD16/ASCII/S7-date codec을 명시한다. [정확한 범위와 preview API](../docs/P3-B-PREVIEW.md)를 따른다. 기존 스키마는 변경하지 않으며 다른 앱의 수신 지원은 자동 확장하지 않는다.

## 2.2.0 제한 다중 입력 파생값

common/source-definition/semantic-definition/value-graph/mapping-set 5개 Schema를 추가했다. Pa/kPa/bar, Decimal 중간값, subtract·linear·unit-convert 노드와 명시적 단위/최종 cast를 정의한다. target/proposal/workspace envelope는 2.0을 유지하며 이전 Schema는 보존했다. [범위와 경계](../docs/P3-C-DERIVED.md)를 따른다. 실제 장치 통신과 다른 앱의 수신·승인은 제외한다.

## 2.3.0 가상 시간·품질

common/mapping-set/preview-scenario 3개 Schema를 추가했다. 매핑의 선택 temporalPolicy, 가상 DataValue와 evaluationContext, 별도 검증 시나리오를 정의한다. 이전 Schema는 보존한다. workspace/target/proposal는 기존 버전을 유지하고 시나리오는 승인 proposal에 자동 포함하지 않는다. [정확한 범위](../docs/P3-D-TIME-QUALITY.md)를 따른다.

## 2.4.0 고정 scalar 배열

common/source-definition/value-graph/mapping-set/preview-scenario 5개 Schema를 추가했다. fixedArray shape/lowerBounds/strides/unit/range와 array-element indices를 명시한다. workspace/target/proposal는 기존 2.0, 의미 프로퍼티는 기존 scalar 계약을 유지한다. Typed slots 가상 시나리오는 2.4를 사용한다. 이전 Schema 39개는 보존했고 native 구조·동적 selector·장치 수집은 제외한다. [정확한 범위](../docs/P3-E-FIXED-ARRAYS.md).

## 2.5.0 · P3-F

common/value-graph만 신규다. 직접 scalar 후보 1~32개, 정수/unit 1 index, 선택적 previousIndex, reject/default-candidate를 정의한다. 다른 문서와 preview-scenario 버전은 재사용한다. 이전 Schema는 보존한다. [P3-F](../docs/P3-F-BOUNDED-SELECTOR.md).

## 2.6.0 · P4-A

common/import-batch/mapping-proposal을 추가했다. 원본 바이트·columnMap·당시 문맥·관측·가정/진단·초안을 분리하고 제안에 원본 evidence와 source-observation을 함께 포함한다. 기존 46개 Schema는 보존한다. source-definition 2.2와 evidence/observation 1.1은 재사용한다. [P4-A](../docs/P4-A-FILE-IMPORT.md).

## 2.7.0 · P4-B

common/source-definition/write-definition/mapping-proposal을 추가했다. 기존 49개 Schema는 보존한다. 비 PLC Typed scalar와 sourceKind/accessMode, 별도 쓰기 방향 계약을 정의한다. 기존 PLC는 implicit read이며 writable을 추측하지 않는다. [P4-B 상세](../docs/P4-B-MIXED-SOURCES.md).


## 2.8.0 로컬 검토 계약

review-baseline, change-assessment, change-review는 불변 기준본·변경/전이 영향·담당자 확인 기록용이다. 기존 53개 Schema와 proposal/작성 workspace는 유지한다. 기존 review-record 1.0과 wire-compatible하다고 간주하지 않으며 proposal에 포함하지 않는다. [P5 설계](../docs/P5-CHANGE-REVIEW.md).


## 2.9.0 Bifrost 파일 연계

mapping-submission/mapping-validation/mapping-approval/mapping-release 4종을 추가했다. 제출 ID와 안정된 스트림, pinned 문맥/기준 릴리스, 전체 파일 SHA, 수신 변경 보고서 hash와 등록된 두 주체의 서명을 사용한다. 기존 56개 문서는 변경하지 않는다. 계약은 데이터로만 복사하고 Bifrost는 독립 구현으로 검사한다. [P6 경계](../docs/P6-BIFROST-PUBLICATION.md).


## 2.11.0 제한 파생 수학

common/value-graph만 추가한다. 2.5.0 그래프의 기존 노드와 sqrt/clamp를 함께 담는다. sqrt는 무차원 1·Decimal·precision 34·rounding half-even을 고정하고 clamp는 같은 known 단위의 decimal low/high를 명시한다. 새 노드를 구버전 graph에 넣으면 거부한다. 기존 62개 schema, workspace 2.0.0, proposal/submission/release와 SQLite 스키마는 변경하지 않는다. [상세](../docs/P3-C-BOUNDED-MATH.md).


## 2.12.0 논리 구조·구조 배열

semantic-definition/mapping-set/common만 추가한다. Structure/StructureArray의 inline members, shape/lowerBounds와 member/index 경로를 선언한다. 깊이 8·정의 256·확장 말단 256·rank 3의 bounded 논리 모델이며 native byte 배치는 정의하지 않는다. 기존 64개 schema와 workspace 2.0.0·SQLite 테이블·publication envelope는 유지한다. [상세](../docs/P3-E-LOGICAL-STRUCTURES.md).
