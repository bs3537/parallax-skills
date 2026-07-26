# Full Parallax Branch Contract

## Purpose

Use this reference when changing Full Parallax orchestration, prompts, model routing, artifact
requirements, or tests. Full Parallax launches two independent Gauntlet Fast research programs and
never synthesizes them.

## Topology

Each branch has five model calls:

| Branch | Four workers | Lead |
| --- | --- | --- |
| Claude | `claude-sonnet-5`, `xhigh` | `claude-opus-5`, `high` |
| Codex | `gpt-5.6-sol`, `high` | `gpt-5.6-sol`, `high` |

The two branch controllers run concurrently. Each set of four workers runs concurrently. A worker or
lead is a leaf and never spawns another agent.

## Lane boundaries

1. Demand, TAM or epidemiology, customers, market expectations, and five-year durability.
2. Competition, substitutes, product or pipeline differentiation, moat inputs, IP, and bear evidence.
3. Filings, financials, capital structure, runway, ownership, and valuation inputs.
4. Catalysts, regulatory/legal status, management/governance, financing, and falsifiers.

Every worker brief must state the objective, decision relevance, output format, allowed and forbidden
tools, prohibited overlap, source/date/locator/excerpt standard, two-attempt abstention, and prohibition
on conclusions outside its lane.

## Retrieval sequence

1. Workers use native web search and open primary documents.
2. The branch runs its own installed Search-as-Code script and persists its own UltraDeep plan,
   source/evidence ledgers, cost log, exclusions, and coverage diagnostics.
3. The lead uses targeted direct Perplexity for residual gaps.
4. The lead verifies primary documents before admitting claims to the branch ledger.

Search results, snippets, FMP, BioMCP metadata, Scite context, and model output are discovery or
structured inputs, not final proof. FMP material figures require filing reconciliation. Biomedical
work uses BioMCP/PubMed first and Scite selectively. A runtime without a BioMCP connector or skill
wrapper uses the installed `biomcp` CLI on PATH.

Search-as-Code is a hard branch gate. A failed or degraded Search-as-Code result stops that branch
before the lead; it cannot be relabeled complete from partial files.

## Branch artifact gate

Require these canonical files:

- `01_scope_and_assumptions.md`
- `02_source_manifest.csv`
- `03_evidence_ledger.csv`
- `04_catalyst_and_pos_model.py`
- `05_valuation_model.py`
- `06_model_outputs.csv`
- `07_working_research.md`
- `08_preliminary_report.md`
- `FINAL_REPORT.md`
- `FINAL_REPORT.html`
- one `*_Model.xlsx`
- `VERIFICATION_LOG.md`
- `sources.jsonl`
- `evidence.jsonl`
- `audit_manifest.json`
- `run_manifest.json`
- `PARALLAX_BRANCH_MANIFEST.json` (outer runner stage status; never overwrites the
  branch-authored `run_manifest.json`)

Require exactly four `lanes/lane_*/report.md` files and the branch-local Search-as-Code plan,
coverage summary, sources, and evidence. The Fast-mode banner and LOW confidence cap are mandatory.

## Isolation and prohibited outputs

- Never place one branch path in the other branch's prompt.
- Never share workers, source ledgers, Search-as-Code outputs, FinTwit context, models, or calculations.
- Never create a merge prompt, merge workspace, merged verdict, combined claim matrix, consensus
  rating, averaged target, preferred report, or combined final answer.
- A successful branch may survive a partial run, but cannot make the overall status `complete_both`.

## Verification

Unit-test argv routing, worker counts, search-plan locality, folder topology, success, one-branch
failure, and both-branch failure. Exercise the complete filesystem flow with `--dry-run`. Before
publishing a revision, run repository tests, install into both WSL skill trees, compare hashes, run
bounded live CLI/model preflights, and complete a fresh-context review of the diff and test output.
