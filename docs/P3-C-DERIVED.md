# P3-C 다중 입력 파생값

2026-10-17. 작성·저장·정적 검증과 가상 입력 평가만 수행한다. 실제 장치 통신·승인·릴리스는 제외한다.

## 계약과 역할

새 2.2.0 common/source-definition/semantic-definition/value-graph/mapping-set을 추가했다. 기존 1.0/1.1/2.0/2.1 Schema는 변경하지 않는다. target-instance와 mapping-proposal, workspace envelope는 2.0.0을 유지하고 문서별 schemaVersion을 검증한다. 소스·대상·노드 참조는 id/version으로 고정하며 서로 다른 설비의 입력을 혼합하지 않는다.

Tyr (Týr)가 파생 정의와 근거를 작성하고 Mimir (Mímir) 후보를 검토한다. Bifrost의 승인/릴리스, Muninn의 소비·실행 계약은 별도이며 2.2 지원을 가정하지 않는다. 프로젝트 간 코드를 공유하지 않는다.

| 노드 op | 이름 있는 입력 | 구성 | 출력 |
|---|---|---|---|
| subtract | left, right | left − right, 순서 명시 | Decimal / 입력과 같은 단위 |
| linear | value | factor, offset: 정확한 십진 문자열 | Decimal / 입력과 같은 단위 |
| unit-convert | value | from, to: 허용된 변환 쌍 | Decimal / to |
| identity | value | 선언 타입·단위 일치 | 입력 전달 |
| decode-u32-words | low, high | 기존 raw UInt16 조합 | UInt32 |

새 수치 노드는 Decimal을 중간 타입으로 사용한다. semantic 결과 타입은 기존 Double/Int32/Boolean/String을 유지한다. 매핑에 명시적 최종 cast를 넣어 binary64 정밀도·정수 반올림·overflow를 검토한다. 임의 문자열 식, eval, sqrt/clamp, 곱셈·나눗셈으로 새로운 차원을 만드는 식은 지원하지 않는다.

## 단위와 스케일

Pa/kPa/bar를 추가했다. 압력 변환은 Pa↔kPa(1000), bar↔Pa(100000), bar↔kPa(100)이며 방향별 정확한 십진 계수를 사용한다. 기존 1/s→rpm, mN.m→N.m, K→Cel도 유지한다. 허용 목록 밖의 변환은 차단한다.

subtract는 두 입력이 수치이고 같은 known 단위이며 Pa/kPa/bar 또는 무차원 1일 때만 허용한다. 동일한 값 모양이나 이름으로 단위를 추정하지 않는다. Cel/K의 절대 온도 차이는 delta 단위 계약이 필요하므로 이번 범위에서 차단한다. 압력의 게이지/절대 기준·측정 위치가 같은지는 의미 정의와 근거로 검토해야 하며 단위 일치만으로 자동 확정하지 않는다.

raw의 unit은 스케일 후에도 유지되는 물리 단위 선언이다. 정수 1500이 150 kPa를 뜻하면 linear ×0.1로 먼저 정규화한다. linear로 단위를 바꾸지 않으며, bar→kPa는 별도 unit-convert를 사용한다. 이미 공학값인 소스에 직접 중복 스케일을 적용하면 진단한다. 입력별 보정과 결과 후처리는 그래프와 mapping.transform으로 구분해 명시한다.

예: D3000 raw UInt16 150 → ×0.01 → 1.50 bar → ×100 → 150.00 kPa.
D2000 raw UInt16 100 kPa와 subtract → 50.00 kPa Decimal → cast Double → 50 kPa.
같은 식을 세 입력 이상에 적용할 때는 제한된 이항 subtract 노드를 연결한다.

## 검증·미리보기

- 저장 전: 포트 누락/추가, 순환, 존재하지 않는 참조/버전, 다른 설비, 수치가 아닌 입력, 단위·선언 출력 불일치, 출처 근거 누락을 검사한다. 모든 노드를 검사하며 사용하지 않는 잘못된 노드도 허용하지 않는다.
- 가상 평가: 입력 HEX/Typed 폭·타입 → 디코딩 → 각 입력 linear/unit-convert → subtract → 최종 cast → 의미의 타입/단위/범위 순서로 표시한다. subtract trace에는 left/right 각각의 값·타입·단위가 포함된다.
- 필수 입력이 없거나 오류면 sample.missing / graph.input-invalid 등과 bad·null 결과를 반환한다. 0 대체·한쪽 값 대체·부분 계산은 없다.
- Decimal 중간 정밀도 한도(4096자리)를 넘으면 오류다. Double/Int32 cast 손실은 loss.precision/loss.rounding으로 표시하고 exact이면 중단한다. half-even을 명시하면 uncertain 결과로 표시한다. 입력 자체의 float 양자화 손실도 유지한다.
- 음수 차압을 절댓값이나 0으로 바꾸지 않는다. 물리 범위는 별도 semantic range로 선언한다.
- 가상 품질 good/uncertain/bad는 오프라인 평가 상태다. 실제 시각·품질·freshness·동시 snapshot은 P3-D 범위다.

## 화면·SQLite

02/03에서 압력 단위를 선택해 접근·의미를 저장한다. 05 값 그래프에서 op·입력·factor/offset·from/to·출력 단위를 편집한다. 06에서 그래프 노드를 객체 프로퍼티에 매핑하고 최종 cast를 선택한다. 07에서 원문 주소와 연산 경로를 조회한다. 09에서 필요한 소스의 가상 입력과 단계별 결과·오류·손실을 확인한다.

SQLite의 기존 workspace JSON·revision CAS·원자 저장을 재사용한다. 새 테이블이나 기존 데이터의 자동 재작성은 필요 없다. 기존 1.x workspace는 P3-A 명시적 백업·이전을 먼저 수행한다. 2.0 envelope는 기존 문서와 새 2.2 문서를 함께 저장·재조회할 수 있다. preview는 저장된 revision만 평가하고 입력/결과를 DB에 저장하지 않는다. 오래된 revision은 409다.

검증 샘플을 주 DB에 추가하기 전 build/p3c-ui/pre-p3c.sqlite3으로 revision 13을 백업했다. 기존 정의를 덮어쓰지 않고 차압 샘플 세 객체를 추가했다.

[독립 fixture](../fixtures/p3c/README.md) · [검증 결과](verification/P3-C-RESULTS.md) · [계획](../MVP-PLAN.md).
