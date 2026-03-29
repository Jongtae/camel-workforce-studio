#!/usr/bin/env python3
"""Build normalized context packs for workforce runs."""

import argparse
import json
import subprocess
from shutil import copy2
from pathlib import Path
import sys
from typing import Iterable, List


ROOT_DIR = Path(__file__).resolve().parents[2]
CONTEXT_DIR = ROOT_DIR / "context"
RAW_DIR = CONTEXT_DIR / "raw"
NORMALIZED_DIR = CONTEXT_DIR / "normalized"
WORKFLOW_INPUTS_DIR = CONTEXT_DIR / "workflow-inputs"
REQUIREMENT_DEBATE_DIR = ROOT_DIR / "scripts" / "requirement-debate"
WORKSPACE_ISSUES_REPO = "Jongtae/camel-workforce-studio"

if str(REQUIREMENT_DEBATE_DIR) not in sys.path:
    sys.path.insert(0, str(REQUIREMENT_DEBATE_DIR))

from workforce_artifacts import (
    discover_latest_run_for_workforce,
    first_section,
    load_run_ledger,
    parse_topic_catalog_items,
    summarize_latest_run,
    bullet_lines,
    markdown_sections,
)


WORKFLOW_OBJECTIVES = {
    "commitment": "현재 프로젝트에서 가장 중요한 gap을 식별하고 topic catalog에서 가장 작은 issue-ready slice 하나를 선택한다.",
    "core": "development 팀 관점에서 mock-to-service 전환을 위한 실제 구현과 아키텍처 결정을 구체화한다.",
    "operator": "운영자 관점에서 컨텐츠 자정, 모니터링, 운영 정책, 기능 개선 레버를 정리한다.",
    "ux": "forum / admin surface UI-UX 완성도를 먼저 닫아 사용자가 실제로 쓰고 싶어지는 가장 작은 slice를 정리한다.",
    "society": "API 기반 forum 위에서 action하는 stateful AI agent의 상태, 기억, characteristic, 내부/외부 콘텐츠 소비 규칙을 정리한다.",
}

DEFAULT_SOFT_GUIDANCE = "처음 시도로는 서비스 완성도를 먼저 닫는 것을 최우선으로 한다. threads와 Twitter 같은 잘 설계된 포럼 UX를 참고하되, 화면이 반쯤 만들어진 것처럼 보이면 ux workforce를 먼저 고려하고 전체 UI/UX 레이아웃과 정보 구조를 먼저 정한 뒤 thread continuity, reply context, compact compose entrypoint, tag navigation, feed clarity, empty state, navigation coherence, copy tone, visual hierarchy 같은 바로 체감되는 surface UX를 정리한다. 운영 도구가 만들다 만 것처럼 보이면 operator hub의 첫 화면, 카드 배치, replay viewer, sprint summary, 빈 상태를 먼저 정리한다. 시뮬레이션 고도화, 불쾌감 감지, 행동 해석, 고급 분석은 서비스가 먼저 닫힌 뒤에만 논의한다."
DEFAULT_TOPIC_CATALOG_PATH = ROOT_DIR / "docs" / "topic-catalog.md"


def ensure_dirs() -> None:
    for path in [
        RAW_DIR / "github",
        RAW_DIR / "reports",
        RAW_DIR / "progress",
        RAW_DIR / "sim-results",
        CONTEXT_DIR / "history",
        CONTEXT_DIR / "schemas",
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


def collect_error_issues(repo: str) -> list:
    """Collect issues and PRs that mention errors, failures, or blockers."""
    # Collect recent closed issues for error patterns
    all_issues = run_gh_json(
        [
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            "all",
            "--limit",
            "200",
            "--json",
            "number,title,body,labels,state,updatedAt,url",
        ],
    )

    error_keywords = [
        "bug", "error", "failed", "failure", "blocked", "blocker",
        "crash", "exception", "timeout", "panic", "broken",
        "regression", "issue", "problem", "failed test",
        "missing", "unmet", "dependency", "cannot", "unable",
        "fix:", "bug:", "issue:", "error:", "broken:"
    ]

    errors = []
    for issue in all_issues if isinstance(all_issues, list) else []:
        title_lower = (issue.get("title", "") or "").lower()
        body_lower = (issue.get("body", "") or "").lower()

        # Check for error keywords
        found_keyword = any(kw in title_lower or kw in body_lower for kw in error_keywords)
        if found_keyword:
            errors.append({
                "number": issue.get("number"),
                "title": issue.get("title", ""),
                "state": issue.get("state", ""),
                "updated": issue.get("updatedAt", ""),
                "url": issue.get("url", ""),
                "labels": [label.get("name", "") for label in issue.get("labels", [])],
                "preview": (issue.get("body", "") or "").split("\n")[0][:100],
            })

    # Sort: open first, then by recency
    errors.sort(key=lambda x: (x["state"] == "closed", -ord(x.get("updated", "")[0]) if x.get("updated") else 0))

    errors_path = RAW_DIR / "github" / "error_issues.json"
    errors_path.write_text(
        json.dumps(errors, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return errors


def collect_workspace_open_issues() -> list:
    issues = run_gh_json(
        [
            "issue",
            "list",
            "--repo",
            WORKSPACE_ISSUES_REPO,
            "--state",
            "open",
            "--limit",
            "50",
            "--json",
            "number,title,body,labels,assignees,updatedAt,url",
        ]
    )
    issues_path = RAW_DIR / "github" / "workspace_issues.json"
    issues_path.write_text(
        json.dumps(issues, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return issues if isinstance(issues, list) else []


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
            "number,title,state,closedAt,url,labels,assignees,comments",
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
                "issue_status": entry.get("issue_status", ""),
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


def collect_sim_results(sim_results_dir: Path | None) -> list:
    if sim_results_dir is None or not sim_results_dir.exists():
        return []

    destination_root = RAW_DIR / "sim-results"
    items = []
    for path in sorted(sim_results_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".json", ".yaml", ".yml", ".md", ".txt", ".log"}:
            continue

        relative = path.relative_to(sim_results_dir)
        destination = destination_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        copy2(path, destination)

        item = {"name": relative.name, "path": str(destination), "relative_path": str(relative)}
        if path.suffix.lower() == ".json":
            try:
                item["entry"] = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                item["text"] = path.read_text(encoding="utf-8", errors="ignore")
        else:
            item["text"] = path.read_text(encoding="utf-8", errors="ignore")
        items.append(item)
    return items


def discover_sim_results_dir(source_dir: Path) -> Path | None:
    candidates = [
        source_dir / "sim-results",
        source_dir / "sim_results",
        source_dir / "results" / "sim",
        source_dir / "reports" / "sim-results",
        source_dir / "docs" / "sim-results",
        source_dir / "artifacts" / "sim-results",
        source_dir / "context" / "sim-results",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


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


def render_soft_guidance(guidance: str | None) -> str:
    lines = ["# Soft Guidance", ""]
    if guidance:
        lines.append(f"- {guidance.strip()}")
    else:
        lines.append("- No soft guidance was provided for this run.")
    return "\n".join(lines).strip() + "\n"


def render_topic_catalog(catalog_text: str | None, catalog_path: Path | None = None) -> str:
    lines = ["# Topic Catalog", ""]
    if not catalog_text:
        source = catalog_path or DEFAULT_TOPIC_CATALOG_PATH
        lines.append(f"- No topic catalog was found at {source}.")
        lines.append("- Commitment will fall back to direct issue-ready slice discovery.")
        return "\n".join(lines).strip() + "\n"
    lines.append(catalog_text.strip())
    return "\n".join(lines).strip() + "\n"


def render_topic_catalog_selection(catalog_text: str | None, catalog_path: Path | None = None) -> str:
    lines = ["# Topic Catalog Selection", ""]
    if not catalog_text:
        source = catalog_path or DEFAULT_TOPIC_CATALOG_PATH
        lines.append(f"- No topic catalog selection index was found at {source}.")
        lines.append("- Commitment will fall back to direct issue-ready slice discovery.")
        return "\n".join(lines).strip() + "\n"

    items = parse_topic_catalog_items(catalog_text)
    if not items:
        lines.append("- No selectable topic entries were parsed from the catalog.")
        return "\n".join(lines).strip() + "\n"

    for item in items:
        lines.extend(
            [
                f"## {item.get('key', '').strip()}",
                f"- Issue Topic: {item.get('issue_topic', '').strip() or item.get('key', '').strip()}",
                f"- Preferred Workforce: {item.get('preferred_workforce', '').strip() or 'unknown'}",
                f"- Goal: {item.get('goal', '').strip() or 'unknown'}",
                f"- Why now: {item.get('why_now', '').strip() or 'unknown'}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


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
    workspace_issues: list,
) -> str:
    latest_summary = latest_workforce_state.strip() or "- No previous workforce state found."
    recent_commit_subjects = [
        commit["subject"] for commit in source_state.get("recent_commits", [])[:3]
    ]
    open_prs = pull_requests.get("open", [])
    merged_prs = pull_requests.get("merged", [])
    open_pr_titles = [pr.get("title", "") for pr in open_prs[:3] if pr.get("title")]
    merged_pr_titles = [pr.get("title", "") for pr in merged_prs[:3] if pr.get("title")]
    workspace_issue_titles = [issue.get("title", "") for issue in workspace_issues[:3] if issue.get("title")]
    lines = [
        "# Current Situation",
        "",
        f"- GitHub repository target: {repo}",
        f"- Local source repository path: {source_state.get('path', '')}",
        f"- Open PR count collected: {len(open_prs)}",
        f"- Recent merged PR count collected: {len(merged_prs)}",
        f"- Workspace open issue count collected: {len(workspace_issues)}",
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
                f"- Workspace open issue directions: {', '.join(workspace_issue_titles) if workspace_issue_titles else 'none'}",
                "",
                "## Already Decided Or Suggested",
                "- Latest workforce state below is the current studio-level baseline unless explicitly challenged.",
                "- 다만 latest workforce state가 source repo intent와 어긋나면 source repo intent를 우선하라.",
                "- Workspace open issues are only relevant when this run is explicitly operating on the studio repo itself.",
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


def render_workspace_open_issues(issues: list, included: bool) -> str:
    lines = ["# Workspace Open Issues", ""]
    if not included:
        lines.append("- Workspace open issues are not included in this run.")
        lines.append("- Pass `--include-workspace-issues` when operating on `camel-workforce-studio` itself.")
        return "\n".join(lines) + "\n"
    if not issues:
        lines.append("- No open workspace issues were found.")
        return "\n".join(lines) + "\n"

    for issue in issues:
        labels = ", ".join(label["name"] for label in issue.get("labels", [])) or "no labels"
        assignees = ", ".join(assignee.get("login", "") for assignee in issue.get("assignees", [])) or "unassigned"
        lines.extend(
            [
                f"## #{issue['number']} {issue['title']}",
                f"- Updated: {issue.get('updatedAt', '')}",
                f"- URL: {issue.get('url', '')}",
                f"- Assignees: {assignees}",
                f"- Labels: {labels}",
                "",
            ]
        )
        body = issue.get("body", "")
        if body:
            lines.append(trim(body, max_lines=8))
            lines.append("")
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


def render_sim_results(sim_results: list) -> str:
    lines = ["# Sim Results", ""]
    if not sim_results:
        lines.append("- No sim result files were collected.")
        return "\n".join(lines) + "\n"

    for item in sim_results:
        lines.append(f"## {item['relative_path']}")
        entry = item.get("entry")
        if entry is not None:
            if isinstance(entry, dict):
                for key, value in entry.items():
                    lines.append(f"- {key}: {value}")
            elif isinstance(entry, list):
                for value in entry:
                    lines.append(f"- {value}")
            else:
                lines.append(f"- {entry}")
        else:
            lines.append(trim(item.get("text", ""), max_lines=12) or "- Empty sim result")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def render_error_analysis(errors: list) -> str:
    lines = ["# Error & Blocker Analysis", ""]
    if not errors:
        lines.append("- No error or blocker issues were found.")
        return "\n".join(lines) + "\n"

    open_errors = [e for e in errors if e["state"] == "open"]
    closed_errors = [e for e in errors if e["state"] == "closed"]

    if open_errors:
        lines.extend(["## Open Errors/Blockers", ""])
        for error in open_errors[:10]:
            labels_str = ", ".join(error["labels"]) if error["labels"] else "no labels"
            lines.extend([
                f"### #{error['number']} {error['title']}",
                f"- Updated: {error['updated']}",
                f"- Labels: {labels_str}",
                f"- Preview: {error['preview']}",
                f"- URL: {error['url']}",
                "",
            ])

    if closed_errors:
        lines.extend(["## Recently Closed Errors (last 30 days)", ""])
        for error in closed_errors[:5]:
            labels_str = ", ".join(error["labels"]) if error["labels"] else "no labels"
            lines.extend([
                f"### #{error['number']} {error['title']} [CLOSED]",
                f"- Closed: {error['updated']}",
                f"- Labels: {labels_str}",
                f"- URL: {error['url']}",
                "",
            ])

    lines.extend([
        "## Workforce Implications",
        f"- {len(open_errors)} open error/blocker issue(s) require attention.",
        f"- {len(closed_errors)} recently closed error(s) may suggest recurring patterns.",
        "- Use this analysis to route 'operator' or 'core' workforce to address critical blockers.",
        "- Consider whether error patterns suggest gaps in backend/frontend/integration tests.",
    ])

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
                f"- Issue Status: {entry.get('issue_status', 'unknown')}",
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


def summarize_thread_comment(issue_state: dict) -> str:
    comments = issue_state.get("comments", [])
    if not comments:
        return ""
    latest_comment = comments[-1]
    body = str(latest_comment.get("body", "")).strip()
    if not body:
        return ""
    excerpt_lines = []
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("## "):
            continue
        excerpt_lines.append(line)
        if len(excerpt_lines) >= 3:
            break
    excerpt = " ".join(excerpt_lines)
    return trim(excerpt, max_lines=2) if excerpt else ""


def render_issue_thread_summary(history: list) -> str:
    lines = ["# Issue Thread Summary", ""]
    if not history:
        lines.append("- No run-linked issue threads were found.")
        return "\n".join(lines) + "\n"

    for entry in history[:12]:
        lines.extend(
            [
                f"## {entry.get('recorded_at', 'unknown time')}",
                f"- Workforce: {entry.get('workforce', 'unknown')}",
                f"- Topic: {entry.get('topic', 'unknown')}",
                f"- Issue Status: {entry.get('issue_status', 'unknown')}",
            ]
        )
        issue_states = entry.get("issue_states", [])
        if issue_states:
            for state in issue_states:
                labels = ", ".join(label["name"] for label in state.get("labels", [])) or "no labels"
                assignees = ", ".join(
                    assignee.get("login", "") for assignee in state.get("assignees", [])
                ) or "unassigned"
                thread_state = str(state.get("state", "")).upper() or "UNKNOWN"
                lines.append(
                    f"- Thread Issue #{state.get('number')} {state.get('title')} [{thread_state}] "
                    f"(assignees: {assignees}; labels: {labels})"
                )
                comment_excerpt = summarize_thread_comment(state)
                if comment_excerpt:
                    lines.append(f"  - Latest Comment Excerpt: {comment_excerpt}")
        else:
            lines.append("- No linked issue snapshot was available.")

        decision_summary = ""
        run_dir = Path(str(entry.get("run_dir", "")))
        if run_dir.exists():
            decision_path = run_dir / "decision.md"
            reflection_path = run_dir / "reflection.md"
            if decision_path.exists():
                decision_summary = first_section(
                    decision_path.read_text(encoding="utf-8"),
                    "Summary",
                    "Key Decisions",
                    "Required Decisions",
                )
            reflection_summary = ""
            if reflection_path.exists():
                reflection_summary = first_section(
                    reflection_path.read_text(encoding="utf-8"),
                    "What Worked",
                    "What Is Still Blocked",
                    "Continuation Hint",
                )
            if decision_summary:
                lines.append(f"- Latest Decision Summary: {trim(decision_summary, max_lines=3)}")
            if reflection_summary:
                lines.append(f"- Latest Reflection Hint: {trim(reflection_summary, max_lines=3)}")
        lines.append("")

    lines.extend(
        [
            "## Commitment Use",
            "- Use this summary as the first memory layer when deciding whether a topic is truly new or a continuation.",
            "- Prefer continuation comments and follow-up reasoning over re-opening a closed thread as a brand-new ticket.",
            "- If the summary already shows the same issue family has been explored, route to the next workforce or append continuation context instead of restarting from scratch.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def render_latest_workforce_state(latest_workforce_state: str) -> str:
    return latest_workforce_state.strip() + ("\n" if latest_workforce_state else "")


def render_society_output_contract(contract: dict) -> str:
    lines = ["# Society Output Contract", ""]
    if not contract.get("exists"):
        lines.append("- No society run artifacts were found.")
        return "\n".join(lines) + "\n"

    lines.extend(
        [
            f"- Source Run Dir: {contract.get('source_run_dir', '')}",
            f"- Source Decision: {contract.get('decision_path', '')}",
            f"- Export Path: {contract.get('export_path', '')}",
            "",
            "## Agent Seed",
        ]
    )
    agent_seed = contract.get("agent_seed", {})
    for key, value in agent_seed.items():
        lines.append(f"- {key}: {value}")

    for section_name in [
        "action_loop",
        "state_model",
        "memory_writeback_rules",
        "action_selection_links",
        "content_consumption",
        "required_backend_artifacts",
    ]:
        section = contract.get(section_name, {})
        lines.extend(["", f"## {section_name}"])
        if isinstance(section, dict):
            for key, value in section.items():
                lines.append(f"- {key}: {value}")
        else:
            lines.append(f"- {section}")

    return "\n".join(lines).strip() + "\n"


def write_normalized_file(name: str, content: str) -> Path:
    path = NORMALIZED_DIR / name
    path.write_text(content, encoding="utf-8")
    return path


def write_json_file(name: str, payload: dict) -> Path:
    path = NORMALIZED_DIR / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def build_society_output_contract(output_dir: Path) -> dict:
    latest_society_run = discover_latest_run_for_workforce(output_dir, "society")
    if not latest_society_run:
        return {"exists": False}

    decision_path = latest_society_run / "decision.md"
    if not decision_path.exists():
        return {"exists": False}

    decision_text = decision_path.read_text(encoding="utf-8", errors="ignore")
    sections = markdown_sections(decision_text)
    export = {
        "exists": True,
        "version": 1,
        "source_run_dir": str(latest_society_run),
        "decision_path": str(decision_path),
        "issue_title": first_section(decision_text, "Issue Title").splitlines()[0].strip() if first_section(decision_text, "Issue Title") else "",
        "summary": bullet_lines(first_section(decision_text, "Summary")),
        "acceptance_criteria": bullet_lines(first_section(decision_text, "Acceptance Criteria")),
        "technical_notes": bullet_lines(first_section(decision_text, "Technical Notes")),
        "open_questions": bullet_lines(first_section(decision_text, "Open Questions")),
        "priority": first_section(decision_text, "Priority").splitlines()[0].strip() if first_section(decision_text, "Priority") else "",
        "agent_seed": {
            "identity": sections.get("State Model", ""),
            "memory_initial": sections.get("Memory Writeback Rules", ""),
            "characteristic": sections.get("State Model", ""),
        },
        "action_loop": sections.get("Action Loop", ""),
        "state_model": sections.get("State Model", ""),
        "state_transitions": sections.get("State Transitions", ""),
        "memory_writeback_rules": sections.get("Memory Writeback Rules", ""),
        "action_selection_links": sections.get("Action Selection Links", ""),
        "content_consumption": sections.get("Content Consumption", ""),
        "required_backend_artifacts": sections.get("Required Backend Artifacts", ""),
    }
    export_path = NORMALIZED_DIR / "society_output_contract.json"
    export["export_path"] = str(export_path)
    return export


def build_workflow_input(workforce: str, normalized: dict) -> str:
    return f"""# Workflow Input

## Workflow
{workforce}

## Objective
{WORKFLOW_OBJECTIVES[workforce]}

## Soft Guidance
{normalized['soft_guidance']}

## Topic Catalog
{normalized['topic_catalog']}

## Topic Catalog Selection
{normalized['topic_catalog_selection']}

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

## Issue Thread Summary
{normalized['issue_thread_summary']}

## Active Issues
{normalized['active_issues']}

## Error & Blocker Analysis
{normalized['error_analysis']}

## Active Pull Requests
{normalized['active_pull_requests']}

## Recent Merged Pull Requests
{normalized['recent_merged_pull_requests']}

## Recent Progress
{normalized['recent_progress']}

## External Evidence
{normalized['external_report_briefs']}

## Sim Results
{normalized['sim_results']}

## Society Output Contract
{normalized['society_output_contract']}

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
    parser.add_argument(
        "--sim-results-dir",
        type=str,
        default=None,
        help="AI-Fashion-Forum 실험 산출물을 읽을 로컬 디렉터리 경로",
    )
    parser.add_argument(
        "--include-workspace-issues",
        action="store_true",
        help="camel-workforce-studio 자체의 open issues를 context에 포함한다. 기본값은 false다.",
    )
    parser.add_argument(
        "--soft-guidance",
        type=str,
        default=None,
        help="commitment/topic selection에 반영할 soft guidance 문장",
    )
    parser.add_argument(
        "--topic-catalog",
        type=str,
        default=None,
        help="commitment가 참고할 topic catalog markdown 파일 경로",
    )
    args = parser.parse_args()

    ensure_dirs()

    issues = collect_github_issues(args.repo)
    error_issues = collect_error_issues(args.repo)
    workspace_issues = collect_workspace_open_issues() if args.include_workspace_issues else []
    pull_requests = collect_github_pull_requests(args.repo)
    reports = collect_reports()
    progress_items = collect_progress_logs()
    sim_results_dir = Path(args.sim_results_dir) if args.sim_results_dir else discover_sim_results_dir(Path(args.source_dir))
    sim_results = collect_sim_results(sim_results_dir)
    source_state = collect_source_repo_state(Path(args.source_dir))
    source_intent = collect_source_repo_intent(Path(args.source_dir))
    latest_workforce_state = summarize_latest_run(ROOT_DIR / "scripts" / "requirement-debate" / "outputs")
    issue_execution_history = collect_issue_execution_history()
    issue_thread_summary = render_issue_thread_summary(issue_execution_history)
    society_output_contract = build_society_output_contract(ROOT_DIR / "scripts" / "requirement-debate" / "outputs")

    topic_catalog_path = Path(args.topic_catalog) if args.topic_catalog else DEFAULT_TOPIC_CATALOG_PATH
    topic_catalog_text = topic_catalog_path.read_text(encoding="utf-8") if topic_catalog_path.exists() else ""

    normalized = {
        "soft_guidance": render_soft_guidance(args.soft_guidance),
        "topic_catalog": render_topic_catalog(topic_catalog_text, topic_catalog_path),
        "topic_catalog_selection": render_topic_catalog_selection(topic_catalog_text, topic_catalog_path),
        "current_situation": render_current_situation(
            args.repo,
            source_state,
            source_intent,
            latest_workforce_state,
            pull_requests,
            workspace_issues,
        ),
        "project_snapshot": render_project_snapshot(args.repo, issues, pull_requests),
        "workspace_open_issues": render_workspace_open_issues(workspace_issues, args.include_workspace_issues),
        "source_repo_intent": render_source_repo_intent(source_intent),
        "source_repo_state": render_source_repo_state(source_state),
        "latest_workforce_state": render_latest_workforce_state(latest_workforce_state),
        "issue_execution_history": render_issue_execution_history(issue_execution_history),
        "issue_thread_summary": issue_thread_summary,
        "active_issues": render_active_issues(issues),
        "error_analysis": render_error_analysis(error_issues),
        "active_pull_requests": render_active_pull_requests(pull_requests),
        "recent_merged_pull_requests": render_recent_merged_pull_requests(pull_requests),
        "recent_progress": render_recent_progress(progress_items),
        "external_report_briefs": render_external_report_briefs(reports),
        "sim_results": render_sim_results(sim_results),
        "society_output_contract": render_society_output_contract(society_output_contract),
        "open_questions": render_open_questions(issues, progress_items, pull_requests),
    }

    for filename, content in [
        ("current_situation.md", normalized["current_situation"]),
        ("soft_guidance.md", normalized["soft_guidance"]),
        ("topic_catalog.md", normalized["topic_catalog"]),
        ("topic_catalog_selection.md", normalized["topic_catalog_selection"]),
        ("project_snapshot.md", normalized["project_snapshot"]),
        ("workspace_open_issues.md", normalized["workspace_open_issues"]),
        ("source_repo_intent.md", normalized["source_repo_intent"]),
        ("source_repo_state.md", normalized["source_repo_state"]),
        ("latest_workforce_state.md", normalized["latest_workforce_state"]),
        ("issue_execution_history.md", normalized["issue_execution_history"]),
        ("issue_thread_summary.md", normalized["issue_thread_summary"]),
        ("active_issues.md", normalized["active_issues"]),
        ("error_analysis.md", normalized["error_analysis"]),
        ("active_pull_requests.md", normalized["active_pull_requests"]),
        ("recent_merged_pull_requests.md", normalized["recent_merged_pull_requests"]),
        ("recent_progress.md", normalized["recent_progress"]),
        ("external_report_briefs.md", normalized["external_report_briefs"]),
        ("sim_results.md", normalized["sim_results"]),
        ("society_output_contract.md", normalized["society_output_contract"]),
        ("open_questions.md", normalized["open_questions"]),
    ]:
        write_normalized_file(filename, content)
    write_json_file("society_output_contract.json", society_output_contract)

    for workforce in WORKFLOW_OBJECTIVES:
        path = WORKFLOW_INPUTS_DIR / f"{workforce}.md"
        path.write_text(build_workflow_input(workforce, normalized), encoding="utf-8")
        print(f"✓ workflow input 생성: {path}")

    print(f"✓ normalized context 생성 완료: {NORMALIZED_DIR}")


if __name__ == "__main__":
    main()
