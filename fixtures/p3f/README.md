# P3-F fixtures

자료는 모두 가상이다. workspace.json: D1000(100 kPa), D2000(200 kPa) 후보와 D4000 현재 인덱스, D4001 명시적 이전 인덱스. 의미는 선택 압력으로 차압과 구분한다.

samples.json은 little-endian UInt16 바이트다. cases.json은 독립 작성한 7개 기대값/진단이다. timed-workspace.json과 scenario.json은 P3-D와 결합한 0 → 1 출처 변경을 재현한다.

실행: python -B scripts/test_p3f.py --report docs/verification/p3f-validation.json

[상세 설계](../../docs/P3-F-BOUNDED-SELECTOR.md).
