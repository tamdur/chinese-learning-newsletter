#!/usr/bin/env python3
"""Merge all glossary sources into final glossary.json.

Reads:
    data/pipeline/glossary_matched.json    — dictionary pre-match (single + multi-char)
    data/pipeline/glossary_chars_*.tsv     — agent single-char outputs (one TSV per batch)
    data/pipeline/glossary_words_*.json    — agent multi-char outputs (one JSON per batch)
    data/pipeline/articles.json            — articles, used for completeness check

Writes:
    data/pipeline/glossary.json            — merged, validated glossary
    data/pipeline/glossary_missing.txt     — single-char keys still missing (one per line)

Parallel-safe: each agent batch writes to its own unique file (e.g.
glossary_chars_b1.tsv, glossary_chars_b2.tsv); this script globs and merges them.

Override order (later wins): dictionary < chars-agent < words-agent.
Zhuyin validation: entries lacking any Bopomofo (U+3100-U+312F) are discarded.

Exit codes:
    0 — merged (caller should check glossary_missing.txt for remediation)
    1 — input error (required file missing or malformed)
"""

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PIPE = REPO / "data" / "pipeline"
ARTICLES_PATH = PIPE / "articles.json"
MATCHED_PATH = PIPE / "glossary_matched.json"
GLOSSARY_PATH = PIPE / "glossary.json"
MISSING_PATH = PIPE / "glossary_missing.txt"

CJK_RE = re.compile(r"[\u4e00-\u9fff]")
BOPOMOFO_RE = re.compile(r"[\u3100-\u312F]")
PUNCTUATION = set("，。「」！？、：（）—；：""''…《》〈〉【】")

# Field-name aliases — agents occasionally use synonyms.
ZHUYIN_KEYS = ("zhuyin", "bopomofo", "pronunciation", "pinyin", "reading")
ENGLISH_KEYS = ("english", "definition", "meaning", "gloss", "translation", "en")


def has_bopomofo(zhuyin: str) -> bool:
    return bool(zhuyin) and bool(BOPOMOFO_RE.search(zhuyin))


def first_value(entry: dict, keys: tuple) -> str:
    for k in keys:
        v = entry.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def normalize_entry(value) -> dict | None:
    """Coerce an agent entry into {zhuyin, english}. Returns None if unusable."""
    if not isinstance(value, dict):
        return None
    zhuyin = first_value(value, ZHUYIN_KEYS)
    english = first_value(value, ENGLISH_KEYS)
    if not zhuyin and not english:
        return None
    return {"zhuyin": zhuyin, "english": english}


def strip_bom_and_fences(text: str) -> str:
    if text.startswith("\ufeff"):
        text = text[1:]
    # Strip ALL markdown code fences anywhere in the text — not just at the edges,
    # since agents sometimes prepend prose before opening the fence.
    text = re.sub(r"```(?:json|tsv|text)?\s*\n?", "", text)
    text = re.sub(r"\n?```", "", text)
    return text


def extract_json_blob(text: str) -> str | None:
    """Find the outermost JSON object/array in text, even with surrounding prose.

    Prefers whichever of `{...}` or `[...]` appears earliest and parses cleanly,
    so an outer array isn't mistaken for an inner object.
    """
    text = strip_bom_and_fences(text).strip()
    if not text:
        return None
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass
    candidates = []
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = text.find(open_ch)
        end = text.rfind(close_ch)
        if start >= 0 and end > start:
            blob = text[start:end + 1]
            try:
                json.loads(blob)
                candidates.append((start, blob))
            except json.JSONDecodeError:
                continue
    if not candidates:
        return None
    # Prefer the candidate that starts earliest; ties broken by length (longer wins).
    candidates.sort(key=lambda c: (c[0], -len(c[1])))
    return candidates[0][1]


def coerce_to_glossary(data) -> dict:
    """Accept a variety of agent-produced shapes and return {key: {zhuyin, english}}.

    Handled shapes:
      - {key: {zhuyin, english}}                      — canonical
      - {key: {pronunciation, definition, ...}}       — alias field names
      - [{key/word/char: K, zhuyin: Z, english: E}]   — list of records
      - {"glossary": {...}} or {"entries": {...}}     — single-key wrapper
    """
    if data is None:
        return {}

    # Single-key wrapper {"glossary": {...}} or {"entries": [...]}.
    if isinstance(data, dict) and len(data) == 1:
        only_value = next(iter(data.values()))
        if isinstance(only_value, (dict, list)) and not normalize_entry(only_value):
            data = only_value

    out = {}
    if isinstance(data, dict):
        for key, value in data.items():
            if not isinstance(key, str) or not key:
                continue
            entry = normalize_entry(value)
            if entry:
                out[key] = entry
    elif isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            key = first_value(item, ("key", "word", "char", "character", "term", "headword"))
            if not key:
                continue
            entry = normalize_entry(item)
            if entry:
                out[key] = entry
    return out


def load_json_lenient(path: Path, source_name: str) -> dict:
    """Load a glossary JSON file tolerantly. Returns {} on unrecoverable errors."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"WARN {path.name}: read failed ({e})", file=sys.stderr)
        return {}
    blob = extract_json_blob(raw)
    if blob is None:
        print(f"WARN {path.name}: no parseable JSON found, skipped", file=sys.stderr)
        return {}
    try:
        data = json.loads(blob)
    except json.JSONDecodeError as e:
        print(f"WARN {path.name}: invalid JSON ({e}), skipped", file=sys.stderr)
        return {}
    coerced = coerce_to_glossary(data)
    if not coerced:
        print(f"WARN {path.name}: no usable entries after normalization", file=sys.stderr)
    return coerced


def parse_tsv_lenient(path: Path) -> dict:
    """Parse a glossary-chars TSV file tolerantly.

    - Skips blank lines and a header row if first column literally says "character".
    - Strips markdown fences if the agent wrapped its output.
    - Accepts >3 columns (uses first 3); skips lines with <3 columns.
    - Falls back to JSON parse if the file is actually JSON despite .tsv extension.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"WARN {path.name}: read failed ({e})", file=sys.stderr)
        return {}

    text = strip_bom_and_fences(raw).strip()
    if not text:
        return {}

    # Curveball: agent wrote JSON into a .tsv file.
    if text.lstrip().startswith(("{", "[")):
        blob = extract_json_blob(text)
        if blob is not None:
            try:
                return coerce_to_glossary(json.loads(blob))
            except json.JSONDecodeError:
                pass

    entries = {}
    for line_num, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.rstrip()
        if not line.strip():
            continue
        parts = line.split("\t")
        # Tolerate single-tab vs multi-space separators.
        if len(parts) < 3:
            parts = re.split(r"\s{2,}|\t+", line)
        if len(parts) < 3:
            print(f"WARN {path.name}:{line_num}: <3 columns, skipped: {line!r}",
                  file=sys.stderr)
            continue
        char, zhuyin, english = parts[0].strip(), parts[1].strip(), parts[2].strip()
        if char.lower() in ("character", "char", "key"):
            continue  # header row
        if not char or not zhuyin:
            continue
        entries[char] = {"zhuyin": zhuyin, "english": english}
    return entries


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_unique_chars(articles: list) -> set[str]:
    chars = set()
    for article in articles:
        for field in ("headline_html", "headline", "body_html", "body"):
            text = article.get(field, "")
            text = re.sub(r"<[^>]+>", "", text)
            for ch in text:
                if CJK_RE.match(ch) and ch not in PUNCTUATION:
                    chars.add(ch)
    return chars


def merge_layer(merged: dict, layer: dict, source: str, discarded: list):
    for key, value in layer.items():
        if not isinstance(value, dict):
            continue
        zhuyin = value.get("zhuyin", "")
        if not has_bopomofo(zhuyin):
            discarded.append(f"{source}:{key} (zhuyin={zhuyin!r})")
            continue
        merged[key] = {"zhuyin": zhuyin, "english": value.get("english", "")}


def main():
    if not ARTICLES_PATH.exists():
        print(f"ERROR: {ARTICLES_PATH} not found", file=sys.stderr)
        sys.exit(1)
    if not MATCHED_PATH.exists():
        print(f"ERROR: {MATCHED_PATH} not found "
              "(run scripts/glossary_lookup.py first)", file=sys.stderr)
        sys.exit(1)

    articles = load_json(ARTICLES_PATH)
    dict_entries = load_json(MATCHED_PATH)

    chars_files = sorted(PIPE.glob("glossary_chars_*.tsv"))
    words_files = sorted(PIPE.glob("glossary_words_*.json"))

    chars_entries = {}
    for path in chars_files:
        chars_entries.update(parse_tsv_lenient(path))

    words_entries = {}
    for path in words_files:
        words_entries.update(load_json_lenient(path, path.name))

    merged: dict = {}
    discarded: list = []
    merge_layer(merged, dict_entries, "dictionary", discarded)
    merge_layer(merged, chars_entries, "chars-agent", discarded)
    merge_layer(merged, words_entries, "words-agent", discarded)

    unique_chars = extract_unique_chars(articles)
    missing = sorted(ch for ch in unique_chars if ch not in merged)

    PIPE.mkdir(parents=True, exist_ok=True)
    with open(GLOSSARY_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    with open(MISSING_PATH, "w", encoding="utf-8") as f:
        for ch in missing:
            f.write(ch + "\n")

    single = sum(1 for k in merged if len(k) == 1)
    multi = len(merged) - single

    print(f"Sources: dict={len(dict_entries)} chars={len(chars_entries)} "
          f"words={len(words_entries)} (from {len(chars_files)} TSV + "
          f"{len(words_files)} JSON files)")
    print(f"Merged: {len(merged)} entries ({single} single-char, {multi} multi-char)")
    print(f"Discarded (bad zhuyin): {len(discarded)}")
    for d in discarded[:10]:
        print(f"  - {d}")
    if len(discarded) > 10:
        print(f"  ... and {len(discarded) - 10} more")
    print(f"Article unique chars: {len(unique_chars)}")
    print(f"Missing single-char entries: {len(missing)}")
    if missing:
        print(f"  {''.join(missing)}")
    print(f"Written: {GLOSSARY_PATH}")
    print(f"Written: {MISSING_PATH}")


if __name__ == "__main__":
    main()
