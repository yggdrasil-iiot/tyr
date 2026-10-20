# P4-E 공통 입력을 레코드 배열에 적용

## 범위와 사용 예

가상 DB 결과의 각 레코드에 공통 PLC 실제값·상수·외부 값을 붙여 객체 배열을 만든다. 예를 들어 A-001의 목표값900과 A-002의 목표값950에 공통 PLC 원시값1200(×0.1), 기준압력100, 외부값101, 라인코드LINE-A를 적용하면 목표값90/95만 다르고 실제값120/기준100/외부101/라인코드는 같은 두 객체가 나온다.

실제 DB 조회·PLC 취득·외부 SQL·쓰기·운영 활성화는 구현하지 않는다. 정의와 가상 입력은 별도로 저장한다. 합성 자료 성공은 현장 PoV 또는 vendor native 배치 인증이 아니다.

## 계약과 기존 호환성

- opt-in `record-mapping/2.22.0`을 기존 workspace의 선택 `recordMappings`에 저장한다. 기존2.20 record-only,2.21 one-object field source 및 기존 템플릿 계약은 그대로 유지한다. 2.21 source의 단일 객체 제한을 완화하지 않는다.
- `bindings`는 원본 행 필드→슬롯: fieldId/nullPolicy/defaultValue. `commonBindings`는 공통 소스→슬롯: sourceRef{id,version,sha256}. 두 집합은 중복 없이 템플릿 전체 슬롯을 정확히 채운다.
- `commonSources`는 실제 선언의 고정 snapshot이다. top-level source와 byte-canonical 내용이 같아야 하며, 같은ID/버전의 재정의를 저장/발행 이력에서 차단한다. wire는 source ID/버전을 고정한다. 현재 workspace는 source ID별1개 정의를 유지하므로, 고정 소스를 바꾸려면 새 source ID를 만들고 기존 정의를 보존한 채 새 매핑 버전에서 명시적으로 연결한다. 동일 source ID의 여러 버전을 동시에 보관하는 inventory는 이번에 추가하지 않는다.
- 템플릿2.19는 모델·memberPath·값 그래프·단위/스케일/cast를 고정한다. 생성 시 프로퍼티별 직접 행 필드/공통 소스를 작성하고, 재사용 시 기존 템플릿의 그래프를 포함한 입력 슬롯을 연결한다. 템플릿/매핑 선행 버전과 정준 SHA가 고정된다.
- 공통 입력은 같은 설비의 ready/read 직접 스칼라 PLC·상수·솔루션 태그·외부 값이다. 이번 버전은 공통 source view/fixedArray/recordField를 거부한다. 임의 그래프를 공통 소스 자체로 넣는 대신 고정 템플릿 그래프의 슬롯으로 구성한다. 설비 간 결합은 제외한다.
- 결과 스키마의 typed String/Boolean/Int32/Double, 1~4개 필수 String 복합 키, 선택 all/key, 최대64개 행, canonical-key-utf8 정렬과 unknownFields 보존/거부를 재사용한다. 숫자는 정밀도 보존을 위해 문자열이다. 묵시적인 첫 행·마지막 행·잘라내기는 없다.

## 공통 프레임의 적용

`commonPolicy.mode=single-virtual-frame`: 호출자가 제공한 가상 공통 입력을 복사해 모든 행에 같은 값/시각/품질/출처로 적용한다. 재조회하거나 행마다 다른 값을 주입하지 않는다. 해시가 전체 결과와 각 행에 함께 남는다. 디코딩·정준 변환은 부작용 없는 기존 계산기를 사용한다.

상수는 정의에서 읽고 가상 입력으로 덮어쓰지 않는다. 나머지 공통 입력은 value/sourceTimestamp/serverTimestamp/quality/sequence DataValue envelope가 필요하다. sequence는 null만 허용한다. DB 시각·품질은 결과 집합에서 가져오며 공통 envelope로 덮어쓰지 않는다.

전체 프레임에 maxAgeMs·maxSkewMs·uncertainInput 정책을 적용한다. DB 시각과 모든 비상수 공통 입력의 source 시각 사이 skew도 검증한다. 미래/결측/잘못된 시각·bad 품질은 전체 오류이다. uncertain은 명시적으로 전파 또는 거부한다. 0건이어도 공통 입력 디코딩과 공통 입력만 사용하는 변환을 확인한다. 템플릿 자체 temporalPolicy를 중복 적용하지 않으며, 이 버전은 해당 템플릿 대신 프레임 정책을 요구한다.

`atomicSnapshot=false`: 이 검사는 선언된 가상 시각의 정합성이다. 실제 PLC 동시 취득, DB 트랜잭션 원자성, 여러 provider 사이 동시성 보장이 아니다.

## 오류와 손실

| 구분 | 처리 |
|---|---|
| 스키마/핀/슬롯/단위/타입 계약 오류 | 저장·발행 거부 |
| 공통 입력 결측/디코딩/변환·시각/품질 오류 | 행 정책과 무관하게 전체 result=null |
| 키 누락/NULL/빈 값/중복, 선택 건수 초과 | 전체 차단; 중복 키는 선택 전 전체 입력에서 검증 |
| 선택된 행의 필수 필드/타입/NULL/변환 오류 | reject-all은 전체 차단; omit-invalid는 해당 키의 행 제외 |
| NULL 기본값 | nullable 필드의 명시적 기본값만 허용; 경고 및 uncertain |
| 단위/스케일/cast 손실 | 기존 trace/losses 보존, uncertain; 자동 은폐하지 않음 |
| 미정의 필드 | 결과 스키마에 따라 해당 행 오류 또는 원본 별도 보존 |

JSON 숫자·객체/BLOB 등 허용 wire primitive 밖의 행 값은 snapshot schema 오류로 요청 전체를 거부한다. 허용 primitive 안에서 발생한 필드 타입/범위·변환 오류는 행 정책을 적용한다.

기본 rowErrorPolicy는 reject-all이다. omit-invalid는 명시적으로 선택하고 불변 매핑 버전에 저장한다. 전체 result는 성공한 행만 담고 records/omittedRecords에는 모든 선택 행의 키·입력행 번호·품질·오류·부분 진단을 남긴다. 일부/전부 행을 제외한 배열은 valid=true,quality=uncertain이다. 모든 선택 행이 실패해 []가 되어도 제외 이력을 남긴다. zeroPolicy는 선택 결과 자체가0건인 경우에 적용한다. partialResults는 성공 행의 진단 자료이며 reject-all의 대체 출력으로 사용하지 않는다. 선택되지 않은 행의 필드 변환은 수행하지 않지만 키/중복은 전체에서 검증한다.

## 작업자 화면과 저장

22에서 20의 결과 스키마, 의미 모델, 설비를 선택하고 각 프로퍼티에 행 필드/공통 소스를 연결한다. 단위·주소·타입을 표시하고 단위 변환/스케일/NULL 정책을 작성한다. 고정 템플릿 재사용 시 슬롯을 연결한다. 비교→계약 검증→확인한 정의와 신규 템플릿 원자 저장 순서이며 입력 변경 시 저장을 다시 검증한다.

DB 결과 집합 입력창1개와 각 공통 입력창1개만 표시한다. 상수는 입력창을 만들지 않는다. 공통 입력 결측을 체크해 검증하고 결측 시나리오도 복원할 수 있다. 2건 예제, 키별 결과/오류/부분값/정확한 cast와 손실, 공통 시각/품질 trace, 입력 SHA를 확인한다. 기존19 변경 영향/명시적 개정,18 URI 영향,13 승인·릴리스 화면으로 이어진다.

workspace JSON과 기존 SQLite CAS를 재사용한다. 새 row/version은 append-only이고 과거 정의 변경/삭제를 거부한다. 가상 입력만 명시 저장하면 기존 opt-in record_scenarios 테이블에 broadcast-scenario2.22를 저장한다. 새 테이블/자동 DDL/마이그레이션이 없고 scenarioRevision으로 충돌을 방지한다. 재조회 시 workspaceRevision/hash와 mapping pin을 유지하며 이전 정의의 시나리오는 화면에서 자동 재생하지 않는다. 기존20 화면에는2.20 매핑만 표시해 공통 입력을 누락한 미리보기/편집을 막는다.

## Bifrost 경계

제출에는2.22 recipe, 고정 템플릿/이력/의미 모델, 실제 공통 source 정의와 근거 closure를 포함한다. 가상 행·공통 샘플·시나리오는 제외한다. Python은 정준 template application과 row-field source의 정의 수준 projection을 만든다. Bifrost Java는 별도 코드로 같은 projection과 슬롯/핀/출력/이력/URI를 검증하며 승인·발행·복구 시 재검사한다. 양 앱은 wire/schema/fixture만 공유한다. Java는 Python을 호출하지 않는다. 승인은 기존 두 확인자 Ed25519 서명/불변 릴리스 경로를 사용한다. 실행/활성화는 수행하지 않는다.

## 현장 PoV 및 남은 범위

실제 DB 키/NULL/선택/스케일의 정답, PLC와 조회 시점의 업무상 허용 age/skew, 실패 행을 제외해도 되는지의 소비자 계약, 작업자 작성·검토 시간과 잘못된 연결 빈도, vendor/provider export를 별도 현장 PoV로 남긴다. native DB 타입 전체·실제 SQL/커넥터·join/group/집계·무한 스트림·다중 결과 집합·설비 간 결합·공통 view/배열 자동 적응은 이번 완료 조건에 포함하지 않는다.


[실측 수용 검증 결과](verification/RECORD-BROADCAST-RESULTS.md): Python·fixture1,195, 독립 Java237, network-none 통합36 통과.
