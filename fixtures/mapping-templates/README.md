# 매핑 템플릿 합성 fixture

workspace.json: 하나의 pressure-kit 템플릿 1.0.0/1.1.0, 네 PLC 적용본과 OPC UA 명시적 갱신 이력. before-update.json은 새 버전이 있지만 모든 적용본이 1.0.0을 유지한 상태다. cases.json은 독립 숫자 정답이다. bundle은 네 적용 매핑의 self-contained wire 패키지이며 Bifrost test resources에 별도 데이터 사본을 둔다.

AB/OPC UA typed UInt16과 DB/MELSEC little-endian bytes UInt16을 소스별로 디코딩한 후 같은 슬롯에 연결한다. 값150/50/2에서 quotient는 AB50, UA갱신100, DB50, MELSEC50이다. 코드/구현 공유는 없다. 생성기 scripts/generate_mapping_templates.py는 빈 출력 디렉터리에서만 실행한다.

이 자료는 합성 정답이며 native 배치/실제 현장 의미나 작업시간의 PoV를 대체하지 않는다.

views-workspace.json / views-bundle: AB의 Boolean alarm alias 템플릿을 MELSEC에 적용한다. 입력 슬롯1개가 부모 워드→bit view→alias 소스3개를 고정한다. 부모 워드 00 80 HEX에서 true이며 부모의 정의 변경이나 누락을 거부한다. 기존 already-engineered 단계와 직접 슬롯에 없는 부모 근거의 보존을 검증한다.
