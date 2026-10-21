# P0·P1 정준 모델 검증 기준

이 문서는 P0·P1의 완료 판정 기준이다. 실제 장치 통신, 펌웨어·드라이버 인증, 실시간 수집 성공은 완료 조건에 포함하지 않는다. 문서·설정·수동 선언을 일관된 계약으로 관리하고 상위 거버넌스가 해석할 수 있는지 검증한다.

## 정준화의 단위

- 접근 정의는 PLC별 구체적 표현을 보존한다. D1000, DB10 byte 20, Logix 심볼, OPC UA NodeId를 서로 치환하지 않는다.
- 개념 식별은 semanticId다. role·결과 타입·단위는 해당 ID의 정준 표현을 제약한다. 같은 ID에서 이들이 충돌하면 semantic.identity-conflict다. 단위가 다른 표현을 사용하려면 변환 후 동일 정준 단위에 맞춘다.
- 의미 ID가 같아도 설비 인스턴스는 별개다. 개념 재사용과 개별 관측의 동일성을 구분한다. 실제 관측 문맥은 equipmentInstanceId와 개념·멤버 연결에 남긴다.
- name은 표시 이름이다. 이름·주소·수치의 일치만으로 의미를 추론하거나 병합하지 않는다. 같은 이름의 실제 속도와 목표 속도는 별도 의미 ID와 role로 공존한다.
- 의미 ID는 근거와 검토를 바탕으로 작성자가 부여한다. 이 게이트는 선언의 일관성을 검증하며, 물리적 측정 위치나 업무 의미를 자동으로 증명하지 않는다. 정의가 애매하면 초안/재검토로 남긴다.

## 수용 기준과 실행 증거

| ID | 판정 기준 | 실행 증거 |
|---|---|---|
| G01 수렴 | 네 이질 접근 정의가 동일한 의미·단위·결과 타입으로 정규화되고 독립 기준값 1234.5 rpm에 도달 | canonical:speed-a~d, four-way-convergence |
| G02 구분 | 같은 표시 이름의 다른 개념·role은 별개, 설비 인스턴스도 보존 | coexisting-same-label-different-meaning, equipment-instances-preserved |
| G03 충돌 | 동일 semanticId의 role·단위·타입 불일치를 검출 | semantic-id-conflicting-role, same-id-* / result-type-change |
| G04 수치 손실 | Int64→Double 정밀도, 정수 반올림, overflow를 감지. exact는 손실 시 결과 거부 | loss:* |
| G05 투영 손실 | legacy UDT 부분집합 생성 시 누락되는 접근·원시 표현·변환·단위·역할·근거를 명시 | projection:loss-inventory, legacy-is-not-full-contract |
| G06 변경 | 의미·단위·role·타입, 스케일, 디코딩, 주소, 문맥, 범위, 근거 변경을 분류하고 재검토 필요 표시 | governance:* 및 changeAssessments |
| G07 표시 변경 | 이름만 바꾸면 의미는 유지하고 presentation으로 분류 | rename-preserves-meaning |
| G08 무결성 | 참조 고정, 내용 해시, 검토 대상 해시, 잘못된 정의의 거부를 유지 | 기존 package/schema/review gate |
| G09 비접속 | socket 차단 상태로 전체 게이트 통과 | --deny-network |

fixtures/governance-cases.json에 입력·기준값·예상 분류·예상 손실을 명시한다. scripts/governance_checks.py가 실제 패키지 정의를 해석해 평가한다. fixture 기대값을 정규화 결과로 재생성하지 않는다. 같은 출력 숫자만으로 수렴을 판정하지 않고 의미 선언까지 대조한다.

수치 평가는 계약 검증을 위한 제한된 실행 하네스다. 네 기본 표현, linear/cast, bit-select/enum-map 일부를 지원한다. 일반 제품 preview 엔진의 완성을 의미하지 않는다. 시험하지 않은 연산 조합의 정확성을 주장하지 않는다.

## 변경과 승인 계약

meaning 변경(semanticId·role·단위·결과 타입), constraint, transform, decode, access, context, evidence, reference, binding 변경은 재검토가 필요하다. presentation은 의미 변경과 분리한다. 이 분류는 오프라인 비교 결과이고 실제 승인 상태 전이를 수행하지 않는다.

기존 review-record는 개별 문서 해시를 고정한다. 소스·의미 변경으로 매핑의 의존성이 바뀐 경우에는 매핑 문서 해시가 그대로여도 변경 비교 결과에 따라 재검토해야 한다. P6에서는 전체 proposal/의존성 해시와 검토를 결합한다. 현재 개별 review 해시만으로 전이적 승인을 주장하지 않는다.

내용 변경은 문서 version을 올린다. 비교 fixture는 변화 검출을 격리하기 위해 메모리에서 한 필드를 수정하며 제출용 개정 패키지나 자동 승인 예제가 아니다. 동일 의미 ID에 다른 정준 단위·role·타입을 부여하려면 동일 ID의 호환 개정으로 처리하지 않고 새 의미 정의와 명시적인 이행 검토가 필요하다.

## 손실 보고와 소비 경계

governance-assessment는 proposalSha256, 정준 binding, 표본 수치 결과, projectionLosses, changeAssessments를 가진다. 승인·release가 아닌 검증용 진단 계약이며 proposal.files에 넣지 않는다. 분석한 proposal의 바이트 해시로 범위를 고정한다. P1 검토용 1.0.0에 새 문서 종류를 추가했으며 기존 문서 형식은 변경하지 않았다. 외부 발행 기준본이 확정된 뒤의 변경은 별도 계약 버전으로 관리한다.

legacy 투영은 member의 name/type/semanticId/range만 만드는 명시적 부분집합 하네스다. 실제 Bifrost 어댑터 실행 결과로 표시하지 않는다. 보고하는 필드 목록은 fixture에서 검증하며 이 투영으로 원래 계약을 복원할 수 있다고 주장하지 않는다. 생략된 버전·문맥·검토까지 포함하는 전체 거버넌스 묶음은 원본 proposal과 정의 파일을 유지해야 한다.

소비자는 정준 의미·설비 인스턴스를 사용하고 PLC별 접근 문자열을 업무 의미의 키로 사용하지 않는다. Týr는 작성·비교·제안, Bifrost는 후속 검증·승인·발행, Mímir는 후보 제공, Muninn은 후속 승인 계약 소비를 담당한다. 앱 간 공유 코드가 없다.

## 완료 범위

P0: 핵심 가설, 네 접근 표현, 의미 식별·충돌·손실·변경 정책, 역할·재사용 경계를 문서화하면 완료다.

P1: G01~G09와 기존 형식·참조 회귀 게이트를 통과하고 입력·스키마·검증기 해시와 결과를 저장하면 완료다.

현장 원본·솔루션 버전·검토자 확보는 P4/P7의 대표성·실무 유용성 검증을 강화한다. 이는 P0·P1의 미완료 사유가 아니다. 실제 장치 통신은 이번 MVP 완료 조건에서 제외한다. UI·importer·Bifrost 실제 승인 연계는 각 후속 단계의 완료 조건으로 유지한다.
