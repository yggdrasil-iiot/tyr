# P1 정준 모델 검증 결과

실행일: 2026년 10월 17일 Asia/Seoul
실행 시각 UTC: 2026-10-16T23:43:03.168387+00:00
결과: **93/93 통과, 실패 0**, 종료 코드 0

## 실행과 추적

```text
python scripts/validate_contracts.py --deny-network --report docs/verification/p1-validation.json
```

[전체 결과](p1-validation.json)는 12개 스키마, 두 검증기와 모든 fixture 입력의 SHA-256을 기록한다. 실행 후 저장 파일의 해시를 다시 대조했다. [정준 평가 결과](governance-assessment.json)는 해당 보고서의 governanceAssessment를 별도 파일로 추출한 것이다.

기존 63개 항목에 새 진단 스키마 검사 1개와 거버넌스 검증 29개를 추가했다. 네 정준 값 4개, 네 표현 수렴 1개, 변경 시나리오 12개, 의미 공존·설비 보존 2개, 투영 손실 2개, 수치 손실·경계 5개, 진단 계약 2개, 패키지 의미 ID 충돌 거부 1개다.

## 확인한 결과

- MELSEC Int32/0.1, S7-300 DB Float32, AB Logix 심볼 Float32, S7-1500 OPC UA Float64를 실제 파일 정의로 해석해 모두 1234.5 rpm과 동일한 정준 의미 선언으로 수렴했다.
- 표시 이름이 같은 actual-speed와 target-speed는 다른 semanticId/role로 공존했다. 네 설비 인스턴스도 구분했다.
- 같은 semanticId의 role·단위·타입 충돌을 탐지했다. 패키지 내 role 충돌은 semantic.identity-conflict로 거부했다.
- Int64→Double 정밀도 손실, 정수 exact 변환 거부, half-even 반올림 손실 보고와 overflow 거부를 확인했다.
- legacy UDT 부분집합 투영에서 접근·원시 표현·변환·단위·role·근거·식별 문맥 손실 목록을 보고했다.
- 의미·role·단위·타입, 스케일, 바이트/워드 해석, 주소, 범위, 연결 문맥, 근거 변경을 분류하고 재검토가 필요함을 표시했다. 표시 이름 변경은 presentation으로 분리했다.
- 기존 참조·해시·검토 무결성과 오류 거부 시험도 통과했다.

## 완료 판정과 해석 범위

[정준 모델 검증 기준](../P1-GOVERNANCE-CRITERIA.md)의 G01~G09에 따라 P0·P1을 완료한다. 실제 장치 통신은 이번 완료 조건에서 제외했다. 실제 현장 파일·제품 버전·검토자 확보는 P4/P7의 대표성·실무 수용성 검증으로 이어진다.

이 결과는 선언된 의미의 일관성·수렴·구분·손실·변경을 검증한다. 의미 ID의 업무적 타당성을 이름만으로 추론하는 기능은 없다. 가상 자료가 현장의 모든 예외를 대표한다는 뜻도 아니다.

비교 fixture는 변경 분류를 격리하는 메모리 개정본이고 제출·승인 가능한 새 release가 아니다. 정준 평가 결과는 실제 Bifrost 승인이나 Muninn의 독립 소비 성공을 의미하지 않는다. UI·제품 importer·일반 preview·승인 연계는 P2 이후에 구현한다. 개별 review 해시와 전이적 의존성 재검토의 구분도 기준 문서에 기록했다.
