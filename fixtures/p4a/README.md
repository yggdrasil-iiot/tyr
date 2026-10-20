# P4-A synthetic fixtures

context.json: 한 가상 설비의 네 PLC 논리 연결.
settings.json: 네 접근 방식과 3개 template instance, override D2050, 두 단계 alias, cycle/missing alias, unknown expression 및 vendorExtension.
memory-map.xlsx: 한국어 헤더, D3000, template D3100/D3190, alias, 동적 주소식과 수식 셀. columns.json으로 헤더를 대응한다.

settings/excel-request.json은 원본 바이트를 담은 재현 요청이다. batch.json과 workspace.json은 해석/선택 초안 저장 예시다. 독립 주소 정답은 test_p4a.py ORACLES에 별도로 작성했다. 모든 데이터는 가상이며 실제 제품 exporter 지원을 뜻하지 않는다.

실행: python -B scripts/test_p4a.py --report docs/verification/p4a-validation.json

[상세 계약·한도](../../docs/P4-A-FILE-IMPORT.md).
