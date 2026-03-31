#!/usr/bin/env python3
"""Insert a Special Edition article into docs/index.html.

Reads checkpoint files from data/pipeline/, builds the SE HTML block,
inserts it into the page, and merges the glossary.

Usage:
    python3 scripts/insert_se.py
"""

import json
import re
import sys
from pathlib import Path

PIPELINE = Path("data/pipeline")
INDEX = Path("docs/index.html")


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_se_html(article: dict, translation: str, se_id: int) -> str:
    return f"""<article class="article se-article" data-se-id="{se_id}">
  <h2 class="article-headline">{article['headline_html']}</h2>
  <p class="article-source">{article['source_label']}</p>
  <div class="article-body-zh">{article['body_html']}</div>
  <button class="translation-toggle" type="button">顯示翻譯 Show Translation</button>
  <div class="article-body-en" hidden>{translation}</div>
</article>"""


def find_glossary_json(html: str):
    """Find the GLOSSARY object in the HTML by brace-matching."""
    marker = "const GLOSSARY = "
    start = html.index(marker)
    json_start = start + len(marker)

    depth = 0
    for i in range(json_start, len(html)):
        if html[i] == "{":
            depth += 1
        elif html[i] == "}":
            depth -= 1
            if depth == 0:
                return json_start, i + 1
    raise ValueError("Could not find closing brace for GLOSSARY")


def main():
    articles = load_json(PIPELINE / "articles.json")
    translations = load_json(PIPELINE / "translations.json")
    new_glossary = load_json(PIPELINE / "glossary.json")

    art = articles[0]
    trans = translations[0]

    html = INDEX.read_text(encoding="utf-8")

    # Determine SE id
    existing_ids = [int(x) for x in re.findall(r'data-se-id="(\d+)"', html)]
    next_id = max(existing_ids, default=0) + 1

    se_article = build_se_html(art, trans, next_id)

    # Insert into page
    if '<div id="special-editions">' in html:
        # Find the closing </div> of the SE container and insert before it
        # The SE container ends with </article>\n</div>
        se_end = html.index('<div id="special-editions">')
        # Find the matching closing </div> by scanning for </article> blocks
        # Simple approach: find last </article> in SE section, then next </div>
        container_start = se_end
        # Find all se-article closings after the container start
        pos = container_start
        last_article_end = pos
        while True:
            idx = html.find("</article>", last_article_end + 1)
            if idx == -1 or idx > html.find('<div class="toolbar"', container_start):
                break
            last_article_end = idx + len("</article>")
        # Insert new article before the closing </div> of the container
        close_div = html.find("</div>", last_article_end)
        html = html[:close_div] + se_article + "\n" + html[close_div:]
    else:
        # Create new SE container
        se_block = f"""<div id="special-editions">
  <h2 class="se-header">特別報導 Special Edition</h2>
{se_article}
</div>"""
        html = html.replace(
            "</main>\n\n<div class=\"toolbar\"",
            f"</main>\n\n{se_block}\n\n<div class=\"toolbar\""
        )

    # Merge glossary
    json_start, json_end = find_glossary_json(html)
    existing = json.loads(html[json_start:json_end])
    merged = {**existing, **new_glossary}
    merged_json = json.dumps(merged, ensure_ascii=False, separators=(",", ":"))
    html = html[:json_start] + merged_json + html[json_end:]

    INDEX.write_text(html, encoding="utf-8")

    print(f"SE #{next_id} inserted: {art['headline_plain']}")
    print(f"Glossary: {len(existing)} existing + {len(new_glossary)} new = {len(merged)} merged")


if __name__ == "__main__":
    main()
