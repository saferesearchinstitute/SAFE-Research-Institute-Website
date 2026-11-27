"""Rebuild feed.xml (Atom) from the list in research.html.

Usage (from the repo root):  python3 docs/templates/build_feed.py

research.html is the only place reports and news are listed. This script reads its
table and writes feed.xml, so the feed never needs editing by hand. Rows without a
link (items listed as scheduled) are left out. Each entry's summary is the linked
page's meta description.
"""
import re, html, pathlib, datetime
from xml.sax.saxutils import escape

SITE = "https://saferi.org"
root = pathlib.Path(__file__).resolve().parents[2]
src = (root / "research.html").read_text()
src = re.sub(r"<!--.*?-->", "", src, flags=re.S)
table = re.search(r'<table[^>]*id="reportsTable".*?</table>', src, re.S).group(0)

entries = []
for row in re.findall(r"<tr>(.*?)</tr>", table, re.S):
    cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
    if len(cells) < 3:
        continue
    link = re.search(r'<a href="([^"]+)"[^>]*>(.*?)</a>', cells[0], re.S)
    when = re.search(r'datetime="([^"]+)"', cells[1])
    if not link or not when:
        continue
    href, title = link.group(1), html.unescape(re.sub(r"<[^>]+>", "", link.group(2))).strip()
    date = when.group(1)
    if len(date) == 7:
        date += "-01"
    page = root / href
    summary = ""
    if page.exists():
        m = re.search(r'<meta name="description" content="([^"]*)"', page.read_text())
        summary = html.unescape(m.group(1)) if m else ""
    url = SITE + "/" + (href[:-5] if href.endswith(".html") else href)
    kind = html.unescape(re.sub(r"<[^>]+>", "", cells[2])).strip()
    entries.append((date, title, url, summary, kind))

entries.sort(reverse=True)
updated = (entries[0][0] if entries else datetime.date.today().isoformat()) + "T00:00:00Z"
out = [
    '<?xml version="1.0" encoding="utf-8"?>',
    '<feed xmlns="http://www.w3.org/2005/Atom">',
    "  <title>SAFE Research Institute: publications and news</title>",
    "  <subtitle>Reports and announcements from the SAFE Research Institute, the educational platform of the Science and Freedom for Everyone Foundation.</subtitle>",
    f'  <link href="{SITE}/feed.xml" rel="self" type="application/atom+xml"/>',
    f'  <link href="{SITE}/research" rel="alternate" type="text/html"/>',
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
print(f"feed.xml: {len(entries)} entries")
