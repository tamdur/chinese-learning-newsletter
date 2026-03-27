#!/usr/bin/env python3
"""Post-assembly validation for the 今日讀報 newsletter.

Reads docs/index.html and checks for common issues:
- Simplified characters
- Unwrapped Chinese characters in article bodies
- Missing sections / incorrect structure
- GLOSSARY population
- Navigation integrity
- Mobile tap-hold glossary popup functionality

Exit codes:
    0 = all checks pass
    1 = warnings only
    2 = hard failures
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INDEX = REPO / "docs" / "index.html"
ARCHIVE = REPO / "docs" / "archive"

# Simplified-only characters (each has a distinct traditional form).
# Excludes dual-use characters that appear in both systems (面, 会, 没, 来, etc.)
SIMPLIFIED_CHARS = set(
    "国体学发时对让这说还经车长门问间关开"
    "书写认识东义习乡买产亲从众伤传伦"
    "华单卖厅历叶号团图场坏块声处备头"
    "夸奋妇实宝导层岁币师带帮广应张总态"
    "战拥择担据损换摇斗断旧条杂构标样"
    "桥检欢汇决沟灵独环现画盘"
    "码礼称竞笔节纪约红纸终编网虽蓝补观"
    "记设证评语请课谁调谈运过进远连选释铁链"
    "错钟钱键际随难题飞饭馆驾验鱼鸡"
)


class ValidationResult:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str):
        self.errors.append(msg)

    def warn(self, msg: str):
        self.warnings.append(msg)

    @property
    def exit_code(self) -> int:
        if self.errors:
            return 2
        if self.warnings:
            return 1
        return 0


def check_simplified_chars(html: str, result: ValidationResult):
    """Check for simplified characters in article content."""
    # Extract article body and headline text (strip tags)
    article_sections = re.findall(
        r'<div class="article-body-zh">(.*?)</div>', html, re.DOTALL
    )
    headlines = re.findall(
        r'<h2 class="article-headline">(.*?)</h2>', html, re.DOTALL
    )

    all_text = " ".join(article_sections + headlines)
    # Strip HTML tags to get raw text
    text_only = re.sub(r"<[^>]+>", "", all_text)

    found = set()
    for ch in text_only:
        if ch in SIMPLIFIED_CHARS:
            found.add(ch)

    if found:
        chars = "".join(sorted(found))
        result.error(f"Simplified characters found in article content: {chars}")


def check_character_wrapping(html: str, result: ValidationResult):
    """Check that Chinese characters in article bodies are wrapped in <span class='c'>."""
    # CJK Unified Ideographs range
    cjk_pattern = re.compile(r"[\u4e00-\u9fff]")

    article_bodies = re.findall(
        r'<div class="article-body-zh">(.*?)</div>', html, re.DOTALL
    )
    headlines = re.findall(
        r'<h2 class="article-headline">(.*?)</h2>', html, re.DOTALL
    )

    for section in article_bodies + headlines:
        # Remove all <span class="c">X</span> occurrences
        stripped = re.sub(r'<span class="c">[^<]*</span>', "", section)
        # Remove remaining HTML tags
        stripped = re.sub(r"<[^>]+>", "", stripped)
        # Check for remaining CJK characters (punctuation is OK)
        unwrapped = cjk_pattern.findall(stripped)
        # Filter out punctuation that looks like CJK
        unwrapped = [c for c in unwrapped if c not in "，。「」！？、：（）—"]
        if unwrapped:
            sample = "".join(unwrapped[:10])
            result.error(f"Unwrapped Chinese characters in article content: {sample}...")


def check_article_count(html: str, result: ValidationResult):
    """Check that at least 1 article is present."""
    article_ids = re.findall(r'data-article-id="(\d+)"', html)
    if not article_ids:
        result.error("No articles found")
    elif len(article_ids) < 5:
        result.warn(f"Expected 5 articles, found {len(article_ids)}")


def check_glossary(html: str, result: ValidationResult):
    """Check that GLOSSARY is populated (not empty)."""
    m = re.search(r"const GLOSSARY = ({.*?});", html, re.DOTALL)
    if not m:
        result.error("GLOSSARY script block not found")
        return

    glossary_str = m.group(1)
    if glossary_str.strip() in ("{}", "{ }"):
        result.error("GLOSSARY is empty")
    elif len(glossary_str) < 100:
        result.warn(f"GLOSSARY seems small ({len(glossary_str)} chars)")


def check_navigation(html: str, result: ValidationResult):
    """Check that navigation links point to existing files."""
    prev_match = re.search(r'data-prev="([^"]+)"', html)
    if prev_match:
        prev_path = prev_match.group(1)
        full_path = REPO / "docs" / prev_path
        if not full_path.exists():
            result.error(f"Navigation data-prev points to non-existent file: {prev_path}")


def check_translation_toggles(html: str, result: ValidationResult):
    """Check that each article has a translation toggle and hidden English section."""
    article_count = len(re.findall(r'data-article-id="\d+"', html))
    toggle_count = html.count('class="translation-toggle"')
    en_count = len(re.findall(r'class="article-body-en"[^>]*hidden', html))

    if toggle_count != article_count:
        result.warn(f"Translation toggle count ({toggle_count}) != article count ({article_count})")
    if en_count != article_count:
        result.warn(f"Hidden English section count ({en_count}) != article count ({article_count})")


def check_mobile_glossary_popup(html: str, result: ValidationResult):
    """Check that the mobile tap-hold glossary popup infrastructure is intact.

    Validates:
    1. char-popup div exists with required child elements
    2. GLOSSARY is referenced in JS
    3. findLongestMatch function exists in JS
    4. Touch event handlers (touchstart, touchend, touchmove) are present
    5. lookup-toggle button exists
    6. positionPopup / showPopup functions exist
    """
    # 1. Popup container structure
    if 'id="char-popup"' not in html:
        result.error("Mobile glossary: char-popup element missing")
    for elem_id in ("popup-char", "popup-zhuyin", "popup-def", "popup-close"):
        if f'id="{elem_id}"' not in html:
            result.error(f"Mobile glossary: {elem_id} element missing")

    # 2. GLOSSARY reference in JS
    if "GLOSSARY" not in html:
        result.error("Mobile glossary: GLOSSARY variable not found")

    # 3. findLongestMatch function
    if "findLongestMatch" not in html:
        result.error("Mobile glossary: findLongestMatch function missing from JS")

    # 4. Touch event handlers
    for event in ("touchstart", "touchmove", "touchend"):
        if event not in html:
            result.error(f"Mobile glossary: {event} event handler missing from JS")

    # 5. Lookup toggle button
    if 'id="lookup-toggle"' not in html:
        result.error("Mobile glossary: lookup-toggle button missing")

    # 6. Popup display functions
    for fn in ("positionPopup", "showPopup"):
        if fn not in html:
            result.error(f"Mobile glossary: {fn} function missing from JS")


def check_essential_css(html: str, result: ValidationResult):
    """Check that essential CSS classes for mobile popup are present."""
    essential = [
        ".char-popup",
        ".char-popup.visible",
        ".char-popup-char",
        ".char-popup-zhuyin",
        ".char-popup-def",
        ".lookup-toggle",
        "@media (pointer: coarse)",
        ".c.touch-active",
    ]
    for selector in essential:
        if selector not in html:
            result.warn(f"Mobile glossary CSS: '{selector}' rule missing")


def main():
    if not INDEX.exists():
        print("ERROR: docs/index.html does not exist", file=sys.stderr)
        sys.exit(2)

    html = INDEX.read_text(encoding="utf-8")
    result = ValidationResult()

    check_simplified_chars(html, result)
    check_character_wrapping(html, result)
    check_article_count(html, result)
    check_glossary(html, result)
    check_navigation(html, result)
    check_translation_toggles(html, result)
    check_mobile_glossary_popup(html, result)
    check_essential_css(html, result)

    # Print results
    if result.errors:
        print(f"FAIL — {len(result.errors)} error(s):")
        for e in result.errors:
            print(f"  ERROR: {e}")
    if result.warnings:
        print(f"WARN — {len(result.warnings)} warning(s):")
        for w in result.warnings:
            print(f"  WARN: {w}")
    if not result.errors and not result.warnings:
        print("PASS — all checks passed")

    sys.exit(result.exit_code)


if __name__ == "__main__":
    main()
