# 공통 입력·레코드 배열 오프라인 수용 결과

2026-10-18. 실제 현장 자료·장치·외부 DB/SQL·쓰기·운영 활성화는 사용하지 않았다.

## 실측 결과

- Python·fixture 고유 **1,195/1,195**. 전체18묶음은 신규29건을 포함해1,194건 통과했고, 최종 신규30건으로 교체해 합산했다. P7의 Ran544는 fixture701에 포함되므로 별도 중복 계산하지 않았다. 기존 경로1,165 + 최종 신규30이다.
- 독립 Java 고유 **237/237**. Publication133 + Logical3 + CrossGraph18 + Broadcast18 + MixedObjects17 + RecordMappings15 + Lifecycle18 + Templates13 + Gate2. 최초16건을 최종18건으로 교체하고 두 Maven 실행의 겹치는 클래스는 한 번만 계산했다. Publication133을 먼저 실행한 뒤 공통 핀 이력 방어를 보강하고 관련104건/최종JAR를 재검증했다. 새 방어는 실제 registry 승인 거부를 포함한18건으로 확인했다.
- 최종 network-none 브라우저·HTTP·SQLite·실제 Java 승인·발행 **36/36**. 별도의 중간 BrowserOnly 검증은 이 수에 합산하지 않는다.
- 기존 계약·fixture·evaluation·editor **858개 파일 SHA 보존**, 현재 Týr 계약 **96개**와 Bifrost resource/JAR bytes 동일, mapping 클래스21개 compiled/JAR bytes 동일.
- 최종 JAR SHA256: `1811e443b1f6993d94a3e2f536f08648124ce7f0229cc2cc0cd54ac3ee16ea0d`.

## 확인한 동작

2개의 DB 행에서 target90/95와 공통 actual120/baseline100/external101/line_codeLINE-A 객체 배열을 만들었다. 입력 순서가 바뀌어도 키 정렬과 정체성이 유지되고, 원본 미정의 열과 입력행 번호를 보존한다. DB 필드/공통 슬롯의 그래프 조합, NULL/default, Double cast 손실, 0건, 중복/잘못된 키, 타입/필수 필드, 최대 건수, 공통 결측/디코딩/변환·bad/uncertain·freshness/skew·미래 시각을 확인했다. reject-all은 전체 차단하고 omit-invalid는 실패 키와 오류를 남기며 uncertain 배열을 반환한다. 공통 입력 오류는 omit-invalid로 숨길 수 없다.

22 화면의 속성별 작성·정의 비교·변경 시 재검증·원자 저장, 공통 입력창 공유, 레코드 표 편집과 원본 열 보존, HEX/원시 값 직접 입력, cast 손실, 재개방/시나리오 복원/CAS/stale, 템플릿 고정 재사용/새 매핑 버전, 기존20 화면/19 사용처,13 제출 closure를 실제 Chromium으로 확인했다. 원본 legacy SQLite를 복사해 조회 전후 dump가 같음을 확인했다.

Docker `--network none`·localhost DNS·cap-drop ALL·no-new-privileges·읽기 전용 입력 archive를 사용했다. 브라우저의 모든 요청이 해당 localhost origin으로 제한됐으며 JS 오류가 없었다. Python preview의 socket/SQLite IO 금지도 별도 mock으로 확인했다. Java는 독립 구현으로 같은 정준 projection/소스 핀/슬롯/이력/URI를 확인했다. 실제 두 Ed25519 키로 승인·불변 릴리스·상태 갱신까지 수행하고 private key가 결과물에 없음을 확인했다. 가상 행/공통 샘플/시나리오/쓰기 정의를 제출에서 제외했다.

## 재현 자료

- 전체 Python: `build/broadcast/20261018-145918-3f43275b` (18묶음, 최종 신규 테스트는 아래30건으로 대체).
- 최종 신규 Python30: `build/broadcast/20261018-150431-ff1b60f2`.
- 최종 통합36: `build/broadcast/20261018-151048-5897d908` (`broadcast-results.json`, screenshot, SQLite, registry, submission).
- Java: `build/broadcast-java-final.log`, `build/broadcast-java-focus.log`, `build/broadcast/java-reports`의 XML.
- 집계·무결성: `build/broadcast/final-summary.json`, `integrity.json`; 이전 파일 pin은 이 문서 옆 `broadcast-baseline-pins.json`.
- `scripts/broadcast/run.ps1 -PythonOnly`, `-BroadcastOnly`, `-UiOnly`로 전체/신규/통합 검증. BrowserOnly는 Java 발행을 제외한 개발 확인 모드이며 최종 통합의 대체가 아니다.

## 로컬 시연

`http://127.0.0.1:59790/` → **22 공통 입력·레코드 배열** → `broadcast-current` 시나리오 선택 → 미리보기. workspace revision4, operator-broadcast1.0.1, 최신 선언에 맞춰 가상 입력을 다시 검증·저장했다.13의 broadcast-offline은 published이다. 검증 자료를 별도 build/broadcast-ui로 복사했으며 기존 시연/DB를 변경하지 않았다. Linux에서 생성된 SQLite의 제출 부속 경로를 Windows의 editor.submissions로 옮긴 뒤 실제 HTTP preview와 Bifrost 상태 갱신을 다시 확인했다 (`build/broadcast/demo-http.json`).

## 별도 PoV / 제한

가상 시각 검사는 실제 원자적 취득 보증이 아니다. 실제 키·단위·스케일·NULL·조회/PLC 시간 정합성, 실패 행을 제외할 업무상 권한, 소비자 계약, vendor/provider export, 작업자 작성/검토 편의는 현장 PoV로 남긴다. 공통 view/배열 자동 적응·설비 간 결합·운영 커넥터·SQL/쓰기/활성화는 이번 구현에서 제외한다.2.22는 개별 temporalPolicy를 포함하지 않은 고정 템플릿에 배열 프레임 정책을 적용한다. 구 템플릿/2.20/2.21의 기존 동작은 유지한다.
