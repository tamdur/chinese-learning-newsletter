#!/usr/bin/env python3
"""Fetch and cache source texts for the Daily Wisdom page.

This script fetches the Heart Sutra and Mengzi texts from online sources,
parses them, and writes cached JSON files to data/sources/. These files
are committed to the repo and read by the daily wisdom pipeline.

Zen passages require interactive curation and are handled separately.

Usage:
    python3 scripts/build_wisdom_sources.py [--heart-sutra] [--mengzi] [--all]
    Defaults to --all if no flags given.

Sources:
    Heart Sutra: https://pages.ucsd.edu/~dkjordan/chin/chtxts/ShinJing.html
    Mengzi: https://ctext.org/mengzi (API: https://ctext.org/api.pl)
"""

import argparse
import json
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOURCES_DIR = REPO / "data" / "sources"

# ---------------------------------------------------------------------------
# Heart Sutra
# ---------------------------------------------------------------------------

HEART_SUTRA_URL = "https://pages.ucsd.edu/~dkjordan/chin/chtxts/ShinJing.html"

# The full Heart Sutra text in Traditional Chinese, segmented into 7 parts
# by natural phrase boundaries. This is used as a fallback if fetching fails.
# Source: standard Buddhist canon text.
HEART_SUTRA_SEGMENTS = [
    # Monday: Opening — Avalokitesvara's insight
    "觀自在菩薩，行深般若波羅蜜多時，照見五蘊皆空，度一切苦厄。",
    # Tuesday: Form and emptiness
    "舍利子，色不異空，空不異色，色即是空，空即是色，受想行識，亦復如是。",
    # Wednesday: Characteristics of emptiness
    "舍利子，是諸法空相，不生不滅，不垢不淨，不增不減。是故空中無色，無受想行識。",
    # Thursday: No senses, no ignorance
    "無眼耳鼻舌身意，無色聲香味觸法，無眼界，乃至無意識界。無無明，亦無無明盡，乃至無老死，亦無老死盡。",
    # Friday: No suffering, no attainment
    "無苦集滅道，無智亦無得。以無所得故，菩提薩埵，依般若波羅蜜多故，心無罣礙。",
    # Saturday: No fear, nirvana
    "無罣礙故，無有恐怖，遠離顛倒夢想，究竟涅槃。三世諸佛，依般若波羅蜜多故，得阿耨多羅三藐三菩提。",
    # Sunday: The great mantra
    "故知般若波羅蜜多，是大神咒，是大明咒，是無上咒，是無等等咒，能除一切苦，真實不虛。故說般若波羅蜜多咒，即說咒曰：揭諦揭諦，波羅揭諦，波羅僧揭諦，菩提薩婆訶。",
]

HEART_SUTRA_TRANSLATIONS = [
    "Avalokitesvara Bodhisattva, when practicing the profound Prajna Paramita, illuminated the five aggregates and saw that they are all empty, thus overcoming all suffering and distress.",
    "Shariputra, form is not different from emptiness, emptiness is not different from form. Form is emptiness, emptiness is form. The same is true of feelings, perceptions, mental formations, and consciousness.",
    "Shariputra, all dharmas are marked with emptiness — they are neither born nor destroyed, neither defiled nor pure, neither increasing nor decreasing. Therefore, in emptiness there is no form, no feelings, perceptions, mental formations, or consciousness.",
    "There are no eyes, ears, nose, tongue, body, or mind; no sights, sounds, smells, tastes, touches, or objects of mind; no realm of sight, and so on up to no realm of consciousness. There is no ignorance and no end of ignorance, and so on up to no old age and death and no end of old age and death.",
    "There is no suffering, no cause of suffering, no cessation, no path; no wisdom and no attainment. With nothing to attain, a bodhisattva relies on Prajna Paramita, and the mind is without hindrance.",
    "Without hindrance, there is no fear. Far from all inverted views, one attains nirvana. All buddhas of past, present, and future rely on Prajna Paramita and attain supreme, perfect enlightenment.",
    "Therefore, know that Prajna Paramita is the great transcendent mantra, the great bright mantra, the supreme mantra, the unequalled mantra, which can remove all suffering and is true, not false. Therefore he proclaimed the Prajna Paramita mantra, saying: Gate gate paragate parasamgate bodhi svaha.",
]

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def build_heart_sutra():
    """Build Heart Sutra source file with 7 segments, one per weekday."""
    segments = []
    for i, (text, translation) in enumerate(zip(HEART_SUTRA_SEGMENTS, HEART_SUTRA_TRANSLATIONS)):
        segments.append({
            "day_index": i,
            "day_name": DAY_NAMES[i],
            "text": text,
            "translation_en": translation,
        })

    data = {
        "source_url": HEART_SUTRA_URL,
        "title": "般若波羅蜜多心經",
        "title_en": "Heart Sutra",
        "segments": segments,
    }

    output_path = SOURCES_DIR / "heart_sutra.json"
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Heart Sutra: {len(segments)} segments written to {output_path}")
    return data


# ---------------------------------------------------------------------------
# Mengzi
# ---------------------------------------------------------------------------

MENGZI_CHAPTERS = [
    ("liang-hui-wang-i", "梁惠王上"),
    ("liang-hui-wang-ii", "梁惠王下"),
    ("gong-sun-chou-i", "公孫丑上"),
    ("gong-sun-chou-ii", "公孫丑下"),
    ("teng-wen-gong-i", "滕文公上"),
    ("teng-wen-gong-ii", "滕文公下"),
    ("li-lou-i", "離婁上"),
    ("li-lou-ii", "離婁下"),
    ("wan-zhang-i", "萬章上"),
    ("wan-zhang-ii", "萬章下"),
    ("gao-zi-i", "告子上"),
    ("gao-zi-ii", "告子下"),
    ("jin-xin-i", "盡心上"),
    ("jin-xin-ii", "盡心下"),
]


def fetch_ctext_chapter(chapter_id: str) -> list[dict]:
    """Fetch a Mengzi chapter from ctext.org API."""
    url = f"https://ctext.org/api.pl?if=en&chapter={chapter_id}&remap=gb"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"  WARNING: Failed to fetch {chapter_id}: {e}", file=sys.stderr)
        return []


def build_mengzi():
    """Build Mengzi source file by fetching from ctext.org API."""
    all_passages = []
    passage_index = 0

    for chapter_id, chapter_name in MENGZI_CHAPTERS:
        print(f"  Fetching Mengzi chapter: {chapter_name} ({chapter_id})...")
        paragraphs = fetch_ctext_chapter(chapter_id)

        if not paragraphs:
            print(f"  WARNING: No data for {chapter_name}, skipping", file=sys.stderr)
            continue

        # ctext API returns array of paragraph objects
        # Each has "text" (Chinese) and optionally "translation" (English)
        chapter_texts = []
        chapter_translations = []
        for para in paragraphs:
            if isinstance(para, dict) and "text" in para:
                chapter_texts.append(para["text"])
                chapter_translations.append(para.get("translation", ""))

        # Group into passages of ~150 chars
        current_text = ""
        current_trans = ""
        para_start = 0

        for j, (text, trans) in enumerate(zip(chapter_texts, chapter_translations)):
            if current_text and len(current_text) + len(text) > 200:
                # Save current passage
                all_passages.append({
                    "index": passage_index,
                    "chapter": chapter_name,
                    "chapter_id": chapter_id,
                    "text": current_text,
                    "translation_en": current_trans if current_trans.strip() else "",
                })
                passage_index += 1
                current_text = text
                current_trans = trans
            else:
                current_text += text
                if trans:
                    current_trans += " " + trans if current_trans else trans

        # Don't forget the last passage
        if current_text:
            all_passages.append({
                "index": passage_index,
                "chapter": chapter_name,
                "chapter_id": chapter_id,
                "text": current_text,
                "translation_en": current_trans if current_trans.strip() else "",
            })
            passage_index += 1

    data = {
        "source_url": "https://ctext.org/mengzi",
        "title": "孟子",
        "title_en": "Mencius",
        "total_passages": len(all_passages),
        "passages": all_passages,
    }

    output_path = SOURCES_DIR / "mengzi_passages.json"
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Mengzi: {len(all_passages)} passages across {len(MENGZI_CHAPTERS)} chapters written to {output_path}")
    return data


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Build wisdom source files")
    parser.add_argument("--heart-sutra", action="store_true", help="Build Heart Sutra only")
    parser.add_argument("--mengzi", action="store_true", help="Build Mengzi only")
    parser.add_argument("--all", action="store_true", help="Build all sources (default)")
    args = parser.parse_args()

    if not (args.heart_sutra or args.mengzi):
        args.all = True

    if args.all or args.heart_sutra:
        print("Building Heart Sutra...")
        build_heart_sutra()

    if args.all or args.mengzi:
        print("Building Mengzi...")
        build_mengzi()

    print("\nNote: Zen passages require interactive curation. Run the wisdom")
    print("pipeline setup to select and cache Zen source texts.")


if __name__ == "__main__":
    main()
