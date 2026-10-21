# P3-C 독립 검증 자료

workspace.json은 같은 설비의 필터 3개와 raw UInt16 압력 입력을 정의한다. 모두 가상 자료이며 현장 제품 지원 인증이 아니다.

| 객체 | 입력과 해석 | 기대 차압 |
|---|---|---|
| filter-direct | 96 00 = 150 kPa, 64 00 = 100 kPa | 50 kPa |
| filter-scaled | dc 05 = 1500, ×0.1 = 150 kPa; 하류 100 kPa | 50 kPa |
| filter-mixed | 96 00 = 150, ×0.01 = 1.5 bar → 150 kPa; 하류 100 kPa | 50 kPa |

HEX는 little-endian 16-bit다. cases.json의 18개 기대값은 수동으로 기입한 독립 oracle이며 구현식에서 생성하지 않는다. 음수/0·한쪽 결측·잘못된 HEX·단위 불일치·unknown·Boolean·중복 engineering 스케일·출력 단위 불일치·Double/Int32 손실·exact 중단·overflow를 포함한다. change는 테스트에서 기본 workspace를 명시적으로 변형하는 조건이다. 잘못된 정의의 정적 거부와 방어적 가상 평가를 각각 시험한다.

실행: python -B scripts/test_p3c.py --report docs/verification/p3c-validation.json

기존 fixtures/mapping-patterns의 pressure-difference/multi-input-missing/graph-cycle은 과거 계획 명세로 유지하며 이번 실행 fixture와 대응시킨다. planned를 성공 건수로 계산하지 않는다. source→graph→target.member 출처와 근거, 기존 Schema 보존, SQLite 왕복·오류 저장 원자성·revision 충돌·read-only HTTP preview도 시험한다. 실제 장치 통신은 제외한다.
