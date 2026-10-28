# 의미 URI 개정·폐기 수용 결과

합성 자료 기반 URI lifecycle 구현을 수용했다. 장치 통신·외부 SQL·쓰기 실행·운영 활성화 및 실제 현장 PoV는 수행하지 않았다.

| 검증 | 결과 | 범위 |
| --- | --- | --- |
| Python·fixture | 1,083 고유 검사 통과 | 기존 회귀355 + 수정 후 P7 701 + 신규 lifecycle27 |
| 독립 Java | 174 고유 검사 통과 | 기존156 + 신규18. 최종 lifecycle/CLI20 재검사는 중복 합산하지 않음 |
| URI 연계 | 27 검사 통과 | 불변 driver pin, 브라우저·HTTP·SQLite·실제 두 키 승인·파일 발행. 반복 unit27 제외 |
| 기존 화면 연계 | 58 검사 통과 | 그래프·수식·미리보기·제출·승인·발행·카탈로그·기존 DB. 반복 unit28 제외 |
| 호환성 | 기존 contract77·fixture582·evaluation1·editor2 파일 SHA 유지 | 현재 Schema79개 ID 고유, Tyr (Týr)/Bifrost 사본 및 JAR 내 schema 일치 |
| SQLite | 이전 행·스키마 조회 보존, CAS·재개방·rollback 통과 | workspace2.0 선택 배열, 불변 이벤트 수정/삭제 및 stale revision 거부 |

최종 JAR SHA256: `36fae664449c16544b5060206d5edb3034a62e6b722cc4cba0af07c517d11bbe`. JAR의 MappingRegistry/MappingBundle/SemanticLifecycle class가 현재 compiled class와 일치한다. 신 fixture는 현재 Java 수신기에 수용되고 구 수신기에 거부된다.

## 수용한 행위

설명 개정·사용 중단 권고·종단 폐기, 선행 해시/개정 fork·signature drift·시간·상태 전이·대체 순환/폐기 대체 URI를 검증했다. 읽기/쓰기 및 nested/structure-array 조상 의미의 영향을 구분했다. 폐기 초안의 남은 매핑은 로컬에 보존하되 제출 시 거부한다. URI의 역할·타입·단위·구조를 개정 이벤트로 바꾸지 못한다.

한글 표시 이름·개정 사유를 저장·재조회하고 Python/Java의 선행 canonical hash 및 실제 서명 승인·발행을 확인했다. lifecycle-only 폐기, 이벤트별 release ID/version/SHA, 현재 head/과거 영향과 승인·발행 상태를 확인했다. 승인 뒤 다른 스트림의 폐기와 구 bundle의 lifecycle 생략도 발행 정책을 우회하지 못한다.

## 실행 범위와 수정 기록

최초 Python 전체 실행은 기존355와 당시 신규26을 통과했지만 마지막 P7 standalone CLI의 backend import 경로 의존으로 실패했다. lifecycle core의 canonical hash/시간 helper를 같은 규칙의 scripts 내부 구현으로 분리하고 standalone CLI 회귀를 추가했다. 수정 후 P7 전체701과 신규27이 통과했고 최종 URI 연계에서도 신규27을 반복했다. 최초 실패 실행을 전체 성공으로 표시하지 않는다.

Java 초기 음성 검사는 알 수 없는 offset이 예상보다 앞선 schema 단계에서 거부돼 기대 코드를 수정했다. 다음 쓰기 영향 검사는 다른 쓰기 정의를 비교하던 oracle을 stable ID로 고정했다. 제품 gate는 두 경우 모두 올바르게 거부했다. 전체174 통과 후 새 보고서 순서를 정렬했고 최종20 검사 및 실제 CLI 프로세스 간 동일 report/digest를 확인했다.

화면 사전 실행의 submit 버튼 DOM 조회 오류를 수정했고 저장 후 비동기 조회 완료를 기다리도록 harness를 동기화했다. 병렬 evidence 이름에는 고유 suffix를 추가했다. 최종 driver는 input archive와 같은 불변 사본이며 모든 최종 입력 SHA를 현재 코드와 대조했다. 초기 실패·수정·최종 성공의 원자료는 보존한다.

- 최초 Python: `build/semantic-lifecycle/20261018-112301` — 부분 통과 후 standalone CLI 실패.
- 수정 후 P7/lifecycle: `build/semantic-lifecycle/20261018-114202` — 701 + 27 통과.
- 최종 URI 연계: `build/semantic-lifecycle/20261018-114610-506c62d4` — 27 연계 + 반복27 unit 통과.
- 기존 화면 회귀: `build/cross-graph/20261018-114612` — 58 연계 + 반복28 unit 통과.

Linux Docker network-none·localhost DNS·capability 제거·no-new-privileges·읽기 전용 입력 조건에서 검증했다. Chromium 요청은 모두 해당 localhost origin이었으며 JS 오류가 없었다. 임시 서명 개인 키는 삭제했고 근거·시연에는 공개 키와 서명만 남겼다. 호스트 Windows 전체 방화벽 검증으로 일반화하지 않는다.

[검사 집계](semantic-lifecycle-summary.json) · [범위·입력 감사](semantic-lifecycle-run-audit.json) · [보존](semantic-lifecycle-compatibility.json) · [최종 pin](semantic-lifecycle-validation-pins.json) · [URI 연계](semantic-lifecycle-ui.json) · [기존 화면 회귀](semantic-lifecycle-legacy-ui.json) · [P7](semantic-lifecycle-baseline.json) · [시연 조회·다운로드](semantic-lifecycle-demo.json).

![URI 상태·한글 개정 메타데이터·로컬/과거 릴리스 영향](semantic-lifecycle-history.png)

## 시연과 현장 PoV

`http://127.0.0.1:59786/`의 18 화면에 retired r4 이력, 남은 초안 매핑과 원본 발행 릴리스가 있다. 다른 active URI는 개정 대상으로 선택할 수 있다. 검증 DB의 별도 복사본에서 canonical workspace 행은 보존하고 로컬 submission 경로만 Windows 시연 위치로 옮겼다. 13의 고정 묶음 다운로드도 확인했다.

실제 URI 소유권·권한, 폐기 유예/대체 정책·소비자 inventory·의미/단위 정답·현장 검토 시간 및 vendor native/export 정답은 별도 PoV다. 다른 스트림의 기존 head나 가동 설비를 소급 변경하지 않는다. 운영 IAM·외부 anchor·registry federation·자동 branch rebase·ontology migration은 이번 수용 범위가 아니다.
