"""Build the page, PDF and link-preview image for library documents written in markdown.

Usage (from the repo root):
  python3 docs/templates/build_library.py            all documents in policies/*.md
  python3 docs/templates/build_library.py <id> ...   only the named ones

For each policies/<id>.md (frontmatter: id, title, type, category, summary, updatedAt) it writes
  library/<id>.html       the document page, with share tags
  library/pdf/<id>.pdf    the designed PDF: cover, body, footer with EIN and page numbers
  img/og/<id>.png         the 1200 x 630 link-preview image
and prints the table row to paste into library.html. It never edits library.html.

Needs Playwright (with Chromium) and pypdf. The PDF "version" is the updatedAt date.
"""
import re, sys, html, io, pathlib, datetime, urllib.parse
from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter

ROOT = pathlib.Path(__file__).resolve().parents[2]
SITE = "https://saferi.org"
EIN = "41-2910356"
# The label shown for these documents. The Foundation's published term for them is
# "model policy documents" (see the commitment statement on the About page).
TYPE_LABEL = "Model policy document"
LICENSE = ("CC0 1.0", "https://creativecommons.org/publicdomain/zero/1.0/",
           "Dedicated to the public domain under Creative Commons CC0 1.0. The Foundation's names and logos are reserved.")

def frontmatter(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.S)
    meta = {}
    for line in m.group(1).split("\n"):
        k, _, v = line.partition(":")
        v = v.strip()
        if len(v) > 1 and v[0] == v[-1] == '"': v = v[1:-1]
        meta[k.strip()] = v
    return meta, m.group(2).strip()

def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", s)
    return s

def md_to_html(md):
    """Covers what these documents use: headings, paragraphs, quotes, rules, and lists one level deep."""
    out, para, stack = [], [], []
    def flush():
        if para: out.append("<p>" + inline(" ".join(para)) + "</p>"); para.clear()
    def close(to=0):
        while len(stack) > to: out.append(f"</{stack.pop()}>")
    for raw in md.split("\n"):
        line = raw.rstrip()
        m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", line)
        if m:
            flush()
            depth = 2 if len(m.group(1)) >= 2 else 1
            tag = "ol" if m.group(2)[0].isdigit() else "ul"
            close(depth)
            while len(stack) < depth: out.append(f"<{tag}>"); stack.append(tag)
            out.append("<li>" + inline(m.group(3)) + "</li>")
            continue
        if not line.strip(): flush(); close(); continue
        close()
        if re.match(r"^-{3,}$", line): flush(); out.append("<hr>"); continue
        h = re.match(r"^(#{1,4})\s+(.*)$", line)
        if h: flush(); n = len(h.group(1)); out.append(f"<h{n}>{inline(h.group(2))}</h{n}>"); continue
        if line.startswith(">"): flush(); out.append("<blockquote><p>" + inline(line.lstrip("> ")) + "</p></blockquote>"); continue
        para.append(line.strip())
    flush(); close()
    return "\n".join(out)

def long_date(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.strftime('%B')} {d.day}, {d.year}"

PRINT_CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&display=swap');
* { box-sizing: border-box; margin: 0; }
body { font-family: 'IBM Plex Sans', Helvetica, Arial, sans-serif; color: #3A3550; font-size: 10.5pt; line-height: 1.55; }
h1, h2, h3, h4 { color: #2A2438; font-weight: 600; line-height: 1.2; break-after: avoid; }
h1 { font-size: 20pt; margin-bottom: 14pt; }
h2 { font-size: 13.5pt; margin: 20pt 0 7pt; padding-top: 9pt; border-top: 1.5pt solid #534A6D; }
h3 { font-size: 11.5pt; margin: 14pt 0 5pt; }
p { margin-bottom: 8pt; orphans: 3; widows: 3; }
ul, ol { margin: 0 0 8pt 16pt; padding: 0; }
li { margin-bottom: 4pt; }
blockquote { border-left: 3pt solid #93B7BD; background: #EEF5F5; padding: 9pt 12pt 1pt; margin: 0 0 12pt; break-inside: avoid; }
hr { border: 0; border-top: 0.75pt solid #DAD8E4; margin: 16pt 0 12pt; }
.license { margin-top: 18pt; padding-top: 10pt; border-top: 0.75pt solid #DAD8E4; font-size: 9pt; color: #676380; }
/* cover */
.cover { position: relative; overflow: hidden; width: 8.5in; height: 11in; background: #534A6D; color: #fff; padding: 0.9in 0.85in 0.7in; display: flex; flex-direction: column; justify-content: space-between; }
.cover .mark { width: 1.25in; height: 1.25in; background: #fff; border-radius: 50%; padding: 0.22in; }
.cover .type { font-size: 15pt; color: #BFDADA; margin-bottom: 12pt; }
.cover h1 { color: #fff; font-size: 34pt; line-height: 1.1; letter-spacing: -0.01em; margin-bottom: 20pt; max-width: 6.2in; }
.cover .notice { font-size: 11.5pt; color: #fff; max-width: 5.6in; border-left: 3pt solid #BFDADA; padding-left: 12pt; }
.cover .foot { border-top: 1pt solid rgba(255,255,255,.4); padding-top: 14pt; font-size: 10pt; line-height: 1.6; display: flex; justify-content: space-between; gap: 0.4in; }
.cover .foot div:last-child { text-align: right; color: #BFDADA; }
.cover .edge { position: absolute; right: 0; top: 0; width: 0.28in; height: 11in; background: linear-gradient(180deg, #69698F 0 45%, #93B7BD 45% 80%, #BFDADA 80%); }
"""

def build(md_path, browser):
    meta, body = frontmatter(md_path.read_text())
    slug, title, updated = meta["id"], meta["title"], meta["updatedAt"]
    topic, summary = meta.get("category", ""), meta.get("summary", "")
    when = long_date(updated)
    body = re.sub(r"^#\s+.*\n", "", body, count=1)          # the title is shown by the page and the cover
    notice = re.search(r"^>\s*(.*)$", body, re.M)
    notice_html = inline(notice.group(1)) if notice else ""
    body_html = md_to_html(body)
    mark_svg = re.sub(r"<svg ", '<svg class="mark" ', (ROOT / "img/logo-mark.svg").read_text(), count=1)

    # ---- PDF: cover (no margins) + body (margins, running footer), merged ----
    cover = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{PRINT_CSS} @page {{ size: Letter; margin: 0; }}</style></head><body>
<div class="cover"><div class="edge"></div>{mark_svg}
<div><div class="type">{TYPE_LABEL}</div><h1>{html.escape(title)}</h1><div class="notice">{notice_html}</div></div>
<div class="foot"><div>SAFE Research Institute<br>Science and Freedom for Everyone Foundation<br>Tax ID (EIN): {EIN}</div><div>Version of {when}<br>{LICENSE[0]}, public domain dedication<br>saferi.org/library/{slug}</div></div></div></body></html>"""
    inner = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{PRINT_CSS}</style></head><body>
<h1>{html.escape(title)}</h1>{body_html}
<p class="license">{TYPE_LABEL}. Version of {when}. {LICENSE[2]} Published by the SAFE Research Institute, the educational platform of the Science and Freedom for Everyone Foundation, a 501(c)(3) public charity. Tax ID (EIN): {EIN}. Source: {SITE}/library/{slug}</p></body></html>"""
    foot = f"""<div style="width:100%;font-family:Helvetica,Arial,sans-serif;font-size:7.5pt;color:#676380;padding:0 0.9in;white-space:nowrap;display:flex;justify-content:space-between;">
<span>SAFE Research Institute, EIN {EIN}, saferi.org</span><span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span></div>"""
    page = browser.new_page()
    parts = []
    for doc, opts in ((cover, dict(margin=dict(top="0", bottom="0", left="0", right="0"))),
                      (inner, dict(margin=dict(top="0.85in", bottom="0.95in", left="0.9in", right="0.9in"),
                                   display_header_footer=True, header_template="<span></span>", footer_template=foot))):
        page.set_content(doc, wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        parts.append(page.pdf(format="Letter", print_background=True, **opts))
    page.close()
    writer = PdfWriter()
    for part in parts:
        for p in PdfReader(io.BytesIO(part)).pages: writer.add_page(p)
    writer.add_metadata({"/Title": title, "/Author": "SAFE Research Institute", "/Subject": f"{TYPE_LABEL}. {LICENSE[0]}."})
    pdf_path = ROOT / "library/pdf" / f"{slug}.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    with open(pdf_path, "wb") as fh: writer.write(fh)

    # ---- link-preview image ----
    q = urllib.parse.urlencode(dict(title=title, type=TYPE_LABEL, date=when))
    card = browser.new_page(viewport={"width": 1200, "height": 630})
    card.goto((ROOT / "docs/templates/og-card.html").as_uri() + "?" + q, wait_until="networkidle")
    og = ROOT / "img/og" / f"{slug}.png"
    og.parent.mkdir(parents=True, exist_ok=True)
    card.screenshot(path=str(og)); card.close()

    # ---- document page, on the report template's header and footer ----
    tpl = (ROOT / "docs/templates/report.html").read_text()
    head, rest = tpl.split('<main id="main">', 1)
    footer = rest.split("</main>", 1)[1]
    for k, v in dict(TITLE=html.escape(title), ONE_SENTENCE_SUMMARY=html.escape(summary), SLUG=slug, DATE_ISO=updated).items():
        head = head.replace("{{" + k + "}}", v)
    main = f"""<main id="main">

<div class="container breadcrumb"><a href="../library.html">Evidence Library</a></div>

<section class="report-head">
  <div class="container">
    <div class="report-cover">
      <img class="report-cover-mark" src="../img/logo-mark.svg" alt="" width="68" height="68">
      <div>
        <div class="report-cover-type">{TYPE_LABEL}</div>
        <div class="report-cover-title">{html.escape(title)}</div>
      </div>
      <div class="report-cover-foot">SAFE Research Institute<br>Version of {when}</div>
    </div>
    <div>
      <h1>{html.escape(title)}</h1>
      <p class="report-summary">{html.escape(summary)}</p>
      <dl class="report-meta">
        <dt>Updated</dt><dd><time datetime="{updated}">{when}</time></dd>
        <dt>Type</dt><dd>{TYPE_LABEL}</dd>
        <dt>Topic</dt><dd>{html.escape(topic)}</dd>
        <dt>License</dt><dd><a href="{LICENSE[1]}" rel="license noopener">{LICENSE[0]}</a></dd>
      </dl>
      <a class="btn btn-primary" href="pdf/{slug}.pdf">Download the PDF</a>
    </div>
  </div>
</section>

<div class="container">
  <article class="report-body">
{body_html}
  </article>
</div>

</main>"""
    (ROOT / "library").mkdir(exist_ok=True)
    (ROOT / "library" / f"{slug}.html").write_text(head + main + footer)
    row = f"""              <tr>
                <td><a href="library/{slug}.html">{html.escape(title)}</a></td>
                <td data-label="Type">{TYPE_LABEL}</td>
                <td data-label="Topic">{html.escape(topic)}</td>
                <td data-label="Updated"><time datetime="{updated}">{when}</time></td>
                <td data-label="PDF"><a href="library/pdf/{slug}.pdf">PDF</a></td>
              </tr>"""
    return updated, slug, row, len(PdfReader(str(pdf_path)).pages)

if __name__ == "__main__":
    wanted = sys.argv[1:]
    files = sorted((ROOT / "policies").glob("*.md"))
    if wanted: files = [f for f in files if f.stem in wanted]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        done = [build(f, browser) for f in files]
        browser.close()
    done.sort(reverse=True)
    for updated, slug, row, pages in done: print(f"built {slug}: {pages} pages", file=sys.stderr)
    print("\n".join(r for _, _, r, _ in done))
