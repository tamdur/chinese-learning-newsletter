#!/usr/bin/env python3
"""Post-assembly validation for 今日讀報 pages.

Validates the assembled HTML for common issues across all page types,
plus page-type-specific checks.

Usage:
    python3 scripts/validate.py [--page-type newsletter|wisdom|obsessions]
    Defaults to --page-type newsletter.

Exit codes:
    0 = all checks pass
    1 = warnings only
    2 = hard failures
"""

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"

# Page-type to index file mapping
PAGE_INDEX = {
    "newsletter": DOCS / "index.html",
    "wisdom": DOCS / "wisdom.html",
    "obsessions": DOCS / "obsessions.html",
}

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


# ---------------------------------------------------------------------------
# Shared checks (all page types)
# ---------------------------------------------------------------------------

def check_simplified_chars(html: str, result: ValidationResult):
    """Check for simplified characters in content."""
    # Extract all Chinese content sections
    body_sections = re.findall(
        r'<div class="(?:article-body|section-body)-zh">(.*?)</div>', html, re.DOTALL
    )
    headlines = re.findall(
        r'<h2 class="(?:article-headline|section-title)">(.*?)</h2>', html, re.DOTALL
    )

    all_text = " ".join(body_sections + headlines)
    text_only = re.sub(r"<[^>]+>", "", all_text)

    found = set()
    for ch in text_only:
        if ch in SIMPLIFIED_CHARS:
            found.add(ch)

    if found:
        chars = "".join(sorted(found))
        result.error(f"Simplified characters found in content: {chars}")


def check_character_wrapping(html: str, result: ValidationResult):
    """Check that Chinese characters in content bodies are wrapped in <span class='c'>."""
    cjk_pattern = re.compile(r"[\u4e00-\u9fff]")

    body_sections = re.findall(
        r'<div class="(?:article-body|section-body)-zh">(.*?)</div>', html, re.DOTALL
    )
    headlines = re.findall(
        r'<h2 class="(?:article-headline|section-title)">(.*?)</h2>', html, re.DOTALL
    )

    for section in body_sections + headlines:
        stripped = re.sub(r'<span class="c">[^<]*</span>', "", section)
        stripped = re.sub(r"<[^>]+>", "", stripped)
        unwrapped = cjk_pattern.findall(stripped)
        unwrapped = [c for c in unwrapped if c not in "，。「」！？、：（）—"]
        if unwrapped:
            sample = "".join(unwrapped[:10])
            result.error(f"Unwrapped Chinese characters in content: {sample}...")


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


def check_navigation(html: str, page_type: str, result: ValidationResult):
    """Check that navigation links point to existing files."""
    prev_match = re.search(r'data-prev="([^"]+)"', html)
    if prev_match:
        prev_path = prev_match.group(1)
        full_path = DOCS / prev_path
        if not full_path.exists():
            result.error(f"Navigation data-prev points to non-existent file: {prev_path}")


def check_translation_toggles(html: str, result: ValidationResult):
    """Check that each content section has a translation toggle and hidden English section."""
    # Count content units (articles or sections)
    unit_count = len(re.findall(r'data-article-id="\d+"', html))
    if unit_count == 0:
        unit_count = len(re.findall(r'data-section="[^"]*"', html))

    toggle_count = html.count('class="translation-toggle"')
    en_count = len(re.findall(r'class="(?:article-body|section-body)-en"[^>]*hidden', html))

    if toggle_count != unit_count:
        result.warn(f"Translation toggle count ({toggle_count}) != content unit count ({unit_count})")
    if en_count != unit_count:
        result.warn(f"Hidden English section count ({en_count}) != content unit count ({unit_count})")


def check_mobile_glossary_popup(html: str, result: ValidationResult):
    """Check that the mobile tap-hold glossary popup infrastructure is intact."""
    if 'id="char-popup"' not in html:
        result.error("Mobile glossary: char-popup element missing")
    for elem_id in ("popup-char", "popup-zhuyin", "popup-def", "popup-close"):
        if f'id="{elem_id}"' not in html:
            result.error(f"Mobile glossary: {elem_id} element missing")

    if "GLOSSARY" not in html:
        result.error("Mobile glossary: GLOSSARY variable not found")

    if "findLongestMatch" not in html:
        result.error("Mobile glossary: findLongestMatch function missing from JS")

    for event in ("touchstart", "touchmove", "touchend"):
        if event not in html:
            result.error(f"Mobile glossary: {event} event handler missing from JS")

    if 'id="lookup-toggle"' not in html:
        result.error("Mobile glossary: lookup-toggle button missing")

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


# ---------------------------------------------------------------------------
# Page-type-specific checks
# ---------------------------------------------------------------------------

def check_newsletter(html: str, result: ValidationResult):
    """Newsletter-specific checks."""
    article_ids = re.findall(r'data-article-id="(\d+)"', html)
    if not article_ids:
        result.error("No articles found")
    elif len(article_ids) < 5:
        result.warn(f"Expected 5 articles, found {len(article_ids)}")


def check_wisdom(html: str, result: ValidationResult):
    """Wisdom-specific checks (placeholder for Phase 4)."""
    sections = re.findall(r'data-section="([^"]*)"', html)
    if len(sections) < 3:
        result.warn(f"Expected 3 wisdom sections, found {len(sections)}")


def check_obsessions(html: str, result: ValidationResult):
    """Obsessions-specific checks (placeholder for Phase 5)."""
    sections = re.findall(r'data-obsession-id="([^"]*)"', html)
    if not sections:
        result.warn("No obsession sections found")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Validate assembled page HTML")
    parser.add_argument("--page-type", choices=PAGE_INDEX.keys(), default="newsletter",
                        help="Page type to validate (default: newsletter)")
    args = parser.parse_args()

    page_type = args.page_type
    index_path = PAGE_INDEX[page_type]

    if not index_path.exists():
        print(f"ERROR: {index_path} does not exist", file=sys.stderr)
        sys.exit(2)

    html = index_path.read_text(encoding="utf-8")
    result = ValidationResult()

    # Shared checks
    check_simplified_chars(html, result)
    check_character_wrapping(html, result)
    check_glossary(html, result)
    check_navigation(html, page_type, result)
    check_translation_toggles(html, result)
    check_mobile_glossary_popup(html, result)
    check_essential_css(html, result)

    # Page-type-specific checks
    if page_type == "newsletter":
        check_newsletter(html, result)
    elif page_type == "wisdom":
        check_wisdom(html, result)
    elif page_type == "obsessions":
        check_obsessions(html, result)

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
