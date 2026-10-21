# P3-C 검증 결과

2026-10-17. 다중 입력 차압 정의와 입력별 정규화의 작성·저장·검증·가상 preview를 구현했다. 실제 장치 통신은 제외한다.

| 검증 | 결과 | 증거 |
|---|---|---|
| P3-C | 41/41, 독립 값 oracle 18건 | [수용·해시](p3c-validation.json) |
| P3-B | 66/66 | [회귀](p3b-p3c-regression.json) |
| P3-A SQLite/API | 37/37 | [회귀](p3a-workspace-p3c-regression.json) |
| P3-A 계약 | 52/52 | [회귀](p3a-contract-p3c-regression.json) |
| P2 | 24/24 | [회귀](p2-p3c-regression.json) |
| P1 | 105/105 | [회귀](p1-p3c-regression.json) |
| 기존 패턴 baseline | current 14/14, gap 8/8, planned 34 유지 | [회귀](pattern-p3c-regression.json) |

P3-C에는 direct 150−100, raw 1500×0.1−100, raw 150×0.01 bar→150 kPa−100의 수렴, 음수/0, 결측, HEX 오류, 단위/Boolean/출력 오류, cast 정밀도/반올림/overflow, 이미 공학값 중복 스케일이 포함된다. 네 PLC 접근 프로필의 차압 50 kPa 수렴, 세 개의 서로 다른 입력을 연결한 150−20−10=120도 시험했다.

스키마 meta, 이전 31개 Schema 바이트 보존, 포트 누락/추가·순환·참조 버전·근거 lineage, SQLite 재조회·수정·오류 저장 원자성·revision 충돌, HTTP read-only preview·결측 bad/null·오래된 revision 409·장치 route 부재를 확인했다. preview 전후 DB body/revision/파일 해시가 같다.

## 브라우저 확인과 로컬 상태

주 DB build/p3a-ui/editor.sqlite3의 revision 13을 build/p3c-ui/pre-p3c.sqlite3으로 먼저 백업했다. 기존 정의를 유지하고 가상 필터 3객체·압력 3소스·모델·그래프·매핑을 추가했다.

- revision 14→15: 혼합 단위 그래프의 offset을 화면에서 0.00으로 편집·저장했다.
- 15→16: 새 pressure-ui 그래프를 작성했다. left=pressure-up, right=pressure-down, Decimal/kPa.
- 16→17: filter-direct 프로퍼티를 새 그래프 결과에 연결해 저장했다.
- 17→18: 압력 의미 모델을 화면에서 저장했다. 재로드 후 schemaVersion 2.2와 참조를 확인했다.
- 혼합 입력의 150 raw→1.50 bar→150.00 kPa, 하류 100 kPa, 차압 50.00 Decimal→50 Double을 확인했다. 카드에 단위와 left/right 값, 상세 trace에 입력별 타입·단위·정의·근거가 나온다.
- 하류 입력을 비우면 sample.missing→graph.input-invalid→mapping.input-invalid, bad/null을 확인했다.
- raw 1×0.1−0→Double exact에서 loss.precision와 value.inexact를 확인했다.
- 가상 입력 변경 시 이전 결과를 지우며 preview 중 revision은 18로 유지했다. 이후 정상 50 kPa 화면으로 복원했다.

[화면](p3c-preview.png), [관측 기록](p3c-ui-observation.json). 로컬 서버는 http://127.0.0.1:59772/ 이다.

기존 source/semantic 폼·그래프 입력/출처·디코더·매핑 변환·SQLite JSON/CAS를 재사용했다. 새 2.2 Schema 5종·압력 단위·3개 op·그래프 편집 필드·검증/fixture를 추가했다. MP10/MP11 전체는 임의 식·비선형·일반 차원 분석·시간/품질 조립이 남아 partial이다. 온도 delta, sqrt/clamp, Bifrost 승인·Muninn 실행은 후속이다.

[계약과 사용법](../P3-C-DERIVED.md) · [MVP 계획](../../MVP-PLAN.md).
