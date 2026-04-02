#!/usr/bin/env python3
"""Dictionary pre-matching for the glossary pipeline.

Reads articles from the pipeline checkpoint, extracts unique Chinese characters,
and looks them up against the CEDICT dictionary. Characters resolved from the
dictionary skip the agent-based glossary step; only unresolved characters need
agent lookup.

Also performs longest-match word scanning for multi-character entries.

Usage:
    python3 scripts/glossary_lookup.py

Reads:
    data/pipeline/articles.json — article content
    data/cedict_dictionary.json — pre-built dictionary

Writes:
    data/pipeline/glossary_matched.json — entries resolved from dictionary
    data/pipeline/glossary_unresolved.txt — characters needing agent lookup (one per line)
"""

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ARTICLES_PATH = REPO / "data" / "pipeline" / "articles.json"
DICTIONARY_PATH = REPO / "data" / "cedict_dictionary.json"
MATCHED_PATH = REPO / "data" / "pipeline" / "glossary_matched.json"
UNRESOLVED_PATH = REPO / "data" / "pipeline" / "glossary_unresolved.txt"

# CJK Unified Ideographs range
CJK_RE = re.compile(r"[\u4e00-\u9fff]")

# Chinese punctuation to exclude from character extraction
PUNCTUATION = set("，。「」！？、：（）—；：""''…《》〈〉【】")


def strip_spans(html: str) -> str:
    """Remove <span class="c"> tags, keeping inner text."""
    return re.sub(r'<span class="c">(.*?)</span>', r"\1", html)


def extract_plain_text(articles: list) -> str:
    """Extract plain Chinese text from all articles."""
    parts = []
    for article in articles:
        headline = article.get("headline_html", article.get("headline", ""))
        parts.append(strip_spans(headline))
        body = article.get("body_html", article.get("body", ""))
        # Strip all HTML tags
        body = re.sub(r"<[^>]+>", "", strip_spans(body))
        parts.append(body)
    return "\n".join(parts)


def extract_unique_chars(text: str) -> set[str]:
    """Extract all unique CJK characters from text, excluding punctuation."""
    chars = set()
    for ch in text:
        if CJK_RE.match(ch) and ch not in PUNCTUATION:
            chars.add(ch)
    return chars


def longest_match_words(text: str, dictionary: dict, max_word_len: int = 6) -> dict:
    """Scan text for multi-character dictionary entries using longest-match.

    Returns dictionary entries for all matched multi-char words.
    """
    matched = {}
    chars = [ch for ch in text if CJK_RE.match(ch) or ch in PUNCTUATION]

    i = 0
    while i < len(chars):
        best_match = None
        best_len = 0

        for length in range(min(max_word_len, len(chars) - i), 1, -1):
            candidate = "".join(chars[i:i + length])
            if candidate in dictionary and length > 1:
                best_match = candidate
                best_len = length
                break

        if best_match:
            matched[best_match] = dictionary[best_match]
            i += best_len
        else:
            i += 1

    return matched


def identify_polyphonic(char: str, dictionary: dict) -> bool:
    """Check if a character has multiple readings (polyphonic).

    In our dictionary format, multiple meanings are joined with "; ".
    A character is considered polyphonic if its zhuyin field contains
    different readings — but since we only store one reading per entry
    (the first CEDICT entry), we can't detect this from the dictionary alone.

    Instead, flag characters where the single stored reading may not match
    the article context. For now, we don't flag any — the dictionary's
    first reading is usually the most common one.
    """
    return False


def main():
    # Validate inputs
    if not ARTICLES_PATH.exists():
        print("ERROR: data/pipeline/articles.json not found", file=sys.stderr)
        sys.exit(1)

    if not DICTIONARY_PATH.exists():
        print("ERROR: data/cedict_dictionary.json not found", file=sys.stderr)
        print("Run: python3 scripts/build_dictionary.py", file=sys.stderr)
        sys.exit(1)

    # Load data
    with open(ARTICLES_PATH, "r", encoding="utf-8") as f:
        articles = json.load(f)

    with open(DICTIONARY_PATH, "r", encoding="utf-8") as f:
        dictionary = json.load(f)

    # Extract text and characters
    plain_text = extract_plain_text(articles)
    unique_chars = extract_unique_chars(plain_text)

    print(f"Unique CJK characters in articles: {len(unique_chars)}")
    print(f"Dictionary entries loaded: {len(dictionary)}")

    # Single-character lookup
    matched = {}
    unresolved = set()

    for char in unique_chars:
        if char in dictionary:
            matched[char] = dictionary[char]
        else:
            unresolved.add(char)

    # Multi-character word scanning
    word_matches = longest_match_words(plain_text, dictionary)
    matched.update(word_matches)

    # Stats
    char_matched = len(unique_chars) - len(unresolved)
    char_pct = (char_matched / len(unique_chars) * 100) if unique_chars else 0

    print(f"Single-char matched: {char_matched}/{len(unique_chars)} ({char_pct:.1f}%)")
    print(f"Multi-char words matched: {len(word_matches)}")
    print(f"Unresolved characters: {len(unresolved)}")

    # Write outputs
    MATCHED_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(MATCHED_PATH, "w", encoding="utf-8") as f:
        json.dump(matched, f, ensure_ascii=False, indent=2)

    with open(UNRESOLVED_PATH, "w", encoding="utf-8") as f:
        for char in sorted(unresolved):
            f.write(char + "\n")

    print(f"\nWritten: {MATCHED_PATH}")
    print(f"Written: {UNRESOLVED_PATH}")

    if unresolved:
        print(f"\nUnresolved characters ({len(unresolved)}):")
        print("  " + "".join(sorted(unresolved)))


if __name__ == "__main__":
    main()
