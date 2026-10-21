# P3-E B 논리 구조·중첩 멤버·고정 구조 배열

## 구현 대상

기존 문서·수동 정의의 분산 PLC 접근을 상위 정준 객체로 묶는 오프라인 작성 모델이다. 각 말단은 기존 scalar 소스, 고정 scalar 배열의 array-element 또는 파생 그래프 결과에 연결한다. 같은 설비의 여러 target-instance 및 같은 구조 배열의 여러 요소를 전체 memberPath로 구분한다. 물리 주소의 연속성이나 PLC UDT 구조를 요구하지 않는다.

예: process.pressure.actual, process.pressure.target, modules[1].pressure.actual, modules[2].pressure.actual은 서로 다른 경로다. 배열 두 요소의 actual은 동일한 semanticId를 재사용할 수 있지만 매핑 대상은 인덱스까지 포함해 다르다. 이름이 같아도 경로가 다르면 중복 매핑으로 오인하지 않는다. D1000·D2000·D3000처럼 흩어진 실제값·목표값·상태 워드와 기존 배열 요소를 같은 논리 객체에 연결할 수 있다.

## 계약 2.12.0

semantic-definition, mapping-set, common 세 schema만 새 버전으로 추가한다. 기존 64개 schema는 수정하지 않는다. source-definition/graph/target-instance/proposal/submission/release 버전은 재사용하고 workspace envelope는 2.0.0이다. 구버전 schema에 중첩 멤버·인덱스를 넣으면 거부한다.

| 정의 | 필드와 규칙 |
|---|---|
| scalar 말단 | 기존 memberId/name/semanticId/description/valueType/unit/role/range. 정준 타입은 기존 Double/Int32/Boolean/String |
| Structure | memberId/name/semanticId/description/valueType: Structure/members. unit·range·role을 컨테이너에 붙이지 않는다 |
| StructureArray | Structure와 같은 멤버 템플릿, valueType: StructureArray, 명시적 shape/lowerBounds |
| member 경로 단계 | kind: member, memberId: 정확한 ID |
| index 경로 단계 | kind: index, indices: 전체 축 좌표. 바로 앞 StructureArray의 rank·하한·상한과 일치해야 함 |

경로 예:

    [
      {"kind":"member","memberId":"modules"},
      {"kind":"index","indices":[2]},
      {"kind":"member","memberId":"pressure"},
      {"kind":"member","memberId":"actual"}
    ]

정의 깊이 최대 8, 정의 노드 최대 256, 확장된 scalar 말단 최대 256개다. 구조 배열은 rank 1~3, 축별 shape 1~256, 요소 수의 곱 최대 256이며 여러 중첩 배열을 확장한 전체 말단 제한도 적용한다. lowerBounds는 signed Int32이며 최종 상한도 Int32 이내다. shape/lowerBounds/indices는 JSON 정수 표기를 사용한다. 1.0이나 Boolean을 정수 인덱스로 암묵 변환하지 않는다.

배열은 유한한 논리 반복 구조이며 stride/byteOffset/packing/alignment를 갖지 않는다. 원시 고정 scalar 배열의 2.4 shape/stride와 정준 StructureArray의 shape/lowerBounds는 별개다. 둘 사이 요소 선택은 바인딩마다 명시한다. 예를 들어 source 배열 [0,0]이 target modules[1].pressure.actual로 가는 관계를 작성한다.

members는 inline 정의다. 외부 typeRef/UDT 상속·가변 배열·객체 전체 source 자동 해석·native struct bulk decoding은 포함하지 않는다. 같은 모델의 재사용은 기존 target-instance의 semanticDefinitionRef로 수행한다.

## 정적 검증·거버넌스

형제 memberId 중복, 구조 깊이/크기, 배열 rank/상한, index 누락/범위 초과, 존재하지 않는 말단, scalar 뒤의 추가 경로, 컨테이너 전체를 scalar에 매핑하는 시도를 거부한다. 같은 target·전체 경로에 두 값을 매핑하면 mapping.duplicate-target이다. 다른 index의 동일 말단 이름은 허용한다. 경로는 문자열의 점/슬래시를 분할하지 않는다. memberId가 a.b인 literal 필드는 트리에 ["a.b"]로 표시해 a → b 경로와 구분한다.

완전성은 확장된 모든 말단 경로로 계산한다. 일부가 미매핑이면 기존처럼 초안을 저장할 수 있지만 mapping.incomplete-object 진단을 남기고 Bifrost 승인/발행은 거부한다. 단위·최종 타입·설비·근거 폐쇄와 source/graph 검증은 기존 규칙을 재사용한다.

scalar semanticId의 타입·역할·단위 충돌 규칙은 유지한다. 컨테이너는 자식 ID/의미/시그니처와 shape/lowerBounds도 정체성 시그니처에 포함한다. 이름·설명만으로 의미를 추정하지 않는다. P5에서 mapping.memberPath 변화는 identity, semantic 구조의 shape/lowerBounds 변화는 meaning으로 분류한다. 검토와 서명은 기존 파일/의존 해시에 결속한다.

Bifrost는 schema와 경로·구조·완전성·근거를 독립 Java 구현으로 검사한다. 앱끼리 Python/Java 코드를 공유하지 않는다. recursive schema의 local ref는 유지하고 외부 common ref는 bundled data만 해석한다. 깊이/정의 수를 schema 재귀 평가 전에 검사한다. 승인·파일 발행이며 runtime 활성화나 수치 실행은 아니다.

## 화면과 SQLite

15 논리 구조·구조 배열에서 모델 ID/버전을 지정하고 부모 구조와 새 Structure/StructureArray/scalar를 선택해 추가한다. members JSON으로 전체 정의를 편집할 수 있고, 확장된 말단 트리에서 실제 경로·인덱스·타입·단위를 확인한다. 빈 컨테이너는 편집 중 유지할 수 있으나 저장 전에 말단을 추가해야 한다. 03에서 기존 2.12 모델을 선택해도 이 편집기로 연결된다.

04에서 모델을 target-instance에 연결한다. 06은 모든 말단을 펼쳐 표시하고 소스/그래프·cast·시간/품질을 각 전체 경로에 저장한다. 다른 요소의 동명 멤버에 transform/temporalPolicy가 섞이지 않는다. 07 검색·비교와 09 개별 preview도 전체 경로를 표시한다.

SQLite의 기존 workspace JSON·revision·CAS를 재사용하므로 새 테이블/migration이나 기존 행의 자동 재작성은 없다. 기존 1.x 이전 경로와 2.0 flat 모델/바인딩은 유지한다. 새 bounded 제한을 과거 flat schema에 소급하지 않는다. 기존 write-definition은 그대로 두고 구조/구조 배열 자체에 대한 쓰기 정의·실행을 추가하지 않는다.

## 개별·전체 객체 미리보기

09는 기존 단일 말단의 디코딩→배열 선택/파생→변환→cast→정준 결과를 평가한다. 15의 객체 조립 미리보기는 POST /api/logical-preview에 revision, targetInstanceRef(id/version), samples와 선택적 evaluationContext를 보낸다.

반환은 result, partialResult, quality, members(전체 memberPath·말단별 trace/단위/타입/오류/손실), arrays(shape/lowerBounds), unusedSamples 및 입력/작성본 해시다. 하나라도 bad/미매핑이면 전체 result는 null이다. 정상 말단과 null 오류 위치를 담은 partialResult는 진단 전용이다. 손실/uncertain이 있으면 전체 quality도 uncertain이다. 결측을 0으로 채우거나 다른 요소로 대체하지 않는다.

JSON 배열의 첫 위치는 각 lowerBound에 해당한다. 즉 lowerBounds [1]의 modules JSON [0]은 논리 modules[1]이다. 원래 좌표는 arrays와 members.memberPath에 보존한다. 정확한 수치 표현은 기존 preview와 동일한 십진 문자열이며 Boolean/String은 그대로 유지한다. 정의/말단 보고서가 타입·단위를 제공한다.

가상 입력·미리보기 결과는 workspace나 revision에 저장하지 않는다. 기존 09의 명시적 scenario 저장은 2.4 payload 계약으로 재사용한다. 객체 전체 시나리오의 별도 자동 저장은 추가하지 않는다.

시간·품질은 각 바인딩의 명시적 temporalPolicy 범위다. 전체 객체에 원자 snapshot·프로퍼티 간 skew·단일 실제 품질/시각을 만들어내지 않는다. 같은 source를 여러 바인딩에서 공유하면서 DataValue envelope를 입력한다면 그 소비 바인딩들의 입력 정책도 일관되게 선언해야 한다. raw 값과 envelope를 한 source에 동시에 추정 적용하지 않는다. 다른 말단용 samples를 각 말단의 오류로 오인하지 않고, 객체에 사용하지 않은 samples는 unusedSamples로 반환한다.

## 재사용과 새 구현

| 재사용 | 신규 |
|---|---|
| 네 PLC scalar/고정 배열 접근, low/high·파생 노드, 단위/스케일·cast, evidence, P3-D 정책, P5 검토, SQLite/CAS, Bifrost 제출/승인/발행 | 2.12 schema 3종, 유한 논리 구조/전체 경로 resolver, 객체 조립 preview API, 트리 builder·확장 매핑 UI, 독립 Java 구조 검증, four-profile 40바인딩·중첩 배열·부정 fixture |

[fixture](../fixtures/p3eb/README.md) · [실행 결과](verification/P3-E-B-RESULTS.md) · [계획](../MVP-PLAN.md).

## 별도 검증과 제외 범위

vendor별 UDT/DB native 필드 offset·packing/alignment·endianness·BOOL 배치·상속·OPC UA ExtensionObject decoding과 vendor export의 자동 field selector는 실제 정의 자료를 받아 검증하는 후속이다. 논리 StructureArray를 만들었다고 native array-of-struct 읽기 지원을 주장하지 않는다.

현장 PoV는 실제 문서/설정 파일과 담당자의 독립 정답으로 의미 수렴·오매핑·누락·손실·검토 시간을 비교하는 별도 단계다. 장치 통신·외부 SQL·쓰기 실행·Muninn 활성화는 계속 제외한다.
