#!/usr/bin/env python3
"""Parallax Final Answer backfill tool.

Generates and publishes a reader-facing Final Answer from an EXISTING merged verdict, without
re-running the research/merge pipeline. This is the same deterministic stripper run_parallax.py calls
inline at the end of a live run (make_final_answer() + publish_final_answer(), imported from
run_parallax.py — no logic is duplicated here), decoupled into a standalone tool for:

  - backfilling stock folders that predate the Final Answer feature (existing N_merged_verdict.md files
    with no final/ folder yet), and
  - regenerating a Final Answer after an out-of-band edit to a merged verdict.

Contract: computes the next final/ index and publishes into <stock-dir>/final/ ONLY. Updates nothing
else — it does not touch manifest.json, the stock-folder root numbering, or any other file. The
markdown intermediate render_html() needs is written to a throwaway temp file and removed afterward, so
this tool leaves no persistent side effect beyond final/ itself.

Usage:
    python3 make_final_answer.py --merge-md /path/to/SLUG/3_merged_verdict.md --stock-dir /path/to/SLUG
    python3 make_final_answer.py --merge-md ... --stock-dir ... --slug CUSTOM_LABEL
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_parallax import (  # noqa: E402
    SINGLE_LANE_DISCLOSURE_PREFIX,
    make_final_answer,
    publish_final_answer,
    utc_stamp,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--merge-md", required=True, help="Path to an existing merged-verdict markdown file (e.g. <stock-dir>/N_merged_verdict.md).")
    parser.add_argument("--stock-dir", required=True, help="Stock folder root; final/<n>_<SLUG>_final_answer.html publishes under it.")
    parser.add_argument("--slug", help="SLUG for the title and filename; defaults to --stock-dir's own basename.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    merge_md_path = Path(args.merge_md).expanduser()
    if not merge_md_path.is_file():
        print(f"make_final_answer: --merge-md not found: {merge_md_path}", file=sys.stderr)
        return 5

    stock_dir = Path(args.stock_dir).expanduser().resolve()
    if not stock_dir.is_dir():
        print(f"make_final_answer: --stock-dir not found: {stock_dir}", file=sys.stderr)
        return 5

    slug = args.slug or stock_dir.name
    merge_md_text = merge_md_path.read_text(encoding="utf-8")
    single_lane = merge_md_text.strip().startswith(SINGLE_LANE_DISCLOSURE_PREFIX)
    run_ts = utc_stamp()

    final_text = make_final_answer(merge_md_text, slug, single_lane, run_ts)

    with tempfile.TemporaryDirectory(prefix="parallax-backfill-") as tmp:
        result = publish_final_answer(stock_dir, Path(tmp) / "final_answer.md", slug, final_text)

    print(
        f"make_final_answer: source={merge_md_path} stock_dir={stock_dir} slug={slug} "
        f"single_lane_detected={single_lane}"
    )
    print(f"make_final_answer: index={result['index']} html_status={result['html_status']}")
    if result["published"]:
        print(f"  -> {result['html_path']}")
        return 0

    print(f"make_final_answer: HTML render failed ({result['html_status']}); nothing written to final/", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
