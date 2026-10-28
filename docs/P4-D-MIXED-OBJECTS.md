# P4-D 여러 소스의 정준 객체 매핑

2026-10-18 · 작성/발행 envelope opt-in 2.21.0

## 구현 경계

하나의 target-instance 프로퍼티에 PLC source, 상수, 외부 값, 가상 DB 레코드 필드 또는 기존 값 그래프를 함께 연결한다. 새 혼합 객체 runtime이나 SQL 엔진을 만들지 않는다. 기존2.0 target/memberPath,2.x source/graph/mapping,2.19 template/application과2.20 record-mapping을 재사용한다. Python Tyr (Týr)와 Java Bifrost는 wire 데이터만 공유하며 각자 독립 검증한다. 실제 장치 통신·외부 SQL·쓰기 실행·runtime 활성화는 제외한다.

## 레코드 필드 소스 계약

새 source-definition2.21은 기존 external-value-v1의 read-only typed 형태에 recordField를 추가한다. recordField는 recordMappingRef(id/version/canonical SHA), fieldId, nullPolicy(reject/default), defaultValue를 고정한다. source의 타입·단위·raw/already-engineered·소속 설비는 원본 resultSchema 필드 및 record-mapping과 정확히 일치해야 한다. providerRef/valueKey는 원본 선언에서 파생하고 expressionLanguage=none, expression=null로 고정한다. 원본 record의 query는 비실행 메타데이터로만 closure에 남는다.

필드값은 **선택한 레코드의 원본 필드**이다. 기존 record template의 공학값으로 바꾼 결과를 다시 변환하지 않는다. 새 객체의 mapping/graph가 단위·스케일·최종 cast를 적용한다. source의 inputStage가 이미 공학값이면 기존 이중 변환 검증을 유지한다.

레코드 정의는 object/maxRows1이어야 한다. array 결과에서 임의로 첫 행을 취하지 않는다. 전체 결과에서 선택 또는 복합 키 선택은2.20의 명시적 정책을 따른다.0건은 필드값 자체가 없으므로 원본 객체의 zeroPolicy=null이어도 scalar 필드 해석을 거부한다. 필드 NULL에만 nullable+명시적 default를 적용하며 누락 레코드를 기본값으로 대체하지 않는다.

상위 객체와 DB 필드의 논리 설비가 같아야 한다. 다른 설비의 템플릿 재사용은 기존19 슬롯/소속 설비 계약을 따른다. cross-equipment 주소/결과를 몰래 한 객체에 넣지 않는다. 기존 레코드 정의의 전체 승인·의미 URI 정책도 참조 closure의 일부이며, raw 필드라고 그 정의의 governance를 생략하지 않는다.

새 필드 소스는 선언 ID/version을 수정·삭제·일반 외부 값으로 downgrade하지 못한다. 다른 record 버전/필드/NULL 정책은 새 소스 ID로 작성한다. 자동 ID는 고정 참조·필드·정책으로 결정한다. 템플릿 적용본은 sourceSnapshots에 새 소스와 record pin을 그대로 보존한다. 구 계약·source·SQLite 데이터는 자동 변환하지 않는다.

## 가상 입력과 객체 조립

PLC/외부 값은 기존 bytesHex/typedValue, 상수는 정의값을 사용한다. DB 필드의 입력은 {resultSet: virtual-result-set2.20}이며 임의 scalar 덮어쓰기를 거부한다. 모든 행의 필수 필드·원시 타입·키·중복·미정의 열 정책을 검사한 뒤 선택 결과가 정확히1건인지 확인한다. 선택되지 않은 잘못된 행도 거부한다.

미리보기는 record-field-select trace에 레코드/스키마 pin, 키, 원본 행 번호, 필드, 원본값, default 사용, 입력 SHA, capturedAt/quality, 보존 열을 남긴 뒤 기존 디코딩/graph/단위·스케일/cast 경로를 사용한다. 한 프로퍼티의 오류라도 최종 object result=null, quality=bad이며 진단용 partialResult를 분리한다. 변환 손실·uncertain·명시적 기본값은 경고/품질에 반영한다.

같은 recordMappingRef의 여러 필드는 정확히 같은 가상 result-set SHA를 사용해야 한다. 다른 snapshot을 섞으면 graph 또는 객체 조립에서 snapshot-conflict로 차단한다. 화면21은 같은 pinned record의 입력창 하나를 공유하여 같은 데이터를 여러 번 붙여넣지 않게 한다. 서로 다른 record 정의의 결과는 독립 입력이며 자동 join/broadcast를 하지 않는다.

시간 정책이 있으면 각 source의 기존 DataValue envelope와 평가 시각을 사용한다. DB 입력의 두 시각은 resultSet.capturedAt과 같은 instant이고 quality는 같은 값이어야 하며 임의로 최신 시각/좋은 품질로 바꿀 수 없다. trigger sequence는 이 bounded result-set 입력에서 지원하지 않아 null로 고정한다. freshness/bad/uncertain을 기존 값 매핑 경로로 검증한다. 같은 그래프의 다중 입력에는 skew 정책이 적용되지만 객체의 서로 다른 프로퍼티 전체의 원자성·교차 skew를 보장하지 않는다. 기존 logical-preview의 temporalScope/atomicSnapshot=false를 유지한다. 정책 없는 기존 값 매핑의 의미도 바꾸지 않는다.

## 화면·템플릿·SQLite

21에서 설비·의미 모델을 선택하고 각 프로퍼티의 PLC/DB 필드/상수/외부 값/그래프를 선택한다. 명시적 단위 변환·factor/offset·최종 cast와 optional 시간 정책을 검증한 뒤 신규 DB 필드 소스·공통 템플릿·적용본·생성 target/model/graph/mapping을 기존 workspace CAS 한 트랜잭션으로 저장한다. 저장 전 비교는 읽기 전용이며 입력 변경/오래된 revision/plan 변조를 거부한다. 기존 템플릿의 재적용·명시적 개정은19에서 수행한다.

21에서 객체 전체를 가상 평가하고 프로퍼티별 품질·손실·출처와 단계를 확인한다. DB는 공유 JSON 결과 집합, PLC는 HEX, 외부 값은 typed 입력, 상수는 정의값을 사용한다. 시간 정책이 없는 일반 입력에 시각/품질 편집기를 보여주지 않는다. DB 품질은 입력 자체에서 항상 검증한다.

object-preview-scenario2.21은 전체 targetRef·workspace SHA·입력·평가 시각을 기존 preview_scenarios 테이블/CAS에 별도로 저장한다. workspace revision을 변경하지 않으며 이전 정의의 시나리오는 stale로 표시한다. 기존09의 scalar temporal preview-scenario도2.21로 opt-in하여 resultSet 입력을 저장/재생한다. 구2.3/2.4와 테이블 스키마는 유지하고 종류별 목록을 구분한다. 음성 가상 시나리오도 보존 가능하다. 시나리오는 release 문서가 아니다.

02에서 pinned DB 필드 소스를 일반 external-value로 덮어쓰지 못하도록 읽기 전용으로 안내한다.19는 해당 슬롯에 result-set JSON 입력을 안내하고 시각/품질 검증은09/21에서 수행하도록 표시한다. 기존06/05의 일반 sourceRef와 graph에서도 이 소스를 사용할 수 있다.

## Bifrost 계약과 승인

2.21 proposal은 새 source와 기존 canonical mapping/template/application을 담는다. recordMappingRef의 record 정의·고정 템플릿·element 모델·이력·선언 근거를 참조 closure로 포함한다. 파일/근거 SHA, 슬롯/생성물, 원본 필드 signature, 설비·키/건수 정의, NULL/default, source pin과 registry 이력을 Java가 독립 검증한다. 같은 소스 ID/version을 변경하거나 일반 source로 downgrade한 발행도 registry 이력에서 거부한다. 구 envelope에2.21 source를 넣으면 fail closed다.

기존 두 확인자의 Ed25519 승인·불변 릴리스·복구·의미 URI 폐기 정책을 사용한다. 가상 row/scenario·private key를 bundle에 넣지 않는다. 실제 SQL 조회/PLC 읽기/쓰기/활성화는 수행하지 않는다.

## 합성 수용과 현장 PoV

fixtures/mixed-objects의 기본 객체: PLC D1000의1200×0.1→actual120kPa, DB target950×0.1→target95kPa, 상수 baseline100kPa, 외부 reference101kPa, String 상수 LINE-A. 같은 의미 모델과 기존 템플릿을 사용하며 원본 record 필드950와 최종95를 구분한다. 별도 브라우저 사례는 두 DB 필드를 공유 입력으로 사용하고 Pa→kPa의 Double cast 손실도 표시한다.

계약·키/범위/NULL·품질/시각·동일 snapshot·다중 입력 그래프·템플릿 재사용·실제 SQLite CAS/재개방·독립 Java 서명 승인/발행을 오프라인 검증한다. 결과는 verification/MIXED-OBJECTS-RESULTS.md에 기록한다.

현장 PoV 미완료: 실제 각 소스의 의미/단위/스케일 정답, DB 키 안정성·조회 시점·PLC와의 시간 정합성, provider/vendor export, 소비자 계약, 작업자 편의·검토 시간·실수율. 배열 fan-out/broadcast, 자동 join/집계, cross-equipment 결합, DB native 타입 전체, 운영 커넥터/SQL/쓰기/활성화는 이번 범위가 아니다.
