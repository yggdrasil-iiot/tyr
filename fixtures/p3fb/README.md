# P3-F B fixture

가상 MELSEC 압력 정의와 기존 P3-F 근거를 재사용한다. D1000 raw 1000 ×0.1 → Decimal 100 kPa, D2000 1 bar → Decimal 100 kPa, 두 정규화 값의 차압 → Decimal 0 kPa를 유한 후보로 선택한다. 같은 값·다른 경로와 여러 주소를 사용하는 후보를 구분한다. 하드웨어 통신 자료나 vendor 인증 fixture가 아니다.

- workspace.json / samples.json: 값만 검증하는 세 후보.
- timed-workspace.json / timed-samples.json / evaluation.json: 선택 경로 시간·품질.
- cases.json: 별도 지정한 결과·선택 source·출처 변경 정답.
- support.json: 기존 matrix를 덮어쓰지 않는 지원 overlay.
- scripts/test_p3fb.py: 계약·negative 변이·선택 격리·중첩·손실·시나리오·SQLite/CAS.
- scripts/p3fb/run.ps1: network none 브라우저·Python·Java 수용. 원래 SQLite는 읽기 전용 backup하고 별도 DB에 수행.

독립 Java 수신 자료는 Bifrost core/src/test/resources/mapping-fixtures/p3fb의 JSON/근거 파일이다. 구현 코드를 공유하지 않는다. 네 접근 profile의 기존 fixture는 회귀 검증으로 유지하며 이번 통과를 vendor native selector 지원으로 계산하지 않는다.
