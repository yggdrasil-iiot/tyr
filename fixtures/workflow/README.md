# 독립 결과 스키마·작업 흐름 합성 fixture

before.json은 설비·소스·공통 의미만 있고 recordMappings/mappingTemplates가 없는 workspace다. definition.json은 단독 저장할 result-schema-definition 편집 계약이다. request.json은 독립 스키마를 바로 사용해 공통 PLC/상수/외부 입력과 레코드별 target을 배열로 연결하는 기존2.22 요청이다.

scripts/test_workflow.py는 매핑/템플릿 없는 스키마 저장, 키/형태/버전·CAS·불변 이력, 기존 inline 충돌, SQLite 테이블/읽기 무변경, 사용하지 않은 카탈로그 추가 전후 wire 패키지 바이트 동일, 기존 파일 SHA를 확인한다.

scripts/workflow/run.ps1 -UiOnly는 다섯 단계의 실제 Chromium 작성·개정·가상 검증·독립 Java 승인/발행을 network-none 환경에서 검증한다. -PythonOnly는 신규/기존 전체 회귀, -WorkflowOnly는 신규 검증만 실행한다. 실제 현장 자료·장치 통신·외부 SQL·쓰기 실행은 사용하지 않는다.
