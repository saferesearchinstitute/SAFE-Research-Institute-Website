"""Make the 1200 x 630 link-preview image for a report or news page.

Usage (from the repo root):
  python3 docs/templates/make_og.py <slug> "<title>" "<type>" "<date>"
  python3 docs/templates/make_og.py default          (the site-wide default image)

Writes img/og/<slug>.png. Needs Playwright (pip install playwright; playwright install chromium).
"""
import sys, pathlib, urllib.parse
from playwright.sync_api import sync_playwright

root = pathlib.Path(__file__).resolve().parents[2]
slug = sys.argv[1]
fields = dict(zip(("title", "type", "date"), sys.argv[2:5]))
url = (root / "docs/templates/og-card.html").as_uri() + "?" + urllib.parse.urlencode(fields)
out = root / "img/og" / f"{slug}.png"
out.parent.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1200, "height": 630})
    page.goto(url, wait_until="networkidle")
    page.screenshot(path=str(out))
    browser.close()
print("wrote", out.relative_to(root))
