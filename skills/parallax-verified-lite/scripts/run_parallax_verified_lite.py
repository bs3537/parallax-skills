#!/usr/bin/env python3
"""Launch Parallax Verified Lite through the shared checkpointing engine."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = SKILL_ROOT.parent
CORE_PATH = SKILLS_ROOT / "parallax-lite" / "scripts" / "run_parallax_lite.py"


def load_core():
    if not CORE_PATH.is_file():
        raise SystemExit(
            "parallax-verified-lite: missing shared engine at "
            f"{CORE_PATH}; install parallax-lite beside this skill"
        )
    spec = importlib.util.spec_from_file_location("parallax_lite_shared_engine", CORE_PATH)
    if spec is None or spec.loader is None:
        raise SystemExit(f"parallax-verified-lite: cannot load shared engine: {CORE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main(argv: list[str] | None = None) -> int:
    user_args = list(sys.argv[1:] if argv is None else argv)
    defaults = [
        "--policy",
        "verified",
        "--skill-root",
        str(SKILL_ROOT),
        "--workflow-name",
        "parallax-verified-lite",
        "--final-suffix",
        "parallax_verified_lite",
    ]
    if "--run-base" not in user_args:
        defaults.extend(["--run-base", str(Path.home() / "Parallax_Verified_Lite_Projects")])
    return load_core().main(defaults + user_args)


if __name__ == "__main__":
    raise SystemExit(main())
