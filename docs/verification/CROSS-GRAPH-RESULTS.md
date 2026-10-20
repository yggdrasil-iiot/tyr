# P3-F C 그래프 간 scalar 결과 재사용 수용 결과

2026-10-18. 동일 설비의 그래프 결과를 ID·정의 버전·노드로 참조하는 bounded 2.17.0 확장을 수용했다. 실제 현장 PoV는 미수행이다.

| 구분 | 실측 |
|---|---:|
| 신규 Python 검사 | 28 / 28 |
| 기존 Python·fixture 회귀 | 1,028 / 1,028 |
| Python·fixture 합계 | 1,056 / 1,056 |
| 신규 독립 Java 검사 | 18 / 18 |
| 기존 매핑 관련 Java 검사 | 138 / 138 |
| Java 합계 | 156 / 156 |
| 격리 브라우저·HTTP·SQLite·실제 Java CLI 연계 | 58 / 58 |

UI 최종 실행에서 반복한 집중 Python 28개와 테스트 묶음 exit marker는 합계에 중복 계산하지 않았다. Java는 초기 실행에서 기존 MappingPublication 133개가 통과했고, 음성 fixture 수정 후 신규 18 + LogicalStructure 3 + MappingGate 2를 별도 재검증했다. 최초 새 검사 1건의 실패를 숨기거나 초기 reactor 실패를 성공으로 계산하지 않는다. [실측 집계](cross-graph-summary.json)와 [Java 집계](cross-graph-java-summary.json)를 따른다.

## 구현·검증한 내용

기존 source/node input에 새 graph endpoint를 추가했다. consumer를 producer보다 먼저 선언해도 독립 dependency 순서로 검증한다. 같은 설비의 scalar만 허용하고 정확한 graph ID/version/node를 고정한다. proposal 안에서만 참조를 해석하며 manifest SHA가 정의 바이트를 동결한다. source/graph 정의를 복제·평탄화하거나 registry 최신 정의로 자동 교체하지 않는다.

네 PLC 합성 fixture는 actual150/target50/gain2에서 shared 차압100, consumer sum200/scaled200/quotient50/ratio1, final wrapper50을 독립 정답으로 검사했다. 같은 결과의 diamond 참조는 producer 계산 한 번과 reference trace 두 번이다. 서로 다른 그래프의 같은 node ID를 구분한다.

자기·두·세 그래프 순환, local node cycle, 없는 graph/version/node, 다른 설비, 타입/단위·재귀 근거 누락, 배열 전체 결과, 구 schema로 새 endpoint 제출을 거부했다. 외부 의존성이 있는 집합의 graph 깊이32/node 경로128/총8192 node 한계를 Python/Java가 각각 검증한다. graph selector의 외부 후보는 모든 정의를 정적으로 검증하고 선택 경로만 계산한다. 선택되지 않은 0 분모 경로를 실행하지 않으며 외부 producer의 계산 변경은 lineage fingerprint에 반영된다.

05 입력 선택·저장·reload와 UI 순환 경로 표시, 조작된 HTTP 참조 거부, 06 재귀 근거 자동 수집·저장, 09 원본 입력/producer/consumer/reference trace와 53 kPa 결과, 기존 Decimal/cast 손실·revision409, 기존 검토·카탈로그·P7 경로를 확인했다. SQLite에는 참조를 그대로 JSON으로 저장하고 새 migration/table을 추가하지 않는다. 참조 그래프 제거/버전 변경/순환 저장은 기존 revision을 보존하며 preview는 읽기 전용이다. 기존 change-review 재귀 해시가 upstream 변경을 탐지한다.

새 JAR는 외부 그래프/말단 source/artifact를 포함한 패키지를 독립 검증하고 두 등록 키 승인·불변 파일 발행했다. 순환·없는 버전과 잘못된 출력 단위를 조작하고 manifest/submission SHA까지 다시 만든 패키지도 거부했다. 구 JAR는 2.17을 모르면 schema capability 오류로 거부했다. 실제 장치·외부 SQL·쓰기 실행·runtime 활성화는 수행하지 않았다.

## 호환성과 실행 범위

기존 canonical 파일75(스키마74 포함)·fixture519·평가 계약1·수식 recipe 계약2개의 SHA를 보존했다. 현재 Python/Java의 schema 사본76개는 동일하다. workspaceVersion2.0·기존 SQLite 테이블/CAS·구 compiler/recipe를 유지한다. Bifrost는 기존 MappingBundle과 새 독립 GraphDependencies를 보완하고 2.17 schema·별도 Java 테스트와 wire fixture를 추가했다. Týr 코드를 Java에 공유하거나 가져오지 않는다.

전체 Python 회귀는 `build/cross-graph/20261018-103922`, 최종 UI/새 JAR 연계는 `build/cross-graph/20261018-104900`에서 실행했다. Python 회귀의 기존 CLI 경로는 이전 JAR로 기존 wire 호환을 확인하고, 신규 receiver의 기존 호환은 위 Java138개, 새 계약은 Java18개와 최종 새 JAR UI 연계로 검증했다. 이를 한 JAR/한 실행의 결과처럼 합치지 않는다.

두 실행 사이 변경은 frontend 안내 문구와 UI 전용 하네스의 실행 범위 표기뿐이다. 전체 Python 실행 archive를 바이트 단위 문자열 치환으로 대조했고 Python 계산/저장 코드·계약·fixture는 동일하다. 최종 UI 실행의 전체 현재 입력 SHA와 새 JAR SHA는 현재 파일에 일치한다. [입력 대조](cross-graph-run-input-audit.json)를 참조한다.

기존 로컬 이미지, network none, DNS localhost, cap-drop ALL, no-new-privileges, 읽기 전용 입력 archive로 OS network namespace를 격리했다. browser page error·외부 요청이 없었다. Windows 호스트 전체 방화벽 검증으로 확대 해석하지 않는다.

- [Python 전체 원시 결과](cross-graph-full-python.json), [최종 UI/CLI 결과](cross-graph-ui-acceptance.json), [입력·JAR pin](cross-graph-validation-pins.json)
- [신규 Python 로그](cross-graph-python-tests.log), [기본701 수용](cross-graph-baseline.json), [A07](cross-graph-a07.json)
- [Java 최초 로그](cross-graph-java-initial.log), [Java 최종 집중 검사](cross-graph-java-final.log), [JAR 빌드](cross-graph-java-package.log)
- [기존 호환성](cross-graph-compatibility.json), [이전 파일 SHA](cross-graph-baseline-pins.json), [실행 이력](cross-graph-run-history.json)
- [UI 격리 설정](cross-graph-ui-docker-inspect.json), [실행 인자](cross-graph-ui-docker-arguments.json), [Python 격리](cross-graph-python-docker-inspect.json), [이미지](cross-graph-image-inspect.json), [결과 요약 화면](cross-graph-preview.png), [참조 단계 화면](cross-graph-reference.png), [시각 QA 기록](cross-graph-visual-qa.json)

최초 Java 음성 fixture의 FixedArray 선언이 subtract의 Decimal schema에 먼저 거부되어 기대한 scalar-boundary 진단에 도달하지 못했다. identity 형식의 유효한 선언으로 수정해 의도한 graph.reference-scalar-required 거부를 재검증했다. schema ID 고유성/사본 일치 검사를 추가했다. 사전 UI 실행과 최종 실행은 별도 보존했다.

별도 시연 [localhost:59785](http://127.0.0.1:59785/)의 05/06/09 화면에서 네 PLC의 shared→consumer→final 경로를 확인할 수 있다. DB는 `build/cross-graph-ui/editor.sqlite3` revision2이며 기존 사용자/시연 DB·registry를 변경하지 않았다. 시연 registry는 합성 공개 키·서명 이력만 보존하며 개인 키를 복사하지 않았다.

## 남은 범위

현장 의미/계수/단위/허용 오차·운전모드·검토 시간·재사용성, 실제 vendor export/native 배치 검증은 PoV로 남긴다. 설비 간 템플릿 재사용·동적 그래프/주소식·배열 전체/native bulk 결과·일반 차원 분석/온도 delta는 미완료다. 캐시는 한 preview 안에서만 사용하며 실제 시계 동기화·원자 snapshot·운영 활성화를 보장하지 않는다. 장치 통신·외부 SQL·쓰기 실행은 계속 제외한다.

최종 저장본 복사본을 같은 network-none 이미지에서 다시 열어 값53·참조2단계·읽기 전용을 확인하고 결과 요약과 참조 카드 위치를 캡처했다. 현재 product 입력 SHA는 최종 UI 실행과 일치하며 이 시각 QA를 테스트 합계에 추가하지 않았다.
