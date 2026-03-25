# camel-workforce-studio

`camel-workforce-studio`는 범용 CAMEL 데모 레포가 아니라, [AI-Fashion-Forum](https://github.com/Jongtae/AI-Fashion-Forum)을 위한 companion decision workspace입니다. 이 저장소는 제품 본체를 구현하는 대신, GitHub issue, 외부 리포트, progress log, 이전 논의 결과를 정규화해서 여러 workforce 토론으로 넘기고, 그 결과를 다시 다음 논의나 GitHub handoff로 연결하는 역할을 맡습니다.

핵심 흐름은 `Context Builder -> Commitment/Core/Operator/Society Workforce -> Handoff`입니다. 즉 topic 하나만 던지는 토론기보다, “지금 무엇이 막혀 있고 다음에 어느 workforce가 무엇을 결정해야 하는가”를 구조적으로 다루는 companion repo에 가깝습니다.

## Workforce Model

- `commitment`: 현재 상태의 gap을 읽고 다음 workforce와 topic을 결정합니다.
- `core`: AI-Fashion-Forum mock을 실제 서비스로 전환하는 코어 구현 논의를 맡습니다.
- `operator`: 운영 조직의 관찰 프레임, 메트릭, 개입 레버를 설계합니다.
- `society`: 이용자 조직의 사회 규칙, 상태, 기억, 관계 모델을 설계합니다.
- `default`: 어느 특화 workforce에도 바로 맞지 않는 환경 설계를 다룹니다.

## Operating Flow

1. `scripts/context-builder/build_context.py`가 GitHub issue, 외부 리포트, progress log를 읽어 `context/workflow-inputs/*.md`를 만듭니다.
2. `commitment` workforce가 지금 가장 중요한 gap과 다음 workforce/topic을 결정합니다.
3. 선택된 workforce가 handoff와 context pack을 함께 읽고 토론합니다.
4. 각 실행은 `decision.md`, `handoff.md`, `next_questions.md`, `round_summary.md`, `full_report.md`를 남깁니다.
5. 다음 workforce 또는 GitHub issue 초안은 이 산출물을 기준으로 이어집니다.

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

context/
  README.md
  raw/
  normalized/
  workflow-inputs/

docs/
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

세부 규약은 [docs/workforce-handoff-contract.md](docs/workforce-handoff-contract.md) 에 정리되어 있습니다.

## Shared Memory Policy

이 저장소는 CAMEL memory보다 명시적 handoff 문서를 우선합니다. `share_memory`는 실험적으로 켤 수 있지만 기본값은 꺼져 있습니다.

- 기본 진실 원천: `handoff.md`, `decision.md`, `context/workflow-inputs/*.md`
- 선택적 런타임 보조: `--share-memory`
- 아직 기본 채택하지 않는 이유: 장기 컨텍스트는 CAMEL 내부 memory보다 GitHub issue, reports, progress log, handoff 문서가 더 투명하고 재검토 가능하기 때문입니다.

자세한 평가는 [docs/shared-memory-evaluation.md](docs/shared-memory-evaluation.md) 에 있습니다.
