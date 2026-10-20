# P4-A B fixture 안내

fixtures/p4ab는 현장 자료가 아닌 합성 자료다. 기존 네 프로파일을 한 설비에서 재사용한다. 설정 records에 AB symbol·S7-1500 OPC UA·S7-300 DB·MELSEC, 두 template instance, alias, 미해석 주소식과 opaque vendor metadata를 담는다.

- base-request.json / original-workspace.json: parser 2.6 원본 보존과 미해석.
- resolve-review.json / exclude-review.json / reviewed-workspace.json: D{POINTER}를 명시적 D4000 읽기 정의로 해결하고 vendor metadata를 비소스로 분류한다. 원본 관측/오류는 남는다.
- local-workspace.json: AB label 로컬 수정, OPC UA 주소와 note 로컬 수정.
- incoming-request.json: row reorder·AB 주소 변경·다른 OPC UA 주소 변경·DB 제거·template override·alias 갱신·새 소스.
- merge-plan.json / merge-choices.json / merged-workspace.json / expected.json: 별도 지정한 비교 분류·안정된 ID·비충돌 합성·충돌 ours 선택·제거 보존 정답.
- publication-workspace.json: 정의 완료를 명시한 오프라인 발행 fixture.
- legacy-closed-workspace.json: 기존 2.6 import-batch의 닫힌 문서가 새 Bifrost에서도 승인/발행되는 호환성 fixture.
- digest-cases.json: Unicode·emoji·null·boolean·정규화 수치의 언어 독립 hash 정답.

scripts/p4ab/make_fixtures.py는 원본/기본 비교 fixture를 재현한다. scripts/test_p4ab.py는 이를 읽고 retain·제거 후 재등장·XLSX 수식의 명시적 수동 해결·보존한 미해석 새 배치 해결 후 병합·원본/이력 조작·SQLite/CAS/HTTP 원자성을 추가 검증한다.

Bifrost core/src/test/resources/mapping-fixtures/p4ab 및 p4ab-legacy에는 JSON/원본 파일만 전달한다. 구현 코드를 공유하지 않는다. Java는 자체 검증과 승인/파일 발행을 수행한다. scripts/p4ab/run.ps1은 network none 컨테이너에서 브라우저·SQLite·Python·Java 수용 경로를 검증한다. 반복 실행을 합산해 테스트 수를 부풀리지 않는다.

단위/타입 검사와 가상 fixture 정답은 현장 주소·의미·비소스 분류의 정확성 인증이 아니다. 장치 통신·외부 SQL·쓰기 실행과 현장 PoV는 별도다.
