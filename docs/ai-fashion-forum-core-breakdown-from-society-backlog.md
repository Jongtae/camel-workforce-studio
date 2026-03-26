# AI-Fashion-Forum Core Breakdown From Society Backlog

## Purpose

이 문서는 society backlog에서 정리된 agent action-state backend 요구사항을
AI-Fashion-Forum 구현팀 관점의 실제 development backlog로 다시 나누기 위해 작성했다.

기준 입력:

- society epic/task/sprint: `#184` ~ `#189`
- latest commitment handoff:
  [`/Users/jongtaelee/Documents/camel-workforce-studio/scripts/requirement-debate/outputs/20260326_233019_commitment_gap-_-_-_workforce/handoff.md`](/Users/jongtaelee/Documents/camel-workforce-studio/scripts/requirement-debate/outputs/20260326_233019_commitment_gap-_-_-_workforce/handoff.md)
- latest society decision:
  [`/Users/jongtaelee/Documents/camel-workforce-studio/scripts/requirement-debate/outputs/20260326_232047_society_ai_agent-_-_-_post-comment-react-lurk-silence-_-_-_-_-_-_-_-_backend/decision.md`](/Users/jongtaelee/Documents/camel-workforce-studio/scripts/requirement-debate/outputs/20260326_232047_society_ai_agent-_-_-_post-comment-react-lurk-silence-_-_-_-_-_-_-_-_backend/decision.md)

## Current Read

현재 확인된 사실:

- `#184` ~ `#189`는 GitHub에서 모두 `CLOSED` 상태다.
- 따라서 society backlog의 "문서 정리" 단계는 끝났다고 봐야 한다.
- 다음 논의는 society를 반복하는 것이 아니라, 문서화된 contract를 구현 가능한 backend/API vertical slice로 내리는 것이 맞다.

관련 코드 진실 원천:

- agent loop route:
  [`/Users/jongtaelee/Documents/AI-Fashion-Forum/apps/sim-server/src/routes/agent-loop.js`](/Users/jongtaelee/Documents/AI-Fashion-Forum/apps/sim-server/src/routes/agent-loop.js)
- action choice:
  [`/Users/jongtaelee/Documents/AI-Fashion-Forum/packages/agent-core/action-space.js`](/Users/jongtaelee/Documents/AI-Fashion-Forum/packages/agent-core/action-space.js)
- identity update:
  [`/Users/jongtaelee/Documents/AI-Fashion-Forum/packages/agent-core/identity-update-rules.js`](/Users/jongtaelee/Documents/AI-Fashion-Forum/packages/agent-core/identity-update-rules.js)
- state schema:
  [`/Users/jongtaelee/Documents/AI-Fashion-Forum/packages/shared-types/state-schema.js`](/Users/jongtaelee/Documents/AI-Fashion-Forum/packages/shared-types/state-schema.js)
- existing queue contract:
  [`/Users/jongtaelee/Documents/AI-Fashion-Forum/docs/core-systems/sim-server-api-and-queue.md`](/Users/jongtaelee/Documents/AI-Fashion-Forum/docs/core-systems/sim-server-api-and-queue.md)

## Important Mismatches

구현 전에 바로 잡아야 하는 어긋남:

1. `#185` summary는 `apps/agent-server/src/routes/agent-loop.js`를 가리키지만,
   현재 실제 파일은 [`/Users/jongtaelee/Documents/AI-Fashion-Forum/apps/sim-server/src/routes/agent-loop.js`](/Users/jongtaelee/Documents/AI-Fashion-Forum/apps/sim-server/src/routes/agent-loop.js) 이다.

2. society backlog는 `learn` / `reflect`까지 언급하지만,
   현재 구현 코드에서 즉시 확인되는 visible action space는 `post / comment / react / lurk / silence`다.
   따라서 Sprint 1의 구현 목표는 `learn/reflect를 정식 action으로 추가`가 아니라,
   `memory writeback과 replayable trace를 통해 learn/reflect를 위한 기반을 깐다`로 잡는 편이 맞다.

3. current `agent-loop` route는
   - post/comment persistence
   - AgentState snapshot persistence
   - Interaction insert
   까지는 하지만,
   society backlog가 요구한 `trace / snapshot / event / stored action / forum artifact` vocabulary로 정리되어 있지는 않다.

## Recommended Core Vertical Slice

다음 구현 라운드는 큰 주제를 다시 토론하는 대신 아래 4개 slice로 쪼개는 게 가장 좋다.

### Slice 1. Action Execution Contract

목표:

- `post / comment / react / lurk / silence`를 backend 실행 단위로 고정한다.
- 각 action의 공통 request/result envelope를 정의한다.

필요 산출물:

- action request shape
- action execution result shape
- success / blocked / skipped / stored_only status vocabulary
- target content required 여부

코드 접점:

- [`/Users/jongtaelee/Documents/AI-Fashion-Forum/packages/agent-core/action-space.js`](/Users/jongtaelee/Documents/AI-Fashion-Forum/packages/agent-core/action-space.js)
- [`/Users/jongtaelee/Documents/AI-Fashion-Forum/apps/sim-server/src/routes/agent-loop.js`](/Users/jongtaelee/Documents/AI-Fashion-Forum/apps/sim-server/src/routes/agent-loop.js)

### Slice 2. State Snapshot And Memory Writeback

목표:

- 행동 후 어떤 state field가 읽히고 어떤 field가 갱신되는지 명시한다.
- `identity-update-rules`와 `AgentState` persistence를 같은 vocabulary로 연결한다.

필요 산출물:

- state read keys
- state write keys
- memory writeback record shape
- state snapshot linkage key

코드 접점:

- [`/Users/jongtaelee/Documents/AI-Fashion-Forum/packages/agent-core/identity-update-rules.js`](/Users/jongtaelee/Documents/AI-Fashion-Forum/packages/agent-core/identity-update-rules.js)
- [`/Users/jongtaelee/Documents/AI-Fashion-Forum/packages/shared-types/state-schema.js`](/Users/jongtaelee/Documents/AI-Fashion-Forum/packages/shared-types/state-schema.js)
- [`/Users/jongtaelee/Documents/AI-Fashion-Forum/apps/sim-server/src/models/AgentState.js`](/Users/jongtaelee/Documents/AI-Fashion-Forum/apps/sim-server/src/models/AgentState.js)

### Slice 3. Artifact Persistence Layer

목표:

- society backlog의 `trace / snapshot / event / stored action / forum artifact`를 실제 저장 계층으로 분리한다.
- 최소한 Sprint 1에서는 어떤 것은 문서화만 하고, 어떤 것은 즉시 Mongo에 넣을지 정한다.

필요 산출물:

- trace schema
- event schema
- stored action schema
- forum artifact linkage
- write owner:
  - `agent-core`
  - `sim-server`
  - Mongo model

코드 접점:

- [`/Users/jongtaelee/Documents/AI-Fashion-Forum/apps/sim-server/src/models/Interaction.js`](/Users/jongtaelee/Documents/AI-Fashion-Forum/apps/sim-server/src/models/Interaction.js)
- [`/Users/jongtaelee/Documents/AI-Fashion-Forum/apps/sim-server/src/models/Post.js`](/Users/jongtaelee/Documents/AI-Fashion-Forum/apps/sim-server/src/models/Post.js)
- [`/Users/jongtaelee/Documents/AI-Fashion-Forum/apps/sim-server/src/models/Comment.js`](/Users/jongtaelee/Documents/AI-Fashion-Forum/apps/sim-server/src/models/Comment.js)

### Slice 4. Internal/External Content Ingestion Hook

목표:

- forum input과 external input이 같은 state/memory path로 들어가도록 ingestion envelope를 정의한다.
- Sprint 1에서는 full crawler보다 `normalized input contract`를 먼저 고정한다.

필요 산출물:

- internal content envelope
- external content envelope
- shared exposure payload
- writeback entry point

코드 접점:

- [`/Users/jongtaelee/Documents/AI-Fashion-Forum/packages/agent-core/identity-update-rules.js`](/Users/jongtaelee/Documents/AI-Fashion-Forum/packages/agent-core/identity-update-rules.js)
- [`/Users/jongtaelee/Documents/AI-Fashion-Forum/docs/core-systems/content-provider-normalization.md`](/Users/jongtaelee/Documents/AI-Fashion-Forum/docs/core-systems/content-provider-normalization.md)

## Proposed Development Order

다음 순서가 제일 자연스럽다:

1. action execution contract 정리
2. state snapshot / memory writeback 연결
3. artifact persistence schema 확정
4. internal/external ingestion hook 연결
5. 마지막에 queue/tick route에 stitch

즉 구현 순서는 `185 -> 186 -> 187 -> 188` 이름 그대로가 아니라,
아래처럼 다시 묶는 편이 더 좋다.

1. action contract
2. state transition + memory writeback
3. artifact schema
4. ingestion bridge

## Suggested New Issue Set

닫힌 `#184` ~ `#189`를 반복 재사용하기보다, 다음 라운드는 아래 구현 이슈로 새로 여는 것을 추천한다.

### Issue A

제목:

`Implementation: Agent action execution contract for post/comment/react/lurk/silence`

완료 기준:

- action request/result envelope가 문서로 정의된다.
- `stored_only`, `public_visible`, `public_lightweight` 같은 visibility/status vocabulary가 정리된다.
- `agent-loop.js`와 `action-space.js`에서 같은 용어를 쓰도록 기준이 마련된다.

### Issue B

제목:

`Implementation: State snapshot and memory writeback contract for agent loop`

완료 기준:

- 행동 후 어떤 state field를 읽고 쓰는지 필드 수준으로 정리된다.
- `identity-update-rules.js`와 `AgentState` persistence가 같은 linkage key를 공유한다.
- Sprint 1에서 `learn/reflect`를 action으로 구현하지 않더라도 writeback 기반이 마련된다.

### Issue C

제목:

`Implementation: Trace/event/stored-action/forum-artifact schema for sim-server`

완료 기준:

- trace / event / stored action / forum artifact schema가 정리된다.
- Mongo write 책임이 구분된다.
- `Interaction`, `Post`, `Comment`, `AgentState`와의 연결 키가 명시된다.

### Issue D

제목:

`Implementation: Internal/external content ingestion envelope for agent identity updates`

완료 기준:

- forum/internal content와 external content를 같은 exposure payload로 정리한다.
- identity update 진입점이 단일 vocabulary를 사용한다.
- external fetch는 보류하더라도 ingestion contract는 고정된다.

## Decision

다음 논의는 다시 `society`가 아니라 `core(development)`가 맡는 게 맞다.

더 정확히는:

- society는 이미 요구사항을 만들었고
- closed issue `#184` ~ `#189`로 문서화까지 끝냈고
- 이제 development 팀이 실제 구현 계약과 vertical slice를 나눠야 한다

따라서 다음 commitment 없이도,
다음 작업은 `Issue A`부터 개발 이슈로 여는 것이 자연스럽다.
