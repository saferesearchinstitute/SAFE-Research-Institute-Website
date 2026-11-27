"""Build the Evidence Library from markdown. One command.

Usage (from the repo root):
  python3 docs/templates/build_site.py            build everything
  python3 docs/templates/build_site.py --check    build nothing; fail if any generated file is stale
  python3 docs/templates/build_site.py --no-pdf   skip PDFs and preview images (fast; text outputs only)
  python3 docs/templates/build_site.py --draft <file.md> --out <dir>
        render one unpublished markdown file as a watermarked DRAFT page and PDF into <dir>.
        Nothing else is touched: no listing, feed, sitemap, llms.txt or search index.

Sources: every markdown file in policies/ and publications/ with `status: "published"`.
Frontmatter: id, title, summary, createdAt, updatedAt, and optionally
  kind (display type; default "Model policy document" for policies/, "Report" otherwise),
  area (topic area shown in the library), authors, reviewers, version, license, keywords.

Per publication it writes
  library/<id>.html        publication page (content is in the HTML; no JavaScript needed to read it)
  library/pdf/<id>.pdf     designed PDF: cover, body, running footer; selectable text, live links, metadata
  library/<id>.md          clean markdown copy at the page address plus .md (the llms.txt convention)
  img/og/<id>.png          1200 x 630 link-preview image
and for the site
  library.html, index.html the rows and cover between the LIBRARY markers
  library/search-index.json, feed.xml, sitemap.xml, robots.txt, llms.txt

Needs Playwright with Chromium and pypdf (only for PDFs and preview images).
"""
import re, sys, io, json, html, pathlib, datetime, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parents[2]
SITE = "https://saferi.org"
ORG = "SAFE Research Institute"
FOUNDATION = "Science and Freedom for Everyone Foundation"
EIN = "41-2910356"
LICENSES = {
    "CC0 1.0": ("https://creativecommons.org/publicdomain/zero/1.0/",
                "Dedicated to the public domain under Creative Commons CC0 1.0."),
    "CC BY 4.0": ("https://creativecommons.org/licenses/by/4.0/",
                  "Licensed under Creative Commons Attribution 4.0 International (CC BY 4.0)."),
}
STATIC_PAGES = ["", "library", "education", "about", "donate", "volunteer",
                "privacy", "terms", "conflict-of-interest", "gift-acceptance"]
DISCLOSURE = (f"Published by the {ORG}, the educational platform of the {FOUNDATION}, a 501(c)(3) public charity "
              f"(Tax ID {EIN}), for educational purposes. The Foundation does not recommend the adoption, "
              "modification, or rejection of any specific legislation, regulation, or policy proposal.")

# ---------------------------------------------------------------- markdown

def frontmatter(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.S)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).split("\n"):
        k, sep, v = line.partition(":")
        if not sep:
            continue
        v = v.strip()
        if len(v) > 1 and v[0] == v[-1] == '"':
            v = v[1:-1]
        meta[k.strip()] = v
    return meta, m.group(2).strip()

def listval(v):
    """'["A", "B"]' or 'A; B' -> ['A', 'B']"""
    if not v:
        return []
    v = v.strip()
    if v.startswith("["):
        return [s.strip().strip("\"'") for s in v[1:-1].split(",") if s.strip()]
    return [s.strip() for s in v.split(";") if s.strip()]

def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2" rel="noopener">\1</a>', s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', s)
    # a bare web address (as in a reference list) becomes a link
    s = re.sub(r'(?<![">=])(https?://[^\s<]+[^\s<.,;:)\]])', r'<a href="\1" rel="noopener">\1</a>', s)
    # a data file named in the text becomes a download link; other code spans stay as written
    s = re.sub(r"`((?:[^`\s]*/)?([^`\s/]+\.csv))`", r'<a href="\1" download>\2</a>', s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])", r"<em>\1</em>", s)
    return s

def md_to_html(md, img_base="", ctx=None):
    """Headings, paragraphs, quotes, rules, lists one level deep, pipe tables, links,
    and figures: an image line followed by an italic caption line and an optional 'Source: ...' line."""
    lines = md.split("\n")
    out, para, stack = [], [], []
    counts = {"figures": 0, "tables": 0}
    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>"); para.clear()
    def close(to=0):
        while len(stack) > to:
            out.append(f"</{stack.pop()}>")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        # table
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|?$", lines[i + 1].strip()):
            flush(); close()
            cells = lambda l: [c.strip() for c in l.strip().strip("|").split("|")]
            head = cells(line); i += 2; rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(cells(lines[i])); i += 1
            counts["tables"] += 1
            th = "".join(f'<th scope="col">{inline(c)}</th>' for c in head)
            tb = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows)
            out.append(f'<div class="table-wrap"><table class="data-table pub-table"><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table></div>')
            continue
        # figure
        m = re.match(r"^!\[([^\]]*)\]\(([^)\s]+)\)$", line.strip())
        if m:
            flush(); close()
            alt, src = m.group(1), m.group(2)
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            caption = source = ""
            cm = re.match(r"^\*(.+)\*$", lines[j].strip()) if j < len(lines) else None
            if cm:
                caption = cm.group(1); i = j
                k = i + 1
                while k < len(lines) and not lines[k].strip():
                    k += 1
                if k < len(lines) and lines[k].strip().lower().startswith("source:"):
                    source = lines[k].strip(); i = k
            counts["figures"] += 1
            out.append(figure_html(alt, src, caption, source, img_base, ctx))
            i += 1
            continue
        m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", line)
        if m:
            flush()
            depth = 2 if len(m.group(1)) >= 2 else 1
            tag = "ol" if m.group(2)[0].isdigit() else "ul"
            close(depth)
            while len(stack) < depth:
                out.append(f"<{tag}>"); stack.append(tag)
            out.append("<li>" + inline(m.group(3)) + "</li>")
            i += 1; continue
        if not line.strip():
            flush(); close(); i += 1; continue
        close()
        if re.match(r"^-{3,}$", line):
            flush(); out.append("<hr>"); i += 1; continue
        h = re.match(r"^(#{1,4})\s+(.*)$", line)
        if h:
            flush(); n = len(h.group(1))
            anchor = re.sub(r"[^a-z0-9]+", "-", h.group(2).lower()).strip("-")
            out.append(f'<h{n} id="{anchor}">{inline(h.group(2))}</h{n}>'); i += 1; continue
        if line.startswith(">"):
            flush(); quote = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(lines[i].lstrip("> ").rstrip()); i += 1
            out.append("<blockquote><p>" + inline(" ".join(q for q in quote if q)) + "</p></blockquote>")
            continue
        para.append(line.strip()); i += 1
    flush(); close()
    return "\n".join(out), counts

def csv_table(path, labels=None, cls="data-table pub-table"):
    """A CSV file as an HTML table. Header cells carry the column name so js/figures.js can read it."""
    import csv
    with open(path, newline="") as fh:
        rows = list(csv.reader(fh))
    head, body = rows[0], rows[1:]
    label = lambda f: (labels or {}).get(f) or f.replace("_", " ")
    th = "".join(f'<th scope="col" data-field="{html.escape(f)}">{html.escape(label(f))}</th>' for f in head)
    tb = "".join("<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in r) + "</tr>" for r in body)
    return f'<div class="table-wrap"><table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table></div>', len(body)

def figure_html(alt, src, caption, source, img_base, ctx):
    """A figure: static image, caption, and (when the caption names a data file) the numbers as a table,
    download links, and the chart settings from the sidecar file for js/figures.js."""
    data = None
    m = re.search(r"\s*Data:\s*`([^`]+\.csv)`\.?", caption)
    if m:                                   # "Data: `file.csv`." names the figure's data file and is dropped from the caption
        data = m.group(1); caption = (caption[:m.start()] + caption[m.end():]).strip()
    else:                                   # otherwise the first data file the caption mentions is used and becomes a link
        m = re.search(r"`([^`]+\.csv)`", caption)
        if m:
            data = m.group(1); caption = caption[:m.start()] + f"[the data file]({img_base}{data})" + caption[m.end():]
    num = re.match(r"^Figure (\d+)\.", caption)
    spec = (ctx.charts.get("figures", {}).get(num.group(1)) if ctx and num else None) or {}
    alt = spec.get("alt") or alt
    attrs, extra = "", ""
    if data and ctx:
        table, n = csv_table(ctx.asset_path(data), spec.get("labels"))
        label = f"Data for Figure {num.group(1)}" if num else "Data for this figure"
        extra += f'<details class="figure-data"><summary>{label} ({n} rows)</summary>{table}</details>'
        name = pathlib.Path(src).name
        extra += (f'<p class="figure-downloads">Download: <a href="{img_base}{html.escape(data)}" download>data (CSV)</a> '
                  f'<a href="{img_base}{html.escape(src)}" download="{html.escape(name)}" data-download="png">image (PNG)</a></p>')
        if spec.get("type"):
            chart = {k: v for k, v in spec.items() if k not in ("steps", "alt")}
            attrs = f" data-chart='{html.escape(json.dumps(chart), quote=False).replace(chr(39), '&#39;')}'"
            ctx.interactive = True
            if chart["type"] == "map":
                ctx.needs_map = True
    steps = ""
    if spec.get("steps"):
        lis = "".join(f"<li data-step='{html.escape(json.dumps({k: v for k, v in st.items() if k != 'text'}), quote=False)}'>{inline(st['text'])}</li>" for st in spec["steps"])
        steps = f'<ol class="figure-steps">{lis}</ol>'
    cap = f"<figcaption>{inline(caption)}" + (f'<span class="figure-source">{inline(source)}</span>' if source else "") + "</figcaption>" if caption else ""
    fig = f'<figure class="pub-figure"{attrs}><img src="{img_base}{html.escape(src)}" alt="{html.escape(alt)}" loading="lazy">{cap}{steps}{extra}</figure>'
    look = ctx.charts.get("lookup") if ctx else None
    if look and num and str(look.get("afterFigure")) == num.group(1):
        table, n = csv_table(ctx.asset_path(look["data"]), look.get("labels"))
        cfg = {k: look[k] for k in ("key", "prompt", "placeholder", "fields") if k in look}
        ctx.interactive = True
        fig += (f"<section class=\"place-lookup\" data-lookup='{html.escape(json.dumps(cfg), quote=False).replace(chr(39), '&#39;')}'>"
                f'<h3>{html.escape(look.get("title", "Find your state"))}</h3>'
                + (f'<p>{inline(look["intro"])}</p>' if look.get("intro") else "")
                + lookup_map_html(look, ctx)
                + f'<div class="place-lookup-body"><details class="figure-data"><summary>All {n} rows</summary>{table}</details>'
                f'<p class="figure-downloads">Download: <a href="{img_base}{html.escape(look["data"])}" download>data (CSV)</a></p></div></section>')
    return fig

def lookup_map_html(look, ctx):
    """A state map above the lookup's chooser. It colors states by one of the listed columns of the
    lookup's own table; js/figures.js draws it. Without scripts the table below it is the fallback."""
    m = look.get("map")
    if not m:
        return ""
    ctx.needs_map = True
    cfg = {"key": look["key"], "measures": m["measures"]}
    cap = inline(m.get("caption", "")) + (f'<span class="figure-source">{inline(m["source"])}</span>' if m.get("source") else "")
    return (f"<figure class=\"place-map\" data-map='{html.escape(json.dumps(cfg), quote=False).replace(chr(39), '&#39;')}'>"
            f'<div class="place-map-toggle" role="group" aria-label="Measure shown on the map" hidden></div>'
            f'<div class="place-map-chart" hidden></div>'
            f'<p class="place-map-hint" hidden>Select a state on the map, or use the State menu below.</p>'
            f"<figcaption>{cap}</figcaption></figure>")

class Ctx:
    """What the markdown converter needs to know about one publication's files."""
    def __init__(self, pub, page_dir):
        self.charts, self.page_dir = pub.charts, pathlib.Path(page_dir)
        self.interactive = self.needs_map = False
    def asset_path(self, rel):
        return self.page_dir / rel

def plain(md):
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", md)
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"[*#>|`]", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def long_date(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.strftime('%B')} {d.day}, {d.year}"

# ---------------------------------------------------------------- publications

class Pub:
    def __init__(self, path, draft=False):
        self.path = pathlib.Path(path)
        meta, body = frontmatter(self.path.read_text())
        self.meta, self.draft = meta, draft
        self.slug = meta.get("id") or self.path.stem
        self.title = meta["title"]
        self.summary = meta.get("summary", "")
        self.updated = meta.get("updatedAt") or meta.get("createdAt")
        self.created = meta.get("createdAt") or self.updated
        from_policies = self.path.parent.name == "policies"
        self.kind = meta.get("kind") or ("Model policy document" if from_policies else "Report")
        # The eight documents in policies/ are all public health subjects; their old
        # "category" values stay as keywords.
        self.area = meta.get("area") or ("Public health" if from_policies else "")
        self.keywords = listval(meta.get("keywords")) or ([meta["category"]] if meta.get("category") else [])
        self.authors = listval(meta.get("authors"))
        self.reviewers = listval(meta.get("reviewers"))
        self.license = meta.get("license") or ("CC0 1.0" if self.kind == "Model policy document" else "CC BY 4.0")
        self.version = meta.get("version") or f"Version of {long_date(self.updated)}"
        self.is_news = self.kind == "News"
        body = re.sub(r"^#\s+.*\n", "", body, count=1)
        # Editor's notes never ship: a draft preview drops them, a real build refuses.
        m = re.search(r"^##\s+Editor.s notes.*", body, re.S | re.M | re.I)
        if m:
            assert draft, f"{self.path.name} still has an Editor's notes section. Remove it before publishing."
            body = body[:m.start()].rstrip().rstrip("-").rstrip()
        # the page prints its own citation block
        body = re.sub(r"^##\s+Suggested citation\s*\n.*?(?=^##\s|\Z)", "", body, flags=re.S | re.M | re.I)
        # chart settings, scroll steps and the place lookup live beside the markdown, never in it
        side = self.path.with_suffix(".charts.json")
        self.charts = json.loads(side.read_text()) if side.exists() else {}
        # figures and data files are copied next to the page under assets/<id>/
        self.assets = {}
        def asset(rel):
            if re.match(r"^(https?:|data:|assets/)", rel):
                return rel
            dest = f"assets/{self.slug}/{pathlib.Path(rel).name}"
            self.assets[dest] = self.path.parent / rel
            return dest
        body = re.sub(r"(!\[[^\]]*\]\()([^)\s]+)(\))", lambda m: m.group(1) + asset(m.group(2)) + m.group(3), body)
        body = re.sub(r"(`)([^`\s]+\.csv)(`)", lambda m: m.group(1) + asset(m.group(2)) + m.group(3), body)
        if self.charts.get("lookup", {}).get("data"):
            self.charts["lookup"]["data"] = asset(self.charts["lookup"]["data"])
        # a section headed "Key findings" is lifted into the box at the top
        self.key_findings = ""
        m = re.search(r"^##\s+Key findings\s*\n(.*?)(?=^##\s|\Z)", body, re.S | re.M | re.I)
        if m:
            self.key_findings = m.group(1).strip(); body = body[:m.start()] + body[m.end():]
        # a final section headed "References" is set as the reference list
        self.references = ""
        m = re.search(r"^##\s+References\s*\n(.*?)(?=^##\s|\Z)", body, re.S | re.M | re.I)
        if m:
            self.references = m.group(1).strip(); body = body[:m.start()] + body[m.end():]
        self.body_md = body.strip()
        self.url = f"{SITE}/library/{self.slug}"
        self.pdf_url = f"{SITE}/library/pdf/{self.slug}.pdf"
        notice = re.match(r"^>\s*(.*)$", self.body_md)
        self.notice_md = notice.group(1) if notice else ""

    @property
    def year(self):
        return self.updated[:4]

    def citation(self):
        who = ", ".join(self.authors) if self.authors else ORG
        return (f"{who}. ({self.year}). <em>{html.escape(self.title)}</em> ({self.kind}, {self.version[0].lower() + self.version[1:]}). "
                f"{FOUNDATION}. {self.url}")

    def stats(self):
        _, c = md_to_html(self.body_md)
        c["interactive"] = len([f for f in self.charts.get("figures", {}).values() if f.get("type")])
        links = len(re.findall(r"\]\(https?://", self.body_md + self.references))
        refs = len(re.findall(r"^\s*(\d+\.|-)\s", self.references, re.M))
        return dict(words=len(plain(self.body_md).split()), figures=c["figures"], tables=c["tables"], links=links, references=refs)

def load_pubs():
    pubs = []
    for folder in ("policies", "publications"):
        for f in sorted((ROOT / folder).glob("*.md")):
            meta, _ = frontmatter(f.read_text())
            if meta.get("status", "published") == "published" and meta.get("title"):
                pubs.append(Pub(f))
    pubs.sort(key=lambda p: (p.updated, p.slug), reverse=True)
    return pubs

# ---------------------------------------------------------------- machine-readable metadata

def scholar_meta(p):
    """Google Scholar citation tags (scholar.google.com/intl/en/scholar/inclusion.html).
    Scholar asks for "the authors (and only the actual authors)", so the tags are written
    only when the frontmatter names people. Dates use Scholar's 2010/5/12 form."""
    if not p.authors:
        return ""
    authors = p.authors
    d = lambda iso: "/".join(str(int(x)) for x in iso.split("-"))
    tags = [("citation_title", p.title)]
    tags += [("citation_author", a) for a in authors]
    tags += [("citation_publication_date", d(p.created)),
             ("citation_online_date", d(p.updated)),
             ("citation_technical_report_institution", ORG),
             ("citation_pdf_url", p.pdf_url)]
    return "".join(f'  <meta name="{k}" content="{html.escape(v)}">\n' for k, v in tags)

def json_ld(p):
    lic, _ = LICENSES[p.license]
    org = {"@type": "Organization", "name": ORG, "url": SITE + "/",
           "logo": {"@type": "ImageObject", "url": SITE + "/img/og/default.png"},
           "parentOrganization": {"@type": "NGO", "name": FOUNDATION, "taxID": EIN}}
    data = {
        "@context": "https://schema.org",
        "@type": "NewsArticle" if p.is_news else "Report",
        "@id": p.url,
        "url": p.url,
        "mainEntityOfPage": p.url,
        "headline": p.title,
        "name": p.title,
        "description": p.summary,
        "abstract": p.summary,
        "datePublished": p.created + "T00:00:00+00:00",
        "dateModified": p.updated + "T00:00:00+00:00",
        "version": p.version,
        "inLanguage": "en",
        "isAccessibleForFree": True,
        "license": lic,
        "genre": p.kind,
        "author": [{"@type": "Person", "name": a} for a in p.authors] or org,
        "publisher": org,
        "image": f"{SITE}/img/og/{p.slug}.png",
    }
    if p.area: data["about"] = p.area
    if p.keywords: data["keywords"] = ", ".join(p.keywords)
    if not p.is_news:
        data["encoding"] = {"@type": "MediaObject", "encodingFormat": "application/pdf", "contentUrl": p.pdf_url}
    return '  <script type="application/ld+json">\n' + json.dumps(data, indent=2, ensure_ascii=False) + "\n  </script>\n"

# ---------------------------------------------------------------- interactive figure libraries
# Exact versions from the jsDelivr CDN, with integrity hashes. Loaded only on pages that declare
# interactive figures. Sources and the date checked are in docs/templates/README.md.
LIBS = {
    "d3": ("https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js",
           "sha384-CjloA8y00+1SDAUkjs099PVfnY2KmDC2BZnws9kh8D/lX1s46w6EPhpXdqMfjK6i"),
    "plot": ("https://cdn.jsdelivr.net/npm/@observablehq/plot@0.6.17/dist/plot.umd.min.js",
             "sha384-JUpn2GgRr0gxU0xOBd8D8P634jhRCwobtG8G2MMEkX1RnGJ7/FJNnuukpfT+H2w1"),
    "topojson": ("https://cdn.jsdelivr.net/npm/topojson-client@3.1.0/dist/topojson-client.min.js",
                 "sha384-Ukv1p/xTma6P4/2bY5KzWBw+ydSpXmhCMtyciIQVDJ1RmOxtCYNMF1uXT9T63H67"),
    "us_atlas": ("https://cdn.jsdelivr.net/npm/us-atlas@3.0.1/states-albers-10m.json",
                 "sha384-vyqp+z8MYIFZU8V1K7x8eeS6f4qq+zp2l6YqE81ZLpCykssi+zpvpQSkQNRqIaJb"),
}

def script_tag(lib):
    src, integrity = lib
    return f'<script src="{src}" integrity="{integrity}" crossorigin="anonymous" defer></script>'

# ---------------------------------------------------------------- pages

def chrome(prefix="../"):
    """Header and footer for generated pages come from docs/templates/page.html."""
    tpl = (ROOT / "docs/templates/page.html").read_text()
    head, rest = tpl.split("{{MAIN}}", 1)
    return head.replace("{{P}}", prefix), rest.replace("{{P}}", prefix)

def cover_html(p, prefix="../", link=None):
    tag, href = ("a", f' href="{link}"') if link else ("div", "")
    return f"""<{tag} class="report-cover"{href}>
      <img class="report-cover-mark" src="{prefix}img/logo-mark.svg" alt="" width="68" height="68">
      <div>
        <div class="report-cover-type">{html.escape(p.kind)}</div>
        <div class="report-cover-title">{html.escape(p.title)}</div>
      </div>
      <div class="report-cover-foot">{ORG}<br>{html.escape(p.version)}</div>
    </{tag}>"""

def page_html(p, prefix="../", img_base="", page_dir=None):
    head, foot = chrome(prefix)
    ctx = Ctx(p, page_dir or ROOT / "library")
    body_html, _ = md_to_html(p.body_md, img_base, ctx)
    if ctx.interactive:
        tags = [script_tag(LIBS["d3"]), script_tag(LIBS["plot"])]
        if ctx.needs_map:
            tags.append(script_tag(LIBS["topojson"]))
            head = head.replace('<html lang="en">', f'<html lang="en" data-us-atlas="{LIBS["us_atlas"][0]}" data-us-atlas-integrity="{LIBS["us_atlas"][1]}">')
        tags.append(f'<script src="{prefix}js/figures.js" defer></script>')
        foot = foot.replace("</body>", "\n".join(tags) + "\n</body>")
    lic_url, lic_text = LICENSES[p.license]
    canonical = p.url
    robots = '  <meta name="robots" content="noindex, nofollow">\n' if p.draft else ""
    extra = "" if p.draft else scholar_meta(p) + json_ld(p)
    share = "" if p.draft else f"""  <link rel="canonical" href="{canonical}">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="{ORG}">
  <meta property="og:title" content="{html.escape(p.title)}">
  <meta property="og:description" content="{html.escape(p.summary)}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:image" content="{SITE}/img/og/{p.slug}.png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">
  <meta property="article:published_time" content="{p.created}">
  <meta property="article:modified_time" content="{p.updated}">
  <link rel="alternate" type="text/markdown" href="{p.slug}.md">
  <link rel="alternate" type="application/pdf" href="pdf/{p.slug}.pdf">
  <link rel="alternate" type="application/atom+xml" title="{ORG}: Evidence Library" href="{prefix}feed.xml">
"""
    head = (head.replace("{{TITLE}}", html.escape(p.title)).replace("{{DESCRIPTION}}", html.escape(p.summary))
                .replace("{{HEAD_EXTRA}}", robots + share + extra))
    meta_rows = [("Published", f'<time datetime="{p.created}">{long_date(p.created)}</time>'),
                 ("Version", html.escape(p.version)), ("Type", html.escape(p.kind))]
    if p.area: meta_rows.append(("Topic", html.escape(p.area)))
    if p.authors: meta_rows.append(("Authors", html.escape(", ".join(p.authors))))
    if p.reviewers: meta_rows.append(("Reviewed by", html.escape(", ".join(p.reviewers))))
    meta_rows.append(("License", f'<a href="{lic_url}" rel="license noopener">{p.license}</a>'))
    meta = "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in meta_rows)
    buttons = "" if p.is_news else f"""<div class="pub-actions">
        <a class="btn btn-primary" href="pdf/{p.slug}.pdf" download>Download PDF</a>
        {'' if p.draft else f'<a class="btn btn-outline" href="{p.slug}.md">Plain text</a>'}
      </div>"""
    kf = ""
    if p.key_findings:
        kf_html, _ = md_to_html(p.key_findings)
        kf = f'<section class="key-findings" aria-labelledby="kf"><h2 id="kf">Key findings</h2>\n{kf_html}\n</section>\n'
    refs = ""
    if p.references:
        r_html, _ = md_to_html(p.references)
        refs = f'<section class="pub-references"><h2 id="references">References</h2>\n{r_html}\n</section>\n'
    cite = "" if p.is_news else f"""<section class="cite-block" aria-labelledby="cite">
      <h2 id="cite">Cite this</h2>
      <p class="cite-text">{p.citation()}</p>
    </section>
"""
    watermark = '<div class="draft-banner" role="note">DRAFT. Not approved for publication. Do not share or cite.</div>\n' if p.draft else ""
    main = f"""<main id="main"{' class="is-draft"' if p.draft else ''}>
{watermark}
<article class="publication">
<div class="container breadcrumb"><a href="{prefix}library.html">Evidence Library</a></div>

<header class="report-head">
  <div class="container">
    {cover_html(p, prefix)}
    <div>
      <p class="pub-kind">{html.escape(p.kind)}</p>
      <h1>{html.escape(p.title)}</h1>
      <p class="report-summary">{html.escape(p.summary)}</p>
      <dl class="pub-meta">{meta}</dl>
      {buttons}
    </div>
  </div>
</header>

<div class="container">
  <div class="report-body">
{kf}{body_html}
{refs}{cite}    <p class="report-note">{lic_text} The Foundation's names and logos are reserved. {DISCLOSURE}</p>
  </div>
</div>
</article>

</main>"""
    return head + main + foot

# ---------------------------------------------------------------- question pages and place pages
# Both are generated only from files the report's authors write. Nothing here supplies wording or numbers.

US_STATES = dict(l.split("=") for l in """AL=Alabama AK=Alaska AZ=Arizona AR=Arkansas CA=California CO=Colorado CT=Connecticut DE=Delaware DC=District_of_Columbia FL=Florida GA=Georgia HI=Hawaii ID=Idaho IL=Illinois IN=Indiana IA=Iowa KS=Kansas KY=Kentucky LA=Louisiana ME=Maine MD=Maryland MA=Massachusetts MI=Michigan MN=Minnesota MS=Mississippi MO=Missouri MT=Montana NE=Nebraska NV=Nevada NH=New_Hampshire NJ=New_Jersey NM=New_Mexico NY=New_York NC=North_Carolina ND=North_Dakota OH=Ohio OK=Oklahoma OR=Oregon PA=Pennsylvania RI=Rhode_Island SC=South_Carolina SD=South_Dakota TN=Tennessee TX=Texas UT=Utah VT=Vermont VA=Virginia WA=Washington WV=West_Virginia WI=Wisconsin WY=Wyoming""".split())
US_STATES = {k: v.replace("_", " ") for k, v in US_STATES.items()}

def simple_page(prefix, title, description, canonical, main, draft, ld=None):
    head, foot = chrome(prefix)
    robots = '  <meta name="robots" content="noindex, nofollow">\n' if draft else ""
    share = "" if draft else (f'  <link rel="canonical" href="{canonical}">\n  <meta property="og:type" content="article">\n'
                              f'  <meta property="og:site_name" content="{ORG}">\n  <meta property="og:title" content="{html.escape(title)}">\n'
                              f'  <meta property="og:description" content="{html.escape(description)}">\n  <meta property="og:url" content="{canonical}">\n'
                              f'  <meta property="og:image" content="{SITE}/img/og/default.png">\n  <meta name="twitter:card" content="summary_large_image">\n')
    ldtag = "" if draft or not ld else '  <script type="application/ld+json">\n' + json.dumps(ld, indent=2, ensure_ascii=False) + "\n  </script>\n"
    head = (head.replace("{{TITLE}}", html.escape(title)).replace("{{DESCRIPTION}}", html.escape(description))
                .replace("{{HEAD_EXTRA}}", robots + share + ldtag))
    banner = '<div class="draft-banner" role="note">DRAFT. Not approved for publication. Do not share or cite.</div>\n' if draft else ""
    cls = ' class="is-draft"' if draft else ""
    return head + f'<main id="main"{cls}>\n{banner}{main}\n</main>' + foot

def question_page(path, report, draft, prefix="../"):
    """One page per question people search. Frontmatter: id, question, description, report, updatedAt, related.
    The first paragraph is the answer and should carry the number and its source."""
    meta, body = frontmatter(pathlib.Path(path).read_text())
    slug = meta.get("id") or pathlib.Path(path).stem
    q, desc = meta["question"], meta.get("description", "")
    body = re.sub(r"^#\s+.*\n", "", body, count=1).strip()
    first, _, rest = body.partition("\n\n")
    rest_html, _ = md_to_html(rest)
    related = "".join(f'<li><a href="{r}.html">{html.escape(t)}</a></li>' for r, t in [x.split("|", 1) for x in listval(meta.get("related")) if "|" in x])
    main = f"""<article class="publication question-page">
<div class="container breadcrumb"><a href="{prefix}library.html">Evidence Library</a></div>
<header class="legal-hero"><div class="container">
  <h1>{html.escape(q)}</h1>
  <p class="answer">{inline(first.replace(chr(10), " "))}</p>
</div></header>
<div class="container"><div class="report-body">
{rest_html}
  <section class="cite-block"><h2>From the full report</h2>
    <p><a href="{prefix}library/{report.slug}.html">{html.escape(report.title)}</a>. {html.escape(report.kind)}, {html.escape(report.version[0].lower() + report.version[1:])}. Methods, sources and limits are in the report.</p>
  </section>
  {f'<section class="related"><h2>Related questions</h2><ul>{related}</ul></section>' if related else ''}
  <p class="report-note">{DISCLOSURE}</p>
</div></div>
</article>"""
    url = f"{SITE}/questions/{slug}"
    ld = {"@context": "https://schema.org", "@type": "Article", "headline": q, "description": desc, "url": url, "mainEntityOfPage": url,
          "datePublished": (meta.get("createdAt") or report.created) + "T00:00:00+00:00",
          "dateModified": (meta.get("updatedAt") or report.updated) + "T00:00:00+00:00",
          "author": {"@type": "Organization", "name": ORG, "url": SITE + "/"}, "publisher": {"@type": "Organization", "name": ORG, "url": SITE + "/"},
          "isBasedOn": report.url}
    return slug, q, desc, simple_page(prefix, q, desc, url, main, draft, ld)

def place_pages(report, page_dir, draft, prefix="../../"):
    """One page per row of a data table (for example per state), plus an index page that lists them all.
    Configured in the sidecar under "places"; every sentence pattern there is written by the report's authors.
    Patterns may use {name} and any column as {column}."""
    import csv
    cfg = report.charts.get("places")
    if not cfg:
        return {}
    src = pathlib.Path(page_dir) / cfg["data"] if not pathlib.Path(cfg["data"]).is_absolute() else pathlib.Path(cfg["data"])
    with open(src, newline="") as fh:
        rows = list(csv.DictReader(fh))
    key, path = cfg["key"], cfg["path"]
    name_of = lambda r: US_STATES.get(r[key], r[key]) if cfg.get("names") == "us-states" else r[key]
    slug_of = lambda r: re.sub(r"[^a-z0-9]+", "-", name_of(r).lower()).strip("-")
    num = lambda v: (f"{float(v):,.1f}".rstrip("0").rstrip(".") if re.match(r"^-?\d+(\.\d+)?$", v or "") else (v or "no value"))
    fill = lambda pattern, r: pattern.format(name=name_of(r), **{k: num(v) for k, v in r.items()})
    rows.sort(key=name_of)
    out = {}
    for r in rows:
        title, desc = fill(cfg["title"], r), fill(cfg["description"], r)
        facts = "".join(f"<div><dt>{html.escape(f['label'])}</dt><dd>{num(r.get(f['field']))}{' ' + f['unit'] if f.get('unit') else ''}</dd></div>" for f in cfg["fields"])
        others = "".join(f'<li><a href="{slug_of(o)}.html">{html.escape(name_of(o))}</a></li>' for o in rows if o is not r)
        main = f"""<article class="publication place-page">
<div class="container breadcrumb"><a href="{prefix}library.html">Evidence Library</a> / <a href="{prefix}library/{report.slug}.html">{html.escape(report.title)}</a> / <a href="index.html">{html.escape(cfg.get('indexTitle', 'All places'))}</a></div>
<header class="legal-hero"><div class="container">
  <h1>{html.escape(fill(cfg.get('heading', cfg['title']), r))}</h1>
  <p class="answer">{inline(fill(cfg['intro'], r))}</p>
</div></header>
<div class="container"><div class="report-body">
  <dl class="pub-meta place-facts">{facts}</dl>
  {f"<p>{inline(fill(cfg['note'], r))}</p>" if cfg.get('note') else ''}
  <section class="cite-block"><h2>From the full report</h2>
    <p><a href="{prefix}library/{report.slug}.html#{key}={r[key]}">{html.escape(report.title)}</a>, with this place highlighted. Methods, sources and limits are in the report.</p>
  </section>
  <section class="related"><h2>{html.escape(cfg.get('indexTitle', 'All places'))}</h2><ul class="place-list">{others}</ul></section>
  <p class="report-note">{DISCLOSURE}</p>
</div></div>
</article>"""
        url = f"{SITE}/topics/{path}/{slug_of(r)}"
        out[f"topics/{path}/{slug_of(r)}.html"] = simple_page(prefix, title, desc, url, main, draft)
    th = "".join(f"<th scope=\"col\">{html.escape(f['label'])}</th>" for f in cfg["fields"])
    tb = "".join(f'<tr><td><a href="{slug_of(r)}.html">{html.escape(name_of(r))}</a></td>' + "".join(f"<td>{num(r.get(f['field']))}</td>" for f in cfg["fields"]) + "</tr>" for r in rows)
    main = f"""<article class="publication">
<div class="container breadcrumb"><a href="{prefix}library.html">Evidence Library</a> / <a href="{prefix}library/{report.slug}.html">{html.escape(report.title)}</a></div>
<header class="legal-hero"><div class="container"><h1>{html.escape(cfg.get('indexTitle', 'All places'))}</h1><p>{inline(cfg.get('indexIntro', ''))}</p></div></header>
<div class="container"><div class="report-body" style="max-width:none">
<div class="table-wrap"><table class="data-table pub-table"><thead><tr><th scope="col">Place</th>{th}</tr></thead><tbody>{tb}</tbody></table></div>
<p class="report-note">{DISCLOSURE}</p></div></div></article>"""
    out[f"topics/{path}/index.html"] = simple_page(prefix, cfg.get("indexTitle", "All places"), cfg.get("indexIntro", ""), f"{SITE}/topics/{path}", main, draft)
    return out

# ---------------------------------------------------------------- PDF and preview image

PRINT_CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&display=swap');
* { box-sizing: border-box; margin: 0; }
body { font-family: 'IBM Plex Sans', Helvetica, Arial, sans-serif; color: #3A3550; font-size: 10.5pt; line-height: 1.55; }
a { color: #2C6B74; }
h1, h2, h3, h4 { color: #2A2438; font-weight: 600; line-height: 1.2; break-after: avoid; }
h1 { font-size: 24pt; margin-bottom: 6pt; }
.byline { font-size: 16pt; color: #2A2438; margin-bottom: 4pt; }
.docline { font-size: 9pt; color: #676380; margin-bottom: 16pt; padding-bottom: 10pt; border-bottom: 1.5pt solid #534A6D; }
h2 { font-size: 13.5pt; margin: 20pt 0 7pt; padding-top: 9pt; border-top: 1.5pt solid #534A6D; }
h3 { font-size: 11.5pt; margin: 14pt 0 5pt; }
p { margin-bottom: 8pt; orphans: 3; widows: 3; }
ul, ol { margin: 0 0 8pt 16pt; padding: 0; }
li { margin-bottom: 4pt; }
blockquote { border-left: 3pt solid #93B7BD; background: #EEF5F5; padding: 9pt 12pt 1pt; margin: 0 0 12pt; break-inside: avoid; }
hr { border: 0; border-top: 0.75pt solid #DAD8E4; margin: 16pt 0 12pt; }
table { width: 100%; border-collapse: collapse; font-size: 9pt; margin: 6pt 0 14pt; }
th { text-align: left; color: #676380; font-weight: 600; border-bottom: 1.5pt solid #534A6D; padding: 4pt 6pt 4pt 0; }
td { border-bottom: 0.5pt solid #DAD8E4; padding: 4pt 6pt 4pt 0; vertical-align: top; }
tr { break-inside: avoid; }
figure { margin: 10pt 0 14pt; break-inside: avoid; }
figure img { max-width: 100%; }
figcaption { font-size: 9pt; color: #676380; margin-top: 4pt; }
.figure-source { display: block; }
.figure-data, .figure-downloads, .place-lookup { display: none; }
.figure-steps { font-size: 9pt; margin: 4pt 0 0 14pt; }
code { font-family: inherit; }
.key-findings { border: 1pt solid #DAD8E4; border-top: 3pt solid #93B7BD; padding: 10pt 14pt 4pt; margin-bottom: 14pt; break-inside: avoid; }
.key-findings h2 { border: 0; margin: 0 0 6pt; padding: 0; }
.cite { border-top: 0.75pt solid #DAD8E4; margin-top: 18pt; padding-top: 10pt; font-size: 9pt; }
.license { margin-top: 10pt; font-size: 9pt; color: #676380; }
.cover { position: relative; overflow: hidden; width: 8.5in; height: 11in; background: #534A6D; color: #fff; padding: 0.9in 0.85in 0.7in; display: flex; flex-direction: column; justify-content: space-between; }
.cover .mark { width: 1.25in; height: 1.25in; background: #fff; border-radius: 50%; padding: 0.22in; }
.cover .type { font-size: 15pt; color: #BFDADA; margin-bottom: 12pt; }
.cover h1 { color: #fff; font-size: 34pt; line-height: 1.1; letter-spacing: -0.01em; margin-bottom: 14pt; max-width: 6.2in; }
.cover .who { font-size: 17pt; margin-bottom: 20pt; }
.cover .notice { font-size: 11.5pt; color: #fff; max-width: 5.6in; border-left: 3pt solid #BFDADA; padding-left: 12pt; }
.cover .notice a { color: #fff; }
.cover .foot { border-top: 1pt solid rgba(255,255,255,.4); padding-top: 14pt; font-size: 10pt; line-height: 1.6; display: flex; justify-content: space-between; gap: 0.4in; }
.cover .foot div:last-child { text-align: right; color: #BFDADA; }
.cover .edge { position: absolute; right: 0; top: 0; width: 0.28in; height: 11in; background: linear-gradient(180deg, #69698F 0 45%, #93B7BD 45% 80%, #BFDADA 80%); }
.stamp { position: fixed; top: 38%; left: 0; width: 100%; text-align: center; font-size: 110pt; font-weight: 600; color: rgba(176, 58, 46, 0.13); transform: rotate(-28deg); letter-spacing: 0.08em; z-index: 9; pointer-events: none; }
.cover .stamp { color: rgba(255, 255, 255, 0.22); position: absolute; }
"""

def inline_images(doc, base):
    """Chromium will not load local files into a page set from a string, so figures are embedded."""
    import base64, mimetypes
    def sub(m):
        f = pathlib.Path(base) / m.group(1)
        if not f.exists():
            return m.group(0)
        mime = mimetypes.guess_type(f.name)[0] or "image/png"
        return f'src="data:{mime};base64,{base64.b64encode(f.read_bytes()).decode()}"'
    return re.sub(r'src="(?!data:|https?:)([^"]+)"', sub, doc)

def build_pdf(p, browser, out_path, img_dir=None):
    from pypdf import PdfReader, PdfWriter
    lic_url, lic_text = LICENSES[p.license]
    base_dir = pathlib.Path(img_dir or ROOT / "library")
    body_html, _ = md_to_html(p.body_md, "", Ctx(p, base_dir))
    body_html = inline_images(body_html, base_dir)
    kf = ""
    if p.key_findings:
        k, _ = md_to_html(p.key_findings); kf = f'<div class="key-findings"><h2>Key findings</h2>{k}</div>'
    refs = ""
    if p.references:
        r, _ = md_to_html(p.references); refs = f"<h2>References</h2>{r}"
    who = ", ".join(p.authors) if p.authors else ORG
    stamp = '<div class="stamp">DRAFT</div>' if p.draft else ""
    mark_svg = re.sub(r"<svg ", '<svg class="mark" ', (ROOT / "img/logo-mark.svg").read_text(), count=1)
    notice = f'<div class="notice">{inline(p.notice_md)}</div>' if p.notice_md else ""
    cover = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{PRINT_CSS} @page {{ size: Letter; margin: 0; }}</style></head><body>
<div class="cover">{stamp}<div class="edge"></div>{mark_svg}
<div><div class="type">{html.escape(p.kind)}</div><h1>{html.escape(p.title)}</h1><div class="who">{html.escape(who)}</div>{notice}</div>
<div class="foot"><div>{ORG}<br>{FOUNDATION}<br>Tax ID (EIN): {EIN}</div><div>{html.escape(p.version)}<br>{p.license}<br><a style="color:#BFDADA" href="{p.url}">saferi.org/library/{p.slug}</a></div></div></div></body></html>"""
    inner = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{PRINT_CSS}</style></head><body>{stamp}
<h1>{html.escape(p.title)}</h1>
<p class="byline">{html.escape(who)}</p>
<p class="docline">{html.escape(p.kind)}. Published {long_date(p.created)}. {html.escape(p.version)}. <a href="{p.url}">{p.url}</a></p>
{kf}{body_html}{refs}
<p class="cite"><strong>Cite this.</strong> {p.citation()}</p>
<p class="license"><a href="{lic_url}">{p.license}</a>. {lic_text} The Foundation's names and logos are reserved. {DISCLOSURE}</p></body></html>"""
    foot = f"""<div style="width:100%;font-family:Helvetica,Arial,sans-serif;font-size:7.5pt;color:#676380;padding:0 0.9in;white-space:nowrap;display:flex;justify-content:space-between;">
<span>{ORG}, EIN {EIN}, saferi.org{' (DRAFT, not for distribution)' if p.draft else ''}</span><span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span></div>"""
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
        writer.append(io.BytesIO(part))          # append keeps link annotations
    writer.add_metadata({"/Title": p.title, "/Author": who,
                         "/Subject": f"{p.kind}. {p.version}. {p.license}.",
                         "/Keywords": ", ".join([p.area] + p.keywords if p.area else p.keywords),
                         "/Creator": f"{ORG}, {FOUNDATION}",
                         "/CreationDate": "D:" + p.created.replace("-", "") + "000000Z",
                         "/ModDate": "D:" + p.updated.replace("-", "") + "000000Z"})
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as fh:
        writer.write(fh)
    return len(PdfReader(str(out_path)).pages)

def build_og(p, browser, out_path):
    q = urllib.parse.urlencode(dict(title=p.title, type=p.kind, date=p.version))
    card = browser.new_page(viewport={"width": 1200, "height": 630})
    card.goto((ROOT / "docs/templates/og-card.html").as_uri() + "?" + q, wait_until="networkidle")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    card.screenshot(path=str(out_path)); card.close()

# ---------------------------------------------------------------- site-wide outputs

def row_html(p):
    pdf = "" if p.is_news else f'<a href="library/pdf/{p.slug}.pdf" download>PDF</a>'
    return f"""          <tr data-id="{p.slug}">
            <td><a href="library/{p.slug}.html">{html.escape(p.title)}</a></td>
            <td data-label="Type">{html.escape(p.kind)}</td>
            <td data-label="Topic">{html.escape(p.area)}</td>
            <td data-label="Updated"><time datetime="{p.updated}">{long_date(p.updated)}</time></td>
            <td data-label="PDF">{pdf}</td>
          </tr>"""

def between(text, name, new):
    a, b = f"<!-- {name}:START -->", f"<!-- {name}:END -->"
    assert a in text and b in text, f"markers for {name} missing"
    return text[:text.index(a) + len(a)] + "\n" + new + "\n" + " " * 10 + text[text.index(b):]

def site_outputs(pubs):
    out = {}
    rows = "\n".join(row_html(p) for p in pubs)
    newest = next((p for p in pubs if not p.is_news), None)
    for name, limit in (("library.html", None), ("index.html", 10)):
        t = (ROOT / name).read_text()
        shown = "\n".join(row_html(p) for p in (pubs if limit is None else pubs[:limit]))
        t = between(t, "LIBRARY-ROWS", shown)
        t = between(t, "LIBRARY-COVER", cover_html(newest, "", f"library/{newest.slug}.html") if newest else "")
        out[name] = t
    out["library/search-index.json"] = json.dumps(
        [dict(id=p.slug, title=p.title, type=p.kind, topic=p.area, updated=p.updated, summary=p.summary,
              text=plain(p.key_findings + " " + p.body_md + " " + p.references)) for p in pubs],
        ensure_ascii=False, separators=(",", ":"))
    for p in pubs:
        lic_url, lic_text = LICENSES[p.license]
        header = (f"# {p.title}\n\n{p.kind}. {ORG}, {FOUNDATION}.\nPublished {long_date(p.created)}. {p.version}.\n"
                  f"License: {p.license} ({lic_url}).\nPage: {p.url}\nPDF: {p.pdf_url}\n\n> {p.summary}\n\n")
        kf = f"## Key findings\n\n{p.key_findings}\n\n" if p.key_findings else ""
        refs = f"\n\n## References\n\n{p.references}" if p.references else ""
        out[f"library/{p.slug}.md"] = header + kf + p.body_md + refs + f"\n\n---\n\nSuggested citation: {re.sub(r'<[^>]+>', '', p.citation())}\n"
    # feed
    updated = (pubs[0].updated if pubs else datetime.date.today().isoformat()) + "T00:00:00Z"
    x = html.escape
    feed = ['<?xml version="1.0" encoding="utf-8"?>', '<feed xmlns="http://www.w3.org/2005/Atom">',
            f"  <title>{ORG}: Evidence Library</title>",
            f"  <subtitle>Documents published by the {ORG}, the educational platform of the {FOUNDATION}.</subtitle>",
            f'  <link href="{SITE}/feed.xml" rel="self" type="application/atom+xml"/>',
            f'  <link href="{SITE}/library" rel="alternate" type="text/html"/>',
            f"  <id>{SITE}/</id>", f"  <updated>{updated}</updated>", f"  <author><name>{ORG}</name></author>"]
    for p in pubs:
        feed += ["  <entry>", f"    <title>{x(p.title)}</title>", f'    <link href="{p.url}" rel="alternate" type="text/html"/>',
                 f'    <link href="{p.pdf_url}" rel="enclosure" type="application/pdf"/>' if not p.is_news else "",
                 f"    <id>{p.url}</id>", f"    <published>{p.created}T00:00:00Z</published>", f"    <updated>{p.updated}T00:00:00Z</updated>",
                 f'    <category term="{x(p.kind)}"/>', f"    <summary>{x(p.summary)}</summary>", "  </entry>"]
    out["feed.xml"] = "\n".join(l for l in feed if l) + "\n</feed>\n"
    # sitemap (lastmod only where a real date is known)
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm += [f"  <url><loc>{SITE}/{s}</loc></url>" for s in STATIC_PAGES]
    sm += [f"  <url><loc>{p.url}</loc><lastmod>{p.updated}</lastmod></url>" for p in pubs]
    sm += [f"  <url><loc>{u}</loc></url>" for u, _, _ in EXTRA_URLS]
    out["sitemap.xml"] = "\n".join(sm) + "\n</urlset>\n"
    out["robots.txt"] = ("# Search engines and AI systems are welcome to read, index and cite everything published here.\n"
                         "# One group for every crawler, so the two private tool pages stay excluded for all of them.\n"
                         "User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /write\n\n"
                         f"Sitemap: {SITE}/sitemap.xml\n")
    # llms.txt
    by_kind = {}
    for p in pubs:
        by_kind.setdefault(p.kind, []).append(p)
    ll = [f"# {ORG}", "",
          f"> The {ORG} is the educational platform of the {FOUNDATION}, a 501(c)(3) public charity. It publishes plain-language "
          "analyses of peer-reviewed research on science and technology topics. Everything is free to read, download and cite. "
          "The Institute takes no position on any bill.", "",
          "Each document below is available as a web page, a PDF and a clean markdown file. The markdown links are listed here."]
    for kind, items in by_kind.items():
        ll += ["", f"## {kind}s", ""]
        ll += [f"- [{p.title}]({SITE}/library/{p.slug}.md): {p.summary}" for p in items]
    ll += ["", "## Optional", "",
           f"- [Evidence Library]({SITE}/library): the full list with filters and search",
           f"- [Atom feed]({SITE}/feed.xml): new documents as they are published",
           f"- [About the Foundation]({SITE}/about): board, commitments and tax status",
           f"- [Terms of Use]({SITE}/terms): licenses for each type of material"]
    out["llms.txt"] = "\n".join(ll) + "\n"
    return out

# ---------------------------------------------------------------- main

EXTRA_URLS = []

def copy_assets(p, page_dir):
    import shutil
    for dest, src in p.assets.items():
        target = pathlib.Path(page_dir) / dest
        target.parent.mkdir(parents=True, exist_ok=True)
        if src.resolve() != target.resolve():
            shutil.copyfile(src, target)

def main():
    args = sys.argv[1:]
    if "--draft" in args:
        src = pathlib.Path(args[args.index("--draft") + 1]).resolve()
        out = pathlib.Path(args[args.index("--out") + 1]).resolve()
        ignored = __import__("subprocess").run(["git", "check-ignore", "-q", str(out)], cwd=ROOT).returncode == 0
        assert ignored, f"{out} is not git-ignored. Draft previews must never be committed."
        p = Pub(src, draft=True)
        out.mkdir(parents=True, exist_ok=True)
        copy_assets(p, out)
        (out / f"{p.slug}.html").write_text(page_html(p, prefix="../", page_dir=out))
        extra = 0
        qdir = src.parent / (src.stem + ".questions")
        for q in sorted(qdir.glob("*.md")) if qdir.exists() else []:
            slug, _, _, doc = question_page(q, p, True, prefix="../../")
            doc = doc.replace(f"../../library/{p.slug}.html", f"../{p.slug}.html")
            (out / "questions").mkdir(exist_ok=True); (out / "questions" / f"{slug}.html").write_text(doc); extra += 1
        for rel, doc in place_pages(p, out, True, prefix="../../../").items():
            doc = doc.replace(f"../../../library/{p.slug}.html", f"../../{p.slug}.html")
            f = out / rel; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(doc); extra += 1
        print(f"  plus {extra} question and place pages")
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            n = build_pdf(p, b, out / "pdf" / f"{p.slug}.pdf", img_dir=out)
            b.close()
        print(f"draft preview: {out / (p.slug + '.html')} ({n} PDF pages). Not listed anywhere.")
        return
    pubs = load_pubs()
    if "--check" not in args:
        for p in pubs:
            copy_assets(p, ROOT / "library")
    files = {f"library/{p.slug}.html": page_html(p) for p in pubs}
    by_slug = {p.slug: p for p in pubs}
    extra_urls = []
    for q in sorted((ROOT / "publications/questions").glob("*.md")) if (ROOT / "publications/questions").exists() else []:
        meta, _ = frontmatter(q.read_text())
        if meta.get("status") == "published" and meta.get("report") in by_slug:
            slug, question, desc, doc = question_page(q, by_slug[meta["report"]], False)
            files[f"questions/{slug}.html"] = doc; extra_urls.append((f"{SITE}/questions/{slug}", question, desc))
    for p in pubs:
        for rel, doc in place_pages(p, ROOT / "library", False).items():
            files[rel] = doc; extra_urls.append((f"{SITE}/{rel[:-5]}".replace("/index", ""), "", ""))
    EXTRA_URLS[:] = extra_urls
    files.update(site_outputs(pubs))
    if "--check" in args:
        stale = [f for f, t in files.items() if not (ROOT / f).exists() or (ROOT / f).read_text() != t]
        stale += [f"library/pdf/{p.slug}.pdf" for p in pubs if not p.is_news and not (ROOT / f"library/pdf/{p.slug}.pdf").exists()]
        print("up to date" if not stale else "STALE: " + ", ".join(stale))
        sys.exit(1 if stale else 0)
    for f, t in files.items():
        path = ROOT / f
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(t)
    if "--no-pdf" not in args:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            for p in pubs:
                if not p.is_news:
                    n = build_pdf(p, b, ROOT / "library/pdf" / f"{p.slug}.pdf")
                    print(f"pdf {p.slug}: {n} pages", file=sys.stderr)
                build_og(p, b, ROOT / "img/og" / f"{p.slug}.png")
            b.close()
    print(f"{len(pubs)} publications; {len(files)} text files written")
    for p in pubs:
        s = p.stats()
        print(f"  {p.slug}: {s['words']} words, {s['figures']} figures, {s['tables']} tables, {s['links']} links, {s['references']} references")

if __name__ == "__main__":
    main()
