# P4-C 레코드·결과 집합 객체 매핑

2026-10-18 · 오프라인 작성 계약 2.20.0 · 실제 DB/장치 접속 없음

## 목적과 경계

조회 결과의 각 필드를 기존 정준 의미 모델의 프로퍼티로 변환하고, 키로 식별한 객체 하나 또는 객체 목록을 만든다. Tyr (Týr)는 결과 스키마·키·선택·건수 정책과 필드/템플릿 연결을 작성하고 가상 입력으로 검토한다. Bifrost는 독립 Java 구현으로 선언·생성된 정준 매핑·근거·이력을 검증하고 두 확인자의 서명 승인 및 불변 릴리스를 담당한다. Python 코드를 Java에서 호출하거나 공유하지 않는다.

DB 드라이버·외부 SQL 실행·조회 스케줄러·비밀번호·쓰기 실행은 없다. providerRef/valueKey는 선언이다. 쿼리 원문은 language=none/opaque/sql 메타데이터로 보존할 뿐 파싱·실행하지 않는다. 실제 커넥터가 나중에 계약에 맞는 결과를 제공하는 경계와 분리한다. Muninn/Mimir (Mímir)의 운영 수집·정준 모델 소유권을 대체하지 않는다.

## 계약

기존 2.0 workspace, 2.19 mapping-template/application, 2.7 external-value와 기존 의미·값 그래프 계약은 그대로 유지한다. 새 2.20 record-mapping, virtual-result-set, proposal/common만 추가한다. 구 bundle의 schemaVersion은 자동 변경하지 않는다. 새 record-mapping을 구 envelope로 제출하면 수신기가 거부한다.

- record-mapping: id/version, 소속 설비, templateRef의 canonical SHA와 버전, semanticDefinitionRef, previousMappingRef, 결과 스키마, slot→field bindings, 출력/선택 정책, 작성자·시각·사유·원본 선언 근거.
- 결과 스키마: providerRef/valueKey, 원문 query, fields, keyFields, unknownFields. 필드마다 ID·이름·Int32/Double/Boolean/String·단위·raw/already-engineered·nullable을 선언한다. 같은 schema ID/version의 내용이 다르면 거부한다.
- 식별: NULL이 아닌 String 키 1~4개, 키 값은 비어 있지 않은 최대256자. 복합 키 배열의 canonical JSON UTF-8 바이트 순서로 정렬한다. 입력 행 순서와 무관한 키 SHA를 만들며, SHA는 해당 결과 집합/매핑 안의 식별자이다. 서로 다른 설비의 전역 객체 URI로 오해하지 않는다.
- 필드 변환: 기존 템플릿의 값 그래프·단위 변환·스케일·최종 cast를 재사용한다. 필드 타입·단위·입력 단계가 슬롯 signature와 정확히 같아야 한다. PLC UInt16 슬롯을 DB Int32로 암묵 변환하지 않는다.
- NULL: nullable 선언과 바인딩의 reject/default를 분리한다. 기본값은 타입·범위를 검증하고 적용 시 warning과 원본 NULL을 trace에 남긴다. 비nullable 누락/NULL, 빈 키, 중복 키는 전체 결과를 거부한다.
- object: 전체 또는 명시적 복합 키 선택 후 정확히1건. 0건은 reject/null, 다건은 reject. 임의 first/last 선택은 없다.
- array: 0건 reject/empty, 다건 all, maxRows 1~64. 범위 초과를 잘라내지 않는다. 기존 FixedArray의 shape를 바꾸지 않는 bounded 객체 목록이며, 정준 element 모델을 참조한다.
- 선택 전 전체 입력의 타입·필수 필드·중복 키를 검사한다. 선택되지 않는 행도 잘못되면 실패한다. unknownFields=reject 또는 preserve: 보존 필드는 원본 SHA와 함께 별도 표시하며 의미 프로퍼티에 자동 연결하지 않는다.
- 제한: 결과 필드32, 가상 행64, 키4, 매핑 이력128개/ID당32버전. 일반 SQL 타입(BLOB/DATE/DECIMAL scale 등), join/group/집계/중첩 입력 JSON, 다중 결과 집합과 무한 스트림은 이번 범위 밖이다. 기존 논리 구조/고정 구조 배열 의미 모델의 leaf로는 매핑할 수 있다.

virtual-result-set은 스키마 ID/version/SHA, capturedAt, good/uncertain/bad 품질, flat rows를 가진다. 숫자는 십진수 문자열, Boolean은 JSON Boolean, NULL은 JSON null이다. JSON numeric을 거부해 입력 단계에서의 정밀도 손실을 숨기지 않는다. 가상 snapshot 시각은 offset이 있어야 하며 미래 시각을 거부한다. 기존 템플릿의 temporalPolicy가 있으면 같은 capturedAt/quality를 각 슬롯에 전달한다. 실제 DB 트랜잭션 일관성을 보증하지 않으며 atomicSnapshot=false이다.

## 미리보기와 실패 정책

입력 스키마/키 검사 → 키 선택·건수 검사 → 행별 nullable 정책 → 슬롯 외부 값으로 투영 → 기존 source/graph/단위·스케일/cast preview → 정준 객체 조립 순이다. 각 행의 키, 원본 행 번호, 바인딩 원본 값, 단계 trace, 변환 손실, partial 결과를 보여준다. 한 행이라도 error이면 최종 result=null, quality=bad이다. 경고/정밀도 손실은 uncertain으로 전파한다. 정상0건 object의 null은 valid=true/empty=true로 오류 null과 구분한다.

Double 123.45의 최종 IEEE binary64 값은 정확한 십진수 문자열 123.4500000000000028421709430404007434844970703125로 남는다. 화면의 ≈ 요약은 표시 편의이며 정확한 cast/손실은 상세에 보존한다. fixture oracle은 nominalEngineeringValues와 finalArray/finalObject를 구분한다.

## 템플릿·개정·승인

같은 템플릿을 설비 A의 배열 및 설비 B의 객체 선택에 재사용한다. 새 모델에서 필드 초안과 프로퍼티별 단위/스케일/cast를 작성하면 2.19 템플릿과 element 의미 모델을 함께 원자 저장한다. 이미 존재하는 템플릿은 정확한 버전/SHA로 연결한다. 정의/템플릿 개정은 새 버전과 이전 해시를 잇고 과거를 수정·삭제하지 않는다. 화면19의 레코드 사용처/정책 diff와 화면20의 고정 버전·새 버전 안내를 확인한 뒤 새 매핑 버전에서 명시적으로 선택한다.

발행 selector는 record:<id>@<version>이다. Bifrost bundle에는 record-mapping, 고정 템플릿/선행 이력, 실제 element 의미 모델, 선언 근거만 포함한다. 가상 행/시나리오와 행별 파생 소스/객체는 포함하지 않는다. 두 구현은 결정적으로 ephemeral external-value와 기존 정준 target/graph/mapping을 생성해 같은 정적 검증을 수행한다. Java/Python static-projections oracle로 생성물 일치를 검사한다.

의미 URI 개정/폐기 영향에는 record-<id>-<version>으로 표시되는 파생 mapping-set 사용처를 포함한다. 이 ID는 영향 분석용 정적 투영이며 실제 DB 행별 객체 inventory가 아니다. 폐기 URI는 기존 승인·발행 경로에서 차단한다. registry는 스트림 전체 record/schema/template 이력의 동명 버전 fork를 거부한다.

## SQLite·화면

workspace JSON에 optional recordMappings를 추가하고 기존 CAS/불변 이력 검증을 사용한다. 기존 DB 조회/미리보기만으로 DDL이나 기존 행을 변경하지 않는다. record_scenarios 테이블은 가상 입력을 명시적으로 저장할 때만 트랜잭션 안에서 생성하며 workspace revision과 별도 scenarioRevision CAS를 검사한다. 시나리오 저장은 workspace revision이나 승인 묶음을 변경하지 않는다.

20 화면: 결과 스키마/객체·배열 정책 → 필드 표/키/nullable → 기존 템플릿 또는 의미 모델에서 작성 → 선언 검증 후 저장 → 가상 레코드 표/JSON 붙여넣기/0건/예제/시나리오 → 행별 결과·손실·trace. 19에서 템플릿 변경 영향을, 18에서 URI 영향을, 13에서 별도 승인·발행 상태를 확인한다.

## 합성 수용과 현장 PoV

fixtures/record-mappings의 역순2행, 선택 객체, Pa→kPa, Int32 950×0.1→Double95, Boolean, 미정의 열 보존, 기본값과 부정 시나리오로 검증한다. 실제 Python SQLite·Chromium·독립 Java 서명 승인/발행은 외부 네트워크 없는 컨테이너에서 localhost로만 연결한다. 기존 fixture/schema SHA, 구 DB의 행/스키마, 기존 회귀 검사를 보존한다. 실행 결과는 verification/RECORD-MAPPINGS-RESULTS.md에 별도로 기록한다.

현장 PoV 미완료: 실제 결과 스키마의 버전/키 안정성·중복/NULL 의미·단위와 계수 정답·조회와 PLC 시각의 정합성·실제 provider metadata/export·작업자 작성/검토 시간 및 오류율·승인 권한/소비자 적용. 가상 검증 성공을 DB 연결 또는 현장 수용 인증으로 표시하지 않는다.
