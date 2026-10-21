# P4-A · 파일에서 접근 정의 초안 만들기

2026-10-17. 실제 장치 통신·browse/read/write·운영 적용·Bifrost 승인은 제외한다.

## 지원 범위

2026-10-20 후속 설계: [P4-F 공통 수용 모델·PIO/Kepware 해석기 경계](P4-F-SOLUTION-INTERPRETATION.md). 이 문서의 기존 XLSX/tyr-config-v1 구현 범위는 유지한다. PIO·Kepware는 실제 제품 자료를 확보해 profile별 검증할 신규 대상이며 아직 importer 지원이 아니다. 복합 참조·해석 근거·미해석·전환 판정은 신규 계층으로 설계하며 2.6 import-batch를 소급 변경하지 않는다.

XLSX와 명시적인 tyr-config-v1 JSON 교환 형식을 지원한다. 실제 솔루션 이름·버전은 아직 정해지지 않아 벤더 설정 exporter 지원으로 표시하지 않는다. 파일의 알 수 없는 부분은 그대로 보존하고 임의 주소식이나 수식을 실행하지 않는다.

XLSX는 각 시트의 첫 비어 있지 않은 행을 헤더로 사용한다. inline/shared string과 숫자 원문을 읽으며 표시 형식으로 값을 바꾸거나 수식의 cached value를 정상 주소로 채택하지 않는다. 한국어/현장별 헤더는 columnMap으로 명시적으로 대응한다. 원래 열 이름과 값은 originalColumns로 남긴다. 매핑 충돌은 미해석으로 남긴다.

id는 소문자 ASCII 계약 ID이며 profile은 명시적으로 지정해야 한다. 현장 이름은 label로 따로 보존한다. ID/profile 없는 자료는 자동 추측하지 않고 미해석으로 보존하므로, 별도 ID 열/열 대응 또는 파일 정리가 필요하다.

기본 필드: id, kind(source/template/alias), profile, address, type, unit, stage, byteOrder, wordOrder, width, namespaceUri, identifierType, label.
type은 기존 계약의 UInt16/Int32/Float32 등이다. REAL/DINT 같은 vendor 명칭의 자동 추측·변환은 하지 않는다.
주소 subset: AB symbol leaf, S7-1500 URI 기반 OPC UA identifier, S7-300 DBn.DBBoffset, MELSEC decimal device/register. 비트·고정 배열·codec·vendor 동적 주소식 importer는 후속 범위다. 작성 화면의 기존 수동 기능은 유지한다.

## 템플릿·alias

template은 id, address의 {offset}/{index}, nonnegative integer base/stride, count(1~64)를 요구한다. offset=base+stride×index로 전개하며 instance ID는 template-id-index다. overrides는 인덱스 문자열을 키로 하는 JSON이며 address/label/unit/type/stage/byteOrder/wordOrder/width만 바꿀 수 있다. instance 예외도 원본 template claim에 남긴다. 잘못된 override·없는 파라미터·알 수 없는 placeholder는 템플릿 전체를 채택하지 않는다. 임의 산술식·코드 실행·vendor 상속은 제외한다.

alias의 target은 같은 파일의 source 또는 전개된 instance ID다. 최대 64단계 chain을 해석하며 missing/cycle/duplicate ID를 검사한다. 대상의 알려지지 않은 필드·수식·지원 불가 종류를 alias로 우회할 수 없다. 결과는 기존 direct source draft로 정규화하고, alias→target의 모든 원본 locator를 derivation/evidenceRefs에 보존한다. viewOf 실행 기능으로 취급하지 않는다.

## 계약과 근거

기존 46개 Schema는 변경하지 않는다. 2.6.0 common/import-batch/mapping-proposal이 신규다. 기존 source-definition 2.2, source-observation/evidence-artifact 1.1 및 객체·그래프·매핑은 재사용한다.

import-batch는 원본 bytesBase64, filename, SHA-256, format, parser name/version, origin/capturedAt, equipment, columnMap, 가져오기 당시 contextConnections와 모든 observations를 보존한다. observations는 raw, originalColumns(XLSX), locator, derivation, template, assumptions, issues, draft를 구분한다. parser 결과를 저장 전 원본에서 재생성하여 비교한다. 이후 새 논리 연결을 추가해도 최초 해석 문맥은 바뀌지 않는다.

모든 생성 정의는 draft다. 단위·stage·endian이 없으면 확정하지 않는다. stage 미확인은 초안용 raw 가정과 진단을 남긴다. 저장 폭을 타입에서 도출했다면 assumptions에 표시한다. 문서의 이름을 semanticId로 자동 승격하거나 공통 의미를 자동 승인하지 않는다.

선택한 정의만 sources에 채택한다. source editor record의 importRef(batchId/observationId)는 원래 관측을 가리킨다. source evidenceRefs에는 수동 검토 note 근거와 원본 파일의 셀/JSON pointer를 함께 연결한다. 근거 참조·원본·관측 변조를 검증한다. 기존 02 화면에서 수정해도 importRef와 원본 근거를 보존한다.

제안 패키지는 2.6.0으로 내보내며 원본 bytes, evidence-artifact, import-batch, source-observation, source-definition을 함께 포함한다. XLSX locator는 실제 셀 존재를 검사한다. 미해석 또는 fileIssue가 남아 있으면 import.unresolved를 출력하며 작성 초안은 저장 가능하다. P4-A는 미해석을 무시하는 승인 동작을 제공하지 않는다. 후속 원문 정정/재가져오기 및 검토 해소 계약이 필요하다. 이전 wire 게이트는 2.6 제안을 지원한다고 가정하지 않는다.

## 화면·API·SQLite

10 파일 가져오기에서 소속 설비·형식·파일·열 대응·현장/가상 출처를 정한다. 해석 미리보기는 SQLite를 변경하지 않는다. 검토 표에서 선택한 초안과 전체 원문 관측을 저장한다. 미해석은 채택 불가로 표시하지만 보존된다. 저장한 배치를 재조회하여 template/alias 경로·원문·초안을 펼쳐 보고 원본 파일을 내려받을 수 있다.

POST /api/import-preview: revision/request → 읽기 전용 batch.
POST /api/import-apply: revision/request/selected → 재해석 후 CAS 저장.
Host/Origin/X-Tyr-Editor, 2 MiB 요청, revision 충돌·중복 batch/ID·잘못된 선택의 원자적 거부를 재사용한다.

SQLite workspaceVersion 2.0 authoring envelope에 optional imports 컬렉션과 source importRef를 추가한다. 기존 테이블·CAS를 재사용하며 기존 DB를 열 때 body/revision을 재작성하지 않는다. 기존 데이터는 새 필드 없이 그대로 읽는다. 새 envelope의 optional 필드를 예전 편집기가 지원한다고 가정하지 않는다. wire proposal은 별도 2.6 계약이다.

UI 검증 DB는 build/p3f-ui/editor.sqlite3 revision 30을 backup으로 복제한 build/p4a-ui/editor.sqlite3이다. 원본은 보존한다. 검증 설비/논리 연결 추가 revision 31, XLSX 4개 초안/6개 관측 저장 revision 32, 설정 JSON 9개 초안/14개 관측 저장 revision 33. 기존 02 화면에서 수동 검토 note를 수정하고 importRef/원본 근거를 보존한 revision 34가 최종이다.

## 한도와 후속 범위

파일 512 KiB, XLSX 64 ZIP parts/4 MiB 전체 해제 크기, 256 input/expanded observations, 64 template instances/alias depth, 16 batches, authoring JSON 1.9 MB를 제한한다. XML entity·외부 관계·매크로 parts를 거부하며 ZIP을 파일시스템에 풀지 않는다. 원본 보존은 byte-exact이지 원문을 고쳐서 재출력하는 exporter가 아니다.

재사용: 기존 source/semantic/graph/mapping, manual evidence, proposal hash/locator, SQLite CAS, HTTP 보호, scalar decoder/preview.
신규: XLSX/교환 JSON reader, columnMap, bounded expansion/alias resolver, import-batch/proposal 2.6, 원본·관측 보존과 해석 재검증, 가져오기·검토·다운로드 UI.

후속: 실제 첫 솔루션 exporter 선정·parser, 현장 workbook layout profile/헤더 행 설정, PDF/.xls, vendor type/address codec, alias/템플릿 cross-file 참조와 UDT 상속, 미해석 검토 해소·재가져오기 diff/merge. MP03/12/18은 이 subset에서 부분 지원이다.


후속 P4-A B의 명시적 검토 이력과 3방향 재가져오기 병합은 [2.14 설계](P4-A-IMPORT-RECONCILIATION.md)를 따른다. 이 문서의 2.6 원본 보존/미해석 기준선과 수용 기록은 유지한다.
