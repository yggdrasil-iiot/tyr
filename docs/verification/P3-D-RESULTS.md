# P3-D 검증 결과

2026-10-17. 가상 입력별 시간·품질·sequence 정책과 별도 시나리오 저장/재현을 구현했다. 실제 장치 통신은 제외한다.

| 검증 | 결과 | 증거 |
|---|---|---|
| P3-D 수용 | 62/62, 독립 oracle 32건 포함 | [수용·해시](p3d-validation.json) |
| P3-C 파생값 | 41/41 | [회귀](p3c-p3d-regression.json) |
| P3-B 디코딩 | 66/66 | [회귀](p3b-p3d-regression.json) |
| P3-A SQLite/API | 37/37 | [회귀](p3a-workspace-p3d-regression.json) |
| P3-A 계약 | 52/52 | [회귀](p3a-contract-p3d-regression.json) |
| P2 | 24/24 | [회귀](p2-p3d-regression.json) |
| P1 | 105/105 | [회귀](p1-p3d-regression.json) |
| 기존 패턴 baseline | current 14/14, gap 8/8, planned 34 유지 | [회귀](pattern-p3d-regression.json) |

기존 회귀 합계는 325건이다. planned나 gap 재현을 제품 지원 성공으로 계산하지 않는다.

## 독립 기대값과 저장 경계

기준 10:00:00Z, 상류 150 kPa/09:59:59.500Z, 하류 100 kPa/09:59:59.550Z → age 500/450ms, skew 50ms, 차압 50 kPa다. age 1000ms/skew 100ms 경계는 포함하고 0.001ms 초과·미래 입력·누락/잘못된 시각을 차단한다. source/server 기준·offset 정규화·fallback 금지·uncertain 전파/거부·bad/결측·trigger sequence 일치/불일치·unused bad 격리·암묵적 good 금지를 검증했다.

Typed/바이트 혼합, source-only·low/high·파생 그래프 lineage, uncertain와 수치 정밀도 손실의 복합 전파, 이전 Schema 36개 보존, Schema/정책 오류·SQLite 원자성/CAS·시나리오 hash/ref·stale 보존·동일 내용 재저장·외부 Origin 거부를 검증했다.

preview는 입력·기준 시각·작성본을 변경하지 않는다. DB body/revision·시나리오·DB 파일 해시가 평가 전후 같은 것을 검사했다. 기존 DB에 테이블을 추가해도 기존 body/revision은 유지된다. 시나리오 저장은 작성본 revision을 올리지 않는다. 실제 wall clock을 평가 기준으로 사용하지 않는다.

## 브라우저·주 SQLite 확인

build/p3a-ui/editor.sqlite3의 revision 18을 build/p3d-ui/pre-p3d.sqlite3으로 먼저 백업했다.

- 18→19: pressure-direct-mapping에 sourceTimestamp 기준, age 1000/skew 100ms, uncertain 전파, latest 정책을 화면에서 저장했다.
- 정상 차압 50 kPa/age 500·450/skew 50을 계산하고 filter-time-good 시나리오를 별도 저장·불러왔다. 작성본 revision은 19였다.
- 입력 bad→quality.bad-input, 평가 기준 +2초→age 2500·2450/time.stale-input, 하류 시각 변경→skew 400/time.skew-exceeded를 화면에서 확인했다. 오류 시 수치 계산을 수행하지 않았다.
- 19→20: pressure-mixed-mapping에 trigger-sequence 정책을 화면에서 저장했다.
- 이전 filter-time-good은 작성본 변경됨으로 표시되고 불러오기를 차단했다. 이전 입력은 SQLite에 보존했다.
- trigger 42와 입력 sequence 42/41은 assembly.sequence-mismatch로 bad/null이었다. 42/42와 uncertain 입력은 값 50/최종 uncertain으로 전파했다.
- 정상 42/42·age 500/450ms·skew 50ms를 filter-trigger-good으로 저장했다. 화면을 다시 로드한 뒤 시나리오를 불러와 같은 50 kPa를 재현했다.
- 최종 작성본 revision 20, 시나리오 2개(이전 stale 1개, 현재 1개)다. 입력·시각·품질·sequence/조립 상태→디코딩→linear→단위 변환→subtract→cast 단계를 표시한다. [화면](p3d-preview.png), [관측](p3d-ui-observation.json).

새 2.3 Schema 3종, 시간·품질 preflight, 정책/가상 입력/시나리오 UI, SQLite preview_scenarios와 API를 추가했다. 그래프·값 평가·workspace JSON/CAS는 재사용했다.

단일 바인딩의 가상 묶음 검증만 완료했다. MP16 전체는 partial이다. 실제 시각·OPC 품질, target 전체 원자 조립, 연속 latch/중복/역순·trigger/ack·통신·승인은 후속이다. trigger sequence 일치와 skew 한도 통과를 실제 동시 snapshot의 증거로 해석하지 않는다.

[계약·사용](../P3-D-TIME-QUALITY.md) · [계획](../../MVP-PLAN.md).
