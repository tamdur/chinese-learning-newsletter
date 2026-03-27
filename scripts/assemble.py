#!/usr/bin/env python3
"""Deterministic HTML assembly for the 今日讀報 newsletter.

Reads checkpoint files from data/pipeline/ and the template from
templates/newsletter.html, then constructs a complete standalone HTML file.
Handles archiving the previous issue and patching navigation links.

Usage:
    python3 scripts/assemble.py [--date YYYY-MM-DD]
    Defaults to today in America/Chicago.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# ---------------------------------------------------------------------------
# Paths (relative to repo root)
# ---------------------------------------------------------------------------

REPO = Path(__file__).resolve().parent.parent
TEMPLATE = REPO / "templates" / "newsletter.html"
PIPELINE = REPO / "data" / "pipeline"
DOCS = REPO / "docs"
ARCHIVE = DOCS / "archive"
INDEX = DOCS / "index.html"

CHECKPOINT_FILES = {
    "articles": PIPELINE / "articles.json",
    "translations": PIPELINE / "translations.json",
    "glossary": PIPELINE / "glossary.json",
}


def load_json(path: Path) -> dict | list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Template extraction
# ---------------------------------------------------------------------------

def extract_css(html: str) -> str:
    """Extract content between <style> and </style>."""
    m = re.search(r"<style>(.*?)</style>", html, re.DOTALL)
    if not m:
        raise RuntimeError("Could not extract <style> from template")
    return m.group(1)


def extract_main_js(html: str) -> str:
    """Extract the main IIFE <script> block (the second one, after GLOSSARY)."""
    scripts = re.findall(r"<script>(.*?)</script>", html, re.DOTALL)
    if len(scripts) < 2:
        raise RuntimeError("Could not find main JS IIFE in template")
    return scripts[1]


# ---------------------------------------------------------------------------
# Archive management
# ---------------------------------------------------------------------------

def list_archive_files() -> list[str]:
    """Return sorted list of archive HTML filenames (date order, suffix order)."""
    if not ARCHIVE.exists():
        return []
    pattern = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:-(\d+))?\.html$")
    files = []
    for f in ARCHIVE.iterdir():
        m = pattern.match(f.name)
        if m:
            date_str = m.group(1)
            suffix = int(m.group(2)) if m.group(2) else 0
            files.append((date_str, suffix, f.name))
    files.sort(key=lambda x: (x[0], x[1]))
    return [f[2] for f in files]


def determine_archive_filename(old_date: str) -> str:
    """Determine the archive filename for the old issue, handling same-day suffixes."""
    base = f"{old_date}.html"
    if not (ARCHIVE / base).exists():
        return base

    suffix = 2
    while (ARCHIVE / f"{old_date}-{suffix}.html").exists():
        suffix += 1
    return f"{old_date}-{suffix}.html"


def extract_date_from_html(html: str) -> str | None:
    """Extract date from <p class="date">YYYY-MM-DD</p>."""
    m = re.search(r'<p class="date">(\d{4}-\d{2}-\d{2})</p>', html)
    return m.group(1) if m else None


def fix_paths_for_archive(html: str) -> str:
    """Rewrite nav link paths for a file moving from docs/ into docs/archive/."""
    # data-prev="archive/X.html" -> data-prev="X.html"
    html = html.replace('data-prev="archive/', 'data-prev="')
    # href="archive/X.html" in nav-prev -> href="X.html"
    html = re.sub(
        r'href="archive/([^"]*)" class="nav-link nav-prev"',
        r'href="\1" class="nav-link nav-prev"',
        html,
    )
    return html


def patch_next_link(html: str, next_target: str) -> str:
    """Set data-next and unhide the next link in a nav bar."""
    html = re.sub(r'data-next="[^"]*"', f'data-next="{next_target}"', html)
    html = html.replace(
        'href="" class="nav-link nav-next" hidden',
        f'href="{next_target}" class="nav-link nav-next"',
    )
    # Also handle case where href already has a value
    html = re.sub(
        r'href="[^"]*" class="nav-link nav-next"',
        f'href="{next_target}" class="nav-link nav-next"',
        html,
    )
    return html


def archive_old_issue(today: str) -> str | None:
    """Archive the current docs/index.html. Returns the archive filename or None."""
    if not INDEX.exists():
        return None

    old_html = INDEX.read_text(encoding="utf-8")
    old_date = extract_date_from_html(old_html)
    if not old_date:
        print("WARNING: Could not extract date from old index.html, skipping archive", file=sys.stderr)
        return None

    ARCHIVE.mkdir(parents=True, exist_ok=True)

    archive_name = determine_archive_filename(old_date)
    archive_path = ARCHIVE / archive_name

    # Fix relative paths for archive location
    archived_html = fix_paths_for_archive(old_html)
    archive_path.write_text(archived_html, encoding="utf-8")

    # Patch newly archived file: set data-next to ../index.html
    archived_html = archive_path.read_text(encoding="utf-8")
    archived_html = patch_next_link(archived_html, "../index.html")
    archive_path.write_text(archived_html, encoding="utf-8")

    # Patch previous archive file's next link to point to newly archived file
    all_archives = list_archive_files()
    if len(all_archives) >= 2:
        # Find the file just before the newly archived one
        idx = all_archives.index(archive_name)
        if idx > 0:
            prev_archive = all_archives[idx - 1]
            prev_path = ARCHIVE / prev_archive
            prev_html = prev_path.read_text(encoding="utf-8")
            if '<nav class="issue-nav"' in prev_html:
                prev_html = patch_next_link(prev_html, archive_name)
                prev_path.write_text(prev_html, encoding="utf-8")

    print(f"Archived old issue ({old_date}) to docs/archive/{archive_name}")
    return archive_name


# ---------------------------------------------------------------------------
# HTML construction
# ---------------------------------------------------------------------------

def build_article_html(article: dict, translation: str, article_id: int) -> str:
    """Build one <article> block."""
    return f"""<article class="article" data-article-id="{article_id}">
  <h2 class="article-headline">{article['headline_html']}</h2>
  <p class="article-source">來源：{article['source_label']}</p>

  <div class="article-body-zh">
    {article['body_html']}
  </div>

  <button class="translation-toggle" type="button">顯示翻譯 Show Translation</button>

  <div class="article-body-en" hidden>
    {translation}
  </div>
</article>"""


def build_nav(archive_files: list[str]) -> str:
    """Build the navigation bar HTML."""
    if not archive_files:
        return ""
    most_recent = archive_files[-1]
    return f"""<nav class="issue-nav" data-prev="archive/{most_recent}" data-next="">
  <a href="archive/{most_recent}" class="nav-link nav-prev">← 上一期</a>
  <span class="nav-spacer"></span>
  <a href="" class="nav-link nav-next" hidden>下一期 →</a>
</nav>"""


def build_newsletter(today: str, articles: list, translations: list,
                     glossary: dict, css: str, main_js: str,
                     archive_files: list[str]) -> str:
    """Construct the complete newsletter HTML."""

    # Articles with <hr> separators
    article_blocks = []
    for i, (article, translation) in enumerate(zip(articles, translations)):
        article_blocks.append(build_article_html(article, translation, i + 1))
    articles_html = "\n\n<hr>\n\n".join(article_blocks)

    # Navigation
    nav_html = build_nav(archive_files)

    # Glossary JSON
    glossary_json = json.dumps(glossary, ensure_ascii=False, separators=(",", ":"))

    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>今日讀報 — {today}</title>
  <style>{css}
  </style>
</head>
<body>

<header class="newsletter-header">
  <h1>今日讀報</h1>
  <p class="date">{today}</p>
</header>

{nav_html}

<main>

{articles_html}

</main>

<div class="toolbar" id="toolbar">
  <button id="lookup-toggle" class="lookup-toggle" type="button">查詢模式 OFF</button>
</div>

<footer>
  <p>今日讀報 — 以 Claude Code 製作</p>
</footer>

<div class="char-popup" id="char-popup" role="tooltip">
  <button class="char-popup-close" id="popup-close" aria-label="Close">&times;</button>
  <div class="char-popup-char" id="popup-char"></div>
  <div class="char-popup-zhuyin" id="popup-zhuyin"></div>
  <div class="char-popup-def" id="popup-def"></div>
</div>

<script>
const GLOSSARY = {glossary_json};
</script>

<script>
{main_js}
</script>

</body>
</html>
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Assemble newsletter HTML")
    parser.add_argument("--date", help="Issue date (YYYY-MM-DD), defaults to today in America/Chicago")
    args = parser.parse_args()

    if args.date:
        today = args.date
    else:
        tz = ZoneInfo("America/Chicago")
        today = datetime.now(tz).strftime("%Y-%m-%d")

    # Validate checkpoint files exist
    missing = []
    for name, path in CHECKPOINT_FILES.items():
        if not path.exists():
            missing.append(str(path))
    if missing:
        print(f"ERROR: Missing checkpoint files:\n  " + "\n  ".join(missing), file=sys.stderr)
        sys.exit(1)

    # Load checkpoint data
    articles = load_json(CHECKPOINT_FILES["articles"])
    translations = load_json(CHECKPOINT_FILES["translations"])
    glossary = load_json(CHECKPOINT_FILES["glossary"])

    # Validate article count
    if len(articles) == 0:
        print("ERROR: No articles found", file=sys.stderr)
        sys.exit(1)
    if len(translations) != len(articles):
        print(f"WARNING: Article count ({len(articles)}) != translation count ({len(translations)})", file=sys.stderr)

    # Load template
    template_html = TEMPLATE.read_text(encoding="utf-8")
    css = extract_css(template_html)
    main_js = extract_main_js(template_html)

    # Archive the old issue
    archive_old_issue(today)

    # Get current archive listing (after archiving)
    archive_files = list_archive_files()

    # Build the newsletter
    html = build_newsletter(today, articles, translations,
                            glossary, css, main_js, archive_files)

    # Write new index.html
    DOCS.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(html, encoding="utf-8")

    # Print summary
    print(f"Newsletter assembled for {today}")
    print(f"  Articles: {len(articles)}")
    print(f"  Glossary entries: {len(glossary)}")
    print(f"  Written to: {INDEX}")


if __name__ == "__main__":
    main()
