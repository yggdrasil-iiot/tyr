# P3-A 화면·SQLite 검증 결과

2026-10-17. 실제 장치 통신 제외. 객체·값 그래프 작성/편집/저장/조회와 기존 DB 마이그레이션을 구현했다.

| 검증 | 결과 | 증거 |
|---|---|---|
| 새 SQLite·HTTP 경계 | 37/37 | [결과·코드 해시](p3a-workspace-validation.json) |
| P3-A 계약 회귀 | 52/52 | [결과](p3a-workspace-contract-regression.json) |
| 기존 P2 | 24/24 | [결과](p2-v2-ui-regression.json) |
| 기존 P1 | 105/105 | [결과](p1-workspace-regression.json) |
| 기존 패턴 카탈로그 | current 14/14, gap 8/8, planned 34 유지 | [결과](pattern-workspace-regression.json) |

Storage 검증은 단독 DB와 로컬 HTTP 서버가 함께 실행되는 두 환경에서 수행했다. 기존 패턴 카탈로그는 1.x 기준 기록이며 새 2.0 제품 기능의 증거는 위 37건과 아래 브라우저 확인이다.

## 브라우저에서 직접 확인한 내용

- 기존 32신호 예제의 SQLite 복사본에 모터용 가상 소스 6개를 추가하고, 08 이전 화면에서 네 기존 mapping-set의 객체 ID를 명시해 이전했다.
- 이전 전 revision 5의 DB 백업과 이전 revision 6의 ID 배정 기록을 화면에서 확인했다.
- 같은 line-a-motor-melsec에 motor-a/motor-b를 직접 등록했다.
- motor-a D1000(low)/D2000(high) → counter → result(identity), motor-b D1100(low)/D2100(high) 그래프를 화면에서 작성·저장했다.
- 두 객체의 actual-speed 직접 매핑과 cycle-count 그래프 결과 매핑을 저장했다.
- 저장된 그래프를 다시 열고 순환을 만들었을 때 graph.cycle 오류가 표시되며 revision 12가 유지됐다. 정상 입력으로 복원 후 revision 13으로 저장했다.
- 서버를 재시작하고 페이지를 다시 열어 객체 6개·그래프 2개·매핑 6개가 복원됨을 확인했다.
- 의미 모델·설비 필터로 두 객체의 프로퍼티, low/high 주소 역할, 단위·변환과 이름 관계를 조회했다.

[화면](p3a-workspace.png) · [DB/백업 관측 기록](p3a-ui-observation.json).

## 저장 경계

참조·순환·타입·단위·설비 혼합·중복 대상·잘못된 입력은 원자적으로 거부한다. 초안의 미매핑 프로퍼티와 의미 제약 진단은 저장 후 표시한다. 백업 실패/잘못된 assignment/동시 revision 충돌/중복 이전은 DB 상태를 바꾸지 않는다. 일반 PUT의 우회 업그레이드·다운그레이드도 차단한다.

기존 접근/의미 폼·단위/스케일 편집·동의어/동명이의어 비교를 재사용했다. 1.x workspace는 명시적 이전 전까지 기존 경로로 읽고 저장한다. 기존 schema 1.0/1.1은 유지한다.

실제 원본 build/p2/realistic.sqlite3는 유지했으며 현재 브라우저는 build/p3a-ui/editor.sqlite3를 사용한다. 실행 URL은 http://127.0.0.1:59772 이다. 다른 앱 코드·장치 통신·현장 적용·승인/릴리스는 추가하지 않았다.

P3-B raw bytes decoder/일반 값 preview, P3-C 파생식, P3-D 시간/품질 정책은 후속이다. low/high와 identity 이외의 그래프 op는 아직 미지원이다.

[사용·이전 안내](../P3-A-WORKSPACE.md) · [MVP 계획](../../MVP-PLAN.md).
