# 작업자 흐름·독립 결과 스키마 검증 기록

2026-10-18. 현장 자료 없이 합성 입력으로 검증했다. 장치 통신·외부 SQL·쓰기 실행·운영 활성화는 제외했다.

## 구현과 경계

자료 준비 → 객체 선택 → 연결 → 검증 → 검토·제출의 다섯 단계 시작 화면과 주 메뉴를 구성했다. 기존23개 도구는 각 단계 하위 메뉴에서 그대로 접근한다. 설비·객체 의미 모델·결과 스키마·템플릿 선택을 연결 화면으로 이어받고, 다음 단계 이동 시 미저장 입력을 보존한다. 검증/검토에서 상세 도구를 열어도 단계 문맥을 유지한다.

자료 준비의 결과 스키마에서 필드·키·타입·단위·NULL 정책을 표로 작성하고 검증·저장한다. 레코드 전용 매핑(기존20)을 만들지 않고 객체 배열 연결(기존22)에 사용할 수 있다. 스키마는 불변 버전·선행 SHA·사용 중인 매핑을 표시하며 새 버전 저장이 기존 매핑을 자동 변경하지 않는다.

선택 workspace.resultSchemas는 기존 SQLite JSON/CAS에 저장한다. 새 테이블·DDL·자동 마이그레이션은 없다. 기존 inline 스키마 선택과 API 형식은 유지한다. 사용한 스키마는 기존 wire2.22 본문에 고정하고 편집 카탈로그 wrapper·미사용 버전·가상 입력은 발행하지 않는다. Bifrost 소스·계약·JAR를 변경하지 않았다. 단일 객체의 기존 recordMappingRef 경로는 유지한다.

## 확인한 결과

- 전체 Python·fixture 고유 **1,208/1,208**. 기존1,195 + 신규13. 마지막 P7 report701에 포함된 unittest544와 P3-A 결과를 별도로 중복 합산하지 않았다. 19개 묶음 모두 통과하고 입력 SHA가 유지됐다.

- 새 작업 흐름 network-none 브라우저·HTTP·SQLite·실제 Java 승인/발행31/31.
- 기존 배열 작성 경로 회귀36/36. 두 경로의 중간 실행은 중복 합산하지 않았다.
- 기존 계약·fixture·evaluation·editor890개 파일 SHA 보존.
- 독립 fixture의 기존 Java validation accepted=true, findings=[]; 승인·발행은 위 두 브라우저 경로에서 실제 두 Ed25519 키로 확인했다. Java 전체 단위 검증은 이번 변경에서 재실행하지 않았다.
- Bifrost JAR SHA256: `1811e443b1f6993d94a3e2f536f08648124ce7f0229cc2cc0cd54ac3ee16ea0d`.

새 흐름은 recordMappings와 mappingTemplates가 모두 빈 상태에서 시작해 독립 스키마 작성·저장·재개방, 설비/모델 선택, 슬롯 연결, 비교·원자 저장, 가상 배열 미리보기, 시나리오 저장, 스키마 개정과 이전 버전 고정, 사용처 조회, 제출·승인·불변 발행을 수행했다. 기존20 compose API를 호출하지 않았다. 브라우저 JS 오류가 없고 모든 요청은 localhost였다. 읽기 전후 legacy SQLite dump가 같으며 사용하지 않은 카탈로그 추가 전후 wire package bytes도 같았다. CAS·plan 변조·불변 이력 수정·동일 버전 충돌·키/타입/필드 오류를 거부했다.

Docker network none·cap-drop ALL·no-new-privileges·읽기 전용 입력 archive를 사용했다. private key는 결과물에 남기지 않았다.

## 재현 자료

- 전체 Python: `build/workflow/20261018-191052-62adaf1b`.
- 최종 새 흐름31: `build/workflow/20261018-191954-f9c13e74`.
- 기존 경로36: `build/broadcast/20261018-191226-1205fc6d`.
- 독립 fixture: `fixtures/workflow`, Java 결과 `build/workflow/fixture-java.json`.
- 최종 집계: `build/workflow/final-summary.json`.
- 무결성: `build/workflow/integrity.json`, 이 문서 옆 `workflow-baseline-pins.json`.
- 재현: `scripts/workflow/run.ps1 -PythonOnly` / `-WorkflowOnly` / `-UiOnly`.

## 로컬 화면

현재 `http://127.0.0.1:59790/` 서버를 새 UI/API로 갱신하고 기존 SQLite revision4는 유지했다. 새 단계 메뉴와 스키마 API를 실제 HTTP로 확인했다 (`build/workflow/current-demo-http.json`).

별도 `http://127.0.0.1:59791/`에는 검증 SQLite/제출 부속 파일/registry를 복사했다. 독립 스키마1.0.0·1.0.1과 이전1.0.0에 고정된 workflow-array1.0.0, published 제출이 있다. 검증 단계 → 레코드 객체 배열 → workflow-current 시나리오로 actual120/target90·95/baseline100/external101/line_codeLINE-A 객체 배열을 확인할 수 있다. Windows 경로 이관 후 실제 HTTP 미리보기와 Bifrost 상태를 확인했다 (`build/workflow/demo-http.json`).

## 별도 현장 PoV

실제 작업자 관찰·작성/검토 시간·잘못된 선택률, 실제 문서/provider export·키/NULL/단위 정답은 미수행 현장 PoV다. 합성 브라우저 검증은 사용성 인증이나 실제 동시 취득 보증이 아니다. 편집 카탈로그 메타데이터의 별도 발행, 운영 커넥터·외부 SQL·장치 쓰기·활성화는 이번 범위에 없다.
