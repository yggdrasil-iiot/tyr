# P5 구현 및 검증 결과

2026-10-17. P4-B 다음 주 단계인 P5 변경 비교와 담당자 검토를 구현했다. 실제 장치·솔루션 접속, 외부 SQL, 쓰기 실행 및 Bifrost 승인은 제외한다.

## 구현

- stable 문서 ID와 memberId/mappingId/nodeId 기반 변경 비교. 주소·디코딩·변환·단위·의미·표시·근거·원문 변경을 분리한다.
- 설비/연결·객체/의미·소스/그래프·배열 indices·selector 후보·시간 정책·혼합 읽기/쓰기·importRef의 전이 영향을 추적한다.
- 대상 및 의존 정의 해시에 묶인 담당자·시점·사유·근거 기록을 불변 이력으로 저장한다. 변경 시 needs-review, 삭제 시 target-removed. 최신 판단과 이전 기록을 구분한다.
- 12 변경과 검토 화면 및 별도 SQLite 기준본/검토 테이블. 기존 workspace body/schema/revision, import, migration, 시나리오는 자동 재작성하지 않는다.

## 테스트

신규 **72/72**, 기존 회귀 **592/592**, 합계 **664/664** 통과.

[신규 보고서](p5-validation.json)에는 독립 diff oracle 17개와 기존 53개 schema의 바이트 불변성, 실제 P3-D/E/F 유효 fixture의 시간/배열/selector 변경, 스케일·주소·의미·전이 무효화, 기준본/검토 불변성, 위조 근거/해시, 오래된 revision 거부, SQLite 재개방/추가 테이블 이전, 네트워크·외부 SQL 없는 순수 비교, 실행 API 부재를 포함한다.

기존 회귀는 P1 105, P2 24, P3-A 계약 52/작성본 37, P3-B 66, P3-C 41, P3-D 62, P3-E 55, P3-F 38, P4-A 50, P4-B 62다. 각 *-p5-regression.json과 .log에 직접 실행 결과를 보존했다. 기존 회귀 실행 이후 P5 전용 진단의 동일 상수 오탐/미확인 분류를 보완하고 신규 72개를 최종 재실행했다.

A04 주소 변경, A05 동일 타입의 스케일 변경, A07 선언 view/공유 접근 표시, A16 revision/hash 충돌을 평가했다. A07은 기존 게이트의 지원 경계를 유지하는 진단이며 2.x view 또는 주소 부분 overlap 지원을 새로 주장하지 않는다.

## 실제 화면·저장 확인

P4-B 원본 build/p4b-ui/editor.sqlite3 revision 38을 SQLite backup으로 복제한 build/p5-ui/editor.sqlite3를 사용했다.

1. 화면에서 revision 38을 p5-before 불변 기준본으로 저장했다. 작성본 revision은 바뀌지 않았다.
2. 혼합 소스 매핑을 선택해 근거·의존 정의 13개를 확인하고 p5-mixed-before reviewed 기록을 저장했다.
3. 기존 02 소스 화면에서 mixed-plc-pressure의 D1000→D1001 및 근거 note를 저장했다. 작성본 revision 39.
4. 비교 결과 7개 필드 변경, 영향 대상 3개(소스·차압 그래프·매핑)를 확인했다. 기존 확인은 needs-review로 표시됐다.
5. p5-mixed-after needs-review 판단을 새 이력으로 추가했다. 이전 기록은 후속 검토 있음, 새 기록은 최신 검토로 구분됐다.
6. 서버 재시작·페이지 새로고침 후 두 기록과 기준본·비교 결과를 재조회했다. 브라우저 console error는 없었다.

7개 필드에는 주소와 원문/근거/시각 외에도 기존 PLC 소스 편집기의 명시적 2.7 업그레이드(schemaVersion/sourceKind/accessMode)가 포함된다. 이를 숨기지 않고 표시한다. 의미 모델과 읽기·쓰기 정의는 변경하지 않았다.

원본 P4-B workspace와 불변 snapshot이 동일하며, 기존 import 배치 2개·시나리오 4개·migration 기록을 보존했음을 읽기 전용 SQLite 조회로 대조했다. P5 workspace에서는 소스 하나만 변경됐다. 주소 변경 후에도 가상 입력 9600→150, 상수 110, 차압 40 kPa 결과는 유지됐다. 비교·미리보기 전후 DB 내용도 같았다.

상세 근거: [p5-ui-observation.json](p5-ui-observation.json).

![변경 비교](p5-change-preview.png)

![검토 이력 복원](p5-review-history.png)

## 한계와 다음 단계

검토는 로컬 확인자 ID의 선언이며 인증·전자서명·Bifrost 승인·실장치 검증이 아니다. 기준본은 승인 릴리스가 아니다. 의미 모델처럼 자체/전이 근거가 없는 대상은 단독 검토 폼에서 선택하지 않으며, 근거를 가진 해당 매핑/객체의 검토 범위에 포함한다.

표시 이름 변경도 대상 해시가 달라지므로 보수적으로 재검토한다. import 원문·전개 결과를 구분하고 의존성을 추적하지만 재가져오기 merge, 미해석 해소, native/nested 구조, 부분 주소 범위 overlap, 실제 vendor alias 동등성은 후속이다. 기존 미완성·미해석 finding 22개는 유지하며 검토 기록 저장이 이를 해소하거나 승인하지 않는다.

다음 주 단계는 P6 Bifrost 새 계약·릴리스·승인 연계다. [P5 설계](../P5-CHANGE-REVIEW.md), [MVP 계획](../../MVP-PLAN.md).
