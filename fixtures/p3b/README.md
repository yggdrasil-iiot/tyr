# P3-B fixture

가상 바이트·Typed 샘플만 사용하며 실제 장치 통신은 없다.

- cases.json: 독립 기대값 50건. source/transform/member override는 평가기를 시험하기 위한 가상 시나리오다. 결과·품질·진단 코드·필수 trace 단계를 명시한다.
- workspace.json: 두 모터 low/high 그래프와 별도 검사 레코드의 ASCII·BCD16·S7 날짜·native bit 작성 예제.
- scripts/test_p3b.py: oracle, 2.1 Schema/SQLite 왕복, 기존 Schema 보존, 네 PLC 속도 수렴, read-only snapshot/API 경계 검증.

미리보기의 Float32/64 Typed 샘플은 실제 IEEE 폭으로 양자화한다. 기존 P1의 단순 Decimal Typed harness와 정밀도 가정이 다르며, 입력/변환 손실을 숨기지 않는다.

[계약·사용 안내](../../docs/P3-B-PREVIEW.md). fixture 기대값을 평가기 코드로 자동 생성하지 않는다. snapshot과 원본 byte HEX는 trace에 보존하며 preview 입력은 사용자 SQLite에 저장하지 않는다.
