# P4-F PIO·Kepware 외부 정의 수용과 정준 모델 연결 설계

2026-10-20. 상태: **설계 확정, A1(Mimir wire 계약)은 2026-10-22 완료(mimir PR #3), A2(Tyr 수신·editor 계약)도 2026-10-22 완료(tyr PR #4), 그 밖은 구현 예정**. 같은 날 후속 결정: **원본 해석은 Mimir (Mímir)로 이관**한다. §6 해석기 계약은 Mimir가 구현하고 Tyr (Týr)는 Mimir가 발행한 해석 스냅샷의 소비자다(§3). 이 문서는 신규 논리 모델과 해석기 경계를 정의한다. 실행 가능한 JSON Schema·API·SQLite 저장·fixture·화면이 구현됐다는 뜻이 아니다. 정식 계약 버전은 P4-F A에서 정하며 기존 wire 1.x~2.22와 editor 계약을 소급 변경하지 않는다.

정준화의 목적지는 [정준 의미 계약과 값 생성·매핑 계약](CANONICAL-SEMANTICS-AND-GENERATION.md)의 두 계약이다. PLC 메모리맵은 입력 정의의 일부다. MES에 노출되는 혼합 객체의 업무 뜻과 생성 규칙을 나눠 전환·검토하며, MG01~MG08 fixture 계획을 기존 SI01~SI18에 추가한다.

## 1 목표와 완료 범위

대상 현장의 PIO와 Kepware 설정·백업을 Mimir가 제품별 해석기로 해석해 발행한 스냅샷을 수용한다. 문서가 없고 설정 하나만 있는 경우도 출발점이다. 최종 태그/객체/프로퍼티에서 입력·변환·참조·공통 설정까지 역추적하여 **확보된 자료 안에서 무엇을 설명할 수 있는지**, **기존 Tyr 계약으로 무엇을 옮길 수 있는지**, **무엇을 추가 확인해야 하는지**를 근거와 함께 보여 준다.

설정에 기록된 사실, 제품 규칙에 따른 해석, 사람이 확인한 의미, 가상 검증 결과, Bifrost 승인, 실제 운영 일치 여부를 분리한다. 주소를 찾거나 파일 문법을 읽은 것을 최종 태그의 동작 이해로 판정하지 않는다. 제공 파일이 실제 실행 중인 설정이라는 주장도 별도 확보 근거 없이는 하지 않는다.

제품·버전·드라이버·확보 형식·매핑 패턴별 지원을 관리한다. PIO와 Kepware가 모든 공장에 존재하거나 전 버전을 지원한다는 전제는 두지 않는다. 장치 통신·browse/read/write·외부 SQL·vendor 수식/플러그인 실행·운영 설정 수정·설정 exporter·배포·활성화는 제외한다. 로컬 SQLite의 작성 메타데이터 저장은 허용한다.

## 2 기존 구현과의 경계

| 기존 자산 | 재사용 | 새로 필요한 것 |
|---|---|---|
| [P4-A](P4-A-FILE-IMPORT.md) 2.6 원본 bytes/hash·관측·locator | 원본 식별·보존·파서 버전 고정 원칙 | 여러 파일·범위가 다른 export를 묶는 자료 세트 |
| [P4-A B](P4-A-IMPORT-RECONCILIATION.md) 2.14 검토/채택/3방향 병합 | 결정 hash chain·CAS·명시적 채택·이력 보존 원칙 | scalar source 밖의 제품 구성 그래프와 참조/정책 변경 검토 |
| source/graph/target/mapping·view·구조·selector·템플릿 | 지원되는 정의의 전환 대상과 가상 preview | 제품 구조와 정준 작성본 사이의 명시적 전환 계획·근거 |
| [작업자 흐름](OPERATOR-WORKFLOW.md)·P5·P7 평가 | 단계·입력 보존·변경 영향·독립 정답 비교 | 최종 태그 탐색·쟁점 중심 검토·대조표 반환 |
| P6 Bifrost 파일 제출·검증·승인·발행 | 승인 권위와 기존 계약의 독립 검증 | 향후 새 해석/전환 근거를 검증할 opt-in wire 계약 |

현재 importer는 bounded XLSX/tyr-config-v1이며 실제 PIO/Kepware parser가 아니다. 2.14의 resolve-source도 완전한 PLC 읽기 source 정의를 대상으로 한다. 복합 태그·수식·상속을 강제로 한 source로 평탄화하거나 importRef에 vendor 관측을 끼워 넣지 않는다. 기존 재해석 검증을 우회하지 않는다.

## 3 계층과 책임

```text
[Mimir — vendor 원본을 해석하는 유일한 곳]
원본 설정/백업/허가된 화면·문서
  → SourceBundle (불변 원본과 확보 범위)
  → PIO 또는 Kepware Interpreter (제품 구조·규칙 해석)
  → InterpretationSnapshot (원본 노드·참조·주장·근거·미해석)
═════ 발행: 해석 스냅샷 파일 계약 (Mimir 소유 schema, 소비자는 사본 번들) ═════
[Tyr]
  → 스냅샷 pin·무결성 재검증 (재파싱 없음)
  → 공통 참조 검증 + 최종 endpoint 의존 관계 조회
  → ConversionPlan (정준 의미 계약 + 값 생성·매핑 계약, 기존 Tyr 계약 후보와의 대응)
  → 두 계약의 적합성 검토·담당자 확인·독립 가상 검증·정준 작성본 채택
[Bifrost]
  → 검증/서명 승인/파일 발행 (별도 권한)
  → 별도로: 거버넌스된 정의 ↔ 현재 스냅샷 대조 (ENTERPRISE.md 13번 행)
```

공통 수용 모델은 제품 설정에 무엇이 선언됐는지를 설명한다. 정준 의미 모델은 어떤 설비의 어떤 속성을 의미하는지 설명한다. 원본 태그 ID·계층·주소를 semantic URI로 자동 승격하지 않는다. PIO와 Kepware에서 이름/주소가 같아도 동일 설비·측정 위치·입력 단계·변환 근거가 확인되기 전에는 병합하지 않는다.

값 생성·매핑 모델도 제품 독립 정준화 대상이다. PLC 접근·DB 결과 필드/선택·상수·연산/조건·오류/시간 정책을 보존하고 목적지 의미 계약과 결합한다. 같은 결과 타입·단위라도 작업지시 범위/누적 기준·코드 의미가 다르면 호환으로 간주하지 않는다. 가상 수치 동등성·업무 의미 적합성·Bifrost 승인·실제 운영 일치를 별도로 판정한다.

**원본 형식마다 해석하는 곳은 한 곳이다.** Mimir가 원본 수용·해석(SourceBundle·InterpretationProfile·InterpretationSnapshot)을 소유하고 스냅샷을 파일 계약으로 발행한다. 계약의 소유자는 생산자인 Mimir이며, 소비자는 schema 사본을 번들한다. Tyr는 스냅샷의 pin을 재검증하되 원본을 재파싱하지 않으며 closure 조회·검토·전환 초안·채택을 소유한다. Tyr와 Bifrost는 vendor 원본을 직접 파싱하지 않는다. 이전 결정(Tyr가 해석까지 소유, Mimir는 별도 후보 생산자)은 2026-10-20 후속 결정으로 대체한다. Bifrost는 공개된 파일/wire 계약만으로 독립 검증·승인한다. Muninn/기존 실행 솔루션의 통신·실행은 이번 범위가 아니다. 앱 간 공유 코드·DB 직접 접근·Java→Python vendor 해석 호출을 추가하지 않는다.

## 3-1 정준 경계

벤더 데이터 수집 구성은 장치 접근 정보, 값의 의미, 응용 및 제어 로직이라는 서로 다른 성격의 세 계층을 한 파일 안에 섞어 담을 수 있다. 모델링 워크벤치인 Tyr는 벤더 구성 자체를 직접 읽지 않으며, Mimir가 발행한 해당 구성의 해석 스냅샷을 전달받아 정준 모델로 변환하는 역할을 수행하지만, 원천 파일에 존재하는 모든 내용을 정준 모델로 직접 수용하지는 않는다. 본 절에서는 벤더 구성의 각 요소 중 어느 영역까지를 정준 모델의 경계 내에 편입하며, 각 요소를 어떠한 규칙에 따라 처리할 것인지를 규정한다.

| 계층 | 구성 요소 | 정준 모델 포함 여부 및 처리 원칙 |
| :--- | :--- | :--- |
| 1계층: 접근 | 장치 주소, 데이터베이스 쿼리 | 원천 정의로 정준 모델에 포함하여 보존한다. 단, Tyr가 장치에 연결하거나 외부 SQL을 실행하지는 않는다. |
| 2계층: 값 의미 | 스케일링, 단위, 코드 사전, 복수 입력 결합, 상수 | 내부 상태가 없으며 Tyr의 기존 계약(값 그래프, 템플릿)으로 선언적 표현이 가능할 때 정준 모델에 포함한다. 상수는 역할을 표기하여 유지한다. |
| 3계층: 응용 및 제어 로직 | 상태 유지 읽기 스크립트, 쓰기 스크립트 | 읽기 전용 상태 스크립트는 의미만 정준에 두고, 원문은 불투명 아티팩트로 보존하며 변환을 차단한다. 쓰기 스크립트는 제어로 규정하여 쓰기 존재 및 대상만 기록한다(받는 쪽은 아직 없다, 아래 참조). |

정준 모델을 구축하는 근본 원칙은 의미의 소유권이 벤더의 구성 파일이 아니라 MES와 같은 소비 시스템이 요구하는 소비 계약(consumer contract)에 있다는 점이다. 벤더 구성은 이러한 소비 계약을 구현한 여러 방식 중 하나에 불과하다. 따라서 벤더 구성 파일에 기술되어 있는 이름, 태그 ID, 장치 주소 등은 정준 모델 내에서 자동으로 의미로 승격되지 않는다.

1계층인 접근(access) 영역은 장치 주소와 데이터베이스 조회를 위한 쿼리를 포함한다. 이 영역은 원천 정의(source definitions)로서 정준 모델에 보존되지만, 접속 자격증명과 같은 시크릿 값은 시크릿이 제거된 상태로만 보존된다(§4 참조). 다만 해당 정의를 정준 모델에 보존한다고 해서 Tyr가 물리적 장치에 직접 연결하거나 외부 데이터베이스를 대상으로 SQL을 실행하는 것은 결코 아니며, Tyr는 이러한 실행을 일절 수행하지 않는다.

2계층인 값 의미(value meaning) 영역은 데이터의 스케일링, 공학 단위, 코드 사전, 복수의 입력을 결합하는 로직, 그리고 상수를 포괄한다. 이 계층의 요소들은 내부 상태를 갖지 않는 무상태(stateless) 구조이면서, 값 그래프나 템플릿과 같은 기존 Tyr 계약 틀 안에서 선언적으로 표현될 수 있는 경우에 한하여 정준 모델의 정식 구성요소로 편입된다.

상수는 2계층 내에 유지되지만, 각 상수는 식별자, 스케일 계수, 또는 설정값 및 임계값 중 어느 역할에 해당하는지 명확히 표기되어야 한다. 특히 설정값과 임계값은 비즈니스 정책에 보다 밀접하게 닿아 있으므로, 해당 역할이 모델 상에서 가시적으로 드러나야 한다. 단, 상수에 역할을 표기하는 구체적인 기능은 현재 구현되지 않은 상태이다.

3계층에 속하는 스크립트 중 이전 값 참조, 값의 누적, 에지 감지(edge detection)와 같이 내부 상태를 유지하면서도 오직 읽기 동작만을 수행하는 스크립트의 경우, 그 처리 결과가 가지는 의미 자체는 정준적인 것으로 인정된다. 그러나 스크립트 원문 텍스트는 특정 버전과 해시로 엄격히 고정된 불투명(opaque) 아티팩트로 보존되며, 정준 모델 요소로 변환되는 것은 차단된다. 이는 상태를 수반하는 행위는 변환하지 않고 원형 그대로 보존한다는 섹션 5의 설계 결정과 부합한다.

반면 장치나 데이터베이스로 값을 다시 쓰는(write back) 스크립트는 단순한 데이터 매핑이 아닌 제어(control)에 해당한다. 정준 모델은 쓰기 동작의 구체적인 유형을 현 단계에서 세부적으로 분류하지 않으며, 단지 파일 내에 쓰기 동작이 존재한다는 사실과 그 쓰기가 향하는 대상 경로만을 기록한다. 그러나 이 선언을 전달받을 아티팩트는 아직 존재하지 않는다. Bifrost의 명령 인가(NCMD 정책 및 Heimdall)는 에지를 통과하는 명령만을 대상으로 하며, "변경 관리에 의해 다른 곳에서 통제되는 경로(a path governed elsewhere, by change control)"를 위한 통신 정책(communication-policy) 필드 역시 아직 구현되지 않았다(Bifrost ENTERPRISE §5). 그때까지 벤더 스크립트의 쓰기는 기록되고 가시화되지만 강제되지는 않으며, Tyr와 Bifrost 어느 쪽도 이를 차단하지 않는다. 에지가 없는 사이트에서 이러한 쓰기는 우회(bypass)가 아니라 기존의 제어 경로이다.

시간과 데이터 품질은 정준 계약을 구성하는 필수 규약이다. 벤더 도구에 오류가 발생하여 값을 묵시적으로 누락하는 경우, 데이터에 타임스탬프와 품질 정보가 명확히 수반되지 않는다면 소비자는 그것이 '값 없음'인지, '구성의 변경'인지, 아니면 '수집기 정지'로 인한 것인지 구분할 수 없다. Tyr의 시간 및 품질 계약(P3-D)은 누락된 입력을 명시적으로 거부하며, 불량 입력을 0이나 직전 값으로 대체하여 채우지 않고 불량 상태 그대로 전파한다. 이 규약은 가상 입력에 관한 계약이며, 실제 가동 환경에서 작동하는 수집기의 런타임 품질을 물리적으로 측정하는 것은 본 설계의 범주에 포함되지 않는다.

본 절에서 규정한 정준 경계 및 처리 원칙들은 현재 단계의 설계 결정 사항이다. 실제 현장에서 유통되는 벤더 제품의 포맷을 온전히 지원할 수 있는지 여부는 아직 입증되지 않았으며, 이를 확정하고 검증하기 위해서는 실제 구성 파일에 기반한 추가적인 검증 작업이 필요하다.

## 4 공통 논리 모델 (신규 제안)

모든 불변 문서는 kind/id/version과 본문 hash로 참조한다. 아래 필드명은 설계 이름이며 기존 닫힌 schema에 그대로 추가할 수 있다는 뜻이 아니다. 새 editor 계약과 향후 wire 계약을 구분한다. 원본 bytes SHA256과 JSON 문서 digest는 별도 필드로 두고 기존 hash 알고리즘을 교체하지 않는다. digest 알고리즘/직렬화 버전·숫자/배열 순서·누락과 null 구분은 A에서 명문화하고 독립 fixture로 검증한다.

| 모델 | 소유 | 필수 정보와 불변식 |
|---|---|---|
| SourceBundle | Mimir wire | artifactRefs, 원본 bytes/hash·파일명·안전한 상대 경로·확보 시각/방법, 제품/버전/driver 주장과 근거, synthetic/field-declared 구분, 확보 범위. 설정·보조 파일·화면은 각각 독립 artifact. 원본 수정/교체 금지 |
| InterpretationProfile | Mimir wire | 해석기 ID/버전/구현 digest, 지원 제품/버전/driver/입력 형식/패턴 범위, 적용 규칙 ID/버전, 한도, coverage, 알려진 제한. unknown 제품 버전을 최신 규칙으로 조용히 처리하지 않음 |
| InterpretationSnapshot | Mimir wire | bundle/profile/input manifest pin, 당시 제공된 논리 문맥, nativeNodes, referenceEdges, claims, unresolved, 진단, 재현 정보. 새 파서/추가 파일/검토는 새 snapshot 또는 별도 결정이며 원본 관측을 덮어쓰지 않음 |
| NativeNode | Mimir wire | snapshot 내 nodeId, 제품 namespace와 native 식별자/경로, kind, 원문 locator, 원본 payload 참조, 제공된 출력/프로퍼티. connection/group/tag/map-entry/operation/policy/opaque 등. native 정체성과 향후 canonical ID 분리 |
| ReferenceEdge | Mimir wire | owner node+필드 위치, 관계(input/reference/contains/inherits/overrides/policy/external), 원문 target 표기, resolution 상태(resolved/missing/ambiguous/external-required/unsupported), 명시적으로 해석된 target pin, 후보·판단 근거. 이름만으로 최초 후보 선택 금지 |
| InterpretationClaim | Mimir wire | 주장 경로·값, native locatorRefs, evidenceBasis, rule/profile pin, 의존 claim/edgeRefs, 해석 상태. 원문 사실·규칙 해석을 개별 claim으로 구분. 수동 선언은 스냅샷에 넣지 않고 Tyr의 ReviewDecision으로만 남김 |
| UnresolvedItem | Mimir wire | issueId/code, 노드/필드/edge/원문 위치, 미지원·누락·모호성·제품 동작 미확정 사유, 영향 endpoint, 검토 상태/필요 근거. 모르는 부분은 opaque payload와 원문으로 유지 |
| ReviewDecision | Tyr editor | snapshot/claim/issue/closure pin, 판단·수정 제안·담당자·사유·시각·previousDecisionHash·evidenceRefs. 불변 추가 이력. 로컬 선언은 인증/암호학적 승인 아님 |
| EndpointAssessment | Tyr editor | 선택한 최종 태그/객체/프로퍼티 pin, 의존 closure와 completeness, 차원별 판정, blocker·확인 조건·손실, 기준/규칙/검증 scope. 단일 성공 플래그나 신뢰 점수로 축소 금지 |
| ConversionPlan | Tyr editor | assessment/closure/profile/결정/목적지 workspace revision+hash pin, native→canonical 대응, 생성할 기존 계약 문서·근거·가정, 손실·미지원 동작·불변 validation 결과·plan hash. 적용은 별도 명시 동작 |

전환 목적지를 세분화하는 추가 논리 문서는 다음과 같다. 기존 semantic-definition/source/graph/template 스키마를 대체하거나 소급 수정하지 않는다.

| 추가 모델 | 책임 |
|---|---|
| SemanticContextContract | 기존 의미 정의 pin에 소비 객체·업무 식별/작업/기간/수량 범주·코드 사전·유효성·확인 근거를 연결. 단위/타입 signature 밖의 의미 제약 |
| GenerationContract | 목적지 의미 계약 pin, 기존 source/graph/mapping/record/template 참조·역할/상수·선택/조건/시간/오류 정책과 적합성 근거. 기존에 표현할 수 없는 연산/상태는 unsupported |

ConversionPlan은 native→의미 계약과 native→생성 계약 대응을 각각 고정한다. 의미 확인 상태와 생성 규칙 표현/동등성 상태를 따로 유지하며 어느 하나의 PASS로 다른 쪽을 확정하지 않는다. 상세 혼합 사례와 버전/변경 규칙은 위 경계 문서를 따른다.

evidenceBasis는 다음을 구분한다. 앞의 둘은 **Mimir만**, 뒤의 둘은 **Tyr만** 붙일 수 있으며, 반대편 값이 들어온 문서는 거부한다.

- observed-in-artifact: 실제 확보한 파일/화면에 명시된 값. 이것만으로 runtime 확인이 되지 않는다.
- derived-by-rule: 고정한 제품 규칙·입력 claim으로 도출. 기본값·상속·override 우선순위도 여기에 기록하며 제품 근거가 없으면 unknown이다.
- declared-by-reviewer: 담당자가 명시한 문맥·보정. 원문과 독립 보존하며 파서 사실로 위장하지 않는다.
- verified-by-virtual-case: 입력·기대값·관측 출력·fixture/harness 버전을 고정한 검증 근거. 시험 범위 안에서만 성립한다.

비밀번호/인증서 키 등 비밀 값은 공통 모델·대조표·제출본에 복사하지 않고 설정 존재/비식별 참조만 표현한다. 원본은 승인된 로컬 보관 범위를 따른다. 비식별 사본은 원본과 별도 hash/artifact로 만들고 삭제한 필드의 범위를 기록한다. 비식별 사본의 byte 보존을 원본 전체 byte 보존으로 표시하지 않는다.

## 5 최종 태그의 참조 closure

시작 endpoint는 최종 태그뿐 아니라 객체/배열 프로퍼티도 선택할 수 있다. 값 의존 참조와 적용되는 타입·디코딩·변환·선택·상속·공통 정책을 따라 유한 closure를 만든다. 기본값/상속 우선순위를 알 수 없거나 누락 파일/외부 코드에 의존하면 incomplete다. 제공 export의 외부 적용 코드 존재 여부 자체가 확인되지 않은 경우에도 captureScope=unknown/partial로 남긴다. **해결된 edge가 없다는 이유로 완전하다고 판정하지 않는다.**

평가 의존 순환은 차단한다. contains/문서 cross-link 등 비평가 참조의 정상 순환은 별도 분류한다. 상태 피드백·이전 값 유지·timer 등은 DAG에서 지우지 않고 stateful/unsupported로 보존하여 전환을 차단한다. 읽기·쓰기·event/action 의존성도 구분해 보존하며 실행하지 않는다.

조회 종료는 (a) 입력 leaf 및 적용 규칙/정책이 모두 근거와 함께 해석됨 또는 (b) 미확정 의존성이 위치/사유/영향 endpoint와 함께 드러남이다. 자료 전체의 불명 영역과 선택 endpoint의 영향 범위를 모두 표시한다. closure 밖 미해석 항목은 보존하고 범위 밖이라고 설명하되 현재 import/Bifrost의 전역 차단 규칙을 해제하는 근거로 사용하지 않는다.

안정된 ID는 bundle namespace+제품 native ID/명시 key를 우선한다. 행 번호·표시 이름만으로 개정 간 동일성을 확정하지 않는다. ID 없는 이동/rename·중복 후보는 명시적 대응 결정을 요구한다. 같은 파일 해석 재실행의 결정성과 서로 다른 개정의 동일성은 별도 검사한다.

## 6 제품별 해석기 계약 (Mimir 구현)

공통 계약은 문법 parser를 강제 통일하지 않는다. 각 해석기는 같은 입출력·실행 제한을 지킨다.

**입력 InterpretRequest**: requestId, bundle의 불변 manifest/artifact bytes pin, 명시적 productHint/versionHint와 근거, 선택한 profile pin, 제공된 논리 문맥. endpoint 필터는 결과 조회 범위를 좁힐 뿐 전체 입력의 누락/진단을 숨기지 않는다. 입력은 파일 세트이며 접속 문자열로 파일을 추가 취득하지 않는다.

**출력 InterpretResult**: accepted-for-interpretation 또는 unsupported-profile/invalid-input/limit-exceeded, snapshot pin, 노드/edge/claim/issue 목록, capture/parse coverage와 진단. 결과는 원본의 생성/갱신/읽기 동작을 실행할 권한이 아니다. 동일 입력+profile+문맥에는 동일 의미 결과를 내며 생성 시각/requestId는 의미 digest 바깥 envelope에 둔다. 부분 읽기 성공은 전체 해석 성공이 아니다.

| 경계 | 제품 해석기 | 공통 수용·전환 계층 |
|---|---|---|
| 파일 문법·원문 위치 | 제품별 구조와 native ID 보존 | artifact pin/locator 완전성·한도 검증 |
| native 참조·기본값·상속 | 근거가 있는 규칙으로 해석하고 claim/edge 반환 | 누락/모호성/closure/순환 및 근거 의존성 검사 |
| 타입·주소·연산 | 원문 및 제품 해석 결과를 함께 반환 | 기존 source/graph 등의 표현 가능성 검사 |
| 최종 의미 | 이름/설명을 관측으로만 반환 | 설비·측정 문맥·의미 URI를 담당자가 명시 연결 |
| 채택·승인 | workspace/registry 쓰기 금지 | plan·CAS·검토 후 명시 채택; Bifrost 승인 별도 |

PIO와 Kepware는 독립 profile과 규칙 집합을 갖는다. 한 제품의 태그를 다른 제품과 이름만 맞춰 공통 문법으로 바꾸지 않는다. 해석기는 Mimir 안에 둔다. Tyr와 Bifrost는 InterpretResult를 발행된 파일로만 받으며 해석기를 호출하거나 코드로 의존하지 않는다. 타 앱과 공유 라이브러리를 만들지 않는다.

해석기는 제공된 bytes와 고정된 로컬 규칙만 읽는다. 네트워크·PLC·OPC browse·외부 SQL·COM/ActiveX 객체 생성·제품 서비스 시작·사용자 스크립트·매크로·플러그인 실행 금지. 외부 참조는 진단으로 반환한다. archive path traversal·과도한 압축/참조 깊이·객체 수를 제한하고 임의 파일시스템 탐색을 하지 않는다.

## 7 전환 판정과 채택

EndpointAssessment는 아래 축을 독립 보존한다. 각 축에는 상태뿐 아니라 근거와 blocker가 필요하다.

| 축 | 상태 예시 | 의미 |
|---|---|---|
| 자료 확보 | unknown / partial / declared-complete | 제공된 자료 범위. complete 선언도 runtime 일치 증명 아님 |
| 구조 해석 | complete / partial / unsupported | 필요한 참조·타입·정책을 설명할 수 있는 범위 |
| 계약 표현 | representable / conditional / lossy / unsupported | 기존 Tyr 계약으로 나타낼 수 있는 범위 |
| 가상 동등성 | not-tested / passed-within-scope / failed | 명시한 입력과 oracle에 대한 결과 비교 |
| 의미 확인 | unconfirmed / reviewer-confirmed / disputed | 설비·속성·단위·측정 문맥에 대한 선언 |
| 승인·운영 확인 | 별도 상태 참조 | Bifrost 검증/승인/발행 및 실제 운영 확인을 각각 표시 |

태그 예: 접근과 ×0.1 변환은 해석됐지만 외부 보정 함수가 미확보라면 구조 partial, 최종값 전환 blocked다. 입력 leaf를 관측/초안으로 보존할 수는 있으나 최종 태그 전환 성공으로 표시하지 않는다. 공통 IR에 표현 가능한 연산이어도 현재 Tyr evaluator가 지원하지 않으면 representable이 아니다.

ConvertPlanRequest는 선택 endpoint, 고정된 snapshot/closure, 목적지 설비와 의미 연결, 기존 workspace revision/hash, 명시적 전환 정책을 받는다. 계획은 source/target/graph/mapping/template 등의 기존 계약 후보와 네이티브→정준 대응, 적용할 타입/단위/순서, 미해석/손실을 반환한다. payload 삭제·부족한 정책의 임의 기본값·불명 타입을 Double로 치환하는 전환은 금지한다.

전환 가능 초안 채택과 최종 제출 가능은 별도다. scope가 unknown/partial이면 불완전 경고를 유지하고 최종값의 동등성 확인을 주장하지 않는다. 해석 완료·계약 표현 가능, 미해결 blocker 없음, 필요한 의미 확인, 고정된 검증 범위를 갖춘 경우에만 최종 전환 제출 후보가 된다. 손실/조건부 상태를 검토자 메모 하나로 통과시키지 않는다. 제품 동작을 충실히 옮기는 대신 정책을 바꾼다면 별도 신규 설계·변경으로 기록하고 동등 마이그레이션으로 분류하지 않는다.

리뷰의 보류/의도된 예외/수정 필요/다른 항목/근거 추가는 해석 사실을 덮어쓰지 않는다. 새 자료·parser/rule·기본값·참조 해석·의미 변경은 영향을 받는 closure/claim/plan/preview를 stale로 만든다. 무관한 변경의 판단을 유지하려면 근거 pin과 동일성 확인이 필요하다.

## 8 화면과 반환 산출물

1. 자료 준비: **기존 설정에서 정의서 만들기 / 문서·설정 대조 / 이전 설정과 비교 / 이어하기**. 설정 단독 시작 가능. 제품·버전 미확인/제공 범위를 명시하고 접속 정보 입력을 요구하지 않는다.
2. 객체 선택: 원래 제품 계층의 최종 태그·객체를 탐색하고 생성 과정 요약·의존 개수·확보/미해석 범위를 표시한다. 공통 의미 선택은 별도다.
3. 연결: 왼쪽 원래 구성, 가운데 공통 해석과 참조/원문 위치, 오른쪽 기존 Tyr 전환 후보를 대조한다. 평면 표는 leaf 상세 보기로 유지하며 복합 구조를 잃지 않는다.
4. 검증: 주소 차이만이 아니라 타입·워드 조합·변환 순서·선택/기본값·시간/품질·상태 정책 차이와 그 근거를 보여 준다. 미해석 스크립트는 실행 버튼 없이 보존한다. 입력을 고정한 단계별 가상 trace와 독립 정답 비교를 사용한다.
5. 검토·제출: 영향 endpoint별 쟁점만 검토하고 보류·추가 근거·담당자 결정을 저장한다. 변경된 closure만 재검토하되 전체 자료의 미해석 현황도 표시한다. Bifrost 제출/승인/발행은 별도 상태다.

첫 반환은 **설정 기반 데이터 정의서**와 엑셀 대조표다. 요약/최종 태그 생성 과정/입력·참조/쟁점·미해석/전환 판정/판단 이력 시트를 계획한다. 모든 행은 endpoint·issue ID·원본 locator·snapshot/규칙 pin을 가진다. 화면·엑셀·계약 JSON은 같은 assessment의 투영이어야 한다. 엑셀 의견 재가져오기는 후속으로 분리하고, 설정 파일 자동 생성/덮어쓰기는 포함하지 않는다.

## 9 저장·버전·Bifrost 호환성

**이번 변경은 문서만이며 DB·Schema·코드·fixture를 바꾸지 않는다.** 기존 workspaceVersion2.0과 imports2.6/2.14, 모든 기존 API·proposal builder·Bifrost 계약을 그대로 둔다. 현재 workspace validator는 허용된 컬렉션 외 필드를 거부하므로 임의 interpretation 필드를 추가하지 않는다.

원본 bytes는 기본적으로 Tyr로 넘기지 않는다. 스냅샷 패키지는 manifest와 hash만 담고, 원문 위치 표시에 필요한 원본은 비밀 값을 제거한 비식별 사본을 별도 artifact로 선택해 받는다. 비식별 사본의 보존을 원본 전체 보존으로 표시하지 않는다(§4).

첫 저장 구현은 opt-in **별도 sidecar SQLite** `<workspace-stem>.interpretations.sqlite3`를 계획한다. Mimir에서 **수신한** SourceBundle manifest/snapshot과 Tyr의 decision/assessment/plan 및 안전한 locator 인덱스를 이 DB에 보관하며(가져올 때 hash·pin을 재검증한다) workspace 식별/당시 revision·hash와 결합한다. sidecar 내부 table/schema 버전은 A/B에서 확정한다. 기존 SQLite를 여는 것만으로 파일 생성·DDL·body/revision 변경을 하지 않는다. 사용자가 기능을 시작할 때 생성하고 구 편집기는 sidecar를 읽거나 삭제하지 않는다. 새 sidecar 버전도 명시 migration/backup/CAS를 사용한다.

sidecar 읽기/실패가 기존 작성 기능을 막지 않는다. 원본/관측은 불변이며 결정은 추가 이력, 인덱스는 재생성 가능하다. 메모리 preview와 승인 증거를 섞지 않는다. snapshot·검토·전환 plan은 각각 revision/hash를 재검사한다.

채택 시 기존 workspace의 완전한 정의·필요 원본/근거를 **기존 저장 트랜잭션 안으로 복제·고정**한다. sidecar의 mutable 참조만 남기지 않는다. 두 DB의 분산 원자성을 주장하지 않는다. workspace CAS commit을 채택의 권위로 삼고 plan token/결과 ID·digest로 sidecar receipt를 복구·재조정한다. 중단 후 재시도는 중복 생성하지 않고 실제 workspace 결과를 확인한다. 손상·누락 sidecar로부터 원본을 재발명하지 않는다.

현재 계약은 새 interpretation 문서를 지원하지 않는다. 따라서 기존 2.6 importRef/수동 선언으로 위장하여 Bifrost에 내보내지 않는다. **새 해석 기반 채택·제출은 A의 editor 계약과 D의 wire/gate 근거 closure 검증이 준비되기 전까지 차단**한다. 기존 작성 경로의 제출은 영향 없이 유지한다. 향후 wire는 Mimir 스냅샷 digest·원본 manifest/profile/해석·결정/closure/전환 대응/정준 후보를 고정하고 Bifrost가 참조·무결성·지원 규칙·미해석·손실·기존 타입/의미 계약을 독립 검증하도록 opt-in 확장한다. 타 앱 parser 코드 의존을 만들지 않으며 unsupported 제품 규칙은 fail-closed다.

해석 결과가 형식 검증을 통과해도 원래 제품 동작과 동일하다는 보증은 아니다. 승인 근거에는 가상 oracle의 출처·시험 범위·미확인 운영 범위를 보존한다. 자료 전체 또는 무관한 미해석을 제외한 제출 scope 정책은 새 수신 계약으로 명시·검증해야 하며 현재 전역 차단 기준을 느슨하게 만들지 않는다.

## 10 가상 fixture 계획과 수용 기준

아래는 **작성 예정인 독립 fixture 명세**다. 현재 실행/통과한 fixture가 아니다. synthetic-pio-like와 synthetic-kepware-like는 공통 모델 테스트용 가상 프로파일이며 실제 제품 export와 파일명/문법이 같다고 주장하지 않는다. `fixtures/solution-intake/` 아래 synthetic 입력·기대 native graph/closure·판정·전환 대응·가상 기대 출력·manifest를 별도로 둘 계획이다. oracle은 시험 대상 parser 출력으로 생성하지 않는다.

| ID | 가상 사례 | 기대 결과 |
|---|---|---|
| SI01 | 문서 없는 설정 단독 | 자료 보존·정의서 생성 가능; 미기재 단위/의미/운영 일치는 미확인 |
| SI02 | 서로 다른 두 가상 형식이 같은 정의를 표현 | native ID/원문을 유지하고 동등한 입력·변환 후보로 수렴; 의미 병합은 명시 결정 |
| SI03 | 같은 이름·다른 설비/측정 문맥 | 별도 endpoint 유지·자동 병합 없음 |
| SI04 | 분산 주소 객체/low-high 조합/배열 요소 | 구조·순서·범위·각 입력 근거 보존, 독립 가상 값 일치 |
| SI05 | 다단 태그 참조·상속·override·공통 정책 | 전이 closure·적용 규칙·기본값 근거 재현, 정책 변경 시 종속 판단 stale |
| SI06 | 누락 파일·외부 코드·모호한 참조·unknown scope | 원문/후보/필요 자료 유지·최종 전환 차단; 정상 leaf만으로 complete 판정 금지 |
| SI07 | 평가 순환 vs 비평가 문서 순환 | 평가 순환 차단; 비평가 순환은 보존·유한 조회 |
| SI08 | selector·기본값·이전 값 유지·timer/스크립트 | 지원 선택은 명시적으로 전환; 미지원 상태/코드는 opaque·차단·실행0 |
| SI09 | raw/공학값·단위·스케일·cast/overflow 차이 | 변환 순서·이중 변환·손실 판정·경계값 oracle; 단위 변환 후 동등한 경우도 구별 |
| SI10 | XML/JSON/바이너리 opaque·알 수 없는 옵션 | byte/hash·필드 위치/미해석 보존; 지원하지 않는 컨테이너는 임의 디코딩 없이 거부/진단 |
| SI11 | 개정 파일·stable ID/rename/순서·주소/정책 변경 | 근거 동일 판단 유지, 영향 closure만 재검토, 모호한 rename은 명시 대응, 삭제 자동 적용 없음 |
| SI12 | 원본·profile·locator·edge·plan 변조 | hash/참조 검증 거부; 동일 입력 재해석 결정성·새 rule은 새 snapshot |
| SI13 | 화면·대조표·계약 보고서 | 같은 ID/pin·쟁점·부분 판정·변환 손실, 미확인 내용을 정답으로 출력하지 않음 |
| SI14 | sidecar 없음/구버전·기존 DB 재개방·CAS | legacy body/revision/기존 시나리오/제출 보존; 구 API 동작 유지 |
| SI15 | plan 후 변경·중단/재시도·sidecar 손상 | stale 거부·중복 채택 없음·workspace commit에서 receipt 복구; 준비 전 신규 제출 차단 |
| SI16 | 출처·의미 근거·가상 oracle/승인 상태 | 수동 선언/가상 확인/runtime 확인/서명 승인 구분; 이름만으로 의미 확정 금지 |
| SI17 | 네트워크/실행 차단·공격적 파일·비밀 값 | OS 격리에서 정상 조회, 장치/SQL/COM/수식 실행0, 한도 거부·안전 경로·보고서 비밀 유출 없음 |
| SI18 | 신규 wire 수신/Bifrost seam | 새 계약 지원 전 거부, 지원 후 closure/정준 후보 독립 검증; 기존 제안/서명 승인/발행 회귀 유지 |

**소유 분리:** SI06·SI07·SI10과 SI12의 결정성 부분, SI17의 공격 파일 부분은 해석기 시험이므로 **Mimir 시험**으로 옮긴다. Tyr에는 고정된 스냅샷 fixture를 소비하는 쪽 시험이 남는다. Tyr 쪽에 다음을 추가한다.

| ID | 가상 사례 | 기대 결과 |
|---|---|---|
| SI19 | 스냅샷 pin 변조·알 수 없는 스냅샷 schema 버전·evidenceBasis 소유 위반 | Tyr가 가져오기를 거부하고 기존 sidecar/작성본을 바꾸지 않음 |

SI02의 의미 수렴 정답은 시험 작성자가 독립 선언하고, SI09의 제품 동작 oracle은 가상 프로파일 규칙에 한정한다. synthetic passed가 vendor supported를 의미하지 않는다. 상태·참조 정책을 모르면 테스트 기대값도 unknown/block로 둔다.

## 11 실제 제품 자료와 현장 PoV

| 대상 | 현재 근거/상태 | 실제 지원 확정에 필요한 자료 | 자료 없이 가능한 일 |
|---|---|---|---|
| BEAN PIO | 공개 소개의 Memory Map·PIO Connector 구성만 확인; 버전/실제 파일 미확보 | 허가된 설정/백업 세트·제품/driver 버전·오프라인 화면/항목 대응·복합 예제·기본값/참조 근거 | 공통 모델과 synthetic-pio-like fixture 검증 |
| BEAN TAG MANAGER | 사용자 확인 제품명. 공개 TM Core/TM Connector와의 정확한 관계 미확정 | 정확한 제품명/버전·파일/화면·PIO와의 데이터 연결·외부 코드 범위 | 별도 native 구조 가상 사례; TM Connector와 동일시 금지 |
| Kepware | 대상 제품군 선정; 구체 제품/버전/driver/원본 형식·범위 미확보 | 허가된 프로젝트/export와 필요한 보조 자료·버전/driver·태그/공통 설정/참조/변환의 실제 근거 | 공통 모델과 synthetic-kepware-like fixture 검증 |
| 현장 의미·도입 효과 | 실자료 PoV 미수행 | 설비·측정 문맥 정답, 담당자 확인, 사용성·작성/검토 시간·오경고 비용 | 가상 과제와 측정 양식 준비 |

Kepware라는 이름만으로 특정 파일 확장자나 전체 설정 export 가능성을 확정하지 않는다. 태그 목록만 확보되면 그 범위를 기록하고 나머지 구성은 미확정으로 남긴다. 제조사 협조는 선행 의존성이 아니다. 현장에서 허가된 복사본·인수인계 자료·격리된 시험 프로젝트를 사용할 수 있다. 한 항목씩 바꾼 전후 비교는 오프라인 시험 사본에서만 수행하며 구조 가설/독립 재검증/가상 결과를 구분한다.

실제품 PoV는 단순 태그와 복합 태그 각각에서 최종 endpoint의 의존 범위를 끝까지 추적하고, 미확정 부분을 보존하는지 검증한다. 운영 설정이 최신인지 확인하는 절차·실장치 값 동등성은 별도 현장 범위이며 이번 완료 조건이 아니다. 실자료가 없어도 A~D의 합성 수용은 진행하되 제품 지원 배지는 켜지 않는다.

공개 조사 근거는 [BEAN PIO 소개](https://beancorp.com/pro-pio.html), [TM Expression 소개](https://beancorp.com/pro-tm.html), [공식 자료실](https://beancorp.com/down.html), [FAQ](https://beancorp.com/faq.html)다. 소개/문의 경로가 파일 문법·동작의 기술 명세를 대신하지 않는다. 본 문서에는 확보하지 못한 제품 파일 구조를 예제로 발명하지 않는다.

## 12 구현 순서와 종료 조건

P4-F A1 Mimir 해석 스냅샷 wire 계약 → A2 Tyr editor 계약·참조/판정 fixture → B sidecar·의존 조회·쟁점 검토·대조표 → C 제한 전환·기존 가상 preview·재검토 → D Bifrost opt-in 근거 계약·독립 검증/승인 회귀 순으로 진행한다. 제품별 자료 조사 E는 병행 가능하며 실제 parser/지원 판정은 자료 확보 이후다. **E의 해석기 구현은 Mimir 작업이다.** 현장 PoV F는 합성 수용과 별도다. 세부 미완료 체크는 [MVP 계획](../MVP-PLAN.md)의 P4-F에 둔다.

A는 의미 문맥/생성 계약·적합성 경계를 함께 구체화하고, B는 두 계약과 원문/쟁점/근거의 조회·저장·보고서를 구현한다. C는 제한 조건·레코드 문맥/상수 역할·변경 판정과 MG01~MG07의 합성 수용을 진행하며 미지원 상태 동작은 차단한다. D는 두 계약/전환 대응·의미 근거의 수신 검증과 MG08을 추가한다. 혼합 템플릿 전체 예제는 일반 if 등의 계약이 준비되기 전 실행 지원으로 표시하지 않는다.

공통 단계 완료는 SI01~SI18 중 단계별 기준 통과와 화면/저장/반환 경로의 직접 검증으로 판정한다. 실제 제품 형식 지원은 별도 profile별 근거 목록·제한·독립 시험이 있어야 한다. 새 해석 기반 채택/제출은 D까지 준비되기 전 완료로 표시하지 않는다. 기존 구현의 P0~P7 완료 기록을 소급 변경하거나 새 기능 구현 완료로 확대하지 않는다.
