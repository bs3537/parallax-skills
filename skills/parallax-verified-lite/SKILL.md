---
name: parallax-verified-lite
description: Explicit-invocation-only bounded two-model research with persistent Claude and Codex lanes, streaming checkpoints, primary-source evidence requirements, and a judge that independently verifies only conclusion-flipping disagreements and load-bearing shared-source claims. Use only when the user explicitly asks for Parallax Verified Lite, Verified Lite, or parallax-verified-lite and needs stronger evidence than Parallax Lite without the exhaustive time cost of full Parallax.
---

# Parallax Verified Lite

Run a middle-tier workflow between rapid comparison and exhaustive diligence. Reuse Parallax Lite's tested streaming engine while applying stricter source, verification, and time budgets.

## Dependency

Install `parallax-lite` beside this skill. The packaged `parallax-skills` installer installs both. The wrapper refuses to run if the shared engine is absent.

## Launch

```bash
python3 ~/.codex/skills/parallax-verified-lite/scripts/run_parallax_verified_lite.py SUBJECT
```

For a detailed request:

```bash
python3 ~/.codex/skills/parallax-verified-lite/scripts/run_parallax_verified_lite.py SUBJECT --query-file /path/to/request.md
```

| Profile | Lane limit | Judge limit | Searches per lane | Judge checks | Typical wall time |
| --- | ---: | ---: | ---: | ---: | ---: |
| quick | 240s | 240s | 5 | 4 | 4-8 min |
| standard | 360s | 360s | 8 | 6 | 6-12 min |
| complex | 480s | 480s | 12 | 8 | 8-16 min |

Times are directional. Provider and primary-document latency can extend them.

## Evidence Contract

- Require inline primary-source anchors for every load-bearing claim.
- Require each lane to keep a compact evidence register and distinguish event fact from causal inference.
- Treat search snippets, model memory, and social posts as discovery only.
- Have the judge resolve every conclusion-flipping disagreement within its verification budget.
- Spot-check load-bearing concordant claims when both lanes rely on the same source.
- Mark unresolved conflicts explicitly; never average two conflicting values.
- In single-lane mode, verify the surviving report adversarially and publish a conspicuous partial-result disclosure.

## Reliability Contract

The shared runner provides persistent sessions, streaming raw events, continuously replaced checkpoint files, hard search and output caps, no from-zero retry, automatic complexity scaling, and partial-lane salvage. Use `resume_commands.txt` to continue interrupted sessions manually.

## Quality Gate

Before presenting completion:

1. Require manifest status `complete`, `complete_degraded`, or `complete_partial_single_lane`.
2. Confirm `workflow` is `parallax-verified-lite`, `policy` is `verified`, and `retry_policy` is `none`.
3. Open every usable lane report and the merged answer.
4. Confirm every material claim retained in the bottom line has a primary-source anchor or an explicit `[UNRESOLVED]` label.
5. Confirm the judge stayed within its recorded verification/search budget.
6. Relay the complete `ANSWER LINKS` block verbatim.

Do not silently rerun failures. Exit `2` means no usable lanes; exit `4` means the judge failed while lane artifacts survived; exit `5` means configuration or internal error.

## Boundaries

Use Verified Lite for investment screens, earnings or catalyst reviews, technical comparisons, regulatory questions, and other decisions where primary-source grounding matters but exhaustive diligence is unnecessary. Use full `parallax` for broad, contested, high-stakes work where the larger time budget and fuller verification record are warranted.
