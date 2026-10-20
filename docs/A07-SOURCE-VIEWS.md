# A07 명시적 alias·전체 워드·비트 view

작성일: 2026-10-18. 이 확장은 문서·설정에서 정리한 PLC 정의를 일관된 의미에 매핑하는 오프라인 기능이다. 장치 통신·외부 SQL·쓰기 실행·운영 활성화는 포함하지 않는다.

## 계약과 의미

기존 1.x~2.9.0 스키마 60개의 바이트를 보존하고 2.10.0 source-definition/common 두 스키마를 추가했다. 직접 소스는 기존 버전을 그대로 사용한다. 새 버전은 PLC 읽기 view 전용이며 viewOf에 부모 소스의 id/version을, view에 alias 또는 bit 관계를 명시한다.

~~~json
{
  "schemaVersion": "2.10.0",
  "sourceKind": "plc",
  "accessMode": "read",
  "viewOf": {"id": "status-word", "version": "1.0.0"},
  "view": {"kind": "bit", "bitIndex": 15}
}
~~~

위 코드는 관계 필드의 발췌다. 완전한 문서는 fixtures/a07/workspace.json을 따른다. alias는 부모의 논리 값을 그대로 사용한다. bit는 부모 정수를 디코딩한 뒤 LSB=0으로 비트를 선택한다. 비트 인덱스는 메모리의 바이트 순서가 아니라 디코딩된 값의 비트 좌표다. 따라서 MELSEC little-endian 05 80과 S7 DB big-endian 80 05가 같은 32773을 나타내며 bit0·bit15는 true다.

view의 rawRepresentation과 접근 정보는 부모 저장 형태를 그대로 보존한다. 예를 들어 원시 UInt16 워드의 bit view는 rawRepresentation.valueType=UInt16을 유지하지만 논리 결과 타입과 정준 멤버 타입은 Boolean이다. alias는 부모의 논리 타입/단위를 계승하며 bit 결과 단위는 not-applicable이다. signed Int16/Int32/Int64의 부호 비트도 해당 폭의 비트로 선택한다.

부모는 ready이며 읽기 가능한 PLC 소스여야 한다. view 자체는 read만 허용한다. parent read-write는 읽기 관계로 참조할 수 있지만 view가 쓰기 목적지가 되는 것은 허용하지 않는다. 외부 값·상수·솔루션 태그·native bit·codec·고정 배열·중첩 구조의 view는 이번 범위에서 제외한다. 전체 워드는 Int16/UInt16/Int32/UInt32/Int64를 지원한다. alias 체인과 bit view를 조합할 수 있으며 최대 16관계, 순환·누락·오래된 부모 버전·범위 초과를 검사한다. Boolean bit view의 alias는 가능하지만 bit view를 다시 bit 선택할 수 없다.

## 검증과 근거

Týr의 Python과 Bifrost의 Java가 독립적으로 다음을 검사한다. 소스 코드는 공유하지 않고 JSON 스키마와 파일 fixture만 복제한다.

- 부모의 존재·정확한 버전, 순환 및 깊이.
- 설비·연결·접근 프로파일·접근 필드·rawRepresentation·inputStage·진법 snapshot 일치.
- alias 단위 계승, bit 결과 단위 및 부모의 정수 타입·비트 폭.
- 부모 ready/read 조건과 view의 읽기 전용 정의.
- view 자신의 근거와 부모 체인 전체의 근거를 graph/mapping이 포함하는지.

원본 표시 문자열·현장 신호명은 alias 이름이 될 수 있으므로 물리 위치의 동일성은 구조화 접근 필드로 확인한다. 이름이 같다는 이유로 view 관계를 추정하지 않는다.

부모의 접근/디코딩 변경은 기존 view snapshot과 함께 작성본에 보존할 수 있다. 불일치/부모 미완료 finding이 남고 preview·제안 검증·Bifrost 승인을 차단한다. 근거를 확인하고 14 화면에서 부모를 재선택해 snapshot을 갱신한다. 체인은 부모에 가까운 view부터 갱신한다. 순환·누락·비트 범위 초과 등 구조 오류는 저장 단계에서 거부한다. 과거 제출/승인은 새 작성본에 재사용하지 않으며 내용 해시·Bifrost의 독립 diff/서명으로 구분한다.

## 화면과 가상 입력

14 alias·워드·비트 view에서 부모, 관계, 비트 인덱스, 자체 이름·근거를 작성/편집한다. 02에서 저장된 view를 선택해도 관계 편집 화면으로 이동한다. 05 graph와 06 객체 프로퍼티 매핑에서 일반 소스와 함께 선택하며, 07에서 alias 체인과 논리 타입을 확인한다.

09 preview에는 최종 원본 소스의 가상 입력만 제공한다. 동일 워드의 여러 view는 원본을 한 번 디코딩하며 view:alias/view:bit 단계를 표시한다. view별로 독립 값을 주입하면 sample.view-override로 거부한다. P3-D 시각·품질·결측·freshness/skew 정책도 같은 원본 입력을 사용한다. 원본이 bad이거나 결측이면 view/파생 결과에 전파한다. 이것은 실제 장치에서 원자적 snapshot을 읽었다는 보장이 아니다.

## SQLite 호환과 Bifrost 발행

SQLite의 기존 workspace JSON·revision/CAS·시나리오·기준본·검토·제출 테이블을 재사용한다. 기존 문서를 자동 변환하거나 기존 DB를 다시 쓰지 않는다. 새 view 저장과 재조회는 같은 원자적 workspace 저장 경로로 처리한다. schemaVersion 2.10.0 소스는 2.0 authoring workspace에서만 허용한다.

제안 exporter는 선택된 매핑에서 viewOf 체인을 따라 원본 및 모든 근거를 함께 고정한다. MappingProposal 2.7.0과 submission/approval/release 2.9.0은 유지한다. 2.10.0을 모르는 수신자는 새 소스를 승인하지 못한다. capability 이름만으로 호환을 판단하지 않고 스키마·내용을 실제 검증한다. Týr는 승인 권위나 개인 키 저장 기능을 만들지 않는다.

Bifrost는 재검증·두 등록 키의 서명 승인·전체 파일 불변 릴리스를 사용한다. 릴리스 파일 발행과 Muninn 런타임 소비/운영 활성화는 별개다. 기존 승인·변조·stale base 규칙을 계속 적용한다.

## 검증과 한계

fixtures/a07는 네 PLC의 20개 소스·4개 객체·4개 graph·20개 프로퍼티 매핑과 독립 리터럴 0x8005 기준값을 담는다. 12개 부정 변형은 양쪽 검증기로 검사한다. 별도 tests는 signed high bit·false bit·부모 변경·override·품질·SQLite 재조회·API 원자성을 검사한다.

Týr에서 scripts/test_a07.py --report docs/verification/a07-validation.json, scripts/test_p7.py --report docs/verification/a07-regression.json을 실행한다. 기존 P7 기록은 덮어쓰지 않는다. Bifrost에서 Maven offline MappingPublicationTest/MappingGateTest로 승인·발행과 기존 수신 회귀를 검사한다.

실행 결과는 verification/A07-RESULTS.md에 남긴다. 이 결과는 실제 현장 PoV나 A14 PC 전체 네트워크 격리 완료가 아니다.
