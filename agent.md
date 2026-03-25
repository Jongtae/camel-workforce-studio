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
5. GitHub issue / report / progress log

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

`bundle`은 아래를 생성한다.

- Epic issue
- ordered child task issues
- optional sprint planning issue

`--task-assignee`를 주면 child task는 round-robin으로 담당자에게 배정된다.
sprint issue에는 담당자별 처리 순서가 같이 기록된다.

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

이 저장소는 AI-Fashion-Forum issue 발급을 지원한다.

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

## When Updating This Repo

구조나 운영 원칙을 바꾸면 함께 갱신할 문서:

- `agent.md`
- `CLAUDE.md`
- `README.md`
- `docs/project-history-and-playbook.md`
- `docs/ai-fashion-forum-readiness-scorecard.md`
- `docs/iteration-log.md`

이 저장소는 wiki가 없으므로, 중요한 운영 지식은 반드시 레포 안 문서로 남긴다.
