# 제한 수식 합성 fixture

기존 p3cc의 네 접근 정의·12 소스·4 객체·16 매핑을 복사하고 profile별 `([actual] - [target]) / [gain]`을 2.15 그래프로 컴파일했다. 각 quotient 말단은 새 `expr-result`를 명시적으로 참조한다. 나머지 원래 binding은 유지한다. 이것은 별도 합성 계산 정의이며 기존 실제 의미 정답과의 동등성을 주장하지 않는다.

cases.json의 독립 정답: actual=150 kPa, target=50 kPa, gain=2 → 50 kPa. 1/3의 34자리 half-even 결과도 별도로 고정한다. 우선순위/괄호/좌결합·clamp/linear/sqrt·형식/범위/단위 거부·정적 컴파일과 런타임 0 분모/손실을 구분한다.

scripts/test_expression.py는 문법·입력 제한·view 부모 읽기 준비·근거/출처·원자적 저장/rollback·lazy SQLite 테이블·수식 이력·stale/명시적 재컴파일·HTTP revision/origin을 검증한다. scripts/expression/run.ps1은 17 작성 화면→기존 06 매핑/09 preview→기존 Java CLI 수신 검사·두 키 승인/발행→카탈로그·평가 경로를 OS network=none에서 시험한다. Bifrost 코드·JAR·canonical 계약은 수정하지 않는다.

실제 현장 의미·단위/계수·운전 허용 범위·검토 시간과 vendor native/export 검증은 별도 PoV다. 장치 통신·외부 SQL·쓰기 실행은 제외한다.
