"""Check every link on every page (root, library/ and news/).
Usage: python3 docs/redesign/linkcheck.py [dir]   (default: repo root)
Internal links: the file must exist and any #fragment must be an id on that page.
External links: HTTP status (403/429 from a bot block is reported as unverified, not dead).
Also lists href="#" dead ends."""
import re, sys, glob, os, subprocess
root = sys.argv[1] if len(sys.argv) > 1 else "."
pages = sorted(glob.glob(os.path.join(root, "*.html")) + glob.glob(os.path.join(root, "library", "*.html")) + glob.glob(os.path.join(root, "news", "*.html")))
ids = {}
def page_ids(path):
    if path not in ids:
        t = open(path).read() if os.path.exists(path) else ""
        ids[path] = set(re.findall(r'\bid="([^"]+)"', t))
    return ids[path]
broken, deadend, external, total = [], [], {}, 0
for p in pages:
    t = re.sub(r"<!--.*?-->", "", open(p).read(), flags=re.S)
    for attr, u in re.findall(r'\b(href|src)="([^"]*)"', t):
        total += 1
        name = os.path.relpath(p, root)
        if u.startswith(("mailto:", "tel:", "data:", "javascript:")): continue
        if u.startswith("http"):
            if "fonts.g" in u or "saferi.org" in u: continue
            external.setdefault(u, []).append(name); continue
        if u == "#": deadend.append((name, u)); continue
        path, _, frag = u.partition("#"); path = path.split("?")[0]
        target = p if path == "" else os.path.normpath(os.path.join(os.path.dirname(p), path))
        if not os.path.exists(target): broken.append((name, u, "missing file")); continue
        if frag and target.endswith(".html") and frag not in page_ids(target): broken.append((name, u, "missing #" + frag))
ext_bad = []
for u, where in sorted(external.items()):
    code = subprocess.run(["curl", "-s", "-o", "/dev/null", "-L", "-m", "20", "-A", "Mozilla/5.0 (link check)", "-w", "%{http_code}", u], capture_output=True, text=True).stdout
    state = "ok" if code.startswith("2") else ("unverified (blocked)" if code in ("403", "429") else "DEAD")
    print(f"external {code} {state}: {u}  [{', '.join(sorted(set(where)))}]")
    if state == "DEAD": ext_bad.append(u)
for b in broken: print("BROKEN", *b)
for d in deadend: print("DEAD END", *d)
print(f"pages {len(pages)}, links {total}, broken internal {len(broken)}, dead external {len(ext_bad)}, dead ends (#) {len(deadend)}")
