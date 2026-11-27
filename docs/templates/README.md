# Publishing to the Evidence Library on saferi.org

One markdown file, one command. Only published work is listed: nothing scheduled, nothing "coming soon".

## Add a publication

1. Write `publications/<slug>.md` (the first eight live in `policies/`). Frontmatter:

```
---
id: <slug>
title: "Title"
kind: "Report"                 # shown as the type; "News" makes a news item with no PDF
area: "Energy"                 # topic area shown in the library
summary: "One or two sentences. This is the abstract line and the link-preview text."
authors: ["First Last", "First Last"]     # real people only; leave out if none
reviewers: ["First Last"]                 # only people who reviewed it; leave out if none
createdAt: "2026-12-15"
updatedAt: "2026-12-15"
version: "Version 1.0"         # optional; defaults to "Version of <updated date>"
license: "CC BY 4.0"           # optional; reports default to CC BY 4.0
status: "published"
---
```

2. Write the body in markdown. The template understands:
   - `## Key findings` becomes the box at the top.
   - A figure is an image line, then an italic caption line, then an optional source line:

     ```
     ![Alt text that describes the chart](img/<slug>-fig1.svg)
     *Figure 1. What the figure shows.*
     Source: where the numbers come from.
     ```

     Put figure files in `library/img/`. SVG or PNG. Follow each figure with a table of its numbers so the data is readable without the image.
   - Pipe tables become data tables.
   - `## References` at the end becomes the reference list. Number the entries `1.`, `2.`.
3. Run the build:

```bash
python3 docs/templates/build_site.py
```

It writes the page (`library/<slug>.html`), the designed PDF (`library/pdf/<slug>.pdf`), a clean markdown copy (`library/<slug>.md`), the link-preview image, and it rewrites the library rows and cover in `library.html` and `index.html`, the search index, `feed.xml`, `sitemap.xml`, `robots.txt` and `llms.txt`.

```bash
python3 docs/templates/build_site.py --check
```

fails if anything generated is out of date. Run it before committing.

## Preview an unapproved draft

```bash
python3 docs/templates/build_site.py --draft <file.md> --out .draft-preview
```

Renders one file as a watermarked, noindex DRAFT page and PDF into a git-ignored folder. It is not listed, indexed or fed anywhere. The command refuses to write into a folder git does not ignore, because this repository is public.

## What each publication page carries

Title block (type, published date, version, topic, authors and reviewers when named, license), Download PDF, plain-text copy, key findings, numbered figures and tables, references, a suggested citation, license and disclosure lines. For machines: canonical URL, Open Graph and Twitter card, schema.org `Report` JSON-LD with the PDF as an `encoding`, and Google Scholar `citation_*` tags when the frontmatter names authors.

## Notes

- Header and footer for generated pages come from `docs/templates/page.html`. If the site navigation changes, change it there too and rebuild.
- State lists in the old frontmatter are never printed.
- Needs Playwright with Chromium and `pypdf` for PDFs and preview images. `--no-pdf` skips both.
- Copy rules: educational framing only. The Institute takes no position on any bill and never labels one; no em-dashes; no sign-up walls, social embeds or follow blocks. Run the `audit-compliance-language` skill before deploying.

## Where the machine-readable formats come from (checked 2026-11-27)

| Format | Source |
|---|---|
| Google Scholar `citation_*` tags, date form, PDF first-page layout | https://scholar.google.com/intl/en/scholar/inclusion.html |
| schema.org `Report`, `MediaObject` | https://schema.org/Report and https://schema.org/MediaObject |
| JSON-LD embedding and Article properties | https://developers.google.com/search/docs/appearance/structured-data/article |
| `llms.txt` layout and the `.md` copy convention | https://llmstxt.org/ |
| Sitemap elements and `lastmod` | https://www.sitemaps.org/protocol.html |
| Crawler tokens (not named in `robots.txt`; one open group covers all) | OpenAI https://developers.openai.com/api/docs/bots, Anthropic https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler, Google https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers |
