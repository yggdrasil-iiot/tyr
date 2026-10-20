# P7 평가 준비용 합성 fixture

- fixtures/p3eb/workspace.json과 samples.json을 재사용한다. 네 접근 profile, 네 설비/객체, 구조 배열을 포함한 40개 말단이다. 기존 파일을 변경하지 않는다.
- fixtures/p7-evaluation/oracle.json: 실제/목표/편차/상태와 두 구조 배열 요소의 10항목 × 4 profile. calibration AB 10, evaluation UA/DB 20, heldout MELSEC 10이다. 기대값은 150, 180, -30, false, 100/110/true, 220/210/true로 별도 명시했다. 기대 의미·역할·단위도 명시했다.
- 정의 SHA는 기존 fixture의 회귀 snapshot pin이다. 이를 현장 의미의 독립 정답으로 주장하지 않는다. scripts/pov_evaluation.py가 계산한 값으로 수치 oracle를 생성하지 않았다.
- expected.json: 집계 독립 정답. 평가용 시간은 합성 수작업 1000초/도구 800초, 20.00%다. 조정용 큰 절감률을 평가용에 합산하지 않으며 heldout 시간은 미측정이다. 숫자는 측정 공식 시험용이며 현장 실적이 아니다.
- loss-workspace.json/loss-oracle.json: 150 × 0.001을 Double로 cast할 때의 정확한 binary64 값과 loss.precision을 명시한다. 손실 진단이 빠지면 불일치다.
- test_p7_evaluation.py는 누락·중복 객체 경로·동일 의미 충돌·주소/graph 변경·틀린 값·Boolean 혼동·정답 없는 부분 범위·시간 누락/중복·독립성 미선언·legacy 보존·SQLite/HTTP 읽기 전용을 검사한다.

실제 현장 파일·담당자 정답·native PLC 배치·시간 절감 검증을 완료하지 않았다. 장치 통신·외부 SQL·쓰기 실행은 없다.
