# P6 후속 오프라인 수용 결과 · 2026-10-18

판정: 프로세스 중단 복구·보수적 GC·파일 무결성 fault injection의 제한된 오프라인 범위 충족. 실제 현장 PoV와 전원 손실 durability는 미수행이다.

| 검증 | 최종 결과 | 환경/근거 |
|---|---:|---|
| 새 중단·GC·무결성 Python | 13/13, 스킵 0 | 실제 os._exit, SQLite rollback/commit, quarantine 중단·계획 변경·symlink·누락/변조 |
| 기존 Python·fixture 회귀 | 884/884 | 가져오기 58 + 후보 그래프 39 + 논리 구조 30 + 제한 연산 17 + A07 39 + 기본 701 |
| 매핑 관련 Java | 116/116, 실패/오류/스킵 0 | MappingPublicationTest 111 + LogicalStructureTest 3 + MappingGateTest 2; 로컬 Windows Maven -o |
| 브라우저·HTTP·SQLite·Java CLI 연계 | 34/34 | Linux Chromium/Python/Java, Docker --network none, localhost only |
| 기존 입력 보존 | 계약 파일 72개(schema 71개), fixture 500개 변경 0 | P4-A B baseline SHA 대조; Java schema 사본 71개 모두 동일 |

Python·fixture 합계는 897이다. 브라우저 수용 JSON의 41행 중 7행은 suite exit 확인 표식이므로 별도 검사로 중복 합산하지 않았다. Java의 중간 targeted 실행도 최종 116에 합산하지 않았다. 전체 Bifrost 타 모듈 테스트 완료라는 주장은 아니다.

## 확인한 동작

- Bifrost intent 기록 후·release 이동 후·head 이동 후의 예외와 실제 별도 JVM Runtime.halt 종료에서 재시작 복구, 기준 head CAS, 반복 복구의 무변경을 확인했다.
- 저널 잘림·stage payload/metadata 손상·head 충돌은 거부하며 이전 head와 자료를 보존한다. 미완료 저널은 approve/publish/GC를 차단한다.
- GC 사전 조회는 후보를 보존하고, 같은 계획으로 실행하면 임시 자료만 quarantine으로 이동한다. 새 조회로 중단 후 재개하며 영구 삭제는 없다. 과거 unheaded 릴리스와 승인·전체 근거 closure는 보존하고 역사적 payload 손상은 거부한다.
- Tyr (Týr) 실제 프로세스 종료의 커밋 전 rollback/커밋 후 제출 row 보존, 불변 제출본 재조회와 다운로드, 고아 폴더 구분·손상 표시·격리 차단·workspace 유지·SQLite 재개방을 확인했다.
- 기존 가져오기 검토/병합 작성·저장·가상 preview·불변 제출·독립 Java 검증·두 키 승인·파일 발행·화면 재조회 경로를 함께 통과했다. 서명용 임시 개인 키는 evidence 밖에서 생성 후 삭제했다.

## 재현과 증거

- `scripts/p6r/run.ps1`: 최종 `build/p6r/20261018-041940`, 이미지 tyr-a14:20261018, readonly 입력, --network none / localhost DNS / cap-drop ALL. [실행 인자](p6r-docker-arguments.json), [namespace 설정](p6r-docker-inspect.json), [이미지](p6r-image-inspect.json).
- [연계 수용과 입력 SHA](p6r-full-acceptance.json), [실행 이력·집계](p6r-run-history.json), [제품/Java 소스와 JAR SHA](p6r-validation.json), [호환성](p6r-compatibility.json).
- [새 Python](p6r-recovery-tests.log), [기본 701](p6r-regression.json), [A07](p6r-a07.json), [Java 집계](p6r-java-summary.json), [Java 111 XML](p6r-java-MappingPublicationTest.xml), [화면](p6r-maintenance.png).
- 최초 `build/p6r/20261018-041726`는 연계 34개 통과 후 symlink fixture의 GC-age 전제 때문에 실패했다. 링크 생성 후 폴더 mtime을 다시 과거로 설정해 대상 조건을 맞췄고 제품 코드 변경 없이 전체를 재실행했다. [최초 실패](p6r-initial-failure.json)를 보존했다.
- Windows의 중간 Python 12개 실행은 symlink 권한 때문에 1개 스킵이 있었으며 최종 수용으로 사용하지 않았다. 최종 Linux 13개는 전부 실행/통과했다.

최종 JAR SHA-256: `510485b5ce24fc95138238de1d58adde92c1fcf677b035a0bab78ad6eeddcee9`.

## 별도 미수행

실제 XLSX/제품별 설정·현장 담당자의 독립 정답·수렴/오매핑/누락/손실·검토 시간 PoV, vendor native layout, 운영 IAM/bootstrap/키 책임·외부 anchor·rollback 증명·실제 활성화, Windows 전체 네트워크 차단/배포 수용, OS/전원 손실과 디렉터리 fsync/디스크 캐시/공유 파일시스템 durability 및 대량 규모 성능은 별도다. 이번 결과가 이들을 완료로 바꾸지 않는다.

장치 통신·외부 SQL·쓰기 실행은 추가하거나 실행하지 않았다. 기존 계약/SQLite 테이블과 사용자 기존 DB/registry를 유지했다. 새 시연은 별도 `build/p6r-ui/editor.sqlite3`와 localhost:59779의 13 화면이다. 실제 운영 권한/개인 키를 배치하지 않았다. Bifrost 로컬 feature 브랜치 유지, commit/push/merge 미수행.
