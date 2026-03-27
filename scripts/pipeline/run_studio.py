#!/usr/bin/env python3
"""Run the studio in a semi-autonomous mode."""

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
BUILD_CONTEXT = ROOT_DIR / "scripts" / "context-builder" / "build_context.py"
COMMITMENT_RUNNER = ROOT_DIR / "scripts" / "requirement-debate" / "commitment_debate.py"
OUTPUT_DIR = ROOT_DIR / "scripts" / "requirement-debate" / "outputs"
REQUIREMENT_DEBATE_DIR = ROOT_DIR / "scripts" / "requirement-debate"

if str(REQUIREMENT_DEBATE_DIR) not in sys.path:
    sys.path.insert(0, str(REQUIREMENT_DEBATE_DIR))

from workforce_artifacts import discover_latest_handoff


def default_source_dir() -> str:
    ai_fashion_forum = ROOT_DIR.parent / "AI-Fashion-Forum"
    if ai_fashion_forum.exists():
        return str(ai_fashion_forum)
    legacy_ad_fashion_forum = ROOT_DIR.parent / "ad-fashion-forum"
    if legacy_ad_fashion_forum.exists():
        return str(legacy_ad_fashion_forum)
    return str(ai_fashion_forum)


def default_issue_repo() -> str:
    return os.environ.get("WORKFORCE_TARGET_REPO", "Jongtae/AI-Fashion-Forum")


def run_command(args: list[str]) -> None:
    result = subprocess.run(args, cwd=ROOT_DIR)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build context and run camel-workforce-studio in semi-autonomous mode"
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=default_issue_repo(),
        help="GitHub repository slug to summarize",
    )
    parser.add_argument(
        "--source-dir",
        type=str,
        default=default_source_dir(),
        help="Local source repository path for git situation checks",
    )
    parser.add_argument(
        "--sim-results-dir",
        type=str,
        default=None,
        help="Optional local directory containing AI-Fashion-Forum simulation results",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=1,
        help="Round count for commitment and chained next workforce",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        help="OpenAI model name",
    )
    parser.add_argument(
        "--no-run-next",
        action="store_true",
        help="Run only commitment without chaining to the selected next workforce",
    )
    parser.add_argument(
        "--create-issue",
        action="store_true",
        help="선택된 workforce 결과가 issue-ready면 issue draft를 준비",
    )
    parser.add_argument(
        "--approve-issue",
        action="store_true",
        help="issue draft를 검토했다고 보고 실제 GitHub issue 생성을 승인",
    )
    parser.add_argument(
        "--issue-type",
        type=str,
        default="task",
        help="발급 형태: single, task, epic, sprint, bundle",
    )
    parser.add_argument(
        "--issue-label",
        action="append",
        default=[],
        help="추가 issue label (여러 번 지정 가능)",
    )
    parser.add_argument(
        "--issue-assignee",
        action="append",
        default=[],
        help="single/epic/sprint에 붙일 담당자 login",
    )
    parser.add_argument(
        "--task-assignee",
        action="append",
        default=[],
        help="bundle child task를 순서대로 분배할 담당자 login",
    )
    parser.add_argument(
        "--issue-milestone",
        type=str,
        default=None,
        help="생성할 issue milestone 이름",
    )
    parser.add_argument(
        "--issue-project",
        type=str,
        default=None,
        help="생성할 issue project 제목",
    )
    parser.add_argument(
        "--epic-label",
        type=str,
        default=None,
        help="Epic에 추가할 label 예: epic:forum-actions",
    )
    parser.add_argument(
        "--with-sprint",
        action="store_true",
        help="bundle 생성 시 sprint planning issue도 함께 생성",
    )
    parser.add_argument(
        "--max-child-issues",
        type=int,
        default=5,
        help="bundle 생성 시 child issue 최대 개수",
    )
    parser.add_argument(
        "--share-memory",
        action="store_true",
        help="Enable CAMEL share_memory during workforce runs",
    )
    parser.add_argument(
        "--handoff",
        type=str,
        default=None,
        help="Explicit previous handoff to inject. Defaults to latest discovered handoff.",
    )
    args = parser.parse_args()

    build_context_cmd = [
        sys.executable,
        str(BUILD_CONTEXT),
        "--repo",
        args.repo,
        "--source-dir",
        args.source_dir,
    ]
    if args.sim_results_dir:
        build_context_cmd.extend(["--sim-results-dir", args.sim_results_dir])
    run_command(build_context_cmd)

    handoff_path = args.handoff
    if not handoff_path:
        latest_handoff = discover_latest_handoff(OUTPUT_DIR)
        handoff_path = str(latest_handoff) if latest_handoff else None

    commitment_cmd = [
        sys.executable,
        str(COMMITMENT_RUNNER),
        "--rounds",
        str(args.rounds),
        "--model",
        args.model,
        "--context-pack",
        str(ROOT_DIR / "context" / "workflow-inputs" / "commitment.md"),
    ]
    if handoff_path:
        commitment_cmd.extend(["--handoff", handoff_path])
    if not args.no_run_next:
        commitment_cmd.append("--run-next")
    if args.create_issue:
        commitment_cmd.extend(["--create-issue", "--issue-repo", args.repo, "--issue-type", args.issue_type])
        if args.approve_issue:
            commitment_cmd.append("--approve-issue")
        for label in args.issue_label:
            commitment_cmd.extend(["--issue-label", label])
        for assignee in args.issue_assignee:
            commitment_cmd.extend(["--issue-assignee", assignee])
        for assignee in args.task_assignee:
            commitment_cmd.extend(["--task-assignee", assignee])
        if args.issue_milestone:
            commitment_cmd.extend(["--issue-milestone", args.issue_milestone])
        if args.issue_project:
            commitment_cmd.extend(["--issue-project", args.issue_project])
        if args.epic_label:
            commitment_cmd.extend(["--epic-label", args.epic_label])
        if args.with_sprint:
            commitment_cmd.append("--with-sprint")
        if args.max_child_issues:
            commitment_cmd.extend(["--max-child-issues", str(args.max_child_issues)])
    if args.share_memory:
        commitment_cmd.append("--share-memory")

    run_command(commitment_cmd)


if __name__ == "__main__":
    main()
