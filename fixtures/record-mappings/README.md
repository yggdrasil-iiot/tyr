# 가상 레코드·결과 집합 fixture

실제 DB/SQL/장치 접속 없이 작성한 합성 자료이다. workspace.json은 같은2.19 템플릿으로 설비 A의 배열과 B의 특정 키 객체를 정의한다. snapshot.json은 역순2행, Pa 입력·스케일·Boolean·미정의 열을 포함한다. oracle.json은 명목 공학값과 정확한 최종 Double cast 값을 분리한다. pressure-*-preview.json에는 단계/정밀도 손실/원본 보존이 있다. static-projections.json은 독립 Java와 비교할 canonical 생성물 정답이다.

bundle/에는2.20 레코드 정의·템플릿·의미 모델·선언 근거만 있으며 가상 행은 없다. Python test_record_mappings.py의 negative 사례는0/1/N, 범위 초과, 복합/중복/누락 키, NULL/default, 타입/단위, 품질/시각, 버전 pin/fork, CAS·재개방·기존 SHA 보존을 검사한다.

재생성: scripts/generate_records.py. 기존 bundle 출력은 덮어쓰지 않으므로 먼저 명시적 경로를 확인하여 이전 합성 출력을 별도 build 폴더로 보존한 뒤 실행한다. 실제 자료 정답이나 query 실행 지원으로 해석하지 않는다.
