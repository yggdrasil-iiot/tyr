# Týr 데이터 정의·값 생성과 의미 매핑 설계서

> P0·P1 반영: 시작 범위는 AB Logix 심볼, S7-1500 OPC UA, S7-300 DB, Mitsubishi MELSEC의 네 가지다. wire 계약은 contracts/1.0.0과 docs/P0-DECISIONS.md를 따른다. 아래 초기 JSON 예시는 도식이며 P1의 id/version 참조로 구체화했다.

검토용 설계 초안 v0.1 · 2026년 10월 17일

2026-10-20 후속 설계: [P4-F PIO·Kepware 외부 정의 수용](docs/P4-F-SOLUTION-INTERPRETATION.md). 원본·참조·해석 근거·미해석 항목·전환 판정을 갖는 공통 수용 모델과 제품별 해석기 경계를 추가한다. **문서 설계이며 구현 예정**이다. 아래 초기 설계/과거 구현 기록과 구분하며 기존 계약·SQLite는 변경하지 않는다.

같은 날 [정준 의미 계약과 값 생성·매핑 계약의 경계](docs/CANONICAL-SEMANTICS-AND-GENERATION.md)를 보완했다. 정준화는 PLC 메모리맵뿐 아니라 MES가 받는 값의 뜻과 PLC·DB·상수·조건을 조합한 생성 정의를 포함한다. 업무 문맥/유효성과 소스·연산·정책을 별도 계약으로 고정하며 혼합 템플릿 사례와 미구현 검증 범위를 명시한다.

Týr는 PLC마다 다른 주소·오프셋·심볼 접근 정의를 보존하면서, 이를 상위 애플리케이션이 사용할 공통 의미에 연결하는 모델링 작업대다. 기존 문서와 솔루션 설정 파일, 수동 입력으로 시작하며 사용자는 화면에서 접근 정의·변환·의미·근거를 함께 관리한다.

정준화 범위는 PLC 입력에 한정하지 않는다. DB 레코드·상수·외부 값과 조건/변환을 조합한 최종 객체도 대상으로 하며, 소비자가 받을 뜻을 정하는 정준 의미 계약과 그 값을 만드는 값 생성·매핑 계약을 분리한다. 일반 조건·업무 문맥·상태 모델의 지원 수준은 후속 설계/구현 범위에 명시한다.

Yggdrasil에서 Týr는 작성·검토, Mímir는 모델 후보 도출, Bifrost는 검증·승인·기록, Muninn은 승인된 매핑의 실행을 담당한다. 초기 MVP는 운영 설비에 접속하지 않고 파일과 독립적인 시험 데이터로 검증한다. 명칭 Týr와 명령·저장소 이름 tyr를 사용한다. 아래 데이터 계약과 추가 기능은 구현 제안이다.

# 1 문제와 목표

PLC 엔지니어의 문서와 운영 솔루션의 설정에는 같은 신호에 대한 서로 다른 정보가 담긴다. 문서는 주소와 설명을 제공하고, 설정에는 이름·수집 타입·스케일·단위·상태 해석이 추가될 수 있다. 개정 이후에는 어느 자료가 어느 설비에 해당하는지, 어느 단계에서 값이 변환되는지 추적하기 어렵다.

PLC마다 레지스터·비트 위치, DB·바이트 오프셋, 구조체 심볼 경로, OPC UA NodeId 등 접근 방식이 다르다. 이 차이를 한 주소 문자열로 축소하지 않고 관리한다.

사용자는 다음 질문에 출처와 확인 상태를 포함해 답할 수 있어야 한다.

- 이 데이터는 어디에서 어떤 표현으로 읽는가?

- 원시값 또는 이미 변환된 값은 무엇을 의미하는가?

- 어떤 디코딩과 변환을 거쳐 상위 속성에 연결되는가?

- 문서와 설정 사이에 어떤 차이가 있고 누가 무엇을 확인했는가?

- 개정 이후 어떤 매핑과 소비 계약을 다시 검토해야 하는가?

첫 가치 검증은 의미 확인·변경 검토 업무를 대상으로 한다. 자료에 없는 정보는 미확인으로 남긴다. 추출된 설정, 담당자가 확인한 정의, 승인된 계약, 실제 설비 확인 상태를 구분한다.

문서가 없고 기존 PIO 또는 Kepware 설정만 남은 대상 현장도 시작점이다. 최종 태그·객체·프로퍼티에서 입력·변환·참조·적용 정책을 역추적하고, 확보된 범위·전환 가능한 범위·추가 확인할 부분을 설명한다. 주소 한 행으로 평탄화하지 않는다. 자료 준비 → 쟁점 중심 검토 → 설정 기반 정의서·엑셀 대조표 반환을 다음 제품 우선순위로 두며, 세부 모델과 실제품/가상 검증 경계는 P4-F를 따른다.

# 2 요구사항과 설계 원칙

| ID | 요구사항 | MVP 수용 조건 |
|---|---|---|
| R01 | 이기종 접근 수용 | 주소·DB 오프셋·심볼을 작성·편집·재조회 |
| R02 | 공통 의미 관리 | 의미 ID·설명·결과 타입·단위 관리 |
| R03 | 명시적 매핑 | 설비 인스턴스의 소스와 의미 멤버 연결 |
| R04 | 변환 관리 | 선형 변환·비트 선택·열거형 변환 검증 |
| R05 | 기존 자료 활용 | XLSX 한 양식과 설정 export 한 형식 수용 |
| R06 | 근거 추적 | 파일과 셀·설정 경로로 이동 |
| R07 | 작업 화면 | 소스·의미·매핑 편집과 변경 검토 |
| R08 | 승인·버전 | 초안·제출·승인 릴리스 분리 |
| R09 | 오프라인 동작 | 운영 설비 접속 없이 처리·값 미리보기 |
| R10 | 누락 가시성 | 미지원 자료·행·속성·참조 집계 |
| R11 | 재현성 | 입력·프로파일·추출 결정·매핑 버전 고정 |

접근 방식은 구조화해 보존하고 공통 의미는 독립적으로 재사용한다. 원시 저장 타입, 디코딩 값의 타입, 상위 결과 타입을 분리한다. 기존 설정을 출처 있는 관측 정의로 수용하되 공통 계약의 권위로 자동 승격하지 않는다.

앱들은 공개된 데이터·파일 계약으로 결합한다. 공유 Java 모듈이나 다른 앱의 내부 클래스를 의존하지 않는다. Týr 초안 저장소는 Bifrost의 승인 레지스트리와 구분하며 별도의 승인 SSOT를 만들지 않는다.

전체 제품은 PDF·추가 솔루션·Mímir 관측·런타임 소비로 확장한다. 초기 범위에는 PLC 쓰기, 전 벤더 드라이버, 운영 설정 자동 수정, 임의 스크립트 실행을 포함하지 않는다.

# 3 현재 구현과 보완 대상

2026년 10월 17일 검토한 로컬 소스를 기준으로 구분한다.

| 구성 요소 | 현재 기능 | 보완 |
|---|---|---|
| Mímir | OPC UA ObjectType의 이름·타입·EURange에서 UDT 제안 | 접근 정보와 관측 근거를 보존한 후보 계약 |
| Bifrost | UDT 검증·레지스트리·provenance·활성화 기반 | 접근·의미·매핑 검증과 릴리스 승인 |
| vendor 비교 | 파일을 정규 UDT로 변환해 멤버 차이 대조 | 접근·변환 손실 없는 입력과 대조 |
| Muninn | 정의 무결성 확인·OPC UA 이름/타입 검사·일회성 발행 | 후속 매핑·변환 소비 |
| spec | raw 주소→typed metric과 Git 관리 방향 | 접근·의미·매핑 계약 및 사용자 작업 흐름 |

현재 Mímir의 semanticId는 타입·멤버 이름에서 합성된다. 서로 다른 장비의 명칭을 공통 개념으로 연결하는 의미 사전이 아니다. BrowsedMember와 Member에는 원본 노드 위치·단위·변환·출처가 없다.

Bifrost의 model-reconcile은 파일 입력 기반으로 재사용할 수 있다. 다만 기존 TemplateAdapter를 거쳐 UDT로 투영하면 접근·변환 정보가 사라질 수 있다. 기존 모델 비교는 유지하고 Týr 입력은 필요한 정보를 보존하는 별도 계약으로 수용한다.

현재 구조적 호환성 게이트의 PASS를 의미·접근·변환 전체에 대한 승인으로 사용하지 않는다.

# 4 앱 역할과 계약 경계

| 앱 | 책임 | 입력 | 출력 |
|---|---|---|---|
| Týr | import·수동 작성·의미 선택·매핑·근거 검토·제출 | 파일·수동 입력·후보·승인 계약 | 초안·검토·제안 묶음 |
| Mímir | 타입·모델 후보 도출 | 선택적 OPC UA, 향후 오프라인 타입 자료 | 관측 묶음·모델 후보 |
| Bifrost | 검증·변경 규칙·승인·발행·기록 | Týr 등 생산자의 제안 | 검사 결과·승인 릴리스 |
| Muninn | 승인 매핑으로 값 취득·변환·발행 | 릴리스·별도 연결 설정 | 의미 있는 값·품질 |

Týr는 승인 레지스트리를 직접 덮어쓰지 않는다. Mímir는 의미를 확정하거나 승인하지 않는다. Muninn에는 작성·승인 기능을 넣지 않는다.

기본 흐름은 “문서·설정·수동 입력·Mímir 후보 → Týr 작성과 검토 → Bifrost 검증과 승인 → 승인 릴리스 → Muninn 또는 기존 실행 제품”이다. 검사 결과와 승인 상태는 Týr 화면으로 돌아온다.

Huginn 관측은 선택적 보조 근거다. 통신 흔적이 업무 의미를 확정하지 않으며 패킷 캡처는 도입의 선행 조건이 아니다.

## 4.1 Týr와 Mímir

Týr가 파일 import와 UI 작업을 소유한다. Mímir의 기존 도출 기능은 선택적 입력 생산자로 유지한다. 생성한 local IRI는 suggestedSemanticId와 생성 방식으로 전달해 확인된 의미와 구분한다.

Mímir 후속 관측 계약은 원본 NodeId·namespace URI·원본 타입 식별자·관측 시점·범위를 보존한다. NodeId의 문자열·숫자·GUID·opaque 종류를 구분하고 BrowseName과 문자열 NodeId가 같다는 전제를 일반화하지 않는다.

## 4.2 구현 배치

Týr는 독립된 사용자 도구다. UI·작성 API·파서·검증·로컬 저장소를 한 배포 단위로 시작한다. Bifrost와는 로컬 파일·CLI로 연계한다. HTTP는 동일 계약의 후속 전달 수단이다. 분산 서비스·브로커·그래프 DB는 MVP 필수 의존성이 아니다.

# 5 데이터 모델

| 모델 | 역할 | 내용 |
|---|---|---|
| EvidenceArtifact | 원본 자료 식별 | 파일 해시·개정·확보 일시·범위·보관 참조 |
| SourceObservation | 출처별 주장 | 원문 값·셀/설정 경로·추출 프로파일 |
| SourceDefinition | 편집 가능한 접근 정의 | 설비·연결·접근 종류·원시 표현·근거 |
| SemanticDefinition | 재사용 의미 | 개념·멤버·결과 타입·단위·역할·제약 |
| MappingSet | 설비별 연결 | 소스·대상·변환·무효값 정책·검토 |
| MappingRelease | 승인 묶음 | 모든 정의의 정확한 버전·해시 |

문서와 설정의 주장이 다르면 둘 다 관측으로 보존한다. 채택한 정의와 그 판단 근거를 연결하며 원문을 덮어쓰지 않는다.

## 5.1 식별과 버전

- equipmentInstanceId는 안정적인 설비 ID다. IP·주소·표시 이름과 분리한다.

- sourceId는 소스의 안정적인 ID다. 주소 변경 시 동일 신호인지 검토해 유지 여부를 결정한다.

- semanticId는 공통 개념 참조다. 측정값과 설정값처럼 역할이 다르면 구분한다.

- memberId는 의미 모델 내부 속성 ID다. 표시 이름과 개념 변경을 분리한다.

- mappingId는 설비별 연결 ID다. 초안 수정 번호와 승인 버전은 별개다.

- schemaVersion은 파일 형식 버전이고 version은 정의 내용의 버전이다.

승인 릴리스는 ID·버전·파일 해시를 고정하며 latest 같은 가변 참조를 쓰지 않는다. 주소 변경만으로 공통 의미 모델을 새로 만들 필요는 없지만 접근·매핑 개정과 검토는 필요하다.

## 5.2 소스 접근 정의

공통 필드는 sourceId, equipmentInstanceId, connectionProfileRef, accessProfileRef, access, rawRepresentation, evidenceRefs, revision이다. access.kind마다 별도 필수 필드를 검증한다.

| 종류 | 주요 필드 | 조건 |
|---|---|---|
| device-register | 영역·주소·주소 단위·워드 수·선택적 bitOffset | 모델·프로토콜별 진법·범위 |
| db-offset | 영역·DB 번호·바이트 오프셋·길이·선택적 bitOffset | 바이트/비트 및 DB 접근 조건 |
| symbol | 심볼 경로·원소/멤버 선택 | PLC·드라이버의 심볼 문법 |
| opcua-node | namespace URI·식별자 종류·값 | NodeId 종류 보존 |
| solution-tag | 솔루션 인스턴스·연결·태그 경로 | 하부 소스 관계 별도 보존 |

rawAddressText와 원본 진법을 근거로 보존한다. 진법이 불명이면 추정 확정하지 않는다. accessProfileRef는 벤더뿐 아니라 CPU 계열·모델·프로토콜·버전 조건을 담는다.

connectionProfileRef는 논리적인 연결만 참조한다. 암호·개인키·토큰은 계약에 포함하지 않는다. 구조적으로 타당한 정의와 실장치에서 읽기 가능한 정의를 구분한다. MVP는 실제 접속하지 않는다.

## 5.3 원시 표현과 디코딩

레지스터·바이트 접근에는 저장 타입·점유 길이·부호·바이트 순서·워드 순서를 명시한다. 이미 typed value를 제공하는 심볼·OPC UA 소스에 불필요한 바이트 디코딩을 적용하지 않는다.

필수 정보가 미확인이면 초안 저장은 가능하지만 승인 항목에 포함하지 않는다. 지원하지 않는 구조체·문자열·배열은 원문과 미지원 상태를 남긴다. MVP는 스칼라 또는 명시적으로 선택한 고정 배열 원소를 다룬다.

## 5.4 의미 정의

SemanticDefinition은 모델 ID·버전·설명·멤버 목록을 가진다.

| 멤버 필드 | 의미 |
|---|---|
| memberId | 안정적인 속성 ID |
| name | 상위 계약 이름 |
| semanticId | 공통 개념 참조 |
| description | 업무 설명 |
| valueType | 변환 후 타입 |
| unit | 단위. 해당 없음과 미확인 구분 |
| role | measurement, status, setpoint 등 |
| range 또는 enum | 의미에 맞는 값 제약 |

의미 사전은 대상 설비에 필요한 소수 개념으로 시작한다. 알려진 외부 개념 ID를 참조할 수 있다. local IRI 생성만으로 의미나 표준 적합성을 확인했다고 표시하지 않는다.

## 5.5 매핑 정의

MappingSet은 설비 인스턴스가 의미 모델 멤버를 어떻게 제공하는지 정의한다. MVP는 한 소스와 한 멤버의 연결이다. 여러 설비의 서로 다른 소스는 같은 의미에 연결할 수 있다.

한 설비·멤버의 활성 소스가 둘이면 모호함으로 처리한다. 조건부 소스 선택·이중화·다중 신호 계산은 후속 기능이다.

| 필드 | 내용 |
|---|---|
| mappingId | 연결 ID |
| sourceRef | 소스 ID·개정 |
| targetRef | 의미 모델·버전·memberId |
| transform | 순서형 변환 목록 |
| inputStage | raw 또는 already-engineered 등 |
| invalidValuePolicy | 오류·무효 코드·범위 이탈 처리 |
| evidenceRefs | 대응과 변환의 근거 |
| reviewRef | 확인 기록 |

디코딩은 저장 표현을 값으로 해석하고, 변환은 그 값을 상위 의미에 맞춘다. 둘을 하나의 type이나 scaling으로 합치지 않는다.

# 6 매핑 예시와 변환 규칙

다음은 설명용 가상 예시이며 실제 장치 허용 주소·바이트 순서 기본값이 아니다.

| 설비 | 접근 | 입력 | 변환 | 대상 |
|---|---|---|---|---|
| conveyor-a | D1000, 2워드 | INT32, 순서 명시 | ×0.1 | Motor.actualSpeed, Double, rpm |
| conveyor-b | DB10, byte 20, 4바이트 | FLOAT32, 순서 명시 | Double 변환 | 같은 멤버 |
| conveyor-c | Conveyor.Motor.ActualSpeed | typed FLOAT32, 이미 rpm | Double 변환 | 같은 멤버 |

공통 의미가 같아도 접근·변환·근거는 별개다. 같은 개념이라는 사실이 측정 위치·해상도·시점까지 같음을 뜻하지 않는다.

## 6.1 허용 변환

- linear: y = x × factor + offset. 계수를 십진수 문자열로 보존해 십진 연산하고 결과 타입 변환과 필요한 반올림 규칙을 명시한다.

- cast: 타입 조합·범위·오버플로 처리를 검증한다. 암묵적인 정수 절삭은 금지한다.

- bit-select: 디코딩한 정수의 비트를 선택한다. 접근 측 bitOffset과 이중 적용하지 않는다.

- enum-map: 원시 코드와 상태를 연결하며 미정의 코드 처리를 지정한다.

- 단위 변환: 입출력 단위를 명시하고 검증한 변환만 허용한다.

임의 스크립트는 실행하지 않는다. 고유 표현식은 원문과 unsupported-transform 상태로 보존한다. 무효값은 오류·품질로 처리하고 정상적인 0으로 바꾸지 않는다. 향후 Sparkplug 등으로 전달할 품질 표현은 별도 투영 계약으로 정한다.

## 6.2 이미 변환된 값

솔루션 태그의 engineering value와 PLC raw source를 구분한다. 이미 스케일된 태그를 선택하면 이전 변환을 중복 적용하지 않는다. derivedFrom과 근거로 둘의 관계를 남긴다. 관계가 불명이면 스케일 차이를 오류 확정하지 않고 upstream-transform-unresolved로 표시한다.

임의 애플리케이션의 전체 계보 자동 복원은 MVP 범위 밖이다.

# 7 계약 예시

아래는 MappingSet의 제안 형식이다. targetRef는 상위 semanticDefinitionRef의 모델·버전을 따른다. 승인 릴리스가 모든 참조 파일의 해시를 고정한다. 필드 이름과 스키마는 구현 전 계약 리뷰에서 확정한다.

```json
{
  "kind": "mapping-set",
  "schemaVersion": "1.0",
  "mappingSetId": "conveyor-a-motor",
  "version": "0.1.0",
  "equipmentInstanceId": "plant-a/line-1/conveyor-a/motor-1",
  "semanticDefinitionRef": {"id": "Motor", "version": "1.0.0"},
  "mappings": [
    {
      "mappingId": "actual-speed",
      "sourceRef": {"id": "source-speed-a", "revision": 2},
      "targetRef": {"memberId": "actual-speed"},
      "inputStage": "raw",
      "transform": [
        {"op": "linear", "factor": "0.1", "offset": "0"},
        {"op": "cast", "to": "Double", "overflow": "error"}
      ],
      "invalidValuePolicy": {"onError": "bad-quality"},
      "evidenceRefs": ["ev-address-map:B12", "ev-config:/tags/0"],
      "reviewRef": "review-speed-a-2"
    }
  ]
}
```

# 8 계약 교환과 승인 릴리스

| 계약 | 생산자 | 소비자 | 내용 |
|---|---|---|---|
| ObservationBundle | Týr importer 또는 확장 Mímir | Týr | 관측과 후보·근거 |
| MappingProposal | Týr | Bifrost | 정의·매핑·검토·기준 릴리스 |
| ValidationReport | Bifrost | Týr | 검사·차이·제안 해시 |
| MappingRelease | Bifrost | Týr·실행 소비자 | 승인 계약·버전·해시 |

MVP는 JSON·디렉터리 묶음으로 교환한다. proposal.json, semantic-definitions, sources, mapping-sets, evidence/index.json, reviews를 묶는다. 원본 문서 전체는 실행 계약과 분리된 증거 저장소에 둔다. 실행 환경은 원본 문서 조회에 의존하지 않는다.

## 8.1 검증과 발행

1. Týr가 파일 목록·해시·기준 릴리스를 고정한 제안을 생성한다.

2. Bifrost가 형식·참조·접근 프로파일·변환·의미·변경 규칙을 검사한다.

3. 검토자가 제안 해시를 승인한다. 변경되면 검사·승인을 다시 수행한다.

4. Bifrost가 묶음과 manifest를 발행한다. 일부 파일만 승인 상태로 노출하지 않는다.

5. 소비자는 모든 참조를 검증하고 하나의 릴리스를 사용한다.

제안 명령은 mapping validate, mapping publish, mapping diff다. 현재 존재하는 명령이 아니다. 내용 해시는 무결성을, 서명·신뢰 설정은 발행자와 승인 권한을 검증한다. 로컬 MVP의 확인 기록을 운영 등급 인증으로 설명하지 않는다.

동시 편집은 초안 revision으로 검출한다. 오래된 초안의 저장은 새 변경을 덮어쓰지 않고 충돌로 반환한다. 제출의 baseRelease와 현재 레지스트리가 다르면 재검토한다. 독립적으로 바뀐 필드라도 자동 승인 병합하지 않는다.

## 8.2 기존 계약과의 호환

기존 definition.schema.json은 접근·단위·매핑을 표현하지 않으며 추가 속성을 금지한다. 새 계약에 별도 형식 버전을 부여한다. 기존 UDT 투영은 손실 항목을 기록하고 그 게이트 PASS를 전체 매핑 승인으로 사용하지 않는다.

기존 소비자는 기존 계약을 유지하며 새 소비자는 지원 버전을 선언한다. Muninn 후속 기능은 승인 소스 선택·디코딩·변환·의미 멤버 발행이다. 현재 이름·타입 필터와 구분한다. 연결 비밀은 실행 환경에서 별도 공급한다.

잘못된 새 릴리스 때문에 실행 중인 승인 버전을 자동 폐기하지 않는다. 활성화·교체·복구는 후속 운영 단계에서 Bifrost 활성화 체계와 연결한다.

# 9 검증과 변경 정책

| 검사 | 예시 | 처리 |
|---|---|---|
| 참조·식별 | 소스 없음·다른 설비 연결 | 제출 오류 |
| 접근 완전성 | 진법·DB 번호 미확인 | 초안 허용, 항목 승인 차단 |
| 원시 표현 | 타입·점유 길이 불일치 | 제출 오류 |
| 변환 | 비트 범위 초과·결과 타입 불일치 | 제출 오류 |
| 의미 | 단위·상태 의미 불명 | 검토와 정책별 승인 차단 |
| 모호함 | 한 멤버에 활성 소스 둘 | 선택 규칙 없으면 차단 |
| 출처 | 원본 해시·위치 없음 | 확인 근거 불충분 |
| 부분 import | 누락 행·미지원 속성 | 집계하고 자동 성공 금지 |

같은 워드의 전체값과 비트 뷰는 의도적 중첩일 수 있다. aliasOf 또는 viewOf를 명시한다. 다른 PLC의 동일 주소는 충돌이 아니다. 점유 범위 검사는 등록 정의 안에서 수행하며 PLC 내부 로직 전체를 검증한다고 주장하지 않는다.

| 변경 | 처리 |
|---|---|
| 표시 이름·설명 | 개념 변경 여부 확인 |
| 주소·심볼 | 의미 유지 가능, 접근·매핑 개정과 재검토 |
| 원시 타입·순서 | 디코딩·범위·결과 재검토 |
| 스케일·단위 변환 | 값 의미·후단 이중 변환 재검토 |
| 업무 개념·결과 단위 | 의미 버전 또는 새 ID와 소비 호환성 검토 |
| 원문·import 프로파일 | 영향받는 기존 확인 근거 재검토 |

구조가 같아도 의미가 달라지면 검토한다. 현재 구조적 호환성 검사에 의미·접근·변환 변경 규칙을 추가한다.

# 10 사용자 화면

## 10.1 자료와 소스

사이트·설비의 작업 묶음에서 파일 개정·확보 시점·처리 범위·프로파일·오류·미지원 항목을 본다. 설비 정보가 없는 자료는 자동 귀속하지 않고 사용자가 연결 근거를 남긴다.

소스 목록 옆에 접근 종류별 폼과 원문 근거를 표시한다. 주소·DB·심볼을 같은 입력칸에 넣지 않는다. 원시 타입·이미 변환된 타입·미확인 필드를 구분한다.

## 10.2 의미와 매핑 작업대

왼쪽은 소스 목록, 가운데는 연결·디코딩·변환 편집, 오른쪽은 의미 모델과 멤버 목록이다.

| 영역 | 표시와 작업 |
|---|---|
| 소스 | 설비·연결·주소/오프셋/심볼·원시 타입·근거 |
| 매핑 | 소스와 대상 연결·변환 순서·샘플 결과·검증·확인 상태 |
| 의미 | 모델·버전·멤버·개념·설명·결과 타입·단위 |

기존 의미를 검색해 연결하거나 새 의미 후보를 작성한다. 여러 설비의 매핑을 나란히 비교한다. 표 편집·대량 적용도 동일 검증을 거친다.

미리보기는 입력 단계, 디코딩 값, 변환별 중간값, 결과 타입·단위·품질을 보여준다. fixture 시험을 실장치 확인으로 표시하지 않는다.

## 10.3 변경과 제출

기준 릴리스와 초안의 접근·변환·의미 차이를 구분한다. 원문과 이전 확인 기록을 보고 판단한다. 검사 결과를 제안 해시와 연결하고 수정 후 오래된 PASS·승인을 무효화한다. 승인 이후 편집은 새 초안으로 시작한다.

# 11 근거와 확인 상태

하나의 verified 플래그로 모든 상태를 합치지 않는다.

| 차원 | 상태 예시 |
|---|---|
| 추출 | extracted, partial, unsupported |
| 대응 | unlinked, suggested, confirmed, disputed |
| 검토 | draft, reviewed, needs-review |
| 승인 | unsubmitted, submitted, approved, rejected |
| 실장치 | not-performed, confirmed-at-time |

MVP의 실장치 상태는 not-performed다. 자료 대조 확인은 제공된 자료의 관계를 사람이 확인한 상태다. 자료 기준 시점을 화면과 리포트에 표시한다.

검토에는 대상 해시·확인자·시점·사유·근거를 기록한다. 새 개정에 이전 확인을 무조건 복사하지 않는다. 변경되지 않은 항목은 기존 기록을 참조할 수 있고 변경된 필드·근거는 재검토한다.

# 12 MVP 범위와 단계

## 12.1 포함 범위

- 설비 2~3대와 300~1,000개 태그를 계획 기준으로 한다.

- 주소·DB 오프셋·심볼 접근 모델과 수동 편집을 제공한다.

- 실제 경험한 PLC·드라이버 조합의 프로파일부터 검증한다. 세 표현 지원을 세 벤더 실장치 지원과 동일시하지 않는다.

- XLSX 한 양식과 실제 보유 설정 export 하나를 수용한다.

- 소수 의미 모델·스칼라 매핑·제한된 변환·독립 fixture 미리보기를 제공한다.

- 원문 근거·미지원 목록·개정 비교·검토·Bifrost 제안과 로컬 승인 경계를 구현한다.

- 자료/소스, 의미/매핑, 변경/제출의 세 작업 화면을 제공한다.

## 12.2 후속 범위

PDF·OCR, 추가 제품, Mímir 관측 입력, 복합 타입·배열, 다중 소스 계산, 운영 인증, 실장치 시험, Muninn 소비, 기존 설정 생성·배포는 후속 단계다.

오프라인 모드는 live connector를 구성하지 않는다. 파일의 매크로·외부 링크·스크립트·외부 엔티티를 실행하거나 조회하지 않는다. AI는 선택적 후보 생성으로 사용하며 승인된 환경만 사용한다. 원본 전체 외부 전송은 기본 동작으로 두지 않는다.

| 단계 | 결과 | 다음 조건 |
|---|---|---|
| A 계약·수동 작성 | 세 접근·의미·매핑·기본 화면 | 같은 의미에 세 접근을 저장·검증 |
| B 파일 수용 | XLSX·설정 import·근거·누락 집계 | 전체 처리 상태 설명 가능 |
| C 검토·승인 | diff·검토·Bifrost 연결 | 변경 후 승인 무효화·릴리스 고정 |
| D 현장 업무 평가 | 시간·정확도·부담 측정 | 확대 또는 보완 결정 |

개발자 1명, 정기적인 현장 담당자 참여, 지원 파일 확보를 가정한 제한 PoV는 4~6주를 계획 출발점으로 삼는다. 실제 파일의 상속·스크립트·암호화 복잡도를 확인해 재산정한다.

# 13 수용 시험과 현장 검증

## 13.1 수용 시험

| ID | 시험 | 기대 결과 |
|---|---|---|
| A01 | 네 접근을 같은 의미에 연결 | 공통 결과와 개별 접근 보존 |
| A02 | 다른 PLC의 같은 주소 | 다른 소스로 유지 |
| A03 | 이름이 다른 같은 의미 | 이름 동일성에 의존하지 않음 |
| A04 | 주소 변경 | 의미 유지 가능, 매핑 재검토 |
| A05 | 스케일 변경 | 타입이 같아도 영향 표시 |
| A06 | 진법·단위·타입 미확인 | 초안 허용, 항목 승인 차단 |
| A07 | 전체 워드·비트 뷰 | 명시적 alias/view 허용 |
| A08 | 이미 변환된 태그 | 이중 변환 검토 근거 제공 |
| A09 | 파일·상속·참조 누락 | 입력 불완전 표시 |
| A10 | 독립 기준값 평가 | 값·타입·단위·품질 일치 |
| A11 | 검사·승인 후 파일 변경 | 이전 결과 재사용 불가 |
| A12 | 릴리스 일부 누락·변조 | 소비 검증 실패, 부분 적용 없음 |
| A13 | 동일 자료 재처리 | 고정 프로파일·결정으로 같은 결과 |
| A14 | 네트워크 차단 | 모든 오프라인 기능 완료 |
| A15 | 미지원 행·속성 | 전체와 처리 상태 건수 일치 |
| A16 | 동시 수정·오래된 기준 | 변경 덮어쓰기 대신 충돌 표시 |

fixture 기대값은 동일 생성기에만 의존하지 않는다. 독립적으로 확인한 바이트·원시값·결과를 포함한다. AI 결과는 모델·프롬프트·결정 버전을 보존하고 승인된 추출 결정을 재사용한다. 외부 모델의 반복 호출을 결정론으로 가정하지 않는다.

## 13.2 현장 절차

1. 문서와 설정이 모두 있는 설비를 선정하고 자료 시점을 고정한다.

2. 수작업의 의미 확인·개정 검토 시간과 문의·미확인 항목을 기록한다.

3. 담당자가 주소·타입·스케일·상태·alias를 포함한 50~100개 기준 항목을 확인한다. 미확정은 분리한다.

4. 조정용과 아직 보지 않은 평가용 설비·개정본을 나눈다.

5. 비슷한 난이도의 업무 묶음으로 수작업·도구 사용 순서를 교차한다.

6. 실제 개정본으로 유지·변경·재검토 항목을 확인한다.

7. 다음 설비·사이트의 프로파일·어댑터 추가 비용을 측정한다.

| 지표 | 정의 | 목표 제안 |
|---|---|---|
| 처리 완전성 | 전체 입력의 상태 집계 | 100% 집계 |
| 근거 추적 | 결과에서 원문 위치 확인 | 항목마다 연결 |
| 매칭 정밀도 | 후보 중 확인된 연결 비율 | 자동 후보 구간 95% 이상 |
| 매칭 범위 | 가능한 연결 중 제안 비율 | 정밀도와 별도 보고 |
| 검토 총시간 | 수정·문의·오탐 포함 | 수작업 대비 30% 이상 단축 |
| 변경 검토 | 새 개정 영향 확인 시간 | 기준선과 비교 |
| 재사용 비용 | 다음 설비·양식 추가 시간 | 공통 엔진 수정과 분리 |

수치는 PoV 목표이며 실적이나 자동 운영 승인 기준이 아니다. 통제된 오류 사본의 검출 성능과 실제 자료의 발견 실적을 따로 보고한다. 샘플 무오류를 전체 설비 보장으로 확대하지 않는다.

# 14 기존 기능 활용과 정비

| 영역 | 활용 | 추가 |
|---|---|---|
| 원본·버전 | 기존 저장소·Git·OT 구성 관리 | 설비·개정·근거 인덱스 |
| 추출 | 라이브러리·제품 export | 현장 프로파일·관측 어댑터 |
| 후보 | Mímir 타입 도출 | 접근·근거·후보 상태 |
| 승인 | Bifrost 기반 | 새 계약·매핑 규칙 |
| 비교 | model-reconcile | 이름이 다른 연결·접근·변환 대조 |
| 실행 | 기존 어댑터·솔루션·Muninn | 승인 매핑 소비 |
| 화면 | 기존 UI 프레임워크 | 접근 폼·매핑·근거·변경 검토 |

기존 제품의 정보 보존·검토·export를 샘플로 평가하고 충분하면 재사용한다. 독립 도구라는 정체성이 모든 기능의 자체 구현을 요구하지 않는다.

정비 대상은 다음과 같다.

- 엣지 정보모델링 전략: source D100 예시를 접근·의미·매핑으로 분리한다.

- IT OT 거버넌스 보고서: 제품 역추출을 출처 있는 관측으로 수용하고 권위와 입력 경로를 구분한다. 기존 제품이 없다는 단정 대신 기능 평가 후 공백 구현 기준을 둔다.

- Mímir README: 현재 도출과 후속 관측 계약을 구분한다.

- Bifrost 계약·README: UDT 검증과 전체 매핑 검증을 구분한다.

- ADOPTION: 파일만으로 시작하는 경로를 추가한다.

- Muninn README: 현재 이름·타입 검사와 후속 매핑 소비를 구분한다.

첫 설정 형식은 실제 자료와 검토자가 있는 제품 하나로 선정한다. 의미 사전은 대상 설비에 필요한 범위로 시작한다. 초안은 Týr 로컬 저장소, 승인 계약은 Bifrost, 전달은 파일·CLI를 기본으로 한다.

# 15 구현 근거

기준은 로컬 Yggdrasil의 다음 소스와 문서다. 이 설계는 기존 소스의 변경을 포함하지 않는다.

| 저장소와 경로 | 관련 내용 |
|---|---|
| mimir README.md | 설계시점 후보 생산자 |
| mimir MimirMain.java | live derive CLI |
| mimir OpcUaMixerBrowser.java | 타입·멤버·EURange 관측 |
| mimir DefinitionDeriver.java | local IRI 생성 |
| mimir Member.java·BrowsedMember.java | 현재 필드 범위 |
| bifrost definition.schema.json | 기존 UDT 계약·추가 속성 제한 |
| bifrost CompatibilityChecker.java | 구조적 변경 검사 |
| bifrost ModelReconciler.java | 정규 멤버 대조 |
| bifrost IgnitionUdtAdapter.java | 설정 정보 투영 범위 |
| bifrost docs/ADOPTION.md | 도입 순서·파일 비교 |
| muninn README.md·EgressValidator.java | 일회성 feeder·이름/타입 검사 |

관련 공개 저장소: [Mímir](https://github.com/yggdrasil-iiot/mimir), [Bifrost](https://github.com/yggdrasil-iiot/bifrost), [Muninn](https://github.com/yggdrasil-iiot/muninn).

현재 구현과 제안 기능은 3절에서 구분한다. 최초 계약 리뷰에서는 접근 종류별 필수 필드, 단위 코드, 타입 어휘, 변환 연산, 승인 권한과 릴리스 형식을 확정한다.

## P0·P1 검증 관점 개정

P0·P1의 완료 기준은 [정준 모델 검증 기준](docs/P1-GOVERNANCE-CRITERIA.md)이다. 문서·설정의 이질 정의가 같은 정준 의미로 수렴하고 다른 의미는 구분되며 수치·투영 손실과 의미·변환 변경을 탐지하는지 검증한다. 실제 장치 통신은 이번 완료 조건에서 제외한다. 실제 현장 원본·버전·검토자는 P4/P7에서 대표성과 실무 수용성을 보강하는 조건이다.

## 다중 프로퍼티 객체와 단위 변환

단일 값 UI 제한을 제거했다. SemanticDefinition.members[]와 MappingSet.mappings[]로 D1000/D2000/D3000 등 분산된 소스를 같은 객체의 다른 프로퍼티에 연결한다. 1.1.0은 명시적 단위 변환을 추가한다. 최신 상세는 [객체 매핑](docs/OBJECT-MAPPING.md)을 따른다.


## 매핑 패턴 지원 경계와 모델 확장 결정 (2026-10-17)

현재 구현 범위의 기준은 [매핑 지원 매트릭스](docs/MAPPING-SUPPORT-MATRIX.md)와 [기계 판독 카탈로그](fixtures/mapping-patterns/matrix.json)다. 16개 매핑 패턴과 객체 식별·미해석 보존이라는 2개 공통 요구를 구분한다. 이 절은 확장 설계이며 계약 1.0.0·1.1.0의 구현 완료를 선언하지 않는다. 현재 JSON Schema와 저장 API는 그대로 유지한다.

### 현장 패턴을 모델에 반영하는 방식

D1000(actual), D2000(target), D3000(state)를 한 객체의 세 프로퍼티로 매핑하는 것은 현재 지원한다. 이는 프로퍼티마다 한 소스를 바인딩하는 객체 조립이다. D1000(low)과 D2000(high)를 합쳐 하나의 UInt32를 만드는 것은 다중 입력 디코딩이며 현재 단일 sourceRef 계약으로 표현할 수 없다. 압력 A-B 같은 파생값도 별도 다중 입력 연산이다. 세 형태를 같은 기능으로 표시하지 않는다.

다음 계약 개정의 논리 모델은 다음과 같다. 아래 이름은 제안 필드이며 현재 wire 필드가 아니다.

| 계층 | 모델 책임 | 확장 요구 |
|---|---|---|
| 원문·관측 | 파일 바이트, 해시, 위치, 원래 이름·표현식, 추출기·시점 | 해석 실패도 원문을 보존하고 unresolved로 남김 |
| 접근·원시 표현 | 설비·논리 연결·접근 프로파일 + 주소/심볼/NodeId, 타입·길이·순서 | native bit와 word bit를 구분하고 codec·배열 shape 명시 |
| 변환 그래프 | 이름 있는 입력 참조와 타입 있는 제한 연산 | decode / derive / select 구분, 비순환 검증, 입력별 근거 |
| 의미 모델·인스턴스 | 의미 URI·역할·단위·타입·경로 + 객체 식별 | 모델 재사용과 인스턴스 식별을 분리 |
| 매핑·검토·릴리스 | 소스/그래프 결과 → 대상 경로, 변환 손실·변경·능력 요구 | 미해석/미지원 상태의 승인 차단과 수신자 능력 검증 |

객체 식별 키를 equipmentInstanceId만으로 결정하면 같은 설비의 Motor1·Motor2를 구분하지 못한다. 제안 targetInstanceId는 주소·화면 이름과 독립적인 안정된 ID이며 대상 키는 (equipmentInstanceId, targetInstanceId, semanticDefinitionRef, memberPath)로 삼는다. semanticId는 개념을 식별하고 targetInstanceId는 실물 또는 논리 객체를 식별한다. 프로퍼티 경로는 중첩/배열용 구조화 경로로 설계하며 문자열의 점·괄호를 무조건 파싱하지 않는다. 기존 멤버를 옮기거나 객체를 병합하는 변경에는 명시적 이전 ID와 검토 기록이 필요하다.

단일 입력 MappingSet을 임의로 다중 sourceRef 배열로 바꾸지 않는다. 별도 그래프 제안에서 입력 이름·순서·타입·단위·출처를 명시한다. 객체 조립은 필드별 결과를 보존하고, 다중 주소 디코딩은 바이트/워드 순서와 폭을 검증하며, 파생값은 단위 차원·결측·0 나눗셈·범위·정밀도를 검증한다. selector는 선언된 후보 목록과 인덱스 범위만 허용한다. 임의 Python/JavaScript/SQL 실행은 범위 밖이다.

템플릿은 base·stride·offset·매개변수 타입 및 허용 범위와 인스턴스 override를 분리한다. 원본 템플릿, 해석에 사용한 매개변수, 최종 전개 결과와 override 근거를 함께 보존한다. 해석되지 않은 식을 주소로 추정하거나 0/default로 채우지 않는다. alias/viewOf는 참조 체인·최종 대상·순환·끊긴 참조를 검증한다. 현재 P1의 viewOf 존재 확인만으로 순환 검증이 완료됐다고 보지 않는다.

### 값·시간·품질과 손실

원시 바이트, decoded 값, engineering 값, canonical 값의 단계를 구분한다. BCD 오류, 문자열 잘림/인코딩, 시간대 누락, 정수 오버플로, 스케일 중복, 단위 불일치를 각각 결과와 진단으로 남긴다. rawRepresentation의 byteOrder/wordOrder와 native bit 위치는 같은 좌표가 아니다. 예를 들어 native byte bit와 디코딩 후 정수 bit를 구분하는 fixture를 둔다.

분산 객체를 한 JSON으로 묶었다고 원자적 snapshot이 되지 않는다. 향후 모의 DataValue에는 입력별 value/status/sourceTimestamp/serverTimestamp와 sampleId 또는 sequence를 두고, 조립 정책은 허용 skew·freshness·필수 입력·bad 품질 전파·부분값 허용을 명시한다. trigger/sequence 기반 레코드는 가상 입력으로 latch·불변 결과만 시험한다. 실제 PLC handshake·쓰기·스케줄링·통신 시각 측정은 제외한다.

변경 비교는 source→graph→memberPath→targetInstance→release의 의존성을 추적한다. 이름 변경과 의미 URI·역할·단위 변경을 구분하고, 템플릿/alias 변경이 영향을 주는 인스턴스·프로퍼티를 계산한다. 표현 불가능한 변환·시간 정책을 기존 Bifrost 모델에 투영할 때는 field-loss와 승인이 필요한 손실을 명시한다. 무손실이라고 추정하지 않는다.

### 화면과 계약 경계

현재 P2 비교 화면에는 네 PLC의 8개 프로퍼티와 원문 이름·단위·변환을 보여준다. 후속 화면은 객체 ID/경로 편집, 원문↔해석 결과, 템플릿 전개/override, 입력별 디코딩 단계, 다중 입력 그래프와 미해석 진단을 단계별 추가한다. UI 작성·API 저장·정적 검증·샘플 평가가 모두 확인돼야 해당 지원 축을 yes로 올린다.

Týr는 위 정의·근거·변경의 작성과 오프라인 검증을 소유한다. Mímir는 후보를 제공하며 그 후보가 정준 의미를 자동 확정하지 않는다. Bifrost는 승인·버전·릴리스 권한을 갖는다. Muninn은 향후 승인된 계약을 소비하며 이번 작업에서 실행 엔진이나 통신 어댑터를 구현하지 않는다. 각 프로젝트 코드는 독립적으로 유지하며 published 계약과 fixture만 교환한다.

신규 필드는 새 계약 버전 검토·마이그레이션 예시·수신자 capability 협의를 거쳐 도입한다. 기존 1.0.0/1.1.0 문서를 같은 버전으로 확장하지 않는다. 구 소비자가 알 수 없는 op/codec/시간 정책은 제출/수용 시 실패해야 한다. fixtureSpecVersion은 시험 명세 버전이며 제품 schemaVersion과 무관하다. 실제 제품 export 검증 전에는 제품 전체 호환성을 주장하지 않는다.

## P3-A 계약 구체화

이전 절의 제안 중 target-instance·memberPath·값 그래프를 2.0.0 작성 계약으로 구현했다. [P3-A 계약](docs/P3-A-CONTRACT.md)이 정확한 필드·op·검증·이전 경계를 정의한다. 평면 프로퍼티, raw UInt16 low/high 조합, identity만 이번 범위다. UI/SQLite 2.0 작성·일반 디코더·승인/릴리스는 후속이며 실제 장치 통신은 제외한다.

## P3-A 2.0 작성 경로 구현

[객체·그래프 작성과 SQLite 이전](docs/P3-A-WORKSPACE.md)을 구현했다. workspaceVersion으로 1.x/2.0 경로를 분리하고 기존 접근·의미 폼과 변환 편집기를 재사용한다. target-instance/value-graph는 새 화면·저장 컬렉션이며 명시적 이전과 SQLite backup·revision CAS·이전 이력을 제공한다. 파일 계약 단계에서 후속으로 남긴 UI/저장 작업은 이 확장으로 완료했다. 실제 장치 통신은 제외한다.

## P3-B 미리보기 실행 경계

[가상 바이트·변환 preview](docs/P3-B-PREVIEW.md)를 구현했다. 입력·정렬·디코딩·codec/bit·그래프·변환·cast·정준 결과를 별도 trace 단계로 기록한다. 새 2.1 source-definition은 codec/native bit 좌표를 명시하며 기존 계약 버전은 보존한다. Decimal 중간값과 실제 IEEE 폭을 비교해 손실을 탐지한다. revision·작성본/입력 해시를 고정한 read-only 응답이며 실제 장치 통신·승인·릴리스를 실행하지 않는다. good/uncertain/bad는 가상 평가 결과이고 실제 수집 시점·OPC 품질의 의미는 P3-D에서 별도 설계한다.

## P3-C 제한 파생값 구현

[2.2 계약과 파생값 작성](docs/P3-C-DERIVED.md)을 구현했다. 그래프의 이름 있는 입력·출처와 기존 디코딩/매핑 cast/SQLite revision을 재사용하고, 입력별 linear/unit-convert 및 subtract를 추가했다. 압력 Pa/kPa/bar·무차원 1의 같은 단위에서만 차이를 계산하며 unknown/타입/결측을 추정하지 않는다. Decimal 중간값과 최종 cast 손실을 단계별 기록한다. sqrt/clamp·일반 단위 차원 분석·온도 delta·시간/품질·승인 연계는 후속이다.

## P3-D 시간·품질 평가 경계

[가상 DataValue·시간 정책](docs/P3-D-TIME-QUALITY.md)을 구현했다. temporalPolicy를 매핑에 명시하고 실제 현재 시각 대신 evaluationContext.at을 고정한다. source/server 시각을 구분하고 age/skew·결측·bad·uncertain·가상 sequence를 검사한다. 시간·품질 오류는 수치 계산 전에 차단하며 파생 시각/원자성을 추정하지 않는다. 2.3 작성 계약과 별도 가상 시나리오를 기존 SQLite에 추가한다. Mímir/Bifrost/Muninn의 실제 실행·품질 수신은 확장하지 않는다.

## P3-E 고정 scalar 배열

[2.4 배열 계약](docs/P3-E-FIXED-ARRAYS.md)을 구현했다. source에 고정 저장 형상을 명시하고 array-element로 scalar를 선택해 기존 의미 프로퍼티로 매핑한다. byte/word16/Typed-slot stride와 lowerBounds·exclusive 저장 끝을 구분한다. 값 선택 후 기존 디코더를 적용하며 전체 배열의 endian 재정렬이나 NodeId/심볼 주소 자동 합성을 하지 않는다. 기존 JSON 저장과 시간·품질 정책을 재사용하며 native 구조·중첩·동적 selector·실제 수집은 후속이다.

## P3-F 유한 후보 선택

[graph 2.5 bounded selector](docs/P3-F-BOUNDED-SELECTOR.md)는 가능한 후보 전체의 계약과 실제 선택 출처의 값·시간·품질을 구분한다. 1~32 scalar 후보, 정수 인덱스, 범위 초과 정책과 이전 인덱스 비교를 저장한다. 기존 객체 의미·SQLite·시나리오를 재사용하고 장치 통신 및 승인 경계는 확대하지 않는다.

## P4-A 파일 정의와 근거 보존

[파일 가져오기 설계](docs/P4-A-FILE-IMPORT.md)는 원본·관측·채택 초안을 분리한다. 새 import-batch/proposal 2.6은 raw bytes/hash·locator·template/alias 경로·미해석을 보존한다. 기존 source/semantic/graph/mapping과 SQLite CAS를 재사용한다. 파일 해석 결과는 모두 draft이며 미해석은 승인 차단 finding으로 남긴다. Mímir·Bifrost·Muninn의 역할과 실제 통신 경계는 확대하지 않는다.

## P4-B 혼합 소스와 방향 경계

[2.7 계약](docs/P4-B-MIXED-SOURCES.md)은 PLC/상수/솔루션 태그/외부 값을 하나의 읽기 모델로 연결한다. 상수는 정의 사실로 시간 관측과 구분하며 SQL은 원문으로만 보존한다. write-definition은 의미 → 목적지의 별도 변환·근거이며 execution=excluded다. read-write capability는 승인/인가가 아니다. 기존 객체·매핑·근거·SQLite와 스파인 역할을 재사용한다.


## P5 변경 비교와 검토

불변 기준본·변경 분류·전이 의존 해시·담당자 검토 이력을 추가했다. 기존 계약/작성본은 유지하고 2.8.0 review-baseline/change-assessment/change-review는 별도 로컬 audit 계약이다. Bifrost 승인·장치 통신·SQL·쓰기 실행은 제외한다. [P5 설계](docs/P5-CHANGE-REVIEW.md), [검증](docs/verification/P5-RESULTS.md).


## P6 오프라인 Bifrost 연계

선택한 매핑/근거를 파일로 고정하고 Bifrost가 독립 수신 검증·두 등록 키의 서명 승인·불변 릴리스 발행을 담당한다. Týr는 승인 권위를 만들지 않는다. 기존 작성본/검토/시나리오는 보존한다. [설계](docs/P6-BIFROST-PUBLICATION.md) · [검증](docs/verification/P6-RESULTS.md). 실제 장치·외부 SQL·쓰기 실행·운영 활성화는 제외한다.


## P7 오프라인 수용 기록

A01~A16의 fixture 실행과 화면·저장 경로를 검증했다. 14개 충족, A07 전체 워드/비트 view 및 A14 PC 전체 네트워크 격리는 부분 충족이다. 실제 현장 PoV는 미수행이다. [수용 결과](docs/verification/P7-RESULTS.md)와 [재현·현장 절차](docs/P7-OFFLINE-ACCEPTANCE.md)를 따른다. 기존 2.9.0 이하 계약과 SQLite 스키마는 유지한다.


## A07 후속 지원 (2026-10-18)

[2.10 명시적 source view](docs/A07-SOURCE-VIEWS.md)는 PLC 정수 워드의 alias/bit 관계를 부모 id/version 및 접근 snapshot과 함께 저장한다. 논리 Boolean 결과와 원시 저장 타입을 구분하고, 원본 입력/시각/품질을 재사용하며, 부모 변경·범위·순환·근거와 Bifrost 서명 발행을 검사한다. SQLite 자동 변환·운영 활성화는 수행하지 않는다. [A07 실행 시점 수용 결과](docs/verification/A07-RESULTS.md)는 A07 충족, A14 부분 충족으로 기록하며, 현재 판정은 아래 A14 후속을 따른다.


## P7 A14 구현 주석 — 2026-10-18

[격리 수용 설계](docs/A14-NETWORK-ISOLATION.md)와 [결과](docs/verification/A14-RESULTS.md)를 현재 기준으로 추가한다. 기존 A07/P7 실행 시점의 부분 충족 기록은 역사적 증거다. 브라우저·Python·Java를 실제 OS network namespace로 격리해 localhost 작성/저장/preview/독립 검증/서명 승인/파일 발행을 확인했고, 기존 지원 범위의 A01~A16 오프라인 수용은 16개 충족이다.

기존 62개 Schema·SQLite 스키마·Bifrost jar는 유지했다. frontend/views.js의 기존 view 편집 ID 처리만 수정했다. date-time/uri 검사기는 테스트 이미지의 명시적 의존성과 preflight로 고정했다. 앱은 계속 JSON·파일·CLI로만 결합한다. 실제 현장 PoV와 목표 Windows PC 전체 방화벽 수용은 별도 미수행이며 장치 통신·외부 SQL·쓰기 실행·운영 활성화는 제외한다.


## P3-C B: 제한된 비선형 파생 노드

[2.11.0 설계](docs/P3-C-BOUNDED-MATH.md)를 추가한다. 기존 그래프·근거·시간/품질·최종 cast와 workspace 2.0.0·SQLite CAS를 재사용한다. sqrt는 known 무차원 1만 받아 Decimal 34자리 half-even으로 평가하고 근사 손실을 남긴다. clamp는 같은 known 단위의 명시적 decimal 하한·상한을 적용하고 clipping을 loss.clamp로 남긴다. 범위 역전·타입/단위 불일치·음수 sqrt는 거부한다. 화면에서 작성·저장·재조회·가상 preview하고 Bifrost가 JSON 계약을 독립 검증·서명 승인·파일 발행한다. 기존 graph 계약을 수정하지 않으며 DB migration은 없다. 일반 식/차원 추정·vendor 실장치 검증·활성화는 별도다.


## P3-E B 논리 정준 구조

[2.12 설계](docs/P3-E-LOGICAL-STRUCTURES.md)를 추가한다. 분산 source/graph 결과를 inline Structure/StructureArray의 scalar 말단에 연결하며, 객체 ID와 전체 member/index 경로로 대상을 식별한다. 고정 shape/lowerBounds와 깊이/크기 제한을 명시한다. 화면·SQLite·개별/객체 가상 preview·독립 Bifrost 수신 검증을 지원한다. 미매핑은 초안으로 보존하되 발행을 막고, bad/결측인 객체의 result와 진단 partialResult를 구분한다. 시간·품질은 바인딩 정책 범위이며 전체 원자 snapshot을 추정하지 않는다. 기존 계약/저장 스키마는 보존하고 vendor native 배치 검증·현장 PoV·장치/SQL/쓰기 실행은 별도로 유지한다.


## P3-F B 유한 후보 그래프

[2.13 계약과 실행 경계](docs/P3-F-GRAPH-CANDIDATES.md)는 같은 그래프의 scalar DAG 출력과 직접 소스를 최대 32개 후보로 선택한다. 모든 후보의 타입·단위·근거를 정적으로 검사하고 선택된 경로에만 시간·품질·손실을 적용한다. 후보 참조·계산 정의 해시·실제 선택 source refs로 출처 변화를 표시한다. 기존 SQLite JSON/CAS와 Bifrost 독립 승인·파일 발행을 재사용한다. 임의 주소식·장치 통신·외부 SQL·쓰기 실행과 현장 PoV는 별도다.


## P4-A B 미해석 해결·재가져오기 병합

[2.14 workflow 계약](docs/P4-A-IMPORT-RECONCILIATION.md)은 원본 관측을 고정하고 검토 이력과 이전/현재/새 파일 비교를 보존한다. 안정된 recordKey와 canonical sourceId로 충돌 선택·현재 정의 유지·제거 보존/재등장을 처리한다. 기존 SQLite JSON/CAS와 parser·P6 closure를 재사용하며 Java는 wire 데이터만 독립 검증한다. 현장 vendor 문법/의미 정답과 장치 통신·외부 SQL·쓰기 실행은 별도다.


## P6 후속: 중단 복구와 파일 보존

[복구·GC 설계](docs/P6-RECOVERY-GC.md)는 Bifrost의 파일 발행에 저널과 기준 head CAS 복구를 추가한다. Týr는 SQLite 제출 row를 보존하고 13 화면에서 무결성·고아 폴더 조회/격리를 제공한다. 양쪽 GC는 과거 승인·릴리스·원본 근거를 삭제하지 않고 임시 고아 자료만 가역적으로 격리한다. 기존 정준 계약·SQLite 테이블은 유지한다. 프로세스 중단 수용과 전원 손실 durability·운영 IAM·외부 anchor·실제 현장 PoV는 분리한다.


## P7 독립 정답 기반 평가 준비

[평가 도구·계약](docs/P7-EVALUATION-PREPARATION.md)은 의미·정의 pin·가상 결과와 손실 진단을 별도 oracle로 대조한다. 16 화면과 CLI에서 현재 SQLite 저장본을 읽기만 하고 로컬 pack/report를 내보낸다. 정답 양식은 기대값을 생성하지 않는다. [현장 절차](docs/P7-POV-PROTOCOL.md)와 익명화 인수 양식은 준비하되 실제 자료·담당자 정답·검토 시간 PoV는 미수행으로 유지한다. calibration/evaluation/heldout·정답 범위·미측정 분모를 구분하며 승인 권위·기존 canonical 계약·SQLite 테이블을 확장하지 않는다.


## P3-C C 제한 산술 확장

[2.15 산술 계약](docs/P3-C-BOUNDED-ARITHMETIC.md)은 add/multiply/divide를 유한 scalar 그래프로 추가한다. 단위 1과 명시한 선형 단위만 지원하며 divide의 34자리 half-even·0 분모·근사/최종 cast 손실을 구분한다. 기존 source/semantic/mapping·SQLite/CAS·가상 품질/시간·P6 승인 계약을 재사용하고 Bifrost는 데이터 계약을 독립 검증한다. 일반 식/차원 추론·온도 delta·실제 현장 의미/계수 PoV는 별도다. 장치 통신·외부 SQL·쓰기 실행은 계속 제외한다.


## P6 전역 의미 카탈로그

[카탈로그 설계](docs/P6-SEMANTIC-CATALOG.md)는 하나의 registry 전체 보존 릴리스에서 URI 계약을 파생 조회하고 승인·발행·복구 시 교차 스트림 충돌을 검사한다. 중첩 scalar·구조/배열 서명과 원본 릴리스 근거를 13 화면에 표시한다. 기존 계약·SQLite 테이블을 유지하며 현장 의미 정답·URI 소유권·외부 catalog 연합은 별도다.


## P3-C D 제한 수식 작성

[수식 작성 설계](docs/P3-C-BOUNDED-EXPRESSION.md)는 명시적 소스 참조·사칙연산/괄호·sqrt/clamp/linear 문법을 기존 2.15 DAG로 컴파일한다. 17 화면과 로컬 SQLite 원문/컴파일 이력·stale 비교를 추가하고 05/06/09/13 기능을 재사용한다. Bifrost는 기존 JAR/계약으로 DAG만 독립 검증하며 수식을 실행하지 않는다. 일반 차원 추론·온도 delta·cross-graph·현장 PoV는 미완료다.


### P3-C E 상수 수식 작성 확장

[상세 설계](docs/P3-C-EXPRESSION-LITERALS.md). 작성 compiler 1.1은 bare decimal(무차원)과 quantity(숫자, 명시적 단위)를 기존 2.7 상수 소스 및 2.15 그래프로 낮춘다. 생성 상수/원문 위치와 이력은 로컬 1.1 recipe, 원자 CAS 저장과 stale 탐지를 사용한다. 기존 1.0·정준 계약·SQLite 호환 유지. 단위 추측·일반 차원 분석·온도 delta·장치 통신·외부 SQL·쓰기 실행은 제외한다.


### P3-F C 그래프 간 결과 재사용

[상세 설계](docs/P3-F-CROSS-GRAPH.md). 2.17 endpoint로 같은 설비의 다른 graph ID/버전/결과 노드를 고정한다. 정적 dependency 순서·순환/설비/타입/단위/근거 검증은 독립 Python/Java가 수행한다. SQLite JSON/CAS와 기존 source·mapping·review·발행 closure를 재사용하고, 가상 preview에서 원본 입력·producer/consumer·참조 trace를 연결한다. 구 계약·recipe·DB 보존, 현장 PoV 별도, 실제 통신·외부 SQL·쓰기 실행·활성화 제외.


## P6 의미 URI 개정·폐기

[구현 계약과 경계](docs/P6-SEMANTIC-LIFECYCLE.md): 의미 signature는 고정하고 2.18 불변 개정 이력·명시적 대체 URI·사용 중단 권고·폐기를 관리한다. 18 화면에서 로컬/발행 이력과 읽기/쓰기·중첩 조상 영향, 현재 head/과거 릴리스를 구분한다. 기존 CAS·SQLite JSON 및 Bifrost 서명 승인·발행을 재사용하며 registry 전체 이력을 발행 시 재검사한다. lifecycle-only 제안도 허용한다. 폐기는 신규 계약의 승인·발행을 차단하고 실행 중인 설비를 변경하지 않는다. 실제 조직 정책·의미 정답·현장 PoV는 별도다.


매핑 템플릿과 적용본: [2.19 설계·작업자 UX·계약 경계](docs/P6-MAPPING-TEMPLATES.md). 공통 정의를 고정하고 설비 입력을 연결하며, 명시적 갱신 후 기존 Bifrost 승인·발행 경로를 사용한다.


## 레코드·결과 집합의 정준 객체 매핑 (2.20)

[상세 계약·UX·경계](docs/P4-C-RECORD-MAPPINGS.md). PLC 외부 값의 단일 scalar 정의에 더해, 선언된 결과 스키마의 복합 키·필드 바인딩과 0/1/N 정책으로 객체 또는 bounded 객체 배열을 구성한다. 기존2.19 템플릿·의미 모델·값 그래프를 재사용하고 기존2.0 workspace/SQLite 및 계약은 보존한다. 가상 입력과 선언의 승인 묶음을 분리하며 독립 Java Bifrost가 이력·생성물·의미 URI 정책을 검증한다. 실제 DB 접속·외부 SQL·쓰기 실행·현장 PoV는 포함하지 않는다.


## 여러 소스의 한 객체 매핑 (2.21)

[설계·계약·UX](docs/P4-D-MIXED-OBJECTS.md). PLC·가상 DB 레코드 필드·상수·외부 값·그래프를 기존 target/memberPath와2.19 템플릿 슬롯에 함께 연결한다. 레코드 필드는 원본 정의 버전/SHA·키 선택·필드/NULL 정책으로 고정한 read-only source이며, 원본 필드를 기존 변환 경로로 처리한다.21 작업대의 공유 record 입력·CAS 원자 저장·시나리오·단계 미리보기와 독립 Java Bifrost 승인/발행을 제공한다. 구 계약·SQLite 유지, 실제 장치/외부 SQL/쓰기 실행·운영 활성화·현장 PoV는 제외한다.


공통 입력을 DB 레코드별 객체 배열에 적용하는 opt-in 2.22 설계·정책·UX는 [P4-E](docs/P4-E-RECORD-BROADCAST.md)를 참조한다. 기존2.20/2.21 동작을 유지하고 실행 연결은 제외한다.


현재 작업자 메뉴는 자료 준비 → 객체 선택 → 연결 → 검증 → 검토·제출로 구성한다. 결과 스키마는 독립 저장해 객체 배열에서 바로 사용한다. [작업 흐름과 호환성](docs/OPERATOR-WORKFLOW.md)을 참조한다.

## P4-F PIO·Kepware 공통 수용과 제품별 해석기 (설계·미구현)

[상세 모델·계약 경계·fixture 계획](docs/P4-F-SOLUTION-INTERPRETATION.md). Mímir: SourceBundle → 제품별 Interpreter → InterpretationSnapshot(native 노드·참조·claim·미해석)을 파일 계약으로 발행 → Týr: 스냅샷 pin 재검증 → endpoint 의존 closure/차원별 판정 → ConversionPlan → 기존 정준 작성본으로 이어진다. 사실 추출과 의미 확인, 계약 표현 가능성과 가상 동등성·Bifrost 승인·운영 일치를 분리한다. 제품 해석기는 Mímir에 두며(2026-10-20 후속 결정, 원본 형식마다 해석하는 곳은 한 곳) 제공 bytes와 고정된 로컬 규칙만 읽고 workspace/registry에 쓰지 않는다. Týr와 Bifrost는 vendor 원본을 직접 파싱하지 않는다.

기존 P4-A 2.6/P4-A B 2.14는 유지하며 복합 vendor 정의를 scalar source로 위장하지 않는다. 신규 editor 계약/별도 opt-in sidecar SQLite를 계획한다. 기존 workspaceVersion2.0·DDL·API·wire·JAR 변경은 이번에 없다. 새 해석 기반 채택·제출은 신규 근거 closure 수신 계약과 독립 Bifrost 검증이 준비되기 전 차단한다. 합성 SI01~SI18은 작성 예정이며, PIO/Kepware의 제품·버전·driver·원본 형식 지원과 실제 현장 PoV는 별도 미완료다. 장치 통신·외부 SQL·쓰기 실행·vendor 코드 실행·운영 설정 생성/활성화는 제외한다.

## 정준 의미 계약과 값 생성·매핑 계약 (설계 보완·미구현)

[상세 경계·혼합 템플릿·MG01~MG08 명세](docs/CANONICAL-SEMANTICS-AND-GENERATION.md). 정준 의미 계약은 소비 객체/프로퍼티·타입·단위·식별과 작업/기간/총량·양품/코드 사전·유효성의 업무 뜻을 소유한다. 값 생성·매핑 계약은 정확한 의미 계약을 참조하고 PLC·DB 레코드·상수·외부 값의 선택/조합·변환/조건·시간/품질·오류·상태 의존을 소유한다. 원본·해석 모델은 이 둘의 근거이며 어느 한쪽을 대신하지 않는다. 기존 semantic-definition·source/graph/mapping·record/template 계약을 재사용하되 업무 문맥 계약과 적합성 검증은 신규다.

템플릿은 의미/생성 규칙/정책·슬롯 역할을 고정하고 적용본은 설비별 소스·레코드 선택·허용 상수 바인딩을 고정한다. 총량→양품·작업 범위·상태 우선순위 변경은 타입이 같아도 의미 변경 검토 대상이다. 기존 URI lifecycle을 유지하며 과거 정의를 덮어쓰지 않는다. 일반 조건·동적 키/문맥 비교·상태 기반 기준 카운터는 지원을 확인하기 전 opaque/전환 차단으로 남긴다. 기존 selector나 subtract를 일반 조건/상태 엔진으로 취급하지 않는다. 신규 계약/저장은 P4-F A~D에서 검증하며 이번 변경은 문서뿐이다.
