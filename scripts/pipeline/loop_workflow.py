#!/usr/bin/env python3
"""Repeat run_studio.py in a controlled loop and inspect each run result."""

import argparse
import json
import subprocess
import sys
import time
from typing import Optional
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
RUN_STUDIO = ROOT_DIR / "scripts" / "pipeline" / "run_studio.py"
OUTPUT_DIR = ROOT_DIR / "scripts" / "requirement-debate" / "outputs"


def run_command(args: list[str]) -> int:
    return subprocess.run(args, cwd=ROOT_DIR).returncode


def latest_run_dir() -> Optional[Path]:
    if not OUTPUT_DIR.exists():
        return None
    run_dirs = sorted([path for path in OUTPUT_DIR.iterdir() if path.is_dir()], reverse=True)
    return run_dirs[0] if run_dirs else None


def load_metadata(run_dir: Path) -> dict:
    metadata_path = run_dir / "metadata.json"
    if not metadata_path.exists():
        return {}
    try:
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def summarize_status(metadata: dict) -> str:
    issue_history = metadata.get("issue_history", {}) or {}
    issue_status = issue_history.get("issue_status") or "unknown"
    issue_urls = issue_history.get("issue_urls") or []
    issue_numbers = issue_history.get("issue_numbers") or []
    next_workforce = metadata.get("target_workforce") or ""
    next_topic = metadata.get("next_topic") or ""
    lines = [
        f"- issue_status: {issue_status}",
        f"- issue_urls: {', '.join(issue_urls) if issue_urls else '(none)'}",
        f"- issue_numbers: {', '.join(map(str, issue_numbers)) if issue_numbers else '(none)'}",
        f"- next_workforce: {next_workforce or '(none)'}",
        f"- next_topic: {next_topic or '(none)'}",
    ]
    return "\n".join(lines)


def should_stop(
    metadata: dict,
    stop_on_issue: bool,
    stop_on_duplicate: bool,
    stop_on_created_issue: bool,
) -> bool:
    issue_status = ((metadata.get("issue_history") or {}).get("issue_status") or "").strip()
    if stop_on_created_issue and issue_status == "created":
        return True
    if stop_on_duplicate and issue_status in {
        "blocked_closed_duplicate_commented",
        "reused_open_commented",
        "reopened_closed_duplicate_commented",
    }:
        return True
    if stop_on_issue and issue_status in {
        "created",
        "reused_open",
        "reused_open_commented",
        "reopened_closed_duplicate_commented",
    }:
        return True
    return False


def preset_catalog_loop() -> dict:
    """Preset: Catalog loop - Stop when a new issue is created (default workflow for topic catalog slice progression)"""
    return {
        "iterations": 1,
        "sleep_seconds": 0,
        "stop_on_created_issue": True,
        "create_issue": True,
        "approve_issue": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Repeat run_studio.py, inspect each iteration, and continue to the next round."
    )
    parser.add_argument(
        "--profile",
        type=str,
        choices=["catalog-loop"],
        default=None,
        help="Use a preset profile (catalog-loop: create issues until one succeeds, then stop)",
    )
    parser.add_argument("--iterations", type=int, default=1, help="How many iterations to run")
    parser.add_argument("--sleep-seconds", type=int, default=0, help="Pause between iterations")
    parser.add_argument(
        "--stop-on-issue",
        action="store_true",
        help="Stop after a run that creates or reuses an issue",
    )
    parser.add_argument(
        "--stop-on-created-issue",
        action="store_true",
        help="Stop only when a run creates a brand-new issue; reused/duplicate paths continue",
    )
    parser.add_argument(
        "--stop-on-duplicate",
        action="store_true",
        help="Stop after a run that hits a duplicate/continuation issue path",
    )
    parser.add_argument(
        "--repo",
        type=str,
        default="Jongtae/AI-Fashion-Forum",
        help="Target GitHub repository slug",
    )
    parser.add_argument(
        "--source-dir",
        type=str,
        default=str(ROOT_DIR.parent / "AI-Fashion-Forum"),
        help="Local source repository path",
    )
    parser.add_argument(
        "--source-policy",
        type=str,
        default="read-only",
        choices=["read-only"],
        help="Source repo policy (default: read-only)",
    )
    parser.add_argument("--sim-results-dir", type=str, default=None)
    parser.add_argument("--soft-guidance", type=str, default=None)
    parser.add_argument("--topic-catalog", type=str, default=None)
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--model", type=str, default="gpt-4o-mini")
    parser.add_argument("--create-issue", action="store_true")
    parser.add_argument("--approve-issue", action="store_true")
    parser.add_argument("--issue-type", type=str, default="task")
    parser.add_argument("--issue-label", action="append", default=[])
    parser.add_argument("--issue-assignee", action="append", default=[])
    parser.add_argument("--task-assignee", action="append", default=[])
    parser.add_argument("--issue-milestone", type=str, default=None)
    parser.add_argument("--issue-project", type=str, default=None)
    parser.add_argument("--epic-label", type=str, default=None)
    parser.add_argument("--with-sprint", action="store_true")
    parser.add_argument("--max-child-issues", type=int, default=5)
    parser.add_argument("--share-memory", action="store_true")
    parser.add_argument("--handoff", type=str, default=None)
    parser.add_argument("--no-run-next", action="store_true")
    parser.add_argument("--run-fanout", action="store_true")
    parser.add_argument("--fanout-workforce", action="append", default=[])
    args = parser.parse_args()

    # Apply profile if specified
    if args.profile == "catalog-loop":
        preset = preset_catalog_loop()
        # Override defaults with preset values (unless explicitly provided)
        if not any(
            arg in sys.argv for arg in ["--iterations", "--stop-on-created-issue", "--create-issue", "--approve-issue"]
        ):
            args.iterations = preset.get("iterations", args.iterations)
            args.sleep_seconds = preset.get("sleep_seconds", args.sleep_seconds)
            args.stop_on_created_issue = preset.get("stop_on_created_issue", args.stop_on_created_issue)
            args.create_issue = preset.get("create_issue", args.create_issue)
            args.approve_issue = preset.get("approve_issue", args.approve_issue)
            print("✓ Using catalog-loop preset: create issues until one succeeds, then stop")

    for index in range(1, args.iterations + 1):
        print("\n" + "=" * 72)
        print(f"Iteration {index}/{args.iterations}")
        print("=" * 72)

        cmd = [
            sys.executable,
            str(RUN_STUDIO),
            "--repo",
            args.repo,
            "--source-dir",
            args.source_dir,
            "--source-policy",
            args.source_policy,
            "--rounds",
            str(args.rounds),
            "--model",
            args.model,
        ]
        if args.sim_results_dir:
            cmd.extend(["--sim-results-dir", args.sim_results_dir])
        if args.soft_guidance:
            cmd.extend(["--soft-guidance", args.soft_guidance])
        if args.topic_catalog:
            cmd.extend(["--topic-catalog", args.topic_catalog])
        if args.create_issue:
            cmd.append("--create-issue")
        if args.approve_issue:
            cmd.append("--approve-issue")
        if args.issue_type:
            cmd.extend(["--issue-type", args.issue_type])
        for label in args.issue_label:
            cmd.extend(["--issue-label", label])
        for assignee in args.issue_assignee:
            cmd.extend(["--issue-assignee", assignee])
        for assignee in args.task_assignee:
            cmd.extend(["--task-assignee", assignee])
        if args.issue_milestone:
            cmd.extend(["--issue-milestone", args.issue_milestone])
        if args.issue_project:
            cmd.extend(["--issue-project", args.issue_project])
        if args.epic_label:
            cmd.extend(["--epic-label", args.epic_label])
        if args.with_sprint:
            cmd.append("--with-sprint")
        if args.max_child_issues:
            cmd.extend(["--max-child-issues", str(args.max_child_issues)])
        if args.share_memory:
            cmd.append("--share-memory")
        if args.handoff:
            cmd.extend(["--handoff", args.handoff])
        if args.run_fanout:
            cmd.append("--run-fanout")
            for fanout_workforce in args.fanout_workforce:
                cmd.extend(["--fanout-workforce", fanout_workforce])
        elif args.no_run_next:
            cmd.append("--no-run-next")

        code = run_command(cmd)
        if code != 0:
            raise SystemExit(code)

        run_dir = latest_run_dir()
        if not run_dir:
            print("No run directory found after iteration.")
        else:
            metadata = load_metadata(run_dir)
            print(f"Latest run dir: {run_dir}")
            print(summarize_status(metadata))
            if should_stop(
                metadata,
                args.stop_on_issue,
                args.stop_on_duplicate,
                args.stop_on_created_issue,
            ):
                print("Stop condition reached. Ending loop.")
                break

        if index < args.iterations and args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)


if __name__ == "__main__":
    main()
