# Adding a report to saferi.org

One new file plus one table row.

1. Copy `docs/templates/report.html` to `reports/<slug>.html` (for example `reports/2026-year-in-review.html`).
2. Replace every `{{TOKEN}}` in the copy: `TITLE`, `ONE_SENTENCE_SUMMARY`, `TYPE`, `DATE_LONG` (December 15, 2026), `DATE_ISO` (2026-12-15), `AUTHORS`, `SLUG`, and the body sections. Add or remove `<h2>` sections as the report needs. Search the file for `{{` before committing; none may remain.
3. Put the PDF at `reports/pdf/<slug>.pdf`.
4. In `research.html`, add one `<tr>` at the top of the `#reportsTable` body. The comment above that table shows the exact shape. For a report that was listed as scheduled, edit its existing row instead.

The home page copies its rows from `research.html` (`js/reports.js`), and the cover block on both pages is drawn from the first row, so nothing else needs editing.

Paths in the template are written for a file inside `reports/` (`../css/style.css`). This folder is not deployed (`docs/` is in `.vercelignore`).

Copy rules for a report: educational framing only, no recommendation to adopt, change or reject any legislation, regulation or policy proposal, no em-dashes. Run the `audit-compliance-language` skill before deploying.
