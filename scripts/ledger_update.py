#!/usr/bin/env python3
"""Append today's selected stories to the newsletter topic ledger.

The ledger gives the story-selector semantic memory of which TOPICS and ANGLES
the paper has already covered, so it can avoid reprinting the same running story
with no new angle (the obsessions pipeline has an equivalent headline log).

Run this at the END of a successful newsletter run — after the push, before
checkpoint cleanup — so only published issues are logged.

Reads:
    data/pipeline/selected.json   — selector output: {date, selected: [...]}
    data/pipeline/articles.json   — for Chinese headlines (optional join by id)

Writes:
    data/newsletter_topic_ledger.json  — {"entries": [...]}, trimmed to recent days

Idempotent: if the ledger already has entries for selected.json's date, it does
nothing, so re-running a same-day issue won't double-log.
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SELECTED_PATH = REPO / "data" / "pipeline" / "selected.json"
ARTICLES_PATH = REPO / "data" / "pipeline" / "articles.json"
LEDGER_PATH = REPO / "data" / "newsletter_topic_ledger.json"
RETENTION_DAYS = 30


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def parse_date(s):
    try:
        return date.fromisoformat(str(s)[:10])
    except (ValueError, TypeError):
        return None


def chinese_headlines_by_id(articles) -> dict:
    """Map article_id -> Chinese headline, so the ledger is human-readable."""
    out = {}
    if isinstance(articles, list):
        for a in articles:
            if isinstance(a, dict) and "article_id" in a:
                out[a["article_id"]] = a.get("headline_plain") or a.get("headline") or ""
    return out


def main() -> int:
    selected_doc = load_json(SELECTED_PATH)
    if not isinstance(selected_doc, dict):
        print(f"ledger_update: {SELECTED_PATH.name} missing or unreadable; nothing to do")
        return 0

    issue_date = selected_doc.get("date", "")
    stories = selected_doc.get("selected", []) or []
    if not issue_date or not stories:
        print("ledger_update: selected.json has no date or no stories; nothing to do")
        return 0

    ledger = load_json(LEDGER_PATH)
    entries = ledger.get("entries", []) if isinstance(ledger, dict) else []

    # Idempotent: skip if this date is already logged.
    if any(isinstance(e, dict) and e.get("date") == issue_date for e in entries):
        print(f"ledger_update: {issue_date} already in ledger; skipping")
        return 0

    cn_headlines = chinese_headlines_by_id(load_json(ARTICLES_PATH))

    added = 0
    for story in stories:
        if not isinstance(story, dict):
            continue
        rank = story.get("rank")
        headline = cn_headlines.get(rank) or story.get("title", "")
        entries.append({
            "date": issue_date,
            "rank": rank,
            "topic_id": story.get("topic_id", ""),
            "topic": story.get("topic", ""),
            "angle": story.get("angle") or story.get("new_development", ""),
            "headline": headline,
        })
        added += 1

    # Trim to the retention window (keep entries within RETENTION_DAYS of this issue).
    cutoff = parse_date(issue_date)
    if cutoff:
        cutoff -= timedelta(days=RETENTION_DAYS)
        entries = [
            e for e in entries
            if not isinstance(e, dict)
            or (parse_date(e.get("date")) is None or parse_date(e.get("date")) >= cutoff)
        ]

    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEDGER_PATH.write_text(
        json.dumps({"entries": entries}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"ledger_update: added {added} entries for {issue_date}; "
          f"ledger now holds {len(entries)} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
