# 정준 의미 계약과 값 생성·매핑 계약의 경계

2026-10-20 · **설계 보완·구현 예정**. 본 문서는 [전체 설계](../DESIGN.md)와 [P4-F 외부 정의 수용](P4-F-SOLUTION-INTERPRETATION.md)의 정준화 목적지를 구체화한다. 새 JSON Schema·조건 연산·업무 의미 검증·SQLite 기능을 구현한 문서가 아니다. 기존 1.x~2.22 wire, editor 계약, workspaceVersion2.0과 모든 저장 데이터의 의미를 소급 변경하지 않는다.

## 1 정준화 범위

정준화는 PLC 메모리맵 정리에서 끝나지 않는다. PLC·DB 결과·상수·조건·참조·템플릿을 통해 MES에 노출되는 **값의 뜻과 생성 정의**까지 범위에 포함한다. 단일 문서로 섞는 대신 아래 세 층을 연결한다.

| 층 | 답할 질문 | 소유하는 정보 | 자동 확정하면 안 되는 것 |
|---|---|---|---|
| 원본·해석 모델 | 기존 솔루션에 무엇이 설정됐는가? | native 계층/참조·claim·원본 locator·규칙·미해석·확보 범위 | 실제 운영과의 일치, 최종 업무 의미 |
| 정준 의미 계약 | 소비자가 무엇을 받으며 어떤 뜻으로 이해하는가? | 객체/프로퍼티·타입/단위·식별·업무 정의·관측/집계 범위·유효성 문맥 | 입력 주소나 태그 이름에서 의미 추론 |
| 값 생성·매핑 계약 | 어떤 입력과 규칙으로 그 값을 만드는가? | 소스/레코드 선택·조합/변환/조건·순서·시간/품질·0/1/N·결측·출처·상태 의존 | 지원하지 않는 동작의 삭제, 정의와 실제 취득/실행의 동일시 |

정준 의미는 제품 독립 소비 계약이다. 값 생성·매핑도 제품 고유 표현에서 공통 데이터 계약으로 정준화할 대상이다. PLC 접근 정의는 그 입력 중 하나이며 DB 레코드·상수·외부 값과 공존한다. 원본 해석 결과를 곧바로 의미 확정 또는 전환 동등성 확인으로 승격하지 않는다.

## 2 정준 의미 계약의 책임

의미 URI·객체/멤버 식별, 결과 타입·단위·역할·범위, 객체/배열 shape, 설비/작업 식별 기준을 관리한다. 수치와 이름만으로 충분하지 않은 업무 정의를 별도 명시한다.

- `productionCount`가 PLC 누적 카운터인지, 작업지시별 완료 수량인지, 불량을 제외한 양품 수량인지 구분한다.
- 관측 시점/구간, 작업지시 범위, 누적·구간·순간 값, 총량/양품/불량 범주를 구분한다.
- 상태 코드라면 코드별 뜻과 우선순위의 업무상 정의를 명시한다. 같은 Int32/단위1이라도 RUN/STOP/FAULT의 의미가 다른 계약은 같은 것으로 취급하지 않는다.
- 값이 없는 경우와 0, UNKNOWN 상태와 STOP, 미확인 품질과 정상값을 구분한다.
- MES가 요구하는 외부 필드명/포맷/전송 주기는 별도 소비 인터페이스 바인딩이다. 의미 계약을 MES 한 제품의 태그명에 종속시키지 않는다. 어댑터 배포/전송은 이번 범위 밖이다.

업무 정의가 계산 관계를 규정할 수 있다. 예를 들어 ‘같은 작업지시의 완료 수량에서 불량 수량을 제외한 개수’는 goodCount의 뜻이다. 특정 PLC 주소나 뺄셈 그래프 노드 ID는 이 뜻의 구현 방법이다. 업무 규칙을 모두 구현 상세로 밀어내지 않는다.

**현행 계약 한계:** 기존 semantic-definition의 URI·타입·단위·역할과 설명은 재사용한다. 설명문만으로 작업 범위·코드 사전·업무 계산 정의를 기계 검증할 수 있다고 주장하지 않는다. 신규 `SemanticContextContract`(논리 이름)는 기존 semantic definition pin에 업무 문맥·용어/코드 사전·확인 근거를 연결하는 별도 불변 editor 문서로 계획한다. 필드/버전/검증 규칙은 P4-F A에서 확정하며 구 schema에 unknown 속성을 넣지 않는다. 기존 의미 URI signature/lifecycle 검사를 새 문맥 검증이 이미 수행된 것처럼 표시하지 않는다.

## 3 값 생성·매핑 계약의 책임

| 영역 | 반드시 명시할 내용 |
|---|---|
| 입력과 원시 해석 | PLC 접근/디코딩/byte·word 순서, DB 필드/결과 스키마, 상수, 외부 값, 참조 graph의 불변 pin |
| 레코드 선택 | 키·대상 작업/설비와의 대응, 0/1/N·중복·NULL 정책, 선택 범위. 묵시적 첫 행/최신 행 선택 금지 |
| 변환과 구성 | low/high 조합, 단위·스케일·cast, 연산 순서, 객체/배열 프로퍼티별 연결, 공통 프레임 적용 |
| 조건 | predicate 입력/연산/타입, 분기 순서·우선순위·기본 분기, 선택 branch와 predicate 입력의 품질/시간/결측, lazy/eager 정책 |
| 오류와 유효성 | 잘못된 타입·범위·오버플로·행 오류·무효 입력·변환 손실과 출력 차단/품질 전파 |
| 시간과 상태 | 제공 sample의 시각·품질·freshness/skew, 관측 범위의 일치. 과거 값/초기값/리셋/주기/윈도 상태가 필요하면 의존성을 보존 |
| 추적과 재사용 | 의미 계약 pin·native 해석/근거·rule/template/application version, 슬롯 역할과 소스 연결, 전환 판정/가상 oracle scope |

신규 `GenerationContract`(논리 이름)는 이미 존재하는 source/graph/mapping/record/template 계약을 참조하는 조립·적합성 계약이다. 현재 표현 가능한 연산을 새로운 독자 실행 언어로 다시 만들지 않는다. 기존 계약으로 표현할 수 없는 조건·상태 동작은 신규 계약 검토 전까지 opaque·unsupported로 둔다.

bounded-selector는 정수 인덱스와 유한 후보를 선택하는 기존 연산이다. 이를 임의 Boolean if/else, 비교/논리 연산·여러 조건 우선순위·문자열 조건의 지원으로 간주하지 않는다. 상태 의존 이전 값 유지/카운터 기준점/리셋/누적 창을 현재 무상태 DAG에서 제거해 계산 결과를 만들지 않는다. 상태 의존 정의를 관측으로 보존할 수는 있으나 전환·preview는 차단한다. 임의 vendor 수식·스크립트는 실행하지 않는다.

## 4 두 계약의 결합과 적합성 판정

GenerationContract는 목적지 의미 계약의 정확한 id/version/hash, 입력 역할/범위 제약, 출력 memberPath와 생성 endpoint를 고정한다. 정적 타입/단위 일치뿐 아니라 입력의 업무 범위·단계·관측 시점이 출력 정의를 만족한다는 근거가 필요하다. 모르는 문맥은 unknown으로 남긴다. 단위·타입이 같다는 이유로 current-work-order count와 lifetime count를 교체하지 않는다.

검증 결과는 다음을 분리한다.

1. 구조/참조·기존 schema 적합성.
2. 출력 타입·단위·shape 및 시간/오류 정책 적합성.
3. 작업지시/기간·카운트 범주·코드 사전 등 업무 문맥 적합성: confirmed/unknown/disputed와 확인 근거.
4. 정해진 가상 입력/독립 oracle에서의 동등성: 시험한 범위만 판정.
5. 제품 규칙 해석/전환 손실 및 미해석 여부.
6. Bifrost 검증·서명 승인·발행, 실제 운영 확인: 각각 별도 상태.

담당자 확인은 근거 있는 선언이지 자동 논리 증명이나 제품 실행 검증이 아니다. 가상 예제 몇 개의 수치 일치를 일반 동등성 증명으로 확대하지 않는다. 같은 의미에 둘 이상의 생성 계약이 연결될 수 있지만 각 생성 계약의 적합성은 개별 확인한다.

## 5 혼합 템플릿 사례: MES 작업지시별 설비 생산 문맥

**가상 설계 사례**이며 PIO/Kepware의 실제 export 또는 현재 구현에서 그대로 실행 가능한 JSON이 아니다. 일반 if/업무 문맥 검증이 포함된 전체 예제는 미구현이다. 수치는 독립 oracle 명세이고 실행 통과 기록이 아니다.

### 5.1 의미 계약

객체 `equipment-production-context`, 업무 기준은 ‘평가 시점에 지정된 설비·작업지시의 생산 문맥’이다.

| 프로퍼티 | 결과 타입·단위 | 의미/범위 |
|---|---|---|
| equipmentId | String·해당 없음 | 이 객체가 나타내는 설비의 안정된 업무 식별자 |
| workOrderId | String·해당 없음 | 이번 문맥의 명시적으로 선택한 작업지시 |
| productCode | String·해당 없음 | 같은 작업지시의 제품 코드 |
| goodCount | Int32·1(개수) | 같은 작업지시의 완료 수량에서 같은 범위의 불량 수량을 제외한 개수; 순간 속도/설비 평생 누적 아님 |
| operationState | Int32·1(상태 코드) | 0 STOP, 1 RUN, 2 FAULT. 알람 활성은 운전 비트보다 우선. UNKNOWN/결측을 STOP으로 대체하지 않음 |

각 프로퍼티는 구분된 예시 의미 URI와 문맥 pin을 갖는다. 숫자 단위1만으로 개수와 상태 코드가 호환되는 것은 아니다. 이 의미 선언의 현장 정답은 담당자가 확인한다.

### 5.2 입력 슬롯과 적용본

| 입력 슬롯 | 가상 적용본 EQ-01의 입력 | 고정/교체 범위 |
|---|---|---|
| equipmentIdentity | 상수 String `EQ-01` | 설비 식별 역할. 적용본별 명시 바인딩/근거 |
| completedCount | PLC UInt16 typed 원시값 또는 그 가상 bytes; 이번 작업지시 완료 카운터 | 접근/디코딩은 source 계약, 슬롯에는 해석 후 타입·단위·입력 단계와 업무 역할 제약 |
| running | PLC Boolean 가상 값 | 운전 상태 입력 역할 |
| alarmActive | PLC Boolean 가상 값 | 우선 알람 입력 역할 |
| orderResult | 가상 DB 결과 집합 | 선언한 스키마/키/단위/입력 단계·capturedAt/quality pin. 실제 DB 접속/SQL 없음 |
| selectedWorkOrder | 명시 키 String `WO-100` | 이번 문맥 선택. 운영 DB의 ‘현재’ 레코드 자동 탐색 아님 |

orderResult 필드는 workOrderId(String, 키), equipmentId(String), productCode(String), rejectedCount(Int32·1)다. 선택 키는 WO-100이며 정확히1건이어야 한다. 선택 결과의 equipmentId가 EQ-01인지와 PLC 카운터가 같은 작업지시 범위인지 확인한다. 타입/동일 시각만으로 이 일치를 추정하지 않는다. DB 키 선택·건수/필드 검증은 기존2.20/2.21 원칙을 재사용하되 **동적 키 슬롯/필드 간 문맥 비교의 추가 자동 지원은 별도 구현**이다.

상수는 의미를 구분한다. equipmentIdentity는 설비별 식별 바인딩이며 0/1/2 상태 코드와 알람 우선순위는 의미·규칙에 묶인 값이다. 업무 결과를 바꾸는 기준값을 아무 입력 슬롯에서 교체 가능한 상수로 숨기지 않는다. 보정 상수라면 단위/유효 범위/개정 근거와 의미 적합성 재검토를 요구한다.

### 5.3 값 생성 규칙 (선언용 의사 코드)

```text
order = select exactly one virtual record by workOrderId = selectedWorkOrder
require order.equipmentId == equipmentIdentity
require completedCount and order.rejectedCount refer to the same work order
require 0 <= order.rejectedCount <= completedCount

goodCount = exact Int32(completedCount - order.rejectedCount)
operationState = if alarmActive then 2
                 else if running then 1
                 else 0

output = { equipmentId: equipmentIdentity,
           workOrderId: order.workOrderId,
           productCode: order.productCode,
           goodCount, operationState }
```

조건 predicate도 유효 입력이어야 한다. alarmActive가 결측/bad이면 false로 취급하여 RUN을 내지 않는다. alarmActive=true일 때도 counter/DB처럼 다른 필수 프로퍼티의 입력 오류를 감추지 않는다. 이 사례의 조건식은 alarmActive 우선·lazy branch를 요구하며 필요 predicate/선택 branch의 시간/품질을 검사한다. 선택되지 않은 running 입력의 bad가 상태 출력에 영향을 주는지는 이 규칙에서는 영향을 주지 않는 것으로 명시하지만, 다른 프로퍼티의 필수 입력이나 전역 프레임 정책이면 전체 검증이 우선한다. 제품의 eager 평가를 lazy로 바꾸는 것은 동등 전환이 아니다.

0건/다건·중복 키·equipment 불일치·작업 범위 미확인·불량 수량 초과는 최종 객체 차단이다. 필수 필드 NULL/결측/bad를 0이나 상수로 대체하지 않는다. maxAge=1000ms/maxSkew=500ms의 가상 시간 정책을 예시로 선언하고 필요한 DB/PLC 시각을 검사한다. 이는 실제 동시 취득·DB 트랜잭션 원자성·작업 전환의 일관성을 보장하지 않는다. 상수에는 허구의 취득 시각을 만들지 않는다. 이 사례는 현재2.22 공통 프레임 정책을 그대로 사용한 실행 사례가 아니며 lazy 조건과 프레임 범위의 충돌을 계약에서 해결한 후에만 구현한다.

### 5.4 가상 oracle 사례 (작성 예정)

| 입력/변경 | 기대 결과 또는 판정 |
|---|---|
| EQ-01, WO-100/PRODUCT-A/rejected10, completed1000, running=true, alarm=false, 유효 시각/품질·문맥 | {EQ-01, WO-100, PRODUCT-A, goodCount990, operationState1} |
| 위 입력에서 alarm=true, running=true | operationState2. 알람 우선순위 확인 |
| alarm=false, running=false | operationState0 |
| alarm 결측/bad | UNKNOWN을 STOP으로 바꾸지 않고 객체 차단·근거/진단 보존 |
| 선택 결과0건/2건·중복 키/NULL 필수 필드 | 객체 차단, 묵시적 첫 행/기본값 없음 |
| selected WO-100이 EQ-02 또는 PLC 카운터의 작업 범위 미확인 | 문맥 부적합/미확인으로 전환 적합성 차단; 타입 검증 PASS와 별도 |
| completed9, rejected10 또는 Int32 범위 초과 | 무효 범위/정확한 cast 오류, 자동 clamp/잘라내기 없음 |
| PLC/DB 시각 skew 초과·stale | 최종 객체 차단, 가상 값의 수치 일치로 시간 오류 해제 금지 |
| 같은 관측값이지만 completed가 lifetime count | goodCount 의미 적합성 실패. 가상 수치 일치가 의미 동등성을 증명하지 않음 |
| 같은 타입·단위의 카운터 소스만 교체, 근거와 범위 유지 | 의미 유지 후보; 새 적용 pin/생성 계약/가상 시험·영향 검토 필요 |

‘현재 작업 카운터’를 직접 제공하지 않고 lifetime-counter − 작업 시작 기준값으로 만드는 제품 사례도 수용해야 한다. 그러나 기준값의 취득·reset·재시작·중복 이벤트·overflow 정책이 없으면 incomplete/stateful-unsupported로 남긴다. 현행 그래프의 subtract만으로 상태 동작 지원을 주장하지 않는다.

## 6 템플릿·적용본의 경계와 변경 판정

템플릿은 의미 계약 pin + 값 생성 규칙/정책 + 입력 슬롯의 기술/업무 역할 요구를 묶는다. 적용본은 특정 설비의 source/레코드 선택/허용된 상수 바인딩과 원본 근거를 고정한다. 규칙 내 업무 상수와 자유롭게 바인딩 가능한 식별/보정 값을 구분한다. 새 템플릿을 저장해도 기존 적용본은 자동 갱신하지 않는다.

현행2.19는 model/graphs/mapping을 본문으로 포획하고 application이 templateRef/sourceSnapshots/generated를 고정한다. 이 저장 구조를 강제로 ‘새 의미 문서 참조만 허용’으로 변경하지 않는다. 새 계약은 기존 문서와의 대응/pin을 관리하고, 현재 슬롯 signature(타입·단위·단계)를 업무 역할 적합성의 증명으로 간주하지 않는다.

| 변경 | 의미 계약 영향 | 생성·적용본 영향 |
|---|---|---|
| PLC 주소/연결 변경 | 의미 유지 후보; 설비/측정 문맥 확인 필요 | 새 source/pin·적용본·근거·가상 시험 |
| 단위 표현/디코딩 경로 변경 | 같은 정준 의미가 될 수 있으나 동등성 확인 필요 | 원시 단계·변환 순서·손실·정확한 cast 검토 |
| 총생산량에서 불량을 빼기 시작 | 총량→양품으로 의미 변경 | 새 의미 URI/정의와 별도 생성 규칙; 기존 URI 덮어쓰기 금지 |
| 작업지시 수량을 평생 누적으로 바꿈 | 범위 변경이며 같은 의미로 묵인 불가 | 새 의미/바인딩·소비자 영향 검토 |
| 알람 우선에서 운전 우선으로 변경 | 상태 업무 정의 변경 | 코드 의미/조건 규칙 동시 검토; 새 의미/규칙 계약 필요 |
| 같은 업무 정의를 다른 동등 연산으로 구현 | 의미 유지 후보 | 규칙/가상 동등성 근거·정밀도/범위 검토; 몇 샘플 PASS만으로 일반 동등 판정 금지 |
| 결측을 오류에서0/이전 값으로 변경 | 소비자 유효성 의미에 영향 가능; 기본적으로 재검토 | 새 오류/상태 정책·기능 지원 필요, silent fallback 금지 |
| 설비 식별 상수 EQ-01→EQ-02 | 의미 모델은 재사용 가능 | 다른 설비에는 별도 적용본; 기존 적용본 소속을 이동시키지 않음 |

업무 의미 변경에는 기존 URI lifecycle 원칙에 따라 새 의미 정의/URI와 영향 검토를 사용한다. 기존 semantic signature가 업무 문맥 변화까지 탐지하지 못하는 경우는 신규 문맥 계약/게이트에서 차단해야 하며 현재 구현이 이미 차단한다고 표시하지 않는다.

## 7 재사용 가능 범위와 신규 구현 경계

| 기능 | 현재 재사용 자산 | 이번 관점에서 남은 일 |
|---|---|---|
| 의미 출력·버전 | semantic-definition·URI lifecycle·전역 카탈로그 | 업무 범위·유효성·코드 사전의 별도 불변 문맥 계약/영향 검증 |
| 입력·객체·레코드 | source2.x, [2.20](P4-C-RECORD-MAPPINGS.md), [2.21](P4-D-MIXED-OBJECTS.md), [2.22](P4-E-RECORD-BROADCAST.md) | 키/설비/작업 범위 적합성의 명시 근거·신규 지원 판정 |
| 조합·변환 | 기존 DAG·단위/스케일/cast·selector·cross-graph | 일반 비교/Boolean 조건·순서·lazy/eager·분기 시간/품질의 opt-in 계약. 기존 selector 의미 유지 |
| 템플릿 | [2.19](P6-MAPPING-TEMPLATES.md) model/graph/mapping·slot/application | 의미/생성 계약 각각의 pin·업무 역할·상수 종류·적합성 판정 |
| 원본 해석 | P4-F 공통 모델 설계 | 원본→해석→의미 계약/생성 계약의 이중 전환 대응·근거 closure |
| 상태 동작 | 미지원 관측 보존 계획 | 이번에도 실행 미지원. 별도 상태 모델/계약 검토 전 전환 차단 |

## 8 저장·승인·호환성

이번 변경은 문서뿐이다. 기존 schema·fixture·API·workspace JSON·SQLite DDL/body/revision·가상 시나리오·Bifrost JAR를 바꾸지 않는다. 새 문맥/조립 계약을 기존 닫힌 schema나 자유 note에 몰래 넣어 검증을 우회하지 않는다.

P4-F A에서 새 editor 문서 버전을 확정하고 B의 opt-in sidecar에 해석/의미 문맥/생성 계약/원문 대응/검토 pin을 저장하는 방식을 설계한다. 기존 SQLite를 여는 것만으로 sidecar를 만들거나 기존 정의를 재해석·재분류하지 않는다. 구2.19/2.20/2.21/2.22를 새 의미 계약으로 소급 승인하지 않는다.

P4-F C에서 두 계약과 원본의 대응·적합성·기존 계약 전환 후보를 dry-run한다. 일반 조건·업무 문맥·상태를 표현할 수 없으면 partial/unsupported를 유지한다. P4-F D에서 새 wire 근거 closure와 독립 Java 검증 준비 후에만 새 해석 기반 채택·제출을 허용한다. 기존 Bifrost 경로는 보존하고 Týr가 별도 승인 권위를 만들지 않는다. 승인/발행이 MES 전송·운영 활성화·SQL/장치 실행을 뜻하지 않는다.

## 9 추가 fixture·완료 기준 (명세만, 미작성/미실행)

P4-F SI01~SI18을 교체하지 않고 MG01~MG08을 추가한다. 예상 디렉터리는 `fixtures/solution-intake/semantic-generation/`이며 아직 생성하지 않았다. oracle은 의미 정의/업무 범위와 계산 기대값을 독립 작성한다.

| ID | 검증할 내용 |
|---|---|
| MG01 | 혼합 템플릿의 PLC/DB/상수/조건 전체 의존과 원문→두 계약 대응, 단독 설정에서도 미확인 의미 유지 |
| MG02 | 다른 제품/접근·이름에서 같은 의미/생성 정의로 수렴; 동일 이름/타입·단위의 lifetime/work-order 차이 구분 |
| MG03 | 위 5.4의 정상/우선순위/결측/bad·lazy/eager·0/1/N·중복/NULL·skew·범위/cast 독립 oracle |
| MG04 | 주소 교체·동등 변환은 의미 유지 후보, 총량→양품/범위/코드 우선순위 변경은 의미 변경으로 재검토·기존 URI 덮어쓰기 거부 |
| MG05 | 템플릿 의미/규칙 pin, 식별/보정/업무 규칙 상수 구분, 새 개정이 기존 적용본에 자동 반영되지 않음 |
| MG06 | 조건·동적 키·문맥 비교·이전 값/카운터 기준점 등 미지원 기능을 scalar/selector/subtract로 위장하지 않고 차단 |
| MG07 | sidecar 부재/구계약·기존 SQLite/시나리오·기존 제출 보존, 원본/두 계약/plan 변경 시 stale·다른 판단 유지 범위 검증 |
| MG08 | 새 wire 수신 전 거부, 준비 후 두 계약·업무 근거·전환 후보/미해석 독립 검증; 가상 동등성과 현장/운영/승인 구분 |

완료는 실행 가능한 계약/fixture·독립 검증 및 화면/저장/반환 경로로 확인한다. 이 설계의 문서 완료를 기능 완료로 체크하지 않는다. 실제품 파일 구조·기본값/조건 평가/외부 코드와 실제 MES 업무 정답·담당자 사용성은 P4-F E/F에서 별도 검증한다. 장치 통신·외부 SQL·쓰기 실행·제품 코드 실행·운영 설정 생성/활성화는 계속 제외한다.
