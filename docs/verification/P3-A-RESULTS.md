# P3-A 검증 결과

2026-10-17. 실제 장치 통신 제외.

- P3-A 수용: 52/52. [상세 결과·해시](p3a-validation.json).
- P1 회귀: 105/105. [결과](p1-p3a-regression.json).
- P2 회귀: 24/24. [결과](p2-p3a-regression.json).
- 기존 패턴 게이트: current 14/14, gap 8/8, planned 34 pending. [결과](pattern-matrix-p3a-regression.json).
- 같은 설비의 두 객체, 4바인딩, 6소스: [파일 검증·lineage](p3a-two-motors.json).

## 확인한 내용

motor-a의 D1000=1(low), D2000=2(high)는 131073으로 조합된다. motor-b의 D1100=3, D2100=4는 262147이다. low/high를 바꾼 결과 65538, UInt32 경계 4294967295, 결측·음수·범위 초과·Boolean 입력도 검증했다. 노드·입력 선언 순서는 결과를 바꾸지 않는다.

오류 fixture 32건으로 순환·참조 버전·타입/단위·설비 혼합·대상 중복·근거 누락·해시·미지원 op/path를 검증했다. label 변경으로 객체 ID가 바뀌지 않으며 mapping-set이 달라도 같은 대상의 중복을 거부한다.

네 PLC의 기존 32개 바인딩은 명시적 객체 ID assignment로 임시 파일 패키지에 이전·재로드했다. 소스·의미·근거·원문 바이트, 기존 변환·단위·근거와 입력 원본을 보존했다. 기존 1.0/1.1 Schema 24개는 baseline 해시와 일치한다.

P3-A/P1/패턴 게이트는 socket을 차단했다. P2 회귀는 local HTTP loopback과 임시 SQLite만 사용했다. 사용자 DB·프런트엔드·다른 앱 코드는 변경하지 않았다. 기존 P2 서버는 미지원 버전을 검증 오류로 거부하도록 메시지 처리를 보완했다.

## 후속 경계

이번 구현은 2.0 파일 계약·CLI 검증과 제한된 typed-word harness다. UI/SQLite 2.0 작성은 P3-A 후속, raw bytes decoder·최종 cast의 실제 overflow preview는 P3-B, 파생식은 P3-C, 시간/품질은 P3-D다. Bifrost 승인·release·Muninn 실행과 실제 PLC 통신은 없다. 기존 planned fixture를 제품 지원 통과로 승격하지 않았다.

[계약 상세](../P3-A-CONTRACT.md) · [fixture](../../fixtures/p3a/README.md) · [계획](../../MVP-PLAN.md).
