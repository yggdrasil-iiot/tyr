# A14 격리 오프라인 수용 환경

Tyr (Týr) 작성 화면·Python 저장/미리보기·Bifrost Java 검증/서명/파일 발행을 하나의 Linux network namespace에서 실행한다. 실제 장치 통신·외부 SQL·쓰기 실행·Muninn 운영 활성화는 제외한다. SQLite 자체의 로컬 저장 SQL은 외부 값 소스의 SQL 실행과 구분한다.

[실행 스크립트·상세 재현](../scripts/a14/README.md) · [수용 결과](verification/A14-RESULTS.md).

## 재사용과 변경

기존 62개 계약, A07 및 P1~P6 fixture, 작성 API/SQLite CAS, preview, Bifrost jar와 독립 승인 권위를 재사용한다. 새 수용 harness와 이미지·증거 집계기를 추가했다. 코드/fixture/schema/jar는 읽기 전용 묶음으로 전달한다.

실제 화면 검사에서 발견한 frontend/views.js의 기존 view 편집 중복 ID 문제는 upsert에 definition.id를 명시하여 수정했다. 기존 소스 작성기의 ID 처리와 동일하다. 계약/API·SQLite 스키마·Bifrost 코드는 변경하지 않는다.

## 실제 차단

- Docker --network none, --dns 127.0.0.1, --cap-drop ALL, --security-opt no-new-privileges.
- Docker socket/host network/port publish를 사용하지 않는다.
- OS의 인터페이스가 lo 하나이고 IPv4·IPv6 외부 경로가 없음을 기록한다.
- Python 실제 socket의 IPv4/IPv6 TCP·UDP·외부 DNS 전송 실패와 localhost API 성공을 대조한다.
- 별도 Java probe의 IPv4/IPv6 TCP·DNS UDP 실패 및 localhost HTTP 200을 대조한다.
- 별도 Chromium 페이지에서 외부 IPv4/IPv6·호스트명 탐색 실패를 확인한다. 작성 페이지와 분리하여 실패 페이지의 오류 탐색이 다음 단계에 간섭하지 않게 한다.

브라우저 fetch interception, proxy, context offline 모드, Python monkeypatch를 차단 근거로 사용하지 않는다. 기존 test_p7.py의 Python guard는 추가 방어다. 그 runner가 자신의 javaAndBrowserOSIsolation을 not-performed로 기록하는 필드는 그대로 보존하며, A14의 별도 Docker/OS 증거와 결합한다.

호스트 Windows 전체 방화벽과 in-app browser를 격리했다는 의미가 아니다. 실제 테스트용 Chromium·Python·Java와 자식 프로세스 전체가 격리 경계 안에 있다. Chromium은 headless/--no-sandbox로 실행하므로 Chrome 자체 security sandbox 수용 검증도 아니다. CSP는 완화하지 않는다.

## 준비와 저장 경계

의존성 다운로드는 이미지 준비 때만 수행한다. 수용 실행은 --pull=never이며 패키지를 설치하지 않는다. 정확한 재현에는 수용 결과의 imageId·소스 archive/jar/입력 해시를 사용하고 이미지·자료를 사전에 전달한다. apt 및 transitive pip를 다시 해석하는 새 빌드를 같은 환경으로 계산하지 않는다.

현재 Schema에서 사용하는 date-time·uri checker는 rfc3339-validator·rfc3986-validator로 명시한다. 정상 시각/URN과 잘못된 시각/공백 포함 URI의 preflight를 통과해야 수용 경로를 실행한다. jsonschema 설치만으로 선택적 format 검사가 활성화되었다고 가정하지 않는다.

원본 DB는 읽기 전용 SQLite backup으로 복제한다. 복제본을 기존 Store로 열어 전체 테이블 행·revision·파일 해시가 유지되는지 확인한다. 작성/승인 경로는 별도의 가상 fixture DB에서 실행한다.

실행 DB·제출 묶음·registry는 /work/evidence 로컬 파일시스템에 둔다. Windows/Docker 9p metadata 지연을 검증 hot path와 분리한다. 완료 또는 오류 시 runtime-evidence.tar로 /evidence에 한 번 반출하고 호스트에서 해제한다. 이는 제품 저장 계약 변경이나 성능 개선 실험이 아니다. 기존 59772~59774 DB/registry는 변경하지 않는다.

## 수용 경로와 권위

14 새 alias 작성·기존 view 편집 → 의존 근거 없는 부모 변경 거부/원자성 → 06 공통 의미 매핑 → 재로드/SQLite 재개방 → 09 가상 바이트·bit·alias·cast → 13 불변 제출 → Java 독립 validate → 두 등록 키 approve → 파일 publish → 화면 재조회·ZIP 및 릴리스 파일 해시 → 재로드한다.

개인 키는 컨테이너 /tmp의 TemporaryDirectory에서 생성하고 삭제한다. 브라우저·SQLite·반출 증거에는 개인 키를 기록하지 않는다. 공개 등록 키·서명 receipt만 registry에 남긴다. Tyr는 승인·발행을 웹에서 실행하지 않으며 상태만 조회한다.

기존 fixture의 디코딩·low/high·단위·스케일·파생식·품질·배열·selector·가져오기·변경 검토·변조/충돌 검사는 같은 격리 경계에서 회귀 실행한다. 직접 브라우저 수용 흐름은 alias/Boolean 대표 경로이며 모든 폼 조합의 브라우저 coverage를 주장하지 않는다.

## 실제 현장 PoV

[현장 절차](P7-OFFLINE-ACCEPTANCE.md)의 실제 익명화 문서/설정 export·제품 버전·전후 개정본·독립 정답·전체 검토 시간·타 설비 재사용성 측정은 별도 미수행이다. 이 가상 오프라인 검증으로 현장 정확도나 시간 절감률을 결론 내리지 않는다. 목표 현장 PC/VM의 OS·보안 정책·저장소에서의 배포 수용도 별도로 확인한다.
