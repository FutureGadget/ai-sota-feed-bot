# Main page UX audit batch 2 - E2E screenshots (2026-08-24)

Captured from the production build (`scripts/vercel_build.py` output) served with the
real serverless API handlers, driven by Playwright (Chromium). 15/15 functional
checks passed; zero third-party CSS/JS/font hosts (Oat + Three.js are self-hosted).

| File | Shows |
|---|---|
| `01-desktop-top.png` | Desktop hero: kicker removed, honest meta line, accent Reader-boosted badge, ranked-because lines, feedback row visible, Model Radar rail; focus ring returned to Editor's Desk after Esc |
| `02-desktop-research-lens.png` | Research lens applied: `aria-pressed` tab, honest empty state with widened range + Clear filters |
| `03-desktop-scrolled-floating-bar.png` | Floating compact nav bar engaged after scroll; sticky Model Radar rail pinned (top=16px) |
| `04-desk-dialog.png` | Editor's Desk dialog: grouped nav incl. Model Radar, no orphaned Settings heading |
| `05-desktop-dark.png` | Dark theme via the real theme toggle |
| `06-mobile-top.png` | Mobile masthead: explainer line, kicker + promise copy, honest meta |
| `07-mobile-floating-bar.png` | Mobile floating bar: single compact row (61px), no horizontal overflow |
