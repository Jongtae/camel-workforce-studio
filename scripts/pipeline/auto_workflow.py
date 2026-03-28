#!/usr/bin/env python3
"""
자동 워크플로우 실행 스크립트

Context Builder → Pipeline → Issue 생성까지 자동 진행
모든 설정값이 미리 정의되어 있어 질문 없이 실행됨
"""

import argparse
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def run_command(args: list[str], description: str) -> None:
    """Run a command and report results."""
    print(f"\n{'='*60}")
    print(f"▶ {description}")
    print(f"{'='*60}\n")

    result = subprocess.run(args, cwd=ROOT_DIR)
    if result.returncode != 0:
        print(f"\n❌ Failed: {description}")
        raise SystemExit(result.returncode)
    print(f"\n✓ Completed: {description}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="자동 워크플로우 실행: Context → Pipeline → Issue"
    )
    parser.add_argument(
        "--repo",
        type=str,
        default="Jongtae/AI-Fashion-Forum",
        help="Target GitHub repository (기본값: Jongtae/AI-Fashion-Forum)",
    )
    parser.add_argument(
        "--source-dir",
        type=str,
        default=None,
        help="AI-Fashion-Forum 로컬 경로 (기본값: 자동 감지)",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=1,
        help="Commitment round 수 (기본값: 1)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        help="OpenAI model (기본값: gpt-4o-mini)",
    )
    parser.add_argument(
        "--create-issue",
        action="store_true",
        default=True,
        help="Issue draft 생성 (기본값: True)",
    )
    parser.add_argument(
        "--approve-issue",
        action="store_true",
        help="Issue 자동 생성 (미설정 시 draft만 생성)",
    )
    parser.add_argument(
        "--issue-type",
        type=str,
        default="bundle",
        choices=["single", "task", "epic", "sprint", "bundle"],
        help="Issue 형태 (기본값: bundle)",
    )
    parser.add_argument(
        "--issue-label",
        action="append",
        default=[],
        help="Issue label (여러 번 지정 가능)",
    )
    parser.add_argument(
        "--issue-assignee",
        action="append",
        default=[],
        help="Single/epic/sprint 담당자 login",
    )
    parser.add_argument(
        "--task-assignee",
        action="append",
        default=None,
        help="Bundle child task 담당자 (여러 번 지정 가능, 기본값: jongtae, alice)",
    )
    parser.add_argument(
        "--issue-milestone",
        type=str,
        default="Sprint 1 - Identity Loop Vertical Slice",
        help="Issue milestone 이름 (기본값: Sprint 1 - Identity Loop Vertical Slice)",
    )
    parser.add_argument(
        "--issue-project",
        type=str,
        default=None,
        help="Issue project 제목",
    )
    parser.add_argument(
        "--epic-label",
        type=str,
        default="epic:forum-actions",
        help="Epic label (기본값: epic:forum-actions)",
    )
    parser.add_argument(
        "--with-sprint",
        action="store_true",
        default=True,
        help="Bundle 생성 시 sprint planning issue 함께 생성 (기본값: True)",
    )
    parser.add_argument(
        "--max-child-issues",
        type=int,
        default=5,
        help="Bundle child issue 최대 개수 (기본값: 5)",
    )
    parser.add_argument(
        "--share-memory",
        action="store_true",
        default=True,
        help="CAMEL share_memory 활성화 (기본값: True)",
    )
    parser.add_argument(
        "--no-run-next",
        action="store_true",
        help="Commitment만 실행 (workforce 체인 없음)",
    )
    args = parser.parse_args()

    # 기본 source-dir 설정
    source_dir = args.source_dir
    if not source_dir:
        ai_fashion_forum = ROOT_DIR.parent / "AI-Fashion-Forum"
        if ai_fashion_forum.exists():
            source_dir = str(ai_fashion_forum)
        else:
            legacy_ad_fashion_forum = ROOT_DIR.parent / "ad-fashion-forum"
            if legacy_ad_fashion_forum.exists():
                source_dir = str(legacy_ad_fashion_forum)
            else:
                source_dir = str(ai_fashion_forum)

    # Run Pipeline (context build는 run_studio.py에서 자동 호출됨)
    pipeline_cmd = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "pipeline" / "run_studio.py"),
        "--repo",
        args.repo,
        "--source-dir",
        source_dir,
        "--rounds",
        str(args.rounds),
        "--model",
        args.model,
    ]

    if args.create_issue:
        pipeline_cmd.append("--create-issue")
    if args.approve_issue:
        pipeline_cmd.append("--approve-issue")

    # Issue type and settings
    pipeline_cmd.extend(["--issue-type", args.issue_type])

    # Issue labels
    for label in args.issue_label:
        pipeline_cmd.extend(["--issue-label", label])

    # Issue assignees
    for assignee in args.issue_assignee:
        pipeline_cmd.extend(["--issue-assignee", assignee])

    # Task assignees (default: jongtae, alice)
    task_assignees = args.task_assignee if args.task_assignee else ["jongtae", "alice"]
    for assignee in task_assignees:
        pipeline_cmd.extend(["--task-assignee", assignee])

    # Epic label
    if args.epic_label:
        pipeline_cmd.extend(["--epic-label", args.epic_label])

    # Milestone
    if args.issue_milestone:
        pipeline_cmd.extend(["--issue-milestone", args.issue_milestone])

    # Project
    if args.issue_project:
        pipeline_cmd.extend(["--issue-project", args.issue_project])

    # With sprint
    if args.with_sprint:
        pipeline_cmd.append("--with-sprint")

    # Max child issues
    pipeline_cmd.extend(["--max-child-issues", str(args.max_child_issues)])

    # Share memory
    if args.share_memory:
        pipeline_cmd.append("--share-memory")

    # No run next
    if args.no_run_next:
        pipeline_cmd.append("--no-run-next")

    run_command(
        pipeline_cmd,
        "Step 1: Context Build + Commitment + Issue Creation (via run_studio.py)",
    )

    print(f"\n{'='*60}")
    print("✓ 자동 워크플로우 완료!")
    print(f"{'='*60}\n")

    # Ralph Loop 감지: 다음 반복이 바로 시작될 수 있도록 신호
    print("Iteration 완료. 다음 반복 준비 중...\n")


if __name__ == "__main__":
    main()
