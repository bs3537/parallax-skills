# Parallax Skills

Three installable Claude Code + Codex CLI research workflows that trade speed for verification depth:

1. **Parallax Lite** — rapid dual-model comparison with strict time, search, and output budgets.
2. **Parallax Verified Lite** — bounded dual-model research plus targeted primary-source adjudication.
3. **Parallax Full** — exhaustive two-lane research and a tool-grounded disagreement-verification merger.

All three run Claude and Codex independently, hide model identity from the merger, retain the underlying lane reports, and publish a reader-facing HTML answer plus an audit trail.

## Choose the right version

| Workflow | Best for | Normal wall time | Verification depth | Failure behavior |
| --- | --- | ---: | --- | --- |
| Parallax Lite | Orientation, drafting, quick comparisons, narrow factual questions | 2-4 min quick; 3-6 min standard; 5-8 min complex | Judge checks only 2-4 conclusion-flipping disagreements | No retries; checkpoints and persistent sessions; automatic disclosed partial merge |
| Parallax Verified Lite | Investment screens, earnings/catalyst reviews, regulatory or technical questions needing primary sources | 4-8 min quick; 6-12 min standard; 8-16 min complex | 4-8 targeted primary-source checks, including load-bearing shared-source traps | No retries; checkpoints and persistent sessions; automatic disclosed partial merge |
| Parallax Full | Broad, contested, high-stakes diligence where coverage matters more than latency | Usually 8-15 min; 15-35+ min under slow tools, timeout, or retry paths | Full disagreement set plus load-bearing primary-filing spot checks | One automatic retry; dual-lane required unless `--allow-single` is passed |

These times are directional, not service-level guarantees. Provider load, slow MCP connectors, long filings, and the complexity of the request can dominate. A genuinely multi-year biotechnology diligence request is not a 1-2 minute task if primary-source verification is required.

## Architecture at a glance

```text
                         original request
                                |
                    complexity/profile selection
                                |
                  +-------------+-------------+
                  |                           |
          Claude independent lane     Codex independent lane
                  |                           |
                  +-------------+-------------+
                                |
                      blind Report A / B map
                                |
                    Codex synthesizer / judge
                                |
               merged answer + lane audit artifacts
```

The models never see each other's work during the lane phase. The judge sees neutral Report A and Report B labels in a randomized order. Agreement is treated as concordance, not proof.

## Installation

### Requirements

- Linux or WSL with Python 3.10 or newer.
- An authenticated `codex` CLI.
- An authenticated `claude` CLI.
- Access to the configured default models, or explicit model overrides.
- For source-heavy work: working web search and any desired FMP, SEC, Scite, BioMCP, or other configured connectors.

Clone and install all three skills:

```bash
git clone https://github.com/bs3537/parallax-skills.git
cd parallax-skills
./install.sh
```

The installer writes to `${CODEX_HOME:-$HOME/.codex}/skills`. It refuses to overwrite an existing skill unless `--force` is passed.

Update an existing installation safely:

```bash
cd parallax-skills
git pull --ff-only
./install.sh --force
```

When `--force` is used, existing copies are moved to a timestamped backup under `${CODEX_HOME:-$HOME/.codex}/skill-backups/` before replacement.

Install into another skills directory:

```bash
./install.sh --dest /path/to/codex/skills
```

Preview without changing anything:

```bash
./install.sh --dry-run
```

Validate the repository and all deterministic failure paths:

```bash
./scripts/test_all.sh
```

Restart Codex after installation so the new skill metadata is reloaded.

## 1. Parallax Lite

Invoke explicitly with `$parallax-lite`, “use Parallax Lite,” or “use Parallel Lite.” It is never intended to trigger merely because a question is difficult or mentions a stock.

### What it does

Parallax Lite is the practical daily-use workflow. It constrains both research lanes before they start:

- automatic `quick`, `standard`, or `complex` classification;
- 2-4 minute per-component hard limits depending on profile;
- 3-8 web searches per lane;
- 1,000-2,200 words per lane;
- one pass only, with no subagents and no recursive skills;
- a judge limited to 2-4 conclusion-flipping checks.

### Flow

```text
request
  -> classify complexity
  -> create persistent Claude UUID and persistent Codex session
  -> run both lanes concurrently
       -> append raw events immediately
       -> replace checkpoint whenever usable agent text appears
       -> stop on time, search, or output budget
  -> classify each lane as complete / partial / failed
  -> blind merge all usable material
       -> verify only conclusion-flipping disagreements
  -> publish answer, reports, manifest, and resume commands
```

### Why it is faster

Lite does not ask each panelist to write a universal equity-research template. It scales the brief to the actual question, limits discovery, avoids from-zero retries, and stops verification once another check cannot change the answer.

### Checkpoint and resume behavior

Codex JSON events are appended as they arrive. Each `agent_message` becomes a candidate checkpoint, and `thread.started.thread_id` is saved. Claude runs in streaming JSON mode with an explicit persistent session UUID. If a component times out or exceeds its search budget, the newest usable checkpoint is retained.

The run directory contains `resume_commands.txt`, for example:

```bash
claude --resume <session-uuid>
codex exec resume <thread-id> -
```

The runner does not execute these automatically. Resuming is a deliberate operator action, avoiding the old failure pattern where a 15-minute research attempt was discarded and restarted from zero.

### Usage

```bash
python3 ~/.codex/skills/parallax-lite/scripts/run_parallax_lite.py NVDA
```

Use a custom request file:

```bash
python3 ~/.codex/skills/parallax-lite/scripts/run_parallax_lite.py CCCC \
  --query-file ~/questions/cccc.md
```

Force a profile or budget:

```bash
python3 ~/.codex/skills/parallax-lite/scripts/run_parallax_lite.py NVDA \
  --profile quick --lane-timeout 90 --merge-timeout 90 \
  --max-searches 2 --max-verifications 1
```

### When to use it

- Comparing two possible explanations.
- Quick stock, product, technical, or policy orientation.
- Drafting a decision memo where unresolved items can be clearly labeled.
- Testing whether a question deserves heavier research.

Do not treat Lite as exhaustive diligence or as a substitute for a full valuation, legal opinion, medical review, or regulatory analysis.

## 2. Parallax Verified Lite

Invoke explicitly with `$parallax-verified-lite`, “use Parallax Verified Lite,” or “use Verified Lite.”

### What it adds

Verified Lite uses the same tested checkpoint/resume engine but supplies stricter evidence contracts and larger bounded profiles:

- 5-12 searches per lane;
- 1,500-3,200 words per lane;
- 4-8 judge verification checks;
- primary-source anchors for every load-bearing claim;
- recomputation of nontrivial arithmetic;
- explicit separation of event fact, causal interpretation, and unresolved evidence;
- targeted checks of load-bearing claims where both lanes share the same aggregator or normalized data source.

### Flow

```text
request
  -> identify 3-6 claims capable of changing the conclusion
  -> parallel persistent Claude and Codex research
       -> primary documents first for load-bearing claims
       -> compact evidence register
       -> streaming checkpoints
  -> blind disagreement map
  -> verify every conclusion-flipping disagreement within budget
  -> spot-check shared-source agreement only when decision-critical
  -> publish VERIFIED / CORRECTED / CONCORDANT / UNRESOLVED result
```

### Why it is not Full

Verified Lite intentionally leaves non-load-bearing agreements un-rechecked and caps the number of adjudication calls. Its goal is to establish whether the conclusion survives scrutiny, not to create a complete research archive for every peripheral fact.

### Usage

```bash
python3 ~/.codex/skills/parallax-verified-lite/scripts/run_parallax_verified_lite.py CCCC \
  --query-file ~/questions/cccc.md
```

The wrapper depends on the neighboring `parallax-lite` skill for the shared streaming engine. The repository installer always installs Lite first.

### When to use it

- An investment screen before committing to a full model.
- Earnings, catalyst, financing, or competitive-event attribution.
- A technical or regulatory question where official documentation matters.
- Any decision where a fast answer is useful only if its decisive claims are source-checked.

## 3. Parallax Full

Invoke explicitly with `$parallax` or “use Parallax.” Full is the exhaustive tier and is intentionally slower.

### What it does

Full runs two independent senior-research lanes with broad tool access:

- Claude Opus 5 at high effort.
- GPT-5.6 Sol at high effort.
- GPT-5.6 Sol merger at high effort with live tools.
- Optional FinTwit/X sentiment sidecar only when `--fintwit` is requested.
- Full disagreement-set verification plus load-bearing primary-filing spot checks.
- Deterministic stripping of audit scaffolding into a clean reader-facing Final Answer.

### Flow

```text
request
  -> optional FinTwit sidecar
  -> two full research lanes in parallel
       -> universal business, financial, catalyst, bear-case, and valuation coverage
       -> one automatic retry if a lane fails validation
  -> blind merger with live tools
       -> verify all material disagreements
       -> spot-check decision-critical shared-source figures
  -> full merged verdict
  -> deterministic Final Answer stripper
  -> numbered HTML and Markdown audit artifacts
```

### Reliability tradeoff

Full currently captures Codex raw events but waits for a terminal lane answer, uses ephemeral Codex sessions, and may retry a failed lane from zero. That is acceptable for the exhaustive tier but is exactly why Lite and Verified Lite use a different checkpointing engine. If predictable latency matters, choose one of the Lite workflows.

### Usage

```bash
python3 ~/.codex/skills/parallax/scripts/run_parallax.py CCCC \
  --query-file ~/questions/cccc.md
```

Permit a disclosed single-lane adversarial result:

```bash
python3 ~/.codex/skills/parallax/scripts/run_parallax.py CCCC \
  --query-file ~/questions/cccc.md --allow-single
```

### When to use it

- A broad investment-research screen with many independent evidence streams.
- A contested conclusion where disagreements themselves are valuable signals.
- Work that can tolerate 10-30+ minutes and benefits from a comprehensive audit trail.

Full Parallax is still a screen, not a substitute for the separate Damodaran-grounded `valuation` workflow or other domain-specific high-stakes engines.

## Failure handling comparison

| Behavior | Lite | Verified Lite | Full |
| --- | --- | --- | --- |
| Stream raw events while running | Yes | Yes | Raw Codex events retained after attempt |
| Continuously update usable checkpoint | Yes | Yes | No |
| Persistent resumable sessions | Yes | Yes | No; Codex uses ephemeral execution |
| Automatic retry | Never | Never | One retry per failed lane and merger |
| One lane fails | Automatic disclosed partial merge | Automatic disclosed adversarial verification | Stops unless `--allow-single` |
| Both lanes fail | Exit 2, no fabricated merge | Exit 2, no fabricated merge | Exit 2, no publication |
| Judge fails | Exit 4, lanes preserved | Exit 4, lanes preserved | Exit 4, lanes plus failed-disclosure file published |
| Hard search/word budget | Yes | Yes | No fixed search or length budget |

## Output locations

Lite:

```text
~/Parallax_Lite_Projects/<SLUG>/
```

Verified Lite:

```text
~/Parallax_Verified_Lite_Projects/<SLUG>/
```

Full:

```text
~/Parallax_Projects/<SLUG>/
```

Every successful run prints an `ANSWER LINKS` block. The first link is the clean reader-facing HTML answer; the remaining links expose the merged audit copy and independent lane reports.

## Security and evidence boundaries

- Lane reports and user-supplied content are wrapped as untrusted data before the judge reads them.
- Social content is Tier 4 sentiment only and never anchors a material claim.
- Two-model agreement is not independent verification.
- Primary documents outrank aggregators, summaries, and search snippets.
- A partial or degraded answer is disclosed at the top of the published result and in `manifest.json`.
- No workflow recursively invokes another fusion workflow.

## Repository layout

```text
parallax-skills/
├── README.md
├── install.sh
├── scripts/test_all.sh
└── skills/
    ├── parallax-lite/
    ├── parallax-verified-lite/
    └── parallax/
```

## Uninstall

Remove the three installed skill folders, then restart Codex:

```bash
rm -rf "${CODEX_HOME:-$HOME/.codex}/skills/parallax-lite" \
       "${CODEX_HOME:-$HOME/.codex}/skills/parallax-verified-lite" \
       "${CODEX_HOME:-$HOME/.codex}/skills/parallax"
```

If installed with `--force`, timestamped backups remain under `${CODEX_HOME:-$HOME/.codex}/skill-backups/` until removed manually.
