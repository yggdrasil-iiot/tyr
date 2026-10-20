# A14 외부 네트워크 차단 수용 결과

2026-10-18. **격리된 Linux 컨테이너의 브라우저·Python·Java 전체 실행 경계에서 A14를 충족했다.** 현재 A01~A16은 기존 지원 범위의 오프라인 fixture 기준 16개 충족이다. 실제 현장 PoV는 별도 미수행이다. [현재 수용 기록](a14-acceptance.json) · [설계·재현·경계](../A14-NETWORK-ISOLATION.md).

호스트 Windows 전체 방화벽이나 in-app browser를 차단했다는 의미가 아니다. Docker Linux network namespace 안의 실제 headless Chromium·Python server/preview·Java CLI 및 자식 프로세스가 검증 대상이다.

## 실행 결과

| 검증 | 결과 | 근거 |
|---|---|---|
| A14 형식 의존성·OS 격리·실제 UI/저장/승인/발행 경로 | 45/45 | [개별 판정·입력 hash](a14-results.json) |
| A07 계약·독립 값 oracle·SQLite/API | 39/39 | [JSON](a14-a07.json), [log](a14-a07.log) |
| 기존 P1~P6 | 701/701 | [개별 ID](a14-regression.json), [544 unittest log](a14-regression-tests.log), [runner stdout](a14-regression.log), [P3-A CLI](a14-regression-p3a.json) |
| 릴리스/다운로드 내용 | payload 24파일 hash 일치 | Java 결과·ZIP·수용 JSON |
| 기존 계약·fixture·Java jar | 62개 Schema 보존·기존 60개 불변, fixture 462파일 불변, jar 불변 | [집계·image/source pins](a14-summary.json) |
| 기존 SQLite 복제본 | 전체 테이블 행/revision 및 개방 전후 파일 hash 동일 | sqlite.legacy-open / sqlite.final-reopen |
| 실제 현장 PoV·목표 Windows PC 전체 격리 | 미수행 | 아래 별도 범위 |

701은 544 unittest + P1 gate 105 + 별도 P3-A CLI 52다. 39개와 합계 740개가 같은 OS 격리 안에서 통과했다. Bifrost는 이 환경에서 실제 jar validate/서명 approve/publish/status를 실행했으며 기존 회귀에서도 Java receiver seam을 실행했다. 이전 A07의 Maven 60검사 기록은 변경 없는 jar의 역사적 증거로 유지한다. 이번에 전체 Maven reactor를 재실행했다고 주장하지 않는다.

## 차단 증거

[Docker 실제 설정](docker-inspect-after.json)은 NetworkMode=none, DNS=127.0.0.1, CapDrop=ALL, no-new-privileges 및 port publish 없음을 기록한다. 입력은 읽기 전용이며 Docker socket을 마운트하지 않았다.

[OS 인터페이스·주소·경로](a14-network.json)에는 lo 하나와 외부 IPv4/IPv6 경로 부재가 있다. Python 실제 IPv4/IPv6 TCP·UDP·외부 DNS 전송은 errno 101로 거부됐다. [Java probe](a14-java-network.json)도 외부 TCP/UDP 거부와 localhost HTTP 200을 대조한다. [브라우저 요청](a14-browser.json)·[HAR](a14-browser.har)는 외부 IP/호스트명 탐색 거부, 정상 요청의 localhost 경로, script error 0을 기록한다.

fetch interception·proxy·Python monkeypatch를 OS 차단 증거로 사용하지 않았다. 내부 test_p7.py의 javaAndBrowserOSIsolation=not-performed 필드는 그 runner 자체의 능력 범위다. 값을 덮어쓰지 않고 위 별도 OS/Docker 증거로 실행 경계를 입증한다.

## 실제 작성 → 승인 → 발행

1. A07 가상 fixture의 작성 revision 2에서 14 화면으로 a14-ui-alias를 생성해 revision 3. 부모는 a07-melsec-alarm@1.0.0이다.
2. 기존 view의 부모를 새 alias로 바꾸면서 의존 그래프/매핑의 근거를 누락한 변경은 422 evidence-incomplete로 거부했고 revision 3을 유지했다.
3. 기존 view의 원래 부모를 유지한 편집은 revision 4로 저장했다. 같은 ID의 중복 행을 만들지 않았다.
4. 06에서 alarm 의미를 a14-ui-alias에 연결해 revision 5. 화면 재로드와 SQLite 재개방에서 복원했다.
5. 09에 원본 D3000의 05 80을 입력했다. UInt16 32773 → bit 15 true → UI alias true → Boolean cast/정준 결과 true, quality=good, 오류/손실 0. 작성 revision 5 유지.
6. 13에서 a14-ui-submission / a14-offline-line으로 제출했다. 새 alias와 모든 의존 정의·근거가 실제 묶음에 포함됐다.
7. Java 독립 검증 후 proposer/approver 두 등록 Ed25519 키로 a14-approval을 서명하고 a14-release@1.0.0 파일 릴리스를 발행했다. 임시 개인 키 디렉터리는 삭제했다.
8. 화면에서 published·현재 작성본과 동일을 조회하고 ZIP/릴리스의 24파일 hash를 대조했다. 다시 로드해 같은 릴리스를 확인했다.

![격리 Chromium의 원본 바이트→bit→alias→cast](a14-preview.png)

![격리 Chromium의 Bifrost 발행 상태](a14-publication.png)

직접 브라우저 검사는 대표 alias/Boolean 경로다. low/high·단위·스케일·파생식·시간/품질·배열·selector·import·변경 검토와 오류/손실의 더 넓은 경우는 기존 fixture 회귀로 확인했다. 모든 폼 조합의 브라우저 coverage를 주장하지 않는다.

## 발견 및 보완

- frontend/views.js의 upsert에 definition.id가 빠져 기존 view 편집이 source: duplicate id로 거부되던 버그를 수정했다. 실제 브라우저의 기존 view 편집으로 재검증했다. API·SQLite 스키마·Bifrost 코드는 바꾸지 않았다.
- 초기 이미지의 전체 회귀는 700/701이었다. 선택적 date-time checker가 없어 bad-timestamp fixture가 실패했다. 기존 Schema의 date-time/uri 검사기를 명시적 의존성으로 고정하고 정상/오류 preflight를 추가했다. fixture나 수용 기준을 완화하지 않고 전체 701개를 다시 통과했다.
- Windows/Docker 9p metadata 지연은 Java thread dump의 stat0 → MappingJson.safe → MappingRegistry.status로 확인했다. 검증 DB/registry를 컨테이너 로컬 /work/evidence에 두고 runtime-evidence.tar로 결과를 일괄 반출했다. 제품 성능 개선이나 현장 저장소 성능 검증으로 계산하지 않는다.
- 초기 수집기·CSP 대기식·차단 오류 페이지 탐색·재로드 대기는 수용 harness에서 수정했다. 제품 CSP는 유지했다.

[전체 실행 이력](a14-run-history.json)에 중단/실패를 보존했다. 700/701 실행과 준비 중단을 최종 성공으로 집계하지 않는다. 최종 원본은 build/a14/20261018-010412에 남겼으며 container는 종료 후 제거했다. 이미지 sha256:58da69eebffaf1a3699b8d5557c68407dbd3d4377bcfb0f038aec704093ace31와 입력 archive/jar/파일 hash는 [집계](a14-summary.json)에 고정했다. 이미지 준비의 다운로드와 네트워크 없는 실제 실행은 분리했다.

## 현장 PoV와 완료 경계

[현장 PoV 절차](../P7-OFFLINE-ACCEPTANCE.md)의 실제 익명화 문서·솔루션 export/제품 버전·전후 개정본·독립 담당자 정답·오매핑/누락/손실·전체 검토 시간·타 설비 재사용성 측정은 미수행이다. 목표 현장 PC/VM의 배포 환경 수용도 별도다.

현재 결과는 가상 오프라인 기능 수용이다. 현장 정확도·시간 절감률이나 운영 수용 완료를 결론 내리지 않는다. 실제 장치 통신·외부 SQL·쓰기 실행·Muninn 활성화는 수행하지 않았다. 기존 Windows DB/registry 및 59772~59774 서버는 유지했다. commit/push/merge는 하지 않았다.
