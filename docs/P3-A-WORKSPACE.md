# P3-A 객체·그래프 작성과 SQLite 이전

같은 설비의 여러 객체와 값 그래프를 화면에서 작성·편집·저장·조회한다. 실제 장치 통신은 제외한다. 파일 계약은 [P3-A-CONTRACT.md](P3-A-CONTRACT.md)의 2.0을 사용한다.

## 사용 순서

1. 기존 DB를 열면 08 기존 데이터 이전에서 각 기존 mapping-set에 안정된 객체 ID를 지정한다. 화면의 제안 ID를 확인·수정하고 ‘백업하고 2.0으로 이전’을 누른다. 빈 작성본도 이 경로로 2.0을 시작한다.
2. 01~03에서 기존처럼 설비·논리 연결·접근 정의·의미 모델을 작성한다.
3. 04 객체 인스턴스에서 서로 다른 ID로 Motor A/B 등을 등록한다. 소속 설비·의미 모델은 같아도 된다. 표시 이름을 편집해도 ID는 유지한다.
4. 05 값 그래프에서 소속 설비와 그래프 ID를 지정하고 low/high 소스 또는 노드 입력을 선택한다. decode-u32-words와 identity를 지원한다. 노드 추가·제거·연산/입력/타입/단위 편집이 가능하다.
5. 06 객체 매핑에서 대상 객체를 고르고 프로퍼티마다 직접 소스 또는 특정 그래프 노드 결과를 연결한다. 기존 linear/cast/unit-convert/enum/bit 변환을 재사용한다.
6. 07 메모리맵 비교에서 설비·모델·검색 조건으로 조회한다. 객체 ID, 그래프 입력의 low/high 주소, 단위·스케일, 동의어·동명이의어를 확인한다.

예제: motor-a의 D1000(low)/D2000(high), motor-b의 D1100(low)/D2100(high)를 각각 독립 그래프로 저장하고 cycle-count에 연결한다. 값 조합의 독립 oracle은 기존 131073/262147을 사용한다. 화면은 선언 작성과 조회이며 실제 값을 읽거나 일반 preview를 실행하지 않는다.

## SQLite와 마이그레이션

기존 workspace 테이블의 body JSON에 workspaceVersion 2.0.0과 targets/graphs 컬렉션을 추가한다. 연결·소스·의미·수동 근거는 그대로 보존한다. mappings만 targetInstanceRef/valueRef/memberPath의 2.0 형식으로 전환한다.

POST /api/migrate는 revision과 모든 legacy mapping-set의 객체 ID assignments를 받는다. 중복/잘못된 ID·누락·오래된 revision·이미 이전된 작성본은 거부한다. 일반 PUT으로 버전을 우회 변경하거나 2.0을 1.x로 덮어쓰는 것은 차단한다.

이전은 SQLite BEGIN IMMEDIATE로 작성 경쟁을 막고, 커밋된 이전 전 DB를 SQLite backup API로 복사한 다음 workspace 및 migrations 이력을 한 트랜잭션에서 저장한다. 백업 실패 시 이전을 커밋하지 않는다. 백업은 <DB 파일명>.backups/revision-<기존 revision>-<고유 ID>.sqlite3에 남긴다. 이력에는 이전 revision·백업 경로·객체 ID assignments·시점을 저장한다. 08 화면과 GET /api/workspace에서 재조회할 수 있다.

이전 시 기존 객체를 자동 추정하지 않는다. 화면이 mapping-set별 제안 ID를 보여주고 실제 배정은 이전 요청으로 명시한다. 하나의 기존 mapping-set은 하나의 새 객체로 이전한다. 기존 정의에 숨겨진 복수 객체를 자동 분리하는 importer는 아직 없다.

복구가 필요하면 작성기를 종료하고 백업을 별도 복구 DB 파일로 복사한 뒤 --db로 연다. 새 2.0 DB와 백업 원본은 보존한다. 자동 덮어쓰기/백업 삭제/현장 적용 기능은 없다.

## 저장 검증과 초안

스키마·참조 버전·설비 문맥·그래프 순환·노드 중복·입력 타입/단위·대상 중복·근거 누락은 저장 시 거부하고 기존 revision/body를 유지한다. 객체를 등록했지만 일부 프로퍼티를 아직 매핑하지 않은 경우는 초안으로 저장하고 mapping.incomplete-object를 표시한다. 의미 제약·결과 타입/단위 변경에 따른 진단도 남긴다. 진단을 해결해도 Bifrost 승인 상태는 아니다.

기존 raw 단위 unknown은 보존하며 설명이 있는 경고를 표시한다. 바이트 해석·최종 cast의 값별 overflow·시간/품질·원자성은 P3-B/P3-D의 후속이다. native 구조/배열·일반 파생식은 아직 지원하지 않는다.

## 실행과 검증

```text
python backend/server.py --port 59772 --db build/p3a-ui/editor.sqlite3
python scripts/test_p3a_workspace.py --report docs/verification/p3a-workspace-validation.json
```

현재 브라우저 예제는 기존 build/p2/realistic.sqlite3의 독립 복사본에서 이전했다. 원본 DB는 유지한다. 예제 DB에는 기존 32개 신호와 두 모터용 가상 소스 6개, 객체 6개, 그래프 2개, 매핑 6개가 있다. 실제 설비 메모리 배치를 복원한 자료가 아니다.

[검증 결과](verification/P3-A-WORKSPACE-RESULTS.md).
