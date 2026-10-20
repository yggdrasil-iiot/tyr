# Týr MVP 구현 계획

상태: P0~P6 제한된 오프라인 구현과 P7 A07·A14 후속, P3-C B 제한 sqrt/clamp 완료, P3-E B bounded 논리 구조·구조 배열, P3-F B 유한 후보 그래프, P4-A B 검토·재가져오기 병합, P6 후속 프로세스 중단 복구·보수적 GC·파일 무결성, P7 독립 평가 준비 도구, P3-C C 제한 add/multiply/divide와 P6 registry 전체 의미 카탈로그, P3-C D 제한 수식 작성·컴파일 및 P3-C E 숫자·명시적 단위 상수 및 P3-F C 그래프 간 scalar 재사용, P6 의미 URI 개정·폐기 수용 완료. P7 fixture 수용은 16개 충족이다. A14는 브라우저·Python·Java 전체를 Linux OS network namespace에서 격리 검증했다. 호스트 Windows 전체 방화벽 검증 및 실제 현장 PoV는 별도 미수행이다. vendor native 구조 배치·추가 vendor 파일 검증·실제 현장 PoV·운영 활성화는 후속이다.
작성일: 2026년 10월 17일
기준 설계: [DESIGN.md](DESIGN.md)

2026-10-20 다음 우선순위: [P4-F PIO·Kepware 공통 수용 모델과 제품별 해석기](docs/P4-F-SOLUTION-INTERPRETATION.md). **설계 반영 완료·구현 미착수**이며, 기존 P0~P7 구현/합성 수용 실적과 별도다. 매핑 표현력 확대보다 설정 단독 수용 → 최종 태그 생성 과정 설명 → 쟁점 검토 → 익숙한 산출물 반환을 우선한다. 구체 제품/버전/driver/실제 원본 형식과 현장 PoV는 미확정이다.

이 계획의 구현 대상은 문서·설정·수동 입력에서 PLC 접근 정의를 만들고, 공통 의미에 매핑하며, 근거·변경을 검토한 뒤 Bifrost에 제출하는 오프라인 도구다. P0·P1의 계약·fixture·게이트는 구현했으며, P2~P5의 제한된 오프라인 작성·미리보기·가져오기·변경 검토를 구현했으며, P6 오프라인 승인/파일 발행 연계는 구현했고 P7 fixture 수용 결과는 별도 기록했으며 실제 자료 PoV와 운영 활성화는 후속이다.

## 1 MVP 완료 조건

사용자가 다음 시나리오를 끝까지 수행하면 기능 MVP가 완료된다.

1. 설비와 논리 연결을 등록한다.
2. 주소·DB 오프셋·심볼 소스를 작성하거나 XLSX·설정 export에서 가져온다.
3. 서로 다른 이름과 접근 방식의 네 소스를 같은 의미 멤버에 연결한다.
4. 원시 타입·디코딩·변환·결과 타입과 단위를 확인한다.
5. 독립 fixture의 값으로 변환을 미리 보고 근거를 검토한다.
6. 개정본에서 바뀐 접근·변환·의미를 구분해 재검토한다.
7. 제안을 제출하고 Bifrost 검증 결과와 승인된 릴리스를 구분한다.
8. 네트워크 차단 상태에서도 위 업무가 가능하다.

실장치 연결·Muninn의 runtime 확장·운영 설정 생성·배포는 MVP 이후다. 문서 import만 되거나 CLI만 동작하는 상태를 완료로 보지 않는다.

## 2 기존 기능 활용과 새 구현

| 영역 | 현재 자산 | 활용 방식 | 새로 구현할 부분 |
|---|---|---|---|
| UDT 계약 | Bifrost definition.schema.json, Member, UdtDefinition | 기존 모델·소비자의 호환 유지 | 별도 의미·소스·매핑 계약과 손실 표시 |
| 구조적 검증 | CompatibilityChecker·conformance 계층 | 기존 검사를 기존 계약에 적용 | 단위·접근·변환·참조·변경 검사 |
| 외부 모델 비교 | ModelReconciler | 정규 모델 비교로 유지 | 이름이 다른 신호의 명시 연결, 접근·변환 diff |
| 외부 설정 어댑터 | IgnitionUdtAdapter 등 | 현재 입력 형태와 제약 참고 | 원본 접근·변환·근거를 보존하는 Týr importer |
| 내용 무결성 | provenance publish/verify, manifest 기반 | 해시와 파일 발행 패턴 재사용 | 여러 파일의 참조 고정·전체 검증·묶음 발행 |
| 승인·활성화 | Bifrost의 기존 기록·권한·승인 기반 | 적용 가능한 경로를 조사해 연계 | mapping-release 종류에 대한 승인 연결 |
| 타입 후보 | Mímir derive | 후속 관측 계약의 출발점 | MVP에서는 수정 없이 선택적 후보 입력으로 유보 |
| 실행 | Muninn 이름·타입 필터 | 기존 경로 유지 | 후속 승인 매핑 소비 |
| 파일 처리 | XLSX·JSON/XML 라이브러리 | 파일 구조 처리 재사용 | 현장 양식 프로파일·누락·원문 위치 추적 |
| 사용자 도구 | 신규 Týr | 프레임워크 기능 활용 | 작성 API·저장·검토·세 작업 화면 |

재사용은 상대 저장소의 클래스를 가져오는 뜻이 아니다. Bifrost 내부 확장에서는 해당 앱의 기존 기반을 재사용하고, Týr와의 결합은 공개 JSON·파일·CLI 계약으로 한다.

### 2.1 현재 구현에 대한 구체적인 주의점

- ModelReconciler는 이름으로 대응한 멤버의 타입·range·semanticId를 비교한다. 접근 주소·스케일·단위를 비교하는 엔진으로 사용하지 않는다.
- IgnitionUdtAdapter는 접근·변환 필드를 보존하지 않는다. 현재 Int4·Int8을 같은 타입으로 투영하는 규칙도 신규 importer의 원시 타입 처리에 복제하지 않는다.
- 기존 definition.schema.json은 추가 속성을 금지한다. 새 속성을 붙여 기존 게이트를 우회하지 않는다.
- provenance verify는 현재 latest 항목의 단일 canonical 파일을 검사한다. 이를 버전이 고정된 전체 MappingRelease 검증으로 간주하지 않는다.
- EgressValidator는 이름·타입 검사다. 매핑이나 변환의 실행기가 아니다.
- Bifrost의 기존 활성화 기록이 새 릴리스 종류를 지원하는지 먼저 확인한다. 맞지 않으면 작은 계약 확장을 하고 별도의 승인 권위를 Týr에 만들지 않는다.

## 3 구현 구조와 저장소 경계

다음은 구현 시의 제안 구조다. 현재 계약·fixture·검증기는 contracts, fixtures, scripts에 구현했다. Týr backend/frontend는 아래 경로에 구현했으며 타 앱 확장은 P6 이후 계획이다.

- tyr/backend: 작성 API, domain, application, persistence, importers, preview, bifrost-adapter
- tyr/frontend: 자료/소스, 의미/매핑, 변경/제출 화면
- tyr/contracts: 검토·배포된 스키마의 버전별 사본과 계약 설명
- tyr/fixtures: 가상·공개 가능한 양식, 설정 예시, 독립 기준값
- tyr/scripts: 오프라인 수용 게이트와 seam 실행
- bifrost/core: 새 계약 검증·diff·릴리스 지원
- bifrost/gates: 새 파일 CLI 진입점과 계약 시험

P2는 Python 표준 로컬 서버·SQLite와 HTML/CSS/JavaScript 화면으로 구현했다. P1 검증기를 Týr 안에서 재사용하고 새 프레임워크 의존성을 추가하지 않는 결정이며 [작성 도구 문서](docs/P2-AUTHORING.md)에 근거를 기록했다. 정확한 프레임워크·라이브러리 버전은 P2에서 지원 범위와 호환성을 확인해 고정한다. 첫 구현은 분산 서비스·메시지 브로커·그래프 DB 없이 로컬 DB와 파일 증거 저장소로 시작한다.

DB는 초안·관측·검토·작업 인덱스를 보관하고, 불변 파일 묶음은 제출·승인 단위로 사용한다. 원본 증거와 실행 계약은 분리한다.

## 4 단계별 구현

### P0 입력 자료와 계약 결정

의존성: 없음. 예상 작업량 2~3인일.

- 기존 문서·설정의 실제 형식, 제품 버전, 상속·기본값·표현식 범위를 조사한다.
- P0·P1은 가상 문서·설정으로 정준 모델의 수렴·구분·손실·변경 가설을 검증한다. 첫 실제 XLSX·설정 export 선정과 검토자 확보는 P4/P7에서 수행한다.
- 아직 특정 제품의 파일이 없으면 가상 fixture와 형식 미확정을 명시하고 실제 제품 지원으로 홍보하지 않는다.
- 소수 의미 모델과 접근 프로파일을 선정한다.
- 단위 코드·타입 어휘·십진 계산·반올림·무효값·참조·파일 버전 정책을 결정한다.
- 기존 Bifrost 승인·발행 코드에서 mapping-release에 적용할 수 있는 경로를 확인한다.
- 구현 전 tyr Git 저장소 여부를 확인하고, 기존 저장소라면 feature 브랜치에서 작업한다. 신규 저장소 초기화·원격 생성은 별도 작업 범위다.

산출물: 결정 기록, 자료 목록, 지원 범위, 기준 fixture 목록, 기존 기능 활용표.

종료 조건: 네 접근 표현과 정준 의미 식별·충돌·손실·변경 정책, 재사용·권위 경계가 명확하다. 실제 장치 통신과 실제 원본 확보는 제외한다.

### P1 계약과 독립 fixture

의존성: P0. 예상 작업량 3~4인일.

- EvidenceArtifact, SourceObservation, SourceDefinition, SemanticDefinition, MappingSet의 형식·참조를 명세한다.
- ObservationBundle, MappingProposal, ValidationReport, MappingRelease 스키마를 정의한다.
- 주소·DB 오프셋·심볼을 oneOf 등의 구분된 형식으로 검증한다.
- 선택·필수·미확인·해당 없음의 차이를 명세한다.
- 같은 개념의 서로 다른 이름·타입·스케일과 서로 다른 PLC의 동일 주소 fixture를 작성한다.
- 원시 바이트·typed 값·예상 결과를 생성기와 독립적으로 확인한다.
- 기존 UDT로 투영할 때의 손실과 호환 범위를 기록한다.

재사용: 기존 계약 작성·fixture·CLI 관례.
신규: 접근·의미·매핑 계약 및 해당 시험.

종료 조건: [정준 모델 검증 기준](docs/P1-GOVERNANCE-CRITERIA.md)의 G01~G09와 형식·참조 회귀 검증을 모두 통과한다. 네 표현의 같은 의미·기준값 수렴, 다른 의미의 공존·충돌 거부, 수치·투영 손실 보고, 의미·변환·접근 변경의 재검토 판정이 필요하다. 실제 장치 통신은 제외한다.

### P2 수동 작성의 첫 사용 경로

의존성: P1. 예상 작업량 4~5인일.

- 설비·연결 프로파일·소스·의미·매핑의 작성과 저장 API를 구현한다.
- 자료/소스와 의미/매핑 화면의 최소 경로를 만든다.
- 접근 종류별 폼, 의미 객체의 프로퍼티 추가·편집·검색, 프로퍼티별 분산 주소 매핑과 저장·재조회 기능을 구현한다.
- 이름·단위·스케일이 다른 정의를 객체·설비별로 비교한다.
- rawRepresentation과 valueType을 별도로 편집한다.
- 필수 정보가 없는 초안은 저장하되 제출 제한을 표시한다.
- revision 기반 동시 편집 충돌을 검출한다.

재사용: 웹·DB 프레임워크의 CRUD·트랜잭션.
신규: 도메인 모델, Týr 저장 계층, 화면, 편집 검증.

종료 조건: 사용자가 네 접근의 소스를 같은 의미에 연결하고 재시작 후 다시 열 수 있다. 파일 importer 없이도 핵심 가치가 동작한다.

### P3 디코딩과 값 미리보기

의존성: P2. 예상 작업량 3~4인일.

- 선택된 프로파일의 스칼라 디코더를 구현한다.
- linear, cast, bit-select, enum-map과 제한된 단위 변환을 구현한다.
- 연산 순서·중간값·결과 타입·단위·품질을 화면에 표시한다.
- already-engineered와 raw 입력을 구분한다.
- 미지원 표현식, 오버플로, 무효 코드, 비트 범위 오류를 드러낸다.
- 접근 측 비트 선택과 후단 비트 선택의 중복을 검사한다.

재사용: 수치·바이트 처리 라이브러리.
신규: 제한된 변환 엔진, 타입 검증, preview API·화면.

종료 조건: 독립 기준값의 정상·오류 사례가 기대값과 맞는다. A01, A02, A03, A06, A07, A08, A10을 평가한다. 이 단계만으로 live 접근 성공을 주장하지 않는다.

### P4 파일 수용과 근거 연결

의존성: P2, P1. P3와 일부 작업을 독립적으로 진행 가능. 예상 작업량 4~5인일.

- 첫 XLSX 프로파일과 설정 importer를 구현한다.
- 파일 원본·해시·개정·확보 일시·제품 버전·처리 범위를 기록한다.
- 셀·JSON Pointer·XML 경로 등 원문 위치를 보존한다.
- 관측 정의와 사용자가 편집·채택한 정의를 분리한다.
- 설정의 기본값·상속·참조를 지원 범위 안에서 해석한다. 범위 밖이면 미해결로 남긴다.
- 대상·성공·부분·미지원 항목이 전체와 일치하도록 집계한다.
- 매크로·스크립트·외부 엔티티·외부 연결을 실행하지 않는다.

재사용: 파일 포맷 라이브러리와 제품 export.
신규: 양식 프로파일·손실 없는 importer·증거 인덱스·자료 화면.

종료 조건: import 결과를 수동 작성과 같은 편집 경로에서 사용하고, 각 값의 근거와 누락을 확인한다. R05, R06, R10, R11과 A09, A13, A15를 평가한다.

### P5 변경 비교와 담당자 검토

의존성: P3, P4. 예상 작업량 3~4인일.

- 주소·타입·디코딩·변환·단위·개념 변경을 분리한 diff를 구현한다.
- display name 변경과 stable ID 변경을 구분한다.
- alias/view, 미확인 중첩, 활성 소스 중복을 표시한다.
- 관측·대응·검토·승인·실장치 상태를 별도 관리한다.
- 대상 해시·확인자·시점·사유·근거를 검토 기록에 남긴다.
- 원문·프로파일 변경으로 영향을 받는 확인을 재검토 상태로 전환한다.
- 입력 불완전 때문에 나온 차이와 실제 정의 불일치를 구분한다.

재사용: 기존 모델 비교 결과의 표현 관례.
신규: source/mapping diff와 검토 모델·변경 화면.

종료 조건: 주소·스케일 변경이 이름·타입 동일성에 가려지지 않는다. A04, A05, A07, A16을 평가한다.

### P6 Bifrost 계약 검증과 승인 연계

의존성: P1, P5. 예상 작업량 5~7인일. Bifrost 변경 작업을 포함한다.

- Bifrost에서 새 제안 스키마·참조·접근 프로파일·변환·의미·변경을 검증한다.
- Týr의 사전 검사만 믿지 않고 수신 경계에서 다시 검증한다.
- 제안 해시와 기준 릴리스를 검사하고 오래된 제출을 충돌로 처리한다.
- 적용 가능한 기존 승인·기록 기반에 MappingRelease를 연결한다.
- 디렉터리 묶음의 모든 참조·해시를 고정한다.
- staging 후 완성된 릴리스만 발행하고, 실패 시 기존 릴리스를 유지한다.
- Týr는 파일·CLI 어댑터로 제안·결과·승인 상태를 교환한다.
- no shared code 원칙을 지키며 두 앱의 독립 구현을 같은 wire fixture로 대조한다.

재사용: Bifrost 내부의 검증 결과·CLI·발행·기록 기반.
신규: mapping validate/publish/diff 제안 명령, 전체 묶음 검증, 새 릴리스 종류와 승인 연계.

종료 조건: 미확인·참조 오류·변조·수정 후 오래된 승인으로 발행할 수 없다. A11, A12, A16과 기존 Bifrost 회귀 검사를 수행한다. 릴리스 발행은 운영 활성화가 아니다.

### P7 오프라인 수용과 현장 PoV

의존성: P6. 예상 개발 작업량 3~4인일. 현장 평가 일정은 별도다.

- 네트워크 차단 상태에서 전체 시나리오를 실행한다.
- A01~A16의 결과와 실패 원인을 기록한다.
- 별도 담당자가 정의·매핑·변경 리포트를 보고 근거를 찾는다.
- 실제 개정본을 사용해 수작업과 도구의 전체 검토 시간을 비교한다.
- 조정에 쓰지 않은 설비 자료로 재사용성을 평가한다.
- 파일·프로파일·도구 버전·기준 릴리스를 고정한 검증 기록을 남긴다.

산출물: 사용 설명, 수용 기록, PoV 결과, 미해결 목록, 확대 판단.

종료 조건: 요구사항별 근거가 있고 운영 설비에 접속하지 않았으며, 절감 효과와 한계를 함께 설명할 수 있다.

## 5 의존성과 일정

기본 순서는 P0 → P1 → P2 → P3/P4 → P5 → P6 → P7이다. P4의 파일 처리는 P3 변환 엔진과 일부 독립적이지만 결과 모델은 P1을 따라야 한다.

확장 전 제한 범위의 초기 예상은 약 27~36인일(1명 약 6~8주)이었다. 매핑 패턴 확장에는 이 합계를 적용하지 않으며, 문서 끝의 범위 보정과 계약 검토 후 재산정을 따른다. 현장 대기·자료 정리·제품 상속 해석·개발 환경 준비는 추가 변동 요인이다.

DESIGN.md의 4~6주 제한 PoV 추정은 범위를 줄인 실증의 출발점이다. 세 화면·실제 파일 두 종류·개정 검토·Bifrost 승인까지 포함하는 이 계획은 더 넓으므로 일정도 재산정했다.

가장 먼저 시연 가능한 중간 결과는 P2~P3의 수동 매핑·값 미리보기다. 전체 MVP의 승인 경계를 구현하기 전에 이를 현장 담당자에게 보여줘 표현 모델의 적합성을 확인한다.

## 6 UI와 API 작업 묶음

다음 API 이름은 제안이다. 기술 스택 확정 후 같은 동작 계약을 유지한다.

| 작업 | API 묶음 예시 | 주요 UI |
|---|---|---|
| 자료 등록·추출 | evidence, imports, import-results | 자료 목록·처리 결과 |
| 접근 정의 | equipment, connection-profiles, sources | 접근 종류별 폼 |
| 의미 모델 | semantic-definitions, concepts | 검색·선택·후보 작성 |
| 매핑 | mapping-sets, mappings | 소스와 대상 연결 |
| 미리보기 | mapping-preview | 입력·중간값·결과·품질 |
| 변경·검토 | diffs, reviews | 차이·근거·확인 |
| 제출·승인 | proposals, validations, releases | 제출 상태·검증 결과 |

오류 응답은 ruleCode, 대상 ID와 필드 경로, 근거 참조, 수정 가능한 메시지를 포함한다. 내부 스택 트레이스를 작업 화면의 설명으로 사용하지 않는다.

## 7 시험 전략과 증거

- 계약 시험: 종류별 필수 필드·참조·버전·unknown 상태.
- 도메인 시험: 디코딩·수치 경계·중복 소스·alias·변환 순서.
- import 시험: 정상·병합 셀·누락·기본값·미해결 참조·미지원 타입.
- UI 흐름: 입력→연결→저장→재조회→개정→재검토→제출.
- seam 시험: Týr 파일을 실제 Bifrost CLI가 읽고 검증·발행하며 Týr가 결과를 다시 읽는다.
- 변조 시험: 승인 후 파일 수정·참조 누락·오래된 기준·부분 발행.
- 오프라인 시험: 외부 네트워크 없이 전체 흐름.
- 회귀 시험: 변경한 Bifrost 모듈과 기존 계약을 소비하는 경로.

구현 후 완료 판단은 직접 실행한 결과로 한다. 문서에 기존 테스트 개수를 옮겨 성공 근거로 사용하지 않는다. 단계별 실패·제약도 기록하며 runtime·실장치 기능의 미수행을 PASS에 포함하지 않는다.

## 8 현장 평가와 확대 기준

문서·설정이 모두 있는 설비를 고르고 50~100개 기준 항목을 담당자가 확인한다. 수작업 의미 확인·개정 검토 시간, 문의, 오탐 검토, 수정 시간을 포함한다. 작업 순서를 교차하고 조정용·평가용 자료를 분리한다.

설계서의 목표는 전체 처리 상태 집계, 항목별 근거, 자동 후보 구간 매칭 정밀도 95% 이상, 전체 검토 시간 30% 이상 단축이다. 이는 목표이며 자동 승인 기준이나 실적이 아니다.

확대는 다음을 함께 확인해 결정한다.

- 시간 절감이 오탐·수정 부담을 포함해 유지되는가?
- 중요한 접근·변환 정보를 조용히 누락하지 않는가?
- 담당자가 근거를 찾고 확인 결과를 유지할 수 있는가?
- 다음 설비는 프로파일·어댑터 추가로 수용 가능한가?
- 자료를 갱신할 책임자와 절차가 있는가?

## 9 MVP 이후

| 후속 단계 | 내용 | 선행 조건 |
|---|---|---|
| Mímir 후보 연계 | ObservationBundle에 원본 노드·타입·시점 보존 | Týr 계약과 후보 검토 흐름 안정 |
| 추가 문서·제품 | PDF·OCR·다른 솔루션 importer | 실제 자료·독립 기준집 확보 |
| Muninn 소비 | 릴리스 검증→접근→변환→의미 발행 | 오프라인 변환·계약 통과 후 별도 시험 환경 |
| 기존 제품 실행 | 승인 매핑의 설정 생성·적용 | 제품별 변환 의미·원복·권한 검증 |
| 운영 도입 | 실장치·활성화·복구·인증 | 현장 절차·가용성·권한 검토 |

Mímir를 화면 도구로 다시 만들거나 Muninn에 작성 기능을 추가하지 않는다. Huginn 캡처·live browse는 선택적 근거이며 파일 MVP의 필수 기능으로 확대하지 않는다.

## 10 실행 규율

초기 문서 작업 이후 P0·P1 계약과 검증 도구를 작성했다. P2~P6 오프라인 작성·검토·Bifrost 파일 승인/발행 연계를 구현했다. 운영 런타임·활성화와 P7 실제 자료 검증은 후속이다. Git 초기화·원격 생성·커밋·push·merge는 수행하지 않았다.

실제 구현 시 기존 각 저장소의 지침을 읽고 feature 브랜치에서 작업한다. 기존 main에 직접 변경하지 않는다. 저장소 간에는 published data/wire 계약만 사용한다. 구현 단계별로 필요한 검증을 직접 실행하며, public 저장소에는 기술 문서만 넣고 개인 지원 전략을 섞지 않는다.

## 11 첫 구현 작업 목록

- [x] P0 정준화 가설·의미 식별·손실·변경·역할 경계 확정
- [ ] P4/P7 실제 XLSX·설정 export와 담당자 확보
- [x] P0 접근 프로파일·타입·단위·변환 결정 기록
- [x] P1 JSON Schema와 정상·오류 fixture
- [x] P1 수렴·구분·손실·변경 수용 게이트
- [x] P2 수동 소스·의미·매핑의 저장과 네 접근 폼
- [x] P3-B 독립 기준값 기반 숫자·제한 codec·변환 preview
- [x] P4-A bounded XLSX·tyr-config-v1 import와 원문 근거 (실제 vendor export 지원은 후속)
- [x] P5 개정 diff·로컬 담당자 검토 상태·revision/hash 충돌 처리
- [x] P6 Bifrost 독립 수신 검증·서명 승인·불변 파일 릴리스 연계 (운영 활성화 제외)
- [x] P7 A01~A16 오프라인 실행 및 A07·A14 후속 검증
- [ ] 실제 현장 자료·담당자의 독립 정답을 사용하는 PoV

## 12 코드 근거

기준 루트는 로컬 Yggdrasil 작업 폴더이며 Týr와 Bifrost는 그 아래 형제 디렉터리다.

- mimir/src/main/java/dev/krillin/mimir/DefinitionDeriver.java
- mimir/src/main/java/dev/krillin/mimir/BrowsedMember.java
- bifrost/core/src/main/resources/schema/definition.schema.json
- bifrost/core/src/main/java/dev/krillin/bifrost/core/schema/CompatibilityChecker.java
- bifrost/core/src/main/java/dev/krillin/bifrost/core/vendor/ModelReconciler.java
- bifrost/core/src/main/java/dev/krillin/bifrost/core/conformance/adapter/IgnitionUdtAdapter.java
- bifrost/gates/src/main/java/dev/krillin/bifrost/gates/ProvenancePublish.java
- bifrost/docs/ADOPTION.md
- muninn/src/main/java/dev/krillin/muninn/EgressValidator.java

## P0와 P1 실행 결과

- 시작 대상: AB Logix 심볼, S7-1500 OPC UA, S7-300 DB, Mitsubishi MELSEC.
- 결정·미확정 입력: [P0-DECISIONS.md](docs/P0-DECISIONS.md).
- 계약: [contracts/README.md](contracts/README.md), JSON Schema 12개.
- fixture: [fixtures/README.md](fixtures/README.md), 실제 제품 export가 아닌 가상 자료.
- 검증 도구: scripts/validate_contracts.py. Bifrost의 실제 승인 실행은 P6이다.
- 실제 현장 원본·제품 버전·담당자 확보는 P4/P7의 후속 검증이며 P0·P1 완료 조건에서 제외한다.
- 정준 모델 완료 기준: [P1-GOVERNANCE-CRITERIA.md](docs/P1-GOVERNANCE-CRITERIA.md). 실제 장치 통신은 제외한다.


## P2 실행 결과

- [작성 도구·실행 방법](docs/P2-AUTHORING.md)
- [검증 결과](docs/verification/P2-RESULTS.md): 저장·API 14/14, P1 회귀 93/93.
- 브라우저에서 네 접근 폼으로 작성·공통 의미 매핑·편집·서버 재시작 복원·초안 제한·동시 편집 충돌을 확인했다. 실제 장치 통신은 제외한다.


## P2 객체 매핑 확장

사용자 요구에 따라 단일 값 UI 제한을 제거하고 네 PLC × 8신호(32개), 객체 8프로퍼티, 설비별 객체 매핑을 구현했다. 이름의 동의어·동명이의어와 단위·스케일·상태 코드 차이를 비교 화면에서 확인한다. [객체 모델](docs/OBJECT-MAPPING.md), [확장 검증](docs/verification/P2-EXPANDED-RESULTS.md)을 따른다. 계약 1.0.0은 유지하고 새 단위 변환은 1.1.0에 추가했다. P3의 일반 값 preview와 P6의 승인 연계는 후속이다.


## 매핑 패턴에 따른 P3 이후 범위 보정 (2026-10-17)

[지원 매트릭스](docs/MAPPING-SUPPORT-MATRIX.md)와 [56개 fixture 명세](fixtures/mapping-patterns/README.md)를 후속 구현 범위의 기준으로 사용한다. P0·P1·P2 완료 상태는 유지하되 18개 항목의 전체 지원을 뜻하지 않는다. 우선순위 A는 오프라인 MVP의 다음 구현 대상, B는 실제 자료로 필요성이 확인되면 확장, C는 후순위 정의 보존이다. 이 절이 기존 P3/P4의 세부 범위와 공수 가정을 보정한다.

### P3/P4 작업 묶음과 완료 조건

| 작업 | 우선순위·선행 | 새 구현과 재사용 | fixture·완료 기준 |
|---|---|---|---|
| P3-A 객체 식별·그래프 계약 | A, 가장 먼저 | 현재 Source/Semantic/Mapping 및 P2 저장·편집 재사용. targetInstance·memberPath와 이름 있는 입력 그래프 계약/마이그레이션은 신규 | MP02/11/17. 동일 설비의 두 객체를 별도로 저장·조회·매핑, 그래프 순환/참조/타입 오류 차단. two-instances-same-equipment, graph-cycle |
| P3-B 원시 표현·codec | A, P3-A 계약 | 기존 숫자 endian·scale·enum·bit 평가 재사용. native bit 좌표, 분산 word 결합, bounded ASCII·BCD16·S7 DATE_AND_TIME subset 신규 | MP01/07/08/09. separate-low-high, bit-coordinate-system, melsec-native-relay, ascii-fixed-string, bcd16-invalid, date-timezone-missing. 원시→디코딩 단계와 오류를 화면 확인 |
| P3-C 제한 파생식·값 preview | A, P3-A/B | 기존 linear/cast/unit-convert/enum 평가 재사용. 다중 입력 subtraction, 결측/단위/정밀도 규칙과 단계별 preview 신규 | MP10/11. pressure-difference, multi-input-missing, graph-cycle. 독립 정답과 결과/진단 일치. sqrt/clamp의 제한 2.11.0과 add/multiply/divide의 제한 2.15.0 확장은 아래 후속으로 완료. 제한 수식 작성은 아래 P3-C D로 완료. 일반 식 전체·차원 분석·온도 delta는 미완료 |
| P3-D 모의 시간·품질 조립 | A, P3-A/C | invalidValuePolicy 확장 검토, 입력별 DataValue·skew·freshness·sequence 조립은 신규 | MP16. freshness-good/stale, bad-input-quality, trigger-record. 가상 시각·품질만 사용하고 원자성 가정 금지 |
| P3-E 배열·구조 | 고정 배열 A, 논리 구조 B 구현·native B 별도; P3-A/B | 기존 symbol leaf 접근 재사용. 배열 shape/stride/범위/인덱스, 구조 타입·필드 선택 신규 | MP04/05/06. array-shape-stride/out-of-range를 A에서 구현. 2.12 nested-object-tree·논리 structure-array-to-objects는 아래 B 후속. native-structure-select/UDT 배치는 미검증; 논리 구조가 native 수집을 뜻하지 않음 |
| P3-F bounded selector | B, P3-A/C/D | 후보 소스 목록·인덱스 정책·출처 변경 추적 신규 | MP13. bounded-selector, selector-out-of-range. 실제 동적 PLC read 없음 |
| P4-A 파일·템플릿·alias·미해석 보존 | A, P3-A 계약; 원본 캡처는 독립 착수 | 기존 evidence/SourceObservation·hash·locator·P2 수동 작성 재사용. XLSX/첫 설정 exporter parser, 전개/override, 참조 순환, 원본 byte roundtrip·미해석 검토 신규 | MP03/12/18. template-base-stride/instance-override/missing-param, alias-chain/cycle, unsupported-roundtrip. 미해석 식은 원문 그대로 보존·승인 차단 |
| P4-B 혼합 소스·읽기/쓰기 정의 | 상수·외부 정의 B, read/write C; P4-A | solution-tag 스키마 조각을 완제품 기능으로 간주하지 않음. source kind·참조·변환 방향 계약 신규 | MP14/15. static-context-and-plc, external-query-preservation, read-write-definitions. SQL/쓰기 실행 없음 |

P3-B의 분산 워드 결합은 P3-A의 다중 입력 모델을 사용한다. P3-C의 subtraction과 P3-D의 조립은 같은 입력 모델을 사용하되 수치 연산·객체 조립·레코드 시간 정책을 분리한다. 계약 제안과 독립 fixture를 먼저 검토하고 이후 서버·UI를 구현한다. 샘플 oracle은 구현식으로 자동 생성하지 않는다.

A 범위의 다음 완료 조건은 다음과 같다.

1. 현재 네 접근 정의·32신호의 저장·수렴·구분 검증을 회귀 유지한다.
2. 동일 설비의 복수 객체, 분산 객체 프로퍼티, 분산 low/high, native bit, 고정 배열, 제한 codec·다중 입력 subtraction을 파일/가상 값으로 표현·검증·preview한다.
3. 템플릿·alias 및 지원하지 못하는 문서 표현을 원문/근거와 함께 보존한다. 미지원 항목은 추정 매핑하지 않으며 승인 가능한 ready 정의와 구분한다.
4. 손실·의미 변경과 시간/품질 정책 위반을 탐지한다. 현재 원문 이름 collision/alias 사례를 유지한다.
5. A 범위에 연결된 planned fixture를 실제 API 저장·재로드·검증·샘플 평가·화면 확인으로 승격한다. 일부 예제만 구현한 패턴은 partial을 유지한다.

B/C fixture는 pending을 유지하며 A 완료를 위해 모두 구현할 필요는 없다. 모든 PLC 명령·vendor 표현식·문자열 인코딩·날짜 형식을 포괄한다는 완료 조건은 두지 않는다. importer의 첫 솔루션 이름·버전과 실제 export 범위는 자료 확보 시 확정한다.

### P5·P6·P7에 미치는 영향

- P5: 객체 ID/경로·그래프 입력·template override·alias 변경의 전이 영향과 단위/의미 변경을 구분한다. 원문만 바뀐 경우와 전개 결과가 바뀐 경우를 별도 기록한다.
- P6: Bifrost의 기존 형식으로 표현 가능한 부분과 손실을 분리한다. 승인용 새 계약 및 수신자 capability/unknown-op 거부 검증을 선행한다. 단순 스키마 성공을 실제 승인 연계 완료로 계산하지 않는다.
- P7: current 실행, gap-probe 재현, planned 대기 수를 따로 보고한다. gap 재현 성공은 기능 지원 성공이 아니다. 기존 A01~A16과 함께 패턴별 정답·오류·저장·UI 결과를 확인한다. 현장 담당자가 익명화된 문서와 설정 export로 정답 매핑을 독립 작성하고 Týr 결과의 수렴/오매핑/누락/손실/검토 시간을 비교한다. 파일럿 자료 제공·실제 제품 검증은 아직 미완료다.

실행 순서는 P3-A → P3-B/C → P3-D와 고정 배열 P3-E이며 P4-A 원문 수용을 병행할 수 있다. B/C는 후속 분기로 둔다. 기존 27~36인일 추정은 확장 전의 제한된 범위에 대한 기록이다. 확장 A 범위의 새 일정은 P3-A 계약과 실제 파일 난도 검토 후 산정한다.

실제 장치 연결, browse/read/write, 통신 성공률, 현장 활성화와 handshake는 모든 위 완료 조건에서 계속 제외한다. 오프라인 시간·품질 시험은 장치 통신 검증을 대신하지 않는다.

### 이번 변경의 구현 상태

지원 매트릭스·시험 명세와 오프라인 검증기를 추가했다. 제품 서버/프런트엔드, 현재 wire 계약과 사용자 저장 DB는 변경하지 않았다. 실행 증거는 [MAPPING-PATTERNS-RESULTS.md](docs/verification/MAPPING-PATTERNS-RESULTS.md)를 참조한다.

## P3-A 계약·fixture 실행 결과 (2026-10-17)

이번 요청 범위인 객체 식별·다중 입력 계약과 fixture를 구현했다. [P3-A 계약](docs/P3-A-CONTRACT.md), [fixture](fixtures/p3a/README.md), [검증 결과](docs/verification/P3-A-RESULTS.md)를 따른다.

- [x] 2.0.0 target-instance: 같은 설비의 동일 모델 두 객체를 안정된 ID로 구분.
- [x] 2.0.0 mapping-set: targetInstanceRef, 구조화 memberPath, 직접 source/graph 결과 valueRef.
- [x] value-graph: 이름 있는 입력·로컬 노드 참조, decode-u32-words/identity 제한 op.
- [x] 참조 버전·순환·입력 타입/단위·대상 중복·입력별 근거·객체 완전성 정적 검증.
- [x] 가상 low/high word 조합 oracle, 명시적 객체 ID 기반 1.x→2.0 파일 마이그레이션과 32바인딩 재로드.
- [x] 1.0/1.1 Schema 바이트 보존 및 기존 API의 2.0 버전 거부.
- [x] P3-A 후속: 2.0 객체 ID·그래프 편집/저장/조회와 명시적 SQLite 백업·마이그레이션 구현.
- [x] P3-B: 가상 raw bytes 해석, 그래프 결과→최종 cast/오버플로·손실 preview.
- [x] P3-C: 제한 subtract·입력별 linear/unit-convert·단위/타입/결측 검증·Decimal/cast 손실 preview·SQLite 왕복.
- [x] P3-D: 가상 입력 시간·품질·age/skew·결측/bad/uncertain·trigger sequence 검증, 정책과 가상 시나리오 저장·재현.
- [x] P3-E A: 고정 scalar 배열 shape/lowerBounds/stride/range·고정 indices·요소별 의미 매핑·범위/버퍼 검증·SQLite/preview.
- [x] P3-E B의 논리 구조·중첩 멤버·고정 구조 배열 구현. 최종 수용은 아래 별도 기록.
- [ ] P3-E B vendor native 구조 배치·실제 export 검증.
- [x] P3-F B 같은 그래프의 유한 scalar DAG 후보 선택. 최종 수용은 아래 기록.
- [ ] P3-F 임의 주소식·추가 vendor importer. 같은 설비 scalar cross-graph는 아래 P3-F C로 구현.

위 계약 단계의 실행 기록 이후, 아래 P3-A 화면/저장 후속에서 업그레이드·백업·2.0 작성 경로를 구현했다. 장치 통신은 계속 제외한다.

## P3-A 화면·저장 후속 완료

[사용·이전 정책](docs/P3-A-WORKSPACE.md), [검증 증거](docs/verification/P3-A-WORKSPACE-RESULTS.md). 같은 설비의 복수 객체, low/high·identity 그래프 편집, 그래프 결과 매핑, 검색/단위/이름 비교, SQLite 재시작 복원과 백업·이전 기록을 구현했다. 기존 1.x 작성본은 명시적 이전 전까지 유지하며 우회 업/다운그레이드를 막는다. P3-B 일반 decoder/preview, P3-C 파생식, P3-D 시간/품질 및 Bifrost 승인은 후속이다.

## P3-B 제한 디코딩·가상 미리보기 완료

[계약·사용](docs/P3-B-PREVIEW.md), [독립 fixture](fixtures/p3b/README.md), [실행 증거](docs/verification/P3-B-RESULTS.md). 09 화면과 read-only preview API에서 raw/type/byte-word 순서·low/high·단위·스케일·cast·범위 단계와 오류/손실을 확인한다. 2.1 소스 계약으로 native bit 좌표, 고정 ASCII, BCD16, DB의 S7 날짜 subset을 작성·저장한다. 기존 1.x/2.0 스키마는 유지하고 preview는 SQLite revision/body를 변경하지 않는다. 날짜 시간대 미확인·비정상 입력·정밀도 손실·overflow를 명시한다. P3-C 다중 입력 subtraction은 아래 후속 구현으로 완료했다. 비선형식, P3-D 시간/품질, P3-E 배열/중첩과 P6 승인은 후속이다. 실제 장치 통신은 제외한다.

## P3-C 제한 파생값 완료

[계약·사용](docs/P3-C-DERIVED.md), [독립 fixture](fixtures/p3c/README.md), [실행 증거](docs/verification/P3-C-RESULTS.md). 이름 있는 left/right 뺄셈과 입력별 스케일·단위 변환을 2.2 문서로 작성·저장·조회한다. 단위/타입/참조/순환/근거를 정적 검증하고 필수 입력 결측·cast 손실/overflow를 가상 preview에서 확인한다. 기존 그래프 입력 모델·출처·디코더·최종 cast·SQLite JSON/revision/CAS를 재사용했다. 새 문서 5종과 압력 단위·연산 노드·UI 필드·18개 독립 값 fixture가 신규다. 초기 완료 시 sqrt/clamp는 B 후속이었으며 아래 2.11.0 제한 확장으로 구현했다.  온도 delta·일반 차원 분석·P3-D 시각/품질 정책·P6 승인은 이번 완료 조건에 포함하지 않는다. 실제 장치 통신은 계속 제외한다.

## P3-D 가상 시간·품질 검증 완료

[2.3 계약·사용](docs/P3-D-TIME-QUALITY.md), [독립 fixture](fixtures/p3d/README.md), [실행 증거](docs/verification/P3-D-RESULTS.md). 단일 바인딩의 source lineage에 대해 명시적 평가 기준·입력별 source/server 시각·품질·sequence를 검증한다. freshness/skew 경계·미래/결측·bad/uncertain 전파를 표시하고 시간·품질 오류 시 수치 계산을 중단한다. trigger-sequence는 가상 묶음 내 일치만 검사하며 실제 latch/handshake/동시 snapshot은 보장하지 않는다. 기존 디코더·그래프·cast·workspace/CAS를 재사용했다. 2.3 Schema 3종·sample_quality 평가기·정책/미리보기 UI·별도 SQLite 시나리오 테이블/API·32개 독립 값/시간 fixture가 신규다. 기존 데이터 body/revision은 자동 재작성하지 않으며 실제 장치 통신·P6 승인은 제외한다.

## P3-E 고정 배열 A 완료

[2.4 계약·사용](docs/P3-E-FIXED-ARRAYS.md), [독립 fixture](fixtures/p3e/README.md), [증거](docs/verification/P3-E-RESULTS.md). 고정 scalar 배열의 shape·lowerBounds·축별 stride/좌표 단위·저장 range와 고정 요소 indices를 작성·저장한다. array-element 결과를 기존 객체 프로퍼티에 연결하고 범위·중첩 stride·버퍼 폭·타입/단위·선택 결측을 검사한다. 기존 source/graph/target·decoder/cast·P3-D 정책/시나리오·SQLite JSON/CAS를 재사용했다. 2.4 Schema 5종·fixed_arrays 모듈·array-element·배열 폼/인덱스 probe·23개 독립 값 fixture가 신규다. rank1~3/256요소/4096 buffer 한도이며 native/nested/array-of-struct와 동적 인덱스는 B 이후다. 실제 장치 통신과 P6 승인은 제외한다.

### P3-F bounded selector 완료 · 2026-10-17

- [x] 1~32 scalar 후보·정수 index·reject/default-candidate의 graph 2.5 계약 및 검증.
- [x] 선택 후보만 값/시간/품질 평가, 명시적 previousIndex에 따른 sourceRef 변경 비교와 화면.
- [x] 기존 SQLite CAS/시나리오 재사용, 이전 DB 보존 복제, HTTP 저장·재조회·무변경 preview 검증.

[설계·재사용/신규 범위](docs/P3-F-BOUNDED-SELECTOR.md) · [fixture](fixtures/p3f/README.md) · [검증 보고](docs/verification/P3-F-RESULTS.md). 실제 통신·임의 주소식·후보 그래프·자동 failover 제외. MP13 전체는 부분 지원이다.

### P4-A bounded 파일 importer 완료 · 2026-10-17

- [x] XLSX 시트/행·명시적 columnMap 및 tyr-config-v1 설정 JSON에서 접근 정의 draft 생성.
- [x] base/stride/count·instance override, alias chain·missing/cycle/duplicate·유한 한도 검증.
- [x] 원본 bytes/hash, cell/JSON pointer, 미해석/assumptions·원본 template/alias 경로 보존과 제안 2.6 내보내기.
- [x] 가져오기 미리보기·선택 채택·원문 조회/다운로드, SQLite CAS·재개방·원본 변조/잘못된 채택 차단.

[설계·재사용/신규·한도](docs/P4-A-FILE-IMPORT.md) · [fixture](fixtures/p4a/README.md) · [검증](docs/verification/P4-A-RESULTS.md). 실제 첫 솔루션의 이름·버전/exporter는 미정이다. 벤더 설정 parser, PDF/.xls, UDT 상속·cross-file 참조, 미해석 해소·재가져오기 merge는 후속 범위다. 실제 장치 통신과 승인 제외.

### P4-B 혼합 소스·읽기/쓰기 정의 구현 · 2026-10-17

- [x] PLC/constant/solution-tag/external-value와 명시적 접근 방향의 source 2.7 계약.
- [x] 기존 정준 객체·그래프·읽기 매핑에 혼합 소스를 연결하고 가상 값/상수·품질/시간을 평가.
- [x] 읽기와 독립인 semantic → destination 쓰기 정의, 목적지 capability·타입·단위·근거·중복 검증.
- [x] 02 혼합 소스, 09 읽기 미리보기, 11 별도 쓰기 정의 화면·SQLite 저장/재조회·제안 2.7 보존.

[설계·재사용/신규·한도](docs/P4-B-MIXED-SOURCES.md) · [fixture](fixtures/p4b/README.md) · [검증](docs/verification/P4-B-RESULTS.md). MP14/15는 bounded subset 부분 지원이다. 실제 장치/솔루션 접속·SQL·쓰기 실행과 승인·자동 역변환은 제외한다.


### P5 변경 비교·담당자 검토 구현 · 2026-10-17

- [x] 불변 기준본과 저장본의 stable ID 기반 diff, 접근·디코딩·스케일·단위·의미·표시·원문 분류.
- [x] 객체·그래프·배열 indices·selector 후보·시간 정책·혼합 읽기/쓰기·importRef의 전이 검토 영향.
- [x] 확인자·시점·사유·근거와 대상/의존 해시를 묶은 불변 검토 이력, 변경 시 needs-review.
- [x] 불완전 입력·정의 충돌·선언 view/공유 접근 진단, SQLite 추가 테이블·기존 데이터 보존·12 변경과 검토 화면.
- [x] A04/A05/A07/A16의 오프라인 검증. 기존 2.x에서 금지된 view/native 구조를 새로 허용한다는 뜻은 아니다.

[설계·경계](docs/P5-CHANGE-REVIEW.md) · [fixture](fixtures/p5/README.md) · [검증](docs/verification/P5-RESULTS.md). 검토는 로컬 선언이며 승인/인증/실장치 확인이 아니다. 비교 기준본은 승인 릴리스가 아니다. 다음 주 단계는 P6 Bifrost 계약·승인 연계다. 실제 장치 통신·외부 SQL·쓰기 실행은 계속 제외한다.


### P6 Bifrost 계약·서명 승인·파일 릴리스 완료 · 2026-10-17

- [x] 2.9 submission/validation/approval/release 계약. 기존 56개 Schema는 보존.
- [x] Bifrost 독립 Java 수신 검사: 네 프로파일·설비/연결·전체 참조/파일 hash·타입/단위·의미·그래프/배열/selector·별도 쓰기 정의.
- [x] registered Ed25519 두 키·PUBLISH/APPROVE 권한, 제안/전체 묶음/기준 릴리스/수신 변경 보고서 hash에 묶인 승인.
- [x] 동일 스트림의 같은 semanticId가 다른 role/type/unit으로 바뀌는 개정 거부. 오래된 기준·승인·변조·미확인·unknown-op 거부.
- [x] staging 재검증·원자적 디렉터리/HEAD 발행과 실패 시 이전 HEAD 유지. 발행은 운영 활성화가 아님.
- [x] Týr 선택 매핑 복수 export/ZIP·SQLite 제출 이력·CLI 검사/서명 승인/발행 상태 조회, 13 화면.
- [x] Týr 신규 37 + 회귀 664, Bifrost 기존 614 + 신규 47 직접 검증. A11/A12/A16 오프라인 경계 및 실제 두 앱 seam.

[설계·권위 경계](docs/P6-BIFROST-PUBLICATION.md) · [fixture](fixtures/p6/README.md) · [검증](docs/verification/P6-RESULTS.md). Bifrost는 codex/tyr-p6-mapping-release 로컬 feature 브랜치에서 변경했으며 commit/push/merge는 하지 않았다.

완료 범위는 별도 로컬 registry에서의 파일 승인/발행이다. 운영 IAM/bootstrap, 외부 anchor/rollback-evidence, 전원 손실 durability는 후속이다. 여러 스트림의 의미 카탈로그는 아래 P6 후속에서 하나의 registry 전체 보존 이력 범위로 수용했다. registry 간 연합은 별도다. 프로세스 중단 복구·보수적 GC는 아래 P6 후속 수용에서 별도로 완료했다. 다음 주 단계는 P7 오프라인 수용과 실제 문서/담당자의 PoV이며 실제 자료 확보는 미완료다. 장치 통신·외부 SQL·쓰기 실행은 계속 제외한다.


## P7 오프라인 수용 검증 (2026-10-17)

[절차·현장 PoV 분리](docs/P7-OFFLINE-ACCEPTANCE.md) · [A01~A16 수용 기록](docs/verification/P7-RESULTS.md) · [기계 판정](docs/verification/p7-acceptance.json).

- [x] 기존 P1~P6 fixture의 701개 검사 검증. 최초 로컬 HTTP 오류 1건은 기록을 보존하고 동일 제품/fixture에서 격리 재실행해 통과. P3-A 별도 CLI 52개 포함.
- [x] Bifrost mapping 수용 회귀 47개를 Maven offline으로 실행. 승인 후 변경·릴리스 변조·stale base를 독립 구현으로 재검증.
- [x] A01~A16의 실제 시험 ID 연결: 14개 충족, A07·A14 부분 충족. 부분 충족은 전체 기능 지원으로 계산하지 않음.
- [x] Python 외부 connect/connect_ex/DNS 차단과 거부 negative control. 로컬 UI/API는 loopback 사용.
- [x] 네 접근·객체·그래프·분산 프로퍼티·단위/스케일·가상 차압·원본/미해석·읽기쓰기·변경/검토·릴리스 화면 조회와 복제 SQLite 저장/재조회.
- [x] P6 원본 revision 39 보존. 복제본에서 설비 이름만 바꾸어 revision 40 저장. migration·시나리오·기준본·검토·제출의 모든 행 보존.
- [x] 짧은 화면의 사이드바 하단 메뉴 접근 결함을 세로 스크롤로 수정하고 실제 마우스 클릭 확인.
- [x] A07 전체 워드/비트 view의 새 계약·작성·저장·수신 검증·발행: 아래 2.10.0 후속에서 완료. 최초 P7의 부분 충족 기록과 구분.
- [x] A14 브라우저·Java·Python 전체의 외부 네트워크 차단 수용: 아래 Linux container/OS namespace 후속 완료. Python guard/Maven -o나 호스트 Windows 전체 방화벽 시험으로 대체 계산하지 않음.
- [ ] 실제 익명화 문서·솔루션 export/버전·개정본과 독립 담당자 정답으로 PoV. 오매핑/누락/손실·전체 검토 시간·미사용 설비의 재사용성 측정.

오프라인 검증 결과와 실제 현장 수용 완료를 구분한다. native/nested 구조·추가 vendor 형식·운영 활성화는 기존 후속 범위다. 계약·backend·fixture·SQLite 스키마는 이번에 수정하지 않았다. 실제 장치 통신·외부 SQL·쓰기 실행은 계속 제외한다.


## P7 A07 후속: 명시적 alias·전체 워드·비트 view (2026-10-18)

[계약·사용](docs/A07-SOURCE-VIEWS.md) · [수용 결과](docs/verification/A07-RESULTS.md). 기존 P7의 14/2 기록은 최초 실행의 역사적 결과로 유지하며, 현재 A07은 아래 bounded 범위에서 충족한다.

- [x] 기존 계약 60개 보존, 2.10.0 source-definition/common 추가. 직접 소스와 2.0 작성본·기존 proposal/submission/release 호환 유지.
- [x] PLC 정수 워드의 명시적 alias·bit view, 부모 버전/접근 snapshot·read-only·근거·최대 16단계·순환/누락/범위 검사.
- [x] 14 화면 작성/저장/편집, 05/06 graph·객체 의미 매핑, 07 조회, 09 원본 입력 한 번의 view 단계·시각/품질 전파.
- [x] SQLite 기존 행/스키마 보존, 새 view roundtrip·원자성·revision 검사. 부모 변경은 기존 snapshot 불일치와 함께 보존하고 검토/발행 차단.
- [x] Bifrost 독립 수신 검증·부모/evidence closure·두 키 승인·파일 릴리스 발행. 기존 서명·변조·base 충돌 검사 유지.
- [x] 네 PLC 20소스/20바인딩 fixture, 12개 독립 부정 변형, 전용 39검사·기존 701회귀·Bifrost 60검사, 32/64비트 경계 probe 2개.
- [x] 실제 화면 저장본을 a07-view-release@1.0.0으로 시험 registry에서 발행. 임시 개인 키는 저장소 밖에서 생성 후 삭제.
- [x] A14 테스트 런타임 전체의 OS 네트워크 격리는 아래 후속에서 완료.
- [ ] 호스트 Windows 전체 방화벽 수용 및 실제 현장 PoV는 별도 미수행. vendor alias 자동 해석·배열/codec/native 구조 view·실장치·외부 SQL·쓰기 실행·runtime 활성화는 범위 밖.


## P7 A14 후속: 테스트 런타임 전체 OS 네트워크 격리 (2026-10-18)

[설계·재현·경계](docs/A14-NETWORK-ISOLATION.md) · [수용 결과](docs/verification/A14-RESULTS.md) · [현재 A01~A16](docs/verification/a14-acceptance.json).

- [x] 실제 headless Chromium·Python·Java를 같은 Docker --network none namespace에서 실행. lo/외부 경로 부재·localhost DNS·실제 TCP/UDP/DNS/브라우저 실패 및 loopback 성공 증거.
- [x] 화면 작성·기존 view 편집·공통 의미 매핑·SQLite 재개방·가상 preview·불변 제출·Java 독립 검증·두 키 승인·파일 발행·UI 재조회/ZIP/24파일 hash 확인.
- [x] 기존 view 편집 ID 처리 버그 수정. 계약/API·SQLite 스키마·Java jar 보존.
- [x] date-time/uri 선택적 검사기 의존성과 정상/오류 preflight를 고정. A07 39 + 기존 701을 같은 격리 안에서 전부 직접 검증.
- [x] 원본 SQLite backup/행/revision/개방 바이트 보존, fixture·기존 60개 Schema 불변. 기존 59772~59774 DB/registry 유지.
- [x] 실행 DB/registry는 Linux 로컬 디스크, 결과는 일괄 archive 반출. 중단·실패 원본과 최종 성공을 분리.
- [ ] 실제 현장 자료/독립 정답/검토 시간/타 설비 재사용성 PoV 및 목표 Windows PC/VM의 배포 수용.

현재 16개 충족은 기존 지원 범위의 가상 오프라인 fixture 수용이다. 모든 vendor 형식·모든 브라우저 폼 조합·현장 정확도를 보장하지 않는다. 실제 장치 통신·외부 SQL·쓰기 실행·운영 활성화는 계속 제외한다.


## P3-C B 제한 sqrt·clamp 후속

[계약·범위](docs/P3-C-BOUNDED-MATH.md) · [가상 fixture](fixtures/p3cb/README.md) · [검증 결과](docs/verification/P3-C-B-RESULTS.md).

- [x] 2.11.0 그래프에 무차원 sqrt(34자리 half-even)와 같은 known 단위의 clamp 추가. 기존 계약 파일 유지.
- [x] Python·독립 Java의 타입·단위·경계 검증, 음수 도메인·근사·clipping·최종 cast 진단과 단계별 preview.
- [x] 05 화면의 노드 작성·연결·저장과 기존 SQLite JSON/CAS·재조회 경로. DB 테이블/기존 행의 자동 migration 없음.
- [x] 격리 브라우저 수용 17/17, 새 테스트 17/17, 기존 회귀 740/740, 독립 Java 64/64 통과. 기존 schema 62개·fixture 462개 SHA 유지.

### 남은 항목 재분류

| 항목 | 실제 현장 자료 없이 가능한 다음 구현 | 현장 자료/담당자 검증이 필요한 부분 |
|---|---|---|
| P3-E B | 2.12 논리 구조·중첩·고정 구조 배열 구현, 아래 수용 결과로 완료 판정 | native UDT/DB packing·alignment·vendor export와 실제 타입 일치 |
| P3-F B | 2.13 유한 scalar DAG 후보의 타입/단위/시간/품질·출처 구현, 아래 수용 결과로 완료 판정 | 현장 selector·운전 모드의 의미와 fallback 정책 정답 |
| P4-A B | 2.14 미해석 해결·3방향 충돌/병합·유지/제거 보존 구현, 아래 최종 수용으로 완료 판정 | 실제 XLSX·PDF·제품별 설정 파일의 해석 정확도·미지원 문법 |
| P6 후속 | 프로세스 중단 복구·보수적 GC·파일 무결성 fault injection 구현, 아래 오프라인 수용으로 완료 판정 | 운영 IAM/bootstrap·권한 책임·외부 anchor·실제 활성화 |
| P7 현장 PoV | 익명화 인수 양식·독립 oracle·평가 집계/화면/CLI·절차 준비, 아래 오프라인 수용으로 완료 판정 | 실제 자료와 담당자 독립 정답, 수렴/오매핑/누락/손실/검토 시간 측정 |

이번 단계는 제한 비선형 그래프를 오프라인으로 확장한다. 현장 수요·제품 지원·운영 가용성을 검증 완료로 바꾸지 않는다. 장치 통신·외부 SQL·쓰기 실행은 계속 제외한다.


## P3-E B 논리 구조·중첩 멤버·고정 구조 배열

[계약·화면·경계](docs/P3-E-LOGICAL-STRUCTURES.md) · [독립 fixture](fixtures/p3eb/README.md) · [수용 결과](docs/verification/P3-E-B-RESULTS.md).

- [x] 2.12 semantic-definition/mapping-set/common 추가. inline Structure/StructureArray와 전체 member/index 경로, 깊이·노드·확장 말단·shape/rank/상한 제한.
- [x] 말단별 의미·단위·타입·근거·설비·중복·완전성 검증. 기존 source/graph/target/proposal/release 계약 재사용.
- [x] 15 트리 작성/JSON 편집, 06 전체 경로별 변환/시간·품질 저장, 07 비교, 09 개별 preview, 15 객체 조립·partialResult·오류 전파.
- [x] SQLite workspace 2.0.0·기존 테이블/CAS 재사용. 기존 데이터 자동 재작성/migration 없음.
- [x] 최종 브라우저 20/20, 새 Python 30/30·기존 회귀 757/757, Java 75/75 통과. 기존 schema 64개·fixture 467개 SHA 유지. Full/UI-focused 실행 증거를 분리 보존.
- [ ] vendor native UDT/DB offset/packing/alignment/BOOL/endianness·실제 export/ExtensionObject 자료 검증.
- [ ] 현장 PoV: 실제 자료·담당자의 독립 정답·검토 시간 비교.

이번 범위는 논리 정준 객체 작성과 가상 평가다. native 구조 bulk read/타입 browse·실제 프로토콜 통신·외부 SQL·쓰기 실행·runtime 활성화를 추가하지 않는다. native 배치와 현장 PoV의 미완료 상태는 논리 구조 수용과 별개로 유지한다.


## P3-F B 유한 후보 그래프 선택

[계약·화면·경계](docs/P3-F-GRAPH-CANDIDATES.md) · [fixture](fixtures/p3fb/README.md) · [최종 수용 결과](docs/verification/P3-F-B-RESULTS.md).

- [x] 2.13 graph 계약: 최대 32개 직접 소스 또는 같은 graph의 scalar DAG 출력 후보, 중첩 selector. index/previousIndex는 직접 정수 소스로 유지.
- [x] 모든 후보 타입·단위·근거·참조·DAG/범위 검사. 범위 초과의 명시적 기본 후보와 입력 오류의 대체 금지를 구분.
- [x] 선택 경로의 decoding/연산/변환/cast·손실과 freshness/skew/결측/bad/uncertain을 단계별 preview. 미선택 후보는 not-evaluated.
- [x] 후보 picker·순서·타입/단위 요약, 작성·저장·재열기, SQLite JSON/CAS/시나리오와 이전 버전 호환.
- [x] 후보 참조·계산 정의 SHA·실제 선택 source refs·명시적 이전 후보의 정의 기반 출처 비교. 이전 후보 값을 실행하지 않음.
- [x] 독립 Bifrost schema/DAG/type/unit/evidence 검증, 두 키 승인·파일 발행. 제어 입력 단계와 후보 값 단계의 분리를 독립 Python/Java로 검증.
- [x] OS network namespace 격리 경로 29/29, 신규 39/39·기존 787/787, 독립 Java 84/84. 기존 schema 67개·fixture 파일 475개 SHA 유지.
- [ ] 실제 canonical 의미·운전모드별 후보 정답·fallback 합의·timestamp/quality 수집의 현장 PoV.
- [ ] vendor native 배치/실제 export·임의 주소식·자동 실행 간 lineage 감사. 같은 설비 scalar cross-graph는 아래 P3-F C로 구현.

타입·단위 수용을 물리적 의미 동등성의 자동 증명으로 간주하지 않는다. 장치 통신·외부 SQL·쓰기 실행은 계속 제외한다. 기존 전체 pattern matrix의 partial 상태와 현장 PoV 미수행 상태를 유지한다.


## P4-A B 미해석 항목 해결·재가져오기 충돌·병합

[계약·화면·경계](docs/P4-A-IMPORT-RECONCILIATION.md) · [합성 fixture](fixtures/p4ab/README.md) · [최종 수용 결과](docs/verification/P4-A-B-RESULTS.md).

- [x] 기존 2.6 parser/원본/관측은 고정하고 2.14 검토 hash chain·명시적 source 해결·비소스 분류·별도 draft 채택.
- [x] recordKey와 이전 imported 기준/현재 작성본/새 파일의 3방향 필드 비교. 모든 충돌 선택·현재 정의 전체 유지·새 항목 채택/보존·제거 보존/재등장.
- [x] canonical 소스 ID/버전·매핑 참조·로컬 note 유지, label 병합, 새 source 근거와 의존 객체/그래프/매핑/쓰기 정의의 evidence closure 갱신.
- [x] 미해석 새 batch를 원문 보존→명시적 해결→incoming으로 재선택하여 병합. 자동 주소/이름 추측과 수식 실행 없음.
- [x] 화면 원문/검토 이력·명시적 편집 틀 복사·변경 필드/충돌·이전/현재/새 snapshot과 처리 선택, 저장/재열기/기존 canonical preview.
- [x] 기존 SQLite JSON/CAS/schema/migration 재사용. 2.14 원본 교체·이력 축소·완료 reconciliation 변경을 일반 저장에서도 원자적으로 거부.
- [x] 독립 Bifrost wire 검증·두 키 승인·파일 발행, 기존 2.6 닫힌 importer 호환. 원격 schema/장치/SQL 실행 없음.
- [x] 격리 수용 경로 24/24, 신규 58/58·기존 826/826, Java 100/100. 기존 schema 69개·fixture 파일 483개 SHA 유지.
- [ ] 실제 vendor 설정/현장 XLSX layout·ID 안정성·수동 해석/비소스 분류·canonical 의미 정답·검토 시간/오매핑률의 현장 PoV.
- [ ] PDF/.xls·vendor 타입명/UDT 상속/cross-file alias·대량 history/GC·자동 fuzzy matching.

타입·단위 수용을 현장 의미 동등성의 자동 증명으로 간주하지 않는다. MP03/12/18 전체의 partial 상태와 현장 PoV 미수행 상태를 유지한다. 장치 통신·외부 SQL·쓰기 실행은 계속 제외한다.


## P6 후속 프로세스 중단 복구·GC·파일 무결성 (2026-10-18)

[설계·경계](docs/P6-RECOVERY-GC.md) · [fault fixture](fixtures/p6-recovery/README.md) · [수용 결과](docs/verification/P6-RECOVERY-RESULTS.md).

- [x] Bifrost 파일 발행 저널·기준 head CAS 복구·완료 후 반복 실행 무변경. pending journal은 approve/publish/GC 차단. Týr에는 승인/복구 실행 권위를 추가하지 않음.
- [x] intent/release/head 각 지점의 예외·실제 JVM 종료, Týr 실제 프로세스 종료의 SQLite rollback/commit 보존, 손상·누락·충돌·symlink fault injection.
- [x] 과거 승인·unheaded 릴리스·전체 원본/검토 이력 closure 보존. 보수적 GC 사전 조회·내용/root pin 재검증·유예 기간·가역적 격리·중단 후 새 계획 지원. 영구 삭제 없음.
- [x] 13 화면의 제출 무결성·고아 폴더 조회/격리·corrupt 표시와 차단. 기존 계약·SQLite 테이블/CAS/행 유지, 사용자 기존 DB/registry 보존.
- [x] 최종 Linux 새 Python 13/13 + 기존 884/884, Windows 매핑 관련 Java 116/116, 격리 Chromium/Python/Java 연계 34/34. 기존 계약 파일 72개(schema 71개)·fixture 500개 SHA 보존, Java schema 사본 동일.
- [x] 최초 실패와 fixture 수정 후 전체 재실행·소스/JAR/이미지/실행 인자 증거를 분리 보존. 별도 시연 DB/localhost:59779.
- [ ] 전원/OS 손실·파일시스템 crash durability·목표 Windows 배포/공유 스토리지·대량 규모 수용.
- [ ] 운영 IAM/bootstrap·키 책임·외부 anchor/rollback 증명·실제 활성화 및 실제 자료/담당자 독립 정답 기반 현장 PoV.

장치 통신·외부 SQL·쓰기 실행은 계속 제외한다. 이번 GC는 임시 자료 격리이며 workspace/import history 압축·승인/릴리스 삭제를 구현하지 않는다. 현장 PoV 미완료는 오프라인 수용과 별도로 유지한다.


## P7 후속 독립 정답·평가 준비 (2026-10-18)

[도구·계약](docs/P7-EVALUATION-PREPARATION.md) · [합성 fixture](docs/P7-EVALUATION-FIXTURES.md) · [현장 절차·인수 양식](docs/P7-POV-PROTOCOL.md) · [수용 결과](docs/verification/P7-EVALUATION-RESULTS.md).

- [x] 별도 evaluation pack 1.0.0과 빈 정답 양식·현재 inventory 분리. 독립 검토 선언·근거·설비/객체 버전/전체 member/index identity, source/graph/view 정의 closure pin.
- [x] 의미/정의 차이·가상 값/타입/단위/품질/오류/손실 진단·누락/중복/미검토/추가 미평가와 범위 coverage. 미검토·sample/pin 없는 항목을 완전 확인으로 승격하지 않음.
- [x] calibration/evaluation/heldout, 모든 기준 항목 분모·sample 미실행·시간 미측정, 문의/수정/재검토 포함 여섯 단계 paired 시간과 수행 순서 분리.
- [x] 16 화면과 읽기 전용 API·CLI·pack/report 파일 저장·revision/입력/report pin. 기존 SQLite 테이블·행·기존 데이터 개방 보존, 승인/실행 권위 추가 없음.
- [x] 네 profile/40 nested 말단·독립 수치/손실 oracle. 새 35 + 기존 897 = 932 Python·fixture 검사, 최종 격리 화면/HTTP/SQLite/CLI 18 검사 통과. canonical 계약 파일 72개·기존 fixture 502개와 Bifrost JAR 보존.
- [x] 익명화 인수 template·자료 split/동결·독립 담당자·교차 순서·원시 시간 기록·확대 판단 절차 문서화. 별도 데모 localhost:59780/16 화면.
- [ ] 실제 자료 인수·가명화 확인·독립 담당자 정답·실제 시간/오매핑/누락/손실·미사용 설비 재사용성 측정. 합성 확인율/시간을 현장 실적으로 계산하지 않음.

### 남은 미완료 항목 분류

| 분류 | 남은 내용 | 완료에 필요한 근거 |
|---|---|---|
| 실제 현장 PoV | 제품/버전·동시점 문서/설정·개정본, 의미/selector 정책 정답, 전체 검토 시간·재사용성 | 실제 익명화 자료와 독립 담당자·측정 원본 |
| vendor 검증 | native UDT/DB packing/alignment/BOOL/endianness, 실제 export 문법/ID 안정성 | 제품별 실제 자료와 vendor/native 독립 정답 |
| 추가 제품 확장 | PDF/.xls/OCR·추가 importer/cross-file alias, 일반 식/차원 분석·임의 주소식/cross-value-graph endpoint, registry 간 semantic catalog 연합·대량 history 정리 | 별도 구현 범위·계약/fixture/화면/수신 검증; parser 제품 지원 확정에는 실제 자료 필요 |
| 운영 환경 수용 | Windows 배포/전체 방화벽·공유 스토리지/전원 손실·대량 규모, IAM/bootstrap/외부 anchor/활성화 | 별도 목표 환경과 운영 책임/시험 절차 |

앞의 실제 현장 PoV 체크박스들은 미완료로 유지한다. 평가 도구는 자기 선언·구조 pin·가상 시험의 일치를 보고할 뿐 현장 인증이나 Bifrost 승인을 대체하지 않는다. 장치 통신·외부 SQL·쓰기 실행은 계속 제외한다.


## P3-C C 제한 add·multiply·divide (2026-10-18)

[계약·범위](docs/P3-C-BOUNDED-ARITHMETIC.md) · [합성 fixture](fixtures/p3cc/README.md) · [수용 결과](docs/verification/P3-C-C-RESULTS.md).

- [x] 2.15.0 graph/common 추가. 수치 scalar의 명명된 left/right·Decimal 출력, 같은 선형 단위 add, 무차원 계수 multiply, 무차원 분모/같은 단위 비율 divide. 기존 계약 파일/SQLite 테이블/버전·행 보존.
- [x] Python 단위/정적 검증·제한 계산과 독립 Java 수신 검증. divide 34자리 half-even 고정·0/-0 분모·근사/최종 cast 손실, unknown/온도/복합 차원/임의 문자열 거부.
- [x] 05 작성/편집/저장·09 단계별 가상 preview·SQLite 재개방/CAS/원자성·시간/품질 차단·selector 미선택 후보 지연 평가. 기존 13 서명 승인/파일 발행·16 평가 양식과 연결.
- [x] 네 PLC 12소스/4객체/16바인딩·독립 수치/오류 oracle, 새 Python 28 + 기존 932 = 960 검사, Java 127, 격리 화면/HTTP/SQLite/CLI 21 검사 통과. 실제 이전 JAR 수신 양성/음성 control 2개 통과.
- [x] 기존 canonical 파일 72개·평가 계약 1개·fixture 507개 SHA 보존, 현재 Java schema 사본 73개 동일. P7의 단계별 JAR freeze 단언을 구 schema 보존으로 전환하고 과거 수용 기록 유지.
- [x] 별도 DB/registry와 localhost:59781 시연. 기존 사용자 DB/registry·장치 통신·외부 SQL·쓰기 실행·runtime 활성화 경계 유지.
- [ ] 일반 식 문법 전체·일반 차원 분석/복합/역단위·온도 delta·설비 간/동적 graph 참조 전체 지원. 같은 설비 scalar endpoint는 아래 P3-F C로 구현. 제한 작성 문법은 아래 P3-C D로 별도 완료. 임의 코드 eval 실행은 범위 밖.
- [ ] 실제 자료의 의미·계수/단위·허용 오차·운전 정책·native/export 정답과 전체 검토 시간·재사용성 현장 PoV.

이번 완료는 유한 scalar 산술 세 노드의 제한 확장이다. 이전 일반 식/차원 분석·현장 PoV의 미완료 항목을 일괄 완료 처리하지 않는다. Bifrost는 정적 정의를 승인하고 실제 입력의 계산/0 분모 검사는 이번 가상 preview에서만 수행한다.


## P6 후속: registry 전체 의미 카탈로그 (2026-10-18)

[설계·경계](docs/P6-SEMANTIC-CATALOG.md) · [합성 fixture](fixtures/semantic-catalog/README.md) · [수용 결과](docs/verification/SEMANTIC-CATALOG-RESULTS.md).

- [x] 별도 2.16.0 조회 보고서와 독립 Java 카탈로그. 하나의 registry에 보존된 모든 스트림/역사 릴리스·unheaded 릴리스·중첩 정의·구조 배열 서명·원본 정의 경로/릴리스 SHA 근거.
- [x] 같은 URI의 scalar role/type/unit 및 container 재귀 계약 검사. 같은 이름의 다른 URI는 분리, 다른 이름의 같은 계약은 재사용. 물리적 의미 자동 추론/병합 없음.
- [x] 승인·발행 시 전체 역사 재검사, 지연 승인 충돌과 기존 역사 충돌 차단. pending 복구 요구·파일/서명/head 손상 거부·복구 경로의 의미 계약 재검사.
- [x] 13 화면 현재 작성본 비교와 registry 전체 원본 근거 조회. 미조회/신규/계약 일치/작성본 내부 충돌/보존 릴리스 충돌 구분. SQLite 기존 테이블/행/CAS/제출 기록·정준 계약 보존, 파생 카탈로그 migration 없음.
- [x] 최종 Python·fixture 975/975 (새 15 + 기존 960), 매핑 관련 Java 138/138 (새 11 + 기존 127), 격리 연계 27/27. 기존 계약 74개·fixture 511개·평가 계약 1개 SHA 보존, 현재 스키마 74개 Java 사본 동일. 최초 시험 실패와 전체 재실행 결과 분리 보존.
- [ ] 여러 registry 연합·외부 의미 사전 연계·URI 소유권/개정/폐기 운영 정책·대량 규모 수용. 개정·폐기 메커니즘은 아래 P6 절에서 별도 수용했다.
- [ ] 실제 URI 의미 정답·단위 합의·오매핑/누락·검토 시간·재사용성 현장 PoV, vendor native 배치/실제 export 검증.

전역 범위는 구성된 한 registry 전체 이력이다. 이전 여러 스트림 카탈로그 공백의 이 범위만 구현하며 IAM·외부 anchor·운영 활성화는 완료로 바꾸지 않는다. 장치 통신·외부 SQL·쓰기 실행은 계속 제외한다.


## P3-C D 제한 수식 작성·컴파일 (2026-10-18)

[설계·계약·경계](docs/P3-C-BOUNDED-EXPRESSION.md) · [합성 fixture](fixtures/expression/README.md) · [수용 결과](docs/verification/BOUNDED-EXPRESSION-RESULTS.md).

- [x] 명시적 `[소스ID]`, 사칙연산·괄호·좌결합/우선순위, sqrt/clamp/linear 제한 문법. 입력/깊이/연산/크기 제한·알 수 없는 함수/코드/차원/참조 거부, 기존 2.15 DAG로 컴파일. canonical 계약·Bifrost 코드/JAR 변경 없음.
- [x] 17 화면 컴파일·타입/단위/근거·원문 위치·원문 재열기·stale/명시적 재컴파일, 기존 05 그래프·06 매핑·09 값/손실/품질·13 승인/파일 발행 경로 재사용.
- [x] 로컬 editor recipe 1.0.0과 append-only 원문/DAG/source-context pin 이력. 첫 apply 때만 별도 SQLite 테이블을 같은 CAS 트랜잭션에서 추가, rollback 포함. 기존 DB 재개방/조회/compile만으로 행/schema 변경 없음.
- [x] 최종 새 수식 30 + 기존 975 = Python·fixture 1,005 검사, 격리 연계 37 검사 통과. 기존 계약 75개·fixture 513개·평가 계약 1개 SHA 및 Bifrost 코드/JAR 보존, 기존 schema 74개 사본 동일. 원문 괄호 범위 QA 수정 후 최종 전체 재검증·별도 localhost:59783 시연.
- [ ] 일반 식 전체·조건식·일반 차원 분석/복합/역단위·온도 delta·설비 간/동적 graph 참조. 같은 설비 scalar endpoint는 아래 P3-F C로 구현.
- [ ] 현장 의미/계수/단위/허용 범위 정답·검토 시간·재사용성 및 vendor native/export 검증 PoV.

이번 완료 범위는 작성 문법의 유한 부분집합이며 일반 식/차원 분석 전체 지원으로 표시하지 않는다. Bifrost에는 로컬 원문 recipe를 넣지 않고 기존 canonical DAG와 근거만 제출한다. 장치 통신·외부 SQL·쓰기 실행·runtime 활성화는 계속 제외한다.


## P3-C E 숫자·명시적 단위 상수 (2026-10-18)

[설계·계약·경계](docs/P3-C-EXPRESSION-LITERALS.md) · [합성 fixture](fixtures/expression-literals/README.md) · [수용 결과](docs/verification/EXPRESSION-LITERALS-RESULTS.md).

- [x] compiler 1.1 opt-in, bare 숫자=무차원 및 quantity 숫자/명시적 단위. 기존 1.0 기본 API·recipe 보존, 기존 2.7 constant/2.15 graph로 변환.
- [x] 생성 상수 근거·원문 위치·타입/단위 표시, 값/단위 변경 시 새 ID, 재사용 시 원본 선언 시각 보존. 충돌/수동 변경 덮어쓰기 거부.
- [x] 기존 CAS에서 소스·graph·recipe 원자 저장·rollback, 기존 SQLite 행/테이블 및 정준 계약 유지. 구 소스/이력 자동 삭제 없음.
- [x] 최종 신규 23 + 기존 1,005 = Python·fixture 1,028/1,028, 격리 브라우저·HTTP·SQLite·실제 Java CLI 연계 46/46. 기존 canonical 75개·fixture 516개·평가 계약 1개·local 1.0 계약 1개 SHA 및 Bifrost 관련 85 pin/JAR 유지. 최초 사전 실행 실패와 최종 전체 결과 분리 보존. 별도 localhost:59784 시연.
- [ ] 일반 조건식·차원 분석/복합/역단위·온도 delta·설비 간/동적 graph 참조 전체 지원. 같은 설비 scalar endpoint는 아래 P3-F C로 구현.
- [ ] 실제 계수/단위 의미 정답·검토 시간·재사용성·vendor native/export 현장 PoV.

실제 장치 통신·외부 SQL·쓰기 실행·runtime 활성화는 제외한다. Decimal 가상 계산은 native IEEE 저장 정밀도 검증을 대체하지 않는다.


## P3-F C 그래프 간 scalar 결과 재사용 (2026-10-18)

[설계·계약·경계](docs/P3-F-CROSS-GRAPH.md) · [합성 fixture](fixtures/cross-graph/README.md) · [수용 결과](docs/verification/CROSS-GRAPH-RESULTS.md).

- [x] 2.17.0 graph endpoint의 ID/버전/노드 고정, 기존 producer/consumer 계약 공존. 같은 설비의 scalar만 참조.
- [x] 독립 Python/Java graph 의존 순서·자기/다중 순환·없는 버전/노드·설비·타입/단위·재귀 근거 검증, 32 graph/128 node-path/8192 node 한계.
- [x] 05 외부 결과 선택·순환 경로, 06 근거 자동 수집, SQLite 원자 JSON 저장·기존 DB 보존, 09 재귀 가상 계산·참조 trace·선택 경로/출처 pin.
- [x] 신규 Python28 + 기존1,028 = 1,056/1,056, 신규 Java18 + 기존138 = 156/156, 격리 브라우저·HTTP·SQLite·실제 Java CLI 연계58/58. 기존 canonical75·fixture519·평가1·recipe2 SHA 및 현재 schema76 사본 유지. 최초 음성 fixture 실패·수정·최종 검증 기록 분리, 별도 localhost:59785 시연.
- [ ] 동적 그래프/주소식·배열 전체/native 구조 bulk 결과의 추가 범위. 설비 간 템플릿 재사용은 아래 P6 후속에서 별도로 구현한다.
- [ ] 실제 의미/단위/계수·운전모드·허용 오차·검토 시간/재사용성 및 vendor native/export 현장 PoV.

정준 구 계약·workspace 2.0·SQLite·구 수식 recipe를 보존한다. 장치 통신·외부 SQL·쓰기 실행·runtime 활성화는 계속 제외한다.


## P6 의미 URI 개정·폐기 (2026-10-18)

[설계·계약·경계](docs/P6-SEMANTIC-LIFECYCLE.md) · [합성 fixture](fixtures/semantic-lifecycle/README.md).

- [x] 2.18 불변 lifecycle 이벤트, active/deprecated/retired 전이, 설명 개정·명시적 대체 URI, 의미 signature 고정. URI 의미 변경은 새 URI로 구분.
- [x] 독립 Python/Java의 선행 해시·연속 개정·fork·종단 상태·대체 순환/폐기·타입/단위/구조 signature 검증. 구 proposal·계약과 공존.
- [x] 18 화면에서 로컬/발행 상태·개정 사유/작성자/시각·이벤트별 원본 릴리스와 읽기/쓰기·중첩/구조 배열 조상 영향 조회. 현재 head와 과거 릴리스 구분.
- [x] SQLite workspace 2.0 선택 배열의 CAS 원자 저장·저장 이력 수정/삭제 거부. 기존 테이블과 행 자동 마이그레이션 없음.
- [x] 매핑 동반 또는 lifecycle-only immutable 제출, Bifrost 두 확인자 서명 승인·발행·복구의 registry 전체 이력 재검사. 구 bundle에서 이력을 생략해도 폐기 URI를 재발행할 수 없음.
- [x] Python·fixture 1,083 고유 검사, Java 174 고유 검사, URI 연계27·기존 화면 연계58 통과. 반복 unit/focus는 중복 합산하지 않음. 기존 contract77·fixture582·evaluation1·editor2 SHA 및 SQLite 행·스키마 보존. [수용 결과](docs/verification/SEMANTIC-LIFECYCLE-RESULTS.md). localhost:59786 시연.
- [ ] 실제 URI 소유권·개정/폐기 권한·유예/대체 정책·실제 소비자 inventory·의미 정답·현장 검토 시간 및 vendor native/export PoV.
- [ ] registry 연합·외부 의미 사전·운영 IAM·anchor·자동 branch rebase/ontology migration·운영 활성화.

폐기는 새 매핑의 승인·발행을 차단한다. 보존 릴리스·다른 스트림의 기존 head·실행 중인 설비를 소급 삭제하거나 변경하지 않는다. 남은 사용처를 영향 목록에서 확인한 후 각 스트림을 명시적으로 정리한다. 장치 통신·외부 SQL·쓰기 실행은 계속 제외한다.


## P6 후속: 매핑 템플릿·적용본 (2026-10-18)

[설계·계약·UX](docs/P6-MAPPING-TEMPLATES.md) · [합성 fixture](fixtures/mapping-templates/README.md) · [검증 기록](docs/verification/MAPPING-TEMPLATES-RESULTS.md).

- [x] 2.19 불변 템플릿·적용본 계약, 전이 그래프 포획, 공통 의미/변환/정책, 디코딩/코덱/view 해석 후 타입·단위·기존 입력 단계 슬롯과 설비 소스 연결. 직접 슬롯에 없는 view 부모도 고정 snapshot으로 보존.
- [x] canonical 해시와 템플릿 버전 고정, 단일 버전/적용 체인, 변경 영향·명시적 갱신. 객체 ID 유지·그래프 세대 보존·기존 소비자 자동 변경 없음.
- [x] 19 화면의 슬롯 이름·주소/호환 후보·명시적 추천 채우기·가상 결과/trace·비교 후 저장·개정안/이력 조회. 기존 09/13 경로 연결.
- [x] 기존 SQLite JSON 선택 배열/CAS 원자 저장·이력 수정/삭제 거부, 기존 DDL/자동 migration 없음. Python/독립 Java 결정적 생성물 비교와 Bifrost registry 전체 승인·발행 재검사.
- [x] 최종 Python·fixture1,107, Java 고유187(기존 Publication133 + 최종 package54), 격리 화면/HTTP/SQLite/실제 Java 서명 승인·발행34 통과. 기존 계약80·fixture619·evaluation1·editor2 합계702개 SHA 보존, 현재 schema83개 독립 Java/JAR byte 일치. [검증 결과](docs/verification/MAPPING-TEMPLATES-RESULTS.md). 별도 localhost:59787 시연.
- [ ] 실제 슬롯 의미·단위/계수·잘못된 추천/누락·전체 작성/적용/개정 시간·작업자 편의성·소비자 inventory 현장 PoV, vendor native/export 검증.
- [ ] 배열 배치 자동 적응·일반 template editor·대량 규모·자동 소비자 갱신·registry 연합·운영 IAM/활성화.

장치 통신·외부 SQL·쓰기 실행·운영 활성화는 계속 제외한다. 합성 재사용 성공을 현장 편의성 인증으로 표시하지 않는다.


## P4-C 레코드·결과 집합 객체 매핑 (2026-10-18)

[계약·UX·경계](docs/P4-C-RECORD-MAPPINGS.md) · [합성 fixture](fixtures/record-mappings/README.md) · [검증 기록](docs/verification/RECORD-MAPPINGS-RESULTS.md).

- [x] opt-in 2.20 record-mapping/virtual-result-set, typed 결과 스키마·복합 키·명시적 선택·0/1/N 및 bounded 객체 배열. 기존 의미 모델/2.19 템플릿/단위·스케일·cast·그래프 재사용.
- [x] NULL/default·누락/중복 키·미정의 열 보존·범위/타입/단위·가상 시각/품질·cast 손실과 단계별 미리보기. 오류 시 전체 결과 차단.
- [x] 20 필드 표·모델에서 초안·슬롯 재사용·새 버전 작성·레코드 표/JSON·시나리오 저장, 19 템플릿 사용처/변경 영향 및 18 URI 영향 연계.
- [x] optional workspace JSON/CAS·불변 버전/선행 SHA, 가상 입력만 명시 저장할 때 opt-in record_scenarios 테이블/CAS. 구 DB 조회/미리보기에서 자동 DDL/행 변경 없음.
- [x] record-only Bifrost 제출 closure와 독립 Java 정준 생성물/슬롯/출력/이력/URI 검증, 두 확인자 서명 승인·불변 릴리스. 가상 행은 제출/발행에서 제외.
- [x] Python·fixture 고유1,137/1,137, 독립 Java202/202, network-none 브라우저·HTTP·SQLite·실제 서명 승인/발행33/33. 기존797파일 SHA와 현재87 schema 사본/JAR 일치, 구 DB 조회 무변경. [검증 기록](docs/verification/RECORD-MAPPINGS-RESULTS.md), 별도 localhost:59788 시연.
- [ ] 실제 DB schema/key/NULL·계수·조회 시점/품질·provider export·작업자 편의/검토 시간 및 실제 소비자 계약 현장 PoV.
- [ ] 실제 DB 커넥터·일반 SQL/파라미터 실행·join/group/집계·native DB 타입 전체·다중 결과 집합·무한 스트림·운영 활성화. 별도 요청/범위 결정 필요.

장치 통신·외부 SQL·쓰기 실행·운영 활성화는 계속 제외한다. 가상 결과 집합의 시각/품질은 실제 DB 트랜잭션 일관성 보증이 아니다.


## P4-D 여러 소스의 한 객체 매핑 (2026-10-18)

[계약·UX·경계](docs/P4-D-MIXED-OBJECTS.md) · [합성 fixture](fixtures/mixed-objects/README.md) · [검증 기록](docs/verification/MIXED-OBJECTS-RESULTS.md).

- [x] opt-in source2.21 recordField의 record/필드/선택·SHA 고정, 원본 typed 필드·단위·단계·NULL/default와 기존 PLC/상수/외부 source·graph를 한 target/memberPath에 연결.
- [x] 기존2.19 템플릿/적용본을 재사용하여 신규 field source·객체·의미 모델·mapping·template/application을 한 CAS로 저장. 불변 source pin·새 소스/명시적 버전 적용, 구 계약/테이블/행 자동 변경 없음.
- [x] 21 프로퍼티별 출처/단위/스케일/cast, 같은 record 입력창 공유, 객체 전체·출처/키·단계·손실/부분 진단. 동일 record의 다른 snapshot 혼합·0/다건·중복/결측·타입/품질·시각 위조 차단.
- [x] 기존 SQLite preview_scenarios에 opt-in object/2.21 scalar 시나리오 저장·재개방·CAS/stale 관리,09/19 입력과20 정의 화면 연계.
- [x] self-contained source→record→template/model/history/evidence closure, 독립 Java 필드/슬롯/공학 변환·이력/downgrade 검증과 기존 Bifrost 서명 승인·불변 릴리스.
- [x] Python·fixture 고유1,165/1,165, Java219/219, network-none 브라우저·HTTP·SQLite·실제 서명 승인/발행33/33. 기존819파일 SHA와 현재92 schema 사본/JAR bytes 일치. [검증 기록](docs/verification/MIXED-OBJECTS-RESULTS.md), 별도 localhost:59789 시연.
- [ ] 실제 다중 소스 의미/계수·DB key/NULL·조회/PLC 시간 정합성·vendor/provider export·소비자 계약·작업자 작성/검토 편의 현장 PoV.
- [ ] 자동 DB join/집계·cross-equipment 결합·native DB 타입 전체·운영 커넥터/SQL/쓰기/활성화.

장치 통신·외부 SQL·쓰기 실행은 제외한다. 값 매핑/그래프의 시간 정책은 객체 전체 원자성 또는 서로 다른 프로퍼티 간 skew 보장이 아니다.


## P4-E 공통 입력·레코드 객체 배열 (2026-10-18)

[계약·공통 프레임·행 오류·UX](docs/P4-E-RECORD-BROADCAST.md) · [합성 fixture](fixtures/broadcast/README.md).

- [x] opt-in record-mapping2.22: 원본 행 필드/고정 공통 PLC·상수·외부 소스 슬롯, 템플릿2.19/의미/그래프/단위·스케일·cast 재사용, 이전2.20/2.21 유지.
- [x] single-virtual-frame·전체 freshness/skew/품질, reject-all 기본/명시적 omit-invalid, 키/중복/최대 건수 전역 차단, NULL/default·손실·원본·키별 진단.
- [x] 22 프로퍼티/슬롯 작성·비교·저장·새 버전·가상 배열/행별 미리보기, 공통 입력창 공유·상수 자동 사용·입력 저장·stale/CAS; 기존19/18/13 사용처·URI·승인 경로 연결.
- [x] 기존 workspace JSON·SQLite 테이블 재사용, 과거 불변 버전·소스핀·가상 시나리오 별도 저장. 자동 migration/기존 행 변경 없음.
- [x] 독립 Java 계약/소스핀/정준 생성물/이력·구 계약 우회 거부, 실서명 승인·불변 릴리스. Python·fixture 고유1,195/1,195, Java237/237, network-none 통합36/36. 기존858파일 SHA 및96 schema/JAR bytes 보존·일치. [검증 기록](docs/verification/RECORD-BROADCAST-RESULTS.md), 별도 localhost:59790 시연.
- [ ] 실제 키/단위/NULL/시간 정책·실패 행 제외 허용·소비자 계약·작업자 편의/검토 시간 및 vendor/provider native export 현장 PoV.
- [ ] 공통 source view/배열 자동 적응·설비 간 결합·DB join/집계·운영 커넥터/SQL/쓰기/활성화. 별도 범위.

장치 통신·외부 SQL·쓰기 실행은 계속 제외한다. 가상 시각 검증은 실제 동시 취득/DB 원자성 보장이 아니다.


## 작업자 흐름·독립 결과 스키마 (2026-10-18)

[작업 흐름·편집 계약·발행 경계](docs/OPERATOR-WORKFLOW.md) · [합성 fixture](fixtures/workflow/README.md).

- [x] 다섯 단계 시작/안내 화면·주 메뉴, 기존23개 도구 하위 배치, 단계 이름·선택한 설비/객체/스키마/템플릿 이어받기, 미저장 입력 보존과 검증/검토 문맥 이동.
- [x] 매핑·템플릿 없는 결과 스키마 필드 표 작성·검증·CAS 저장, 불변 버전/선행 SHA·사용처·명시적 개정, 객체 배열에서 직접 선택. 기존20 선행 작성 불필요.
- [x] 선택 workspace.resultSchemas와 기존 SQLite JSON/CAS 재사용, 기존 inline 스키마 fallback·충돌 차단, 무DDL/무자동migration. 기존 API·wire2.22/Bifrost JAR 유지.
- [x] 전체 Python·fixture 고유1,208/1,208, 새 흐름31/31·기존 배열36/36 network-none 브라우저·SQLite·실제 Bifrost 승인/발행, 기존890파일 SHA·JAR 보존. [검증 기록](docs/verification/OPERATOR-WORKFLOW-RESULTS.md).
- [ ] 실제 작업자 사용성/작성·검토 시간·선택 오류율·실제 문서/provider·키/NULL/단위 정답 현장 PoV.

장치 통신·외부 SQL·쓰기 실행은 계속 제외한다.


## 작업자 직접 조작·UX 보완 (2026-10-20)

- [x] 기존20 없이 독립 결과 스키마 → 객체 선택 → PLC/가상 DB/상수/외부 값 배열 연결 → 가상 검증 → 검토·로컬 제출을 CUA 브라우저에서 직접 수행.
- [x] 검증 폼 접기/연결 요약, 입력 범위·타입·단위·상수 안내, 유효한 연결 유지, 행 표 추가/제거, 이전 결과 무효화, 입력 초안 복원, 처리 중 표시, 검토/제출 대상 이어받기.
- [x] SQLite 시나리오 재개방·중복 키/bad 품질 차단 및 수정·Bifrost accepted/승인 대기 확인, 핵심 회귀43/43·기존918파일 SHA/JAR 보존. [검증 기록](docs/verification/OPERATOR-UX-WALKTHROUGH-RESULTS.md).
- [ ] 실제 현장 작업자의 과제 수행·작성/검토 시간·오류율 및 실자료 정답 PoV. 합성 직접 조작 결과와 구분한다.

기존 계약·SQLite DDL은 유지한다. 장치 통신·외부 SQL·쓰기 실행·운영 활성화는 제외한다.


## 빈 작업본·가상 엑셀 직접 검증 (2026-10-20)

- [x] 빈 DB0에서 시작·설비/논리 연결·한글 XLSX 업로드/열 대응·원본 보존·세 소스 검토·상수 저장 직접 수행.
- [x] 빈 시작/사전 조건/열 대응 표/초안 검토 경로/연속 프로퍼티 작성/표현식 선택적 입력 UX 반영. 기존 회귀101/101, 918파일 SHA/JAR 보존.
- [x] 별도 임시 DB의 동일 XLSX→객체/독립 스키마/배열/미리보기/Bifrost 계약 검증. 화면 검증과 구분.
- [x] 외부 값 저장 수정 확인·5프로퍼티 객체/독립 결과 스키마 작성·혼합 입력 배열/템플릿 저장·정상/중복 키 미리보기·SQLite 시나리오·검토/로컬 제출 직접 완료. revision16, Bifrost accepted=true/오류0/승인 대기. [직접 검증 기록](docs/verification/EMPTY-UX-WALKTHROUGH-RESULTS.md).
- [ ] 실제 현장 자료/작업자 PoV. 장치 통신·외부 SQL·쓰기 실행·활성화 제외.

## P4-F PIO·Kepware 외부 정의 수용 (2026-10-20, 설계·미구현)

[상세 설계·논리 모델·경계·SI01~SI18](docs/P4-F-SOLUTION-INTERPRETATION.md). 아래는 신규 작업이며 기존 P4-A/P4-A B 완료를 실제품 parser 지원으로 확대하지 않는다. 제조사 자료 제공은 선행 조건이 아니다. 허가된 현장 사본·오프라인 시험 자료를 확보하면 제품별 E를 진행한다.

2026-10-20 후속 결정: **vendor 원본은 Mímir만 해석**한다. Mímir가 해석 스냅샷을 파일 계약으로 발행하고 Týr는 그 소비자다. 아래 A의 해석 모델(SourceBundle~UnresolvedItem)은 Mímir wire 계약(A1), 검토·판정·전환 모델은 Týr editor 계약(A2)이다. E의 해석기 구현은 Mímir 작업이며 이 계획에는 Týr 쪽 수신·검증만 남는다. [§3 소유 분리](docs/P4-F-SOLUTION-INTERPRETATION.md)

### 재사용과 신규 구현

| 재사용할 부분 | 보완·새 구현 | 유지할 경계 |
|---|---|---|
| 2.6 원본/hash/locator·2.14 불변 관측/검토·CAS/재가져오기 원칙 | Mímir 해석 스냅샷(SourceBundle·profile·native 구조·참조·claim·미해석) 수신·pin 재검증과 Týr editor 계약 | 현재 parser/importRef 검증 우회 금지; unknown 필드를 구 schema에 추가하지 않음 |
| source/graph/target/mapping/view/구조/selector·템플릿·가상 preview | endpoint closure·다차원 판정·native→canonical 전환 계획과 근거 | 지원하지 않는 상태·정책을 삭제해 동등 전환으로 표시하지 않음 |
| P5 영향/검토, 다섯 작업 단계·P7 독립 정답 | 쟁점 작업대·이전 판단 유지/재검토·엑셀 정의서/대조표 | 원문/규칙 해석/사람 선언/가상 확인/실제 운영/승인 분리 |
| 기존 SQLite workspace2.0·시나리오·제출·CAS | opt-in 별도 sidecar·불변 snapshot/결정·plan/receipt 복구 | 기존 DB DDL/자동 재작성 없음; DB 간 분산 원자성 주장 금지 |
| Bifrost 데이터/wire 독립 검증·승인·발행 | 새 근거 closure opt-in 계약·독립 gate | 수신 지원 전 새 경로 채택/제출 차단; 기존 계약·서명 경로 유지 |

### A 공통 계약·참조·전환 판정 (현장 자료 없이 착수 가능)

- [x] 설계에서 원본·참조·해석 근거·미해석·전환 판정과 제품 해석기 책임, 합성/실제품 수용 기준을 분리했다. 이 체크는 문서 완료만 의미한다.
- [x] [정준 의미/값 생성·매핑 계약 경계](docs/CANONICAL-SEMANTICS-AND-GENERATION.md)와 PLC·DB·상수·조건식 혼합 템플릿·MG01~MG08의 명세를 추가했다. 문서 완료이며 조건식/업무 적합성 기능·fixture 실행 완료가 아니다.
- [ ] SemanticContextContract/GenerationContract의 신규 editor 계약과 기존 semantic/source/graph/mapping/record/template 대응·pin·검증 분리. 업무 문맥·코드 사전·유효성/기간/수량 범주와 입력/생성 정책을 분리하고 기존 schema를 바꾸지 않는다.
- [ ] A1 (Mímir): SourceBundle/InterpretationProfile/Snapshot/NativeNode/ReferenceEdge/Claim/UnresolvedItem의 해석 스냅샷 wire Schema·version/hash/locator·한도. Mímir가 소유하고 Týr는 사본을 번들한다.
- [ ] A2 (Týr): ReviewDecision/EndpointAssessment/ConversionPlan의 새 editor Schema와 스냅샷 수신·pin 재검증(재파싱 없음)·evidenceBasis 소유 위반 거부(SI19). 기존 계약은 수정하지 않는다.
- [ ] native ID/모호한 참조·누락 파일/unknown capture scope·평가 순환/비평가 순환·근거 전이와 endpoint closure 검증.
- [ ] synthetic-pio-like/synthetic-kepware-like 독립 입력·oracle 작성. 해석기 쪽 SI06·SI07·SI10·SI12 결정성·SI17 공격 파일 부분은 Mímir 시험으로 둔다. **실제 제품 export 형식이 아닌 가상 프로파일**로 표시. SI01~SI12·SI16·SI17의 계약/결정성/차단 부분을 검증.

종료 조건: 설정 단독과 이질 가상 구조의 의존 관계를 설명하고, 같은 정의/다른 의미·누락 참조·변환 손실을 분리한다. 원본/미해석 손실0, 미확정 closure의 최종 전환 성공 판정0. fixture 실행 전 통과 수치를 기록하지 않는다.

### B 저장·최종 태그 탐색·쟁점 검토·반환 (A 이후, 현장 자료 불필요)

- [ ] 원본 해석→의미 계약→생성 계약의 근거/판정·고정 버전을 sidecar/화면/대조표에서 별도 조회한다. 이름·타입/단위·가상 수치 일치만으로 의미 적합성을 확정하지 않는다. MG01/MG02/MG07의 저장·반환·호환성을 검증한다.

- [ ] 별도 opt-in sidecar SQLite와 schema 버전·원본 보존·CAS·불변 검토 이력·backup/복구. 기존 DB 열기/저장·시나리오·제출 회귀 검증.
- [ ] 설정 단독/두 자료 대조/개정 비교 진입점, native 계층·생성 과정·원문 locator, 불명 부분과 영향 endpoint·근거 보충/보류 화면.
- [ ] 같은 assessment에서 설정 기반 데이터 정의서·엑셀 대조표·기계 판독 보고서 반환. 비밀 값 제외·원문 근거/판정 pin 일치. 엑셀 의견 재가져오기·vendor 설정 exporter는 후속.
- [ ] 새 snapshot/profile/참조/정책 변경에 대한 판단 유지·재검토·명시적 rename 대응. SI11~SI14·SI16·SI17의 화면/저장/산출물 직접 검증.

종료 조건: 빈 작업본에서 합성 설정만 가져와 최종 태그의 쟁점을 판단·보류하고 정의서를 반환한다. 재개방 후 같은 판단·근거·미해석이 복구되며 변경된 의존 관계를 재검토한다. 이 단계에서는 신규 해석 기반 정준 채택/제출을 잠근다.

### C 제한 전환·가상 동등성·채택 계획 (A/B 이후, 현장 자료 불필요)

- [ ] 혼합 템플릿의 Boolean 조건/우선순위·lazy/eager·predicate/분기 품질·결측, DB 키/설비/작업 범위 대응, 상수 역할의 제한 계약/fixture·독립 검증을 먼저 설계·구현한다. 현재 bounded-selector를 일반 if/else로 취급하지 않는다. 상태 유지·기준 카운터/리셋은 계속 미지원 보존·차단한다.
- [ ] MG01~MG07: PLC 완료 수량/운전·알람 + 가상 DB 작업/제품/불량 수량 + 설비 상수로 MES 문맥 생성. 정상/조건 우선순위/0·1·N/키·NULL/결측/bad·시간/범위/cast·업무 문맥 오류, 의미 유지/변경·불변 템플릿/적용본·미지원 차단을 검증한다. 독립 oracle 명세와 구현 결과를 구분한다.
- [ ] 주소/동등 표현 변경과 총량→양품·작업 범위·상태 코드 우선순위 변경을 분리한다. 의미 변경은 새 URI/계약과 기존 lifecycle·영향 검토, 규칙 변경은 새 생성/템플릿 pin·가상 시험을 요구한다. 구 signature의 기계 검증 범위를 과장하지 않는다.

- [ ] 기존 계약으로 표현 가능한 input/operation/policy의 명시적 변환 규칙과 전환 계획. 다중 주소 객체·low/high·배열·참조 그래프·단위/스케일/cast를 지원 범위 안에서 재사용.
- [ ] 의존 설정 완전성/구조 해석/표현 가능성/가상 시험/의미 확인/승인 상태를 별도로 표시. 수동 예외로 손실·미해결 blocker를 해제하지 않음.
- [ ] 독립 oracle과 단계별 preview·경계값/overflow/결측·정책 차이 검증. 상태/스크립트 등 미지원 동작은 opaque 보존·전환 차단.
- [ ] workspace revision/hash·closure/profile/결정 pin을 가진 dry-run plan, stale 거부·결과 대응/receipt 및 중단 재시도 설계·시험. SI02~SI09·SI12·SI15·SI16 검증.

종료 조건: 합성 범위의 전환 후보와 손실/차단을 재현한다. **D 수신 검증 준비 전까지 새 경로의 채택·제출은 비활성**이다. C의 preview 통과를 제품 동등성 또는 승인으로 표시하지 않는다.

### D Bifrost 근거 closure·명시 채택·회귀 (A~C 이후, 현장 자료 불필요)

- [ ] MG08: 의미 문맥과 생성 계약·전환 대응/근거를 각각 고정하고 독립 수신 검증한다. 구2.19 본문 포획/적용본·구 SQLite/시나리오·기존 제안/승인/발행 회귀를 유지한다. 업무 의미 적합성·가상 시험·서명 승인·실제 운영 확인을 별도로 표시한다.

- [ ] editor와 별도의 opt-in wire/version·출처/결정/전환/정준 후보 근거 manifest·제출 scope 정의. 타 앱 간 공유 코드 없이 독립 구현.
- [ ] Bifrost 참조/무결성·지원 규칙·미해석/손실·기존 타입/의미 검증과 unsupported 거부. 원본 제품 동작의 정답/실시간 일치를 gate PASS로 주장하지 않음.
- [ ] 수신 검증 준비 후 명시 채택 해제: 완전한 정의/필수 원본·근거를 workspace commit에 고정. sidecar receipt 실패는 workspace 결과에서 복구·중복 방지. 기존 importRef로 위장하지 않음.
- [ ] SI14/SI15/SI18, 구 wire/SQLite·기존 제출/서명 승인/불변 발행·재개방 회귀와 OS 격리 검증. 직접 화면의 자료→쟁점→전환→검토/제출 경로 수용.

종료 조건: 새 합성 해석 기반 제안을 독립 검증하고 기존 승인 경계를 유지한다. 제품 자료 없이 가능한 A~D 완료와 실제 PIO/Kepware 지원은 분리해 기록한다.

### E 제품별 실제 해석기 — Mímir 작업 (자료 확보 후, A와 병행 조사 가능)

- [ ] PIO: 제품/driver 버전·허가된 설정/백업·단순/복합 태그·화면 대응·기본값/참조/외부 코드 범위 확보. 정확한 parser/profile·원문 locator·제한을 구현/독립 검증.
- [ ] BEAN TAG MANAGER: 정확한 제품/버전·PIO와의 연결, 공개 TM Core/TM Connector와의 관계를 실제 자료로 확인. 같은 제품으로 추정해 합치지 않음.
- [ ] Kepware: 구체 제품/버전/driver·허가된 프로젝트/export·관련 설정·태그와 공통 정책·누락 범위 확보. 확장자/기본값/상속을 추정하지 않고 parser/profile 구현/독립 검증.
- [ ] 제품·버전·입력 형식·패턴별로 단순 태그와 복합 태그의 전이 의존·해석·전환 판정을 검증하고 지원 매트릭스/미지원 범위를 기록. 가상 형식 PASS를 vendor 지원 완료로 표시하지 않음.

자료가 없으면 E는 미완료로 유지한다. A~D를 막지는 않는다. 제품명 전체에 대한 포괄 지원 완료 조건은 두지 않는다.

### F 현장 PoV (별도 미수행)

- [ ] 실제 담당자가 설비·측정 문맥·의미 정답·운영 설정 확보 범위를 확인.
- [ ] 원본/설정 추적과 쟁점 검토의 작성·검토 총시간, 오경고 확인 비용, 미해석 비율/분모, 재가져오기 재작업·인수인계 결과 측정.
- [ ] 기존 방식과 합의된 기준으로 평가하고 제품/현장별 제한·보류 조건을 기록. 합성 UI 수용으로 현장 채택 효과를 인증하지 않음.

일정은 실제 제품 파일 난도와 A 계약 검토 후 별도 산정한다. 기존 초기 27~36인일 추정을 새 범위에 재사용하지 않는다. 모든 단계에서 실제 장치 통신·외부 SQL·쓰기 실행·vendor 코드 실행·운영 설정 수정/생성·배포·활성화는 제외한다.
