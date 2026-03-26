# History

이 디렉터리는 workforce 실행과 GitHub issue 발급의 연결 이력을 로컬에 누적한다.

주요 파일:

- `run-ledger.jsonl`
  - 한 줄에 한 실행(run)씩 기록한다.
  - 어떤 workforce run이 어떤 repo에 어떤 issue들을 발급했는지 저장한다.
  - 다음 `build_context.py` 실행 때 현재 issue 상태를 다시 읽는 기준 파일이다.

주의:

- 이 ledger는 운영 산출물이므로 기본적으로 git에 커밋하지 않는다.
- 대신 `metadata.json`과 `issue_execution_history.md`를 통해 최근 상태를 다시 확인할 수 있다.
