# 매핑 템플릿과 적용본 (2.19.0)

## 목적과 경계

2026-10-20 설계 보완: [정준 의미 계약과 값 생성·매핑 계약](CANONICAL-SEMANTICS-AND-GENERATION.md). 아래2.19 구현/저장 계약은 유지한다. 신규 의미 문맥·생성 조립 계약과 슬롯의 업무 역할/상수 종류·일반 조건·업무 적합성 검증은 P4-F의 미구현 범위다. 기존 template.model/graphs/mapping과 application/sourceSnapshots의 의미를 소급 변경하지 않는다.

공통 의미 모델, 객체 매핑, 전이적인 값 그래프와 변환·결측·시간·품질 정책을 불변 템플릿으로 묶는다. 설비별 접근 정의는 입력 슬롯에 연결한다. 프로토콜·주소·byte/word order는 기존 source-definition이 소유하며, 슬롯은 **디코딩/코덱/view 해석 후 valueType·unit·inputStage**를 고정한다. 같은 UInt16/kPa/raw라면 AB 심볼, OPC UA Node, S7 DB, MELSEC 디바이스가 하나의 템플릿을 공유한다. 소스 디코딩 계약 전체는 적용본 sourceSnapshots에 고정되므로 이후 조용히 변경할 수 없다.

Týr는 작성·추천·비교·가상 미리보기·로컬 SQLite 저장·불변 제출 패키지를 담당한다. Bifrost는 별도 구현한 Java 컴파일러로 생성물을 다시 계산하고, registry 전체의 템플릿/적용본 이력과 의미 카탈로그·URI 폐기를 검사한다. 기존 두 확인자 서명 승인 및 파일 릴리스를 재사용한다. 작성자 문자열과 로컬 저장은 승인 권한이 아니다. Mímir/Muninn의 수집·실행이나 운영 활성화를 추가하지 않는다.

## 계약

- mapping-template: id/version, label/description/reason/authoredBy/authoredAt, previousTemplateRef, slots, model, target, graphs, mapping. 기존 매핑에서 시작하여 참조하는 그래프 전체를 포획한다. 소스 주소를 템플릿의 연결 제약으로 복제하지 않는다. 기존 sourceRef는 입력 슬롯의 대체 지점이며 템플릿 외부 그래프 참조는 허용하지 않는다.
- 슬롯: slotId, 작업자 label, 원형 sourceRef, signature. rawRepresentation 필드에는 디코딩 후 valueType만 담는다. fixedArray는 초기 범위에서 shape/stride/범위 포함 전체 배열 계약 일치를 요구한다. 배열 배치 자동 적응은 추가 범위다.
- template-application: applicationId/revision, 이전 적용본 해시, templateRef(id/version/canonical SHA256), equipmentInstanceId, targetLabel, 슬롯 연결, 전체 sourceSnapshots(직접 슬롯에 없는 view 부모 포함), 생성 정준 정의 generated, 작성자·시각. 적용본은 하나의 설비에 속하며 적용 중 다른 설비로 이동시키지 않는다. 새로운 설비에는 별도 적용본을 만든다.
- mapping-proposal 2.19: 기존 문서 종류와 두 새 종류를 함께 담는다. 구 schema 파일을 바꾸지 않으며, 구 수신기는 새 버전을 거부한다. Bifrost catalog 조회 계약과 기존 workspaceVersion 2.0은 유지한다.

한 템플릿 최대 입력32·그래프64·전체노드1024·버전64, 부모 포함 소스 snapshot128·view 체인17, 적용본 revision256, 고유 템플릿/적용 기록 합계768. 기존 API 본문2MiB·그래프 dependency 한계도 그대로 적용한다. 한계는 대량 공장 규모의 수용을 뜻하지 않는다.

## 생성·고정·명시적 갱신

템플릿은 같은 ID 내 numeric semver의 단일 선행 해시 체인이다. 같은 버전 내용 변경, 이력 삭제·fork를 거부한다. 적용본은 연속 revision과 선행 canonical 해시를 요구한다. 새 템플릿이 저장되어도 적용본의 templateRef와 결과는 그대로다. 갱신 또는 구 버전의 명시적 재적용은 새 적용 revision을 만든다.

객체/매핑 ID는 reuse-적용본ID-target/mapping으로 유지하고 version을 증가시킨다. 모델/그래프는 적용 revision별 ID로 생성하고 이전 세대를 보존한다. 바인딩 ID는 적용본 prefix와 memberPath 해시로 고정한다. 외부 그래프 소비자는 기존 그래프 세대를 계속 참조한다. 구 target version 소비자 등의 충돌은 전체 작업공간 검사에서 차단하며 자동 전파하지 않는다. 원본 template의 의미 URI는 유지한다. 의미 변경이 필요하면 기존 URI lifecycle 규칙에 따라 새 URI로 정의해야 한다.

입력 signature 불일치, 초안 소스, 다른 설비, 슬롯 누락/중복, 없는 pin, 생성물 수정, 현재/역사 소스 변경, 역사 fork를 거부한다. 바이트 순서가 다른 소스 연결 자체는 가능하지만 그 소스 정의에 따라 각각 디코딩하며, 타입/단위 차이를 암묵 변환하지 않는다. BCD16은 Int32, native bit/bit view 및 그 alias는 Boolean, 고정 배열은 FixedArray로 슬롯을 판정한다. 이미 공학값인 기존 already-engineered 명칭을 그대로 수용한다. 부모 소스도 불변 snapshot으로 고정하며 슬롯별 가상 입력은 실제 부모 원시 값/바이트로 모은다. 여러 슬롯이 같은 부모를 가리키면 가상 입력의 충돌을 거부한다. 상수·솔루션 태그·외부 값도 기존 source-definition을 슬롯에 연결할 수 있으며 실제 외부 조회나 쓰기는 실행하지 않는다.

적용 전 plan은 읽기 전용이며 generated·연결·적용 revision·선행 pin·작업공간 revision으로 planSha256을 만든다. 저장 시 최신 상태에서 다시 계산하여 token을 비교하고 기존 CAS 트랜잭션으로 적용 이력·정준 모델·객체·그래프·매핑을 원자 저장한다. 선행 이력은 append-only이다. SQLite DDL 추가/자동 마이그레이션 없이 기존 workspace JSON의 선택 배열 mappingTemplates/templateApplications를 사용한다. 기존 DB 조회는 행/스키마를 변경하지 않는다.

## 작업자 화면 19

1. 기존 객체 매핑을 선택하고 이름·ID·작성자·사유를 입력한다. 포획한 입력 슬롯과 공통 연산·변환 정책을 확인하고 슬롯에 현장용 이름을 붙인다.
2. 템플릿 버전과 설비를 선택한다. 호환 소스는 주소·표시 이름과 함께 제공하고 불일치 후보도 사유로 확인한다. 유일하게 높은 이름 점수의 후보만 추천한다. 추천 채우기는 작업자 클릭으로 수행하며 의미의 정답을 자동 판정하지 않는다.
3. 비교 후 저장한다. 가상 typed 값 또는 HEX 바이트를 입력하면 기존 preview의 디코딩→그래프→변환/cast·품질·손실 trace를 보여준다. 입력 변경 시 저장을 비활성화하고 다시 비교한다. 배열·상세 시간/품질 가상 입력은 저장 후 기존 09 경로를 사용한다.
4. 적용본별 고정 버전, 최신 버전, 변경 위치와 전후 값, 적용 이력을 확인한다. 갱신 버튼은 기존 연결을 채우며 명시적 비교/저장을 요구한다. 최신 버전에서 새 개정안을 작성한다. 초기 정책 폼은 기존 linear factor/offset·cast exact/half-even과 제한 산술 연산을 수정하며, 일반 그래프 편집 전체는 기존 05에서 원형 매핑을 작성한 뒤 포획한다.
5. 13에서 적용 매핑을 제출한다. 템플릿 체인·적용 이력·현재 생성물·참조된 역사 생성물/소스·근거 closure를 포함한다. 적용본을 모르는 구 패키지로 생성물을 다시 제출해도 Bifrost가 이미 알고 있는 소유권과 비교하여 provenance 누락을 거부한다.

## 재사용한 기능 / 추가한 기능

기존 의미 모델·URI lifecycle·그래프 DAG·source decoder·단위/스케일/cast·가상 preview·SQLite CAS·근거/가져오기·불변 submission·서명 승인/릴리스·복구·전역 catalog를 재사용한다. 새 부분은 2.19 wire 계약, 템플릿 포획과 immutable 체인, 입력 슬롯 후보와 pin, 결정적 적용본 컴파일러(Python/독립 Java), 변경 영향/명시적 갱신 화면, provenance closure 및 registry 이력 재검사다.

## 합성 검증과 현장 PoV

fixture는 네 PLC의 actual/target/gain과 3단 그래프·4개 의미 출력을 사용한다. actual150/target50/gain2에서 기본 quotient50, 공통 subtract→add 개정 후 선택한 OPC UA 적용본만100이며 나머지는50이다. 원래 그래프 소비자의 결과도 유지한다. 실제 장치·네트워크 수집·외부 SQL·쓰기 실행·runtime 활성화는 없다.

별도 미완료: 익명화 실제 문서/설정에서 슬롯의 의미 정답, 단위/스케일·운전모드 정답, 잘못된 추천율과 누락, 첫 작성/두 번째 설비 적용/버전 개정의 전체 작업시간, 여러 작업자의 이해도·재사용성, 실제 소비자 inventory와 갱신 절차. vendor native 배치/export 해석, 대량 이력·배포/IAM/registry 연합·자동 source adapter도 현장/추가 범위다.
