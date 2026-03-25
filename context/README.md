# Context Directory

이 디렉터리는 raw source를 바로 workforce에 넣지 않고, 정규화된 context pack으로 변환하기 위한 작업 공간이다.

## Structure

- `raw/github/`: GitHub issue 수집 결과
- `raw/reports/`: 외부 리포트 원문 또는 추출 텍스트
- `raw/progress/`: 로컬 진행 로그
- `normalized/`: workforce 입력에 바로 사용할 정리본
- `workflow-inputs/`: workforce별 input pack

## Build

```bash
python3 scripts/context-builder/build_context.py --repo Jongtae/AI-Fashion-Forum
```

생성된 workflow input은 예를 들어 아래처럼 workforce 실행에 연결할 수 있다.

```bash
python3 scripts/requirement-debate/commitment_debate.py \
  --context-pack context/workflow-inputs/commitment.md
```
