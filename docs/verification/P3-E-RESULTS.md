# P3-E 고정 배열 검증 결과

2026-10-17. 고정 scalar 배열의 형상·저장 범위·고정 인덱스·요소별 의미 매핑과 가상 평가를 구현했다. 실제 장치 통신은 제외한다.

| 검증 | 결과 | 증거 |
|---|---|---|
| P3-E 수용 | 55/55, 독립 oracle 23건 | [수용·해시](p3e-validation.json) |
| P3-D 시간·품질 | 62/62 | [회귀](p3d-p3e-regression.json) |
| P3-C 파생값 | 41/41 | [회귀](p3c-p3e-regression.json) |
| P3-B 디코딩 | 66/66 | [회귀](p3b-p3e-regression.json) |
| P3-A SQLite/API | 37/37 | [회귀](p3a-workspace-p3e-regression.json) |
| P3-A 계약 | 52/52 | [회귀](p3a-contract-p3e-regression.json) |
| P2 | 24/24 | [회귀](p2-p3e-regression.json) |
| P1 | 105/105 | [회귀](p1-p3e-regression.json) |
| 기존 패턴 baseline | current 14/14, gap 8/8, planned 34 유지 | [회귀](pattern-p3e-regression.json) |

기존 회귀 합계는 387건이다. planned·gap 재현을 제품 지원 성공으로 계산하지 않는다. 각 실행의 코드/fixture 해시는 개별 보고서에 기록한다.

## 독립 검증

네 접근 방식의 같은 2×3 Float32 값 100/110/120/패딩/200/210/220을 수동 HEX/Typed 자료로 정의했다. AB/UA는 lower [0,0], strides [4,1] element이고 DB는 lower [1,10]/strides [16,4] byte, MELSEC은 lower [1,10]/strides [8,2] word16이다. 첫/마지막 요소가 100/220 kPa로 수렴한다.

하한/상한 포함·exclusive 상한 초과·rank/분수 인덱스·선택 null·짧은 버퍼·잘못된 HEX·타입/비유한 값·중첩 배열 금지·stride 중첩·저장 범위 부족·Int32 좌표·column-major·rank3를 검증했다. 전체 배열의 암묵적 scalar cast와 legacy 작성/파일 게이트의 배열 오해를 차단한다.

같은 배열의 서로 다른 두 요소를 선택해 220−100=120을 계산하고 입력/원래 access를 변경하지 않는 것을 확인했다. identity로 형상을 전달하는 경로, 원래 decoder/cast 손실 정책, P3-D 시간·품질과 2.4 Typed 시나리오 저장을 검증했다.

SQLite 왕복·요소 인덱스 수정·오류 저장 원자성·CAS·읽기 전용 주소 probe/preview·DB 파일 해시 불변·외부 Origin/stale revision 거부·장치 route 부재도 확인했다. 기존 Schema 39개는 바이트 그대로 보존했다.

## 브라우저와 작성본

기존 build/p3a-ui/editor.sqlite3 revision20을 SQLite backup으로 build/p3e-ui/editor.sqlite3에 복제했다. 원래 DB body/revision을 보존했다. 현재 http://127.0.0.1:59772/는 복제본을 제공한다.

- 복제본 20→21: 네 배열 소스/의미 모델/채널 객체 8개/그래프/매핑을 추가했다.
- 21→22→23: MELSEC 배열 range.endExclusive를 7016으로 편집·저장·재조회했다. 첫 요소 wordCount=2, shape [2,3], lower [1,10], strides [8,2]는 유지한다. 뒤쪽 패딩을 포함해 버퍼가 32 bytes다.
- 읽기 전용 검사: [2,12] → offset12 word16/24bytes → D7012, [2,13] → array.index-range. 검사 중 revision은 23이었다.
- 23→24: array-ui-selected에 FixedArray identity 노드를 작성했다. 24→25: array-element selected를 추가했다. [2,13] 저장은 거부됐고 revision24를 유지했으며 [2,12]를 저장한 뒤 25가 됐다.
- 25→26: MELSEC last 객체의 actual-pressure를 새 selected 노드에 연결하고 시간·품질 정책을 저장했다. 32바이트 가상 입력에서 D7012의 Float32 220 → Double 220 kPa를 확인했다.
- 26→27: AB last 객체의 시간·품질 정책을 저장했다. Typed slots ["100","110","120",null,"200","210","220"]의 [1,2] → slot6 → 220 kPa를 확인했다.
- array-ab-last-good 2.4 시나리오를 별도 저장했다. 화면 새로고침 뒤 불러와 같은 형상·인덱스·가상 시각·220을 재현했다. 미리보기와 시나리오 저장은 작성본 revision27을 유지했다.

최종 복제본에는 소스45/의미 모델4/대상17/그래프11/매핑17과 시나리오3개가 있다. 기존 시나리오 2개는 복제본의 작성본 변경으로 stale이며 원래 DB에 보존돼 있다. 새 배열 시나리오 1개는 현재 hash에 일치한다. [화면](p3e-preview.png), [SQLite/재현 관측](p3e-ui-observation.json).

2.4 Schema 5종·fixed_arrays·array-element·배열 폼/범위 probe/Typed slots 입력을 추가했다. 기존 source/graph/target·디코더·cast·P3-D 정책/시나리오·SQLite JSON/CAS를 재사용했다. 그래프 연산 전환 시 새 입력 필드 생성과 읽기 전용 probe의 수정 상태 처리를 보완했다.

rank1~3/256요소/4096 buffer의 고정 scalar 배열 A만 완료했다. native 구조·중첩·구조체 배열·canonical 배열 출력·동적 인덱스·vendor native array 수집은 후속이다. MP06 전체는 partial이며 실제 통신·snapshot·승인은 보장하지 않는다.

[계약·사용](../P3-E-FIXED-ARRAYS.md) · [계획](../../MVP-PLAN.md).
