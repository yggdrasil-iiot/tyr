# P7 평가 준비: 독립 정답·가상 계산·검토 시간

이 단계는 MVP-PLAN의 P7 준비 항목인 익명화 자료 인수 양식·평가 지표·절차를 실행 가능한 오프라인 도구로 만든다. 실제 현장 PoV 완료를 뜻하지 않는다. 장치 통신·외부 SQL·쓰기 실행·runtime 활성화는 제외한다.

## 이번 단계 선택과 남은 항목

기존 P0~P6 및 P7 가상 수용은 구현됐다. 남은 vendor native layout/실제 exporter·의미 정답/운전모드 정책·현장 검토 시간은 자료와 담당자가 필요하다. PDF/.xls/OCR·임의 식·cross-file alias·workspace history 압축은 별도 제품 확장이고, 목표 Windows 배포/전원 손실/운영 IAM·외부 anchor는 별도 환경 수용이다. 이번에는 새 프로토콜을 구현하지 않고 현장 평가를 재현 가능하게 준비한다.

## 재사용과 새 구현

| 구분 | 내용 |
|---|---|
| 재사용 | workspace 2.0 snapshot·revision/CAS, logical member/index 경로, source/graph 참조, 순수 preview의 codec/변환/품질/손실, 기존 SQLite, 로컬 HTTP/CSP |
| 신규 | scripts/pov_evaluation.py, 별도 evaluation-contracts/1.0.0, 독립 oracle/시간 집계·report pin, 16 화면·파일 입출력, 합성 정상/손실 fixture와 검증 |
| 보존 | 기존 contracts 파일과 Bifrost schema/JAR, SQLite 테이블·기존 행·마이그레이션 정책·불변 제출본 |

평가 pack/report는 별도 로컬 산출물이다. Bifrost 승인 계약이나 canonical Source/Semantic/Mapping 버전이 아니다. Bifrost·Mimir (Mímir)·Muninn 코드는 공유하거나 수정하지 않는다. SQLite에 평가 테이블을 추가하거나 workspace를 재작성하지 않는다.

## 평가 계약 1.0.0

[pack schema](../evaluation-contracts/1.0.0/pov-evaluation.schema.json)는 추가 필드·중복 ID·잘못된 자료를 거부한다. 한 pack은 최대 32 mapping-set, 256 멤버, 항목당 16 sample, sample당 256 가상 입력, 256 시간 비교 쌍을 허용한다. workspace 1.x는 기존 명시적 이전 전까지 평가 대상에서 제외한다.

- origin은 synthetic 또는 field-declared이다. field-declared도 보고서에서 field-declared-unverified / fieldPoV:not-certified로 남는다. 독립성 체크와 reviewerId는 자기 선언이며 인증/승인이 아니다.
- mappingSetIds가 실제 평가 범위다. identity는 equipmentInstanceId + targetInstanceRef(id/version) + 전체 memberPath다. 동일 설비의 다른 객체, 중첩 멤버, 구조 배열 인덱스를 합치지 않는다. 다른 이름은 의미 동등성을 자동 결정하지 않는다.
- cases에는 stable caseId, calibration/evaluation/heldout split, identity, oracleEvidence, expected, samples를 넣는다. 같은 identity를 다른 split으로 중복 사용하면 거부한다. 원본 파일을 다른 ID로 바꾼 자료 누출은 담당자가 인수 manifest로 통제해야 한다.
- expected는 null로 시작한다. 입력 생성기는 identity만 채우고 의미/값/정의 hash 정답을 생성하지 않는다. inventory는 현재 정의와 hash를 별도로 보여 주는 검토 자료다.
- reviewed expected에는 semanticId/valueType/unit/role과 definitionSha256(미검토면 null)를 기록한다. 검토자/독립성 선언과 oracleEvidence가 필요하다. 동일 canonical URI의 서로 다른 타입·단위·역할 정답은 거부한다.
- definitionSha256은 binding과 참조 source/graph/view closure의 구조적 pin이다. 문서 수준의 이름·설명·status·evidenceRefs·rawAddressText는 제외하고 실제 access·rawRepresentation·단위·연산/정책은 포함한다. ID/버전과 전체 graph 문서를 포함하므로 사용하지 않은 후보의 변경도 나타날 수 있다. hash 차이는 구조적 재검토 사유이며 의미 오류로 자동 단정하지 않는다. 현재 inventory hash를 검토 없이 정답으로 복사하면 독립 검증이 되지 않는다.
- samples는 가상 입력과 선택적 evaluationContext, 독립 expected.result/quality/issues/losses를 제공한다. 숫자는 같은 선언 타입·단위에서 정확한 Decimal 값으로 비교하고 150/150.0 표기는 같게 본다. Boolean과 문자열은 혼동하지 않는다. 허용 오차·자동 단위 추정은 없다. issues/losses는 코드 집합을 비교하며 같은 코드의 발생 횟수는 평가하지 않는다. 기존 preview의 전체 단계 trace를 결과에 포함한다.

## 판정·분모

missing, ambiguous, unreviewed, meaning-mismatch, definition-difference, sample-mismatch, partial, verified-fixture를 구분한다. 정의 pin 또는 가상 sample이 없으면 partial이며 완전 확인으로 계산하지 않는다. 오류 기대값(result:null, bad 품질과 코드)도 명시적으로 대조할 수 있다. 상태는 앞에 적힌 우선순위를 사용하지만 definitionDifferenceCases·sampleMismatches·lossDiagnosticMismatches는 독립적으로 집계한다.

split마다 모든 oracle 항목을 분모에 넣어 누락·미검토를 숨기지 않는다. calibration은 evaluation/heldout 실적에 합산하지 않는다. actualBindings/uniqueActualIdentities/reviewedUnambiguousIdentities와 정답 검토 coverage, 정답이 없는 unexpectedMappings를 함께 표시한다. 일부 정답의 100% 확인율을 전체 scope 정확도로 바꾸지 않는다. planned/evaluated/notRun sample도 보존한다. 분모가 0이면 비율은 null/미측정이다.

## 검토 시간

participantId·taskId마다 manual/tool을 한 쌍으로 선언하고 순서를 기록한다. import/interpret/map/inquire/correct/review의 여섯 단계 시간을 모두 요구한다. 한 단계는 0~86400초, 누락·음수·Boolean·중복 비교 쌍은 거부한다. 완료 쌍만 해당 split의 합계에 넣고 미완료 쌍을 별도 표시한다. 두 수행 순서의 존재를 표시하며 통계적 유의성·인과관계는 주장하지 않는다.

절감률은 `(수작업 전체 합계 - 도구 전체 합계) / 수작업 전체 합계`다. 문의·수정·재검토를 뺀 import 시간만으로 계산하지 않는다. 데이터는 수동 선언이며 실제 stopwatch나 작업 로그의 진위를 검증하지 않는다. 시간이 없으면 미측정이며 합성 fixture 숫자를 현장 절감 실적으로 사용하지 않는다.

## 화면·API·CLI

16 독립 정답·평가 준비에서 mapping-set 선택 → 빈 정답 양식 → 별도 독립 검토 → JSON 파일 열기/편집 → 현재 저장본과 평가 → 입력/결과 JSON 저장 순으로 사용한다. 입력을 고치거나 평가가 거부되면 이전 결과 다운로드를 비활성화한다. report에는 revision, workspaceSha256, baselineWorkspaceChanged, packSha256, reportSha256이 들어간다. reportSha256은 자기 필드를 제외한 sample_quality.digest 방식이며 parsed JSON의 pin이다. 원본 파일 바이트 pin·서명·외부 anchor를 대체하지 않는다.

POST /api/pov-template는 revision/mappingSetIds, POST /api/pov-evaluate는 revision/pack을 받는다. 기존 local Origin/X-Tyr-Editor·2 MiB 제한·409 stale/422 invalid 정책을 유지한다. 파일 경로·SQL·실행 명령을 입력으로 받지 않는다. 결과는 고정된 snapshot에 관한 읽기 전용 산출물이다.

~~~powershell
python -B scripts/pov_evaluation.py fixtures/p3eb/workspace.json --template --out build/blank-oracle.json
python -B scripts/pov_evaluation.py fixtures/p3eb/workspace.json --pack fixtures/p7-evaluation/oracle.json --out build/synthetic-evaluation.json
~~~

CLI는 기존 출력 파일이나 입력 파일을 덮어쓰지 않는다. 생성한 blank-oracle.json은 담당자가 별도 편집해 --pack으로 사용할 수 있다. 합성 fixture와 검증은 [fixture 설명](P7-EVALUATION-FIXTURES.md), 실제 자료 준비는 [PoV 절차](P7-POV-PROTOCOL.md)를 따른다. 수용은 [결과 문서](verification/P7-EVALUATION-RESULTS.md)에 별도 기록한다.
