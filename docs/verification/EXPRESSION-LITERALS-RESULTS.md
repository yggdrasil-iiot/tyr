# P3-C E 숫자·명시적 단위 상수 수용 결과

2026-10-18. 기존 P3-C D의 숫자 값 식 공백을 compiler 1.1로 제한 확장했다. 실제 현장 PoV는 미수행이다.

| 구분 | 최종 실측 |
|---|---:|
| 신규 상수 수식 Python | 23 / 23 |
| 기존 Python·fixture | 1,005 / 1,005 |
| Python·fixture 합계 | 1,028 / 1,028 |
| 격리 브라우저·HTTP·SQLite·실제 Java CLI 연계 | 46 / 46 |

최종 실행에는 실패·스킵이 없다. 전체 report의 58개 항목은 연계 46개와 12개 테스트 묶음 exit marker이며 이를 Python 개수에 중복 합산하지 않는다. 기본 수용 fixture 행 701과 A07 39, 나머지 unittest 실행 수를 [실측 집계](literal-summary.json)에 구분했다.

## 검증 범위

Bare number는 무차원, quantity는 명시적 단위다. 네 PLC synthetic fixture의 actual150/target50에서 `(actual-target)*0.5+quantity(3,"kPa")=53 kPa`를 독립 정답으로 검사했다. 음수/정규화/긴 숫자 원문/중복 literal 재사용, 단위 추측·불일치·코드 문법·구 compiler literal 거부, 분모 0·결측·Decimal 나눗셈과 최종 cast 손실을 확인했다.

17 화면의 버전 선택/원문 위치/상수 값·단위·synthetic 근거 표시, compile 읽기 전용, 원자 source/graph/recipe 저장·재개방, 06 화면의 상수 포함 근거 자동 수집·매핑 저장, 기존 09 단계별 계산과 입력 목록의 상수 제외를 확인했다. 변경된 상수는 새 ID를 만들고 구 소스·이력을 보존한다. 기존 ID의 수동 변경은 stale 및 재컴파일 충돌로 탐지하고 덮어쓰지 않는다. transaction fault 시 소스·graph·recipe 전부 rollback한다. 기존 1.0 API·recipe·SQLite 재개방도 통과했다.

생성 상수와 근거가 포함된 동일 기존 2.7/2.15 wire package를 변경 없는 Bifrost JAR로 검증·두 키 승인·파일 발행했다. 잘못된 출력 단위와 재작성된 manifest SHA도 receiver가 거부했다. Java는 Týr 코드나 수식 원문을 실행하지 않는다. 기존 매핑 관련 Java JUnit 138개는 이번 실행 수에 더하지 않았으며 이번에는 실제 CLI 경로를 재실행했다.

## 호환성과 증거

기존 canonical 파일 75개(스키마 74개 포함), fixture 516개, 평가 계약 1개, local editor 1.0 계약 1개의 SHA가 모두 보존됐다. 기존 Bifrost 관련 pin 85개와 JAR SHA도 동일하다. canonical 계약 변경 없이 local editor recipe 1.1만 추가했다. 기존 SQLite 테이블/행을 재작성하지 않고 기존 expression_recipes에 버전별 payload를 append한다.

최종 실행은 `build/expression-literals/20261018-093301`이다. 현재 product/test/fixture/editor 계약 전체 입력 SHA와 최종 실행 pin을 대조했다. 기존 로컬 이미지에서 network none, localhost DNS, cap-drop ALL, no-new-privileges, 읽기 전용 입력 archive를 사용했다. 브라우저 외부 요청·page error가 없었다. Windows 호스트 전체 방화벽 검증을 대신하지 않는다.

- [최종 연계와 입력 SHA](literal-full-acceptance.json), [집계](literal-summary.json), [현재 source pin](literal-validation-pins.json)
- [신규 검사 로그](literal-python-tests.log), [기본 수용](literal-baseline.json), [A07](literal-a07.json)
- [기존 호환성](literal-compatibility.json), [기존 파일 SHA](literal-baseline-pins.json)
- [격리 설정](literal-docker-inspect.json), [인자](literal-docker-arguments.json), [이미지](literal-image-inspect.json)
- [실행 이력](literal-run-history.json), [화면](literal-preview.png)

첫 UI 사전 검증에서는 테스트가 직접 구성한 매핑에 생성 상수 근거가 없어 mapping.evidence-incomplete로 거부됐다. 이를 우회하지 않고 실제 06 매핑 화면의 근거 자동 수집 경로로 바꾼 후 전체를 재실행했다. 실패한 사전 실행도 별도 보존했다. 초기 Windows sandbox의 임시 디렉터리 권한 실패는 권한을 갖춘 별도 사전 검사로 확인했으며 최종 판정은 위 격리 전체 실행만 사용했다.

별도 시연 [localhost:59784](http://127.0.0.1:59784/)의 17 화면에 네 수식을 저장했다. `build/literal-ui` revision7이며 모든 recipe는 current이다. 기존 사용자/시연 DB·registry는 보존했다. 시연 registry에는 합성 공개 키·서명 이력만 복사했으며 개인 키를 남기지 않았다.

## 별도 미완료 범위

일반 조건/비교/Boolean 식·차원 분석/복합/역단위·온도 delta·cross-graph는 후속이다. 2.7 Double 숫자 문자열을 기존 Decimal preview로 계산하며 native IEEE/PLC 저장 정밀도를 보장하지 않는다. 실제 계수/단위/의미 정답·검토 시간·재사용성·vendor native/export 검증은 현장 PoV로 남긴다. 장치 통신·외부 SQL·쓰기 실행·runtime 활성화는 계속 제외한다.
