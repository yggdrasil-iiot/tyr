# P4-B synthetic mixed sources

workspace.json은 PLC UInt16 압력 150 kPa, 정의 상수 100 kPa, 솔루션 가상 압력 80 kPa, 외부 가상 기준 70 kPa, String/Boolean 상수, read-write 솔루션 setpoint와 write-only PLC 목적지를 정의한다.

cases.json의 독립 읽기 기대값 9개에는 PLC−상수=50 kPa가 포함된다. samples.json에는 상수 샘플이 없다. SQL 원문은 access.expression에 줄바꿈까지 보존하며 실행하지 않는다.

별도 쓰기 정의는 semantic setpoint → PLC(UInt16, ×10/cast)와 semantic hmi-setpoint → solution-tag(Double)를 선언한다. 쓰기 결과 값·SQL 결과는 fixture 정답으로 꾸며 넣지 않는다. 모두 execution excluded다.

실행: python -B scripts/test_p4b.py --report docs/verification/p4b-validation.json

[설계·제한](../../docs/P4-B-MIXED-SOURCES.md).
