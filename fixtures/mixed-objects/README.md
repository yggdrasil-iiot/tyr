# 혼합 객체 합성 fixture

before.json:2.20 record 정의와 PLC·상수·외부 값 및 공통 의미 모델. request.json:프로퍼티별 출처/변환 선언. workspace.json:2.21 record-field source와 기존2.19 template/application의 원자 저장 결과. samples.json:가상 PLC HEX·record result-set·외부 typed 값. oracle.json:고정 기대값(actual120,target95,baseline100,external101,line_code LINE-A). preview.json:출처/키/필드/변환/cast trace. bundle/:고정 record/template/evidence closure이며 가상 입력은 포함하지 않는다.

생성기 scripts/generate_mixed_objects.py는 기존 출력 디렉터리를 덮어쓰지 않는다. 재생성 전 정확한 경로를 확인하여 이전 생성물을 build 하위에 보존한다. Python test_mixed_objects.py와 독립 Java MappingMixedObjectsTest가 계약·오류·pin·재사용·SQLite·서명 발행을 검증한다. 실제 장치/DB 정답이나 운영 연결 인증이 아니다.
