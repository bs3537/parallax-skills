---
name: parallax
description: >-
  Explicit-invocation-only dual Gauntlet Fast research workflow that runs one independent Claude Code
  WSL program and one independent Codex CLI WSL program concurrently, saves complete research packages
  in separate Claude and Codex subfolders under one project directory, and produces no merged verdict
  or model preference. Use only when the user affirmatively asks to use or run Parallax, Parallex, or
  parallel Gauntlet Fast research. Never auto-trigger from a ticker, stock, biotech, valuation,
  research-depth request, multi-model wording, or inferred usefulness.
---

# Parallax

Run two independent Gauntlet Fast research programs concurrently and give the user both reports to
compare. Never merge, rank, average, reconcile, adjudicate, or select between them.

## Invocation gate

Run only when the active user request affirmatively names `Parallax`, `Parallex`, or explicitly asks
for parallel Gauntlet Fast research. Negated, quoted, historical, and comparative references do not
authorize execution.

## Required topology

```text
Claude branch                             Codex branch
Opus 5 high lead                         GPT-5.6 Sol high lead
  └─ four Sonnet 5 xhigh workers           └─ four GPT-5.6 Sol high workers
  └─ Claude Search-as-Code                  └─ Codex Search-as-Code
  └─ Claude tools and evidence              └─ Codex tools and evidence
  └─ FINAL_REPORT.md/.html/.xlsx            └─ FINAL_REPORT.md/.html/.xlsx
```

The runner launches both branch controllers concurrently. Each controller launches exactly four
non-overlapping leaf workers, runs its own Search-as-Code second pass, and then launches its own lead.
A delegated `claude -p` or `codex exec` process never spawns subagents.

Read [branch_contract.md](references/branch_contract.md) before changing prompts, artifacts, routing,
or validation.

## Launch

From Claude Code WSL:

```bash
python3 ~/.claude/skills/parallax/scripts/run_parallax.py TICKER
```

From Codex CLI WSL:

```bash
python3 ~/.codex/skills/parallax/scripts/run_parallax.py TICKER
```

Append custom questions to both independent branches:

```bash
python3 <skill-dir>/scripts/run_parallax.py TICKER --query-file /absolute/path/questions.md
```

Choose the shared project folder:

```bash
python3 <skill-dir>/scripts/run_parallax.py TICKER \
  --project-dir ~/Documents/TICKER_Parallax_YYYYMMDD
```

The requested project directory must be absent or empty. The default is
`~/Documents/<SUBJECT>_Parallax_<YYYYMMDD>/`; if that path already exists, the runner adds a UTC time
suffix rather than overwriting it.

## Isolation contract

- Create exactly two research subfolders at the project root: `claude_research/` and
  `codex_research/`.
- Allow both branches to read the shared `REQUEST.md` only through the request text injected by the
  runner.
- Never disclose either branch path, prompts, worker reports, sources, evidence, calculations,
  recommendation, or artifacts to the other branch.
- Run separate Search-as-Code plans and persist separate ledgers.
- Do not create a merger prompt, merged verdict, combined claim matrix, consensus target, preferred
  report, or reader-facing combined answer.
- Do not reuse one branch's failure recovery, evidence, or output in the other branch.

## Research contract

Both branches execute the installed Gauntlet master research methodology in Fast mode:

1. Execute Gauntlet Phases 0 through 6 and Phase 8.
2. Skip Phase 7, external adversarial review, adjudication, round 2, and cross-model critique.
3. Preserve the locked evidence ledger, source accounting, executable catalyst and valuation models,
   calculation verification, detailed Excel workbook, sensitivities, and final-report gate.
4. Put the exact banner `FAST MODE — single-model draft, NOT adversarially reviewed` at the top of
   each `FINAL_REPORT.md`.
5. Cap each branch's estimate confidence at LOW.
6. Record `adversarial review: SKIPPED (fast mode)` in each `VERIFICATION_LOG.md`.

The runner resolves the Gauntlet master prompt from
`~/.claude/skills/gauntlet/references/master_research_prompt.md`, falling back to
`~/gauntlet/references/master_research_prompt.md`. Set `PARALLAX_GAUNTLET_PROMPT` to an explicit
read-only path when needed. Fail preflight if no prompt exists.

## Tool routing

Each branch uses its own runtime and transport:

1. Four workers perform native-web-first discovery and primary-document inspection in non-overlapping
   evidence lanes.
2. The runner executes that surface's installed Search-as-Code `sac_search.py` with an UltraDeep
   24-query plan and imports the branch-local results as discovery.
3. The branch lead uses direct Perplexity only for residual gaps and alternate query formulations.
4. The lead opens and verifies every load-bearing primary document before ledger admission.
5. Use FMP `/stable/` for structured data and reconcile material figures to filings.
6. For biomedical work use BioMCP plus PubMed/PMC first, Semantic Scholar when available, and Scite
   selectively for citation context and editorial notices. Claude may use the installed `biomcp`
   CLI when no BioMCP connector or skill wrapper is exposed.
7. Use the installed valuation engine when valuation is required; preserve Python inputs and outputs.
8. After two materially different failed probes, mark `[UNKNOWN - NOT VERIFIED]`.

FinTwit is off by default. Pass `--fintwit` only when requested; each branch then runs its own
surface-specific Tier-4 pass. Never share one sidecar between branches.

## Output layout

```text
~/Documents/<PROJECT>_Parallax_<YYYYMMDD>/
├── REQUEST.md
├── RUN_MANIFEST.json
├── claude_research/
│   ├── lanes/lane_1_... through lane_4_...
│   ├── search_as_code/
│   ├── 01_scope_and_assumptions.md through 08_preliminary_report.md
│   ├── sources.jsonl
│   ├── evidence.jsonl
│   ├── FINAL_REPORT.md
│   ├── FINAL_REPORT.html
│   ├── <PROJECT>_Claude_Model.xlsx
│   ├── VERIFICATION_LOG.md
│   ├── audit_manifest.json
│   ├── run_manifest.json
│   └── PARALLAX_BRANCH_MANIFEST.json
└── codex_research/
    └── the same independent package
```

The project root contains no third research directory and no combined research artifact.

## QC gate

Before reporting success:

1. Require process exit `0`.
2. Open `RUN_MANIFEST.json`; require `topology: dual_gauntlet_fast_no_merge` and
   `status: complete_both`.
3. Require exactly four complete workers under each branch.
4. Require each branch's Search-as-Code status to be `complete`, then open its coverage summary.
5. Open each `audit_manifest.json`; require `status: pass`.
6. Open each `FINAL_REPORT.md`; require the exact Fast-mode banner and substantive content.
7. Verify each HTML exists and faithfully represents its Markdown.
8. Verify each workbook is a valid XLSX and its formulas/model semantics were independently checked.
9. Search the project tree for forbidden merger artifacts before delivery.

Exit `4` means one complete branch and one failed branch. Surface the successful report and the failed
branch diagnostics, but call the overall run partial. Exit `2` means both branches failed. Exit `5`
means preflight, arguments, environment, or an unexpected internal error.

## Presenting

Give two equally prominent links in this order:

1. Claude independent report: `<project>/claude_research/FINAL_REPORT.html`
2. Codex independent report: `<project>/codex_research/FINAL_REPORT.html`

Also link both workbooks and the root `RUN_MANIFEST.json`. State that no merged verdict was produced
and the user should compare the reports independently. Do not summarize one as better.

## Fixed model contract

| Role | Model | Effort |
| --- | --- | --- |
| Claude lead | `claude-opus-5` | `high` |
| Four Claude workers | `claude-sonnet-5` | `xhigh` |
| Codex lead | `gpt-5.6-sol` | `high` |
| Four Codex workers | `gpt-5.6-sol` | `high` |

The runner does not accept environment overrides for these values. A missing or rejected model fails
that branch and is disclosed; it never silently substitutes another model.

`PARALLAX_GAUNTLET_PROMPT` may override only the read-only Gauntlet master-prompt path.

CLI timeout, Search-as-Code concurrency, minimum-size, dry-run, and FinTwit flags are documented by
`python3 <skill-dir>/scripts/run_parallax.py --help`.
