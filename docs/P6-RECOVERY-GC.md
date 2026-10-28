# P6 후속: 프로세스 중단 복구·보수적 GC·무결성 fault injection

범위는 로컬 파일 registry와 SQLite 제출 저장이다. 장치 통신·외부 SQL·쓰기 실행·runtime 활성화는 제외한다. 기존 2.0 작성본, 2.9 submission/approval/release, 2.14 import 이력과 기존 SQLite 테이블을 그대로 사용한다. 새 운영 저널/조회 결과의 version 1은 정준 데이터 모델이나 승인 계약을 대체하지 않는다.

## 책임과 복구

Bifrost만 승인·발행 권위를 가진다. Tyr (Týr)에는 개인 키나 recover/publish 실행 API를 추가하지 않는다.

1. Bifrost는 staging payload를 독립 검증하고 release.json을 만든다.
2. transactions/<UUID>.json에 streamId, id, releaseVersion, release SHA, staging 이름, baseRelease를 기록한다. 저널 파일 force 후 release 폴더를 atomic move한다.
3. head를 atomic replace하고 저널을 제거한다. 미완료 저널이 있으면 새 approve/publish와 GC를 거부한다.
4. `java -jar bifrost-gates.jar mapping recover <registry>`는 registry lock 안에서 서명·파일 digest·inventory·submission·기준 head를 검증한다. head가 base와 같으면 원래 작업을 완료하고, 이미 target이면 저널만 정리한다. 반복 호출은 빈 actions를 반환한다.
5. 저널 잘림·release/payload 손상·head 충돌·symlink는 거부하고 자료를 보존한다. 임의의 head 롤백이나 잘못된 파일 자동 재생성은 없다. 관리자가 원인과 보존 사본을 조사해야 한다.

Tyr export는 SQLite BEGIN IMMEDIATE 안에서 파일 작성/검증과 제출 row insert를 수행한다. 커밋 전 중단은 row가 롤백되고 고아 파일이 남는다. 커밋 후 중단은 기존 불변 제출본을 재조회한다. 고아 폴더를 제출 기록으로 자동 채택하지 않는다. refresh 재시도는 기존 submissionRevision CAS를 유지한다.

## GC: 조회 후 가역적 격리

- Bifrost `mapping gc <registry> <grace-seconds>`로 사전 조회한다. `--quarantine <planSha256>`를 붙이면 같은 lock 안에서 후보/내용/root pin을 재계산해 일치할 때만 이동한다.
- grace는 3600~31536000초. `.staging-*`, approvals의 UUID `.pending`, heads의 UUID 임시 `.json`만 후보로 삼는다. 이름을 모르는 파일은 보존한다.
- 모든 승인과 모든 릴리스(현재 head에서 벗어난 과거 포함), payload 전체·원본 근거·import 검토/이전 batch closure, identity 파일을 보존한다. 손상된 역사적 릴리스가 있으면 GC를 거부한다.
- Tyr 13 화면의 무결성 검사·GC 조회/격리는 `/api/submission-maintenance`를 사용한다. `{graceSeconds}` 조회, `{graceSeconds,planSha256}` 격리. 화면은 24시간 기준이다. 저장된 row의 폴더는 무조건 보존하고 검증한다. row가 없는 `<submission-id>-<32 hex>` 폴더만 후보로 삼는다.
- Tyr는 SQLite 쓰기 lock으로 export/GC를 직렬화하며 row/내용/mtime pin이 달라지면 거부한다. 손상된 제출본은 조회에 corrupt를 표시하고 격리·다운로드·refresh를 거부한다.
- 격리는 각 관리 root의 quarantine/<UUID>/ 아래 atomic move한다. 파일 영구 삭제, 승인/릴리스 삭제, workspace/import 이력 압축은 이번 GC에 없다. GC 도중 중단해도 이미 이동한 파일은 격리에 남고 새 조회로 나머지를 처리할 수 있다.

## 검증과 재현

[scripts/p6r/run.ps1](../scripts/p6r/run.ps1)은 기존 로컬 Docker 이미지에서 --network none, localhost DNS, capability 제거 상태로 Chromium/Python/Java를 실행한다. 기존 P4-A B 브라우저 작성·저장·preview·승인/발행 경로와 새 무결성·GC·recover CLI를 검증한다. Python 테스트는 실제 os._exit, Java JUnit은 별도 JVM의 Runtime.halt를 사용하며 훅은 테스트 코드에서만 설정한다. HTTP/CLI에는 fault 주입 인자가 없다.

[fixture 시나리오](../fixtures/p6-recovery/fault-matrix.json) · [수용 결과](verification/P6-RECOVERY-RESULTS.md).

## 별도 미완료와 PoV

이번 보장은 프로세스 중단과 재시작의 논리적 복구다. OS/전원 손실·디스크 캐시/디렉터리 fsync·파일시스템별 crash durability, 실제 Windows 배포/공유 스토리지 가용성, 무제한 registry 규모 성능은 검증하지 않았다. atomic move 미지원 파일시스템에서는 거부하며 비원자적 fallback을 추가하지 않았다. registry를 직접 바꾸는 외부 프로세스나 관리자와의 동시 변경은 lock 계약 밖이다.

서명된 approval은 기존 승인 권위를 유지하지만 저널은 로컬 운영 자료다. 공격자가 registry와 head/journal을 함께 재작성하는 상황의 외부 anchor/rollback 증명, 운영 IAM/bootstrap·키 회전 책임, 활성화/현장 수용은 별도다. 실제 자료·담당자 독립 정답·재사용성과 검토 시간에 대한 현장 PoV를 완료로 바꾸지 않는다.
