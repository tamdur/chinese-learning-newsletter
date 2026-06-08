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
POLYPHONIC_PATH = REPO / "data" / "polyphonic_chars.json"
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


def load_polyphonic() -> set[str]:
    """Load the committed list of polyphonic (多音字) single characters.

    Produced by build_dictionary.py. Missing/unreadable file → empty set, which
    disables polyphone routing and preserves the prior (dictionary-only)
    behavior. This is intentional: the pipeline must not break if the list is
    absent.
    """
    try:
        data = json.loads(POLYPHONIC_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    chars = data.get("chars", []) if isinstance(data, dict) else data
    return {c for c in chars if isinstance(c, str) and len(c) == 1}


def identify_polyphonic(char: str, polyphonic: set[str]) -> bool:
    """Whether a character has multiple readings whose choice depends on context.

    The CEDICT pre-match stores only ONE reading per character (the first
    CEDICT line, which is frequently a surname or rare reading), so resolving a
    polyphone from the dictionary alone gives the wrong pronunciation roughly as
    often as the right one (e.g. 還 → ㄏㄨㄢˊ when context wants ㄏㄞˊ). Polyphones
    are therefore handed to the context-aware glossary-chars agent instead.
    """
    return char in polyphonic


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

    polyphonic = load_polyphonic()

    # Extract text and characters
    plain_text = extract_plain_text(articles)
    unique_chars = extract_unique_chars(plain_text)

    print(f"Unique CJK characters in articles: {len(unique_chars)}")
    print(f"Dictionary entries loaded: {len(dictionary)}")
    print(f"Polyphonic characters loaded: {len(polyphonic)}")

    # Single-character lookup.
    # A character resolved from the dictionary still goes to the agent when it is
    # polyphonic: the dictionary's single stored reading is context-blind, so we
    # keep it only as a fallback and let the context-aware glossary-chars agent
    # supply the reading that matches this article. The merge step prefers the
    # agent's entry over the dictionary's.
    matched = {}
    unresolved = set()
    routed_polyphones = 0

    for char in unique_chars:
        if char in dictionary:
            matched[char] = dictionary[char]
            if identify_polyphonic(char, polyphonic):
                unresolved.add(char)
                routed_polyphones += 1
        else:
            unresolved.add(char)

    # Multi-character word scanning
    word_matches = longest_match_words(plain_text, dictionary)
    matched.update(word_matches)

    # Stats. Polyphones are counted as dictionary-matched (they have a fallback
    # entry) even though they are also sent to the agent for a contextual reading.
    char_matched = sum(1 for ch in unique_chars if ch in dictionary)
    char_pct = (char_matched / len(unique_chars) * 100) if unique_chars else 0

    print(f"Single-char matched: {char_matched}/{len(unique_chars)} ({char_pct:.1f}%)")
    print(f"Multi-char words matched: {len(word_matches)}")
    print(f"Polyphones routed to agent (with dict fallback): {routed_polyphones}")
    print(f"Characters needing agent lookup: {len(unresolved)}")

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
