# Parallax

Depth from disagreement: two independent, full-tool-suite equity research passes — Claude Opus 5/high
and GPT-5.6 Sol/high via Codex — on the same stock, plus a GPT-5.6 Sol/high merger that runs WITH live
tools to diff the two reports, verify every disagreement against primary sources, and spot-check
load-bearing shared-source figures against the filings (agreements it does not re-verify are recorded
CONCORDANT — consistency, not confirmation). FinTwit / X sentiment is **OFF by default** (Tier-4) — opt
in with `--fintwit`, only when the user explicitly asks for it. This is Tier 1 of a two-tier pipeline;
Tier 2 (model-fusion / hybrid-model-fusion / valuation) is a separate, heavier, explicit-only escalation.

- **Lanes:** Claude Opus 5/high and GPT-5.6 Sol/high (Codex), both with full tool suites (FMP
  `/stable/`, SEC filings, web search, Scite/BioMCP), run in parallel, independently, with no visibility
  into each other's work.
- **Merger:** GPT-5.6 Sol/high via Codex, **tools enabled** (not a tool-free judge) — verifies rather
  than summarizes; verification is scoped to the disagreement set plus a load-bearing primary-filing
  spot-check, so it runs at `high` (agreements it does not re-verify are labeled CONCORDANT). The two
  lane reports are shown to it **blind** — neutral Report A/B, no model names, order randomized per run —
  so a GPT merger can't favor the GPT-authored lane; the true map is recorded in the manifest for audit.
- **Orchestrator:** control plane only — dispatch, wait, QC, surface. No research call, no evidence
  packet, no authored input to the final answer.
- **Timeouts (default):** 900s per lane (600s retry) / 1200s merge (one retry, same budget).
- **Resilience:** one parallel retry for a failed lane or a failed merge; `--allow-single` degrades to
  single-lane adversarial verification instead of failing outright; merge failure is disclosed, never
  silently salvaged.
- **Publish layout:** the numbered audit trail (`1_opus5_report.{md,html}`, `2_gpt56sol_report.{md,html}`,
  `3_merged_verdict.{md,html}`) publishes at `~/Parallax_Projects/<SLUG>/`; re-runs on the same stock
  continue numbering (`4_`/`5_`/`6_`) instead of colliding. Machine artifacts live under
  `<SLUG>/runs/<UTC ts>/`.
- **Final Answer:** a deterministic post-process (no extra model call) strips the merged verdict down to
  one clean reader-facing answer — no verification scaffolding, every open item rolled into a closing
  "Facts Needing Human Verification" section — published as HTML-only at
  `<SLUG>/final/<n>_<SLUG>_final_answer.html` (its own independent numbering). `ANSWER LINKS` always
  lists it first. A standalone `scripts/make_final_answer.py` backfills it for existing stock folders.

## Quick start

```bash
python3 scripts/run_parallax.py TICKER
```

See `SKILL.md` for the full architecture, orchestrating-CLI contract, QC gate, publish layout and
`ANSWER LINKS` contract, environment variables, exit codes, latency/cost expectations, and the Tier 2
escalation path.
