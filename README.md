# Parallax Skills

Three installable Claude Code + Codex CLI research workflows that trade speed for verification depth:

1. **Parallax Lite** — rapid dual-model comparison with strict time, search, and output budgets.
2. **Parallax Verified Lite** — bounded dual-model research plus targeted primary-source adjudication.
3. **Parallax Full** — two complete Gauntlet Fast research programs, one in Claude and one in Codex,
   saved separately for human comparison with no merged verdict.

Lite and Verified Lite use blind judges. Full deliberately does not: it preserves two complete,
independent research packages and leaves comparison to the user.

## Choose the right version

| Workflow | Best for | Normal wall time | Verification depth | Failure behavior |
| --- | --- | ---: | --- | --- |
| Parallax Lite | Orientation, drafting, quick comparisons, narrow factual questions | 2-4 min quick; 3-6 min standard; 5-8 min complex | Judge checks only 2-4 conclusion-flipping disagreements | No retries; checkpoints and persistent sessions; automatic disclosed partial merge |
| Parallax Verified Lite | Investment screens, earnings/catalyst reviews, regulatory or technical questions needing primary sources | 4-8 min quick; 6-12 min standard; 8-16 min complex | 4-8 targeted primary-source checks, including load-bearing shared-source traps | No retries; checkpoints and persistent sessions; automatic disclosed partial merge |
| Parallax Full | Reading two independent institutional research packages side by side | About 1-2 hours, not yet benchmarked on the new topology | Two separate UltraDeep/Gauntlet Fast evidence, model, and report gates | One branch may survive as an explicitly partial run; no synthesis |

These times are directional, not service-level guarantees. Provider load, slow MCP connectors, long filings, and the complexity of the request can dominate. A genuinely multi-year biotechnology diligence request is not a 1-2 minute task if primary-source verification is required.

## Architecture at a glance

```text
                         original request
                                |
          +---------------------+----------------------+
          |                                            |
 Claude Gauntlet Fast program              Codex Gauntlet Fast program
 Opus 5 high lead                          GPT-5.6 Sol high lead
 four Sonnet 5 xhigh workers               four GPT-5.6 Sol high workers
 Claude Search-as-Code                     Codex Search-as-Code
 complete research package                 complete research package
          |                                            |
          +---------------- no merge -------------------+
```

Full's programs never see each other's work. Lite and Verified Lite retain their existing blind-judge
architectures.

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
./install.sh --surface both
```

The installer writes to both `~/.claude/skills` and `${CODEX_HOME:-$HOME/.codex}/skills`. It
preflights both destinations and refuses to overwrite an existing skill unless `--force` is passed.

Update an existing installation safely:

```bash
cd parallax-skills
git pull --ff-only
./install.sh --surface both --force
```

When `--force` is used, existing copies are moved to timestamped backups under the corresponding
Claude and Codex runtime homes before replacement.

Install into another skills directory:

```bash
./install.sh --dest /path/to/codex/skills
```

Preview without changing anything:

```bash
./install.sh --surface both --dry-run
```

Validate the repository and all deterministic failure paths:

```bash
./scripts/test_all.sh
```

Restart Claude Code and Codex after installation so the new skill metadata is reloaded.

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

Invoke explicitly with `$parallax`, “use Parallax,” “use Parallex,” or “run parallel Gauntlet Fast.”
Full is the exhaustive comparison tier and is intentionally slower.

### What it does

Full runs two complete independent research programs:

- Claude: Opus 5 high lead over exactly four Sonnet 5 xhigh workers.
- Codex: GPT-5.6 Sol high lead over exactly four GPT-5.6 Sol high workers.
- Separate native-web-first research, Search-as-Code runs, Perplexity gap searches, evidence ledgers,
  executable models, detailed Excel workbooks, audits, Markdown reports, and HTML reports.
- Optional independent FinTwit/X sentiment passes only when `--fintwit` is requested.
- No merger, adjudication, combined target, preferred model, claim matrix, or Final Answer.

### Flow

```text
request
  -> create one project folder with claude_research/ and codex_research/
  -> launch both branch controllers concurrently
       -> each launches exactly four non-overlapping research workers
       -> each runs its own UltraDeep Search-as-Code plan
       -> each lead executes Gauntlet Fast Phases 0-6 and 8
       -> each publishes and audits its own MD / HTML / XLSX package
  -> print two equally prominent report links
  -> stop; user compares the reports
```

### Reliability tradeoff

Full executes ten model calls before any retries: four workers and one lead per branch. The two
five-call programs run concurrently, but total compute is roughly twice a single Gauntlet Fast run.
If predictable latency matters, choose one of the Lite workflows.

### Usage

```bash
python3 ~/.codex/skills/parallax/scripts/run_parallax.py CCCC \
  --query-file ~/questions/cccc.md \
  --project-dir ~/Documents/CCCC_Parallax_20260726
```

The same runner is installed in Claude:

```bash
python3 ~/.claude/skills/parallax/scripts/run_parallax.py CCCC
```

### When to use it

- A decision where the user wants two independent institutional reports rather than a consensus.
- A broad or contested investment question where vendor/model differences are informative.
- Work that can tolerate roughly one to two hours and ten model calls.

Each branch uses the Gauntlet valuation methodology and installed valuation engine where required.

## Failure handling comparison

| Behavior | Lite | Verified Lite | Full |
| --- | --- | --- | --- |
| Stream raw events while running | Yes | Yes | Codex raw events retained per worker/lead |
| Continuously update usable checkpoint | Yes | Yes | No |
| Persistent resumable sessions | Yes | Yes | No; leaves are ephemeral |
| Automatic retry | Never | Never | One retry per failed worker; two Search-as-Code attempts |
| One branch fails | Automatic disclosed partial merge | Automatic disclosed adversarial verification | Exit 4; successful independent package preserved |
| Both branches fail | Exit 2, no fabricated merge | Exit 2, no fabricated merge | Exit 2; no reports fabricated |
| Lead/package gate fails | Exit 4, lanes preserved | Exit 4, lanes preserved | Branch fails; the other branch remains independent |
| Hard search/word budget | Yes | Yes | 24-query Search-as-Code plan; report depth follows Gauntlet |

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
~/Documents/<PROJECT>_Parallax_<YYYYMMDD>/
├── claude_research/FINAL_REPORT.html
└── codex_research/FINAL_REPORT.html
```

Every successful Full run prints the two independent report paths and the root manifest. It never
prints a merged answer.

## Security and evidence boundaries

- Full keeps each research branch isolated; neither receives the other branch's paths or artifacts.
- Social content is Tier 4 sentiment only and never anchors a material claim.
- Primary documents outrank aggregators, summaries, and search snippets.
- A partial Full run is disclosed in `RUN_MANIFEST.json` and the command exit status.
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

Remove the three installed skill folders from each surface, then restart both CLIs:

```bash
rm -rf "$HOME/.claude/skills/parallax-lite" \
       "$HOME/.claude/skills/parallax-verified-lite" \
       "$HOME/.claude/skills/parallax"
rm -rf "${CODEX_HOME:-$HOME/.codex}/skills/parallax-lite" \
       "${CODEX_HOME:-$HOME/.codex}/skills/parallax-verified-lite" \
       "${CODEX_HOME:-$HOME/.codex}/skills/parallax"
```

If installed with `--force`, timestamped backups remain under the corresponding runtime homes until
removed manually.
