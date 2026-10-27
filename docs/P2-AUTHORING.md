# P2 로컬 작성 작업대

상태: 구현·검증 완료. 기준: MVP-PLAN.md의 P2.
실제 장치 통신은 포함하지 않는다.

## 실행

Tyr (Týr) 폴더에서 실행한다.

```powershell
python -m pip install -r requirements-contracts.txt
python backend/server.py
```

의존성이 이미 설치됐다면 설치 명령은 생략한다. 서버가 출력한 http://127.0.0.1:<port> 주소를 브라우저로 연다. 기본 포트는 OS가 자동 배정한다. 고정 주소가 필요하면 --port 59771처럼 지정한다. Windows에서 예약된 포트는 바인딩이 거부될 수 있으므로 --port 0으로 자동 배정할 수 있다.

기본 DB는 build/p2/workspace.sqlite3이다. --db <경로>로 작업 공간을 분리할 수 있다. 서버를 종료한 뒤 SQLite 파일을 복사하면 작성본을 보관할 수 있다. 서버를 다시 실행해 같은 DB를 사용하면 저장본이 복원된다.

## 사용 흐름

1. **설비와 논리 연결**: 설비 ID·이름, 연결 ID·이름·소속 설비·접근 방식을 저장한다.
2. **PLC 접근 정의**: 기존 연결을 선택하고 접근 필드·원시 타입·값 단계·입력 단위·근거를 작성한다.
3. **공통 의미**: 의미 ID URI, 표시 이름, role, 결과 타입·정준 단위·범위·설명을 저장한다. 기존 정의를 이름·URI·설명으로 검색하고 편집할 수 있다.
4. **의미 매핑**: 소스와 기존 의미를 선택한다. 필요하면 linear 계수·오프셋을 지정한다. 명시적 cast의 결과 타입·단위는 선택한 의미를 따르고 반올림 정책을 저장한다.
5. 저장된 항목을 눌러 다시 편집한다. 각 저장 버튼은 화면 데이터 전체를 하나의 트랜잭션으로 저장한다.

ID는 영문 소문자로 시작하고 영문 소문자·숫자·점·밑줄·슬래시·하이픈을 사용한다. 새 폼에서 기존 ID를 입력해 덮어쓰는 동작은 막고 기존 항목을 선택해 편집하도록 안내한다.

네 설비의 모터 속도는 동일한 의미 ID를 재사용할 수 있다. 개념은 같아도 설비 인스턴스는 각각 유지한다. 같은 설비·의미 멤버에 중복 소스를 연결하면 P1의 mapping.duplicate가 표시된다.

## 네 접근 폼

| 프로파일 | 보존하는 접근 정보 | 원시 표현 |
|---|---|---|
| AB Logix symbol | 심볼 경로 | typed와 값 타입 |
| S7-1500 OPC UA | namespace URI, 식별자 종류와 값 | typed와 값 타입 |
| S7-300 DB | DB 번호, byte offset/length, 선택적 bit offset | bytes, 타입, byte/word order |
| MELSEC device | 디바이스 영역, 숫자 인덱스, 원문 진법, word count, 선택적 bit offset | bytes, 타입, byte/word order |

MELSEC의 숫자 인덱스는 10진 정수로 입력하고 원문 진법을 별도로 보존한다. rawAddressText는 원문 표기이며 이를 파싱해 의미나 접근 필드를 추측하지 않는다.

미확인 접근·타입·순서는 null로 저장한다. 초안 저장과 제출 전 검사는 구분한다. draft 소스가 연결된 매핑은 저장할 수 있지만 source.draft / mapping.source-not-ready로 제한을 알린다. 형식에 어긋난 데이터, 없는 연결·설비·소스·의미 버전 참조와 설비 문맥 불일치는 저장하지 않는다.

## 구현과 재사용 결정

- backend/server.py: Python 3.13.5 표준 http.server·sqlite3. 기존 jsonschema 4.26.0 / referencing 의존성은 requirements-contracts.txt를 따른다.
- frontend: HTML/CSS/JavaScript. 런타임 패키지·외부 CDN·번들러가 없다.
- P1 contracts와 scripts/validate_contracts.py를 **Tyr 내부**에서 재사용한다. Bifrost·Mimir (Mímir)·Muninn 코드를 가져오거나 수정하지 않았다.
- P0의 JVM 우선 검토를 거쳐, P2 로컬 작성은 이미 검증한 Python 계약 도구를 직접 재사용하는 방식으로 결정했다. 서버 프레임워크·새 JVM 의존성·패키지 다운로드를 추가하지 않고 핵심 작성·저장 경로를 검증한다. 향후 배포 백엔드 선택은 이 파일 계약과 독립적이다.
- 데이터 저장은 단일 SQLite 행의 전체 workspace JSON과 revision, updated_at이다. 규모를 가정한 서비스 분리·공유 DB는 도입하지 않았다.

## 작성 API와 revision

GET /api/workspace는 revision, workspace, updatedAt, findings를 반환한다.

PUT /api/workspace의 body는 {revision, workspace}이고 Content-Type: application/json 및 X-Tyr-Editor: 1을 사용한다. workspace는 equipment, connections, sources, semantics, mappings 배열로 구성된다. 소스 편집 레코드는 definition, note, origin, capturedAt과 선택적 label(현장 신호명)을 가진다.

SQLite의 조건부 UPDATE는 일치하는 revision에서만 갱신하고 revision을 1 증가시킨다. 오래된 창은 409를 받는다. 화면은 해당 입력을 유지하고 최신 저장본을 다시 열도록 안내한다. 형식·참조 오류는 422이며 DB를 변경하지 않는다. 자동 재시도나 자동 덮어쓰기를 하지 않는다.

소스·의미·매핑은 P1 wire 문서 구조를 사용한다. workspace API는 mutable 작성 상태이며 승인된 불변 release가 아니다. 화면은 기존 문서 version과 멤버 ID를 보존하고 새 문서는 1.0.0으로 시작한다. 저장 revision은 작성본의 동시 편집 토큰이며 문서 version과 별개다. 불변 버전 발행은 P6에서 수행한다.

## 근거와 제출 전 검사

수동 근거 note·origin·capturedAt을 DB에 저장한다. 검증 시 note를 UTF-8 text로 만들고 evidence-artifact와 text-line:1 참조를 생성해 기존 패키지 검증기로 검사한다. 이는 사용자의 수동 선언 근거이며 XLSX/PDF 원본을 가져온 것으로 표시하지 않는다.

findings는 저장 시와 재조회 시 계산한다. 단위·타입·길이·중복 매핑·미확인 값·이중 스케일 등의 P1 규칙을 화면에서 보여준다. 원본 파일이나 Bifrost proposal을 발행하지 않고 임시 패키지로 검증한 뒤 정리한다. 검사가 통과해도 승인 상태로 바꾸지 않는다.

## 범위 경계

P2 확장 화면은 객체당 여러 프로퍼티와 mapping-set당 여러 연결을 지원한다. 각 프로퍼티의 서로 떨어진 주소·원시 타입·해석을 보존한다. 프로퍼티 선택에서 새 프로퍼티를 추가하고 객체 매핑 화면에서 행별로 연결한다. 부분 객체의 누락은 제출 전 확인에 표시한다.

변환 작성은 cast, linear, bit-select, enum-map, unit-convert를 지원한다. 복잡한 전체 파이프라인은 JSON으로 그대로 보존한다. 값 preview는 P3에서 구현한다. source.viewOf 복합 뷰는 이번 화면에서 지원하지 않는다.

최신 샘플·1.1 계약·비교 화면은 [객체 매핑 문서](OBJECT-MAPPING.md)와 [확장 검증 결과](verification/P2-EXPANDED-RESULTS.md)를 따른다.

이 서버는 로컬 단일 사용자 작업대다. 127.0.0.1에만 바인딩하고 같은 origin의 작성 요청만 받는다. 연결 프로파일은 논리 문맥·접근 종류만 저장한다. 장치 주소·자격증명·연결/읽기/쓰기 API가 없다. 화면·스타일·스크립트는 로컬 파일만 읽는다.

삭제·파일 importer·개정 diff 화면·Bifrost 승인·Muninn 실행은 후속 단계다. P2의 기존 정의 편집은 초안 변경이며 승인 이력 관리가 아니다.

## 검증

```powershell
python scripts/test_p2.py --report docs/verification/p2-validation.json
node --check frontend/app.js
python scripts/validate_contracts.py --deny-network
```

[실행 결과](verification/P2-RESULTS.md)를 참조한다.

## P3-A 작성기 확장

현재 화면은 [객체·그래프 및 SQLite 이전 안내](P3-A-WORKSPACE.md)를 따른다. 기존 1.x 작성본은 읽고 저장할 수 있으며 명시적 이전 후 2.0 작성 기능을 사용한다.
