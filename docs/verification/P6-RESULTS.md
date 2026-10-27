# P6 구현 및 검증 결과

2026-10-17. Bifrost 독립 수신 검증·등록 키 서명 승인·불변 파일 릴리스와 Tyr (Týr) 파일/CLI/SQLite/화면 연계를 구현했다. 실제 장치/솔루션 접속·외부 SQL·쓰기 실행·운영 활성화는 제외했다.

## 결과

- 기존 계약 56개를 변경하지 않고 2.9 submission/validation/approval/release 4종을 추가했다.
- Bifrost는 별도 Java 구현과 자체 bundled schema로 네 접근 프로파일·설비/연결·참조·hash·근거·타입/단위·의미·그래프/배열/selector·쓰기 정의를 검사한다. Tyr 코드를 import/실행하지 않는다.
- 승인에 proposal/전체 bundle/기준 릴리스/수신 변경 보고서 hash를 묶고 등록된 두 Ed25519 키와 PUBLISH/APPROVE 권한을 확인한다.
- 수정·변조·stale base/approval·unknown-op·미확인·같은 의미 ID의 role/type/unit 변경을 거부한다. source-only 묶음을 매핑 릴리스로 발행하지 못한다.
- staging 재검증, atomic 디렉터리 이동·HEAD 교체를 구현했다. 실패 주입 시험에서 이전 HEAD를 유지했다.
- 13 화면에서 복수 객체 매핑/쓰기 정의 scope 선택, 제출 저장/ZIP, 독립 검사·서명 승인·발행 상태를 구분한다. 웹에 승인/발행/키 입력/실행 API는 없다.

## 직접 실행한 검증

Tyr **701/701**: 신규 **37**, P1~P5 회귀 **664**. [신규 보고서](p6-validation.json)와 각 *-p6-regression.json/.log를 참조한다.

Bifrost **661/661**의 중복 제외 검증 범위: 기존 **614**, 신규 core **45**, CLI **2**.
전체 reactor 실행에서 655개(기존 614 + 당시 신규 41)가 통과했다. 이후 변경 보고서 바인딩·의미 변경·source-only 거부·UTF-8 출력 보완을 포함한 최종 45+2개를 다시 실행했다. 최종 jar package도 성공했다.

- [전체 reactor log](bifrost-p6-tests.log)
- [최종 P6 시험 log](bifrost-p6-final-tests.log)
- [최종 package log](bifrost-p6-final-build.log)
- [집계·jar hash](bifrost-p6-validation.json)

Maven은 offline 모드로 실행했다. CycloneDX SBOM goal은 online 모드 요구로 건너뛰었다. 이를 SBOM 생성 성공으로 계산하지 않는다.

공유 wire fixture에서 MELSEC/AB/S7-UA/S7-DB 및 기존 P3-D/E/F 계약을 두 독립 구현으로 대조했다. 전체 manifest digest도 Python과 Java 결과가 일치했다. 등록/미등록/잘못된 키·자기 승인·서명 변조·권한 변경·퇴역 키·승인 후 수정·원본 근거 변조·stale base·staging 실패·출처/단위/타입/참조 오류를 검사했다. 한글 wire JSON은 Windows 콘솔 encoding과 무관하게 UTF-8 bytes로 출력한다.

## 화면·CLI seam

원본 build/p5-ui/editor.sqlite3 revision 39를 backup으로 복제한 build/p6-ui/editor.sqlite3를 사용했다. 기존 P5 workspace body/updatedAt과 migration·시나리오·기준본·검토 테이블의 모든 행이 원본과 동일함을 읽기 전용 SQLite로 대조했다. import 2개·가상 시나리오 4개·검토 기록 2개를 보존했다.

1. 13에서 mixed-tank-mapping과 해당 객체의 쓰기 정의 2개를 p6-mixed-first 제출본으로 저장했다. streamId=mixed-line. 작성 revision은 39 유지.
2. Bifrost CLI가 다시 검사해 승인 대기 상태를 표시했다.
3. 별도 시험 registry에서 임시 proposer/approver 등록 키로 p6-approval-first 서명 승인을 생성했다. Tyr에서 서명 승인됨을 조회했다.
4. Bifrost CLI가 mixed-release@1.0.0을 파일 발행했다. Tyr에서 릴리스 발행됨과 ID/버전을 확인했다.
5. 최종 jar로 status/전체 payload를 재검증했다. 32개 파일 byte SHA가 제출본과 같았다. SQL 원문의 앞 공백 2개·뒤 개행/공백도 그대로였다.
6. 기존 가상 preview 150−110=40 kPa가 유지됐다. 브라우저 console error는 없었다.

제안 SHA: 02b4831eb5127b1a39f61a2c6089ea2b3b4790c2fb651171cd8a4acf646b2ca8
전체 묶음 SHA: 4d88ce495d62333badec94bd76509f7b0d4601d4a00942640c1db8fc83c0c386

실제 관찰: [p6-ui-observation.json](p6-ui-observation.json), [서명 승인](p6-ui-approval.json), [파일 릴리스](p6-ui-release.json).

![서명 승인 상태](p6-approved.png)

![파일 릴리스 상태](p6-published.png)

## 완료 경계

A11 검사/승인 후 파일 변경에 따른 이전 승인 재사용 거부, A12 릴리스 일부 누락/변조에 따른 파일 검증 거부와 HEAD 보존, A16 revision/base/승인 충돌을 오프라인으로 평가했다. A12는 복제한 시험 registry에 대한 실제 CLI 부정 probe 2개도 확인했다: [probe 근거](p6-release-negative-probes.json). 운영 소비/적용은 검증 범위 밖이다.

이번 발행은 선택한 혼합 매핑 scope다. 작성본 전체의 기존 draft/import 미해석 finding 22개를 승인하거나 해소하지 않는다. local P5 reviewed 판단을 Bifrost 승인으로 취급하지 않는다.

registry identity/policy·파일시스템은 운영자가 보호할 trust root다. 여러 독립 스트림을 가로지르는 전역 semantic catalog, 외부 anchor/rollback-evidence, 운영 IAM/bootstrap/배포, crash staging GC 및 전원 손실 durability는 후속이다. 실제 현장 원본·독립 담당자 PoV도 아직 없다.

Bifrost 작업은 codex/tyr-p6-mapping-release 로컬 feature 브랜치에 있다. main 변경·commit·push·merge는 하지 않았다. hash가 고정된 schema/fixture에는 Git newline normalization 방지 속성을 추가했다.

[설계·사용](../P6-BIFROST-PUBLICATION.md) · [MVP 계획](../../MVP-PLAN.md). 다음 주 단계는 P7 오프라인 수용 및 실제 자료 PoV다.

시험용 임시 private/public key 파일은 저장소 밖에서 생성했고 검증 후 삭제했다. registry에는 과거 서명 검증에 필요한 등록 공개 키와 서명 artifact만 남겼다. 최종 코드/jar hash는 [artifact 목록](p6-final-artifact-sha256.json)에 기록했다. 마지막 화면 라벨 추가는 브라우저 재조회로 확인했다.
