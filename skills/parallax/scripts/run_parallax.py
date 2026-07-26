#!/usr/bin/env python3
"""Run two independent Gauntlet Fast research programs in parallel.

Full Parallax is intentionally a comparison workflow, not a synthesis workflow:

* Claude branch: four Sonnet 5 xhigh workers -> one Opus 5 high lead.
* Codex branch: four GPT-5.6 Sol high workers -> one GPT-5.6 Sol high lead.
* Each branch runs its own Search-as-Code pass and writes a complete research package.
* Neither branch may read the other branch's files.
* No merger, adjudicator, combined verdict, claim matrix, or final answer is produced.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any
import zipfile


CLAUDE_LEAD_MODEL = "claude-opus-5"
CLAUDE_LEAD_EFFORT = "high"
CLAUDE_WORKER_MODEL = "claude-sonnet-5"
CLAUDE_WORKER_EFFORT = "xhigh"
CODEX_LEAD_MODEL = "gpt-5.6-sol"
CODEX_LEAD_EFFORT = "high"
CODEX_WORKER_MODEL = "gpt-5.6-sol"
CODEX_WORKER_EFFORT = "high"

BRANCH_DIRECTORY = {
    "claude": "claude_research",
    "codex": "codex_research",
}

WORKER_LANES = (
    {
        "id": 1,
        "slug": "demand_market",
        "objective": (
            "Demand durability, TAM and addressable population or unit volumes, customer evidence, "
            "market expectations, end-market structure, and five-year demand/rent-capture outlook."
        ),
    },
    {
        "id": 2,
        "slug": "competition_moat",
        "objective": (
            "Competitive landscape, substitutes, named direct and adjacent threats, product or "
            "pipeline differentiation, moat scoring inputs, IP, switching costs, and bear evidence."
        ),
    },
    {
        "id": 3,
        "slug": "filings_financials_valuation",
        "objective": (
            "SEC and issuer filings, historical statements and KPIs, capital structure, ownership, "
            "runway, valuation inputs, scenario mechanics, and independently reproducible figures."
        ),
    },
    {
        "id": 4,
        "slug": "catalysts_regulatory_management",
        "objective": (
            "Catalysts, regulatory and legal status, clinical or operating milestones, management "
            "and governance, insider activity, institutional ownership, financing, and falsifiers."
        ),
    },
)

REQUIRED_BRANCH_FILES = (
    "01_scope_and_assumptions.md",
    "02_source_manifest.csv",
    "03_evidence_ledger.csv",
    "04_catalyst_and_pos_model.py",
    "05_valuation_model.py",
    "06_model_outputs.csv",
    "07_working_research.md",
    "08_preliminary_report.md",
    "FINAL_REPORT.md",
    "FINAL_REPORT.html",
    "VERIFICATION_LOG.md",
    "sources.jsonl",
    "evidence.jsonl",
    "audit_manifest.json",
    "run_manifest.json",
)

USER_HOME = Path.home()
CLAUDE_CONFIG_ROOT = Path(
    os.environ.get("CLAUDE_CONFIG_DIR", str(USER_HOME / ".claude"))
).expanduser()
CODEX_CONFIG_ROOT = Path(
    os.environ.get("CODEX_HOME", str(USER_HOME / ".codex"))
).expanduser()

GAUNTLET_PROMPT_CANDIDATES = (
    CLAUDE_CONFIG_ROOT / "skills/gauntlet/references/master_research_prompt.md",
    USER_HOME / "gauntlet/references/master_research_prompt.md",
)

SEARCH_AS_CODE_SCRIPTS = {
    "claude": CLAUDE_CONFIG_ROOT / "skills/search-as-code/scripts/sac_search.py",
    "codex": CODEX_CONFIG_ROOT / "skills/search-as-code/scripts/sac_search.py",
}

FAST_BANNER = "FAST MODE — single-model draft, NOT adversarially reviewed"
FORBIDDEN_ARTIFACT_TOKENS = (
    "merged",
    "merger",
    "verdict",
    "claim_matrix",
    "final_answer",
    "adjudicator",
    "adjudication_report",
    "combined_report",
    "combined_final",
    "consensus_report",
    "consensus_verdict",
    "preferred_model",
    "preferred_report",
)
FORBIDDEN_REPORT_PHRASES = (
    "merged verdict",
    "combined verdict",
    "claim matrix",
    "preferred model",
    "preferred report",
    "consensus verdict",
    "cross-model adjudication",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value.strip()).strip("_")
    return (slug or "Research")[:80]


def ticker_guess(subject: str) -> str | None:
    candidate = subject.strip().upper()
    return candidate if re.fullmatch(r"[A-Z]{1,6}(?:[.-][A-Z]{1,3})?", candidate) else None


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(
        f".{path.name}.tmp-{os.getpid()}-{threading.get_ident()}"
    )
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json(path: Path, payload: Any) -> None:
    atomic_write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def default_project_dir(subject: str) -> Path:
    date = datetime.now().astimezone().strftime("%Y%m%d")
    return Path.home() / "Documents" / f"{slugify(subject)}_Parallax_{date}"


def resolve_project_dir(subject: str, requested: Path | None) -> Path:
    if requested is not None:
        return requested.expanduser().resolve()
    base = default_project_dir(subject)
    if not base.exists():
        return base
    return base.with_name(f"{base.name}_{utc_stamp().split('_', 1)[1]}")


def resolve_gauntlet_prompt() -> Path:
    override = os.environ.get("PARALLAX_GAUNTLET_PROMPT")
    candidates = ((Path(override).expanduser(),) if override else ()) + GAUNTLET_PROMPT_CANDIDATES
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    joined = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"Gauntlet master research prompt not found; checked: {joined}")


def ensure_project_layout(project_dir: Path) -> dict[str, Path]:
    if project_dir.exists() and any(project_dir.iterdir()):
        raise FileExistsError(f"project directory is not empty: {project_dir}")
    project_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Path] = {}
    for branch, dirname in BRANCH_DIRECTORY.items():
        branch_dir = project_dir / dirname
        for relative in ("lanes", "search_as_code", "logs", "prompts"):
            (branch_dir / relative).mkdir(parents=True, exist_ok=True)
        result[branch] = branch_dir
    return result


def build_claude_argv(model: str, effort: str, cwd: Path) -> list[str]:
    """Build a full-tool Claude leaf invocation without stripping hosted MCPs."""
    return [
        "claude",
        "-p",
        "--model",
        model,
        "--effort",
        effort,
        "--permission-mode",
        "bypassPermissions",
        "--output-format",
        "text",
        "--no-session-persistence",
        "--disable-slash-commands",
        "--add-dir",
        str(cwd),
    ]


def build_codex_argv(model: str, effort: str, cwd: Path) -> list[str]:
    """Build a full-tool Codex leaf invocation preserving user MCP configuration."""
    return [
        "codex",
        "exec",
        "--cd",
        str(cwd),
        "--skip-git-repo-check",
        "--ephemeral",
        "-s",
        "danger-full-access",
        "-c",
        'approval_policy="never"',
        "-c",
        "tools.web_search=true",
        "-m",
        model,
        "-c",
        f'model_reasoning_effort="{effort}"',
        "--json",
        "-",
    ]


def codex_last_message(events_jsonl: str) -> str:
    messages: list[str] = []
    for line in events_jsonl.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or event.get("type") != "item.completed":
            continue
        item = event.get("item")
        if (
            isinstance(item, dict)
            and item.get("type") == "agent_message"
            and isinstance(item.get("text"), str)
        ):
            messages.append(item["text"])
    return messages[-1] if messages else ""


def terminate_process_group(proc: subprocess.Popen[str], grace_seconds: float = 5.0) -> None:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=grace_seconds)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        return


def run_capture(
    argv: list[str],
    *,
    stdin_text: str | None = None,
    timeout: int,
    codex_json: bool = False,
    cwd: Path | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    proc = subprocess.Popen(
        argv,
        stdin=subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
        cwd=cwd,
    )
    try:
        stdout, stderr = proc.communicate(input=stdin_text, timeout=timeout)
        raw_stdout = stdout
        final_stdout = codex_last_message(raw_stdout) if codex_json else raw_stdout
        return {
            "status": "ok" if proc.returncode == 0 else "error",
            "returncode": proc.returncode,
            "seconds": round(time.monotonic() - started, 3),
            "stdout": final_stdout,
            "raw_stdout": raw_stdout if codex_json else "",
            "stderr": stderr,
            "argv": argv,
        }
    except subprocess.TimeoutExpired as exc:
        terminate_process_group(proc)
        stdout, stderr = proc.communicate()
        def decoded(value: str | bytes | None) -> str:
            if isinstance(value, bytes):
                return value.decode("utf-8", errors="replace")
            return value or ""

        raw_stdout = decoded(exc.stdout) + decoded(stdout)
        final_stdout = codex_last_message(raw_stdout) if codex_json else raw_stdout
        return {
            "status": "timeout",
            "returncode": 124,
            "seconds": round(time.monotonic() - started, 3),
            "stdout": final_stdout,
            "raw_stdout": raw_stdout if codex_json else "",
            "stderr": decoded(exc.stderr) + decoded(stderr),
            "argv": argv,
        }
    except Exception as exc:  # last-resort operational capture
        terminate_process_group(proc)
        return {
            "status": "exception",
            "returncode": -1,
            "seconds": round(time.monotonic() - started, 3),
            "stdout": "",
            "raw_stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
            "argv": argv,
        }


def write_stage_logs(base: Path, stage: str, result: dict[str, Any]) -> None:
    log_dir = base / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "stage": stage,
        "status": result.get("status"),
        "returncode": result.get("returncode"),
        "seconds": result.get("seconds"),
        "argv": result.get("argv"),
        "recorded_at": utc_now(),
    }
    write_json(log_dir / f"{stage}.json", metadata)
    atomic_write(log_dir / f"{stage}.stderr.log", result.get("stderr", "") or "")
    if result.get("raw_stdout"):
        atomic_write(log_dir / f"{stage}.raw_events.jsonl", result["raw_stdout"])


def build_search_plan(subject: str, request: str, output_dir: Path) -> dict[str, Any]:
    """Create the same coverage contract but a separate plan for each branch."""
    query_specs = (
        ("official filings latest 10-K 10-Q 8-K exhibits", "filings", "Map current primary filings."),
        ("latest earnings release transcript guidance KPIs", "results_earnings", "Verify current operating results."),
        ("investor relations presentation products pipeline strategy", "issuer_ir", "Verify active programs and strategy."),
        ("historical revenue margins cash flow balance sheet shares", "financials", "Build audited financial history."),
        ("capital structure debt converts warrants options dilution", "financials", "Reconcile the equity bridge."),
        ("governance executives board compensation ownership Form 4", "governance", "Assess management and governance."),
        ("institutional ownership 13F 13D 13G changes", "governance", "Map lag-aware ownership changes."),
        ("competitive landscape direct competitors substitutes market share", "peers", "Map named competition."),
        ("customer supplier partner evidence demand market size", "peers", "Test demand and ecosystem claims."),
        ("bear case short thesis risks failed assumptions", "bear_case", "Find contrary evidence."),
        ("regulatory legal litigation compliance decisions", "news_catalyst", "Map legal and regulatory risk."),
        ("catalysts next 12 months exact dates calendar", "news_catalyst", "Build a dated catalyst calendar."),
        ("financing offerings ATM shelf capital raises runway", "ma", "Assess financing and solvency."),
        ("valuation reverse DCF expectations multiples peers", "valuation", "Map market expectations and valuation inputs."),
        ("five year demand durability moat bottlenecks rent capture", "peers", "Assess long-horizon durability."),
        ("recent news last 90 days material developments", "news_catalyst", "Capture current developments."),
        ("clinical trials FDA PubMed evidence safety efficacy", "news_catalyst", "Discover biomedical evidence when relevant."),
        ("patents intellectual property exclusivity freedom to operate", "issuer_ir", "Assess defensibility."),
        ("bull case upside optionality underappreciated assets", "valuation", "Find supportable upside evidence."),
        ("historical catalyst outcomes stock reactions analogs", "news_catalyst", "Calibrate event-response assumptions."),
        ("consensus estimates dispersion revisions expectations", "valuation", "Map expectations without importing targets."),
        ("segment geography product unit economics pricing volumes", "financials", "Build operating drivers."),
        ("M&A partnerships licensing milestones royalties contracts", "ma", "Verify strategic and partner economics."),
        ("thesis falsifiers kill switches measurable thresholds", "bear_case", "Define observable invalidation tests."),
    )
    queries = []
    for index, (suffix, query_type, purpose) in enumerate(query_specs, start=1):
        queries.append(
            {
                "query": f"{subject} {suffix}",
                "purpose": f"{purpose} User request context: {request[:180]}",
                "query_type": query_type,
                "max_results": 10,
                "snippet_mode": "high",
                "priority": index,
            }
        )
    plan: dict[str, Any] = {
        "topic": subject,
        "mode": "ultradeep",
        "output_dir": str(output_dir),
        "plan_type": "parallax_gauntlet_fast_branch",
        "entity": subject,
        "queries": queries,
    }
    ticker = ticker_guess(subject)
    if ticker:
        plan["ticker"] = ticker
    return plan


def branch_models(branch: str) -> dict[str, str]:
    if branch == "claude":
        return {
            "lead_model": CLAUDE_LEAD_MODEL,
            "lead_effort": CLAUDE_LEAD_EFFORT,
            "worker_model": CLAUDE_WORKER_MODEL,
            "worker_effort": CLAUDE_WORKER_EFFORT,
        }
    return {
        "lead_model": CODEX_LEAD_MODEL,
        "lead_effort": CODEX_LEAD_EFFORT,
        "worker_model": CODEX_WORKER_MODEL,
        "worker_effort": CODEX_WORKER_EFFORT,
    }


def build_worker_prompt(
    branch: str,
    branch_dir: Path,
    lane_dir: Path,
    lane: dict[str, Any],
    subject: str,
    request: str,
) -> str:
    models = branch_models(branch)
    return f"""# Independent Gauntlet Fast research worker

You are worker {lane['id']} of exactly four research workers in one isolated research program.
You are a delegated leaf. Never spawn agents, subagents, panels, workflows, or child processes.
Do not invoke deep-research, Search-as-Code, Gauntlet, Parallax, model-fusion, or another skill.
The outer runner performs fan-out and Search-as-Code after this native-discovery wave.

Subject: {subject}
User request:
{request}

Your non-overlapping lane objective:
{lane['objective']}

Execution contract:
- Use your runtime's native web search first for discovery and current verification.
- Open primary documents and inspect the exact passages supporting material claims.
- Use FMP /stable/ when relevant, then reconcile every material financial figure to filings.
- For biomedical topics use BioMCP and PubMed/PMC first, then Scite selectively. If your runtime
  lacks a BioMCP connector or skill wrapper, use the installed `biomcp` CLI on PATH.
- Do not use direct Perplexity in this wave; the branch runs Search-as-Code next and the lead performs
  targeted Perplexity gap searches afterward.
- Preserve source identity, issuer/author, date, exact locator, and a short direct excerpt or observed
  output for every material item.
- Execute nontrivial arithmetic with Python or the appropriate domain tool.
- After two materially different failed verification attempts, mark [UNKNOWN - NOT VERIFIED].
- Treat search snippets and connector summaries as discovery only.
- Do not state a final rating or price target outside this lane.
- Do not read outside this branch directory: {branch_dir}
- You may use only this lane workspace for scratch files: {lane_dir}

Model contract recorded by the runner: {models['worker_model']} at {models['worker_effort']} effort.

Final response format:
1. Lane scope and searched query families.
2. Verified evidence table with atomic claim, classification, source, date, exact locator, excerpt,
   source tier, status, and consequence if wrong.
3. Calculations and preserved outputs.
4. Contrary evidence and source conflicts.
5. Unknowns after the two-attempt rule.
6. Handoff notes limited to this lane.

Emit the complete lane report in your final response. Do not return only a path.
"""


def worker_stub(branch: str, lane: dict[str, Any], subject: str) -> str:
    lines = [
        f"# {branch.title()} worker lane {lane['id']} dry-run report",
        "",
        "## Lane scope and searched query families",
        lane["objective"],
        "",
        "## Verified evidence",
        "| Claim | Classification | Source | Date | Locator | Excerpt | Tier | Status | Consequence |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        f"| Dry-run claim for {subject} | VERIFIED FACT | dry-run primary source | 2026-01-01 | page:1 | deterministic test excerpt | 1 | verified | dry-run consequence |",
        "",
        "## Calculations",
        "Dry-run calculation output: 1 + 1 = 2.",
        "",
        "## Contrary evidence and conflicts",
        "No dry-run conflict.",
        "",
        "## Unknowns",
        "None in deterministic dry-run.",
        "",
        "## Handoff",
        "This is deterministic test content, not research.",
    ]
    text = "\n".join(lines) + "\n"
    while len(text.encode("utf-8")) < 1800:
        text += "Dry-run evidence padding for minimum-size and capture-path validation.\n"
    return text


def should_force_fail(branch: str, stage: str) -> bool:
    forced = os.environ.get("PARALLAX_DRY_RUN_FAIL", "").strip().lower()
    return forced in {branch, "both", f"{branch}_{stage}", f"both_{stage}"}


def execute_worker(
    *,
    branch: str,
    branch_dir: Path,
    lane: dict[str, Any],
    subject: str,
    request: str,
    dry_run: bool,
    timeout: int,
    retry_timeout: int,
    min_bytes: int,
) -> dict[str, Any]:
    lane_dir = branch_dir / "lanes" / f"lane_{lane['id']}_{lane['slug']}"
    lane_dir.mkdir(parents=True, exist_ok=True)
    prompt = build_worker_prompt(branch, branch_dir, lane_dir, lane, subject, request)
    atomic_write(lane_dir / "prompt.md", prompt)

    attempts: list[dict[str, Any]] = []
    for attempt, attempt_timeout in ((1, timeout), (2, retry_timeout)):
        if dry_run:
            if should_force_fail(branch, "worker"):
                result = {
                    "status": "error",
                    "returncode": 1,
                    "seconds": 0.001,
                    "stdout": "",
                    "raw_stdout": "",
                    "stderr": f"dry-run forced {branch} failure",
                    "argv": ["<dry-run>"],
                }
            else:
                result = {
                    "status": "ok",
                    "returncode": 0,
                    "seconds": 0.001,
                    "stdout": worker_stub(branch, lane, subject),
                    "raw_stdout": "",
                    "stderr": "",
                    "argv": ["<dry-run>"],
                }
        else:
            models = branch_models(branch)
            if branch == "claude":
                argv = build_claude_argv(
                    models["worker_model"], models["worker_effort"], lane_dir
                )
                result = run_capture(
                    argv,
                    stdin_text=prompt,
                    timeout=attempt_timeout,
                    codex_json=False,
                    cwd=lane_dir,
                )
            else:
                argv = build_codex_argv(
                    models["worker_model"], models["worker_effort"], lane_dir
                )
                result = run_capture(
                    argv, stdin_text=prompt, timeout=attempt_timeout, codex_json=True
                )
        attempts.append(
            {
                "attempt": attempt,
                "status": result["status"],
                "returncode": result["returncode"],
                "seconds": result["seconds"],
                "bytes": len(result.get("stdout", "").encode("utf-8")),
            }
        )
        write_stage_logs(lane_dir, f"worker_attempt_{attempt}", result)
        output = result.get("stdout", "")
        if result["returncode"] == 0 and len(output.encode("utf-8")) >= min_bytes:
            atomic_write(lane_dir / "report.md", output)
            return {
                "id": lane["id"],
                "slug": lane["slug"],
                "status": "complete",
                "attempts": attempts,
                "report": str(lane_dir / "report.md"),
                "bytes": len(output.encode("utf-8")),
            }
    atomic_write(
        lane_dir / "FAILED.md",
        f"# Worker failed\n\nBranch: {branch}\nLane: {lane['id']}\nAttempts: {json.dumps(attempts)}\n",
    )
    return {
        "id": lane["id"],
        "slug": lane["slug"],
        "status": "failed",
        "attempts": attempts,
        "report": None,
        "bytes": 0,
    }


def run_workers(
    *,
    branch: str,
    branch_dir: Path,
    subject: str,
    request: str,
    args: argparse.Namespace,
) -> list[dict[str, Any]]:
    results: dict[int, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(
                execute_worker,
                branch=branch,
                branch_dir=branch_dir,
                lane=lane,
                subject=subject,
                request=request,
                dry_run=args.dry_run,
                timeout=args.worker_timeout,
                retry_timeout=args.retry_timeout,
                min_bytes=args.min_worker_bytes,
            ): lane["id"]
            for lane in WORKER_LANES
        }
        for future in as_completed(futures):
            lane_id = futures[future]
            try:
                results[lane_id] = future.result()
            except Exception as exc:
                results[lane_id] = {
                    "id": lane_id,
                    "slug": WORKER_LANES[lane_id - 1]["slug"],
                    "status": "failed",
                    "attempts": [],
                    "report": None,
                    "bytes": 0,
                    "error": f"{type(exc).__name__}: {exc}",
                }
    return [results[index] for index in sorted(results)]


def write_dry_search_outputs(search_dir: Path, plan: dict[str, Any], branch: str) -> None:
    write_json(search_dir / "search_plan.json", plan)
    write_json(
        search_dir / "run_manifest.json",
        {
            "status": "complete",
            "mode": "ultradeep",
            "branch": branch,
            "dry_run": True,
            "successful_http_request_count": 0,
        },
    )
    write_json(search_dir / "plan_quality.json", {"status": "pass", "dry_run": True})
    write_json(
        search_dir / "coverage_diagnostics.json",
        {"status": "pass", "dry_run": True, "query_count": len(plan["queries"])},
    )
    atomic_write(
        search_dir / "coverage_summary.md",
        f"# Dry-run Search-as-Code coverage\n\nBranch: {branch}\nQueries: {len(plan['queries'])}\n",
    )
    atomic_write(
        search_dir / "sources.jsonl",
        json.dumps(
            {
                "source_id": f"dry-{branch}-source-1",
                "title": "Dry-run source",
                "source_tier": 1,
                "url": "https://example.invalid/dry-run",
            }
        )
        + "\n",
    )
    atomic_write(
        search_dir / "evidence.jsonl",
        json.dumps(
            {
                "source_id": f"dry-{branch}-source-1",
                "evidence_type": "extracted_quote",
                "quote": "Dry-run extracted evidence.",
                "locator": "page:1",
            }
        )
        + "\n",
    )


def run_search_as_code(
    *,
    branch: str,
    branch_dir: Path,
    subject: str,
    request: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    search_dir = branch_dir / "search_as_code"
    plan = build_search_plan(subject, request, search_dir)
    plan_path = search_dir / "search_plan.json"
    write_json(plan_path, plan)
    if args.dry_run:
        if should_force_fail(branch, "search"):
            return {
                "status": "failed",
                "attempts": 1,
                "query_count": len(plan["queries"]),
                "run_dir": str(search_dir),
                "dry_run": True,
                "error": f"dry-run forced {branch} Search-as-Code failure",
            }
        write_dry_search_outputs(search_dir, plan, branch)
        return {
            "status": "complete",
            "attempts": 1,
            "query_count": len(plan["queries"]),
            "run_dir": str(search_dir),
            "dry_run": True,
        }

    script = SEARCH_AS_CODE_SCRIPTS[branch]
    if not script.is_file():
        return {
            "status": "failed_degraded",
            "attempts": 0,
            "query_count": len(plan["queries"]),
            "run_dir": str(search_dir),
            "error": f"missing Search-as-Code script: {script}",
        }

    validate = run_capture(
        ["python3", str(script), "validate", "--plan", str(plan_path)],
        timeout=120,
    )
    write_stage_logs(branch_dir, "search_as_code_validate", validate)
    if validate["returncode"] != 0:
        return {
            "status": "failed_degraded",
            "attempts": 0,
            "query_count": len(plan["queries"]),
            "run_dir": str(search_dir),
            "error": "SearchPlan validation failed",
        }

    attempts = 0
    last: dict[str, Any] | None = None
    for attempts in (1, 2):
        last = run_capture(
            [
                "python3",
                str(script),
                "run",
                "--plan",
                str(plan_path),
                "--out-dir",
                str(search_dir),
                "--concurrency",
                str(args.sac_concurrency),
                "--extract",
            ],
            timeout=args.search_timeout,
        )
        write_stage_logs(branch_dir, f"search_as_code_attempt_{attempts}", last)
        if last["returncode"] == 0 and (search_dir / "coverage_summary.md").is_file():
            return {
                "status": "complete",
                "attempts": attempts,
                "query_count": len(plan["queries"]),
                "run_dir": str(search_dir),
            }
    return {
        "status": "failed_degraded",
        "attempts": attempts,
        "query_count": len(plan["queries"]),
        "run_dir": str(search_dir),
        "error": (last or {}).get("stderr", "Search-as-Code failed"),
    }


def build_lead_prompt(
    *,
    branch: str,
    branch_dir: Path,
    gauntlet_prompt: Path,
    subject: str,
    request: str,
    worker_results: list[dict[str, Any]],
    search_result: dict[str, Any],
    fintwit: bool,
) -> str:
    models = branch_models(branch)
    lane_paths = "\n".join(
        f"- {item['report']}" for item in worker_results if item.get("report")
    )
    social = (
        "Run this branch's own surface-specific FinTwit step and save fintwit_context.md. "
        "Treat it as Tier 4 only."
        if fintwit
        else "Do not run FinTwit; record that it was not requested."
    )
    return f"""# Independent Gauntlet Fast branch lead

You are the sole lead, verifier, model owner, and report writer for one isolated Gauntlet Fast
research program. You are a delegated leaf: never spawn agents or subagents. The outer Parallax
runner already completed exactly four research workers and a branch-local Search-as-Code pass.

Subject: {subject}
User request:
{request}

Branch directory (the only project directory you may read or write):
{branch_dir}

Read the complete Gauntlet master methodology from:
{gauntlet_prompt}

Execute Gauntlet FAST only:
- Execute Phases 0 through 6 and Phase 8.
- Do not execute Phase 7, external review, adjudication, round 2, or any cross-model critique.
- Preserve the Gauntlet evidence rules, source breadth accounting, locked ledger, Python models,
  Damodaran-grounded valuation, sensitivities, detailed formula-driven Excel model, and final report.
- Start FINAL_REPORT.md with the exact banner: {FAST_BANNER}
- Cap the branch's estimate confidence at LOW because this branch is not adversarially reviewed.
- Do not refer to another research branch, another model's report, comparison, merger, or consensus.
- Do not read any path outside {branch_dir}, except the read-only master methodology and installed
  tool/skill code needed to execute the stated workflow.

Worker reports to inspect and QC:
{lane_paths}

Branch-local Search-as-Code directory:
{search_result['run_dir']}
Search-as-Code status: {search_result['status']}

Retrieval order now:
1. Treat worker outputs and Search-as-Code as discovery/claims, not truth.
2. Use targeted direct Perplexity only for residual gaps and alternative query formulations.
3. Open primary documents and independently verify load-bearing claims before ledger admission.
4. Use FMP /stable/ and reconcile every material figure to filings.
5. For biomedical work, use BioMCP + PubMed/PMC first and Scite selectively for citation context,
   corrections, retractions, and editorial notices. If this runtime lacks a BioMCP connector or
   skill wrapper, use the installed `biomcp` CLI on PATH.
6. After two materially different failed probes, mark [UNKNOWN - NOT VERIFIED].

Social-sentiment instruction:
{social}

Create all of these canonical files directly under {branch_dir}:
{chr(10).join(f"- {name}" for name in REQUIRED_BRANCH_FILES)}
- {slugify(subject)}_{branch.title()}_Model.xlsx

Artifact requirements:
- 02_source_manifest.csv records discovered/deduplicated/opened/cited source identity and counts.
- 03_evidence_ledger.csv records atomic claims, classification, source/date/exact locator/excerpt,
  source tier, verification status, and consequence if wrong.
- 04 and 05 are executable Python; run them and preserve outputs/errors.
- The workbook is a valid formula-driven XLSX with assumptions, WACC, scenario, bridge, and sensitivity
  sheets as applicable. Verify its semantics independently before shipping.
- FINAL_REPORT.html is a faithful rendering of FINAL_REPORT.md.
- audit_manifest.json has status "pass" only after claim, citation, calculation, model, and report
  checks pass; otherwise write status "fail" and do not claim completion.
- run_manifest.json records model/effort, exact commands where available, tool routing, source counts,
  stage durations, fallbacks, and absolute artifact paths without secrets. Set its status to
  "complete" only after all branch artifact and audit gates pass; otherwise set it to "failed".
- VERIFICATION_LOG.md records every load-bearing recomputation, discrepancy, unresolved unknown, tool
  failure, and the literal line "adversarial review: SKIPPED (fast mode)".

Model contract recorded by the runner: {models['lead_model']} at {models['lead_effort']} effort.

Your final response must briefly state whether all required files were created and audited. The files,
not the chat response, are the deliverable.
"""


def minimal_xlsx(path: Path, branch: str) -> None:
    """Write a small but valid deterministic XLSX for orchestration dry-runs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""",
        )
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        )
        archive.writestr(
            "xl/workbook.xml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="{branch.title()} Dry Run" sheetId="1" r:id="rId1"/></sheets>
<calcPr fullCalcOnLoad="1"/></workbook>""",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""",
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Dry-run model</t></is></c>
<c r="B1"><f>1+1</f><v>2</v></c></row></sheetData></worksheet>""",
        )


def dry_branch_artifacts(
    branch: str,
    branch_dir: Path,
    subject: str,
    worker_results: list[dict[str, Any]],
    search_result: dict[str, Any],
) -> None:
    models = branch_models(branch)
    atomic_write(
        branch_dir / "01_scope_and_assumptions.md",
        f"# Dry-run scope\n\nSubject: {subject}\nBranch: {branch}\n",
    )
    atomic_write(
        branch_dir / "02_source_manifest.csv",
        "source_id,title,issuer,date,url,tier,opened,cited,tags\n"
        f"dry-{branch}-1,Dry-run source,Dry issuer,2026-01-01,https://example.invalid/{branch},1,true,true,test\n",
    )
    atomic_write(
        branch_dir / "03_evidence_ledger.csv",
        "claim_id,claim,classification,source,date,locator,excerpt,tier,status,consequence\n"
        f"C1,Dry-run claim for {subject},VERIFIED FACT,dry-{branch}-1,2026-01-01,page:1,Dry excerpt,1,verified,test only\n",
    )
    atomic_write(
        branch_dir / "04_catalyst_and_pos_model.py",
        "#!/usr/bin/env python3\nprint('dry-run catalyst model: 0.50')\n",
    )
    atomic_write(
        branch_dir / "05_valuation_model.py",
        "#!/usr/bin/env python3\nprint('dry-run valuation model: 2.0')\n",
    )
    atomic_write(
        branch_dir / "06_model_outputs.csv",
        "metric,value,unit\ncatalyst_probability,0.50,probability\nvalue,2.0,dry_units\n",
    )
    atomic_write(
        branch_dir / "07_working_research.md",
        f"# Dry-run working research\n\n{branch} branch for {subject}.\n",
    )
    atomic_write(
        branch_dir / "08_preliminary_report.md",
        f"# Dry-run preliminary report\n\nIndependent {branch} draft for {subject}.\n",
    )
    final_md = (
        f"> **{FAST_BANNER}**\n\n"
        f"# {subject} — {branch.title()} Independent Research\n\n"
        "This is deterministic dry-run content. It is not investment research.\n\n"
        "**Estimate confidence: LOW.**\n\n"
        "## Executive Summary\n\n"
        "Dry-run summary used only to exercise the orchestration and package gates.\n\n"
        "## Evidence and Method\n\n"
        "The test fixture records a primary-source row, a claim-ledger row, executable model files, "
        "a model-output table, and a valid workbook container.\n\n"
        "## Independent Valuation\n\n"
        "The dry-run valuation is a deterministic placeholder and carries no investment meaning.\n\n"
        "## Risks and Falsifiers\n\n"
        "The dry-run package must never be treated as live research.\n\n"
        "## Source Coverage and Data Cutoff\n\n"
        "One deterministic fixture source; cutoff 2026-01-01.\n"
    )
    while len(final_md.encode("utf-8")) < 3400:
        final_md += (
            "\nDry-run report padding validates the real report-size gate without introducing "
            "research claims.\n"
        )
    atomic_write(branch_dir / "FINAL_REPORT.md", final_md)
    atomic_write(
        branch_dir / "FINAL_REPORT.html",
        "<!doctype html><html><head><meta charset=\"utf-8\"><title>"
        + html.escape(f"{subject} — {branch.title()} Independent Research")
        + "</title></head><body><pre>"
        + html.escape(final_md)
        + "</pre></body></html>\n",
    )
    atomic_write(
        branch_dir / "VERIFICATION_LOG.md",
        "# Verification Log\n\n"
        "adversarial review: SKIPPED (fast mode)\n\n"
        "Dry-run orchestration and artifact checks passed.\n",
    )
    atomic_write(
        branch_dir / "sources.jsonl",
        json.dumps(
            {
                "source_id": f"dry-{branch}-1",
                "title": "Dry-run source",
                "source_tier": 1,
            }
        )
        + "\n",
    )
    atomic_write(
        branch_dir / "evidence.jsonl",
        json.dumps(
            {
                "claim_id": "C1",
                "source_id": f"dry-{branch}-1",
                "quote": "Dry excerpt",
                "locator": "page:1",
                "verification_status": "verified",
            }
        )
        + "\n",
    )
    write_json(
        branch_dir / "audit_manifest.json",
        {
            "status": "pass",
            "dry_run": True,
            "claim_gate": "pass",
            "calculation_gate": "pass",
            "report_gate": "pass",
        },
    )
    write_json(
        branch_dir / "run_manifest.json",
        {
            "workflow": "gauntlet_fast_branch",
            "branch": branch,
            "status": "complete",
            "dry_run": True,
            "models": models,
            "workers": worker_results,
            "search_as_code": search_result,
            "created_at": utc_now(),
        },
    )
    minimal_xlsx(branch_dir / f"{slugify(subject)}_{branch.title()}_Model.xlsx", branch)


def validate_branch_package(branch_dir: Path, min_report_bytes: int) -> tuple[bool, list[str]]:
    errors: list[str] = []
    for path in branch_dir.rglob("*"):
        relative_name = str(path.relative_to(branch_dir)).lower()
        for token in FORBIDDEN_ARTIFACT_TOKENS:
            if token in relative_name:
                errors.append(f"forbidden merger artifact path: {relative_name}")

    for name in REQUIRED_BRANCH_FILES:
        path = branch_dir / name
        if not path.is_file():
            errors.append(f"missing {name}")
        elif path.stat().st_size == 0:
            errors.append(f"empty {name}")

    report = branch_dir / "FINAL_REPORT.md"
    if report.is_file():
        text = read_text(report)
        if FAST_BANNER not in text:
            errors.append("FINAL_REPORT.md missing fast-mode banner")
        if "confidence" not in text.lower() or not re.search(r"\bLOW\b", text):
            errors.append("FINAL_REPORT.md missing LOW confidence disclosure")
        lowered = text.lower()
        for phrase in FORBIDDEN_REPORT_PHRASES:
            if phrase in lowered:
                errors.append(f"FINAL_REPORT.md contains forbidden comparison phrase: {phrase}")
        if len(text.encode("utf-8")) < min_report_bytes:
            errors.append(
                f"FINAL_REPORT.md too small: {len(text.encode('utf-8'))} < {min_report_bytes}"
            )

    html_report = branch_dir / "FINAL_REPORT.html"
    if html_report.is_file():
        html_text = read_text(html_report)
        if FAST_BANNER not in html_text:
            errors.append("FINAL_REPORT.html missing fast-mode banner")
        html_lowered = html_text.lower()
        for phrase in FORBIDDEN_REPORT_PHRASES:
            if phrase in html_lowered:
                errors.append(
                    f"FINAL_REPORT.html contains forbidden comparison phrase: {phrase}"
                )
        if len(html_text.encode("utf-8")) < min_report_bytes:
            errors.append(
                f"FINAL_REPORT.html too small: "
                f"{len(html_text.encode('utf-8'))} < {min_report_bytes}"
            )

    audit = branch_dir / "audit_manifest.json"
    if audit.is_file():
        try:
            if json.loads(read_text(audit)).get("status") != "pass":
                errors.append("audit_manifest.json status is not pass")
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"invalid audit_manifest.json: {exc}")

    branch_manifest = branch_dir / "run_manifest.json"
    if branch_manifest.is_file():
        try:
            if json.loads(read_text(branch_manifest)).get("status") != "complete":
                errors.append("run_manifest.json status is not complete")
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"invalid run_manifest.json: {exc}")

    verification_log = branch_dir / "VERIFICATION_LOG.md"
    if verification_log.is_file() and (
        "adversarial review: SKIPPED (fast mode)" not in read_text(verification_log)
    ):
        errors.append("VERIFICATION_LOG.md missing fast-mode review disclosure")

    workbooks = list(branch_dir.glob("*_Model.xlsx"))
    if len(workbooks) != 1:
        errors.append(f"expected exactly one *_Model.xlsx, found {len(workbooks)}")
    elif not zipfile.is_zipfile(workbooks[0]):
        errors.append(f"invalid XLSX zip container: {workbooks[0].name}")

    lane_reports = list((branch_dir / "lanes").glob("lane_*/report.md"))
    if len(lane_reports) != 4:
        errors.append(f"expected four lane reports, found {len(lane_reports)}")

    search_dir = branch_dir / "search_as_code"
    for name in ("search_plan.json", "coverage_summary.md", "sources.jsonl", "evidence.jsonl"):
        if not (search_dir / name).is_file():
            errors.append(f"missing search_as_code/{name}")
    return not errors, errors


def validate_project_topology(project_dir: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []
    directories = sorted(path.name for path in project_dir.iterdir() if path.is_dir())
    expected = sorted(BRANCH_DIRECTORY.values())
    if directories != expected:
        errors.append(f"expected project directories {expected}, found {directories}")
    for path in project_dir.rglob("*"):
        relative_name = str(path.relative_to(project_dir)).lower()
        for token in FORBIDDEN_ARTIFACT_TOKENS:
            if token in relative_name:
                errors.append(f"forbidden merger artifact path: {relative_name}")
    return not errors, errors


def execute_lead(
    *,
    branch: str,
    branch_dir: Path,
    subject: str,
    request: str,
    worker_results: list[dict[str, Any]],
    search_result: dict[str, Any],
    gauntlet_prompt: Path,
    args: argparse.Namespace,
) -> dict[str, Any]:
    prompt = build_lead_prompt(
        branch=branch,
        branch_dir=branch_dir,
        gauntlet_prompt=gauntlet_prompt,
        subject=subject,
        request=request,
        worker_results=worker_results,
        search_result=search_result,
        fintwit=args.fintwit,
    )
    atomic_write(branch_dir / "prompts" / "lead_prompt.md", prompt)

    if args.dry_run:
        dry_branch_artifacts(branch, branch_dir, subject, worker_results, search_result)
        result = {
            "status": "ok",
            "returncode": 0,
            "seconds": 0.001,
            "stdout": "Dry-run branch artifacts created and audited.",
            "raw_stdout": "",
            "stderr": "",
            "argv": ["<dry-run>"],
        }
    else:
        models = branch_models(branch)
        if branch == "claude":
            argv = build_claude_argv(
                models["lead_model"], models["lead_effort"], branch_dir
            )
            result = run_capture(
                argv,
                stdin_text=prompt,
                timeout=args.lead_timeout,
                codex_json=False,
                cwd=branch_dir,
            )
        else:
            argv = build_codex_argv(
                models["lead_model"], models["lead_effort"], branch_dir
            )
            result = run_capture(
                argv, stdin_text=prompt, timeout=args.lead_timeout, codex_json=True
            )
    write_stage_logs(branch_dir, "lead", result)
    valid, errors = validate_branch_package(branch_dir, args.min_report_bytes)
    return {
        "status": "complete" if result["returncode"] == 0 and valid else "failed",
        "returncode": result["returncode"],
        "seconds": result["seconds"],
        "validation_errors": errors,
        "final_report_md": (
            str(branch_dir / "FINAL_REPORT.md")
            if (branch_dir / "FINAL_REPORT.md").is_file()
            else None
        ),
        "final_report_html": (
            str(branch_dir / "FINAL_REPORT.html")
            if (branch_dir / "FINAL_REPORT.html").is_file()
            else None
        ),
    }


def run_branch(
    *,
    branch: str,
    branch_dir: Path,
    subject: str,
    request: str,
    gauntlet_prompt: Path,
    args: argparse.Namespace,
) -> dict[str, Any]:
    started = time.monotonic()
    workers = run_workers(
        branch=branch,
        branch_dir=branch_dir,
        subject=subject,
        request=request,
        args=args,
    )
    if any(worker["status"] != "complete" for worker in workers):
        result = {
            "status": "failed",
            "reason": "one or more of exactly four workers failed after retry",
            "workers": workers,
            "search_as_code": {"status": "not_run"},
            "lead": {"status": "not_run"},
            "models": branch_models(branch),
            "seconds": round(time.monotonic() - started, 3),
        }
        write_json(branch_dir / "PARALLAX_BRANCH_MANIFEST.json", result)
        return result

    search = run_search_as_code(
        branch=branch,
        branch_dir=branch_dir,
        subject=subject,
        request=request,
        args=args,
    )
    if search["status"] != "complete":
        result = {
            "status": "failed",
            "reason": "branch-local Search-as-Code failed after allowed attempts",
            "workers": workers,
            "search_as_code": search,
            "lead": {"status": "not_run"},
            "models": branch_models(branch),
            "seconds": round(time.monotonic() - started, 3),
        }
        write_json(branch_dir / "PARALLAX_BRANCH_MANIFEST.json", result)
        return result

    lead = execute_lead(
        branch=branch,
        branch_dir=branch_dir,
        subject=subject,
        request=request,
        worker_results=workers,
        search_result=search,
        gauntlet_prompt=gauntlet_prompt,
        args=args,
    )
    result = {
        "status": "complete" if lead["status"] == "complete" else "failed",
        "reason": None if lead["status"] == "complete" else "lead or package validation failed",
        "workers": workers,
        "search_as_code": search,
        "lead": lead,
        "models": branch_models(branch),
        "seconds": round(time.monotonic() - started, 3),
    }
    write_json(branch_dir / "PARALLAX_BRANCH_MANIFEST.json", result)
    return result


def preflight(args: argparse.Namespace) -> tuple[bool, list[str], Path | None]:
    errors: list[str] = []
    gauntlet_prompt: Path | None = None
    try:
        gauntlet_prompt = resolve_gauntlet_prompt()
    except FileNotFoundError as exc:
        errors.append(str(exc))
    if not args.dry_run:
        for executable in ("claude", "codex"):
            if shutil.which(executable) is None:
                errors.append(f"missing executable on PATH: {executable}")
        for branch, path in SEARCH_AS_CODE_SCRIPTS.items():
            if not path.is_file():
                errors.append(f"missing {branch} Search-as-Code script: {path}")
    return not errors, errors, gauntlet_prompt


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run independent Claude and Codex Gauntlet Fast research programs in parallel; "
            "publish two reports and no merged verdict."
        )
    )
    parser.add_argument("subject", metavar="TICKER_OR_TOPIC")
    parser.add_argument("--query-file", type=Path)
    parser.add_argument("--project-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fintwit", action="store_true")
    parser.add_argument("--worker-timeout", type=int, default=1800)
    parser.add_argument("--retry-timeout", type=int, default=1200)
    parser.add_argument("--search-timeout", type=int, default=1800)
    parser.add_argument("--lead-timeout", type=int, default=5400)
    parser.add_argument("--sac-concurrency", type=int, default=10)
    parser.add_argument("--min-worker-bytes", type=int, default=1500)
    parser.add_argument("--min-report-bytes", type=int, default=3000)
    return parser.parse_args(argv)


def build_request(subject: str, query_file: Path | None) -> str:
    request = f"Research {subject} using two independent Gauntlet Fast programs."
    if query_file is None:
        return request
    path = query_file.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"query file not found: {path}")
    return request + "\n\nCustom user questions:\n" + read_text(path)


def validate_positive_args(args: argparse.Namespace) -> None:
    for name in (
        "worker_timeout",
        "retry_timeout",
        "search_timeout",
        "lead_timeout",
        "sac_concurrency",
        "min_worker_bytes",
        "min_report_bytes",
    ):
        if getattr(args, name) <= 0:
            raise ValueError(f"--{name.replace('_', '-')} must be positive")


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    subject = args.subject.strip()
    if not subject:
        print("parallax: subject cannot be empty", file=sys.stderr)
        return 5
    try:
        validate_positive_args(args)
        request = build_request(subject, args.query_file)
        ok, preflight_errors, gauntlet_prompt = preflight(args)
        if not ok or gauntlet_prompt is None:
            for error in preflight_errors:
                print(f"parallax preflight: {error}", file=sys.stderr)
            return 5
        project_dir = resolve_project_dir(subject, args.project_dir)
        branches = ensure_project_layout(project_dir)
    except (FileNotFoundError, FileExistsError, OSError, ValueError) as exc:
        print(f"parallax: {exc}", file=sys.stderr)
        return 5

    atomic_write(project_dir / "REQUEST.md", request + "\n")
    root_manifest: dict[str, Any] = {
        "workflow": "parallax",
        "topology": "dual_gauntlet_fast_no_merge",
        "subject": subject,
        "request_file": str(project_dir / "REQUEST.md"),
        "project_dir": str(project_dir),
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "status": "running",
        "dry_run": args.dry_run,
        "fintwit": args.fintwit,
        "gauntlet_master_prompt": str(gauntlet_prompt),
        "branches": {},
        "no_merge_contract": True,
    }
    write_json(project_dir / "RUN_MANIFEST.json", root_manifest)

    results: dict[str, dict[str, Any]] = {}
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(
                run_branch,
                branch=branch,
                branch_dir=branch_dir,
                subject=subject,
                request=request,
                gauntlet_prompt=gauntlet_prompt,
                args=args,
            ): branch
            for branch, branch_dir in branches.items()
        }
        for future in as_completed(futures):
            branch = futures[future]
            try:
                results[branch] = future.result()
            except Exception as exc:
                results[branch] = {
                    "status": "failed",
                    "reason": f"unexpected branch exception: {type(exc).__name__}: {exc}",
                    "workers": [],
                    "search_as_code": {"status": "not_run"},
                    "lead": {"status": "not_run"},
                    "models": branch_models(branch),
                }

    topology_ok, topology_errors = validate_project_topology(project_dir)
    claude_ok = results.get("claude", {}).get("status") == "complete"
    codex_ok = results.get("codex", {}).get("status") == "complete"
    if not topology_ok:
        status = "failed_topology"
        exit_code = 2
    elif claude_ok and codex_ok:
        status = "complete_both"
        exit_code = 0
    elif claude_ok:
        status = "partial_claude"
        exit_code = 4
    elif codex_ok:
        status = "partial_codex"
        exit_code = 4
    else:
        status = "failed_both"
        exit_code = 2

    root_manifest.update(
        {
            "updated_at": utc_now(),
            "status": status,
            "seconds": round(time.monotonic() - started, 3),
            "branches": {branch: results[branch] for branch in sorted(results)},
            "topology_gate": {
                "status": "pass" if topology_ok else "fail",
                "errors": topology_errors,
            },
        }
    )
    write_json(project_dir / "RUN_MANIFEST.json", root_manifest)

    print("=" * 72)
    print(f"Parallax dual Gauntlet Fast run: {status}")
    print(f"Project: {project_dir}")
    for branch in ("claude", "codex"):
        result = results.get(branch, {})
        report = result.get("lead", {}).get("final_report_html")
        print(f"{branch}: {result.get('status', 'missing')}")
        if report:
            print(f"  report: {report}")
        elif result.get("reason"):
            print(f"  reason: {result['reason']}")
    print(f"Manifest: {project_dir / 'RUN_MANIFEST.json'}")
    print("No merged verdict was produced.")
    return exit_code


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except KeyboardInterrupt:
        print("parallax: interrupted", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"parallax: unexpected internal error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(5)
