# 매핑 패턴 정리 검증 결과

기준일: 2026-10-17. 실제 장치 통신 제외. 지원 매트릭스와 fixture 명세·검증기를 추가했으며 제품 서버·프런트엔드·wire 계약·사용자 저장 DB는 변경하지 않았다.

| 검증 | 결과 | 해석 |
|---|---|---|
| 지원 카탈로그 | 18항목 / 56사례 | 16개 매핑 + 2개 공통 요구. ID·근거·코드 위치·case schema·경로·패턴별 사례 연결 검증 |
| current | 14/14 | 현재 파일 계약·수동 작성 상태와 기존 evaluator 동작 확인 |
| gap-probe | 8/8 재현 | 현재 거부/누락을 예상대로 확인. 기능 지원 통과가 아님 |
| planned | 34 pending | 명세 envelope만 검증. 구현 통과로 계산하지 않음 |
| P1 회귀 | 105/105 | 현재 계약·정준화·손실·의미 변경 게이트 |
| P2 회귀 | 24/24 | 작성·저장·API·객체 매핑 회귀. 로컬 loopback 테스트만 사용 |

## 실행 증거

- [패턴 검증 JSON](pattern-matrix-validation.json): 사례별 actual/expect 및 SHA-256.
- [P1 회귀 JSON](p1-pattern-regression.json).
- [P2 회귀 JSON](p2-pattern-regression.json).
- 검증기: scripts/validate_pattern_matrix.py, scripts/validate_contracts.py, scripts/test_p2.py.

실행 명령:

```text
python scripts/validate_pattern_matrix.py --deny-network --report docs/verification/pattern-matrix-validation.json
python scripts/validate_contracts.py --deny-network --report docs/verification/p1-pattern-regression.json
python scripts/test_p2.py --report docs/verification/p2-pattern-regression.json
```

패턴 검증기는 임시 파일 bundle만 사용하고 socket 생성을 차단한다. P2 회귀는 기존 HTTP API의 로컬 loopback 및 임시 SQLite 시험을 포함한다. PLC browse/read/write나 외부 솔루션 실행은 없다. 새 UI 기능의 브라우저 검증은 이번 변경에 포함되지 않으며 기존 구현 상태를 평가했다.

## 확인한 경계

D1000/D2000/D3000 각 1워드→객체의 다른 프로퍼티, 다른 원문 이름→같은 의미, PV/Status 동명이의어, 단위 변환, 연속 2워드 순서, 같은 원시 word→상태/알람 fan-out은 현재 범위의 실행 사례다. 표현식 관측의 JSON 보존은 무손실 vendor importer 구현을 의미하지 않는다.

다중 입력 scalar, native 구조/배열 타입, 원시 문자열, native bit 주소 단위는 현재 계약이 거부한다. MELSEC M 영역에 word16 정의를 붙여도 source_rules가 차단하지 않는다. alias 순환은 P1에서 통과하지만 P2 편집기는 viewOf를 거부한다. 같은 설비의 동일 모델 두 객체는 현재 중복 대상 키에 걸린다. 이 항목을 정상 지원으로 감추지 않았다.

독립 객체 ID·다중 입력 모델·codec·템플릿 전개·시간/품질 조립 등은 [MVP 계획](../../MVP-PLAN.md)의 후속 구현이다. 실제 제품 export 및 현장 담당자 독립 정답 비교는 아직 수행하지 않았다.
