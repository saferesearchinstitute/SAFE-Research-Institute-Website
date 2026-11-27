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

## Interactive figures, the state lookup, question pages and place pages

The page is complete without JavaScript: every figure has its static image, its caption and its numbers in an HTML table. `js/figures.js` reads that same table, draws the chart, and only then hides the image. The words and numbers always come from the report's files; the build supplies none.

**Give a figure its data.** Name the CSV in the caption, in backticks. `Data: \`path/file.csv\`.` is dropped from the caption; any other backticked `.csv` path becomes a link. The build copies figures and CSVs next to the page under `library/assets/<id>/`, prints the table (collapsed), and adds "data (CSV)" and "image (PNG)" downloads.

**Make it interactive.** Put a sidecar file beside the markdown, `<file>.charts.json`. Nothing in it reaches the PDF, the markdown copy, the search index or `llms.txt`.

```
{
  "figures": {
    "1": { "type": "line", "x": "year", "y": "value", "low": "range_low", "high": "range_high",
           "alt": "One sentence describing the chart for screen readers.",
           "labels": { "value": "Axis label" },
           "steps": [ { "text": "A sentence from the report.", "highlight": 2024, "highlightField": "year" } ] },
    "2": { "type": "map", "key": "state", "value": "change_pct", "diverging": true },
    "3": { "type": "bar", "x": "name", "y": "value", "orient": "h" },
    "4": { "type": "stacked", "x": "name", "values": ["a", "b"], "exclude": { "field": "name", "values": ["Total"] } },
    "5": { "type": "scatter", "x": "a", "y": "b", "name": "label_column", "key": "state", "xDomain": [-90, 150] },
    "6": { "type": "line", "x": "year", "y": "value", "series": "group_column" }
  },
  "lookup": { "afterFigure": 2, "title": "Find your state", "data": "path/states.csv", "key": "state",
              "fields": [ { "field": "change_pct", "label": "Change, 2019 to 2025", "unit": "percent" } ] },
  "places": { "path": "topic-name", "data": "assets/<id>/states.csv", "key": "state", "names": "us-states",
              "title": "{name}: ...", "description": "... {name} ... {change_pct} ...",
              "intro": "First paragraph with the number and its source, using {name} and {column} tokens.",
              "note": "The caution that applies to every place.", "indexTitle": "...", "indexIntro": "...",
              "fields": [ { "field": "change_pct", "label": "Change (%)" } ] }
}
```

- Figure keys are the figure numbers in the captions ("Figure 2.").
- `steps` turns a figure into a scroll-led one: the chart stays in view while the reader scrolls through the sentences, and each step can highlight a value, switch the `y` column or filter rows. Write each step as a sentence that is in the report.
- A map uses two-letter state codes in the `key` column. Choosing a state in the lookup, or clicking it on the map, highlights it on every chart that names the same `key`.
- `lookup` prints the whole table in the page and adds a chooser. There is no county lookup until a report has county data.
- `places` writes one page per row at `topics/<path>/<place>.html` plus an index page listing them all. Every sentence pattern is yours.
- Question pages: put `publications/questions/<id>.md` with frontmatter `id`, `question`, `description`, `report` (the report's id), `status: "published"`, optional `related: ["other-id|Link text"]`. The first paragraph is the answer and should carry the number and its source. To preview questions for a draft, put them in `<draft file name>.questions/`.

Libraries, loaded only on pages that have a sidecar: D3 7.9.0, Observable Plot 0.6.17, topojson-client 3.1.0 and the us-atlas 3.0.1 state shapes, from jsDelivr with integrity hashes (see `LIBS` in `build_site.py`).

**Search guidance this follows (checked 2026-11-27).** Google retired the FAQ rich result in 2026 and its QAPage markup is for user-submitted answers, so question pages carry `Article` data only. Google's spam policies name "scaled content abuse" and "doorway" pages and give no exemption for per-place pages; they are judged on real per-place data, a real destination and a browseable hierarchy, which is why every place page shows its own numbers and an index page lists them all.

| Topic | Source |
|---|---|
| FAQ rich result retired | https://developers.google.com/search/updates#removing-faq-rich-result |
| QAPage scope | https://developers.google.com/search/docs/appearance/structured-data/qapage |
| People-first content | https://developers.google.com/search/docs/fundamentals/creating-helpful-content |
| Spam policies | https://developers.google.com/search/docs/essentials/spam-policies |
| Title links, snippets | https://developers.google.com/search/docs/appearance/title-link, https://developers.google.com/search/docs/appearance/snippet |
| Dataset markup (not yet emitted) | https://developers.google.com/search/docs/appearance/structured-data/dataset |
| Library versions and files | https://data.jsdelivr.com/v1/packages/npm/d3 (and the same address for `@observablehq/plot`, `topojson-client`, `us-atlas`) |

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
