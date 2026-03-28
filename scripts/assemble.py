#!/usr/bin/env python3
"""Page-type-aware HTML assembly for 今日讀報.

Reads checkpoint files from data/pipeline/ and shared/page-specific templates,
then constructs a complete standalone HTML file. Handles archiving the previous
issue and patching navigation links.

Usage:
    python3 scripts/assemble.py [--page-type newsletter|wisdom|obsessions] [--date YYYY-MM-DD]
    Defaults to --page-type newsletter and today in America/Chicago.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# ---------------------------------------------------------------------------
# Paths (relative to repo root)
# ---------------------------------------------------------------------------

REPO = Path(__file__).resolve().parent.parent
TEMPLATES = REPO / "templates"
SHARED_CSS = TEMPLATES / "_shared.css"
SHARED_JS = TEMPLATES / "_shared.js"
PIPELINE = REPO / "data" / "pipeline"
DOCS = REPO / "docs"

# Page-type configuration: index file, archive dir, page title
PAGE_CONFIG = {
    "newsletter": {
        "index": DOCS / "index.html",
        "archive": DOCS / "archive",
        "template": TEMPLATES / "newsletter.html",
        "title": "今日讀報",
        "footer": "今日讀報 — 以 Claude Code 製作",
    },
    "wisdom": {
        "index": DOCS / "wisdom.html",
        "archive": DOCS / "archive" / "wisdom",
        "template": TEMPLATES / "wisdom.html",
        "title": "每日智慧",
        "footer": "每日智慧 — 以 Claude Code 製作",
    },
    "obsessions": {
        "index": DOCS / "obsessions.html",
        "archive": DOCS / "archive" / "obsessions",
        "template": TEMPLATES / "obsessions.html",
        "title": "深度專題",
        "footer": "深度專題 — 以 Claude Code 製作",
    },
}

CHECKPOINT_FILES = {
    "articles": PIPELINE / "articles.json",
    "translations": PIPELINE / "translations.json",
    "glossary": PIPELINE / "glossary.json",
}

# Site navigation pages (order matters for display)
SITE_NAV_PAGES = [
    ("newsletter", "index.html", "今日讀報"),
    ("wisdom", "wisdom.html", "每日智慧"),
    ("obsessions", "obsessions.html", "深度專題"),
]


def load_json(path: Path) -> dict | list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Shared asset loading
# ---------------------------------------------------------------------------

def read_shared_css() -> str:
    """Read the shared CSS file."""
    return SHARED_CSS.read_text(encoding="utf-8")


def read_shared_js() -> str:
    """Read the shared JS file."""
    return SHARED_JS.read_text(encoding="utf-8")


def read_page_css(page_type: str) -> str:
    """Read page-specific CSS from the page template's <style> block, if any."""
    template_path = PAGE_CONFIG[page_type]["template"]
    if not template_path.exists():
        return ""
    html = template_path.read_text(encoding="utf-8")
    m = re.search(r"<style>(.*?)</style>", html, re.DOTALL)
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# Site navigation
# ---------------------------------------------------------------------------

def build_site_nav(current_page: str, base_url: str = "") -> str:
    """Build the site-wide navigation bar. Always shows all page links.

    base_url is prepended to hrefs so links work from archive subdirectories.
    Top-level pages pass "" (default); archive fixup rewrites to relative prefix.
    """
    links = []
    for page_type, href, label in SITE_NAV_PAGES:
        active = " active" if page_type == current_page else ""
        links.append(f'  <a href="{base_url}{href}" class="site-nav-link{active}">{label}</a>')

    return '<nav class="site-nav">\n' + "\n".join(links) + "\n</nav>"


# ---------------------------------------------------------------------------
# Archive management (parameterized by page type)
# ---------------------------------------------------------------------------

def list_archive_files(archive_dir: Path) -> list[str]:
    """Return sorted list of archive HTML filenames (date order, suffix order)."""
    if not archive_dir.exists():
        return []
    pattern = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:-(\d+))?\.html$")
    files = []
    for f in archive_dir.iterdir():
        m = pattern.match(f.name)
        if m:
            date_str = m.group(1)
            suffix = int(m.group(2)) if m.group(2) else 0
            files.append((date_str, suffix, f.name))
    files.sort(key=lambda x: (x[0], x[1]))
    return [f[2] for f in files]


def determine_archive_filename(archive_dir: Path, old_date: str) -> str:
    """Determine the archive filename for the old issue, handling same-day suffixes."""
    base = f"{old_date}.html"
    if not (archive_dir / base).exists():
        return base

    suffix = 2
    while (archive_dir / f"{old_date}-{suffix}.html").exists():
        suffix += 1
    return f"{old_date}-{suffix}.html"


def extract_date_from_html(html: str) -> str | None:
    """Extract date from <p class="date">YYYY-MM-DD</p>."""
    m = re.search(r'<p class="date">(\d{4}-\d{2}-\d{2})</p>', html)
    return m.group(1) if m else None


def fix_paths_for_archive(html: str, page_type: str) -> str:
    """Rewrite nav link paths for a file moving into its archive directory."""
    if page_type == "newsletter":
        # Newsletter archives live in docs/archive/ (one level deep)
        # data-prev="archive/X.html" -> data-prev="X.html"
        html = html.replace('data-prev="archive/', 'data-prev="')
        html = re.sub(
            r'href="archive/([^"]*)" class="nav-link nav-prev"',
            r'href="\1" class="nav-link nav-prev"',
            html,
        )
        # Site nav: "index.html" -> "../index.html", etc.
        for _, href, _ in SITE_NAV_PAGES:
            html = html.replace(f'href="{href}" class="site-nav-link', f'href="../{href}" class="site-nav-link')
    else:
        # Sub-page archives live in docs/archive/{page_type}/ (two levels deep)
        # data-prev="archive/{type}/X.html" -> data-prev="X.html"
        archive_prefix = f"archive/{page_type}/"
        html = html.replace(f'data-prev="{archive_prefix}', 'data-prev="')
        html = re.sub(
            rf'href="{archive_prefix}([^"]*)" class="nav-link nav-prev"',
            r'href="\1" class="nav-link nav-prev"',
            html,
        )
        # Site nav: "index.html" -> "../../index.html", etc.
        for _, href, _ in SITE_NAV_PAGES:
            html = html.replace(f'href="{href}" class="site-nav-link', f'href="../../{href}" class="site-nav-link')
    return html


def patch_next_link(html: str, next_target: str) -> str:
    """Set data-next and unhide the next link in a nav bar."""
    html = re.sub(r'data-next="[^"]*"', f'data-next="{next_target}"', html)
    html = html.replace(
        'href="" class="nav-link nav-next" hidden',
        f'href="{next_target}" class="nav-link nav-next"',
    )
    html = re.sub(
        r'href="[^"]*" class="nav-link nav-next"',
        f'href="{next_target}" class="nav-link nav-next"',
        html,
    )
    return html


def archive_old_issue(page_type: str, today: str) -> str | None:
    """Archive the current page's index file. Returns the archive filename or None."""
    config = PAGE_CONFIG[page_type]
    index_path = config["index"]
    archive_dir = config["archive"]

    if not index_path.exists():
        return None

    old_html = index_path.read_text(encoding="utf-8")
    old_date = extract_date_from_html(old_html)
    if not old_date:
        print(f"WARNING: Could not extract date from old {index_path.name}, skipping archive", file=sys.stderr)
        return None

    archive_dir.mkdir(parents=True, exist_ok=True)

    archive_name = determine_archive_filename(archive_dir, old_date)
    archive_path = archive_dir / archive_name

    # Fix relative paths for archive location
    archived_html = fix_paths_for_archive(old_html, page_type)

    # If the page has no issue nav (first-ever issue), inject one after the header
    if '<nav class="issue-nav"' not in archived_html:
        empty_nav = """<nav class="issue-nav" data-prev="" data-next="">
  <a href="" class="nav-link nav-prev" hidden>← 上一期</a>
  <span class="nav-spacer"></span>
  <a href="" class="nav-link nav-next" hidden>下一期 →</a>
</nav>"""
        archived_html = archived_html.replace("</header>\n\n\n\n<main>",
                                              f"</header>\n\n{empty_nav}\n\n<main>")
        # Fallback: if exact header pattern not found, try before <main>
        if '<nav class="issue-nav"' not in archived_html:
            archived_html = archived_html.replace("<main>", f"{empty_nav}\n\n<main>")

    archive_path.write_text(archived_html, encoding="utf-8")

    # Patch newly archived file: set data-next to parent index
    archived_html = archive_path.read_text(encoding="utf-8")
    if page_type == "newsletter":
        next_target = "../index.html"
    else:
        next_target = f"../../{config['index'].name}"
    archived_html = patch_next_link(archived_html, next_target)
    archive_path.write_text(archived_html, encoding="utf-8")

    # Patch previous archive file's next link
    all_archives = list_archive_files(archive_dir)
    if len(all_archives) >= 2:
        idx = all_archives.index(archive_name)
        if idx > 0:
            prev_archive = all_archives[idx - 1]
            prev_path = archive_dir / prev_archive
            prev_html = prev_path.read_text(encoding="utf-8")
            if '<nav class="issue-nav"' in prev_html:
                prev_html = patch_next_link(prev_html, archive_name)
                prev_path.write_text(prev_html, encoding="utf-8")

    print(f"Archived old issue ({old_date}) to {archive_path.relative_to(REPO)}")
    return archive_name


# ---------------------------------------------------------------------------
# Issue navigation (prev/next within page type)
# ---------------------------------------------------------------------------

def build_issue_nav(page_type: str, archive_dir: Path, archive_files: list[str]) -> str:
    """Build the prev/next navigation bar HTML for a page type."""
    if not archive_files:
        return ""

    config = PAGE_CONFIG[page_type]
    most_recent = archive_files[-1]

    if page_type == "newsletter":
        prev_href = f"archive/{most_recent}"
    else:
        prev_href = f"archive/{page_type}/{most_recent}"

    return f"""<nav class="issue-nav" data-prev="{prev_href}" data-next="">
  <a href="{prev_href}" class="nav-link nav-prev">← 上一期</a>
  <span class="nav-spacer"></span>
  <a href="" class="nav-link nav-next" hidden>下一期 →</a>
</nav>"""


# ---------------------------------------------------------------------------
# Content unit builder (shared across page types)
# ---------------------------------------------------------------------------

def build_content_unit_html(unit: dict, translation: str, unit_id: int) -> str:
    """Build one <article> block for a content unit."""
    source_line = ""
    if unit.get("source_label"):
        source_line = f'\n  <p class="article-source">{unit["source_label"]}</p>'

    return f"""<article class="article" data-article-id="{unit_id}">
  <h2 class="article-headline">{unit['headline_html']}</h2>{source_line}

  <div class="article-body-zh">
    {unit['body_html']}
  </div>

  <button class="translation-toggle" type="button">顯示翻譯 Show Translation</button>

  <div class="article-body-en" hidden>
    {translation}
  </div>
</article>"""


# ---------------------------------------------------------------------------
# Page-type builders
# ---------------------------------------------------------------------------

def build_page_shell(today: str, page_type: str, site_nav: str, issue_nav: str,
                     main_content: str, glossary: dict, shared_css: str,
                     page_css: str, shared_js: str) -> str:
    """Build the complete HTML page shell shared by all page types."""
    config = PAGE_CONFIG[page_type]
    glossary_json = json.dumps(glossary, ensure_ascii=False, separators=(",", ":"))

    # Combine CSS
    css = shared_css
    if page_css.strip():
        css += "\n\n    /* --- Page-specific CSS --- */\n" + page_css

    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{config['title']} — {today}</title>
  <style>
{css}
  </style>
</head>
<body>

{site_nav}

<header class="page-header">
  <h1>{config['title']}</h1>
  <p class="date">{today}</p>
</header>

{issue_nav}

<main>

{main_content}

</main>

<div class="toolbar" id="toolbar">
  <button id="lookup-toggle" class="lookup-toggle" type="button">查詢模式 OFF</button>
</div>

<footer>
  <p>{config['footer']}</p>
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
{shared_js}
</script>

</body>
</html>
"""


def build_newsletter_content(articles: list, translations: list) -> str:
    """Build the <main> inner content for the newsletter page."""
    blocks = []
    for i, (article, translation) in enumerate(zip(articles, translations)):
        blocks.append(build_content_unit_html(article, translation, i + 1))
    return "\n\n<hr>\n\n".join(blocks)


def build_wisdom_section_html(unit: dict, translation: str, section_id: str) -> str:
    """Build one <section class="wisdom-section"> block."""
    source_line = ""
    if unit.get("source_label"):
        source_line = f'\n  <p class="article-source">{unit["source_label"]}</p>'

    return f"""<section class="wisdom-section" data-section="{section_id}">
  <h2 class="section-title">{unit['headline_html']}</h2>{source_line}

  <div class="section-body-zh">
    {unit['body_html']}
  </div>

  <button class="translation-toggle" type="button">顯示翻譯 Show Translation</button>

  <div class="section-body-en" hidden>
    {translation}
  </div>
</section>"""


def build_wisdom_content(articles: list, translations: list) -> str:
    """Build the <main> inner content for the wisdom page."""
    section_ids = ["heart-sutra", "mengzi", "zen"]
    blocks = []
    for i, (article, translation) in enumerate(zip(articles, translations)):
        sid = section_ids[i] if i < len(section_ids) else f"section-{i}"
        blocks.append(build_wisdom_section_html(article, translation, sid))
    return "\n\n<hr>\n\n".join(blocks)


def build_obsession_section_html(unit: dict, translation: str, obsession_id: str) -> str:
    """Build one <section class="obsession-section"> block."""
    source_line = ""
    if unit.get("source_label"):
        source_line = f'\n  <p class="article-source">{unit["source_label"]}</p>'

    return f"""<section class="obsession-section" data-obsession-id="{obsession_id}">
  <h2 class="section-title">{unit['headline_html']}</h2>{source_line}

  <div class="section-body-zh">
    {unit['body_html']}
  </div>

  <button class="translation-toggle" type="button">顯示翻譯 Show Translation</button>

  <div class="section-body-en" hidden>
    {translation}
  </div>
</section>"""


def build_obsessions_content(articles: list, translations: list) -> str:
    """Build the <main> inner content for the obsessions page."""
    blocks = []
    for i, (article, translation) in enumerate(zip(articles, translations)):
        obsession_id = article.get("obsession_id", f"obsession-{i}")
        blocks.append(build_obsession_section_html(article, translation, obsession_id))
    return "\n\n<hr>\n\n".join(blocks)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Assemble page HTML")
    parser.add_argument("--page-type", choices=PAGE_CONFIG.keys(), default="newsletter",
                        help="Page type to assemble (default: newsletter)")
    parser.add_argument("--date", help="Issue date (YYYY-MM-DD), defaults to today in America/Chicago")
    args = parser.parse_args()

    page_type = args.page_type
    config = PAGE_CONFIG[page_type]

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

    # Validate content unit count
    if len(articles) == 0:
        print("ERROR: No content units found", file=sys.stderr)
        sys.exit(1)
    if len(translations) != len(articles):
        print(f"WARNING: Content unit count ({len(articles)}) != translation count ({len(translations)})", file=sys.stderr)

    # Load shared assets
    shared_css = read_shared_css()
    shared_js = read_shared_js()
    page_css = read_page_css(page_type)

    # Archive the old issue
    archive_old_issue(page_type, today)

    # Get current archive listing (after archiving)
    archive_files = list_archive_files(config["archive"])

    # Build navigation
    site_nav = build_site_nav(page_type)
    issue_nav = build_issue_nav(page_type, config["archive"], archive_files)

    # Build page content based on type
    if page_type == "newsletter":
        main_content = build_newsletter_content(articles, translations)
    elif page_type == "wisdom":
        main_content = build_wisdom_content(articles, translations)
    elif page_type == "obsessions":
        main_content = build_obsessions_content(articles, translations)
    else:
        main_content = build_newsletter_content(articles, translations)

    # Assemble complete page
    html = build_page_shell(today, page_type, site_nav, issue_nav,
                            main_content, glossary, shared_css, page_css, shared_js)

    # Write output
    index_path = config["index"]
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(html, encoding="utf-8")

    # Print summary
    print(f"{config['title']} assembled for {today}")
    print(f"  Content units: {len(articles)}")
    print(f"  Glossary entries: {len(glossary)}")
    print(f"  Written to: {index_path}")


if __name__ == "__main__":
    main()
