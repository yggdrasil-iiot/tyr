# P5 변경 비교와 담당자 검토

## 목적과 권위 경계

불변 비교 기준본과 현재 저장본 사이의 접근·디코딩·변환·의미·근거 변경을 검토한다. 네트워크 조회, 외부 SQL 및 장치/솔루션 읽기·쓰기 실행은 없다. 담당자 검토는 로컬 사용자 ID의 선언이며 인증·전자서명·Bifrost 승인·활성화가 아니다. 승인 상태는 not-requested, 실장치 확인은 not-performed다.

P4-B 다음 주 단계인 P5를 구현한다. P3-E native/nested 구조, 임의 동적 주소식, 실제 vendor export 지원 확대는 별도 후속 범위로 유지한다.

## 재사용과 신규

재사용: 기존 작성본·PLC/혼합 소스·의미·객체·그래프·읽기/쓰기 정의·import 근거, 계약 검증 finding, canonical JSON SHA-256, SQLite transaction/revision, Host/Origin 보호.
신규: change_review.py의 비교·의존 관계·검토 판단, 2.8.0 로컬 audit 계약 3종, 불변 기준본/검토 테이블, 비교/검토 API, 12 변경과 검토 화면, P5 fixture와 검증.

Bifrost/Mimir (Mímir)/Muninn 코드 의존을 추가하지 않는다. 기존 53개 schema를 변경하지 않는다. 작성 workspaceVersion 2.0과 기존 proposal 2.7 등 내보내기 버전은 유지한다. 새 audit 문서를 기존 proposal에 조용히 넣거나 기존 review-record 1.0으로 가장하지 않는다. P6에서 실제 수신 계약을 별도로 연결한다.

## 비교 모델

안정 식별은 문서 종류 + ID다. 표시 이름으로 자동 대응하지 않는다. ID 변경은 삭제/추가로 표시한다. memberId/mappingId/nodeId가 있는 목록은 해당 ID로 비교하고, 순서 변경도 표시한다. 변환 목록·indices 등 순서가 의미 있는 다른 배열은 전체 전후 값을 보존한다.

분류: identity, presentation, access, decode, transform, meaning, constraint, context, reference, graph, evidence, import-evidence, definition. 주소·접근 방향·외부 SQL/상수 정의는 access, codec/원시 타입/배열은 decode, 스케일·cast/시간 정책은 transform, semanticId/role/단위/의미 타입은 meaning이다. 알 수 없는 신규 필드도 definition으로 표시해 누락하지 않는다.

import batch의 원문·template/alias/override/미해석 항목은 import-evidence로 비교하고 source draft 등 해석 결과의 변경은 별도 행으로 비교한다. 원문만 달라진 경우 해석 결과가 바뀌었다고 추정하지 않는다. source.importRef를 통해 원문 batch 변경도 해당 소스와 매핑의 검토에 보수적으로 전파한다. 재가져오기 merge나 미해석 항목의 자동 해소는 수행하지 않는다.

현재 finding을 incomplete와 definition-conflict로 나누고, 선언된 view/공유 접근 및 import derivation을 별도 표시한다. ready 소스의 동일 설비·연결·접근 표현 중복을 검토 대상으로 표시하며, 명시적 view가 있으면 declared-view로 구분한다. 기존 게이트가 지원하지 않는 2.x view나 native 구조를 이 화면에서 허용하지 않는다. 정확히 같은 접근과 bit 차이를 제거한 동일 범위 비교까지만 하며, 부분 주소 범위 overlap과 vendor alias의 실제 동등성 증명은 후속이다.

## 의존 해시와 재검토

대상 row의 canonical JSON SHA-256과 전이 의존 정의의 해시 묶음을 따로 기록한다. 소스의 수동 note/label/capturedAt/importRef도 대상 row에 포함한다. 참조하는 설비/연결, sourceRef/graphRef, 객체→의미, viewOf, 가져오기 batch를 따라간다. 그래프 후보는 모두 정적으로 포함하며 가상 입력에서 선택된 후보만으로 검토 범위를 축소하지 않는다. 누락 참조도 의존 digest에 남긴다. 순환 방문은 유한 집합으로 제한한다.

이는 wire 파일의 바이트 SHA-256과 다른 canonical authoring 대상 해시다. 의미/수치가 같다는 증명이나 장치 상태 해시가 아니다.

검토 기록은 reviewed/needs-review/disputed 중 하나다. 대상 또는 의존 해시가 달라지면 조회 시 needs-review, 대상 삭제 시 target-removed로 표시한다. 원래 기록을 수정하지 않는다. 최신 추가 기록이 현재 판단이며 이전 기록은 superseded로 표시한다. 무관한 소스 추가는 해당 대상 검토를 무효화하지 않는다.

presentation 분류는 의미 변경과 구분하지만 정확한 대상 해시에 묶인 확인은 표시 이름만 바뀌어도 보수적으로 재검토한다. 추후 '표시 변경 확인' 정책을 추가할 수 있다.

## SQLite·API

review_baselines(id, body), change_reviews(seq, id, body) 테이블을 CREATE TABLE IF NOT EXISTS로 추가한다. 기존 workspace body/revision, migration 및 preview_scenarios 행을 자동 재작성하지 않는다. 기준본 최대 20개, 검토 기록 최대 1000개. 삭제/덮어쓰기 API는 없다.

- GET/POST /api/review-baselines: 기준본 목록/현재 저장본의 불변 snapshot.
- POST /api/review-diff: 기준본 ID + 현재 revision 비교. 읽기 전용.
- GET/POST /api/reviews: 대상·해시·현재 판단·이력 조회/검토 추가.

저장은 BEGIN IMMEDIATE 안에서 revision·기준본 해시·작성본 해시·대상 해시·의존 해시를 검증한다. 근거는 해당 대상 의존 범위에 실제 존재하는 evidenceRef만 허용한다. 확인자·시점·사유·근거 필수. 이미 사용된 ID, 오래된 기준 요청, 위조 해시/근거, 승인/실장치 확인 주장과 빈 사유를 거부한다. 기존 local Host/Origin/header/2MiB JSON 요청 경계를 유지한다.

## 화면 사용

12에서 현재 저장본을 기준으로 저장 → 비교 → 근거가 있는 대상 선택 → 확인자/판단/사유 입력 → 검토 기록 저장. 저장하지 않은 편집 내용은 비교하지 않는다. 소스/그래프/매핑을 기존 화면에서 수정한 후 12에서 다시 비교하면 직접 변경과 전이 영향을 볼 수 있다. 비교·검토 저장은 작성본 revision을 변경하지 않는다.

P5 UI 검증은 P4-B revision 38 DB의 복제본 build/p5-ui/editor.sqlite3를 사용한다. 원본은 보존한다. 실제 담당자 인증/승인, Bifrost 제출/릴리스, 운영 배포는 P6 이후다.

독립 fixture: [fixtures/p5](../fixtures/p5/README.md). 검증: [P5-RESULTS.md](verification/P5-RESULTS.md).

검증 완료: 신규 72/72, 기존 회귀 592/592. 화면 저장·주소 변경·needs-review 전이·서버 재시작 복원 및 원본 보존을 [결과 보고서](verification/P5-RESULTS.md)에 기록했다. 자체/전이 근거가 없는 의미 모델은 근거가 있는 매핑/객체 검토에 포함하며 단독 검토 폼에서는 제외한다.
