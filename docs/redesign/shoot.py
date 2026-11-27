"""Full-page screenshots at desktop and phone width.
Usage: python3 docs/redesign/shoot.py <outdir> <url> [<url> ...]
Scrolls each page first so scroll-triggered content is visible."""
import sys, os
from playwright.sync_api import sync_playwright
out, urls = sys.argv[1], sys.argv[2:]
os.makedirs(out, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch()
    for label, vp in (("desktop", {"width": 1440, "height": 900}), ("phone", {"width": 390, "height": 844})):
        pg = b.new_page(viewport=vp, device_scale_factor=1)
        errs = []
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errs.append(str(e)))
        for u in urls:
            errs.clear()
            pg.goto(u, wait_until="load"); pg.wait_for_timeout(1200)
            h = pg.evaluate("document.documentElement.scrollHeight")
            y = 0
            while y < h:
                pg.evaluate(f"window.scrollTo(0,{y})"); pg.wait_for_timeout(120); y += 600
            pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(900)
            name = u.rstrip("/").split("/")[-1].split("?")[0].replace(".html", "") or "index"
            if name == "index" and "/directions/" in u: name = u.rstrip("/").split("/")[-2]
            pg.screenshot(path=f"{out}/{name}-{label}.png", full_page=True)
            sw = pg.evaluate("document.documentElement.scrollWidth")
            print(name, label, "h=%d" % h, "overflow-x" if sw > vp["width"] else "ok", "| console errors: %d" % len(errs), *errs[:3])
    b.close()
