# Ralph Loop: MVP v1 Topic Catalog Progression (Iterations=3)

Execute the MVP v1 workflow to progress through topic catalog slices.
Maximum 3 iterations - each iteration creates one new GitHub issue, then stops.

## Setup

```bash
source .venv/bin/activate
```

## Command

```bash
python scripts/pipeline/loop_workflow.py \
  --profile mvp-v1 \
  --repo Jongtae/AI-Fashion-Forum \
  --source-dir /Users/jongtaelee/Documents/AI-Fashion-Forum
```

## Loop Parameters

- **iterations**: 1 (preset, creates one issue per loop invocation)
- **profile**: mvp-v1 (auto: --stop-on-created-issue, --create-issue, --approve-issue)
- **total ralph-loop iterations**: 3 (will run up to 3 times)

## Each Iteration

1. **Context Builder**: Collects AI-Fashion-Forum state
2. **Commitment**: Decides next priority slice from topic catalog
3. **Workforce**: Selected workforce (society/core/operator) analyzes
4. **Issue Creation**: New GitHub issue generated → loop stops
5. **Stop Condition**: --stop-on-created-issue met

## Progress Tracking

- GitHub issue URL and number in output
- `context/history/run-ledger.jsonl` for issue tracking
- `git log --oneline` for commit history
- `scripts/requirement-debate/outputs/` for decision documents

## Expected Flow

- **Iteration 1**: TC-1 or next available slice → Issue created
- **Iteration 2**: Next uncovered slice → Issue created
- **Iteration 3**: Continues if slices remain → Issue created

If topic catalog exhausted before iteration 3, loop terminates naturally.

## Resume

Ralph loop saves state. Next invocation continues from latest context.
