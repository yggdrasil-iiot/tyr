# P6 후속: 여러 스트림의 의미 카탈로그

## 목적과 범위

하나의 구성된 Bifrost registry에 보존된 모든 파일 릴리스의 semantic URI를 비교한다. 현재 head에서 제거된 릴리스도 포함한다. 장치 입력이나 vendor native 정보는 필요하지 않다. 여러 registry의 연합·외부 사전 가져오기·자동 URI 병합은 이번 범위에 포함하지 않는다.

동일 URI의 scalar 계약은 `role/valueType/unit`이다. 이름·설명·range는 이 동일성 서명에 포함하지 않는다. range는 기존 정적 검증과 제출 변경 보고서에서 계속 검토한다. Structure는 memberId별 child URI와 재귀 서명, StructureArray는 이에 shape와 lowerBounds를 더한다. 컨테이너 계약이 달라지면 말단 URI가 같아도 컨테이너 URI는 새로 정의해야 한다. 이는 물리적 의미의 자동 증명이 아니라 이미 합의한 URI의 계약 일관성 검사다.

## 재사용과 새 구현

기존 2.9 submission/approval/release, Ed25519 등록 키·권한·두 확인자, 파일 무결성, registry lock, head CAS, 복구 저널과 보수적 GC를 재사용한다. LogicalStructure의 독립 Java signature와 Týr의 Python signature를 각각 사용하며 코드를 공유하지 않는다.

새 보고서 계약은 `contracts/2.16.0/semantic-catalog.schema.json`이다. 기존 제안 문서 버전을 올리지 않는다. `mapping catalog <registry>`는 검증한 모든 릴리스와 URI별 signature variant, 정의 ID/버전·전체 authored member 경로·레이블·스트림/릴리스/SHA 근거를 반환한다. 구조 배열은 index별 실행값이 아닌 authored 정의를 기록하며 shape/bounds를 서명에 포함한다. catalogSha256은 자신을 제외한 정렬 JSON의 SHA-256이다. 문서·릴리스 순서를 고정해 같은 역사에서 같은 digest를 계산한다.

pending journal이 있으면 복구 후 조회한다. 과거 릴리스의 파일·서명·payload inventory·head SHA가 틀리면 조회를 거부하며 불완전한 빈 카탈로그를 성공으로 반환하지 않는다. 기존 역사에 계약 충돌이 있으면 variant와 compatible=false를 보여주고 새 승인·발행을 차단한다. 승인·발행 시 각각 현재 전체 역사를 다시 검사하므로 승인 후 다른 스트림이 충돌 URI를 발행했어도 우회할 수 없다. 복구도 원래 intent의 계약과 보존 역사를 비교한다.

한 registry에 릴리스 256개·URI 4096개·보고서 4MiB의 제한을 둔다. 대량 규모·외부 anchor/rollback 증명·키 운영 책임은 별도다. unsigned release metadata의 기존 설계 한계와 외부 신뢰 anchor의 미완료 상태를 이번 카탈로그가 해결했다고 간주하지 않는다.

## 화면·저장 경계

13 화면의 ‘의미 카탈로그 조회·작성본 비교’가 `/api/semantic-catalog`를 읽는다. 현재 SQLite revision/workspace SHA와 registry history를 함께 표시한다. 작성본 내부 충돌, 보존 릴리스 충돌, 계약 일치, 신규 URI, registry 미조회를 구분한다. 전체 registry URI의 signature와 각 릴리스 근거도 펼쳐 확인한다. CLI 미설정/구버전/손상/중단 상태를 호환 확인으로 승격하지 않는다.

카탈로그는 파생 조회 자료이며 새 SQLite 테이블·migration·workspace 재작성·캐시를 만들지 않는다. 기존 작성/저장/preview/export 경로를 그대로 이용한다. 카탈로그 비교 자체는 workspace 변경을 막지 않는다. draft에서 충돌을 검토하고 새 URI를 명시적으로 선택할 수 있으며 Bifrost가 승인·발행을 최종 거부한다. Týr HTTP/화면에 승인·개인 키·복구 실행 권위를 추가하지 않는다.

## 검증과 현장 PoV

[합성 사례](../fixtures/semantic-catalog/README.md)와 [수용 기록](verification/SEMANTIC-CATALOG-RESULTS.md)을 구분한다. 네 PLC 접근·기존 graph·SQLite·서명 발행 회귀를 재사용하고 서로 다른 stream의 계약 일치/충돌·지연 승인·중첩 멤버·unheaded history·손상·pending 복구를 시험한다.

실제 URI 소유자, 의미 동등성, 단위 표준화 합의, 정상적인 의미 개정/폐기 정책, 실제 검토 시간·오매핑률은 현장 PoV에 남긴다. 장치 통신·외부 SQL·쓰기 실행·runtime 활성화는 계속 제외한다.
