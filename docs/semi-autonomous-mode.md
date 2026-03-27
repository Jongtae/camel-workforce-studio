# Semi-Autonomous Mode

이 저장소는 완전 자율형 agent runtime이 아니라, `ad-fashion-forum`을 위한 `semi-autonomous decision studio`로 운영한다.

## What Gets Automated

- GitHub issue 수집
- 로컬 source repository의 git 상태, 최근 커밋, 변경 파일 요약
- 최신 workforce handoff 자동 발견
- context pack 생성
- commitment workforce 실행
- 선택된 next workforce로의 연쇄 실행
- 표준 산출물 저장

## What Still Needs Human Review

- 어떤 external report가 실제로 중요한지
- commitment route가 프로젝트 방향과 맞는지
- 산출물을 GitHub issue, PR, product decision에 반영할지
- 프로젝트 방향을 바꾸는 수준의 메타 의사결정

## Recommended Run

```bash
source .venv/bin/activate
python scripts/pipeline/run_studio.py \
  --repo Jongtae/ad-fashion-forum \
  --source-dir /Users/jongtaelee/Documents/ad-fashion-forum \
  --rounds 1
```

## Situation Inputs

현재 상황은 최소한 아래 source에서 읽는다.

- GitHub issues
- local source repo git status
- recent commits
- changed files
- local reports in `context/raw/reports`
- local progress logs in `context/raw/progress`
- latest workforce `handoff.md` / `decision.md`

## Why This Boundary Exists

프로젝트의 진실은 CAMEL 내부 memory보다 GitHub, 로컬 repo 상태, handoff 문서에 더 명시적으로 남는다. 그래서 이 저장소는 memory-first보다 source-of-truth-first 구조를 택한다.
