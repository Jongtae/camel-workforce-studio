# Source Repo Read-Only Policy

`camel-workforce-studio`는 `AI-Fashion-Forum`을 위한 decision workspace다.

원칙:

- `AI-Fashion-Forum`은 읽기 전용 source repo로 취급한다.
- 여기서 수행하는 일은 context 수집, 토론, issue 초안화, continuation comment, handoff 생성까지다.
- source repo의 파일을 직접 수정하거나, code change를 적용하거나, 화면/동작을 바꾸는 작업은 하지 않는다.
- 실제 구현이 필요하면 반드시 issue로 발급하고, 그 issue를 대상 repo의 담당 작업으로 넘긴다.

이 정책의 목적은:

- decision workspace와 product repo의 책임을 분리하고
- issue-ready slice만 외부로 전달하며
- 실수로 target repo를 직접 수정하는 일을 막는 것이다.
