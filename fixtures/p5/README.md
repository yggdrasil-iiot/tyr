# P5 독립 변경·검토 fixture

실제품/현장 export가 아닌 가상 자료다. before.json은 P4-B 혼합 scalar 예제를 동결하고 읽기 linear factor=1을 명시했다. after.json은 주소 D1000→D1001과 읽기 factor=1→2를 바꾼 독립 개정본이다.

cases.json의 17개 기대 분류·전이 영향은 비교 엔진으로 생성하지 않았다. 주소, endian, 표시 이름, 원문 표기, 개념/role/단위, 수동 근거, 상수, SQL 원문, 읽기·쓰기 scale, 연결 프로파일, 객체 stable ID를 각각 확인한다. 일부 부정/불일치 개정은 순수 diff 엔진의 입력 진단 시험이며 저장 게이트 통과를 의미하지 않는다.

추가 시험은 기존 P3-D/E/F의 실제 유효 fixture에서 시간 정책·고정 배열 indices·selector 후보를 변경해 비교한다. template/alias 원문 변화는 해석 정의 변화와 구분하고 importRef 의존 영향으로 검사한다. 주소·scale 변경(A04/A05), 명시 view와 중복 접근 표시(A07), revision/hash 충돌(A16), 검토 불변성·재개방·전이 무효화·근거 위조·실행 경계도 검사한다.

실행: python -B scripts/test_p5.py --report docs/verification/p5-validation.json
실제 장치 통신·SQL·쓰기 실행은 없다.
