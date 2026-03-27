# Context Directory

이 디렉터리는 raw source를 바로 workforce에 넣지 않고, 정규화된 context pack으로 변환하기 위한 작업 공간이다.

## Structure

- `raw/github/`: GitHub issue 수집 결과
- `raw/reports/`: 외부 리포트 원문 또는 추출 텍스트
- `raw/progress/`: 로컬 진행 로그
- `raw/sim-results/`: AI-Fashion-Forum 실험 산출물 복사본
- `normalized/`: workforce 입력에 바로 사용할 정리본
- `normalized/society_output_contract.json`: 최신 society 결정문을 JSON 계약으로 정규화한 결과
- `workflow-inputs/`: workforce별 input pack

## Build

```bash
python3 scripts/context-builder/build_context.py \
  --repo Jongtae/AI-Fashion-Forum \
  --source-dir /Users/jongtaelee/Documents/AI-Fashion-Forum \
  --sim-results-dir /Users/jongtaelee/Documents/AI-Fashion-Forum/path/to/sim-results
```

생성된 workflow input은 예를 들어 아래처럼 workforce 실행에 연결할 수 있다.

```bash
python3 scripts/requirement-debate/commitment_debate.py \
  --context-pack context/workflow-inputs/commitment.md
```

`current_situation.md`에는 GitHub issue, 로컬 source repo의 git 상태, 최근 커밋, 변경 파일, 최신 workforce handoff 요약이 함께 들어간다.
`sim_results.md`가 있으면 AI-Fashion-Forum 실험 산출물이 정규화되어 함께 들어가고, `--sim-results-dir`를 주지 않아도 source repo 안의 표준 후보 경로를 자동 탐색한다. `society_output_contract.json/md`는 최신 society 결정문을 구조화된 계약 형태로 다시 저장한다.
