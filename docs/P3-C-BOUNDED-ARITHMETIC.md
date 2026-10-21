# P3-C C: 제한된 add·multiply·divide

## 범위와 계약

MVP-PLAN의 일반 식 미완료 중 유한 scalar 산술 노드 세 개를 구현한다. expression 문자열/eval·임의 주소 생성·cross-graph 참조·일반 차원 추론은 제외한다. 기존 graph의 decode/identity/subtract/linear/unit-convert/array/sqrt/clamp/selector를 유지하는 2.15.0 value-graph/common schema를 추가하고 구 schema는 수정하지 않는다. workspace 2.0, source/semantic/mapping/target 및 2.9 submission/approval/release·SQLite 테이블을 유지한다. 새 연산은 2.15.0을 명시해야 하고 구버전 수신기는 거부한다.

모든 새 노드는 inputs.left/right가 필요하며 수치 scalar를 받아 Decimal을 출력한다. 암묵적 cast나 단위 변환이 없다. 허용 선형 단위는 1, Pa, kPa, bar, rpm, 1/s, N.m, mN.m이다. unknown/not-applicable, Cel/K는 거부한다. 이 목록은 지원 정책이며 모든 물리량/온도 계산을 대표하지 않는다.

| 노드 | 단위 규칙 | 수치 정책 |
|---|---|---|
| add | left/right가 같은 허용 단위; 그 단위로 출력 | 4096자리 중간 계산, 비정확해지면 value.numeric-limit으로 거부 |
| multiply | 한 입력이 무차원 1; 다른 입력 단위 유지 | 4096자리 중간 계산, 비정확하면 거부 |
| divide | 분모가 1이면 분자 단위 유지; 양쪽 같은 허용 단위면 1 | precision:34, rounding:half-even 필수·고정 |

분모 0과 -0은 value.divide-zero이며 result:null/bad다. 나눗셈 근사는 loss.precision/uncertain으로 보존한다. 이후 cast의 손실과 exact 거부는 별도 단계다. 정확한 1/2는 근사 손실이 없다. 1/3은 그래프 근사와 Double cast 손실이 각각 표시된다. Pa/kPa를 자동 상쇄하지 않으며 먼저 명시적 unit-convert가 필요하다. 무차원/압력 같은 역단위·압력×압력 등의 복합 차원은 지원하지 않는다.

수치·단위가 일치해도 실제 물리적 의미가 같다는 보장은 없다. 이미 engineered된 값의 산술은 의도적 파생 정의로 기록하며 자동 raw 스케일 적용이 아니다. 현장 의미와 계수·유효 범위의 정답은 별도 PoV가 필요하다. Java는 값/분모를 실제 읽지 않으므로 정적 수신 검증이 모든 실행 시점의 0 분모 부재를 보장하지 않는다.

## 재사용과 구현

Python bounded_arithmetic는 단위 정책과 제한 계산을 담당하고 p3a gate/preview에서 재사용한다. 기존 codec·Decimal/cast·그래프 DAG/설비/참조/근거 closure·P3-D 시간/품질·selector lazy evaluation·P7 evaluator·SQLite CAS·P6 승인/파일 발행을 유지한다. Bifrost MappingBundle은 같은 계약을 Java에서 독립 검증하며 Python 코드를 공유하지 않는다. 기존 파일 registry 저널·GC·서명·base head 정책을 변경하지 않는다.

05에서 세 연산과 left/right를 선택하고 출력 단위를 명시한다. divide는 고정 정밀도 정책을 표시한다. 새 노드가 있거나 이미 2.15인 graph는 2.15로 저장하며 기존 graph는 불필요하게 올리지 않는다. 06 프로퍼티 매핑·09 원시 입력/단계/손실·13 독립 검증/승인/발행·16 독립 평가 양식을 재사용한다. 같은 workspace JSON/CAS를 저장하므로 DB migration이나 기존 행 재작성이 없다.

0 나누기·부정 단위·타입·순환·근거 누락·오래된 revision을 검사한다. P3-D 검사 실패 시 산술 수치를 노출하지 않고, 선택하지 않은 후보는 계산하지 않는다. 최종 cast/semantic range와 기존 invalidValuePolicy도 유지한다.

## 검증·현장 PoV

[fixture](../fixtures/p3cc/README.md) · [수용 결과](verification/P3-C-C-RESULTS.md). scripts/test_p3cc.py, Bifrost MappingPublicationTest의 arithmetic 검사와 scripts/p3cc/run.ps1에서 재현한다. 테스트는 localhost-only Docker·별도 SQLite/registry·임시 등록 키를 사용한다. 실제 자료/독립 담당자와 의미·계수·허용 오차·작업 시간 PoV는 미수행이다. 장치 통신·외부 SQL·쓰기 실행·runtime 활성화는 계속 제외한다.

이번 완료는 세 제한 산술 노드이며 일반 식·일반 차원 분석·온도 delta·cross-value-graph endpoint 전체 완료가 아니다. 이전 P7 테스트의 단계별 고정 JAR hash 검사는 향후 수신 기능 추가를 막지 않도록 구 schema 사본 보존 검사로 바꾸고, 기존 승인/발행 회귀로 구 동작을 확인한다. 과거 P7 수용 기록은 수정하지 않는다.
