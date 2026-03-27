# camel-workforce-studio

`camel-workforce-studio`는 범용 CAMEL 데모 레포가 아니라, [AI-Fashion-Forum](https://github.com/Jongtae/AI-Fashion-Forum)을 위한 companion decision workspace입니다. 이 저장소는 제품 본체를 구현하는 대신, GitHub issue, GitHub PR, 외부 리포트, progress log, 이전 논의 결과를 정규화해서 여러 workforce 토론으로 넘기고, 그 결과를 다시 다음 논의나 GitHub handoff로 연결하는 역할을 맡습니다.

핵심 흐름은 `Context Builder -> Commitment/Development/Operator/Society Workforce -> Handoff`입니다. 즉 topic 하나만 던지는 토론기보다, “지금 무엇이 막혀 있고 다음에 어느 workforce가 무엇을 결정해야 하는가”를 구조적으로 다루는 companion repo에 가깝습니다.

## Workforce Model

- `commitment`: 현재 상태의 gap을 읽고 다음 workforce와 topic을 결정합니다.
- `core`: 내부 키는 `core`지만, 사용자-facing으로는 `AI-Fashion-Forum`을 실제 서비스로 전환하는 `development` 팀입니다.
- `operator`: 포럼 운영자로서 컨텐츠 자정, 모니터링, 기능 개선사항 도출을 담당합니다.
- `society`: API 기반 forum 위에서 action하는 stateful AI agent의 상태, 기억, characteristic, 내부/외부 콘텐츠 소비 규칙을 설계합니다.
- `default`: 어느 특화 workforce에도 바로 맞지 않는 환경 설계를 다룹니다.

## Operating Flow

1. `scripts/context-builder/build_context.py`가 GitHub issue, GitHub PR, 외부 리포트, progress log, 선택적 sim-results를 읽어 `context/workflow-inputs/*.md`를 만듭니다.
2. `commitment` workforce가 지금 가장 중요한 gap과 다음 workforce/topic을 결정합니다.
3. 선택된 workforce가 handoff와 context pack을 함께 읽고 토론합니다.
4. 각 실행은 `decision.md`, `handoff.md`, `next_questions.md`, `round_summary.md`, `full_report.md`를 남깁니다.
5. issue를 발급하면 run-to-issue ledger가 `context/history/run-ledger.jsonl`에 기록됩니다.
6. 다음 workforce 또는 GitHub issue 초안은 이 산출물과 ledger를 기준으로 이어집니다.

## Repository Layout

```text
scripts/
  context-builder/
    build_context.py
  requirement-debate/
    debate.py
    commitment_debate.py
    core_debate.py
    operator_debate.py
    society_debate.py
    bridge_debate.py
    workforce_artifacts.py
    *_roles.yaml
    outputs/
  pipeline/
    run_studio.py

context/
  README.md
  history/
  raw/
  normalized/
  workflow-inputs/

docs/
  project-history-and-playbook.md
  ai-fashion-forum-readiness-scorecard.md
  iteration-log.md
  workforce-handoff-contract.md
  shared-memory-evaluation.md
```

## Quick Start

### 1. Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

환경 변수로 OpenAI API 키가 필요합니다.

```bash
export OPENAI_API_KEY=your_key_here
```

### 2. Build context packs

```bash
python3 scripts/context-builder/build_context.py --repo Jongtae/AI-Fashion-Forum
```

### 3. Run commitment and hand off automatically

```bash
python3 scripts/requirement-debate/commitment_debate.py \
  --context-pack context/workflow-inputs/commitment.md \
  --run-next
```

### 3-1. Run in semi-autonomous mode

```bash
python3 scripts/pipeline/run_studio.py \
  --repo Jongtae/AI-Fashion-Forum \
  --source-dir /Users/jongtaelee/Documents/AI-Fashion-Forum \
  --sim-results-dir /Users/jongtaelee/Documents/AI-Fashion-Forum/path/to/sim-results \
  --rounds 1
```

이 모드는 아래를 순서대로 수행합니다.

- AI-Fashion-Forum 로컬 repo의 git 상태, 최근 커밋, 변경 파일을 읽음
- GitHub issue, open/merged PR, 로컬 report/progress, 선택적 sim-results를 합쳐 context pack 생성
- 최신 workforce handoff가 있으면 자동으로 commitment 입력에 포함
- commitment 실행 후 선택된 다음 workforce까지 연쇄 실행

`--sim-results-dir`는 AI-Fashion-Forum 실험 산출물이 들어 있는 로컬 경로를 가리킵니다. 지정하지 않아도 `build_context.py`가 source repo 안의 표준 후보 경로를 자동 탐색합니다.

### 3-2. Run and issue AI-Fashion-Forum issues

```bash
python3 scripts/pipeline/run_studio.py \
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

실제 GitHub 발급까지 하려면 검토 후 `--approve-issue`를 추가합니다.

이 모드는 선택된 workforce 결과를 기준으로 아래를 생성할 수 있습니다.

- `single` 또는 `task`: 단일 실행 issue
- `epic`: umbrella issue
- `sprint`: sprint planning issue
- `bundle`: epic + ordered child tasks + optional sprint issue

`bundle`에서는 `Next Actions` 또는 `Acceptance Criteria`를 기준으로 child task를 만들고, `--task-assignee` 순서대로 담당자를 round-robin 배정합니다. sprint issue에는 담당자별 처리 순서도 함께 기록됩니다.

### 4. Run a specific workforce with handoff/context

```bash
python3 scripts/requirement-debate/core_debate.py \
  --topic "현재 mock을 실제 서비스로 전환할 때 가장 먼저 구현해야 할 end-to-end 루프는 무엇인가?" \
  --context-pack context/workflow-inputs/core.md
```

### 5. Bridge one workforce into another

```bash
python3 scripts/requirement-debate/bridge_debate.py \
  --from-workforce society \
  --to-workforce operator \
  --context-pack context/workflow-inputs/operator.md
```

## Output Contract

각 workforce 실행은 `scripts/requirement-debate/outputs/<timestamp>_<workforce>_<topic-slug>/` 아래에 표준 산출물을 저장합니다.

- `full_report.md`: 전체 라운드와 최종 합성 결과
- `decision.md`: 최종 결정문
- `handoff.md`: 다음 workforce로 넘길 구조화된 handoff
- `next_questions.md`: 후속 논의 질문
- `round_summary.md`: 라운드별 정리
- `metadata.json`: 실행 메타데이터
- `sim_results.md`: 선택적 AI-Fashion-Forum 실험 산출물 정규화본
- `society_output_contract.json`: 최신 society 결정을 구조화한 계약 파일
- `issue_plan.md`: issue-ready일 때 생성되는 발급 초안
- `context/history/run-ledger.jsonl`: 실행과 발급된 issue를 연결하는 ledger
- `context/normalized/active_pull_requests.md`: 현재 open PR 정규화
- `context/normalized/recent_merged_pull_requests.md`: 최근 merged PR 정규화

세부 규약은 [docs/workforce-handoff-contract.md](docs/workforce-handoff-contract.md) 에 정리되어 있습니다.

## Issue Issuance

이 저장소는 결과를 `AI-Fashion-Forum` 쪽 GitHub issue로 보낼 수 있습니다.

- 기본 대상 repo: `Jongtae/AI-Fashion-Forum`
- 대상 변경: `--issue-repo owner/repo`
- 발급 유형: `--issue-type single|task|epic|sprint|bundle`
- 추가 label: `--issue-label`
- epic label: `--epic-label`
- milestone: `--issue-milestone`
- project: `--issue-project`
- 담당자 배정: `--issue-assignee`, `--task-assignee`
- sprint 묶음 생성: `--with-sprint`

GitHub Actions에서 `AI-Fashion-Forum`에 issue를 실제로 생성하려면 `secrets.WORKFORCE_GH_TOKEN`(대상 repo 접근 권한이 있는 PAT 또는 GitHub App 토큰)과 `secrets.OPENAI_API_KEY`가 필요합니다.

주의:
- GitHub Project 추가는 `gh auth refresh -s project` 권한이 없으면 자동으로 생략됩니다.
- `bundle`은 Epic을 먼저 만들고, 그 아래 child task를 순서대로 발급합니다.
- child task의 처리 순서는 `Next Actions` 순서를 따릅니다.
- 닫힌 issue와 제목/핵심 키워드가 과하게 비슷하면 새 발급을 멈추고 `issue_plan.md`만 남깁니다.
- issue를 발급하면 해당 run과 issue URL/번호가 `context/history/run-ledger.jsonl`에 기록됩니다.
- 다음 `build_context.py` 실행은 ledger를 읽어 현재 issue 상태를 `context/normalized/issue_execution_history.md`에 반영합니다.
- GitHub에 이미 같은 제목의 issue가 있거나, 제목과 본문 핵심 키워드가 매우 비슷한 issue가 있으면 새로 만들지 않고 기존 issue를 재사용합니다.
- commitment와 각 workforce는 issue뿐 아니라 open PR과 최근 merged PR도 context source로 읽습니다.
- closed society backlog가 감지되면 commitment는 society 재선택보다 core/operator 전환을 우선합니다.
- `--create-issue`를 주면 먼저 `issue_plan.md` draft를 만듭니다.
- 실제 GitHub 발급은 `--approve-issue`를 함께 줬을 때만 수행합니다.
- `Issue Title`, `Summary`, `Acceptance Criteria`, `Next Actions`가 충분히 갖춰져 issue-ready 기준을 넘을 때만 draft/생성이 진행됩니다.

## Shared Memory Policy

이 저장소는 CAMEL memory보다 명시적 handoff 문서를 우선합니다. `share_memory`는 실험적으로 켤 수 있지만 기본값은 꺼져 있습니다.

- 기본 진실 원천: `handoff.md`, `decision.md`, `context/workflow-inputs/*.md`
- 선택적 런타임 보조: `--share-memory`
- 아직 기본 채택하지 않는 이유: 장기 컨텍스트는 CAMEL 내부 memory보다 GitHub issue, GitHub PR, reports, progress log, handoff 문서가 더 투명하고 재검토 가능하기 때문입니다.

자세한 평가는 [docs/shared-memory-evaluation.md](docs/shared-memory-evaluation.md) 에 있습니다.

## Project Knowledge Base

GitHub wiki 대신 레포 안 문서에 운영 지식을 남깁니다.

- [agent.md](agent.md): Codex 및 일반 coding agent용 저장소 운영 가이드
- [CLAUDE.md](CLAUDE.md): Claude Code용 저장소 운영 가이드
- [docs/project-history-and-playbook.md](docs/project-history-and-playbook.md): 왜 이 저장소를 만들었는지, 어떤 시행착오가 있었는지, 다음 사람이 어떻게 이어받아야 하는지
- [docs/ai-fashion-forum-readiness-scorecard.md](docs/ai-fashion-forum-readiness-scorecard.md): AI-Fashion-Forum 실전 활용 가능 판정 기준
- [docs/iteration-log.md](docs/iteration-log.md): iteration별 튜닝 기록과 점수 변화
- [docs/workforce-handoff-contract.md](docs/workforce-handoff-contract.md): workforce 간 전달 규약
- [docs/society-output-schema.md](docs/society-output-schema.md): society workforce 결과를 JSON/YAML 계약으로 재사용하는 규약

## Semi-Autonomous Boundary

이 저장소의 목표는 완전 무인 agent OS가 아니라 `semi-autonomous decision studio`입니다.

자동화하는 것:
- source repo 상태 읽기
- GitHub issue / PR / report / progress 수집
- latest handoff 자동 포함
- commitment 실행과 next workforce 체이닝
- 표준 산출물 저장

사람이 여전히 확인해야 하는 것:
- external report 중요도 판단
- 잘못된 route 결과 수정
- 실제 GitHub 반영 여부 승인
- 프로젝트 방향을 바꾸는 최종 결정

## Documentation Sync Rule

에이전트 작업 가이드를 바꾸는 변경이 있으면 아래 파일을 함께 갱신합니다.

- `agent.md`
- `CLAUDE.md`

두 파일은 항상 같은 운영 기준을 반영해야 합니다.
