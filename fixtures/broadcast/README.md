# 합성 공통 입력·레코드 배열 fixture

before/request는22 화면 작성과 동일한 입력이다. workspace는 CAS 저장 결과, snapshot은 서로 다른 두 행과 원본 미정의 열, common-samples는 단 한 번 제공한 PLC bytes와 외부 typed 값이다. 상수100/LINE-A는 정의에만 있다.

정답은 A-001→{actual:120,target:90,baseline:100,external:101,line_code:LINE-A}, A-002→target95이고 나머지 공통 값은 같다. 숫자는 문자열이다. preview는 키/입력행/해시/변환 trace를 보존한다. static-projection은 Java의 독립 정준 생성물 비교용 데이터이다. bundle에는 가상 값 없이 정의·템플릿·소스·근거만 포함한다.

`scripts/test_broadcast.py`는 행/공통 오류, NULL/default, freshness/skew, cast 손실, 그래프 슬롯 혼합, SQLite 재개방/CAS/불변 버전, 기존 파일 SHA를 확인한다. `scripts/broadcast/run.ps1`은 network-none 브라우저·Python·SQLite·Java 승인·발행 검증이다. 현장 자료·장치·SQL 실행은 없다.
