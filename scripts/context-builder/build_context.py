#!/usr/bin/env python3
"""Build normalized context packs for workforce runs."""

import argparse
import json
import subprocess
from pathlib import Path
import sys
from typing import Iterable, List


ROOT_DIR = Path(__file__).resolve().parents[2]
CONTEXT_DIR = ROOT_DIR / "context"
RAW_DIR = CONTEXT_DIR / "raw"
NORMALIZED_DIR = CONTEXT_DIR / "normalized"
WORKFLOW_INPUTS_DIR = CONTEXT_DIR / "workflow-inputs"
REQUIREMENT_DEBATE_DIR = ROOT_DIR / "scripts" / "requirement-debate"

if str(REQUIREMENT_DEBATE_DIR) not in sys.path:
    sys.path.insert(0, str(REQUIREMENT_DEBATE_DIR))

from workforce_artifacts import summarize_latest_run


WORKFLOW_OBJECTIVES = {
    "commitment": "현재 프로젝트에서 가장 중요한 gap을 식별하고 다음 workforce와 topic을 결정한다.",
    "core": "development 팀 관점에서 mock-to-service 전환을 위한 실제 구현과 아키텍처 결정을 구체화한다.",
    "operator": "운영자 관점에서 컨텐츠 자정, 모니터링, 운영 정책, 기능 개선 레버를 정리한다.",
    "society": "API 기반 forum 위에서 action하는 stateful AI agent의 상태, 기억, characteristic, 내부/외부 콘텐츠 소비 규칙을 정리한다.",
}


def ensure_dirs() -> None:
    for path in [
        RAW_DIR / "github",
        RAW_DIR / "reports",
        RAW_DIR / "progress",
        NORMALIZED_DIR,
        WORKFLOW_INPUTS_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def default_source_dir() -> str:
    candidate = ROOT_DIR.parent / "AI-Fashion-Forum"
    return str(candidate)


def run_gh_json(repo: str, args: List[str]) -> list:
    cmd = ["gh", "issue", "list", "--repo", repo, *args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return []


def run_git_command(repo_dir: Path, args: List[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def collect_github_issues(repo: str) -> list:
    issues = run_gh_json(
        repo,
        [
            "--state",
            "open",
            "--limit",
            "100",
            "--json",
            "number,title,body,labels,assignees,updatedAt,url",
        ],
    )
    issues_path = RAW_DIR / "github" / "issues.json"
    issues_path.write_text(
        json.dumps(issues, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return issues


def collect_source_repo_state(source_dir: Path) -> dict:
    if not source_dir.exists():
        return {
            "exists": False,
            "path": str(source_dir),
            "branch": "",
            "status": "",
            "recent_commits": [],
            "changed_files": [],
        }

    branch = run_git_command(source_dir, ["rev-parse", "--abbrev-ref", "HEAD"])
    status = run_git_command(source_dir, ["status", "--short"])
    commits_raw = run_git_command(
        source_dir,
        ["log", "--max-count=8", "--pretty=format:%h%x09%ad%x09%s", "--date=short"],
    )
    changed_files_raw = run_git_command(source_dir, ["status", "--short"])
    recent_commits = []
    for line in commits_raw.splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3:
            recent_commits.append(
                {"sha": parts[0].strip(), "date": parts[1].strip(), "subject": parts[2].strip()}
            )
    changed_files = [line.strip() for line in changed_files_raw.splitlines() if line.strip()]
    return {
        "exists": True,
        "path": str(source_dir),
        "branch": branch,
        "status": status,
        "recent_commits": recent_commits,
        "changed_files": changed_files,
    }


def read_text_files(paths: Iterable[Path]) -> list:
    items = []
    for path in paths:
        if not path.is_file():
            continue
        items.append(
            {
                "name": path.name,
                "path": str(path),
                "text": path.read_text(encoding="utf-8", errors="ignore"),
            }
        )
    return items


def collect_reports() -> list:
    report_dir = RAW_DIR / "reports"
    files = sorted(
        [
            *report_dir.glob("*.md"),
            *report_dir.glob("*.txt"),
        ]
    )
    return read_text_files(files)


def collect_progress_logs() -> list:
    progress_dir = RAW_DIR / "progress"
    items = []
    for path in sorted(progress_dir.iterdir() if progress_dir.exists() else []):
        if path.suffix in {".md", ".txt"}:
            items.extend(read_text_files([path]))
            continue
        if path.suffix == ".json":
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if isinstance(payload, list):
                for entry in payload:
                    items.append({"name": path.name, "entry": entry})
            elif isinstance(payload, dict):
                items.append({"name": path.name, "entry": payload})
    return items


def trim(text: str, max_lines: int = 12) -> str:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines[:max_lines]).strip()


def render_project_snapshot(repo: str, issues: list) -> str:
    return (
        "# Project Snapshot\n\n"
        f"- Source repository: {repo}\n"
        "- This workspace acts as a companion decision studio for AI-Fashion-Forum.\n"
        "- Workforce runs are expected to consume normalized context rather than raw issue or report dumps.\n"
        f"- Open GitHub issues collected for this build: {len(issues)}\n"
    )


def render_current_situation(repo: str, source_state: dict, latest_workforce_state: str) -> str:
    latest_summary = latest_workforce_state.strip() or "- No previous workforce state found."
    recent_commit_subjects = [
        commit["subject"] for commit in source_state.get("recent_commits", [])[:3]
    ]
    lines = [
        "# Current Situation",
        "",
        f"- GitHub repository target: {repo}",
        f"- Local source repository path: {source_state.get('path', '')}",
    ]
    if not source_state.get("exists"):
        lines.append("- Local source repository was not found, so git-based situation checks are unavailable.")
    else:
        lines.extend(
            [
                f"- Current branch: {source_state.get('branch', '') or 'unknown'}",
                f"- Changed file count: {len(source_state.get('changed_files', []))}",
                f"- Recent commit count collected: {len(source_state.get('recent_commits', []))}",
                "",
                "## Current Signals",
                f"- Working tree is {'clean' if not source_state.get('changed_files') else 'dirty'}",
                f"- Latest commit directions: {', '.join(recent_commit_subjects) if recent_commit_subjects else 'none'}",
                "",
                "## Already Decided Or Suggested",
                "- Latest workforce state below is the current studio-level baseline unless explicitly challenged.",
                "",
                "## Working Tree Status",
            ]
        )
        status = source_state.get("status", "")
        lines.append(status if status else "- Working tree is clean.")
        lines.extend(
            [
                "",
                "## Current Blocker Heuristic",
                "- If the working tree is clean and recent commits landed, the blocker is more likely a missing next decision than missing code edits.",
                "- If latest workforce state already suggests a next workforce/topic, commitment should either confirm it or explain why it must change.",
            ]
        )
    lines.extend(["", latest_summary, ""])
    return "\n".join(lines).strip() + "\n"


def render_source_repo_state(source_state: dict) -> str:
    lines = ["# Source Repo State", ""]
    if not source_state.get("exists"):
        lines.append("- Local source repository was not found. Pass `--source-dir` to enable git situation checks.")
        return "\n".join(lines) + "\n"

    lines.extend(
        [
            f"- Path: {source_state['path']}",
            f"- Branch: {source_state.get('branch', '') or 'unknown'}",
            "",
            "## Changed Files",
        ]
    )
    changed_files = source_state.get("changed_files", [])
    if changed_files:
        lines.extend([f"- {line}" for line in changed_files[:30]])
    else:
        lines.append("- Working tree is clean.")

    lines.extend(["", "## Recent Commits"])
    commits = source_state.get("recent_commits", [])
    if commits:
        for commit in commits:
            lines.append(f"- {commit['date']} {commit['sha']} {commit['subject']}")
    else:
        lines.append("- No recent commits were collected.")
    return "\n".join(lines).strip() + "\n"


def render_active_issues(issues: list) -> str:
    lines = ["# Active Issues", ""]
    if not issues:
        lines.append("- No GitHub issues were collected. Add `--repo` or run `gh auth login` if needed.")
        return "\n".join(lines) + "\n"

    for issue in issues:
        labels = ", ".join(label["name"] for label in issue.get("labels", [])) or "no labels"
        lines.extend(
            [
                f"## #{issue['number']} {issue['title']}",
                f"- Updated: {issue.get('updatedAt', '')}",
                f"- Labels: {labels}",
                f"- URL: {issue.get('url', '')}",
                trim(issue.get("body", "") or "No body provided.", max_lines=8) or "No body provided.",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def render_recent_progress(progress_items: list) -> str:
    lines = ["# Recent Progress", ""]
    if not progress_items:
        lines.append("- No local progress logs found in `context/raw/progress`.")
        return "\n".join(lines) + "\n"

    for item in progress_items:
        lines.append(f"## {item['name']}")
        entry = item.get("entry")
        if entry is not None:
            for key, value in entry.items():
                lines.append(f"- {key}: {value}")
        else:
            lines.append(trim(item.get("text", ""), max_lines=10) or "- Empty progress note")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def render_external_report_briefs(reports: list) -> str:
    lines = ["# External Report Briefs", ""]
    if not reports:
        lines.append("- No report files found in `context/raw/reports`.")
        return "\n".join(lines) + "\n"

    for report in reports:
        lines.extend(
            [
                f"## {report['name']}",
                trim(report["text"], max_lines=12) or "No extractable text.",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def render_open_questions(issues: list, progress_items: list) -> str:
    lines = ["# Open Questions", ""]
    if not issues and not progress_items:
        lines.append("- No structured open questions were found. Add issue bodies or progress logs with explicit gaps.")
        return "\n".join(lines) + "\n"

    for issue in issues[:10]:
        lines.append(f"- Issue #{issue['number']}에서 아직 풀리지 않은 결정: {issue['title']}")
    if progress_items:
        lines.append("- Progress logs에서 드러난 검증 공백과 미해결 항목을 다음 workforce에서 정리해야 한다.")
    return "\n".join(lines).strip() + "\n"


def render_latest_workforce_state(latest_workforce_state: str) -> str:
    return latest_workforce_state.strip() + ("\n" if latest_workforce_state else "")


def write_normalized_file(name: str, content: str) -> Path:
    path = NORMALIZED_DIR / name
    path.write_text(content, encoding="utf-8")
    return path


def build_workflow_input(workforce: str, normalized: dict) -> str:
    return f"""# Workflow Input

## Workflow
{workforce}

## Objective
{WORKFLOW_OBJECTIVES[workforce]}

## Current Situation
{normalized['current_situation']}

## Project Snapshot
{normalized['project_snapshot']}

## Source Repo State
{normalized['source_repo_state']}

## Latest Workforce State
{normalized['latest_workforce_state']}

## Active Issues
{normalized['active_issues']}

## Recent Progress
{normalized['recent_progress']}

## External Evidence
{normalized['external_report_briefs']}

## Open Questions
{normalized['open_questions']}

## Constraints
- 이미 정리된 normalized context를 우선 근거로 사용한다.
- raw source 전체를 다시 요약하지 말고, 이번 workforce에 필요한 결정을 우선한다.

## Expected Output
- `decision.md`
- `handoff.md`
- `next_questions.md`
- `round_summary.md`
""".strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="GitHub issues, reports, and progress logs into workforce-ready context packs"
    )
    parser.add_argument(
        "--repo",
        type=str,
        default="Jongtae/AI-Fashion-Forum",
        help="수집할 GitHub repository (owner/name)",
    )
    parser.add_argument(
        "--source-dir",
        type=str,
        default=default_source_dir(),
        help="상황을 읽을 로컬 source repository 경로",
    )
    args = parser.parse_args()

    ensure_dirs()

    issues = collect_github_issues(args.repo)
    reports = collect_reports()
    progress_items = collect_progress_logs()
    source_state = collect_source_repo_state(Path(args.source_dir))
    latest_workforce_state = summarize_latest_run(ROOT_DIR / "scripts" / "requirement-debate" / "outputs")

    normalized = {
        "current_situation": render_current_situation(args.repo, source_state, latest_workforce_state),
        "project_snapshot": render_project_snapshot(args.repo, issues),
        "source_repo_state": render_source_repo_state(source_state),
        "latest_workforce_state": render_latest_workforce_state(latest_workforce_state),
        "active_issues": render_active_issues(issues),
        "recent_progress": render_recent_progress(progress_items),
        "external_report_briefs": render_external_report_briefs(reports),
        "open_questions": render_open_questions(issues, progress_items),
    }

    for filename, content in [
        ("current_situation.md", normalized["current_situation"]),
        ("project_snapshot.md", normalized["project_snapshot"]),
        ("source_repo_state.md", normalized["source_repo_state"]),
        ("latest_workforce_state.md", normalized["latest_workforce_state"]),
        ("active_issues.md", normalized["active_issues"]),
        ("recent_progress.md", normalized["recent_progress"]),
        ("external_report_briefs.md", normalized["external_report_briefs"]),
        ("open_questions.md", normalized["open_questions"]),
    ]:
        write_normalized_file(filename, content)

    for workforce in WORKFLOW_OBJECTIVES:
        path = WORKFLOW_INPUTS_DIR / f"{workforce}.md"
        path.write_text(build_workflow_input(workforce, normalized), encoding="utf-8")
        print(f"✓ workflow input 생성: {path}")

    print(f"✓ normalized context 생성 완료: {NORMALIZED_DIR}")


if __name__ == "__main__":
    main()
