# Adding to the Evidence Library on saferi.org

`library.html` holds the one list of published work. The home page block, the cover, `feed.xml` and `sitemap.xml` are all made from its table, so an item is listed in exactly one place. Only list what is published: nothing scheduled, nothing "coming soon".

Every document lives in one folder: page at `library/<slug>.html`, PDF at `library/pdf/<slug>.pdf`, link-preview image at `img/og/<slug>.png`.

## A document written in markdown (how the first eight were made)

1. Write `policies/<slug>.md` with the frontmatter the existing files use (`id`, `title`, `category`, `summary`, `updatedAt`).
2. Run the generator. It writes the page, the designed PDF (cover, body, footer with EIN and page numbers) and the preview image, and prints the table row.

```bash
python3 docs/templates/build_library.py <slug>
```

3. Paste the printed `<tr>` at the top of the `#libraryTable` body in `library.html`.
4. Rebuild the feed and sitemap.

```bash
python3 docs/templates/build_feed.py
```

Run `build_library.py` with no arguments to rebuild all documents after a design change. The PDF "version" is the `updatedAt` date. State lists in the frontmatter are never printed.

## A report written as a page

1. Copy `docs/templates/report.html` to `library/<slug>.html` and replace every `{{TOKEN}}`. Search for `{{` before committing; none may remain.
2. Put its PDF at `library/pdf/<slug>.pdf`.
3. Make the preview image, add the row (shape is in the comment above the table in `library.html`), rebuild the feed.

```bash
python3 docs/templates/make_og.py <slug> "<title>" "<type>" "<date>"
```

```bash
python3 docs/templates/build_feed.py
```

## A news item

Copy `docs/templates/news.html` to `news/<slug>.html`. Its row has Type exactly `News` and empty Topic and PDF cells. Then the same two commands.

## Notes

- Type labels in use: "Model policy document" (the Foundation's published term for the eight documents in `policies/`; license CC0 1.0). Reports and educational materials are CC BY 4.0.
- Every page carries share tags (title, description, canonical URL, Open Graph, large-image Twitter card). `ONE_SENTENCE_SUMMARY` or the frontmatter `summary` is the text a link preview shows.
- Paths in the templates are written for a file one folder down (`../css/style.css`). This folder is not deployed (`docs/` is in `.vercelignore`).
- Needs Playwright with Chromium and `pypdf`.
- Copy rules: educational framing only. The Institute takes no position on any bill and never labels one; no em-dashes; no sign-up walls, social embeds or follow blocks. Run the `audit-compliance-language` skill before deploying.
