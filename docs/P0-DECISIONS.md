# P0 범위와 계약 결정 기록

상태: P0 완료. 이질 정의의 정준화·거버넌스 검증 범위와 계약 경계 확정.
작성일: 2026년 10월 17일

## 0 검증 가설과 완료 범위

비일관적으로 관리되던 문서·설정의 PLC 접근 정의를 손실을 드러내며 공통 계약에 수용하고, 상위 의미로 수렴·구분·변경 관리할 수 있는지가 핵심 가설이다. 실제 장치 통신은 이번 완료 조건에서 제외한다.

[정준 모델 검증 기준](P1-GOVERNANCE-CRITERIA.md)의 G01~G09가 P1 종료 기준이다. 네 접근 종류를 표현하는 것만으로 완료를 선언하지 않는다. 의미의 근거는 작성자·검토자가 정하고 게이트는 그 선언의 일관성·변경·손실을 검사한다.

## 1 시작 범위

사용자가 확정한 네 접근 범위는 다음과 같다.

| 프로파일 ID | 대상 | 접근 종류 | fixture |
|---|---|---|---|
| ab-logix-symbol-v1 | AB Logix | symbol | source-c / Conveyor.Motor.ActualSpeed |
| s7-1500-opcua-v1 | S7-1500 OPC UA | opcua-node | source-d / namespace URI와 식별자 |
| s7-300-db-v1 | S7-300 DB | db-offset | source-b / DB10 byte 20 |
| melsec-device-v1 | Mitsubishi MELSEC | device-register | source-a / D1000, 2워드 |

이는 데이터 정의의 시작 범위이며 실장치 드라이버 지원 인증이 아니다. 모든 현재 값·파일·검토 기록은 가상 fixture다.

AB는 심볼 경로를 있는 그대로 보존한다. S7-1500은 OPC UA namespace URI·식별자 종류·값을 보존하고 DB 절대 주소로 환원하지 않는다. S7-300은 DB 번호와 바이트 오프셋·길이를 분리한다. MELSEC은 영역·주소·진법·워드 수를 분리하며 계열 미확정 상태에서 X/Y 진법을 통일하지 않는다.

## 2 자료 조사와 미확정 입력

2026-10-20 후속: 대상 솔루션군은 PIO·Kepware로 선정했다. 아래는 P0 당시의 미확정 기록이다. 실제 제품/driver 버전·원본 파일/형식과 지원 범위는 여전히 미확정이며 [P4-F 공통 수용·제품별 해석기 설계](P4-F-SOLUTION-INTERPRETATION.md)에서 합성 검증과 실제 제품 자료 검증을 분리한다. 기존 네 PLC 접근 범위나 P0/P1 계약은 바꾸지 않는다.

Yggdrasil 하위에서 XLSX·XLS·CSV·PDF 및 Ignition·Kepware 관련 파일명을 조사했다. 기존 Bifrost의 vendor/template 검증 JSON은 확인했지만 실제 현장 문서 또는 완전한 제품 export 원본이라고 확인할 자료는 없었다.

| 입력 | 현재 상태 | 후속 조건 |
|---|---|---|
| 네 PLC 접근 범위 | 사용자 확정 | 위 표 적용 |
| CPU 모델·펌웨어·연결 드라이버 버전 | 미확정 | 실제 자료 제공 시 기록 |
| 첫 현장 XLSX 양식 | 미확정 | 실제 원본·허용된 비식별 사본 확보 |
| 첫 운영 솔루션·버전·export | 미확정 | 제품과 원본·상속·기본값 범위 확인 |
| 현장 의미·매핑 검토 담당자 | 미확정 | 자료 대조 책임자 지정 |
| P1 문서 대체 | 가상 CSV·JSON | XLSX importer나 제품 지원으로 표시하지 않음 |

이 미확정 입력은 P0·P1의 완료를 막지 않는다. 실제 원본 선정과 제품 importer 지원은 P4/P7의 대표성·현장 수용성 검증으로 분리한다. CSV는 XLSX를 구현했다는 의미가 아니며 fixture의 주소 문법도 공식 제품 export 형식이 아니다.

## 3 역할과 재사용 결정

| 영역 | 결정 | 코드 근거 |
|---|---|---|
| 작성·검토 | Tyr (Týr)가 초안·근거·매핑을 소유 | 신규 기능 |
| 후보 도출 | Mimir (Mímir) 유지, 현재 수정 없음 | DefinitionDeriver, BrowsedMember |
| 승인 SSOT | Bifrost 유지 | 레지스트리·검증 기반 |
| 런타임 | Muninn 후속 확장, 현재 수정 없음 | EgressValidator |
| 기존 UDT | 기존 계약 유지, 새 계약과 분리 | definition.schema.json |
| 구조적 비교 | 기존 기능을 기존 모델에 재사용 | CompatibilityChecker, ModelReconciler |
| 원본 설정 | Tyr 새 importer 필요 | IgnitionUdtAdapter는 접근·스케일 손실 가능 |
| 해시 발행 | Bifrost 내부 패턴 재사용 | RecipePublish, RecipeManifest |
| 전체 묶음 | 새 릴리스 검증 필요 | 기존 verify는 latest 단일 파일 검사 |
| 활성화 | 새 ArtifactResolver 후보, P6에서 구현 | ActivationService·ArtifactResolver |

ActivationRequest는 kind/ref/version을 받고 ArtifactResolver는 바이트 해시를 반환하므로 향후 mapping-release resolver를 연결할 자리가 있다. 그러나 ActivationService는 ACTIVATE/ROLLBACK와 운영 target을 기록한다. 이번 작성 승인과 동일한 행위로 재사용하지 않는다.

P6에서는 검증·검토 승인·불변 발행을 연결하고 운영 활성화는 별도 상태로 둔다. Tyr에 두 번째 승인 권위를 만들지 않는다. 기존 코드의 존재를 mapping-release가 이미 구현됐다는 근거로 사용하지 않는다.

## 4 계약 결정

- JSON Schema Draft 2020-12, 계약 버전 1.0.0을 사용한다.
- ID와 SemVer는 각 불변 문서의 식별이다. 소스 참조도 id/version으로 통일한다.
- 편집 revision은 후속 작성 API의 동시 수정 토큰이다. 불변 wire 계약 버전과 중복하지 않는다.
- schemaVersion은 1.0.0으로 고정한다. 현재 설계서의 JSON 도식보다 contracts/1.0.0이 우선한다.
- 미확인 값은 명시적 null 또는 unit.status=unknown이다. 필드 누락과 해당 없음은 구분한다.
- source.status=draft는 미확인 접근을 저장할 수 있다. ready는 선언의 완전성이며 실장치 확인이나 승인이 아니다.
- unit은 known/code, not-applicable, unknown으로 구분한다. P1 단위 어휘는 rpm, Cel, N.m, 1이다.
- raw 타입은 Int16, UInt16, Int32, UInt32, Int64, Float32, Float64, Boolean으로 시작한다. 결과 타입은 Double, Int32, Boolean, String이다.
- 십진 계수는 문자열로 보존한다. 과학적 표기·NaN·Infinity는 허용하지 않는다.
- linear → 명시적 cast 순서와 exact/half-even 반올림, overflow=error, invalid=bad-quality를 사용한다.
- typed 소스에는 바이트 순서를 넣지 않는다. bytes 소스에는 바이트·워드 순서를 명시한다.
- source 접근의 bitOffset은 저장값에서 불리언 뷰를 선택한다. 후단 bit-select를 중복 적용하지 않는다.
- already-engineered 입력의 비항등 linear는 P1 승인 검증에서 거부한다. 후속 단위 변환 지원 시 근거를 가진 별도 연산으로 확장한다.
- 문서 해시는 UTF-8 원본 바이트에 대해 계산한다. JSON 재직렬화로 해시를 계산하지 않는다.
- duplicate JSON key, 비유한 JSON 수치, 상대 경로 이탈·외부 schema retrieval은 거부한다.
- evidence 원본·문서·review·proposal·release의 참조 해시는 자기 자신을 포함하지 않는다.
- 로컬 검토 기록과 manifest의 문자열은 인증 증거가 아니다. 서명·실제 승인 연계는 P6이다.
- 기본 앱 결합은 파일·CLI이며 공유 코드·Maven 의존·운영 접속을 추가하지 않는다.

## 5 도구 버전과 기술 경계

P1 검증 환경은 로컬 Python 3.13.5와 jsonschema 4.26.0이다. requirements-contracts.txt에 검증 의존성을 고정했다. 스키마와 fixture는 언어 중립이고 Python 스크립트는 계약 시험 도구이며 제품 백엔드가 아니다.

P0에서는 JVM 환경을 우선 검토하되 제품 실행 환경 선택을 P2로 보류했다. P2는 기존 P1 검증기를 직접 재사용하는 Python 3.13.5 표준 서버·SQLite와 HTML/CSS/JavaScript를 선택했다. 새 프레임워크 의존성 없이 로컬 작성·저장 가설을 확인하는 결정이다. [P2 결정 근거](P2-AUTHORING.md)를 따른다.

## 6 벤더 문서 근거

AB Logix 심볼 접근은 Rockwell의 Logix5000 Data Access Programming Manual에 설명되어 있다.
[Rockwell 매뉴얼](https://support.rockwellautomation.com/ci/okcsFattach/get/1057724_5)

S7-1500의 OPC UA namespace와 NodeId는 BrowseName만으로 식별할 수 없다는 점을 Siemens 문서가 설명한다.
[Siemens namespace 문서](https://docs.tia.siemens.cloud/r/en-us/v20/configuring-automation-systems/using-opc-ua-communication-s7-1200-s7-1500/what-you-need-to-know-about-opc-ua-s7-1200-s7-1500/namespace-overview-for-the-opc-ua-server-of-the-s7-1200/1500-cpus-s7-1200-s7-1500-s7-1500t)
[Siemens OPC UA 클라이언트 예제](https://cache.industry.siemens.com/dl/files/901/109737901/att_1116717/v2/109737901_OPC_UA_Client_S7-1500_DOKU_V1_5_en.pdf)

MELSEC-F 계열의 X/Y는 8진수 예가 있고 MC 통신 형식에도 OCT/HEX 차이가 있으므로 계열·프레임·데이터 코드가 미확정이면 진법을 추측하지 않는다.
[Mitsubishi FAQ](https://fa-faq.mitsubishielectric.com/faq/show/24868)
[FX5 MC 매뉴얼](https://dl.mitsubishielectric.com/dl/fa/document/manual/plcf/jy997d60801/jy997d60801g.pdf)

실제 장치별 범위·타입·인증·접근 가능성은 모델과 firmware, 제공 파일이 확정된 뒤 별도 검증한다.


## 객체 매핑 확장 결정

다중 프로퍼티·다중 연결 구조는 1.0.0 계약에 이미 존재하며 P2 화면의 단일 값 제한을 제거했다. 신규 단위·unit-convert는 별도 1.1.0에 정의했다. 현재 작성·검증은 두 버전을 구분해 사용한다. [객체 매핑](OBJECT-MAPPING.md)을 따른다.
