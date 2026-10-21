# Synthetic semantic URI lifecycle

기존 p4b mixed-source workspace의 주소·매핑·근거를 유지하고 첫 pressure URI의 metadata revise revision 1과 deprecate revision 2를 추가한다. 모든 자료는 가상 fixture이며 장치 통신이 없다.

- workspace.json: SQLite/화면 입력.
- cases.json: 독립 signature/영향 개수/state oracle와 revision 3 retire 이벤트.
- bundle/: 실제 Bifrost가 읽는 2.18 immutable wire bundle. 동일 사본은 Java test resources에 있다.

폐기 후에도 로컬 매핑 초안을 보존하지만 해당 binding은 승인·발행할 수 없다. lifecycle-only 제출 또는 명시적인 새 URI 재매핑으로 정리한다. nested/array 조상 영향은 기존 p3eb fixture를 사용한다.
