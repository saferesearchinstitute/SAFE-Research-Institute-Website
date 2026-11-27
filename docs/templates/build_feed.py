"""Rebuild feed.xml (Atom), sitemap.xml and robots.txt from the list in library.html.

Usage (from the repo root):  python3 docs/templates/build_feed.py

library.html is the only place published work is listed. This script reads its table,
so the feed and the sitemap never need editing by hand. Rows without a link are left
out. Each feed entry's summary is the linked page's meta description.
"""
import re, html, pathlib, datetime
from xml.sax.saxutils import escape

SITE = "https://saferi.org"
STATIC = ["", "library", "education", "about", "donate", "volunteer",
          "privacy", "terms", "conflict-of-interest", "gift-acceptance"]
root = pathlib.Path(__file__).resolve().parents[2]
src = re.sub(r"<!--.*?-->", "", (root / "library.html").read_text(), flags=re.S)
table = re.search(r'<table[^>]*id="libraryTable".*?</table>', src, re.S).group(0)
strip = lambda s: html.unescape(re.sub(r"<[^>]+>", "", s)).strip()

entries = []
for row in re.findall(r"<tr>(.*?)</tr>", table, re.S):
    cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
    if len(cells) < 4:
        continue
    link = re.search(r'<a href="([^"]+)"[^>]*>(.*?)</a>', cells[0], re.S)
    when = re.search(r'datetime="([^"]+)"', cells[3])
    if not link or not when:
        continue
    href, title, date = link.group(1), strip(link.group(2)), when.group(1)
    page = root / href
    summary = ""
    if page.exists():
        m = re.search(r'<meta name="description" content="([^"]*)"', page.read_text())
        summary = html.unescape(m.group(1)) if m else ""
    url = SITE + "/" + (href[:-5] if href.endswith(".html") else href)
    entries.append((date, title, url, summary, strip(cells[1])))

entries.sort(reverse=True)
updated = (entries[0][0] if entries else datetime.date.today().isoformat()) + "T00:00:00Z"
out = [
    '<?xml version="1.0" encoding="utf-8"?>',
    '<feed xmlns="http://www.w3.org/2005/Atom">',
    "  <title>SAFE Research Institute: Evidence Library</title>",
    "  <subtitle>Documents published by the SAFE Research Institute, the educational platform of the Science and Freedom for Everyone Foundation.</subtitle>",
    f'  <link href="{SITE}/feed.xml" rel="self" type="application/atom+xml"/>',
    f'  <link href="{SITE}/library" rel="alternate" type="text/html"/>',
    f"  <id>{SITE}/</id>",
    f"  <updated>{updated}</updated>",
    "  <author><name>SAFE Research Institute</name></author>",
]
for date, title, url, summary, kind in entries:
    out += [
        "  <entry>",
        f"    <title>{escape(title)}</title>",
        f'    <link href="{url}" rel="alternate" type="text/html"/>',
        f"    <id>{url}</id>",
        f"    <updated>{date}T00:00:00Z</updated>",
        f'    <category term="{escape(kind)}"/>',
        f"    <summary>{escape(summary)}</summary>",
        "  </entry>",
    ]
out.append("</feed>")
(root / "feed.xml").write_text("\n".join(out) + "\n")

urls = [f"{SITE}/{p}" for p in STATIC] + [u for _, _, u, _, _ in entries]
sm = ['<?xml version="1.0" encoding="utf-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
sm += [f"  <url><loc>{u}</loc></url>" for u in urls] + ["</urlset>"]
(root / "sitemap.xml").write_text("\n".join(sm) + "\n")
(root / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /write\n\nSitemap: {SITE}/sitemap.xml\n")
print(f"feed.xml: {len(entries)} entries; sitemap.xml: {len(urls)} URLs")
