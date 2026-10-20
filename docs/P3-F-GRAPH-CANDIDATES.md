# P3-F B 유한 후보 그래프 선택

## 지원 범위와 재사용

2.13.0 value-graph의 bounded-selector는 candidate0..candidate31에 직접 sourceRef 또는 **같은 value-graph의 nodeId 출력**을 받는다. 후보는 기존 decode-u32-words, identity, subtract, linear, unit-convert, array-element, sqrt, clamp, 중첩 bounded-selector로 구성한 유한 DAG의 부분 그래프다. 별도 그래프 간 graphRef 연결·임의 식·주소 생성은 제외한다. index/previousIndex는 기존대로 정수·단위 1의 직접 소스다.

graph 연산·위상 검증·source codec·시간 품질 정책·SQLite JSON/CAS·시나리오·P6 closure/서명 승인/파일 발행을 재사용한다. 새 구현은 node 후보를 허용하는 버전 schema, lazy 후보 평가, DAG 정의/출처 추적, 후보 picker·요약과 fixture다. Bifrost는 schema/data 계약과 기존 독립 Java DAG/type/unit/evidence 검사기를 사용한다. Python 구현을 공유하거나 실행하지 않는다.

## 계약과 호환성

2.5.0/2.11.0 schema는 변경하지 않는다. node 후보를 쓰는 graph를 2.13.0으로 저장하며 이미 2.13.0인 graph는 편집 시 버전을 유지한다. source-only selector와 기존 mapping-set/target/semantic 문서는 유지한다. node 후보 endpoint 예시는 {"kind":"node","nodeId":"scaled-up"}이다. 후보의 모든 가능 입력에 대한 evidence closure가 필요하다.

SQLite 테이블 변경이나 데이터 재작성 없이 JSON/CAS로 후보 순서·nodeId·정책을 저장한다. 시나리오는 기존 별도 SQLite 테이블과 workspace hash를 사용한다. 기존 1.x→2.0 이전 경로도 유지한다.

## 정적 검증

선택 여부와 무관하게 모든 후보의 scalar 출력 타입·단위가 selector 출력과 정확히 일치해야 한다. unknown 단위를 허용하지 않고 다른 단위는 후보 내부에서 정규화한다. 암묵적 cast를 하지 않는다. 타입·단위 일치는 물리적 의미의 동등성을 자동 증명하지 않는다. 절대압과 차압처럼 차원이 같아도 의미가 다르면 현장 검토에서 별도 canonical 의미/프로퍼티로 구분해야 한다. 참조 ID/버전/설비/read 권한, 모든 가능 입력의 근거, 중복 nodeId, 순환·누락 노드, 연속 후보 번호·32개 상한·default 범위를 검사한다. 선택하지 않은 잘못된 후보도 저장·승인할 수 없다. 값의 inputStage는 후보에서만 결정하며 index/previousIndex의 단계는 이중 변환 판정에 섞지 않는다. Python과 독립 Java에서 같은 규칙을 검증한다.

## 선택 평가와 시간·품질

현재 index와 범위 정책으로 후보를 결정하고 **선택된 후보만** 평가한다. 여러 주소가 필요한 후보는 그 입력 전부를 requiredSources에 포함한다. 중첩 selector도 실제 선택 경로만 포함한다. DAG 정의 추적은 방문 집합으로 처리하여 공유 하위 그래프를 지수적으로 펼치지 않는다.

선택된 경로 + 현재/명시적 이전 index DataValue에 기존 freshness/skew/결측/bad/uncertain/sequence 검증을 적용한다. 선택하지 않은 후보의 bad·missing·stale·변환 손실은 결과를 오염시키지 않는다. 이전 후보 값은 실행하지 않는다. default-candidate는 index 범위 초과에만 적용하고 선택된 입력 오류를 대신하지 않는다.

P3-D처럼 가상 수치 probe로 필요 입력을 결정한 뒤 시간·품질을 검사한다. 실패 시 probe 수치를 결과/수치 trace로 노출하지 않고 selectionValueValidated=false 및 출처 해석 정보만 제공한다. 실제 동시 읽기/원자 snapshot을 보장하지 않는다.

## 출처 추적

선택 기록은 candidateRef, valueType/unit, 정적 sourceRefs, selectedSourceRefs, definitionSha256, previousCandidate, candidateChanged, sourceChanged를 제공한다. 후보별 시간·품질은 선택 경로만 평가하며 나머지는 not-evaluated다. 선택 입력의 가상 시각·품질·age/issues는 selectedInputDataValues에 표시한다.

definitionSha256은 출력 endpoint, 같은 그래프 ID/버전과 참조 DAG 노드 정의를 고정 JSON으로 해시한다. 같은 값이라도 다른 node/계산 경로면 sourceChanged=true, 같은 endpoint를 여러 인덱스가 공유하면 false다. 기존 sourceRef/previousSourceRef는 직접 소스일 때 유지하고 node 후보에서는 null이다. selectedSourceRefs는 중첩 selector의 실제 경로다. previousLineageMode=definition-only는 이전 후보의 sourceRefs가 가능한 정의의 closure이며 이전 시점 실행 결과가 아님을 뜻한다. 실행 간 자동 이력 비교는 제공하지 않는다. 기존 workspace/sample/evaluation hash를 별도로 유지한다.

## 화면과 검증

후보 picker에 소스/노드·출력 타입·단위를 표시하고 순서 목록에 추가한다. 직접 입력은 소스 ID, s:소스ID, n:노드ID를 허용한다. 0 기반 순서·타입·단위 요약, 저장·재열기, 미리보기 선택 경로/정의 해시/시간 품질 상세, 시나리오 저장, 독립 Bifrost validate/두 키 승인/파일 publish를 검증한다.

[fixture](../fixtures/p3fb/README.md) · [수용 결과](verification/P3-F-B-RESULTS.md). 실제 장치 통신·외부 SQL·쓰기 실행 제외. vendor native 배치, 실제 selector/운전모드 의미, timestamp/quality 수집, fallback 정책의 현장 정답은 별도 PoV다.
