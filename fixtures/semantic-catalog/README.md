# Semantic catalog 합성 검증

cases.json은 pressure.actual의 독립 scalar 서명과 상태별 기대값이다. 기존 p3eb 논리 구조·중첩/배열, p3cc 네 접근 프로파일과 산술 workspace, Bifrost valid/p3eb wire fixture를 재사용하며 기존 fixture 파일은 수정하지 않는다.

Python test_semantic_catalog.py: 작성본/registry 미조회·계약 일치·이름 변경·다른 URI·타입/단위/역할·중첩/shape 변경·작성본 내부 충돌·출처 경로·digest/schema 오류·SQLite/HTTP 읽기 경계.

Java MappingPublicationTest의 catalog* 사례: 두 실제 등록 키와 파일 registry에서 같은 URI 계약의 교차 스트림 재사용, 역할 충돌, 이름/URI 분리, 승인 이후 다른 스트림 발행, 중첩 말단 변경, unheaded 역사 보존, 손상 거부, 기존 충돌 역사 표시/차단, pending 복구. 현장 의미 정답이나 실제 vendor memory layout을 검증한 자료가 아니다.

scripts/catalog/run.ps1은 기존 작성/저장/산술 preview/서명 승인/파일 발행 경로와 새 카탈로그 화면을 network=none 컨테이너에서 실행한다. 실제 장치 통신·외부 SQL·쓰기 실행은 없다.
