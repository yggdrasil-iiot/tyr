# P3-A fixture

모두 가상 자료이며 실제 PLC 연결은 없다. [계약 설명](../../docs/P3-A-CONTRACT.md)을 참조한다.

| 파일/폴더 | 역할 |
|---|---|
| two-motors/proposal.json | 새 2.0 파일 proposal, 각 문서 SHA-256 고정 |
| two-motors/targets | 같은 설비 안 motor-a/motor-b, 같은 의미 모델 |
| two-motors/sources | motor-a D1000/D2000/D3000, motor-b D1100/D2100/D3100 각 1word |
| two-motors/graphs | low/high 조합 및 identity 결과 노드 |
| two-motors/mappings | 각 객체의 actual-speed 직접 매핑과 cycle-count 그래프 결과 매핑 |
| oracles.json | 독립 기대값 131073/262147/65538/4294967295 |
| invalid-cases.json | 순환·참조·중복·타입·단위·근거·해시 오류 32건 |
| migration-assignments.json | 기존 realistic 네 mapping-set에 부여할 명시적 객체 ID 예제 |
| legacy-schema-baseline.json | 이번 변경 전 1.0/1.1 Schema 해시 24개 |

오프라인 게이트는 scripts/test_p3a.py다. 기존 32개 신호 bundle은 테스트에서 임시 생성하여 마이그레이션·재로드·원본 보존을 검증한다. 사용자 SQLite DB는 열지 않는다. fixture harness는 가상 UInt16 word만 조합하며 일반 디코더/실제 통신/화면 preview는 구현하지 않는다.

기존 mapping-patterns의 planned 사례는 전체 제품 지원 기준이라 pending을 유지한다. P3-A 파일 계약·제한된 word 조합 증거를 해당 사례의 부분 검증으로 연결한다. 거부 fixture와 계획 명세를 정상 지원으로 집계하지 않는다.

## 2.0 workspace fixture

workspace-v2.json은 두 모터 계약을 현재 수동 근거 이름 규칙에 맞춘 UI/SQLite fixture다. scripts/test_p3a_workspace.py가 백업·마이그레이션·재시작·그래프 저장 오류·HTTP 경계를 검증한다.
