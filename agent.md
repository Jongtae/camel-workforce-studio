# agent.md

이 파일은 Codex를 포함한 agentic coding assistant가 `camel-workforce-studio`를 다룰 때 참고하는 작업 가이드다.

## Sync Policy

이 파일의 내용이 바뀌면 반드시 `CLAUDE.md`도 함께 갱신해야 한다.
반대로 `CLAUDE.md`가 바뀌면 `agent.md`도 같은 의미로 동기화해야 한다.

두 파일은 표현만 약간 다를 수 있지만, 아래 항목은 항상 같은 기준을 유지해야 한다.

- repository intent
- workforce roles
- source of truth
- standard operating loop
- issue issuance rules
- iteration and issue ledger rules
- society quality bar
- 문서 갱신 규칙

## Repository Intent

이 저장소는 범용 CAMEL 데모가 아니다.
목표는 [AI-Fashion-Forum](https://github.com/Jongtae/AI-Fashion-Forum)을 위한 companion decision studio를 운영하는 것이다.

핵심 흐름:

`Context Builder -> Commitment -> Selected Workforce -> Handoff -> AI-Fashion-Forum Issue`

즉, 제품 코드 자체보다 "무엇을 다음에 결정해야 하는가"를 구조화하는 저장소다.

## Workforce Roles

- `commitment`
  - 현재 상황에서 가장 중요한 gap을 읽고 다음 workforce와 topic을 정한다.
  - 가능한 한 AI-Fashion-Forum source repo intent를 직접 근거로 삼아야 한다.

- `core`
  - 사용자-facing 의미는 development 팀이다.
  - mock-to-service, API, migration, execution loop, backend implementation을 다룬다.

- `operator`
  - 운영자 조직이다.
  - moderation, monitoring, policy, intervention, improvement를 다룬다.

- `society`
  - 추상 사회이론이 아니다.
  - API 기반 forum 위에서 action하는 stateful AI agent backend requirement를 다룬다.
  - 항상 아래 다섯 요소를 함께 다루는지 확인한다:
    - action loop
    - state model
    - state transitions
    - content consumption
    - required backend artifacts

## Source Of Truth

이 저장소는 CAMEL memory보다 명시적 문서를 우선한다.

우선순위:

1. `context/workflow-inputs/*.md`
2. `scripts/requirement-debate/outputs/*/decision.md`
3. `scripts/requirement-debate/outputs/*/handoff.md`
4. AI-Fashion-Forum source repo 상태
5. GitHub issue / PR / report / progress log

## Standard Operating Loop

### 1. Build context

```bash
source .venv/bin/activate
python scripts/context-builder/build_context.py \
  --repo Jongtae/AI-Fashion-Forum \
  --source-dir /Users/jongtaelee/Documents/AI-Fashion-Forum
```

### 2. Run commitment and chain next workforce

```bash
python scripts/pipeline/run_studio.py \
  --repo Jongtae/AI-Fashion-Forum \
  --source-dir /Users/jongtaelee/Documents/AI-Fashion-Forum \
  --rounds 1
```

### 3. Issue bundle issuance

```bash
python scripts/pipeline/run_studio.py \
  --repo Jongtae/AI-Fashion-Forum \
  --source-dir /Users/jongtaelee/Documents/AI-Fashion-Forum \
  --rounds 1 \
  --create-issue \
  --issue-type bundle \
  --epic-label epic:forum-actions \
  --issue-milestone "Sprint 1 - Identity Loop Vertical Slice" \
  --task-assignee jongtae \
  --task-assignee alice \
  --with-sprint
```

실제 GitHub issue까지 만들려면 검토 후 `--approve-issue`를 추가한다.

`bundle`은 아래를 생성한다.

- Epic issue
- ordered child task issues
- optional sprint planning issue

`--task-assignee`를 주면 child task는 round-robin으로 담당자에게 배정된다.
sprint issue에는 담당자별 처리 순서가 같이 기록된다.

issue를 발급한 run은 반드시 `context/history/run-ledger.jsonl`에 기록되어야 한다.
다음 `build_context.py` 실행은 이 ledger를 읽어 현재 issue 상태를 `context/normalized/issue_execution_history.md`로 다시 정규화해야 한다.
`context-builder`는 issue thread summary도 만들어 `context/normalized/issue_thread_summary.md`와 `context/workflow-inputs/*.md`에 포함해야 한다.
같은 실행에서 open PR과 최근 merged PR도 `context/normalized/active_pull_requests.md`, `context/normalized/recent_merged_pull_requests.md`로 정규화해야 한다.
GitHub에 이미 같은 제목의 issue가 있거나, 제목과 본문 핵심 키워드가 매우 비슷한 issue가 있으면 새로 만들지 않고 기존 issue를 재사용해야 한다.
`context-builder`는 선택적으로 AI-Fashion-Forum의 sim-results를 읽어 `context/normalized/sim_results.md`와 `context/normalized/society_output_contract.json`으로 정규화해야 한다.

## Society Quality Bar

Codex가 `society` 관련 프롬프트/출력을 수정할 때는 아래 기준을 유지해야 한다.

- `post/comment/react/lurk/silence`를 직접 다룰 것
- 각 action에 대해 다음을 가능하면 모두 포함할 것
  - trigger condition
  - state read
  - state write
  - artifact
  - successful outcome
- internal forum content consumption과 external web content consumption을 같은 state/memory loop에 연결할 것
- trace, snapshot, event, forum artifact의 필요성을 설명할 것

## Issue Issuance Rules

이 저장소는 `AI-Fashion-Forum` issue 발급을 기본으로 지원한다.

중요 옵션:

- `--issue-repo`
- `--issue-type single|task|epic|sprint|bundle`
- `--issue-label`
- `--epic-label`
- `--issue-assignee`
- `--task-assignee`
- `--issue-milestone`
- `--issue-project`
- `--with-sprint`

주의:

- GitHub Project 추가는 PAT/project scope가 없으면 실패할 수 있다.
- 이 경우 issue 생성은 유지하고 project 추가만 생략하는 것이 현재 정책이다.
- issue를 발급하는 변경은 run ledger와 metadata 반영까지 함께 유지해야 한다.
- `--create-issue`는 issue-ready 결과에만 적용한다. 최소 기준은 `Issue Title`, 충분한 `Summary`, 2개 이상의 `Acceptance Criteria`, 그리고 착수 가능한 `Next Actions`다.
- `--create-issue`만 주면 먼저 `issue_plan.md` draft를 저장한다.
- 실제 GitHub 발급은 `--approve-issue`를 함께 줬을 때만 수행한다.
- GitHub에 같은 제목의 issue가 이미 있으면 중복 생성 대신 기존 issue를 재사용한다.
- 닫힌 issue와 제목/핵심 키워드가 과하게 비슷하면 새 발급을 중단하고 기존 issue에 continuation comment만 남긴다.
- closed society backlog가 보이면 commitment는 society 재선택보다 core/operator로 넘기는 것을 우선한다.

## When Updating This Repo

구조나 운영 원칙을 바꾸면 함께 갱신할 문서:

- `agent.md`
- `CLAUDE.md`
- `README.md`
- `docs/project-history-and-playbook.md`
- `docs/ai-fashion-forum-readiness-scorecard.md`
- `docs/iteration-log.md`

이 저장소는 wiki가 없으므로, 중요한 운영 지식은 반드시 레포 안 문서로 남긴다.
