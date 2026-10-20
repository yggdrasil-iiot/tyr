# P6 Bifrost 계약·승인·릴리스 연계

## 역할과 재사용

Týr는 선택한 객체 매핑과 전이 의존 문서·원본 근거를 불변 제출본으로 내보낸다. Bifrost는 별도 Java 수신 검증기로 동일 wire 데이터를 다시 검사하고 등록 키·권한·두 확인자로 승인한 묶음을 파일 릴리스로 발행한다. Python 코드를 JVM에서 실행하거나 Maven 의존으로 결합하지 않는다. 공유하는 것은 버전별 JSON Schema의 바이트 동일한 데이터 사본뿐이다. 기존 계약 56개는 유지한다.

재사용: Týr package/evidence builder·P3 검증·SQLite/CAS, Bifrost JSON/identity/Ed25519·KeyFileLedgerSigner preflight·ActivationAuthorizer·ActivationPolicyStore.
신규: 독립 bundle/schema/type/unit/graph 검증기, mapping registry/CLI, PUBLISH 권한, 제출·승인·릴리스 wire 계약과 scoped export/화면.

기존 ActivationService/운영 activation ledger를 호출하지 않는다. PUBLISH와 APPROVE 권한은 target=mapping-publication, kind=mapping-release, ref=streamId에 적용한다. ACTIVATE 권한을 갖고 있다고 매핑 발행 권한을 부여하지 않는다.

## 계약 2.9.0

- mapping-submission: 불변 제출 ID, 안정된 streamId, 작성본 canonical SHA, proposal byte SHA, 기준 릴리스 id/version/sha256, 제안자, 설비·논리 연결 문맥, execution=excluded.
- mapping-validation: 수신자가 다시 계산한 proposal/bundle SHA, accepted/finding, 고정 capability.
- mapping-approval: payload SHA와 두 Ed25519 서명. 제안/제출/스트림·proposal/bundle SHA·기준 릴리스·두 주체·시각·capability와 Bifrost가 계산한 기준 대비 변경 보고서 해시에 묶인다.
- mapping-release: 전체 payload 파일 목록·byte SHA, 서명 승인, 제안/제출/스트림·기준 릴리스, publishedBy=bifrost, activation=not-performed, execution=excluded.

기존 proposal 2.0/2.6/2.7 및 source/graph/mapping/write 계약은 유지한다. 기존 proposal.baseRelease에도 기존 계약이 요구하는 SHA를 포함한다. P5의 로컬 reviewed를 Bifrost approval로 변환하지 않는다.

bundle SHA는 정렬된 path + TAB + byte SHA + LF의 UTF-8 SHA-256이다. proposal.json, submission.json, 정의, evidence와 원본 data 모두 포함한다. JSON 공백도 byte hash에 포함한다. OS 절대 경로는 제외한다.

## 독립 수신 검사

Bifrost는 자체 classpath Schema만 사용하며 caller URI를 가져오지 않는다. JSON duplicate/trailing token, unknown version/kind/op, 잘못된 path·symlink escape, 목록 외 파일, 해시/참조/근거 locator 오류를 거부한다. XLSX cell은 별도 ZIP/XML 검사로 시트·셀 존재를 확인하며 외부 DTD/관계는 사용하지 않는다.

네 접근 프로파일과 pinned equipment/connection 일치, source readiness/표현/폭/codec/배열 geometry, semanticId 충돌, 객체 완전성, 그래프 순환·입력·타입·단위·근거, selector 후보/정수 인덱스/기본 후보, 읽기·쓰기 변환과 목적지 방향/중복을 다시 검사한다. 가상 수치 계산·SQL/provider/device 실행은 하지 않는다.

Týr 작성 도구가 미확인 단위를 경고로 보존하더라도 Bifrost 발행은 확인된 단위를 요구한다. 미해석 import, draft, 2.x view, native/nested/임의 주소식 및 미지원 연산은 거부한다. importer의 template/alias 의미를 새 vendor parser로 재구현한 것은 아니다. 원본 hash/locator·선언된 미해석 상태·확정 source 계약을 검증하고 원문/관측을 보존한다.

최대 파일 4096개·묶음 32MiB와 단일 파일 검사 한도를 둔다. 실제 현장 파일럿·vendor parser 완전성·통신 정확도는 별도다.

## 승인·발행 절차

1. validate에서 수신 검증.
2. approve에서 현재 기준 릴리스, 등록 키의 주체·유효 기간·서로 다른 키, PUBLISH/APPROVE 권한 확인.
3. 완성된 승인 receipt를 임시 파일에서 atomic move. 무서명 승인 경로는 없다.
4. publish에서 수신 검사와 승인 digest·서명·현재 키/권한·기준 릴리스와 변경 보고서 해시를 재검증.
5. registry lock 아래 staging 복사·재검증, 완성 디렉터리 atomic move, 릴리스 hash를 담은 HEAD atomic replace.
6. status에서 manifest·각 파일·서명·payload를 다시 검사. 다른 스트림 HEAD는 거부.

실패 시 이전 HEAD를 유지하고 비원자적 fallback을 하지 않는다. process 실패/부분 쓰기 경계를 검사하며 전원 손실의 fsync durability는 보장하지 않는다. 실패 staging이나 HEAD 반영 전의 완성된 미참조 디렉터리는 조사용으로 남을 수 있다. 운영자 복구·GC는 후속이다.

registry identity/policy 및 파일시스템은 운영자가 보호하는 trust root다. 기존 activation의 외부 anchor/rollback-evidence를 이 registry에 자동 연결했다고 주장하지 않는다. 키·권한 변경은 새 발행에 반영하며 과거 서명은 보존된 등록 키로 검사한다.

## 사용과 저장

~~~text
java -jar bifrost-gates.jar mapping validate <bundle>
java -jar bifrost-gates.jar mapping diff <before> <after>
java -jar bifrost-gates.jar mapping approve <registry> <bundle> <approval-id> --by <proposer> --by-key <key-file> --approved-by <approver> --approved-by-key <key-file>
java -jar bifrost-gates.jar mapping publish <registry> <bundle> <release-id> <version> --approval <approval-id>
java -jar bifrost-gates.jar mapping status <registry> <stream-id>
~~~

서버 --bifrost-jar / --mapping-registry 설정 후 13 화면에서 제출 생성·수신 검증/상태 조회·ZIP 다운로드를 사용한다. 미설정 시 파일 내보내기는 가능하다. Java/registry 경로는 서버 설정이며 웹 요청이 바꾸지 못한다. 웹에 승인·발행·키 입력·SQL·쓰기 실행 endpoint는 없다.

승인 전/승인됨/발행됨/수신 거부/기준 충돌, 현재 작성본과의 차이, 마지막 조회를 구분한다. 상태는 마지막 CLI 관찰이다. SQLite mapping_submissions를 추가하고 기존 body/revision·import·P5 기록·가상 시나리오는 자동 재작성하지 않는다. 제출 최대 100개. 후속 개정은 같은 스트림과 새 제출 ID를 사용한다. 상태 refresh는 별도 revision CAS이며 제출 파일 변경은 거부한다.

[검증 결과](verification/P6-RESULTS.md) · [wire fixture](../fixtures/p6/README.md). 실제 장치 통신·외부 SQL·쓰기 실행 및 운영 활성화는 제외한다.

동일 스트림의 이전 릴리스와 같은 semanticId가 다른 role/valueType/unit으로 재정의되면 승인을 거부한다. 다른 개념은 새 semanticId로 선언해야 한다. 여러 독립 스트림을 가로지르는 전역 개념 catalog 검증은 이번 범위에 포함하지 않는다.


## 프로세스 중단 복구 후속

[P6-RECOVERY-GC.md](P6-RECOVERY-GC.md)에서 로컬 발행 저널·기준 head CAS 복구·보수적 임시 파일 격리·무결성 fault injection을 확장한다. 전원 손실 durability/외부 anchor/운영 IAM/실제 활성화는 계속 별도다. 기존 submission/approval/release 2.9.0 계약과 SQLite 행은 유지한다.
