# P3-C D 제한 수식 작성 수용 결과

2026-10-18. 명시적 source ID·사칙연산/괄호·sqrt/clamp/linear 작성 문법을 기존 canonical DAG로 컴파일하는 유한 subset이다. 현장 PoV는 미수행이다.

| 구분 | 최종 실측 |
|---|---:|
| 새 수식 Python 검사 | 30 / 30 |
| 기존 Python·fixture 회귀 | 975 / 975 |
| Python·fixture 합계 | 1,005 / 1,005 |
| OS 격리 브라우저·HTTP·SQLite·실제 Java CLI 연계 | 37 / 37 |

실패·스킵은 없다. 합계는 수식 30 + 카탈로그 15 + 산술 28 + 평가 35 + 복구 13 + import 58 + graph 39 + structure 30 + math 17 + A07 39 + 기본 수용 701이다. 기본 수용의 fixture 행과 unittest 수를 구분해 원시 기록을 남겼다.

## 확인한 기능과 경계

네 접근 profile의 12 소스·4 객체·16 매핑에서 같은 명시적 차압/계수 수식을 컴파일하고 independent nominal 150/50/2 → 50 kPa와 1/3 근사·최종 cast 손실을 확인했다. 우선순위·좌결합·괄호·숫자 인수·지원 함수·static 단위/타입·읽기/ready/view 부모·근거 closure·길이/토큰/깊이/연산/graph 크기 제한을 검증했다. 실제 sample의 분모 0·결측은 기존 preview에서 검사한다.

17 화면 작성/compile/read-only·stale revision 409·graph/recipe 원자 저장·reload 원문·수동 graph 변경 stale·명시적 재컴파일/이력 보존을 확인했다. 새 lazy 테이블을 포함한 rollback, source/connection 변경 감지·무관한 source 변경 제외·graph 제거 후 이력 보존·과대 history fault 거부를 검증했다. 기존 05/06/09/13/16 경로와 옛 DB 재개방 행 보존도 통과했다.

Bifrost **코드·schema·JAR는 변경하지 않았다**. 이전 카탈로그 단계의 매핑 관련 Java JUnit 138개는 이번 새 실행 수에 더하지 않는다. 동일 JAR SHA를 재확인하고 새 컴파일된 2.15 DAG를 실제 Java CLI로 수신 검증·두 등록 키 승인·파일 발행했다. output unit을 변조하고 manifest SHA까지 다시 만든 음성 package도 receiver가 graph.output-unit으로 거부했다. Java가 Tyr (Týr) 코드를 참조하거나 수식 원문을 실행하지 않는다.

기존 canonical 계약 파일 75개(스키마 74개 포함)·fixture 513개·평가 계약 1개 SHA가 유지됐고 schema 74개 Java 사본은 동일하다. 새 local editor recipe 계약만 별도 추가했다. 기존 SQLite workspace/기존 테이블·행·CAS·버전은 유지한다. 최초 명시적 수식 apply에서만 별도 recipe 테이블을 추가하며 조회/compile/옛 DB 재개방은 테이블이나 행을 만들지 않는다.

## 실행·증거

최종 `build/expression/20261018-091415`는 기존 로컬 이미지, network=none, DNS localhost, cap-drop ALL, no-new-privileges와 읽기 전용 입력 archive를 사용했다. browser 요청은 localhost뿐이고 page error가 없었다. Windows 호스트 전체 firewall·운영 배포·native 장치 격리를 수용한 결과가 아니다.

- [실측 집계](expression-summary.json), [최종 연계/입력 SHA](expression-full-acceptance.json), [현재 source pin](expression-validation-pins.json)
- [새 Python 검사](expression-python-tests.log), [기본 수용](expression-baseline.json), [A07](expression-a07.json)
- [기존 호환성](expression-compatibility.json), [이전 계약/fixture SHA](expression-baseline-pins.json)
- [격리 설정](expression-docker-inspect.json), [실행 인자](expression-docker-arguments.json), [이미지](expression-image-inspect.json)
- [실행 이력](expression-run-history.json), [최종 화면](expression-preview.png)

사전 UI 실행과 초기 전체 실행은 별도 보존했다. 화면 QA에서 괄호 부분식의 시작 위치가 한 글자 빠진 점을 발견했다. 계산 DAG는 같았지만 근거 표시를 수정하고 완전한 괄호/원문 범위 검증을 추가한 뒤 최종 전체 실행으로 판정했다. 초기 실행의 성공을 최종 source 검증으로 대체하지 않았다. 최종 source/fixture/editor 계약/JAR pin은 현재 파일과 일치한다.

최종 합성 시연은 http://127.0.0.1:59783/ 의 17 화면이다. `build/expression-final-ui`에 네 수식과 명시적 매핑을 저장했고 초기 시연 DB는 별도 보존했다. 공개 키·서명 이력만 복사했으며 개인 키는 시연 DB/registry에 저장하지 않았다. 원래 사용자 DB·registry를 변경하지 않았다.

일반 식 전체·조건/비교/Boolean 식·일반 차원 추론/복합/역단위·온도 delta·cross-graph·vendor/native·현장 의미/계수/단위 정답·검토 시간/재사용성·대량 규모 수용은 미완료다. 로컬 원문 이력은 서명된 Bifrost 사실이 아니며 실제 의미 동등성을 자동 증명하지 않는다. 장치 통신·외부 SQL·쓰기 실행·runtime 활성화는 계속 제외한다.
