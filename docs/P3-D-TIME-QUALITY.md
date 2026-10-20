# P3-D 가상 입력 시각·품질과 검증 시나리오

2026-10-17. 실제 장치 통신·시간 측정·handshake·승인·활성화는 제외한다.

## 계약과 재사용 경계

2.3.0 common/mapping-set/preview-scenario를 추가했다. 기존 1.x·2.0·2.1·2.2 Schema는 수정하지 않는다. workspace envelope/target/proposal는 2.0, 소스/의미/그래프의 기존 문서 버전은 유지한다. 매핑 바인딩의 선택 필드 temporalPolicy로 검증을 명시적으로 활성화한다. 기존 바인딩에 정책을 자동 주입하지 않는다.

그래프 source lineage·기존 HEX/Typed 디코더·수치 변환·최종 cast·revision snapshot·SQLite JSON/CAS를 재사용했다. sample_quality.py, 가상 DataValue·시간/품질 preflight·별도 시나리오 저장/API·quality.js는 신규다. 평가기는 datetime.now를 사용하지 않는다.

Týr가 작성·검증을 소유한다. Mímir 후보, Bifrost 승인·release, Muninn 실행/품질 전파의 실제 수신 지원은 이번 변경으로 확정되지 않는다. 프로젝트 간 코드 공유는 없다.

## 매핑의 temporalPolicy

| 필드 | 허용 값과 의미 |
|---|---|
| timestampBasis | source 또는 server. 이 시각으로 age와 skew를 계산 |
| maxAgeMs | 0~86400000 정수. 0 ≤ 기준 시각−입력 시각 ≤ 한도 |
| maxSkewMs | 0~86400000 정수. 필요한 입력 시각의 최댓값−최솟값 ≤ 한도 |
| uncertainInput | propagate: 수치 평가 후 uncertain 전파, reject: bad/null |
| missingInput | reject 고정. 누락/값 없음은 bad/null |
| badInput | propagate 고정. 입력 bad는 전체 파생 결과 bad/null |
| assembly | latest: 선택한 입력 묶음, trigger-sequence: 각 입력 sequence가 명시한 triggerSequence와 일치 |

age·skew 경계는 포함한다. 1000ms age/100ms skew 한도에서 정확히 같은 값은 허용하고 0.001ms 초과는 거부한다. 미래 입력은 허용 오차 없이 차단한다. UTC offset을 정규화해 마이크로초 정수 차이로 비교한다.

시각은 offset을 가진 RFC3339 형태, 소수 초 최대 6자리다. offset 없는 시각·불가능한 날짜·알 수 없는 offset -00:00은 차단한다. sourceTimestamp 미확인을 serverTimestamp로 대체하지 않는다. 선택하지 않은 시각도 제공했다면 형식을 검사하지만 freshness/skew에는 선택한 기준만 사용한다.

## 가상 DataValue와 평가

기존 값 전용 샘플은 정책 없는 매핑에서 그대로 유지한다. 정책이 있는 매핑은 다음 envelope를 요구한다.

    {
      "value": {"bytesHex": "9600"},
      "quality": "good",
      "sourceTimestamp": "2026-10-17T09:59:59.500Z",
      "serverTimestamp": "2026-10-17T10:00:00Z",
      "sequence": null
    }

value는 기존 bytesHex/typedValue 페이로드 또는 null이다. null은 결측 검증 사례다. 시각·sequence 미확인도 null로 보존한다. quality는 good/uncertain/bad의 가상 추상화이며 vendor status code나 실제 OPC UA DataValue 지원을 뜻하지 않는다.

POST /api/preview의 기존 revision/mappingSetId/mappingId/samples와 함께 evaluationContext를 전달한다.

    {"at": "2026-10-17T10:00:00Z", "triggerSequence": null}

필수 입력은 선택한 바인딩의 source→graph 전체 의존성에서 구한다. 동일 소스의 여러 사용은 한 입력으로 검사한다. 사용하지 않는 bad 표본은 계산을 오염시키지 않고 sample.unused 경고로 표시한다. source-only, low/high, 입력별 변환을 거친 차압도 같은 정책을 사용한다.

처리 순서는 명시적 평가 기준 → 각 입력 시간·품질 → 조립/skew/sequence → 기존 디코딩·그래프·변환·cast다. 시간·품질 오류가 있으면 수치 계산 전에 중단한다. 결측을 0·마지막 값·다른 시각으로 대체하지 않는다.

응답 temporal에는 입력별 시각·품질·age·sequence, skew, 입력 시각 범위, 조립 상태가 있다. dataValue는 최종 품질·평가 기준·입력 시각 범위·확인한 trigger sequence를 기록한다. 파생 결과의 sourceTimestamp/serverTimestamp는 null이며 임의로 입력 시각을 대표 시각으로 만들지 않는다. atomicSnapshot=false를 항상 명시한다. 수치 변환 손실과 uncertain 입력은 최종 품질을 uncertain으로 전파하고, 오류는 bad/null로 전파한다.

sampleSha256은 메타데이터를 포함한 samples 전체, evaluationSha256은 samples+evaluationContext, workspaceSha256은 정책을 포함한 작성본을 고정한다. 같은 입력/기준이면 같은 결과이며 서버의 실제 현재 시각과 무관하다.

## SQLite와 가상 시나리오

정책은 기존 workspace JSON에 저장하며 revision CAS·원자 저장을 유지한다. 새 preview_scenarios 테이블은 입력과 가상 평가 기준만 별도로 저장한다. 기존 DB에 CREATE TABLE IF NOT EXISTS로 추가하므로 기존 body/revision/이전 이력은 재작성하지 않는다. 적용 전 주 DB revision 18을 build/p3d-ui/pre-p3d.sqlite3으로 백업했다.

preview-scenario에는 id/version/label, mappingSetRef(id/version), mappingId, workspaceSha256, evaluationContext, samples가 들어간다. 독립 검증 자료이며 mapping-proposal/release의 승인 파일로 자동 포함하지 않는다.

- GET /api/scenarios: 작성본 revision/hash, 시나리오 및 stale 여부.
- POST /api/scenarios: workspaceRevision/scenarioRevision/scenario. 작성본 revision·hash·매핑 참조·정책·Schema를 확인하고 시나리오 자체 revision CAS로 저장한다.
- 시나리오 ID 최대 100개, 요청 2MiB 제한. 잘못된 요청·외부 Origin을 거부한다.
- 작성본 내용이 달라지면 시나리오는 보존하되 stale로 표시한다. 화면의 불러오기는 차단한다. 같은 내용의 단순 재저장은 hash가 같으므로 stale이 아니다.
- 시나리오 저장은 작성본 revision을 바꾸지 않는다. 미리보기는 어느 테이블에도 쓰지 않으며 결과를 자동 저장하지 않는다.

## 화면 사용

06 객체 매핑에서 시간·품질 정책을 선택하고 timestampBasis·age/skew·uncertain·조립 방식을 저장한다. 09에서는 가상 평가 기준 시각, 입력별 quality/sourceTimestamp/serverTimestamp/sequence를 입력한다. 값을 비우면 해당 입력 결측을 시험한다. 입력 변경 시 이전 결과를 지운다.

시나리오 ID/설명을 지정하고 명시적으로 저장한다. 목록에서 불러온 뒤 재평가하면 저장 당시 가상 시각으로 재현한다. 기준 시각은 실제 현재 시각으로 자동 갱신하지 않는다.

## 정확한 완료 범위

선택한 단일 바인딩의 필수 입력 묶음을 검증한다. target 전체 프로퍼티의 한 번에 조립·부분 객체 정책·이력 기반 freshness·실제 OPC 품질·시계 동기화는 별도다. trigger-sequence는 한 번의 가상 묶음에서 일치 여부를 확인하며 연속 이벤트의 latch·중복/역순 처리·PLC trigger/ack 동작은 구현하지 않는다. 이 일치가 실제 동시성을 증명하지 않는다. MP16 전체 지원은 partial로 유지한다.

[독립 fixture](../fixtures/p3d/README.md) · [검증 결과](verification/P3-D-RESULTS.md) · [계획](../MVP-PLAN.md).
