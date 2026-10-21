# P7 독립 평가 준비 수용 결과 · 2026-10-18

판정: P7 평가 준비 도구의 제한된 오프라인 범위 충족. 실제 현장 PoV는 미수행이다.

| 검증 | 최종 결과 | 근거 |
|---|---:|---|
| 신규 evaluator/API | 35/35 | 네 profile·40 nested/구조 배열 말단, 정답 범위/누락/중복/의미·정의·값·손실·시간·독립성·SQLite/HTTP |
| 기존 Python·fixture | 897/897 | 복구 13 + 가져오기 58 + 후보 그래프 39 + 구조 30 + 제한 연산 17 + A07 39 + 기본 701 |
| 브라우저·HTTP·CLI·SQLite | 18/18 | 격리 Chromium/Python, blank oracle·미검토·의미/값·입출력 hash·전 테이블 무변경·legacy 개방·stale/invalid 거부 |
| 추가 CLI 파일 보호 | 3/3 | 임시 복제 입력·정답·기존 출력 파일 overwrite 거부와 바이트 보존 |
| 기존 입력 | 변경 0 | canonical 계약 파일 72개·기존 fixture 502개 SHA 보존, Bifrost JAR 동일 |

Python·fixture 합계 932다. 전체 runner의 26행 중 8행은 suite exit 표식이므로 별도 시험으로 중복 합산하지 않는다. 최종 UI 재실행의 동일 18항목도 중복 합산하지 않는다. Java 소스/JAR 변경이 없어 Java JUnit을 다시 실행하지 않았다. 이전 P6의 Java 116개는 역사적 근거이며 이번 신규 검사 수에 포함하지 않는다. 기존 기본 회귀의 Java CLI 호출은 --network none 안에서 실행했다.

## 확인한 경로

- 독립 정답 양식은 기대 의미/값/hash를 자동으로 채우지 않는다. 빈 양식은 40개 unreviewed/0%로 나타난다.
- 설비·객체 버전·전체 member/index 경로로 항목을 구분한다. AB/UA/DB/MELSEC 가상 자료의 같은 canonical 의미가 그룹으로 보이되 객체 인스턴스를 합치지 않는다.
- 의미 불일치와 구조적 정의 차이를 분리하며 미검토/누락/중복/추가 미평가/부분 검증을 숨기지 않는다. 일부 oracle만 있으면 scope coverage를 별도로 표시한다.
- 독립 수치 정답·정밀도 손실 코드·품질/오류·타입/단위를 대조하고 전체 preview trace를 보존한다. 숫자 표기 150/150.0과 Boolean/String은 각각 적절히 구분한다.
- calibration/evaluation/heldout과 분모·미측정을 분리한다. 여섯 작업 단계의 완료 pair만 시간 비교에 넣으며 문의/수정/재검토를 제외하지 않는다. 합성 숫자는 현장 절감 실적이 아니다.
- 평가/양식 생성 전후 SQLite 모든 기존 테이블과 revision/행이 같고 재개방 값도 같다. 기존 DB backup 개방도 행을 보존한다. 평가 결과/입력은 별도 JSON 파일이며 평가 테이블/마이그레이션이 없다.
- local Origin/header/CSP·409 stale/422 invalid·파일 export·결과 pin 검증을 유지한다. 원본 workspace/pack이나 기존 출력 파일을 CLI가 덮어쓰지 않는다.

## 실행·원본 증거

전체 `build/p7eval/20261018-053654`와 최종 UI `build/p7eval/20261018-053937` 모두 성공했다. 전체 이후 product 변경은 기존 memberPathLabel을 사용한 화면 경로 표시뿐이며, 캡처 위치와 fixture oracle 설명 파일을 추가했다. backend/evaluator/schema/new test cases는 동일하다. 변경 목록과 최종 전체 source pin 일치를 [실행 이력](p7eval-run-history.json)에 기록했다.

- [추가 CLI 파일 보호](p7eval-cli-file-protection.json). 이 세 검사는 Python 932/연계 18에 중복 합산하지 않았다.
- [전체 수용](p7eval-full-acceptance.json), [최종 화면 수용](p7eval-ui-acceptance.json), [기존 701 회귀](p7eval-regression.json), [신규 35](p7eval-evaluation-tests.log).
- [입력/JAR pin](p7eval-validation.json), [이전 입력 보존](p7eval-compatibility.json), [Docker 설정](p7eval-docker-inspect.json), [실행 인자](p7eval-docker-arguments.json).
- [합성 평가 report](p7eval-example-report.json), [화면](p7eval-summary.png), [설계·계약](../P7-EVALUATION-PREPARATION.md), [현장 절차](../P7-POV-PROTOCOL.md).

재현은 `scripts/p7eval/run.ps1`, 화면만 재검증할 때 `-UiOnly`다. 로컬 이미지 tyr-a14:20261018, --network none / localhost DNS / cap-drop ALL, readonly 입력을 사용했다. 이전 DB/registry를 변경하지 않았으며 별도 시연은 build/p7eval-ui/editor.sqlite3와 localhost:59780이다. 합성 입력 파일은 fixtures/p7-evaluation/oracle.json이다.

## 완료와 별도 미완료

이번 완료는 평가 계약/양식·집계기·화면/CLI·익명화 인수 양식·절차 및 합성 검증이다. field-declared/independenceAttested는 자기 선언이고 report hash는 서명이 아니다. oracleEvidence 문자열의 실제 파일/담당자 진위, 가명화 품질·자료 누출, 의미/계산 허용 오차와 시간 기록 진위는 도구가 인증하지 않는다. verified-fixture는 정의 pin과 가상 시험의 일치이며 Bifrost 승인/운영 적합성이나 자동 후보 precision 95% 달성을 뜻하지 않는다.

실제 자료·독립 정답·오매핑/누락/손실·전체 검토 시간/재사용성의 현장 PoV, vendor native/export 검증, 추가 importer/일반 식·cross-graph 확장, Windows 배포/전체 방화벽·전원 손실 durability·IAM/외부 anchor·실제 활성화는 별도다. 장치 통신·외부 SQL·쓰기 실행은 추가하거나 실행하지 않았다. commit/push/merge는 수행하지 않았다.
