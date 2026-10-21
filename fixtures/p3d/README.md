# P3-D 독립 가상 시간·품질 fixture

workspace.json은 P3-C 차압 정의에 2.3 temporalPolicy를 붙인 가상 작성본이다. scenario.json은 workspace hash와 바인딩을 고정한 저장 가능 사례다.

cases.json의 32개 기대값은 수동으로 기입했다. 기본 가상 기준은 2026-10-17T10:00:00Z, 상류 값 150/시각 09:59:59.500Z, 하류 값 100/시각 09:59:59.550Z다. 기대 age는 500/450ms, skew는 50ms, 차압은 50kPa다. 날짜·시간대·경계값은 구현에서 정답을 생성하지 않는다.

정상·age/skew 경계 포함·1마이크로초 초과·미래 입력·source/server 기준·시각 결측과 fallback 금지·동일 offset 순간·잘못된 날짜/offset·uncertain 전파/거부·bad 전파·값/입력 결측·가상 trigger sequence 일치/불일치·unused bad 격리·기존 샘플의 암묵적 good 금지를 포함한다.

python -B scripts/test_p3d.py --report docs/verification/p3d-validation.json

추가 검증은 source-only/low-high/차압 lineage, 이전 Schema 보존, 정책 오류 저장 원자성, SQLite 기존 DB의 테이블 추가와 기존 body/revision 유지, 시나리오 저장·재조회·hash stale·revision 충돌, preview 전후 DB 파일 해시 불변이다.

fixtures/mapping-patterns의 freshness-good/freshness-stale/bad-input-quality/trigger-record 계획 사례와 대응한다. 기존 planned baseline을 일괄 성공으로 계산하지 않는다. 실제 장치·네트워크 지연·시계 동기화·snapshot/handshake는 검증하지 않는다.
