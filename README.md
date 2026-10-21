# Týr

PLC별 접근 정의와 상위 의미의 매핑을 작성·검토하는 Yggdrasil 모델링 작업대.

P0~P6의 제한된 작성·저장·미리보기·Bifrost 파일 승인/발행과 P7 오프라인 수용을 구현·검증했다. 현재 A01~A16은 기존 지원 범위에서 16개 충족이다. 실제 현장 PoV·장치 통신·외부 SQL·쓰기 실행·운영 활성화는 제외한다.

- [설계서](DESIGN.md): 요구사항, 역할, 데이터 계약, 화면, MVP 범위와 수용 시험.
- [MVP 구현 계획](MVP-PLAN.md): 기존 기능 활용, 새 구현, 단계별 산출물·종료 조건·시험.

## 문서 기준

DESIGN.md는 2026년 10월 17일 초기 설계 스냅샷을 가져온 뒤 P0·P1 범위와 후속 설계를 반영했다. MVP-PLAN.md는 이 로컬 설계서를 기준으로 작성하고 구현 결과와 후속 계획을 누적 기록한다. 이후 구현 검토에서는 이 폴더의 로컬 문서와 변경 이력을 기준으로 한다.

## 역할

Týr는 작성·검토, Mímir는 후보 도출과 vendor 설정 원본 해석(원본을 읽는 유일한 곳, 계획 단계), Bifrost는 검증·승인·기록, Muninn은 승인된 계약의 실행을 담당한다. 앱들은 데이터·파일 계약으로만 결합하며 공유 코드를 만들지 않는다.

## 저장소 포함 범위

코드·계약·재현용 합성 fixture·설계/사용 문서와 Markdown 검증 기록을 버전 관리한다. build/ 산출물, 로컬 SQLite와 백업/제출 폴더, 의존성, 개인 키·환경 설정, docs/verification의 원시 로그/캡처/테스트 결과는 로컬에 보존하고 커밋에서 제외한다. 문서가 참조하는 원시 검증 파일은 해당 로컬 실행 환경에서만 존재할 수 있다.

기존 fixture와 참조 무결성의 SHA-256을 보존하기 위해 Git의 줄바꿈 자동 변환을 사용하지 않는다. 줄바꿈 정규화가 필요하면 관련 해시/manifest 재생성과 별도 검증을 동반한다.

## P0와 P1

- [결정 기록](docs/P0-DECISIONS.md)
- [데이터 계약](contracts/README.md)
- [검증 fixture](fixtures/README.md)
- [실행 결과](docs/verification/P1-RESULTS.md)

검증: python scripts/validate_contracts.py --deny-network

P0·P1은 가상 문서·설정으로 정준 의미의 수렴·구분·수치/투영 손실·의미 변경을 검증한다. [검증 기준](docs/P1-GOVERNANCE-CRITERIA.md)을 따른다. 실제 장치 통신은 완료 조건에서 제외하며 실제 원본의 대표성은 P4/P7에서 확장한다.


## 로컬 작성 화면

Týr 폴더에서 python backend/server.py를 실행하고 출력된 로컬 주소를 연다. 기본 데이터는 build/p2/workspace.sqlite3에 저장한다. [P2 실행·사용 방법](docs/P2-AUTHORING.md)과 [검증 결과](docs/verification/P2-RESULTS.md)를 참조한다.

## 객체 매핑과 확장 메모리맵

현재 화면은 다중 프로퍼티 객체와 주소별 매핑을 지원한다. 05 메모리맵 비교에서 네 PLC의 32개 신호, 같은 의미의 다른 이름·같은 이름의 다른 의미, 단위·스케일을 확인한다.

[객체 모델·샘플 주소표](docs/OBJECT-MAPPING.md) · [최신 확장 검증 결과](docs/verification/P2-EXPANDED-RESULTS.md)

확장 샘플 실행: python backend/server.py --db build/p2/realistic.sqlite3

## 매핑 패턴 지원 검토

[지원 매트릭스](docs/MAPPING-SUPPORT-MATRIX.md) · [56개 fixture](fixtures/mapping-patterns/README.md) · [검증 결과](docs/verification/MAPPING-PATTERNS-RESULTS.md). 현재 지원·알려진 공백·후속 계획을 분리하며 실제 장치 통신은 제외한다.

## P3-A 파일 계약

[객체 인스턴스·다중 입력 계약](docs/P3-A-CONTRACT.md) · [fixture](fixtures/p3a/README.md). 2.0 작성 계약·CLI 검증과 객체/그래프 화면·SQLite 이전을 지원한다.

## P3-A 객체·그래프 작성기

[화면·SQLite 이전 안내](docs/P3-A-WORKSPACE.md). 객체 인스턴스·low/high 그래프·노드 참조·프로퍼티 매핑을 작성하고 조회한다. 기존 DB는 08 이전 화면에서 백업 후 명시적으로 이전한다. 실제 장치 통신은 없다.

## P3-B 가상 바이트 미리보기

[사용·계약](docs/P3-B-PREVIEW.md) · [fixture](fixtures/p3b/README.md). 09 화면에서 디코딩·low/high·단위/스케일·최종 cast와 오류/손실을 확인한다. 가상 입력과 결과는 DB에 저장하지 않으며 실제 장치 통신은 없다.

## P3-C 다중 입력 파생값

[계약·화면 사용법](docs/P3-C-DERIVED.md), [검증 결과](docs/verification/P3-C-RESULTS.md). 입력별 스케일·압력 단위 변환 후 차압을 작성·저장·조회하고, 가상 입력으로 결측/타입/단위/정밀도·최종 cast 오류를 확인한다. 기존 SQLite 작성본과 스키마를 유지한다. 실제 장치 통신은 제외한다.

## P3-D 가상 시간·품질

[계약·사용법](docs/P3-D-TIME-QUALITY.md), [검증 결과](docs/verification/P3-D-RESULTS.md). 매핑의 freshness/skew·uncertain·조립 정책과 입력별 가상 시각/품질/sequence를 작성한다. 09에서 시간·품질→기존 수치 처리 단계를 확인하고 입력/기준을 별도 SQLite 시나리오로 명시적으로 저장·불러온다. preview는 DB에 쓰지 않으며 실제 장치 통신은 제외한다.

## P3-E 고정 배열

[계약·화면 사용](docs/P3-E-FIXED-ARRAYS.md), [검증 결과](docs/verification/P3-E-RESULTS.md). shape·stride·범위와 고정 indices로 배열 요소를 scalar 의미에 매핑한다. DB/MELSEC bytes와 AB/OPC UA Typed slots의 인덱스·주소·디코딩을 미리보고 범위 초과를 차단한다. 현재 화면 DB는 기존 revision20 복제본 build/p3e-ui/editor.sqlite3이다. 원래 build/p3a-ui/editor.sqlite3은 보존했다. 실제 장치 통신은 제외한다.

## P3-F bounded selector

유한 후보와 현재/이전 인덱스·기본 후보 정책을 작성·저장하고 출처 변경을 가상 검증한다. [설계](docs/P3-F-BOUNDED-SELECTOR.md) · [fixture](fixtures/p3f/README.md). 실제 장치 통신 제외.

## P4-A 파일 가져오기

10 파일 가져오기에서 XLSX/tyr-config-v1 JSON을 해석하고 선택 초안·원본·미해석 관측을 SQLite에 보존한다. template/alias 경로와 원본 hash/locator를 조회한다. [설계·한도](docs/P4-A-FILE-IMPORT.md) · [fixture](fixtures/p4a/README.md). 실제 벤더 exporter와 장치 통신은 제외한다.

## P4-B 혼합 소스·방향 정의

02에서 상수/솔루션 태그/외부 값을 선언하고 기존 객체·읽기 graph/mapping에 연결한다. 11에서 읽기와 독립인 쓰기 방향 정의를 저장·검증한다. SQL 원문 보존과 가상 입력만 지원하며 장치·SQL·쓰기 실행은 제외한다. [설계](docs/P4-B-MIXED-SOURCES.md) · [fixture](fixtures/p4b/README.md).


## P5 변경 비교와 검토

불변 기준본·변경 분류·전이 의존 해시·담당자 검토 이력을 추가했다. 기존 계약/작성본은 유지하고 2.8.0 review-baseline/change-assessment/change-review는 별도 로컬 audit 계약이다. Bifrost 승인·장치 통신·SQL·쓰기 실행은 제외한다. [P5 설계](docs/P5-CHANGE-REVIEW.md), [검증](docs/verification/P5-RESULTS.md).


## P6 오프라인 Bifrost 연계

선택한 매핑/근거를 파일로 고정하고 Bifrost가 독립 수신 검증·두 등록 키의 서명 승인·불변 릴리스 발행을 담당한다. Týr는 승인 권위를 만들지 않는다. 기존 작성본/검토/시나리오는 보존한다. [설계](docs/P6-BIFROST-PUBLICATION.md) · [검증](docs/verification/P6-RESULTS.md). 실제 장치·외부 SQL·쓰기 실행·운영 활성화는 제외한다.


## P7 오프라인 수용

최초 P7 실행에서는 기존 fixture와 화면·복제 SQLite 저장 경로를 검증했고 A01~A16 중 14개 충족, 전체 워드/비트 view A07 및 PC 전체 네트워크 격리 A14는 부분 충족이다. 실제 현장 자료·독립 검토·시간 측정 PoV는 미수행이다. [실행 결과](docs/verification/P7-RESULTS.md) · [재현·PoV 절차](docs/P7-OFFLINE-ACCEPTANCE.md). 장치·외부 SQL·쓰기 실행은 제외한다.


## A07 명시적 source view

14에서 PLC 전체 워드의 alias/bit view를 작성·저장하고 05/06 의미 매핑, 09 원본 가상 입력 preview, 13 Bifrost 승인·파일 릴리스 조회로 연결한다. 기존 계약·SQLite는 보존하며 2.10.0 source view만 추가한다. [설계·한도](docs/A07-SOURCE-VIEWS.md) · [검증](docs/verification/A07-RESULTS.md). A07 실행 시점의 기록은 15개 충족·A14 부분 충족이며, 현재 A14 후속 결과는 아래에 별도로 기록한다. 실제 현장 PoV·장치·외부 SQL·쓰기 실행은 제외한다.


## P7 A14 실제 네트워크 격리 수용

브라우저·Python·Java 전체를 Linux OS network namespace에서 localhost만 가능한 상태로 실행해 작성·저장·미리보기·Bifrost 서명 승인·파일 발행·재조회와 740개 기존 검증을 통과했다. 기존 view 편집 ID 처리 버그를 수정했고 계약·SQLite 스키마는 유지했다. [결과](docs/verification/A14-RESULTS.md) · [설계·재현](docs/A14-NETWORK-ISOLATION.md). 호스트 Windows 전체 방화벽과 실제 현장 PoV는 별도 미수행이다.


## P3-C B 제한 sqrt·clamp

05 값 그래프에서 무차원 sqrt(34자리 half-even)와 같은 단위 clamp를 작성·저장하고 09에서 디코딩→파생→cast의 값과 근사·clipping 손실을 확인한다. 새 graph 계약만 2.11.0으로 추가하며 기존 계약·workspace·SQLite는 유지한다. Bifrost는 독립 검증·서명 승인·파일 발행을 지원한다. [설계](docs/P3-C-BOUNDED-MATH.md) · [가상 fixture](fixtures/p3cb/README.md) · [검증](docs/verification/P3-C-B-RESULTS.md). 현장 PoV와 장치 통신·외부 SQL·쓰기 실행은 제외한다.


## P3-E B 논리 구조·구조 배열

15에서 inline 중첩 구조와 고정 구조 배열의 의미 모델을 작성하고, 06에서 각 전체 member/index 경로를 source/graph에 연결한다. 09 개별 preview와 15 객체 조립 preview가 디코딩·변환·cast·오류/손실을 표시한다. 미매핑/bad이면 전체 result와 진단 partialResult를 구분한다. 기존 계약·SQLite는 유지하고 2.12 semantic/mapping/common만 추가한다. [설계](docs/P3-E-LOGICAL-STRUCTURES.md) · [fixture](fixtures/p3eb/README.md) · [결과](docs/verification/P3-E-B-RESULTS.md). vendor native 배치·현장 PoV·장치/외부 SQL/쓰기 실행은 별도다.


## 의미 URI 개정·폐기

18 화면에서 URI별 설명 개정·사용 중단 권고·폐기 이력과 읽기/쓰기 매핑 영향을 확인한다. 기존 URI signature는 고정하며 의미 변경은 새 URI와 명시적 대체 관계로 관리한다. 로컬 SQLite 초안과 Bifrost 서명 승인·발행을 구분한다. 매핑 없이 관리 이력만 제출할 수도 있다. [설계·계약·경계](docs/P6-SEMANTIC-LIFECYCLE.md), [합성 fixture](fixtures/semantic-lifecycle/README.md), [수용 결과](docs/verification/SEMANTIC-LIFECYCLE-RESULTS.md). 장치 통신·외부 SQL·쓰기 실행은 제외한다.


매핑 템플릿과 적용본: [2.19 설계·작업자 UX·계약 경계](docs/P6-MAPPING-TEMPLATES.md). 공통 정의를 고정하고 설비 입력을 연결하며, 명시적 갱신 후 기존 Bifrost 승인·발행 경로를 사용한다.


레코드·결과 집합 객체 매핑: [2.20 계약·필드/키·0/1/N·UX](docs/P4-C-RECORD-MAPPINGS.md). 20 화면에서 가상 결과의 필드를 객체/배열의 의미 프로퍼티로 변환하고, 기존 템플릿·SQLite·Bifrost 승인/발행을 재사용한다. 가상 입력은 별도 시나리오로 저장하며 실제 DB 접속·외부 SQL·쓰기 실행은 제외한다. [합성 fixture](fixtures/record-mappings/README.md) · [수용 결과](docs/verification/RECORD-MAPPINGS-RESULTS.md).


여러 소스의 한 객체 매핑: [2.21 설계·UX](docs/P4-D-MIXED-OBJECTS.md).21에서 PLC·가상 DB 필드·상수·외부 값·그래프를 프로퍼티별로 연결해 템플릿과 함께 저장한다. 같은 record 입력을 공유하고, SQLite 시나리오와 독립 Bifrost 승인/발행을 지원한다. 실제 접속·외부 SQL·쓰기 실행 및 현장 PoV는 제외한다.


공통 입력을 DB 레코드별 객체 배열에 적용하는 opt-in 2.22 설계·정책·UX는 [P4-E](docs/P4-E-RECORD-BROADCAST.md)를 참조한다. 기존2.20/2.21 동작을 유지하고 실행 연결은 제외한다.


현재 작업자 메뉴는 자료 준비 → 객체 선택 → 연결 → 검증 → 검토·제출로 구성한다. 결과 스키마는 독립 저장해 객체 배열에서 바로 사용한다. [작업 흐름과 호환성](docs/OPERATOR-WORKFLOW.md)을 참조한다.
