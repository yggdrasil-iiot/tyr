# 매핑 패턴 fixture

이 디렉터리는 현재 제품 wire bundle이 아닌 오프라인 시험 명세다. fixtureSpecVersion 1.0.0은 제품 schemaVersion과 무관하다. 네 PLC 자료와 planned 사례는 모두 가상 자료다. 실제 장치 접근은 없다.

- matrix.json: 18개 패턴의 다섯 지원 축·우선순위·근거·코드 위치·56개 사례 목록.
- case.schema.json: 사례 envelope 검증. input/expect는 시나리오 자료이며 미래 wire 필드로 확정된 것이 아니다.
- current 14개: 실제 현재 구현 경로를 호출한다.
- gap-probe 8개: 현재 한계 재현이다. 거부/누락 재현이 성공해도 해당 기능 지원을 뜻하지 않는다.
- planned 34개: 명세 envelope 검증만 하고 결과는 pending. 구현 결과와 비교하지 않으며 통과 수에 포함하지 않는다.

## 실행

python scripts/validate_pattern_matrix.py --deny-network --report docs/verification/pattern-matrix-validation.json

러너는 임시 파일 bundle만 사용하고 서버를 띄우거나 사용자 SQLite DB를 열지 않는다. socket 생성은 차단한다. 보고서는 코드·계약·입력 해시와 currentChecks/gapProbes/planned를 분리한다. 계획 항목을 구현할 때 action, runner, oracle, 저장/UI 검증 근거와 매트릭스를 함께 변경한다. 조건 없는 xfail/skip을 pass로 승격하지 않는다.

## 사례 목록

| ID | 패턴 | 모드 | 입력과 기대 결과 |
|---|---|---|---|
| [direct-four-profiles](cases/direct-four-profiles.json) | MP01 | current | JSON의 input/expect 참조 |
| [dispersed-motor](cases/dispersed-motor.json) | MP02 | current | JSON의 input/expect 참조 |
| [aliases-and-collisions](cases/aliases-and-collisions.json) | MP02 | current | JSON의 input/expect 참조 |
| [partial-object](cases/partial-object.json) | MP02 | current | JSON의 input/expect 참조 |
| [u32-low-first](cases/u32-low-first.json) | MP07 | current | JSON의 input/expect 참조 |
| [u32-high-first](cases/u32-high-first.json) | MP07 | current | JSON의 input/expect 참조 |
| [word-fanout](cases/word-fanout.json) | MP08 | current | JSON의 input/expect 참조 |
| [enum-unknown](cases/enum-unknown.json) | MP08 | current | JSON의 input/expect 참조 |
| [unit-rps-rpm](cases/unit-rps-rpm.json) | MP10 | current | JSON의 input/expect 참조 |
| [unit-millitorque](cases/unit-millitorque.json) | MP10 | current | JSON의 input/expect 참조 |
| [unit-kelvin](cases/unit-kelvin.json) | MP10 | current | JSON의 input/expect 참조 |
| [missing-unit-conversion](cases/missing-unit-conversion.json) | MP10 | current | JSON의 input/expect 참조 |
| [observation-opaque-expression](cases/observation-opaque-expression.json) | MP18 | current | JSON의 input/expect 참조 |
| [legacy-projection-loss](cases/legacy-projection-loss.json) | MP18 | current | JSON의 input/expect 참조 |
| [multi-input-rejected](cases/multi-input-rejected.json) | MP11 | gap-probe | JSON의 input/expect 참조 |
| [structure-rejected](cases/structure-rejected.json) | MP04 | gap-probe | JSON의 input/expect 참조 |
| [array-rejected](cases/array-rejected.json) | MP06 | gap-probe | JSON의 input/expect 참조 |
| [raw-string-rejected](cases/raw-string-rejected.json) | MP09 | gap-probe | JSON의 input/expect 참조 |
| [native-bit-unit-rejected](cases/native-bit-unit-rejected.json) | MP08 | gap-probe | JSON의 input/expect 참조 |
| [native-area-unchecked](cases/native-area-unchecked.json) | MP08 | gap-probe | JSON의 input/expect 참조 |
| [alias-cycle-unchecked](cases/alias-cycle-unchecked.json) | MP12 | gap-probe | JSON의 input/expect 참조 |
| [two-objects-one-equipment](cases/two-objects-one-equipment.json) | MP17 | gap-probe | JSON의 input/expect 참조 |
| [template-base-stride](cases/template-base-stride.json) | MP03 | planned | JSON의 input/expect 참조 |
| [template-instance-override](cases/template-instance-override.json) | MP03 | planned | JSON의 input/expect 참조 |
| [template-missing-parameter](cases/template-missing-parameter.json) | MP03 | planned | JSON의 input/expect 참조 |
| [native-structure-select](cases/native-structure-select.json) | MP04 | planned | JSON의 input/expect 참조 |
| [nested-object-tree](cases/nested-object-tree.json) | MP05 | planned | JSON의 input/expect 참조 |
| [array-shape-stride](cases/array-shape-stride.json) | MP06 | planned | JSON의 input/expect 참조 |
| [array-out-of-range](cases/array-out-of-range.json) | MP06 | planned | JSON의 input/expect 참조 |
| [array-of-struct-to-objects](cases/array-of-struct-to-objects.json) | MP06 | planned | JSON의 input/expect 참조 |
| [separate-low-high](cases/separate-low-high.json) | MP07 | planned | JSON의 input/expect 참조 |
| [bit-coordinate-system](cases/bit-coordinate-system.json) | MP08 | planned | JSON의 input/expect 참조 |
| [melsec-native-relay](cases/melsec-native-relay.json) | MP08 | planned | JSON의 input/expect 참조 |
| [ascii-fixed-string](cases/ascii-fixed-string.json) | MP09 | planned | JSON의 input/expect 참조 |
| [bcd16-valid](cases/bcd16-valid.json) | MP09 | planned | JSON의 input/expect 참조 |
| [bcd16-invalid](cases/bcd16-invalid.json) | MP09 | planned | JSON의 input/expect 참조 |
| [s7-date-time](cases/s7-date-time.json) | MP09 | planned | JSON의 input/expect 참조 |
| [date-timezone-missing](cases/date-timezone-missing.json) | MP09 | planned | JSON의 input/expect 참조 |
| [sqrt-domain](cases/sqrt-domain.json) | MP10 | planned | JSON의 input/expect 참조 |
| [sqrt-range](cases/sqrt-range.json) | MP10 | planned | JSON의 input/expect 참조 |
| [pressure-difference](cases/pressure-difference.json) | MP11 | planned | JSON의 input/expect 참조 |
| [multi-input-missing](cases/multi-input-missing.json) | MP11 | planned | JSON의 input/expect 참조 |
| [graph-cycle](cases/graph-cycle.json) | MP11 | planned | JSON의 input/expect 참조 |
| [alias-chain](cases/alias-chain.json) | MP12 | planned | JSON의 input/expect 참조 |
| [alias-cycle-rejected](cases/alias-cycle-rejected.json) | MP12 | planned | JSON의 input/expect 참조 |
| [bounded-selector](cases/bounded-selector.json) | MP13 | planned | JSON의 input/expect 참조 |
| [selector-out-of-range](cases/selector-out-of-range.json) | MP13 | planned | JSON의 input/expect 참조 |
| [static-context-and-plc](cases/static-context-and-plc.json) | MP14 | planned | JSON의 input/expect 참조 |
| [external-query-preservation](cases/external-query-preservation.json) | MP14 | planned | JSON의 input/expect 참조 |
| [read-write-definitions](cases/read-write-definitions.json) | MP15 | planned | JSON의 input/expect 참조 |
| [freshness-good](cases/freshness-good.json) | MP16 | planned | JSON의 input/expect 참조 |
| [freshness-stale](cases/freshness-stale.json) | MP16 | planned | JSON의 input/expect 참조 |
| [bad-input-quality](cases/bad-input-quality.json) | MP16 | planned | JSON의 input/expect 참조 |
| [trigger-record](cases/trigger-record.json) | MP16 | planned | JSON의 input/expect 참조 |
| [two-instances-same-equipment](cases/two-instances-same-equipment.json) | MP17 | planned | JSON의 input/expect 참조 |
| [unsupported-roundtrip](cases/unsupported-roundtrip.json) | MP18 | planned | JSON의 input/expect 참조 |

문헌과 현재 제한: [지원 매트릭스](../../docs/MAPPING-SUPPORT-MATRIX.md).

## P3-A 부분 구현 연결

[2.0 파일 계약 fixture](../p3a/README.md)가 separate-low-high, two-instances-same-equipment, graph-cycle의 계약·제한 표본을 검증한다. versionSupport로 1.x/P2와 구분한다. 기존 planned는 전체 제품 기준이며 pending을 유지한다.
