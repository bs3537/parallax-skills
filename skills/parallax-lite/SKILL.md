---
name: parallax-lite
description: Explicit-invocation-only fast two-model comparison using persistent Claude and Codex CLI lanes, streaming checkpoints, hard search and output budgets, complexity-scaled prompts, partial-lane salvage, and a bounded load-bearing-only judge. Use only when the user explicitly asks for Parallax Lite, Parallel Lite, or parallax-lite and wants a practical answer in roughly 2-4 minutes rather than exhaustive diligence.
---

# Parallax Lite

Run two independent bounded research passes in parallel, then blind-merge them with a targeted judge. Keep the full `parallax` skill unchanged for exhaustive diligence.

## Launch

Use one command:

```bash
python3 ~/.codex/skills/parallax-lite/scripts/run_parallax_lite.py SUBJECT
```

For a detailed request, write it to a file and pass:

```bash
python3 ~/.codex/skills/parallax-lite/scripts/run_parallax_lite.py SUBJECT --query-file /path/to/request.md
```

The runner automatically selects a profile. Override only when the user requests a specific speed/depth tradeoff:

```bash
python3 ~/.codex/skills/parallax-lite/scripts/run_parallax_lite.py SUBJECT --profile quick
```

| Profile | Lane limit | Judge limit | Searches per lane | Output per lane | Typical wall time |
| --- | ---: | ---: | ---: | ---: | ---: |
| quick | 120s | 120s | 3 | 1,000 words | 2-4 min |
| standard | 180s | 180s | 5 | 1,500 words | 3-6 min |
| complex | 240s | 240s | 8 | 2,200 words | 5-8 min |

Times are directional, not guarantees. Tool latency and provider load can dominate.

## Runtime Contract

- Treat the invoking Codex session as the control plane only: launch, monitor, QC, and relay.
- Do not run a third research pass or rewrite the judge's answer.
- Run exactly one Claude lane and one Codex lane. Never retry automatically.
- Preserve persistent session IDs. On interruption, use `resume_commands.txt` in the run directory.
- Stream raw events to `logs/` and update `lane_*.checkpoint.md` or `merge.checkpoint.md` whenever usable agent text appears.
- Enforce search and word budgets. A budget breach stops that component and salvages its latest checkpoint when usable.
- Proceed with one surviving lane automatically, but prepend an explicit partial-single-lane disclosure.
- Ask the judge to verify only disagreements capable of reversing the conclusion. Agreement is not proof.

## Quality Gate

Before presenting completion:

1. Open `manifest.json` and require status `complete`, `complete_degraded`, or `complete_partial_single_lane`.
2. Confirm `retry_policy` is `none` and each stage reports `attempts: 1`.
3. Confirm `merged_answer.md` is non-empty and begins with the required disclosure when degraded.
4. Confirm the published Final Answer HTML exists.
5. Inspect every usable lane file for real content; a process exit alone is not success.
6. Relay the runner's complete `ANSWER LINKS` block verbatim at the end of the response.

Exit `2` means no lane produced usable output. Exit `4` means usable lanes were preserved but the judge failed. Exit `5` means invalid arguments or an internal error. Do not silently rerun any of them.

## Artifacts

Runs publish under `~/Parallax_Lite_Projects/<SLUG>/`:

```text
<SLUG>/
├── <n>_claude_report.{md,html}
├── <n>_codex_report.{md,html}
├── <n>_merged_answer.{md,html}
├── final/<n>_<slug>_parallax_lite.html
└── runs/<UTC timestamp>/
    ├── manifest.json
    ├── original_prompt.md
    ├── lane_claude.md
    ├── lane_codex.md
    ├── lane_*.checkpoint.md
    ├── merged_answer.md
    ├── merge.checkpoint.md
    ├── resume_commands.txt
    ├── prompts/
    ├── logs/
    └── workspace/
```

Use `--dry-run` for deterministic zero-model validation. Use `--dry-run-fail claude|codex|both|merge` to exercise failure paths.

## Boundaries

Use Lite for comparisons, orientation, drafting, and time-sensitive screening where bounded coverage is acceptable. Do not represent it as exhaustive research. For primary-source investment, medical, legal, regulatory, or other high-stakes diligence, use `parallax-verified-lite` or the full `parallax` workflow when explicitly requested.
