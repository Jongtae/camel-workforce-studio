# Issue Thread Continuation Memory Design

## Problem

현재 duplicate guard는 동일하거나 유사한 issue가 새로 발급되는 것을 막는다. 이 방식은 중복 폭증을 줄이지만, 이미 발급된 issue를 이어서 발전시키는 경로가 약하다. 결과적으로 `issue = memory record`가 아니라 `issue = stop signal`처럼 작동하기 쉽다.

## Goal

GitHub issue thread를 CAMEL-style workflow memory에 더 가깝게 사용한다.

- closed or duplicate issue를 단순 차단하지 않는다.
- 기존 issue thread에 continuation comment를 남겨 다음 round의 memory record로 남긴다.
- run ledger와 normalized context가 issue thread의 현재 상태를 요약한다.
- commitment와 downstream workforce는 thread summary를 읽고, 다음 action/role/topic을 고른다.

## Proposed Layers

### 1. Thread Summary Layer

각 issue thread마다 다음 요약을 저장한다.

- current state
- latest decision
- active blockers
- next workforce
- next topic
- linked PRs / commits
- continuation notes

### 2. Continuation Comment Layer

닫힌 issue 또는 중복 issue가 감지되면 새 issue를 만들지 않고 기존 thread에 continuation comment를 남긴다.

Comment should include:

- current run topic
- matched issue number/title/state
- why the new run is a continuation rather than a new ticket
- current draft body or next candidate summary

### 3. Retrieval Layer

commitment / society / core / operator는 다음 source들을 함께 본다.

- GitHub issue thread
- continuation comments
- run ledger
- issue_execution_history
- latest handoff / decision
- recent PRs / commits

### 4. Reflection Layer

각 run 종료 시 `reflection.md`를 생성한다.

- 무엇이 맞았는지
- 무엇이 막혔는지
- 다음 run에서 바꿀 것
- 다음 workforce로 넘길 핵심 질문

## Acceptance Criteria

- duplicate or closed similar issue가 새 issue 생성으로 이어지지 않는다.
- 대신 기존 issue에 continuation comment가 남는다.
- run ledger와 normalized context에 thread continuation state가 반영된다.
- 다음 commitment run이 continuation state를 읽고 더 나은 workforce routing을 만든다.
- thread summary와 reflection note를 사람이 읽어도 현재 상태를 빠르게 이해할 수 있다.

## Initial Scope

- current duplicate guard을 continuation note 방식으로 정리
- `issue_execution_history.md`에 thread status 요약 추가
- `reflection.md` 산출물 추가
- `commitment` prompt에 continuation-aware guard 추가

## Non-goals

- 완전한 자동 merge system
- PR review automation
- full agentic memory DB

