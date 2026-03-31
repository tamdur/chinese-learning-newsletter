#!/usr/bin/env python3
"""Merge glossary sources into a single validated glossary.

Reads dictionary pre-match and agent-produced glossary files from
data/pipeline/, validates zhuyin (Bopomofo only), and writes the
final merged glossary.

Usage:
    python3 scripts/glossary_merge.py [agent_words.json ...]

Arguments are optional paths to agent-produced word glossary JSON files.
If none provided, only merges glossary_matched.json with any existing
glossary_agent_chars.json and glossary_agent_words.json in data/pipeline/.
"""

import json
import re
import sys
from pathlib import Path

PIPELINE = Path("data/pipeline")
BOPOMOFO = re.compile(r"[\u3100-\u312F\u31A0-\u31BF]")


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_zhuyin(glossary: dict) -> dict:
    """Keep only entries with valid Bopomofo zhuyin."""
    clean = {}
    dropped = 0
    for k, v in glossary.items():
        if BOPOMOFO.search(v.get("zhuyin", "")):
            clean[k] = v
        else:
            dropped += 1
    if dropped:
        print(f"  Dropped {dropped} entries with invalid zhuyin (pinyin or empty)")
    return clean


def main():
    # Load dictionary pre-match
    matched = load_json(PIPELINE / "glossary_matched.json")

    # Load agent-produced single-char entries
    agent_chars = load_json(PIPELINE / "glossary_agent_chars.json")

    # Load agent-produced multi-char word entries
    agent_words = load_json(PIPELINE / "glossary_agent_words.json")

    # Also load any files passed as arguments
    for arg in sys.argv[1:]:
        extra = load_json(Path(arg))
        agent_words.update(extra)

    # Merge: agent entries override dictionary for same key
    merged = {**matched, **agent_chars, **agent_words}

    # Validate zhuyin
    merged = validate_zhuyin(merged)

    single = sum(1 for k in merged if len(k) == 1)
    multi = sum(1 for k in merged if len(k) > 1)
    print(f"Glossary: {len(merged)} total (single-char: {single}, multi-char: {multi})")

    with open(PIPELINE / "glossary.json", "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()
