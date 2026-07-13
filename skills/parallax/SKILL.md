---
name: parallax
description: >-
  Explicit-invocation-only two-model parallel screener research with tool-grounded cross-verification
  merge (parallax). Use only when the user affirmatively asks to use or run parallax. Never auto-trigger
  from a ticker, stock/equity/biotech, valuation, catalyst, earnings, screener, portfolio, or
  public-market question, a speed request, or inferred usefulness.
---

# Parallax

## Concept: depth from disagreement

Two strong models research the same stock independently, with their full tool suites, and never see
each other's work. A third pass then diffs the two reports and re-verifies — with live tools — every
figure the reports disagree on, resolving each against a primary source rather than re-querying the same
endpoint both lanes already used. Where the two lanes agree, the figure is recorded as CONCORDANT
(consistency, not truth) and left un-re-verified — with one exception: any load-bearing figure both
lanes drew from a single shared source (e.g. FMP) is spot-checked against the primary filing, because
that is exactly where a shared-source error hides behind false agreement. The disagreements a naive
single-model pass would never surface are exactly where the verification budget goes. The two reports are
handed to the merger **blind** — neutral "Report A"/"Report B" labels, no model names, order randomized
per run — so the GPT-based merger cannot give same-family deference to the GPT-authored lane; the true
Report→model mapping is recorded in the manifest (`stages.merge.blind_map`) for audit. This is Tier 1 of
a two-tier pipeline:
fast, daily-use screener depth. Tier 2 (model-fusion / hybrid-model-fusion / valuation) is the slower,
heavier escalation path for names that clear this first screen — see "Escalation" below.

A deterministic post-process (no extra model call) then strips the merged verdict down to one clean
Final Answer — no claim-verification tables, no correction notes, no scaffolding — while the full
verified verdict stays on disk, unabridged, for audit. See "Final Answer & Publish Layout" below.

## Invocation Gate

This skill is opt-in only. Run it only when the active user request affirmatively names `parallax` or
explicitly asks to use/run Parallax. An ordinary ticker, stock/equity/biotech, valuation, catalyst,
earnings, screener, portfolio, or public-market question is not authorization by itself. A speed
request ("fast", "quick") alone is not authorization either. Negated, quoted, historical, and
comparative references do not count.

## Architecture

```text
                         ┌─────────────────────────┐
                         │   Orchestrator (this     │
                         │   CLI) — control plane   │
                         │   only. See "Contract".  │
                         └────────────┬─────────────┘
                                      │
                     ┌────────────────┴────────────────┐
                     │  FinTwit sidecar (opt-in, Tier-4)│
                     │  fintwit_engine.py --ticker ...  │
                     └────────────────┬──────────────────┘
                                      │ injected into both lanes + merge (only when --fintwit is passed)
              ┌───────────────────────┼───────────────────────┐
              ▼                                                ▼
   ┌────────────────────────┐                     ┌────────────────────────┐
   │  Lane: Claude Opus 4.8 │                      │  Lane: GPT-5.6 Sol      │
   │  (high) — full tool    │                      │  via Codex (high) —     │
   │  suite, independent    │                      │  full tool suite,       │
   │  research pass         │                      │  independent research   │
   └────────────┬────────────┘                     └────────────┬────────────┘
                │  lane_claude.md                                │  lane_codex.md
                └───────────────────────┬────────────────────────┘
                                         ▼
                     ┌──────────────────────────────────────┐
                     │  Merger: GPT-5.6 Sol via Codex (high) │
                     │  — LIVE TOOLS ENABLED (not a judge    │
                     │  with tools disabled). Diffs both     │
                     │  reports. Verifies disagreements;     │
                     │  spot-checks load-bearing agreed      │
                     │  figures vs filings; else CONCORDANT  │
                     └──────────────────┬─────────────────────┘
                                         ▼
              PUBLISH: numbered answers at the stock-folder root
        1_opus48_report.{md,html}  2_gpt56sol_report.{md,html}
                    3_merged_verdict.{md,html}
                                 │
                                 ▼
        STRIP (deterministic post-process, NO extra model call): drop
        verification scaffolding, keep the thesis, roll every open item
        into one closing section  ->  final/<n>_SLUG_final_answer.html
              (HTML only — the copy-ready reader-facing entry point)
        + machine artifacts under <stock folder>/runs/<UTC ts>/
```

## How to Launch

One bash call; background-friendly (the run can take several minutes — launch it and poll, or run it in
the background and wait for the notification):

```bash
python3 ~/.codex/skills/parallax/scripts/run_parallax.py TICKER 2>&1 | tee /tmp/parallax_run.log
```

(There is no `--print` flag — terminal echo is unconditional, not opt-in: the runner always prints a
summary block, the full merged verdict, and an `ANSWER LINKS` block to stdout on success; `tee` above is
optional, just a convenience for background launches.)

Published answers land at `~/Parallax_Projects/<SLUG>/` by default (`--run-base` overrides the master
folder; `SLUG` is the uppercase ticker, e.g. `NVDA`, or a topic slug for free-form subjects). Read
`<SLUG>/final/<n>_<SLUG>_final_answer.html` first — it is the one clean answer with no verification
scaffolding; the numbered root files (lane reports + merged verdict) are the full audit trail behind it.
See "Final Answer & Publish Layout" below.

For a free-form topic instead of a single ticker:

```bash
python3 ~/.codex/skills/parallax/scripts/run_parallax.py "AI datacenter cooling thematic screen"
```

With a custom question file appended to both lanes' briefs:

```bash
python3 ~/.codex/skills/parallax/scripts/run_parallax.py TICKER --query-file /path/to/questions.md
```

With the FinTwit / X social-sentiment sidecar (Tier-4), which is **OFF by default** — add `--fintwit`
**only when the user explicitly asks for social/X sentiment**, never by default:

```bash
python3 ~/.codex/skills/parallax/scripts/run_parallax.py TICKER --fintwit
```

## Orchestrating-CLI Contract

The orchestrating CLI (this Claude Code / Codex / Gemini session) is a **control plane only**: it
dispatches the run, waits for it to finish, QC's the artifacts, and surfaces the result. It does **not**
run its own research pass, does not pre-answer the question, does not supply evidence to any lane or to
the merger, and does not synthesize a second opinion on top of `merge.md`. All research and verification
happens inside the three model invocations the runner dispatches (two lanes + one merger); the
orchestrating CLI's job is dispatch, wait, QC, surface — nothing else. (Same control-plane framing as
`stock-fusion-fast/references/runner_contract.md`.)

## QC Gate (mandatory before relaying a result)

Before presenting a Parallax result as done, the orchestrating CLI must check ALL of:

1. **Exit code** — `0` is the only unqualified success code; `4` still publishes (see below) but is a
   failure the user must be told about. Any other nonzero exit means nothing was published; read the
   stderr diagnostic the runner printed (it names what exists and where) before doing anything else.
2. **`manifest.json` status** — open the `manifest.json` under `<stock folder>/runs/<UTC ts>/` (the path
   is printed in the run summary and in `manifest["run_dir"]`) and confirm `"status"` is `"complete"` or
   `"complete_single_lane"`. Do not infer success from exit code alone; the two are written
   independently and both must agree. `manifest["published"]` lists every numbered answer actually
   written, each with its own `md_path`/`html_path`/`html_status` — treat this list, not a guess at
   filenames, as the source of truth for what exists.
3. **The highest-numbered `*_merged_verdict.md` starts with real content** — open it and confirm it is
   not the failure-disclosure stub (`# Parallax Merge — FAILED`) and, for single-lane runs, that the
   single-lane disclosure line is present as literally the first line and was expected.
4. **`manifest["final_answer"]["published"]` matches expectations** — `true` with an `html_status` of
   `"ok"` on a normal success; `false` with `html_status: "skipped: merge failed"` on exit `4` (no final
   answer is ever produced when the merge itself failed — nothing was verified to read); `false` with a
   different `html_status` string only in the rare case the merge succeeded but the Final Answer's own
   HTML render failed (still surfaced, never silently dropped — see "Final Answer & Publish Layout").

**Hard rule:** whenever a run publishes anything (exit `0`, or exit `4` where at least one lane
survived — DELTA 1 always publishes the FAILED-disclosure merge file too, so its links stay valid), the
orchestrating CLI MUST relay the `ANSWER LINKS` block from stdout to the user **verbatim**, at the end of
its own reply, unmodified — do not paraphrase it, drop entries from it, or summarize it away. This is the
mechanism by which the user actually finds the published answers; skipping it defeats the point of
publishing them at fixed, numbered, re-runnable locations.

On any failure that published nothing (exit `2`, `3`, `5`), surface the lane files under
`<stock folder>/runs/<UTC ts>/` (e.g. `lane_claude.md` / `lane_codex.md`) and the stderr diagnostic to
the user instead — never silently retry, never silently proceed with a partial or fabricated result, and
never present a merged verdict as verified unless all three checks above passed.

## Environment Variables

| Variable | Default | Meaning |
| --- | --- | --- |
| `PARALLAX_CLAUDE_MODEL` | `claude-opus-4-8` | Claude lane model |
| `PARALLAX_CLAUDE_EFFORT` | `high` | Claude lane effort |
| `PARALLAX_CODEX_MODEL` | `gpt-5.6-sol` | Codex lane model |
| `PARALLAX_CODEX_EFFORT` | `high` | Codex lane effort |
| `PARALLAX_MERGE_MODEL` | `gpt-5.6-sol` | Merger model (tools enabled) |
| `PARALLAX_MERGE_EFFORT` | `high` | Merger effort |
| `PARALLAX_LANE_TIMEOUT` | `900` | Seconds, first attempt per lane |
| `PARALLAX_RETRY_TIMEOUT` | `600` | Seconds, single retry per failed lane |
| `PARALLAX_MERGE_TIMEOUT` | `1200` | Seconds, per merge attempt (1 retry uses the same budget) |
| `PARALLAX_MIN_BYTES` | `2500` | Minimum valid lane report size |
| `PARALLAX_DRY_RUN_FAIL` | unset | Test-only: `claude`\|`codex`\|`merge` — force that component to fail in `--dry-run` |

All are also settable as CLI flags (`--lane-timeout`, `--claude-model`, etc.); the flag wins over the
env var, which wins over the hardcoded default.

**Effort rationale:** lanes run at `high` — they are parallel breadth-research passes, and the merger
re-verifies their disagreements downstream regardless, so lane effort doesn't need to be maximal. The
merger also runs at `high` (DELTA 3, 2026-07-13, down from `xhigh`): its verification is now scoped — the
disagreement set plus a primary-filing spot-check of load-bearing shared-source figures, rather than
re-verifying every agreement — so the largest, hardest slice of merge work is gone and `xhigh`'s extra
depth is no longer warranted. Lane quality is now load-bearing for merge speed: cleaner lanes produce a
smaller, truer disagreement set, so lane effort stays at `high` rather than dropping.
`PARALLAX_MERGE_TIMEOUT` stays at 1200s as a generous kill-switch floor — not a target; the scoped merge
finishes well under it.

## Exit Codes

| Code | Publishes? | Meaning |
| --- | --- | --- |
| `0` | Yes | Success — the numbered merged verdict is a verified verdict (dual-lane or, if `--allow-single`, single-lane adversarial). `ANSWER LINKS` printed; relay it. |
| `2` | No | Both lanes failed validation, even after one retry each. Nothing to merge, nothing published. |
| `3` | No | One lane failed validation after retry and `--allow-single` was not passed. Nothing published (the raw surviving lane is on disk under `runs/<ts>/` for inspection, but it is not promoted to a numbered answer). |
| `4` | Yes | Merge failed validation after one retry. The lane answer(s) that survived AND an explicit FAILED-disclosure file are still published as the next numbered answers so any shared link stays valid (never a silent salvage — the file says plainly that no verified synthesis exists). **No Final Answer is produced** — nothing was verified to read, so `final/` gets no new entry, and `ANSWER LINKS` leads with a one-line "not produced (merge failed)" note instead of a first link. `ANSWER LINKS` still printed; relay it, but tell the user this run did not succeed. |
| `5` | No | Bad arguments or environment, **or an unexpected internal error.** Covers: empty subject, missing `--query-file`, unwritable `--run-base` or stock folder, non-positive timeout/byte/day value, a malformed int-typed environment variable (e.g. `PARALLAX_LANE_TIMEOUT=900s` — reported with a one-line diagnostic naming the variable, checked before argparse/`--help` even runs, never a bare traceback), and — as a last-resort catch-all around the whole `__main__` entry point — any other unhandled exception, reported as `parallax: unexpected internal error: <type>: <message>`. |

## Escalation — Tier 2

Parallax is Tier 1: fast, two-model, daily-screener depth. For names that clear this screen and warrant
heavier diligence, escalate explicitly to Tier 2 — all opt-in-only, none auto-triggered by this skill or
by a ticker:

- `model-fusion` / `hybrid-model-fusion` — three-model panel-to-judge or blind-peer-review workflows.
- `valuation` — Damodaran-grounded DCF/FCFE/DDM/APV, rNPV/SOTP, comps, WACC.

Parallax never invokes Tier 2 itself; it only exists as a documented next step for the user to
explicitly request.

## Latency & Cost

- Lanes: roughly 4-10 minutes each, running in parallel (observed-analog to `stock-fusion-fast` and
  `hybrid-model-fusion` panelist lanes at comparable effort, adjusted upward for full tool suites; there
  is no longer a fixed word target — report length follows coverage, not a count). Default
  `--lane-timeout 900` (15 min) sits above this range; raise it for unusually deep or contested names
  rather than lowering it — the timeout is a hard external kill-switch, not a model-visible budget, so
  tightening it cannot make a lane answer faster.
- Merge: roughly 3-8 minutes at `high` effort with scoped verification (the disagreement set plus a
  load-bearing primary-filing spot-check — no longer the exhaustive re-verification of every agreement
  that dominated the old `xhigh` pass's cost). Default `--merge-timeout 1200` (20 min). *(These figures
  are directional estimates for the DELTA-3 configuration, not yet re-measured on a live run — the last
  timed run predates these changes.)*
- Total wall clock, typical run: roughly 8-15 minutes (parallel lanes + sequential merge).
- FinTwit sidecar: **OFF by default** (DELTA 3, 2026-07-13) — opt in with `--fintwit`. When enabled it is
  pulled once per run, roughly $0.05-0.15 per ticker (grok-4.3 token cost + `x_search` $5/1000 calls),
  regardless of how many lanes use it.

## Final Answer & Publish Layout

**Rationale:** the reader-facing copy is the answer only — no verification scaffolding, one clean read;
the audit copy (the numbered root files) is the full merged verdict with every claim check, correction,
and open item intact, kept on disk unchanged, for whenever someone needs to see the work. Two folders,
two audiences, same run.

DELTA 1 (2026-07-11) replaced the old flat one-directory-per-run model with a persistent per-stock
publish folder; Round 4 (2026-07-11) added the Final Answer layer on top of it:

- **Master folder:** `~/Parallax_Projects/` by default (`--run-base` overrides it).
- **Per-stock folder:** `~/Parallax_Projects/<SLUG>/`, where `SLUG` is the uppercase ticker (e.g. `NVDA`)
  when the subject looks like one, else a lowercase-hyphenated topic slug. This folder **persists**
  across runs — it is not recreated per invocation.
- **Published audit trail** lives at the stock folder's ROOT, numbered in pipeline order with
  model-descriptive names, each with a rendered `.html` sibling: `1_opus48_report.{md,html}`,
  `2_gpt56sol_report.{md,html}`, `3_merged_verdict.{md,html}` — the full, unabridged research and
  verification record.
- **Published reader-facing answer** lives in `<SLUG>/final/`, which holds **ONLY** numbered HTML
  finals — `<n>_<SLUG>_final_answer.html`, nothing else ever. No `.md` goes in `final/`; the markdown is
  provenance only, kept at `runs/<ts>/final_answer.md`. `final/`'s own numbering is a **completely
  independent sequence** from the root's — see "Two Independent Numbering Sequences" below.
- **Re-run numbering (root):** a second run on the same stock scans the folder root for existing `^\d+_`
  file prefixes and continues from `max+1` — e.g. a second `NVDA` run publishes `4_opus48_report.*`,
  `5_gpt56sol_report.*`, `6_merged_verdict.*`, never overwriting the first run's answers. The base index
  is computed once per run and reused for the whole triplet (or pair).
- **Single-lane mode** (`--allow-single` with one dead lane): only the surviving lane + the merged
  verdict publish at the root, numbered consecutively (e.g. `1_opus48_report.*`, `2_merged_verdict.*` if
  the Codex lane died) — never a gap or a placeholder for the dead lane. The Final Answer still
  publishes normally, with the single-lane disclosure preserved directly under its title.
- **Merge failure (exit `4`):** the lane answer(s) that survived AND the FAILED-disclosure file still
  publish at the root as the next numbered answer(s), so a link already shared or bookmarked from the
  stock folder never 404s. **No Final Answer is produced** — nothing was verified to read — and `final/`
  gets no new entry for that run.
- **Machine artifacts** (`original_prompt.md`, `fintwit.md`, `final_answer.md`, `prompts/`, `logs/`,
  `workspace/`, `manifest.json`, and the raw unnumbered `lane_claude.md`/`lane_codex.md`/`merge.md`/
  `report.html` working files) move under `<stock folder>/runs/<UTC ts>/` — everything the pipeline
  produces is still written there for debuggability; the numbered root files and `final/` are the
  published finals, and `manifest.json`'s `"published"` array and `"final_answer"` object record their
  exact paths.

```text
~/Parallax_Projects/<SLUG>/
├── 1_opus48_report.md
├── 1_opus48_report.html
├── 2_gpt56sol_report.md
├── 2_gpt56sol_report.html
├── 3_merged_verdict.md
├── 3_merged_verdict.html
├── final/                          <- READ THIS FIRST — HTML only, own numbering
│   └── 1_<SLUG>_final_answer.html
└── runs/
    └── <UTC yyyymmdd_hhmmss>/
        ├── original_prompt.md
        ├── fintwit.md
        ├── lane_claude.md
        ├── lane_codex.md
        ├── merge.md
        ├── final_answer.md          <- Final Answer markdown, provenance only (never copied into final/)
        ├── report.html
        ├── manifest.json
        ├── prompts/
        │   ├── lane_claude_prompt.md
        │   ├── lane_codex_prompt.md
        │   └── merge_prompt.md
        ├── workspace/
        │   ├── claude/
        │   ├── codex/
        │   └── merge/
        └── logs/
            ├── run.log
            ├── *.stderr.log            (one per stage/retry)
            └── *.raw_events.jsonl      (codex --json stages only: lane_codex[.+_retry], merge[.+_retry])
```

### Two Independent Numbering Sequences

The root triplet (`1_opus48_report` / `2_gpt56sol_report` / `3_merged_verdict`, or `4_`/`5_`/`6_` on a
re-run, ...) and `final/`'s own sequence (`1_<SLUG>_final_answer`, `2_`, `3_`, ...) are scanned and
numbered **completely separately** — `next_base_index()` runs once against the stock-folder root and
once against `final/`, each scoped to its own directory. A stock's second research run might publish
`final/2_<SLUG>_final_answer.html` alongside `6_merged_verdict.html` at the root; that mismatch (2 vs. 6)
is expected, not a bug — `final/`'s numbers count Final Answers, the root's count published research
artifacts, and neither sequence is aware of the other.

### Final Answer Contract (the stripper)

`make_final_answer()` in `scripts/run_parallax.py` is a **deterministic post-process — no extra model
call.** It operates on the merged verdict's `## ` (H2) section boundaries:

- **Dropped** (case-insensitive, tolerating `§`/brackets/punctuation): "Claim Verification Table",
  "Corrections", "[UNRESOLVED]", "§ Verification Log", plus any heading containing "agree", "disagree",
  "unique insight", "consensus", or "blind spot" (a defensive net against verification-scaffolding
  headings the merge rubric doesn't currently produce but a drifting model output might).
- **Kept**, in original order: Executive Summary, Verified Thesis, Catalysts, Bear Case, FinTwit / X
  Sentiment, Bottom Line & Conviction — and **any heading not on the drop list**, which is the safe
  default (unknown content is kept, never silently discarded).
- **Title:** `# <SLUG> — Parallax Final Answer (<YYYY-MM-DD> UTC)` is prepended.
- **Single-lane disclosure:** if the merged verdict's first line is the single-lane disclosure
  (`> **Single-lane mode:** ...`), it is preserved directly under the title.
- **Nothing dropped is deleted, only relocated:** a mandatory closing `## Facts Needing Human
  Verification` section collects every item/paragraph from the dropped `[UNRESOLVED]` section plus every
  item from the `**Verify before acting:**` footer (split on commas/semicolons), deduplicated
  case-insensitively when identical — that footer line is itself stripped from the body, since it is now
  represented here. If nothing was found, the section reads a single sentinel bullet: `None — all
  load-bearing claims in this answer were verified against primary sources.` The full merged verdict with
  the dropped sections intact is unaffected on disk either way — nothing here touches the root files.
- **HTML render failure:** no file lands in `final/` (never a `.md` fallback);
  `manifest["final_answer"]["html_status"]` records the reason and the `ANSWER LINKS` block says so.

### Backfill: regenerating a Final Answer without re-running the pipeline

`scripts/make_final_answer.py` is a thin standalone CLI around the same `make_final_answer()` +
`publish_final_answer()` functions `run_parallax.py` calls inline — for stock folders that predate this
feature, or to regenerate after an out-of-band edit to a merged verdict. It touches `final/` ONLY (no
manifest, no root-file changes):

```bash
python3 ~/.codex/skills/parallax/scripts/make_final_answer.py \
  --merge-md ~/Parallax_Projects/NVDA/3_merged_verdict.md \
  --stock-dir ~/Parallax_Projects/NVDA
```

### The `ANSWER LINKS` block

Every run that publishes anything ends stdout with a literal `ANSWER LINKS` block, **HTML only** (no
`.md` parentheticals), in fixed reading-priority order — independent of the files' own archival index
numbers (see "Two Independent Numbering Sequences" above):

```text
ANSWER LINKS
1. Final Answer (read this): /home/.../<SLUG>/final/<n>_<SLUG>_final_answer.html
2. Merged Verdict (full verification): /home/.../<SLUG>/3_merged_verdict.html
3. Opus 4.8 Report: /home/.../<SLUG>/1_opus48_report.html
4. GPT-5.6 Sol Report: /home/.../<SLUG>/2_gpt56sol_report.html

Open in Windows: \\wsl.localhost\<distro>\home\bhavneesh\Parallax_Projects\<SLUG>
```

Single-lane mode naturally produces 3 links (final answer, merged verdict, the one surviving lane — no
entry for the dead one). Merge-failed (exit `4`) replaces line 1 with a plain `Final answer: not produced
(merge failed).` note and lists whatever did publish (the FAILED-disclosure merged verdict, labeled
`(FAILED — not verified, see file)`, plus the lane report(s)). The closing line is always the Windows UNC
form of the stock folder (`\\wsl.localhost\<distro>\...`, distro from `$WSL_DISTRO_NAME`, falling back to
`Ubuntu`) so the user can paste it straight into Windows Explorer or a browser — or, per the concept note
at the top of this section, copy the whole `<SLUG>/final/` folder into a fresh session in one operation.
See the QC Gate's hard rule above: **the orchestrating CLI must relay this block verbatim.**

## Tuning

- `--allow-single`: if one lane fails validation even after retry, proceed in single-lane adversarial
  review mode instead of failing the run (exit `3`). The merged verdict gets an explicit top disclosure
  line either way (prompt-instructed AND runner-guaranteed, not left to model compliance alone).
- `--fintwit`: opt in to the FinTwit / X social-sentiment sidecar (Tier-4). **OFF by default** — the
  orchestrating CLI passes it only when the user explicitly asks for social/X sentiment.
- `--min-bytes`: raise for names that tend to need long reports; the merge threshold is fixed at 900
  bytes and is not exposed as a flag.
- `--dry-run`: exercise the entire pipeline (dirs, parallel dispatch, validation, retry, publish
  numbering, the Final Answer stripper, `ANSWER LINKS`, manifest, HTML, exit codes) with deterministic
  stub text and zero model/network cost. The stub merged verdict is built specifically to exercise the
  stripper's drop/keep/dedup logic (a Claim Verification Table, Corrections, two `[UNRESOLVED]` items, a
  § Verification Log, and a two-item `**Verify before acting:**` footer with one deliberate duplicate).
- Re-running the same ticker is intentional and safe: it accumulates new numbered answers rather than
  overwriting or colliding with the previous run's.

## Known Gaps

Surfaced by an independent code review (2026-07-11); documented here rather than fixed, either because
they are out of this skill's scope or because the fix would add more risk/complexity than the gap
currently warrants. Re-evaluate if real-world usage actually hits one of these:

1. **Publish numbering is not concurrency-safe.** `next_base_index()` scans a directory once at the
   start of a run and reuses that number for the whole publish step. Two Parallax processes launched
   against the SAME stock at the same moment can both compute the same base index and race to write the
   same numbered filenames, each partially clobbering the other's answers. Sequential re-runs (the
   documented, expected usage) are unaffected — this only bites genuinely simultaneous runs on one stock.
   Applies identically to `final/`'s own sequence (Round 4) — same function, same caveat, scanned against
   a different directory; two simultaneous backfill runs (`scripts/make_final_answer.py`) against the
   same stock folder carry the same race.
2. **No atomic publish.** Each numbered answer is written with a plain `Path.write_text()`, one file at a
   time, not a temp-file-plus-rename. A process killed mid-`publish_answers()` (e.g. `kill -9` from
   outside, OOM) can leave a partial numbered set at the stock-folder root — e.g. `4_opus48_report.*` and
   `5_gpt56sol_report.*` present but `6_merged_verdict.*` missing. `manifest.json`'s `"published"` array
   is only fully accurate once the run completes; a partial set is diagnosable by comparing it against
   the directory listing, but nothing currently does that comparison automatically.
3. **Published filenames are fixed labels, not model-derived.** `1_opus48_report.md` / `2_gpt56sol_report.md`
   are constants tied to the skill's default model identity (see `LANE_FILE_LABELS`), not dynamically
   built from `--claude-model`/`--codex-model`/`PARALLAX_CLAUDE_MODEL`/`PARALLAX_CODEX_MODEL`. Running
   with a materially different model override still publishes under the same filenames — the manifest
   and the file's own content correctly show the true resolved model, but the filename alone can mislead.
4. **`render_html()` mutates `sys.path` for the process lifetime.** It inserts the deep-research
   `scripts/` dir into `sys.path` on first use and never removes it (checked-before-insert, so it's
   idempotent, not unbounded) — harmless for this short-lived CLI script, but worth knowing if
   `run_parallax.py`'s functions are ever imported into a longer-lived process instead of run as `python3
   run_parallax.py ...`.

## Reference Files

- `references/lane_brief.md` — the shared research brief injected into both lanes.
- `references/merge_rubric.md` — the merger's independent-verification-with-live-tools contract,
  including the single-lane adversarial-mode branch.
- `scripts/make_final_answer.py` — standalone Final Answer backfill CLI; see "Backfill: regenerating a
  Final Answer without re-running the pipeline" above.
