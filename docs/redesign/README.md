# saferi.org redesign working folder

Not deployed (`docs/` is in `.vercelignore`).

- `directions/`: three working homepage directions (A register, B working paper, C three faces). Open through the local preview at `/docs/redesign/directions/<name>/index.html`.
- `screenshots/after/`: every redesigned page at both widths, plus the report template.
- `screenshots/before/`: every current page at 1440 and 390 px wide.
- `screenshots/directions/`: the three directions at both widths.
- `shoot.py`: full-page screenshot script (scrolls first, reports console errors and horizontal overflow).

## Direction chosen (2026-11-27)

A (the register) as the base, with B's report cover and C's cube with three faces (research reports, open access briefings, public education). Logo: the purple and teal cube.

## Logo colors (from the vector logo files)

| Role in logo | Hex |
|---|---|
| Cube, dark face and "RESEARCH INSTITUTE" | `#534A6D` |
| Cube, lower face | `#69698F` |
| "SAFE" wordmark | `#93B7BD` |
| Cube top face, wordmark highlight | `#BFDADA` |

`#93B7BD` and `#BFDADA` fail contrast as text on white, so links use a derived deep teal `#2C6B74` (6.1:1) and body text a derived ink `#2A2438`.

## What the current design gets wrong

1. The real logo is not on the site. The header shows a letter "S" tile and the words "SAFE RESEARCH".
2. The palette is an approximation of the logo (`#5fa8b0`, `#585181`, `#1e2148`), and the first screen is a dark navy block, not a light page.
3. Research is not in the navigation. The nav is Policies, Education, About, Donate.
4. The homepage is 10,892 px tall on desktop and 18,436 px on a phone, with two "Coming Soon" sections and no published work above them.
5. Cards start at opacity 0 and only appear on scroll (`js/main.js`), so the page shows blank bands to anyone who prints, screenshots or has scripts blocked.
6. Dense material is laid out as card grids with hover effects, not tables.
7. A stat block presents "3 Activities", "50 States Served", "100% Non-Partisan" and an infinity sign as figures.
8. The newsletter forms show a thank-you alert and send nothing.
9. Footer links to State Disclosures, Donor Privacy Policy, Research Hub, Science News Hub, 990 Disclosures and Contact Us point at `#`.
10. Two footer variants exist; most pages show the short one without the address or the affiliation disclosure.
11. All-caps tracked labels sit above nearly every heading, and inline `style` attributes carry much of the layout.
