---
name: parallax-verified-lite
description: Explicit-invocation-only bounded two-model research with persistent Claude and Codex lanes, streaming checkpoints, primary-source evidence requirements, and a judge that independently verifies only conclusion-flipping disagreements and load-bearing shared-source claims. Use only when the user explicitly asks for Parallax Verified Lite, Verified Lite, or parallax-verified-lite and needs stronger evidence than Parallax Lite without the exhaustive time cost of full Parallax.
---

# Parallax Verified Lite

Run a middle-tier workflow between rapid comparison and exhaustive diligence. Reuse Parallax Lite's tested streaming engine while applying stricter source, verification, and time budgets.

## Agents, models, review and web search: follow the saved custom instructions

This skill does not choose models or effort levels for its roles. Take them from the user's saved custom instructions for the host you are running in: Claude Code `~/.claude/CLAUDE.md` (with its imported memory files) · agy/Gemini `~/.gemini/GEMINI.md` · Codex CLI `~/.codex/AGENTS.md` · Grok CLI `~/.grok/AGENTS.md` · Kimi Code `~/.kimi-code/AGENTS.md` · claude.ai / Desktop: the profile custom instructions. Read the relevant parts before the first spawn or search:
- **Subagents / data collectors / workers / lanes:** model and effort, which tool and connector calls must go through them, and the text their briefs must carry (e.g. the search-fallback paragraph).
- **Orchestrator (main model):** which model does the quantitative work, synthesis and rating this skill assigns to "the main model" or "the lead".
- **Reviewer / judge / verifier:** whether this output needs an independent review, with which model and effort, and what the reviewer is given.
- **Web search:** providers, their order, the fallback chain, and which native search tools not to use.

Where this skill, its references or its scripts name a model (e.g. a `claude-sonnet-*` default in a script or config), that value only mirrors the current custom instructions; the saved custom instructions win on any conflict. If they are silent on a point, use the host default and say so in the output's methodology note.

The cross-vendor design (one independent Claude lane and one independent Codex lane) is this skill's identity and stays, but the model version and effort of each lane, the merge judge and any collectors follow the host's saved custom instructions (Claude: `~/.claude/CLAUDE.md`; Codex: `~/.codex/AGENTS.md`); the names and ids in `scripts/run_parallax_verified_lite.py` (which reuses the `parallax-lite` engine and its defaults) and in tables are current defaults mirroring them.

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
- Primary-source anchors for SEC filings come from the `edgar-intel` MCP when exposed (accession + item + char offsets + sec.gov URL via `search_filings`/`get_section`; cover shares via `get_cover_page_facts`); the judge re-slices disputed quotes with `get_chunk`/`get_section` instead of re-fetching sec.gov. Run `prefetch` only if the ticker is not in `index_status` and the budget allows.
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
