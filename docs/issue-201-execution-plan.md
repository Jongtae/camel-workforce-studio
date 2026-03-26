# Issue 201 Execution Plan

## Target

- GitHub issue:
  [#201](https://github.com/Jongtae/AI-Fashion-Forum/issues/201)
- Title:
  `Implement action execution contract for post/comment/react/lurk/silence`

## Why This First

현재 AI-Fashion-Forum은 action 선택 로직과 tick route가 이미 존재한다.

핵심 파일:

- [`/Users/jongtaelee/Documents/AI-Fashion-Forum/packages/agent-core/action-space.js`](/Users/jongtaelee/Documents/AI-Fashion-Forum/packages/agent-core/action-space.js)
- [`/Users/jongtaelee/Documents/AI-Fashion-Forum/apps/sim-server/src/routes/agent-loop.js`](/Users/jongtaelee/Documents/AI-Fashion-Forum/apps/sim-server/src/routes/agent-loop.js)
- [`/Users/jongtaelee/Documents/AI-Fashion-Forum/packages/shared-types/action-schema.js`](/Users/jongtaelee/Documents/AI-Fashion-Forum/packages/shared-types/action-schema.js)

즉 다음 단계는 "새로운 큰 구조를 상상"하는 것이 아니라,
이미 있는 action vocabulary를 execution contract로 고정하는 것이다.

## Current Code Read

현재 확인된 사실:

- `action-space.js`는 `silence`, `lurk`, `react`, `comment`를 직접 생성한다.
- `post`는 현재 `chooseForumAction()`에서 직접 나오지 않고, tick replay entry 처리 쪽에서 주로 다뤄진다.
- action record는 이미 `action_id`, `tick`, `agent_id`, `type`, `target_content_id`, `visibility`, `payload`, `ui` 구조를 가진다.
- visibility는 현재 최소한 아래 3개가 실제 코드에 있다:
  - `stored_only`
  - `public_lightweight`
  - `public_visible`
- `agent-loop.js`는 replay entry를 받아 post/comment persistence를 하며, state snapshot과 interaction 기록도 일부 남긴다.

## Execution Goal

이번 이슈의 목표는 action 실행을 위한 공통 contract를 먼저 고정하는 것이다.

즉 아래 질문에 답해야 한다:

1. action request는 어떤 shape인가
2. action result는 어떤 shape인가
3. 어떤 action은 `target_content_id`가 필수인가
4. 어떤 visibility/status가 가능한가
5. 어떤 action이 어디에 persist되는가

## Proposed Deliverables

### 1. Action Execution Contract Doc

추천 위치:

- `docs/core-systems/agent-action-execution-contract.md`

반드시 포함할 섹션:

- action type matrix
- request envelope
- result envelope
- visibility vocabulary
- target requirements
- persistence/write owner

### 2. Shared Vocabulary Alignment

반드시 정리할 키:

- `action_id`
- `agent_id`
- `tick`
- `type`
- `target_content_id`
- `visibility`
- `payload`
- `ui`
- `status`
- `block_reason`

`status`와 `block_reason`는 아직 명시적으로 없더라도 이번 이슈에서 먼저 contract level에 올리는 게 좋다.

## Recommended Breakdown

### Step 1. Action Matrix

각 action에 대해 아래를 표나 bullet로 정리:

- `post`
- `comment`
- `react`
- `lurk`
- `silence`

각 action별 필수 필드:

- visible or stored only
- target required 여부
- payload minimum keys
- persistence target

### Step 2. Request Envelope

초안:

- `action_id`
- `agent_id`
- `tick`
- `type`
- `target_content_id`
- `visibility`
- `payload`

주의:

- `post`는 target이 없을 수 있다
- `comment`와 `react`는 target이 필요하다
- `lurk`는 target이 있을 수도 있고 없을 수도 있는데 Sprint 1에서는 target thread/content 기준으로 고정하는 편이 낫다

### Step 3. Result Envelope

초안:

- `action_id`
- `status`
- `persisted_entities`
- `state_write_keys`
- `artifact_refs`
- `block_reason`

권장 `status`:

- `executed`
- `stored_only`
- `blocked`
- `skipped`

### Step 4. Persistence Boundary

정리 대상:

- 어떤 action이 `Post`를 만든다
- 어떤 action이 `Comment`를 만든다
- 어떤 action은 `Interaction`만 남긴다
- 어떤 action은 `AgentState` snapshot과만 연결된다

현재 코드 기준 가설:

- `post` -> `Post`
- `comment` -> `Comment`
- `react` -> currently lightweight reaction contract but persistence boundary needs explicit definition
- `lurk` -> stored trace only
- `silence` -> stored trace/state only

## File Touch List

이번 이슈에서 직접 보게 될 파일:

- [`/Users/jongtaelee/Documents/AI-Fashion-Forum/packages/agent-core/action-space.js`](/Users/jongtaelee/Documents/AI-Fashion-Forum/packages/agent-core/action-space.js)
- [`/Users/jongtaelee/Documents/AI-Fashion-Forum/packages/shared-types/action-schema.js`](/Users/jongtaelee/Documents/AI-Fashion-Forum/packages/shared-types/action-schema.js)
- [`/Users/jongtaelee/Documents/AI-Fashion-Forum/apps/sim-server/src/routes/agent-loop.js`](/Users/jongtaelee/Documents/AI-Fashion-Forum/apps/sim-server/src/routes/agent-loop.js)
- [`/Users/jongtaelee/Documents/AI-Fashion-Forum/docs/core-systems/action-space-and-light-reactions.md`](/Users/jongtaelee/Documents/AI-Fashion-Forum/docs/core-systems/action-space-and-light-reactions.md)
- [`/Users/jongtaelee/Documents/AI-Fashion-Forum/docs/core-systems/sim-server-api-and-queue.md`](/Users/jongtaelee/Documents/AI-Fashion-Forum/docs/core-systems/sim-server-api-and-queue.md)

## Definition Of Done

이번 이슈는 아래가 되면 끝난다:

- `post/comment/react/lurk/silence`의 request/result contract가 한 문서에 정리된다
- visibility vocabulary가 고정된다
- `target_content_id` required 여부가 action별로 정해진다
- persistence 책임이 `sim-server`/model 기준으로 설명된다
- 다음 이슈 `#202`, `#203`이 이 문서를 그대로 입력으로 쓸 수 있다

## Not In This Issue

이번 이슈에서 하지 않을 것:

- external ingestion 구현
- state snapshot schema 상세 정의
- trace/event/stored-action schema 상세 정의
- operator dashboard read model

## Suggested Immediate Start

가장 작은 첫 변경은 이거다:

1. `docs/core-systems/agent-action-execution-contract.md` 생성
2. `action-space.js`의 action별 필드와 `agent-loop.js`의 persistence 지점을 같은 vocabulary로 옮겨 적기
3. `status` / `block_reason`를 contract 초안에만 먼저 추가

즉, `#201`은 코드 구현보다 먼저 "실행 계약 문서"를 고정하는 문서+경계 정의 이슈로 처리하는 게 가장 좋다.
