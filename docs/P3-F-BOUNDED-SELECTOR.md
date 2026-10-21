# P3-F · bounded selector

2026-10-17. 파일과 가상 입력의 정준 모델 검증이다. 실제 장치 통신과 운영 적용은 제외한다.

## 계약과 경계

기존 44개 Schema는 보존하고 common/value-graph 2.5.0을 추가했다. source-definition, target-instance, mapping-set, preview-scenario와 workspaceVersion 2.0.0은 재사용한다. 같은 설비 안의 서로 다른 PLC profile/논리 연결도 참조할 수 있다. 후보의 디코딩 타입·단위는 같아야 한다.

Týr가 정의와 근거를 작성한다. Mímir의 관측, Bifrost의 승인·발행, Muninn의 실행 계약은 확대하지 않는다. preview의 출처 비교는 승인된 런타임 감사 이력이 아니다.

## 노드 모델

- op: bounded-selector.
- inputs.index: 직접 source 참조. 디코딩 타입 Int16/UInt16/Int32/UInt32/Int64, known unit 1.
- inputs.candidate0 ~ candidate31: 1~32개 연속 번호의 직접 scalar source 참조. 순서가 의미를 가지며 0-based다. 이름이 아닌 id/version을 저장한다. 중복 참조는 허용한다.
- inputs.previousIndex: 선택적인 직접 정수 source. 명시적으로 제공한 가상 이전 선택 비교값이다. 숨겨진 서버 상태나 지난 preview 결과를 읽지 않는다.
- outOfRange: reject 또는 default-candidate. 후자는 후보 안의 defaultCandidate 정수를 반드시 지정한다. reject에서는 해당 필드를 허용하지 않는다.
- valueType/unit/evidenceRefs: 모든 후보와 타입·단위 일치. 인덱스와 모든 가능한 후보의 근거를 포함한다. 소속 설비·참조·연속 번호·기본 후보 범위는 저장 시 검증한다.

기본값은 literal 0이 아니라 명시한 후보 소스의 값이다. 인덱스가 음수 또는 후보 수 이상일 때만 적용한다. 인덱스 디코딩 실패·소수·결측·bad 품질 및 선택된 후보의 결측·bad 품질은 다른 후보로 대체하지 않는다. 자동 failover는 제외한다.

이번 후보와 index는 직접 source만 받는다. 후보별 정규화 graph의 결과 선택은 후속 범위다. selector 출력에는 기존 그래프와 단위·스케일·cast를 연결할 수 있다. 이미 공학값인 후보는 이중 변환을 막기 위해 보수적으로 검사한다.

## 평가와 출처

index 디코딩 → 범위/정책 판단 → 선택 후보 디코딩 → 후속 그래프/변환/cast 순서다. static lineage에는 가능한 후보 전체를 보존한다. runtime requiredSources에는 실제 사용한 index, 선택 후보, 지정한 previousIndex와 후속 연산 입력만 포함한다. 미선택 후보의 결측·bad·stale는 결과를 오염시키지 않는다. 미선택 후보의 정적 계약 오류는 저장을 차단한다.

P3-D가 있으면 가상 value로 필요한 출처를 결정하는 내부 probe 후 해당 출처만 freshness/skew/quality 검사한다. probe 수치 결과는 공개하지 않으며 검사 통과 후 다시 순수 평가한다. bad이면 최종 결과는 null이다. 출처 결정 메타데이터만 selector-resolution으로 남기고 selectionValueValidated=false를 표시하며 probe 수치 trace는 노출하지 않는다. previousIndex를 지정했다면 그 입력의 결측·품질·시간도 검사한다. 실제 동시 수집·원자성은 보장하지 않는다.

selections와 graph:bounded-selector trace:
requestedIndex, selectedIndex, sourceRef(id/version), candidateCount, defaultUsed, previousSourceRef, sourceChanged.

sourceChanged는 값이 아닌 실제 sourceRef 비교다. 같은 값이라도 다른 출처면 true, 다른 인덱스가 동일 sourceRef를 가리키면 false, 이전 입력이 없으면 null이다. previousIndex에도 같은 범위 정책을 적용한다. default-used/source-changed는 경고이며 품질은 uncertain이다. 정의 자체의 변경은 workspace hash로 식별한다. 실행 간 자동 이력 저장은 후속 과제다.

## 화면과 SQLite

05에서 유한 후보 연산, 현재/이전 인덱스 소스, 순서 있는 후보 ID 목록, 범위 초과 정책·기본 후보·타입·단위를 작성한다. 06에서 객체 프로퍼티에 연결한다. 09에서 입력 바이트/typed value와 시각·품질, 선택된 출처·기본 후보 사용·출처 변경·단계별 trace를 확인한다.

graph 2.5 JSON은 기존 SQLite CAS 저장·조회 경로로 보존한다. 테이블 변경이나 기존 데이터의 암묵적 재작성은 필요 없다. P3-D 시나리오는 index/previousIndex/후보 가상 입력을 보존하며 재개방·hash 고정·stale 차단을 재사용한다. 미리보기는 DB를 변경하지 않는다.

검증 DB는 build/p3e-ui/editor.sqlite3 revision 27을 backup으로 복제한 build/p3f-ui/editor.sqlite3이다. 원본은 수정하지 않는다. fixture 추가 revision 28, 화면 기본 후보 1 저장 revision 29, 선택 압력 member 정정·시간 정책 적용 revision 30.

## 재사용·신규·검증

재사용: 네 PLC scalar decoder, 객체 식별·매핑, 후속 변환/cast, 시간·품질/시나리오, SQLite JSON/CAS/HTTP 보호와 근거 hash/locator.
신규: graph 2.5 selector 계약·검증, 선택 후보 평가와 requiredSources, 이전 인덱스 기반 provenance 비교, 편집 필드·출처 요약, fixture/test_p3f.py.

7개 독립 정답은 첫/마지막 후보·동일 출처·출처 변경·범위 초과·기본 후보를 검증한다. 자동 검증은 음수·소수·32개 한도, 번호/타입/단위/참조, 선택/미선택 결측과 품질·freshness, 기본 후보 결측, 동일 값의 출처 변경, alias, 순수성, SQLite/CAS와 HTTP 저장·재조회·무변경 preview를 포함한다.

MP13은 bounded subset 부분 지원이다. 임의/동적 주소식, 후보 그래프, 동적 배열 인덱스, vendor multiplex importer, 실행 간 lineage 감사 이력은 후속 범위다.


후속 P3-F B의 같은 그래프 내 유한 DAG 후보 확장은 [2.13 설계](P3-F-GRAPH-CANDIDATES.md)를 따른다. 이 문서의 2.5 소스 전용 범위와 수용 기록은 역사적 기준으로 유지한다.
