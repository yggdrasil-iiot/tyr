# Týr 매핑 패턴 지원 매트릭스

기준일: 2026-10-17. 16개 매핑 패턴 + 객체 식별/미해석 보존 2개 공통 요구. 실제 장치 통신은 제외한다. 아래 표는 현재 소스·계약·검증기의 범위이며 제품 전체 호환성 인증이 아니다.

## 상태를 읽는 방법

- 지원: 명시된 현재 범위에서 구현되어 있음. 부분: 제한된 하위 형태만 구현. 계약만: 스키마 관측/보존 틀만 있으며 해당 제품 기능은 없음. 미지원: 전용 모델·실행 경로 없음.
- 원문 보존의 부분은 수동 근거/원문 필드 보존이다. 실제 vendor export의 무손실 importer/roundtrip을 뜻하지 않는다.
- 샘플 평가는 오프라인 harness이며 UI 값 preview가 아니다. 정적 검증의 지원도 해당 패턴 제한 안에서만 성립한다.
- A: 다음 오프라인 MVP 핵심. B: 자료로 필요성 확인 후 확장. C: 후순위 정의 보존. 계획은 구현된 지원 상태와 독립적이다.

## 현재 지원과 우선순위

| ID·패턴 | 계약 표현 | 원문 보존 | 정적 검증 | 샘플 평가 | 화면 | 우선순위·단계 | 제한 |
|---|---|---|---|---|---|---|---|
| MP01 단일 소스 → 스칼라 | 지원 | 부분 | 지원 | 부분 | 지원 | A / P3-B | 숫자/Boolean·제한 codec의 단계별 read-only preview 지원. 네 접근의 가상 입력만 검증하며 실장치 통신은 제외. |
| MP02 분산 주소 → 객체 프로퍼티 | 지원 | 부분 | 지원 | 부분 | 지원 | A / P3-A | 평면 및 2.12 중첩 scalar 말단·구조 배열 경로. 완전성 검사는 전체 경로 기준. 원자적 시점 보장 없음. |
| MP03 파라미터·기준 주소·인스턴스 예외 | 부분 | 부분 | 부분 | 부분 | 부분 | A / P4-A subset 구현 | base/stride/count·인스턴스 override의 유한 전개. vendor UDT 상속/임의 식 제외. |
| MP04 네이티브 구조체 → 객체 | 부분 | 계약만 | 부분 | 미지원 | 부분 | B / P3-E | 구조체 멤버를 scalar 심볼로 쓰는 것만 가능. 전체 타입/필드 selector 미지원. |
| MP05 중첩 객체·반복 객체 인스턴스 | 부분 | 부분 | 부분 | 부분 | 부분 | B / P3-E 논리 subset | 2.12 inline 구조·고정 구조 배열과 전체 경로 작성/검증/가상 객체 조립. 외부 typeRef/UDT 상속·native 배치는 제외. |
| MP06 배열 shape·stride·인덱스 | 부분 | 부분 | 부분 | 부분 | 부분 | 고정 배열 A / P3-E | 2.4 고정 scalar 배열 형상·저장 범위·요소 선택·가상 평가. 2.12 논리 구조 배열 추가. vendor native struct 배치·동적 인덱스는 별도 후속. |
| MP07 여러 워드 → 단일 저장값 | 부분 | 부분 | 부분 | 부분 | 부분 | A / P3-B | 분산 UInt16 low/high→UInt32와 최종 cast/overflow를 바이트부터 preview. UInt64·분산 signed 재해석은 후속. |
| MP08 워드 fan-out·비트·상태 코드 | 부분 | 부분 | 부분 | 부분 | 부분 | A / P3-B | word bit/명시 native-byte 좌표·MELSEC native bit subset을 2.1로 작성하고 preview. 실제 frame·CPU 범위는 미검증. |
| MP09 문자열·BCD·날짜 codec | 부분 | 부분 | 부분 | 부분 | 부분 | A / P3-B | 2.1 고정 ASCII/NUL·BCD16·DB의 S7 DATE_AND_TIME subset 작성/preview. DateTime 결과 타입·일반 인코딩/날짜 형식은 미지원. |
| MP10 스케일·단위·비선형 변환 | 부분 | 부분 | 부분 | 부분 | 부분 | A / P3-C | 입력별 linear/unit-convert와 압력 Pa/kPa/bar 변환·최종 cast 손실 preview 구현. 2.11.0 무차원 sqrt·같은 단위 clamp 추가. 일반 차원 분석은 B 후속. |
| MP11 여러 입력 → 계산·조립 스칼라 | 부분 | 부분 | 부분 | 부분 | 부분 | A / P3-C | 2.2 이름 있는 left/right subtract와 입력별 변환을 작성·저장·preview. 압력/무차원 같은 known 단위만 허용. 결측은 bad/null. 일반 식·시간/품질 조립은 후속. |
| MP12 별칭·참조 체인·view | 부분 | 부분 | 부분 | 부분 | 부분 | A / P4-A subset 구현 | 파일 내 alias chain·순환/결측·근거 경로. vendor view/alias importer 제외. |
| MP13 동적 주소·소스 선택 | 부분 | 부분 | 부분 | 부분 | 부분 | B / P3-F 구현 | 1~32 scalar 후보·정수 index·기본 후보·sourceRef 변경. 임의 주소식·후보 그래프·장치 read 제외. [P3-F 검증](P3-F-BOUNDED-SELECTOR.md). |
| MP14 상수·솔루션 태그·외부 값 혼합 | 부분 | 부분 | 부분 | 부분 | 부분 | B/C / P4-B subset 구현 | 상수/솔루션/외부 Typed 값과 PLC 혼합. provider/SQL 실행 제외. |
| MP15 읽기·쓰기별 정의·변환 | 부분 | 부분 | 부분 | 부분 | 부분 | B/C / P4-B subset 구현 | 명시적 접근 방향과 별도 쓰기 변환·근거 검증. 자동 역변환/쓰기 실행 제외. |
| MP16 시각·품질·레코드 조립 | 부분 | 부분 | 부분 | 부분 | 부분 | A / P3-D | 2.3 가상 age/skew·결측·bad/uncertain·trigger sequence 검증과 시나리오 저장. 실제 시각/품질·원자 조립·연속 latch는 후속. |
| MP17 객체 인스턴스 식별 | 지원 | 부분 | 지원 | 부분 | 지원 | A / P3-A | 2.0 객체 ID와 같은 설비의 복수 객체 작성·조회·중복/완전성 검사 지원. 기존 1.x는 명시적 이전 필요. |
| MP18 미지원 원문·손실·미해결 보존 | 부분 | 부분 | 부분 | 부분 | 부분 | A / P4-A subset 구현 | XLSX/교환 JSON raw bytes/hash·locator·미해석/수식 보존·왕복. PDF/.xls 제외. |

## 근거와 해석 범위

Ignition UDT의 멤버별 경로·매개변수·override와 Kepware Complex Tags의 그룹화를 보면 분산된 소스를 객체 프로퍼티로 묶는 방식은 기존 제품이 명시적으로 제공하는 패턴이다. 여러 제품에서 반복 지원한다는 근거이며 현장 사용률 통계는 아니다. SPIN 사례는 유틸리티 분야이며 제조 공장 전체를 대표하지 않는다. 구조체 한 번 읽기와 개별 태그 조립은 별도이며 조립 자체로 동일 시점 snapshot이 되지 않는다.

- [Ignition 8.1 UDT Parameters](https://www.docs.inductiveautomation.com/docs/8.1/platform/tags/user-defined-types-udts/udt-parameters): MP02, MP03, MP17
- [Ignition 8.1 UDT Nesting](https://www.docs.inductiveautomation.com/docs/8.1/platform/tags/user-defined-types-udts/udt-nesting): MP05, MP17
- [Ignition 8.1 UDT Inheritance](https://www.docs.inductiveautomation.com/docs/8.1/platform/tags/user-defined-types-udts/udt-inheritance): MP03
- [Kepware Complex Tags](https://support.ptc.com/help/kepware/kepwareplus/en/kepwareplus/advanced-tags/complex-tags.html): MP02, MP16
- [Kepware Derived Tags](https://support.ptc.com/help/kepware/kepwareplus/en/kepwareplus/advanced-tags/derived-tags.html): MP11
- [Kepware Scaling](https://www.ptc.com/help/kepware/kepware_server/en/kepware/server/scaling.html): MP10
- [Beckhoff OPC UA StructuredTypes](https://infosys.beckhoff.com/content/1033/ts6100_tc2_opcua_server/15563544971.html): MP04
- [Ignition 8.1 Mitsubishi TCP Driver](https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/opc-ua/opc-ua-drivers/mitsubishi-tcp-driver): MP06, MP07, MP08, MP09
- [Ignition 8.1 Siemens Driver / Addressing](https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/opc-ua/opc-ua-drivers/siemens): MP08, MP09, MP11
- [Ignition 8.1 Modbus Address Mapping](https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/opc-ua/opc-ua-drivers/modbus/modbus-address-mapping): MP06, MP07
- [Ignition 8.1 Types of Tags](https://www.docs.inductiveautomation.com/docs/8.1/platform/tags/types-of-tags): MP01, MP10, MP12, MP14, MP15, MP18
- [Siemens WinCC Unified Multiplexing, 04/2026](https://docs.tia.siemens.cloud/r/en-us/v1.0/wincc-unified/modernization-how-tos/hmi-tags/multiplexing?contentId=ecAyM8kjDjJuOKgIayMX_g): MP13
- [OPC UA Part 4 DataValue](https://reference.opcfoundation.org/specs/OPC-10000-4/7.11): MP16
- [AVEVA System Platform Object I/O Access official training](https://community.aveva.com/heroes-hq/m/aveva-system-platform---beg---2017-training/21859): MP02, MP18
- [Tatsoft / SPIN Automation case study (utilities)](https://tatsoft.com/wp-content/uploads/2020/09/CaseStudy_Spin.pdf): MP02

각 패턴의 evidenceRefs와 codeRefs는 [matrix.json](../fixtures/mapping-patterns/matrix.json)에 있다. 문헌의 제품 지원과 Týr의 현재 지원을 혼동하지 않는다. Modbus 주소 매핑은 배열/stride 패턴의 참고이며 이번 네 접근 프로파일에 Modbus를 추가했다는 뜻이 아니다.

## 검증과 승격

총 56개 명세: current 14개, gap-probe 8개, planned 34개. current는 기존 코드 동작을 확인하고 gap-probe는 현재 거부/누락을 재현한다. planned는 기대 결과가 있는 명세로만 검증되며 pending이다. 스키마 거부를 지원 성공으로 세지 않는다. 18개 패턴 전체 지원률을 이 숫자로 계산하지 않는다.

1.x/P2에서 남은 공백: 동일 설비의 복수 동일 모델 객체를 식별하는 키가 없고, P1 viewOf는 순환을 탐지하지 않는다. MELSEC native relay 영역과 word 주소 단위의 호환성 검사가 없다. 이 공백은 숨겨진 정상 fixture가 아닌 gap-probe로 남긴다.

지원 승격에는 새 버전 계약, 독립 정답, 정상/오류 검증, API 저장/재로드, 해당 화면 확인, 구 계약 회귀와 미지원 수신자 거부 근거가 필요하다. 지원하지 않는 표현은 unresolved로 보존하고 승인 가능한 정의로 자동 승격하지 않는다.

실행: python scripts/validate_pattern_matrix.py --deny-network --report docs/verification/pattern-matrix-validation.json. [실행 결과](verification/MAPPING-PATTERNS-RESULTS.md), [단계별 계획](../MVP-PLAN.md).

## P3-A 2.0 파일 계약 추가

MP07/11/17의 계약·정적 검증 일부를 추가했다. [P3-A 계약](P3-A-CONTRACT.md)과 [별도 실행 증거](verification/P3-A-RESULTS.md)를 참조한다. matrix.json의 versionSupport가 1.x/P2와 2.0 파일 계약을 구분한다. 기존 56개 사례의 current/gap-probe는 1.x 기준이며 planned는 전체 제품 기준으로 유지한다. 2.0 word 조합 harness가 통과해도 일반 decoder·UI·SQLite 지원으로 승격하지 않는다.

## P3-A 화면·SQLite 지원 추가

[2.0 작성기](P3-A-WORKSPACE.md)에서 MP17 객체 식별과 MP07/MP11의 low/high·identity subset을 작성·저장·조회한다. versionSupport의 2.0.0-workspace로 구분한다. 기존 1.x gap 재현 결과는 해당 경로의 기록으로 유지한다. 일반 decoder/preview·파생식·시간/품질은 후속이다.

## P3-B 가상 값 평가 추가

[바이트·codec·변환 미리보기](P3-B-PREVIEW.md)와 별도 50개 oracle을 추가했다. 현재 지원 축은 제한 subset으로 유지하며 기존 56개 baseline의 planned를 전체 패턴 지원 통과로 계산하지 않는다. 입력·결과는 read-only이며 실제 장치 통신은 제외한다.

## P3-C 파생값 subset

MP10/MP11의 2.2.0-derived 경로에서 subtract·입력별 linear/unit-convert·최종 cast의 작성/저장/조회/preview를 검증했다. [독립 실행 fixture](../fixtures/p3c/README.md)와 [실행 증거](verification/P3-C-RESULTS.md)를 따른다. 기존 planned 34건을 일괄 성공으로 올리지 않는다. 임의 계산·비선형·일반 차원·시간/품질 조립이 남아 MP10/MP11 전체 지원 축은 partial로 유지한다.

## P3-D 가상 시간·품질 subset

MP16의 2.3.0-virtual-time-quality 경로에서 단일 바인딩의 필수 입력 시각·품질·freshness/skew·결측/bad·가상 trigger sequence를 검증하고 별도 SQLite 시나리오로 재현한다. [fixture](../fixtures/p3d/README.md), [증거](verification/P3-D-RESULTS.md). 실제 OPC DataValue 품질·시계 동기화·원자 snapshot·target 전체 조립·연속 latch/trigger/ack는 포함하지 않아 전체 지원은 partial이다. 기존 planned baseline 성공 건수는 유지한다.

## P3-E 고정 scalar 배열 subset

MP06의 2.4.0-fixed-scalar-array 경로에서 shape/lowerBounds/stride/range·고정 indices·주소/범위 검사·scalar 의미 매핑과 SQLite/가상 preview를 지원한다. [fixture](../fixtures/p3e/README.md), [실행 증거](verification/P3-E-RESULTS.md). 배열 요소의 의미 매핑을 native 구조/중첩/구조체 배열/동적 selector 지원으로 계산하지 않는다. MP06 전체는 partial이며 기존 planned baseline은 별도로 유지한다.


## P4-A bounded importer · 2026-10-17

MP03·MP12·MP18은 XLSX/tyr-config-v1 subset에서 부분 지원한다. template base/stride/count·인스턴스 override, alias chain/cycle/missing, 원본 byte/hash·locator·미해석 보존을 구현했다. 벤더 설정·UDT 상속·임의 식·PDF/.xls는 포함하지 않는다. 기계 판독 matrix.json을 갱신했으며 기존 planned 시험은 역사적 기준선으로 유지한다. 실행 증거는 test_p4a.py와 [P4-A 설계](P4-A-FILE-IMPORT.md)를 따른다.

## P4-B · 2026-10-17

MP14/15를 [혼합 소스·방향 정의](P4-B-MIXED-SOURCES.md)의 bounded 범위에서 구현했다. scalar 가상 읽기와 쓰기 메타데이터 검증을 구분하며 SQL/쓰기 실행을 지원으로 세지 않는다. 역사적 planned 목록은 별도이고 실제 검증은 test_p4b.py를 따른다.


## A07 2.10.0 명시적 word/bit view

MP08·MP12의 새 경로는 PLC 정수 전체 워드와 alias/bit view를 작성·저장·조회·가상 preview하고 Bifrost가 독립 검증·서명 승인·파일 발행한다. 부모 버전·snapshot·16단계 체인·범위·근거 closure·원본 시각/품질을 검사한다. [계약·화면](A07-SOURCE-VIEWS.md) · [fixture](../fixtures/a07/README.md) · [실행 결과](verification/A07-RESULTS.md).
기존 1.x/P2의 current/gap/planned 사례를 덮어쓰지 않으며 matrix.json의 sourceViewsVerification으로 새 경로를 구분한다. native 구조·임의 vendor alias importer·runtime 소비까지 MP08/MP12 전체가 지원된다는 뜻은 아니다.


## P3-C B bounded math subset

MP10/MP11에 [2.11.0 sqrt·clamp](P3-C-BOUNDED-MATH.md) 작성·저장·preview와 독립 Bifrost 계약 검증·파일 승인/발행 경로를 추가한다. sqrt는 무차원, clamp는 같은 known 단위의 명시 범위에 한정한다. 근사·clipping·cast 손실을 따로 표시한다. 일반 식·임의 차원 분석·native 구조·현장 PoV는 남아 전체 축은 partial이다. 기존 planned baseline은 이번 두 노드 테스트만으로 일괄 성공 처리하지 않는다.


## P3-E B 논리 구조 subset

[2.12 계약·작성·객체 preview](P3-E-LOGICAL-STRUCTURES.md)에서 MP02/MP05/MP06의 논리 경로를 확장한다. 서로 다른 주소/고정 source 배열 요소/graph 결과를 중첩 말단과 각 구조 배열 요소에 명시적으로 연결한다. 네 profile 공통 객체 정답과 독립 Java 수신 검증을 사용한다. 기존 matrix.json/current/gap/planned 기록은 바꾸지 않고 [새 overlay](../fixtures/p3eb/support.json)로 구분한다. native struct bulk decoding·vendor 필드 배치·현장 PoV가 남아 전체 패턴 축은 partial이다.


## P3-F B 유한 후보 그래프 subset

MP13은 [2.13 계약·화면·미리보기](P3-F-GRAPH-CANDIDATES.md)에서 직접 소스와 같은 그래프 DAG 결과를 후보로 지원한다. 타입/단위/근거는 모든 후보, 시간·품질·손실은 선택된 경로만 검증한다. 기존 matrix/current/gap/planned는 유지하고 [새 overlay](../fixtures/p3fb/support.json)로 구분한다. 임의 주소 생성·실제 동적 PLC read·vendor 운전모드 PoV가 남아 전체 축은 partial이다.


## P4-A B 검토·재가져오기 subset

MP03/12/18은 [2.14 workflow](P4-A-IMPORT-RECONCILIATION.md)에서 원본/미해석을 보존한 명시적 해결·비소스 분류, ID 기반 3방향 비교·충돌 선택·현재 정의 유지·제거/재등장과 SQLite/CAS를 지원한다. [합성 overlay](../fixtures/p4ab/support.json)로 기존 matrix/current/gap/planned와 구분한다. 실제 vendor parser·PDF/.xls·UDT/cross-file 참조·현장 의미 PoV가 남아 전체 축은 partial이다.


## P3-C C 제한 add·multiply·divide

MP10/MP11에 [2.15.0 제한 scalar 산술](P3-C-BOUNDED-ARITHMETIC.md)의 작성·저장·가상 preview·독립 수신/파일 승인 경로를 추가한다. add는 같은 허용 선형 단위, multiply는 한쪽이 1, divide는 분모 1 또는 같은 단위의 비율만 허용한다. 0 분모·34자리 half-even 근사·최종 cast 손실·missing/bad/stale/skew를 검증한다. 일반 식/eval·복합 차원/역단위·온도 delta·cross-graph·현장 의미/계수 정답은 미완료이므로 전체 패턴 지원 축은 partial을 유지한다. 기존 current/gap/planned baseline fixture를 일괄 성공으로 바꾸지 않는다.


## P6 registry 전체 의미 일관성

[2.16 카탈로그 보고서](P6-SEMANTIC-CATALOG.md)는 기존 접근/매핑 패턴을 변경하지 않고 모든 보존 릴리스의 URI·scalar/구조 서명을 비교한다. 이름 기반 자동 병합은 없으며 타입·단위·역할·중첩 구성 충돌을 승인/발행에서 거부한다. 전역 범위는 구성된 하나의 registry다. cross-registry 연합·실제 의미 정답·URI 관리 정책·대량 수용은 미완료다.


## P3-C D 제한 수식 작성 subset

MP10/MP11의 [제한 작성 문법](P3-C-BOUNDED-EXPRESSION.md)은 직접 소스 참조와 기존 유한 연산을 2.15 canonical DAG로 변환한다. 원문/컴파일/저장 이력·단위 검사·가상 preview·기존 수신 승인 경로를 연결한다. 일반 식/eval·일반 차원 분석·복합/역단위·온도 delta·cross-graph·실제 의미 정답 PoV는 남아 전체 패턴 축은 partial이다. 기존 fixture current/gap/planned 기록은 수정하지 않는다.


### P3-C E 제한 literal 작성

Bare decimal은 무차원, quantity(숫자, 단위)는 명시적 단위 상수다. compiler 1.1 작성→기존 2.7 constant/2.15 graph, 생성 근거·값 변경 새 ID·구 이력 보존·충돌 거부를 지원한다. 기존 1.0 원문 규칙 유지. [상세](P3-C-EXPRESSION-LITERALS.md). 조건식/차원 추론/온도 delta/native 바이너리 저장·현장 단위 정답 PoV는 별도다.


### P3-F C bounded cross-value-graph endpoint

[2.17 설계](P3-F-CROSS-GRAPH.md)와 [지원 overlay](../fixtures/cross-graph/support.json)는 같은 설비의 scalar graph 결과를 ID/버전/노드로 재사용한다. source/node/외부 graph 입력과 selector 후보·재귀 근거·순환/깊이 검증·SQLite/preview·독립 Bifrost 검증/발행을 지원한다. 기존 current/gap/planned 역사 기준선은 유지한다. 다른 설비·동적 참조·배열 전체/native 구조 결과·현장 의미 정답은 미완료다.


P3-F C 수용: [실측 결과](verification/CROSS-GRAPH-RESULTS.md) — Python·fixture1,056, Java156, 격리 연계58 통과. 기존 기준선 planned를 일괄 승격하지 않는다.
