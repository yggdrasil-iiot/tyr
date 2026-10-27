# P3-F C 그래프 간 scalar 결과 재사용

## 목적과 범위

같은 설비에서 이미 정의한 차압·단위 변환·조합 결과를 여러 후속 그래프와 객체 매핑에서 재사용한다. 그래프를 복제하거나 저장 시 평탄화하지 않는다. 논리 그래프 정의와 가상 입력만 사용하며 실제 장치 통신·외부 SQL·쓰기 실행·runtime 활성화는 제외한다. 실제 의미/단위/계수 정답과 vendor native/export 검증은 현장 PoV로 남긴다.

## 새 wire 계약과 호환성

2.17.0 value-graph/common을 추가한다. 기존 모든 canonical 파일은 보존한다. 새로운 node input은 `{"kind":"graph","graphRef":{"id":"shared-ab","version":"1.0.0"},"nodeId":"delta"}`이며 source/node와 함께 사용할 수 있다. ID·정의 버전·결과 노드를 정확히 고정한다. 참조는 같은 proposal 안의 정의로만 해석하고 실제 정의 바이트는 manifest SHA와 불변 릴리스가 동결한다. latest/자동 버전 추적은 없다. 기존 producer 그래프의 2.0~2.15 결과도 새 consumer에서 참조할 수 있다. 동일 equipmentInstanceId와 scalar 결과만 허용한다. FixedArray 전체 결과의 외부 전달은 거부하며 필요한 요소를 producer에서 scalar로 먼저 선택한다.

기존 mapping-set의 graph valueRef, workspaceVersion 2.0, SQLite 테이블/CAS, 1.0/1.1 수식 recipe를 유지한다. 17 제한 수식 문법은 변경하지 않으며 이번 재사용 작성은 05 그래프 화면에서 한다. 기존 수식 그래프를 05에서 수정하면 기존 원문 pin과 달라 stale로 표시한다. 구 receiver가 2.17을 모르면 schema capability 오류로 발행을 거부한다.

## 정적 의존성 검증

Tyr (Týr)와 Bifrost가 각자 wire 정의를 해석한다. 공유 구현 라이브러리나 상호 코드 의존을 추가하지 않는다. consumer를 producer보다 먼저 저장/제출해도 graph dependency topological order로 타입·단위·근거를 검증한다.

모든 graph endpoint에서 참조 그래프/정확한 버전/노드 존재, 설비 경계, scalar 여부를 검사한다. 자기 참조·두 그래프·다중 그래프 순환을 차단한다. 참조한 노드 경로가 직접 순환하지 않아도 graph 정의끼리 상호 의존하면 거부한다. 선택되지 않은 selector 후보 및 다른 미사용 노드도 정적 검증 대상이다. 기존 로컬 node cycle 검사도 유지한다.

외부 참조가 존재하는 정의 집합은 총 8192 노드, 그래프 의존 깊이 32, source부터 결과까지 노드 경로 깊이 128로 제한한다. 기존 그래프당 64 노드 및 패키지/작성본 크기 제한을 유지한다. 하나의 미리보기 평가 안에서 같은 DAG 결과를 여러 번 참조하면 (graph ID, version, node ID) 단위로 평가를 캐시하며 동일 이름의 다른 그래프 노드를 혼동하지 않는다. 타입·단위와 원본 source/evidence closure를 경계 너머로 전달하고 기존 연산 검증을 재사용한다.

## 작성·저장·미리보기

05 입력 선택 목록에 같은 설비의 다른 그래프 결과를 버전·노드·타입·단위와 함께 제공한다. selector 후보 추가에도 같은 핸들을 사용한다. 그래프 간 순환 경로는 화면에서 먼저 표시하고, 조작된 HTTP 요청도 backend가 별도로 차단한다. 외부 참조를 쓴 그래프는 2.17로 저장한다. 06 매핑은 재귀 source closure에서 근거를 수집한다.

SQLite는 참조를 그대로 workspace JSON에 저장한다. 새 테이블·기존 행 재작성·자동 migration은 없다. 참조된 그래프 제거/버전 변경/순환 도입은 저장을 거부하고 이전 revision을 유지한다. 여러 정의를 변경할 때 기존 원자 workspace CAS를 사용한다.

09는 원본 가상 입력과 producer/consumer 계산 단계, graph:reference의 정확한 graphRef/nodeId를 표시한다. 실제 샘플 입력은 재귀 말단 PLC/솔루션/외부 소스이며 상수는 기존 정책대로 제외한다. bad/결측/freshness/skew/정밀도·최종 cast 손실을 기존 경로로 평가한다. selector는 모든 후보를 정적으로 검사하되 실제 계산/시간·품질은 선택 경로만 평가한다. 선택·이전 후보의 source closure와 정의 fingerprint에 외부 그래프 노드 정의를 포함한다. 시계 동기화·원자 snapshot을 보장하지 않는다.

## 변경 검토·승인·발행

기존 change-review의 graphRef 재귀 의존 해시와 P7 평가 정의 closure를 재사용한다. upstream 그래프 정의가 바뀌면 consumer의 의존성 pin이 달라진다. 제출은 참조된 graph 전체·재귀 source·artifact를 포함하고 원래 graph 경계를 유지한다. Bifrost가 독립적으로 순환/참조/타입/단위/근거를 재검사한 후 기존 두 키 승인·불변 파일 발행을 수행한다. producer 최신값으로 자동 대체하거나 Tyr 식을 Java에서 실행하지 않는다.

## 합성 수용과 남은 범위

네 PLC profile에서 actual150/target50/gain2이면 shared delta100, consumer sum200/scaled200/quotient50/ratio1, final wrapper50이다. fixture graph 순서를 consumer-first로 뒤집어도 같은 결과를 요구한다. diamond 중복 참조는 producer 계산 한 번, 참조 trace 두 번이다. 순환/없는 ID·버전·노드/다른 설비/타입·단위/근거/배열 전체/구 schema/깊이·크기 초과를 거부한다. SQLite 왕복·원본 DB 보존·HTTP/UI 오류·가상 preview·구 receiver 거부·실제 Java 승인/발행을 검증한다.

설비 간 재사용 템플릿, 동적 그래프/주소 해석, native 구조 bulk 결과, 운영 활성화는 이번 범위가 아니다. 현장 의미 동등성·허용 오차·운전 정책·검토 시간·재사용성은 실제 익명화 자료와 독립 담당자 정답이 필요하다.
