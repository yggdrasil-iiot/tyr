# P3-A 객체 인스턴스와 값 그래프 계약

상태: 2.0.0 작성 계약·파일 검증 및 fixture 구현. 이후 [2.0 화면·SQLite 작성 경로](P3-A-WORKSPACE.md)를 추가했다. Bifrost 승인/릴리스는 후속이다. 실제 장치 통신은 제외한다.

## 버전과 역할

기존 1.0.0/1.1.0 Schema 24개는 바이트 그대로 유지한다. 새 2.0.0에는 common, mapping-proposal, mapping-set, target-instance, value-graph 5개 Schema를 둔다. 소스·의미·근거 문서는 기존 1.0/1.1 형식을 재사용한다. 2.0 proposal은 이 여섯 종류의 실제 문서(source, semantic, evidence, target, graph, mapping 중 common 제외)를 파일 목록으로 고정한다. release/review/승인 계약을 2.0 지원한다고 주장하지 않는다.

Tyr (Týr)가 작성·검증하고 Mimir (Mímir)는 후보만 제공한다. Bifrost의 승인/발행 권한 및 Muninn의 향후 소비 경계는 유지한다. 다른 앱의 코드를 의존하거나 변경하지 않았다.

## 객체 식별

target-instance.id가 안정된 객체 식별자다. equipmentInstanceId는 소속 설비, semanticDefinitionRef는 재사용할 의미 모델, label은 표시 이름이다. mapping-set은 targetInstanceRef(id/version)를 고정하고 valueRef를 memberPath에 바인딩한다.

같은 설비에 motor-a·motor-b가 같은 motor-counter 모델을 사용할 수 있다. 같은 이름/주소/모델이라는 이유로 두 객체를 합치지 않는다. label 변경은 객체 ID를 바꾸지 않는다. 중복 대상 키는 (equipmentInstanceId, target-instance.id, memberPath)이며 mapping-set ID나 모델 버전을 바꿔도 같은 대상의 이중 바인딩을 허용하지 않는다. 한 proposal 안 같은 객체 ID의 복수 버전은 target.multiple-versions로 거부한다.

memberPath는 구조화 배열이다. 현재는 [{kind:"member", memberId:"cycle-count"}] 한 단계만 허용한다. 중첩 객체와 배열 index는 P3-E에서 계약을 개정한다. 문자열의 점/괄호를 임의 해석하지 않는다. 객체 병합/분리/ID 교체의 이전 이력·영향 비교는 P5이다.

## 값 참조와 그래프

mapping.valueRef는 다음 둘 중 하나다.

- {kind:"source", sourceRef:{id,version}}: 기존 단일 소스.
- {kind:"graph", graphRef:{id,version}, nodeId}: 특정 그래프 노드 결과.

value-graph의 각 노드는 nodeId/op/inputs/valueType/unit/evidenceRefs를 갖는다. inputs는 이름 있는 포트이며 입력은 특정 sourceRef 또는 같은 그래프의 nodeId를 참조한다. 그래프 간 연결·임의 식 실행은 지원하지 않는다.

현재 연산은 두 개로 제한한다.

| op | 입력 | 결과와 제약 |
|---|---|---|
| decode-u32-words | low, high | raw UInt16 두 입력. 각 입력 단위 not-applicable. 결과 UInt32 및 명시된 결과 단위. low + (high << 16). |
| identity | value | 입력 타입·단위 그대로. 명시한 valueType/unit과 일치해야 함. |

주소 연속성은 요구하지 않는다. D1000=1(low), D2000=2(high)이면 UInt32 131073이다. 입력 역할은 JSON key와 sourceRef로 명시되며 파일 순서·노드 배열 순서·사전 순서가 역할을 바꾸지 않는다. low/high를 바꾸면 65538이 되며 해당 차이를 oracle로 검증한다.

이 연산은 바이트를 직접 읽는 장치 디코더가 아니다. SourceDefinition에 각 원시 word의 타입·길이·byteOrder/wordOrder를 보존하고, 이번 fixture harness는 이미 UInt16으로 해석된 가상 입력만 받는다. 실제 raw bytes→word→graph→최종 cast의 일반 미리보기는 P3-B이다. UInt32 최댓값 4294967295는 노드 결과로 유효하지만 Int32 대상 매핑의 실제 값 오버플로는 후속 preview에서 error 정책을 적용해야 한다.

객체 프로퍼티 세 개에 세 소스를 바인딩하는 것과 두 소스를 합쳐 한 scalar를 만드는 것은 별도 표현이다. subtraction·sqrt·selector·native 구조/배열·시간/품질 조립은 이번 op 집합에 없다.

## 정적 검증

scripts/p3a_contracts.py는 다음을 검증한다.

- kind/schemaVersion, 추가 필드 금지, 지원하는 op/포트/경로.
- 파일 경로·바이트 해시·문서 정체성·문서/파일 중복.
- source/target/model/graph의 id와 정확한 version 참조.
- 대상의 소속 설비와 그래프·각 입력 소스의 소속 설비 일치.
- 모든 노드의 중복 ID·참조 누락·순환. 사용되지 않는 노드도 검사.
- raw UInt16 입력과 unknown/engineering 입력의 디코딩 오용, identity 타입·단위, 기존 변환의 타입/단위 흐름.
- 소스·노드·매핑의 근거 참조 및 모든 조합 입력의 근거 포함 여부.
- 대상 프로퍼티 중복과 미매핑 프로퍼티, 같은 의미 URI의 타입/역할/단위 충돌.

원문 근거 locator는 현재 text-line/json-pointer만 읽는다. XLSX locator의 실제 해석은 P4까지 evidence.locator-unsupported로 차단한다. 실제 메모리 범위·심볼 존재·서버 권한·동시 시점은 확인하지 않는다.

기존 직접 매핑에서 raw 단위 unknown은 1.x 정책대로 보존하고 mapping.input-unit-unknown-preserved warning을 낸다. 최종 단위 선언을 물리 차원 검증 완료로 간주하지 않는다. decode 입력에 unknown 단위를 허용하지 않으며 not-applicable word 두 개와 결과 단위를 명시한다. 소스 근거와 원시 단위를 마이그레이션 과정에서 추정/변경하지 않는다.

각 binding의 source lineage를 보고서에 남긴다. 완전한 변경 diff/전이 영향/서명된 승인 증거를 대신하지 않는다. 분산 입력의 동일 시점/품질/원자성은 보장하지 않으며 P3-D의 명시 정책이 필요하다.

## 마이그레이션과 수신 경계

1.x mapping-set ID → target-instance ID의 명시적 assignment 파일이 필수다. equipmentInstanceId에서 객체 ID를 자동 생성하지 않는다. 입력 원본은 수정하지 않고 존재하지 않는 출력 디렉터리에 새 proposal을 만든다. 모든 legacy mapping-set에 assignment가 있어야 하며 대상 충돌·불완전한 결과는 게시하지 않는다.

변경되는 필드는 mapping-set schemaVersion/version, targetInstanceRef, valueRef, memberPath다. source-definition·semantic-definition·evidence-artifact 및 원문 파일 바이트는 보존한다. 기존 변환·단위·invalidValuePolicy·mappingId·근거도 보존한다. 제출 proposal 버전은 2.0.0으로 바뀐다. 이는 새 로컬 제안이며 기존 승인·release·review를 자동 승계하지 않는다. 마이그레이션 입력은 P2 파일 bundle이며 review/release/observation이 섞인 범용 묶음의 이전은 아직 지원하지 않는다.

1.x 작성 경로는 2.0 문서를 직접 혼합하면 검증 오류로 거부한다. 별도 workspaceVersion 2.0 작성 경로는 새 화면과 SQLite 이전을 지원한다. 알 수 없는 버전을 조용히 저장하거나 그래프를 단일 소스로 축소하지 않는다. Bifrost·Muninn에서 2.0을 받아들이는 구현은 P6의 독립 검증 대상이다.

## 실행

```text
python scripts/p3a_contracts.py --package fixtures/p3a/two-motors --deny-network
python scripts/test_p3a.py --report docs/verification/p3a-validation.json
```

기존 P2 bundle을 이전하는 예:

```text
python scripts/p3a_contracts.py --package <legacy-bundle> --migrate-to <new-directory> --assignments fixtures/p3a/migration-assignments.json --deny-network
```

assignment의 mapping-set ID는 입력과 정확히 일치해야 한다. fixture assignment는 realistic workspace용 예제이며 임의 현장 자료에 그대로 적용하지 않는다.

[fixture](../fixtures/p3a/README.md) · [검증 결과](verification/P3-A-RESULTS.md) · [계획](../MVP-PLAN.md).
