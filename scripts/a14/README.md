# A14 OS 격리 수용 재현

Docker Desktop Linux 엔진과 로컬 Python을 사용한다. 제품 코드는 JSON/파일/CLI로만 연결하며 Docker socket·host network·외부 SQL/쓰기 실행을 사용하지 않는다.

## 이미지 준비와 실행

이미지 준비 단계에는 의존성 다운로드가 있다. 실제 수용 실행과 분리한다.

~~~powershell
docker build --pull=false -t tyr-a14:20261018 -f scripts/a14/Dockerfile scripts/a14
./scripts/a14/run.ps1
python -B scripts/report_a14.py build/a14/<실행 디렉터리>
~~~

정확한 재현에는 docs/verification/a14-summary.json의 imageId를 사용해 run.ps1의 -Image에 전달한다. 새 이미지 빌드의 apt/transitive pip 버전은 변할 수 있으므로 동일 환경이라고 가정하지 않는다. 실행에는 --pull=never를 적용한다. 격리 현장으로 이관할 때는 사전에 docker save/load로 이미지와 소스·jar·seed DB를 전달한다. 실행 중에는 패키지를 설치하지 않는다.

run.ps1은 기본 build/a07-ui/editor.sqlite3를 SQLite backup으로 복제한다. -SeedDb로 호환되는 기존 DB 경로를 지정할 수 있다. 코드/fixture/schema/Java jar는 읽기 전용 archive로 전달하며, 결과는 build/a14/<시각>에만 쓴다. disposable container는 종료 후 제거하지만 이미지·원본 증거는 보존한다. 호스트 방화벽이나 기존 59772~59774 서버는 변경하지 않는다.

## 격리 경계

실제 Chromium·Python HTTP server/preview·Java receiver/서명 CLI가 모두 같은 Linux network namespace에서 실행된다. --network none, DNS 127.0.0.1, capability ALL drop, no-new-privileges, 포트 publish 없음, Docker socket 마운트 없음이다. 외부 인터페이스/IPv4·IPv6 경로 부재와 실제 소켓/브라우저 실패를 기록하고 localhost 성공과 대조한다. 애플리케이션의 fetch interception·proxy·Python monkeypatch로 차단을 대신하지 않는다. 기존 P7 runner의 Python guard는 추가 방어일 뿐이다.

브라우저는 자동 수용 시험용 headless Chromium이며 --no-sandbox로 실행한다. Chrome 보안 sandbox 시험이나 호스트 Windows 전체 방화벽 검증을 주장하지 않는다. CSP는 그대로 유지하고 DOM으로 대기한다. in-app browser는 이 네트워크 격리 증거에 포함하지 않는다.

## 작성·승인 경로

14 새 alias 작성 및 기존 view 편집 → 근거 누락 부모 변경의 422/원자성 → 06 공통 의미 매핑 → 재로드/SQLite 재개방 → 09 원본 바이트 디코딩·bit·alias·cast → 13 불변 제출 → Java 독립 validate → 별도 두 등록 키 승인 → 파일 publish → 화면 상태 재조회·ZIP 내용 hash 확인 → 재로드한다.

개인 키는 컨테이너 /tmp의 TemporaryDirectory에서 생성·삭제한다. 화면·SQLite·증거에는 개인 키를 남기지 않는다. 공개 등록 키와 서명 receipt만 registry에 보존한다. 운영 활성화가 아니다.

실제 현장 자료·독립 담당자·정답·개정본·전체 검토 시간과 타 설비 재사용성 PoV는 docs/P7-OFFLINE-ACCEPTANCE.md에 따라 별도로 수행한다.

날짜 형식 검사는 rfc3339-validator를 명시적으로 설치하고 정상/잘못된 date-time의 preflight를 실행한다. jsonschema의 선택적 checker가 없으면 해당 형식이 무시될 수 있으므로 설치 여부만으로 통과를 판단하지 않는다. 전체 회귀의 개별 unittest log와 runner stdout을 별도 파일로 보존한다.

현재 스키마의 format은 date-time(18곳)·uri(17곳)다. URI checker용 rfc3986-validator도 고정하고 정상 URN/공백 포함 URI의 preflight로 검사 활성화를 확인한다.

검증 DB·제출 묶음·registry는 컨테이너 로컬 /work/evidence에서 실행한다. Windows/Docker 9p의 metadata 지연이 수용 경로를 지배하지 않도록 완료/오류 시 runtime-evidence.tar로 한 번 내보내고 호스트에서 해제한다. /evidence는 결과 반출 전용이다. 성능 벤치마크나 Windows 전체 PC 검증이 아니다.
