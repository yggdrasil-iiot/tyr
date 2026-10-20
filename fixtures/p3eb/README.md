# P3-E B 논리 구조·구조 배열 fixture

workspace.json은 네 PLC profile, 16개 scalar/기존 고정 배열 소스, 4개 그래프, 하나의 2.12 논리 모델, 4개 target과 40개 전체 경로 바인딩을 담는다. 같은 말단 이름·semanticId를 여러 구조와 배열 요소에서 재사용한다. MELSEC 실제값·목표값·상태 워드는 각각 D1000·D2000·D3000의 1 word이며, modules의 압력 값은 기존 고정 scalar 배열의 별도 요소에 매핑한다. 실제 장치의 배치를 검증한 자료가 아니다.

- samples.json: 기존 P3-E A의 Float32 버퍼/typed slots와 scalar 150/180/상태 워드 3. 바이트/slot 좌표와 논리 객체 좌표를 자동 동치로 취급하지 않는다.
- expected.json: 수작업으로 지정한 네 profile 공통 객체 정답. process 실제/목표/편차는 150/180/-30, root 상태 false, modules는 [100/110/true, 220/210/true].
- nested-model.json / nested-expected.json: 음수 하한 racks[-1..0] 안의 rank-2 slots[1..2,3..4], 총 8말단의 독립 논리 조립 정답.
- negative-cases.json: 전체 경로/인덱스/shape 오류의 독립 mutation과 기대 rule. test_p3eb.py에서 실행한다.

같은 index/전체 경로 중복과 다른 index의 같은 이름을 구분한다. 미매핑 초안은 보존하지만 승인/발행은 거부하며, bad/결측 시 전체 result null과 진단 partialResult를 구분한다. 기존 fixture 파일은 수정하지 않는다.

[설계](../../docs/P3-E-LOGICAL-STRUCTURES.md)
