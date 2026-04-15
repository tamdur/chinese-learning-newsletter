---
name: translator
description: Translate a Traditional Chinese news article to natural English HTML for the newsletter translation toggle.
model: haiku
tools: []
---

# Translator — Chinese to English

Translate a Traditional Chinese news article to natural English for the newsletter's translation toggle.

## Instructions

Translate the following Chinese article to English:
- Natural, readable English — not a literal word-for-word translation
- Maintain the same paragraph structure
- Output plain HTML paragraphs (`<p>` tags only)
- Do not include the headline — only translate the body text

## Article to Translate

{{article_text}}

## Output

Return only the HTML translation:
```html
<p>First paragraph translation...</p>
<p>Second paragraph translation...</p>
```
