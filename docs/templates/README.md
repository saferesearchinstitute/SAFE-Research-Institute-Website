# Adding a report or a news item to saferi.org

`research.html` holds the one list of reports and news. The home page "Latest" section, the cover block and `feed.xml` are all made from it, so an item is listed in exactly one place.

## A report

1. Copy `docs/templates/report.html` to `reports/<slug>.html` (for example `reports/2026-year-in-review.html`).
2. Replace every `{{TOKEN}}` in the copy: `TITLE`, `ONE_SENTENCE_SUMMARY`, `TYPE`, `DATE_LONG` (December 15, 2026), `DATE_ISO` (2026-12-15), `AUTHORS`, `SLUG`, and the body sections. Add or remove `<h2>` sections as the report needs. Search the file for `{{` before committing; none may remain.
3. Put the PDF at `reports/pdf/<slug>.pdf`.
4. In `research.html`, add one `<tr>` at the top of the `#reportsTable` body. The comment above that table shows the exact shape. For a report that was listed as scheduled, edit its existing row instead.
5. Run the two commands below.

## A news item

Same steps with `docs/templates/news.html`, saved as `news/<slug>.html`. Its row has Type exactly `News` and an empty PDF cell. News items have no PDF.

## Two commands after adding a row

```bash
python3 docs/templates/make_og.py <slug> "<title>" "<type>" "<date>"
```

```bash
python3 docs/templates/build_feed.py
```

The first writes `img/og/<slug>.png`, the 1200 x 630 image that link previews show (the page's share tags already point at it). The second rewrites `feed.xml` from the table. Neither is an edit; both read what you already wrote. `make_og.py` needs Playwright.

## What each page carries for link previews

Title, description, canonical URL (`https://saferi.org/reports/<slug>` or `/news/<slug>`), Open Graph title, description, URL and image, and a large-image Twitter card. `ONE_SENTENCE_SUMMARY` is what shows under the title in a preview, so write it for that.

## Notes

- Paths in the templates are written for a file inside `reports/` or `news/` (`../css/style.css`). This folder is not deployed (`docs/` is in `.vercelignore`).
- The home page shows the newest five rows. The cover shows the newest report, even when a news item is newer.
- Copy rules: educational framing only. The Institute takes no position on any bill and never labels one; no recommendation to adopt, change or reject any legislation, regulation or policy proposal; no em-dashes; no social feed embeds or follow blocks. Run the `audit-compliance-language` skill before deploying.
