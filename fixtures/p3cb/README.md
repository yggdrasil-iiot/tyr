# P3-C B 가상 검증 자료

- workspace.json: 기존 MELSEC UInt16 byte 접근 두 소스와 sqrt/clamp 그래프. 가상 무차원 의미이며 압력 측정으로 해석하지 않는다. 기존 source/evidence ID는 P3-C 합성 자료를 재사용한다.
- cases.json: 수작업으로 명시한 7개 정상·경계·근사·clipping oracle. evaluator로 기대값을 생성하지 않는다.
- negative-cases.json: 음수·경계 역전·차원 단위·고정 precision 위반의 mutation 명세. scripts/test_p3cb.py의 대응 테스트에서 실행한다.
- temporal-workspace.json: sqrt(up) − clamp(down) 조합과 기존 P3-D temporalPolicy. 결측·bad·freshness·skew 실패가 새 노드 실행 전에 전파되는지 검사한다.

최종 cast 손실과 graph 계산의 손실을 구분한다. 구버전 graph 계약의 새 op 거부, 같은 경계 허용, 단위 변환 후 clamp, 근거·참조·순환 및 기존 SQLite 행·CAS·preview 무변경도 검사한다. 네 PLC 통신 지원이나 vendor 실측을 주장하지 않는다. 기존 네 PLC 접근 회귀는 별도로 유지한다.

[설계](../../docs/P3-C-BOUNDED-MATH.md)
