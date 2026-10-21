# P4-B · 혼합 소스와 읽기·쓰기 정의

2026-10-17. 실제 장치 통신, 외부 SQL 및 쓰기 실행은 제외한다. SQLite의 작성본 저장과 외부 SQL 실행은 구분한다.

## 계약과 역할 경계

기존 49개 Schema는 보존하고 2.7.0 common/source-definition/write-definition/mapping-proposal을 추가한다. 객체·의미·값 그래프·읽기 mapping-set, import-batch 2.6과 원본 근거, SQLite CAS는 재사용한다.

source-definition 2.7은 sourceKind와 accessMode를 명시한다. 기존 PLC 1.x~2.4는 호환 시 sourceKind=plc, accessMode=read로 해석한다. 기존 정의에서 쓰기 가능성을 추정하지 않는다. 새 PLC 정의는 2.4의 접근/codec/배열 계약을 보존하며 접근 방향을 별도 명시한다.

sourceKind: plc / constant / solution-tag / external-value.
accessMode: read / write / read-write. constant/external-value는 read만 허용한다. 쓰기 전용 소스는 읽기 바인딩과 그래프 입력으로 사용할 수 없다.

Týr는 정의·매핑·검증 근거를 작성한다. Mímir 관측, Bifrost 승인/인가, Muninn 실행 계약을 확대하지 않는다. source의 read-write 표시는 실행 권한이 아니며 write-definition 저장으로 명령을 발행하지 않는다. 제안 2.7을 기존 downstream이 지원한다고 가정하지 않는다.

## 비 PLC 소스

설비 문맥에는 귀속하지만 PLC 논리 연결을 꾸며 만들지 않는다. connectionProfileRef와 addressRadix는 null이다. scalar Typed Int32/Double/Boolean/String을 지원하며 타입·단위·단계·근거를 선언한다.

- constant-v1: access.value에 고정 정의값. 숫자는 정확한 십진 문자열, Boolean은 실제 JSON Boolean, 문자열은 원문을 보존한다. Int32 범위·유한 수·타입을 검사한다. Double은 미리보기에서 IEEE64 양자화와 손실을 표시한다.
- solution-tag-v1: solutionInstanceRef, solutionName, solutionVersion, tagPath를 보존한다. 식별자는 논리 선언이며 실제 제품 접속/태그 조회를 하지 않는다.
- external-value-v1: providerRef, valueKey, expressionLanguage(none/opaque/sql), expression을 보존한다. providerRef는 논리 식별자이며 실행 가능한 연결 문서 참조가 아니다. SQL 문법·파라미터를 해석하지 않으며 결과를 가져오지 않는다. 평가에는 별도 가상 Typed 값이 필요하다.

기존 객체 프로퍼티에 PLC와 비 PLC 소스를 함께 연결하거나 기존 그래프에서 조합한다. 같은 설비·타입·단위·근거 검증을 재사용한다. semanticId는 원문 태그명이나 SQL을 보고 자동 생성하지 않는다. cross-equipment 그래프, 외부 배열/구조, provider polling과 vendor tag importer는 제외한다.

## 가상 읽기 미리보기

읽기 방향은 source → graph → read transform → semantic이다. 상수는 정의값을 사용하고 sample로 덮어쓰면 sample.constant-override 오류다. String·Boolean·숫자 타입을 검증하고, provider의 시각·품질은 기존 P3-D 가상 DataValue로 검사한다.

상수는 관측 데이터가 아닌 정의다. static source/evidence lineage에는 포함하지만 freshness/skew 필수 샘플에서 제외하며 source/server timestamp를 만들지 않는다. 상수만 사용하는 timed 매핑의 inputTimestampRange는 null이다. constant-definition trace에 정의값과 근거를 남긴다. 솔루션/외부 값은 typed-input trace에 sourceKind/accessMode/원문 접근 메타데이터와 virtual-input-only 표시를 남긴다.

## 별도 쓰기 정의

write-definition은 targetInstanceRef + 단일 memberPath → destinationRef를 지정한다. transform은 의미 값에서 목적지 표현으로 가는 명시적 linear/unit-convert/cast(숫자·Boolean·String)를 선언한다. UInt16 등 원시 목적지 타입의 cast도 정의할 수 있다. 읽기 변환을 자동 반전·복사하지 않는다.

execution=excluded, invalidValuePolicy=reject를 강제한다. write/read-write가 명시된 PLC 또는 solution-tag만 목적지로 허용한다. reference/version/equipment/member, 근거, 변환 입력/출력 타입·단위, 중복 member·목적지를 검사한다. 태그의 목적지 식별에는 instance/path를 사용하므로 표시 이름·제품 버전 차이로 중복을 우회할 수 없다.

현재는 한 객체 member에 쓰기 정의 하나를 허용한다. fan-out/group commit, 그래프 목적지, codec/배열 역직렬화와 주소 범위 overlap 분석은 후속 범위다. write transform의 범위·rounding·overflow 정책은 선언으로 보존하고 구조/타입을 검사한다. 실제 setpoint 값의 범위/반올림 결과 평가, 바이트 인코딩, write acknowledgement, retry/rollback/atomicity는 구현하지 않는다.

쓰기 정의용 목적지가 초안이면 finding을 남긴다. 정의가 형식 검증을 통과해도 승인·장치 쓰기가 가능한 상태라는 뜻이 아니다.

## 화면·SQLite·재사용

02에서 PLC/상수/솔루션/외부 종류와 접근 방향을 선택한다. 비 PLC 식별·값·원문 표현식과 수동 근거를 작성한다. PLC와 import 근거 편집을 유지한다. 06은 읽기 매핑이다. 09는 상수와 가상 provider 입력을 함께 미리보고 읽기 방향을 표시한다. 11은 별도 쓰기 방향 정의·목적지·변환 JSON을 작성/저장/조회하며 실행 버튼은 없다.

workspaceVersion 2.0 작성 envelope의 optional writes 컬렉션을 추가한다. 기존 테이블·CAS/Host/Origin 보호를 재사용한다. 기존 DB를 열 때 body/revision을 재작성하지 않는다. optional imports와 함께 저장·내보내기를 검증한다. wire proposal은 2.7로 구분한다. 이전 편집기/소비자가 새 필드를 지원한다고 가정하지 않는다.

검증 DB는 build/p4a-ui/editor.sqlite3 revision 34를 backup으로 복제한 build/p4b-ui/editor.sqlite3이다. 원본 파일·import 배치·시나리오는 보존한다.

재사용: PLC decoder/array/codec, 의미·객체·읽기 graph/mapping, evidence/hash/locator, P3-D, importer 원문 보존, SQLite JSON/CAS.
신규: sourceKind/accessMode와 비 PLC scalar 계약, 상수/가상 Typed 평가, 별도 write-definition 및 타입/단위/방향 게이트, 혼합 소스·쓰기 UI, fixture/검증.

MP14/15는 bounded subset 부분 지원이다. 실제 솔루션/외부 provider 연동, SQL·쓰기 실행, 승인/명령 delivery는 포함하지 않는다.


## 구현 확인

P4-B 구현 및 검증을 완료했다. 신규 62개와 기존 회귀 530개가 통과했다. UI DB revision 35에서 fixture를 추가하고 36에서 상수 110, 37에서 별도 쓰기 factor 20, 38에서 SQL 앞뒤 공백을 저장했다. 읽기 미리보기 150−110=40 kPa 및 외부 가상 값 70 kPa, 쓰기 정의 재조회, 원본 P4-A 데이터·import·시나리오 보존을 확인했다. 상세 근거와 후속 제한은 [검증 결과](verification/P4-B-RESULTS.md)에 기록했다.
