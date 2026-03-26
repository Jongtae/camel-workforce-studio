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

from workforce_artifacts import load_run_ledger, summarize_latest_run


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
        CONTEXT_DIR / "history",
        NORMALIZED_DIR,
        WORKFLOW_INPUTS_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def default_source_dir() -> str:
    candidate = ROOT_DIR.parent / "AI-Fashion-Forum"
    return str(candidate)


def run_gh_json(command: List[str]) -> object:
    cmd = ["gh", *command]
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
        [
            "issue",
            "list",
            "--repo",
            repo,
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


def collect_github_pull_requests(repo: str) -> dict:
    open_prs = run_gh_json(
        [
            "pr",
            "list",
            "--repo",
            repo,
            "--state",
            "open",
            "--limit",
            "30",
            "--json",
            "number,title,body,labels,assignees,updatedAt,url,baseRefName,headRefName,isDraft,author",
        ]
    )
    merged_prs = run_gh_json(
        [
            "pr",
            "list",
            "--repo",
            repo,
            "--state",
            "merged",
            "--limit",
            "20",
            "--json",
            "number,title,body,labels,assignees,updatedAt,url,baseRefName,headRefName,mergedAt,author",
        ]
    )

    open_prs_path = RAW_DIR / "github" / "open_prs.json"
    open_prs_path.write_text(
        json.dumps(open_prs, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    merged_prs_path = RAW_DIR / "github" / "merged_prs.json"
    merged_prs_path.write_text(
        json.dumps(merged_prs, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "open": open_prs if isinstance(open_prs, list) else [],
        "merged": merged_prs if isinstance(merged_prs, list) else [],
    }


def collect_issue_snapshot(repo: str, issue_number: int) -> dict:
    result = subprocess.run(
        [
            "gh",
            "issue",
            "view",
            str(issue_number),
            "--repo",
            repo,
            "--json",
            "number,title,state,closedAt,url,labels,assignees",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}


def collect_issue_execution_history() -> list:
    history = []
    for entry in load_run_ledger(limit=12):
        repo = entry.get("issue_repo", "")
        issue_numbers = entry.get("issue_numbers", [])
        issue_states = []
        for issue_number in issue_numbers:
            snapshot = collect_issue_snapshot(repo, issue_number)
            if snapshot:
                issue_states.append(snapshot)
        history.append(
            {
                "recorded_at": entry.get("recorded_at", ""),
                "run_dir": entry.get("run_dir", ""),
                "workforce": entry.get("workforce", ""),
                "topic": entry.get("topic", ""),
                "issue_repo": repo,
                "issue_type": entry.get("issue_type", ""),
                "issue_urls": entry.get("issue_urls", []),
                "issue_numbers": issue_numbers,
                "issue_states": issue_states,
            }
        )
    return history


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


def collect_source_repo_intent(source_dir: Path) -> dict:
    intent = {
        "exists": False,
        "signals": [],
    }
    if not source_dir.exists():
        return intent

    files = {
        "README": source_dir / "README.md",
        "CLAUDE": source_dir / "CLAUDE.md",
        "agent_loop": source_dir / "apps" / "sim-server" / "src" / "routes" / "agent-loop.js",
        "action_space": source_dir / "packages" / "agent-core" / "action-space.js",
        "identity_update": source_dir / "packages" / "agent-core" / "identity-update-rules.js",
        "state_schema": source_dir / "packages" / "shared-types" / "state-schema.js",
    }

    signals = []
    if files["README"].exists():
        signals.append(
            "- README 기준 이 제품은 AI-native fashion forum simulation이며, 살아 있는 social system을 목표로 한다."
        )
    if files["CLAUDE"].exists():
        signals.append(
            "- CLAUDE 기준 핵심 루프는 content-starter-pack -> biased exposure -> memory writeback -> state-driven posts 이다."
        )
    if files["agent_loop"].exists():
        signals.append(
            "- sim-server에는 agent tick 기반 action 실행 경로가 이미 존재하므로, society는 추상 현상보다 action backend 요구사항을 우선해야 한다."
        )
    if files["action_space"].exists():
        signals.append(
            "- agent-core에는 silence/lurk/react/comment 같은 action 선택 로직이 있으므로, society topic은 action/state contract를 다뤄야 한다."
        )
    if files["identity_update"].exists():
        signals.append(
            "- identity-update-rules가 존재하므로, characteristic 유지와 변화는 memory/state transition requirement로 연결되어야 한다."
        )
    if files["state_schema"].exists():
        signals.append(
            "- shared-types state schema가 존재하므로, society는 belief/interest/self-narrative/mutable axes를 포함한 state model을 전제로 논의해야 한다."
        )

    return {
        "exists": True,
        "signals": signals,
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


def render_project_snapshot(repo: str, issues: list, pull_requests: dict) -> str:
    open_prs = pull_requests.get("open", [])
    merged_prs = pull_requests.get("merged", [])
    return (
        "# Project Snapshot\n\n"
        f"- Source repository: {repo}\n"
        "- This workspace acts as a companion decision studio for AI-Fashion-Forum.\n"
        "- Workforce runs are expected to consume normalized context rather than raw issue or report dumps.\n"
        f"- Open GitHub issues collected for this build: {len(issues)}\n"
        f"- Open GitHub PRs collected for this build: {len(open_prs)}\n"
        f"- Recent merged GitHub PRs collected for this build: {len(merged_prs)}\n"
    )


def render_source_repo_intent(source_intent: dict) -> str:
    lines = ["# Source Repo Intent", ""]
    if not source_intent.get("exists"):
        lines.append("- Local source repository was not found, so repo intent signals are unavailable.")
        return "\n".join(lines) + "\n"

    signals = source_intent.get("signals", [])
    if signals:
        lines.extend(signals)
    else:
        lines.append("- No repo intent signals were extracted.")
    return "\n".join(lines).strip() + "\n"


def render_current_situation(
    repo: str,
    source_state: dict,
    source_intent: dict,
    latest_workforce_state: str,
    pull_requests: dict,
) -> str:
    latest_summary = latest_workforce_state.strip() or "- No previous workforce state found."
    recent_commit_subjects = [
        commit["subject"] for commit in source_state.get("recent_commits", [])[:3]
    ]
    open_prs = pull_requests.get("open", [])
    merged_prs = pull_requests.get("merged", [])
    open_pr_titles = [pr.get("title", "") for pr in open_prs[:3] if pr.get("title")]
    merged_pr_titles = [pr.get("title", "") for pr in merged_prs[:3] if pr.get("title")]
    lines = [
        "# Current Situation",
        "",
        f"- GitHub repository target: {repo}",
        f"- Local source repository path: {source_state.get('path', '')}",
        f"- Open PR count collected: {len(open_prs)}",
        f"- Recent merged PR count collected: {len(merged_prs)}",
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
                f"- Open PR directions: {', '.join(open_pr_titles) if open_pr_titles else 'none'}",
                f"- Recent merged PR directions: {', '.join(merged_pr_titles) if merged_pr_titles else 'none'}",
                "",
                "## Already Decided Or Suggested",
                "- Latest workforce state below is the current studio-level baseline unless explicitly challenged.",
                "- 다만 latest workforce state가 source repo intent와 어긋나면 source repo intent를 우선하라.",
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
                "- If open PRs already encode implementation intent, commitment should treat them as near-term execution signals rather than ignoring them.",
                "- If recently merged PRs materially changed the backend or simulation loop, commitment should prefer follow-up work that closes the new gap they exposed.",
                "- If latest workforce state already suggests a next workforce/topic, commitment should either confirm it or explain why it must change.",
                "- For society routing, abstract social-conflict topics are lower priority than agent backend/state/action/content-consumption requirements when the source repo already exposes agent-loop style implementation signals.",
            ]
        )
    if source_intent.get("signals"):
        lines.extend(["", "## Source Repo Intent Signals", *source_intent["signals"]])
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


def render_active_pull_requests(pull_requests: dict) -> str:
    lines = ["# Active Pull Requests", ""]
    open_prs = pull_requests.get("open", [])
    if not open_prs:
        lines.append("- No open PRs were collected.")
        return "\n".join(lines) + "\n"

    for pr in open_prs:
        labels = ", ".join(label["name"] for label in pr.get("labels", [])) or "no labels"
        assignees = ", ".join(
            assignee.get("login", "") for assignee in pr.get("assignees", [])
        ) or "unassigned"
        author = (pr.get("author") or {}).get("login", "unknown")
        lines.extend(
            [
                f"## PR #{pr['number']} {pr['title']}",
                f"- Updated: {pr.get('updatedAt', '')}",
                f"- Author: {author}",
                f"- Assignees: {assignees}",
                f"- Labels: {labels}",
                f"- Branch: {pr.get('headRefName', '')} -> {pr.get('baseRefName', '')}",
                f"- Draft: {'yes' if pr.get('isDraft') else 'no'}",
                f"- URL: {pr.get('url', '')}",
                trim(pr.get("body", "") or "No body provided.", max_lines=8) or "No body provided.",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def render_recent_merged_pull_requests(pull_requests: dict) -> str:
    lines = ["# Recent Merged Pull Requests", ""]
    merged_prs = pull_requests.get("merged", [])
    if not merged_prs:
        lines.append("- No recently merged PRs were collected.")
        return "\n".join(lines) + "\n"

    for pr in merged_prs[:10]:
        labels = ", ".join(label["name"] for label in pr.get("labels", [])) or "no labels"
        author = (pr.get("author") or {}).get("login", "unknown")
        lines.extend(
            [
                f"## PR #{pr['number']} {pr['title']}",
                f"- Merged At: {pr.get('mergedAt', '')}",
                f"- Updated: {pr.get('updatedAt', '')}",
                f"- Author: {author}",
                f"- Labels: {labels}",
                f"- Branch: {pr.get('headRefName', '')} -> {pr.get('baseRefName', '')}",
                f"- URL: {pr.get('url', '')}",
                trim(pr.get("body", "") or "No body provided.", max_lines=6) or "No body provided.",
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


def render_open_questions(issues: list, progress_items: list, pull_requests: dict) -> str:
    lines = ["# Open Questions", ""]
    open_prs = pull_requests.get("open", [])
    if not issues and not progress_items and not open_prs:
        lines.append("- No structured open questions were found. Add issue bodies or progress logs with explicit gaps.")
        return "\n".join(lines) + "\n"

    for issue in issues[:10]:
        lines.append(f"- Issue #{issue['number']}에서 아직 풀리지 않은 결정: {issue['title']}")
    for pr in open_prs[:8]:
        lines.append(f"- PR #{pr['number']}가 암시하는 후속 결정: {pr['title']}")
    if progress_items:
        lines.append("- Progress logs에서 드러난 검증 공백과 미해결 항목을 다음 workforce에서 정리해야 한다.")
    return "\n".join(lines).strip() + "\n"


def render_issue_execution_history(history: list) -> str:
    lines = ["# Issue Execution History", ""]
    if not history:
        lines.append("- No run-to-issue ledger entries were found yet.")
        return "\n".join(lines) + "\n"

    for entry in history:
        lines.extend(
            [
                f"## {entry.get('recorded_at', 'unknown time')}",
                f"- Workforce: {entry.get('workforce', 'unknown')}",
                f"- Topic: {entry.get('topic', 'unknown')}",
                f"- Repo: {entry.get('issue_repo', 'unknown')}",
                f"- Issue Type: {entry.get('issue_type', 'unknown')}",
                f"- Run Dir: {entry.get('run_dir', 'unknown')}",
            ]
        )
        issue_states = entry.get("issue_states", [])
        if issue_states:
            lines.append("- Current Issue States:")
            for state in issue_states:
                labels = ", ".join(label["name"] for label in state.get("labels", [])) or "no labels"
                assignees = ", ".join(
                    assignee.get("login", "") for assignee in state.get("assignees", [])
                ) or "unassigned"
                lines.append(
                    f"  - #{state.get('number')} {state.get('title')} [{state.get('state')}] "
                    f"(assignees: {assignees}; labels: {labels})"
                )
        else:
            urls = entry.get("issue_urls", [])
            if urls:
                lines.append("- Issued URLs:")
                for url in urls:
                    lines.append(f"  - {url}")
            else:
                lines.append("- No linked issue URLs were recorded.")
        lines.append("")
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

## Source Repo Intent
{normalized['source_repo_intent']}

## Source Repo State
{normalized['source_repo_state']}

## Latest Workforce State
{normalized['latest_workforce_state']}

## Issue Execution History
{normalized['issue_execution_history']}

## Active Issues
{normalized['active_issues']}

## Active Pull Requests
{normalized['active_pull_requests']}

## Recent Merged Pull Requests
{normalized['recent_merged_pull_requests']}

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
    pull_requests = collect_github_pull_requests(args.repo)
    reports = collect_reports()
    progress_items = collect_progress_logs()
    source_state = collect_source_repo_state(Path(args.source_dir))
    source_intent = collect_source_repo_intent(Path(args.source_dir))
    latest_workforce_state = summarize_latest_run(ROOT_DIR / "scripts" / "requirement-debate" / "outputs")
    issue_execution_history = collect_issue_execution_history()

    normalized = {
        "current_situation": render_current_situation(
            args.repo, source_state, source_intent, latest_workforce_state, pull_requests
        ),
        "project_snapshot": render_project_snapshot(args.repo, issues, pull_requests),
        "source_repo_intent": render_source_repo_intent(source_intent),
        "source_repo_state": render_source_repo_state(source_state),
        "latest_workforce_state": render_latest_workforce_state(latest_workforce_state),
        "issue_execution_history": render_issue_execution_history(issue_execution_history),
        "active_issues": render_active_issues(issues),
        "active_pull_requests": render_active_pull_requests(pull_requests),
        "recent_merged_pull_requests": render_recent_merged_pull_requests(pull_requests),
        "recent_progress": render_recent_progress(progress_items),
        "external_report_briefs": render_external_report_briefs(reports),
        "open_questions": render_open_questions(issues, progress_items, pull_requests),
    }

    for filename, content in [
        ("current_situation.md", normalized["current_situation"]),
        ("project_snapshot.md", normalized["project_snapshot"]),
        ("source_repo_intent.md", normalized["source_repo_intent"]),
        ("source_repo_state.md", normalized["source_repo_state"]),
        ("latest_workforce_state.md", normalized["latest_workforce_state"]),
        ("issue_execution_history.md", normalized["issue_execution_history"]),
        ("active_issues.md", normalized["active_issues"]),
        ("active_pull_requests.md", normalized["active_pull_requests"]),
        ("recent_merged_pull_requests.md", normalized["recent_merged_pull_requests"]),
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
