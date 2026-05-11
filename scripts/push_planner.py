#!/usr/bin/env python3
"""Plan a chunked, verifiable MCP push for the cloud Routine.

The Claude Routines orchestrator pushes pipeline output via
`mcp__github__push_files`. Each call requires reading every pushed
file's contents into the orchestrator's context first. When a pipeline
produces many large files (a 60 KB archive + a 60 KB glossary +
shared.css + shared.js + ...), a single push call has been observed
to drop the largest files — most likely because the orchestrator hits
its per-turn token budget while assembling the call.

This script does NOT call MCP itself. It produces a deterministic
plan the orchestrator follows:
  - `groups`: an ordered list of file groups, each <= MAX_GROUP_BYTES,
    that the orchestrator pushes via SEPARATE sequential MCP calls
    (each becomes one commit on origin/main).
  - `verify_cmd`: the bash one-liner the orchestrator runs after the
    final group to confirm every file landed on origin/main.

Usage:
    python3 scripts/push_planner.py [--max-bytes 25000] [--against HEAD~1]

Prints JSON to stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Soft cap on bytes per push call. Empirically the cloud orchestrator
# starts dropping files when one push includes >~30 KB of content,
# so we keep groups comfortably under that.
DEFAULT_MAX_GROUP_BYTES = 25_000


def changed_files(against: str) -> list[str]:
    """Return paths changed in HEAD relative to `against` (e.g. HEAD~1)."""
    out = subprocess.check_output(
        ["git", "diff", "--name-only", against, "HEAD"], cwd=REPO, text=True
    )
    return [line.strip() for line in out.splitlines() if line.strip()]


def file_size(path: str) -> int:
    full = REPO / path
    return full.stat().st_size if full.exists() else 0


def plan_groups(files: list[str], max_bytes: int) -> list[list[str]]:
    """Greedy bin-packing: largest file first, fill remaining with smaller ones.

    Any single file larger than max_bytes goes alone (we can't split it).
    This puts the most-fragile pushes (single large file, no padding)
    first so verification catches them early.
    """
    sized = [(file_size(f), f) for f in files]
    sized.sort(reverse=True)  # largest first

    groups: list[list[str]] = []
    for size, fname in sized:
        if size > max_bytes:
            groups.append([fname])
            continue
        placed = False
        for g in groups:
            g_bytes = sum(file_size(p) for p in g)
            if g_bytes + size <= max_bytes:
                g.append(fname)
                placed = True
                break
        if not placed:
            groups.append([fname])
    return groups


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--against", default="HEAD~1",
                   help="Git ref to diff against (default: HEAD~1).")
    p.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_GROUP_BYTES,
                   help="Max bytes per push group (default: 25000).")
    args = p.parse_args()

    files = changed_files(args.against)
    groups = plan_groups(files, args.max_bytes)

    plan = {
        "against": args.against,
        "max_bytes": args.max_bytes,
        "file_count": len(files),
        "group_count": len(groups),
        "groups": [
            {
                "index": i,
                "files": g,
                "total_bytes": sum(file_size(f) for f in g),
            }
            for i, g in enumerate(groups, 1)
        ],
        "verify_cmd": (
            "git fetch origin main && "
            "git diff origin/main..HEAD --name-only"
        ),
        "verify_expectation": (
            "verify_cmd must print nothing. Any output is a file that did "
            "not land on origin/main and must be re-pushed individually."
        ),
    }
    print(json.dumps(plan, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
