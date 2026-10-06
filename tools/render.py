#!/usr/bin/env python3
"""Render site/index.html from status.tsv, series.tsv and notes/double-issues.tsv.

Runs in CI on every push (see .github/workflows/pages.yml); needs only the
standard library. status.tsv itself is rebuilt locally by build_status.py.
"""
import csv
import collections
import datetime as dt
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BLITZ = "https://github.com/EveryPuzzleProject/blitz/issues/new?template=request-blitz.yml"
CATALOG = "https://github.com/EveryPuzzleProject/catalog/blob/main/publications/boston-globe.md"
REPO = "https://github.com/EveryPuzzleProject/bostonglobe"
STATES = [  # (state, label, meaning)
    ("in-gxd", "In the archive", "in the xd crossword corpus"),
    ("in-mr", "Submitted", "in a merge request to the corpus, under review"),
    ("ready", "Ready", "we have a digital copy; still to submit"),
    ("need-image", "Scan wanted", "known to exist in print; we need the page"),
    ("missing", "Not found yet", "nothing found yet"),
]


def read(name: str) -> list[dict]:
    return list(csv.DictReader(open(ROOT / name, encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE))


def e(s: str) -> str:
    return html.escape(s or "")


def main() -> None:
    rows = read("status.tsv")
    series = read("series.tsv")
    sundays = [r for r in rows if r["series"] in ("sunday", "sunday-easier")]
    count = collections.Counter(r["state"] for r in sundays)
    by_year = collections.defaultdict(collections.Counter)
    for r in sundays:
        by_year[r["date"][:4]][r["state"]] += 1

    wanted = [r for r in rows if r["state"] == "need-image"]
    missing = collections.defaultdict(list)
    for r in sundays:
        if r["state"] == "missing":
            missing[r["date"][:4]].append(r["date"][5:])

    def wanted_rows() -> str:
        out = []
        for r in wanted:
            what = {"harder": "Harder puzzle", "easier": "Easier puzzle"}.get(r["slot"], "Sunday puzzle")
            out.append(f"<tr><td>{e(r['date'])}</td><td>{e(what)}</td><td>{e(r['title'])}</td><td>{e(r['author'])}</td><td>{e(r['note'])}</td></tr>")
        return "\n".join(out)

    def missing_years() -> str:
        out = []
        for y in sorted(missing, reverse=True):
            days = missing[y]
            out.append(f"<details><summary><b>{y}</b> · {len(days)} Sunday{'s' * (len(days) != 1)}</summary><p class=dates>{', '.join(days)}</p></details>")
        return "\n".join(out)

    def bars() -> str:
        out = []
        for y in sorted(by_year):
            c = by_year[y]
            total = sum(c.values())
            seg = "".join(f'<span class="seg {s}" style="flex:{c[s]}" title="{lab}: {c[s]}"></span>' for s, lab, _ in STATES if c[s])
            have = c["in-gxd"] + c["in-mr"] + c["ready"]
            out.append(f'<div class=bar><span class=yr>{y}</span><span class=track>{seg}</span><span class=n>{have}/{total}</span></div>')
        return "\n".join(out)

    def legend() -> str:
        return "".join(f'<span class=key><span class="sw {s}"></span>{lab} <span class=muted>({count[s]})</span></span>' for s, lab, _ in STATES)

    def series_rows() -> str:
        return "\n".join(
            f"<tr><td>{e(s['name'])}</td><td>{e(s['days'])}</td><td>{e(s['from'])}</td><td>{e(s['to'])}</td><td>{e(s['status'])}</td></tr>"
            for s in series)

    def table_rows() -> str:
        label = {s: lab for s, lab, _ in STATES}
        return "\n".join(
            f'<tr data-state="{e(r["state"])}"><td>{e(r["date"])}</td><td>{e(r["slot"])}</td><td><span class="pill {e(r["state"])}">{e(label.get(r["state"], r["state"]))}</span></td>'
            f"<td>{e(r['title'])}</td><td>{e(r['author'])}</td><td>{e(r['gxd'])} {e(r['mr'])}</td><td>{e(r['note'])}</td></tr>"
            for r in sorted(rows, key=lambda r: r["date"], reverse=True))

    have = count["in-gxd"] + count["in-mr"] + count["ready"]
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Boston Globe Crosswords</title>
<style>
:root {{ --bg:#fbfaf7; --fg:#1d1d1b; --muted:#6b6a65; --line:#e3e0d8; --card:#ffffff; --accent:#8a1c1c;
  --s-in-gxd:#2f6f4f; --s-in-mr:#4f8fbf; --s-ready:#c9a227; --s-need-image:#c4572c; --s-missing:#d9d5cc; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#161614; --fg:#ecebe6; --muted:#a3a19a; --line:#34332f; --card:#1f1f1c; --accent:#e07a6a;
  --s-in-gxd:#5fae86; --s-in-mr:#6fa8d6; --s-ready:#d8b443; --s-need-image:#e0794f; --s-missing:#3b3a36; }} }}
:root[data-theme="dark"] {{ --bg:#161614; --fg:#ecebe6; --muted:#a3a19a; --line:#34332f; --card:#1f1f1c; --accent:#e07a6a;
  --s-in-gxd:#5fae86; --s-in-mr:#6fa8d6; --s-ready:#d8b443; --s-need-image:#e0794f; --s-missing:#3b3a36; }}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:16px/1.55 Georgia, "Times New Roman", serif }}
main {{ max-width:960px; margin:0 auto; padding:32px 16px 64px }}
h1 {{ font-size:2rem; margin:0 0 4px }} h2 {{ margin:40px 0 8px; font-size:1.35rem; border-bottom:2px solid var(--fg); padding-bottom:4px }}
h3 {{ margin:24px 0 6px; font-size:1.05rem }}
a {{ color:var(--accent) }} .muted {{ color:var(--muted) }} .lede {{ font-size:1.1rem }}
.cta {{ background:var(--card); border:1px solid var(--line); border-left:4px solid var(--accent); padding:16px 20px; margin:20px 0 }}
.cta ol {{ margin:8px 0 0; padding-left:22px }}
table {{ width:100%; border-collapse:collapse; font:14px/1.4 system-ui, sans-serif }}
th, td {{ text-align:left; padding:6px 8px; border-bottom:1px solid var(--line); vertical-align:top }}
th {{ font-weight:600 }} .scroll {{ overflow-x:auto }}
details {{ font:14px/1.5 system-ui, sans-serif; margin:2px 0 }} summary {{ cursor:pointer }} .dates {{ margin:4px 0 8px 18px; color:var(--muted) }}
.bar {{ display:flex; align-items:center; gap:8px; font:12px system-ui, sans-serif; margin:2px 0 }}
.yr {{ width:3em; color:var(--muted) }} .n {{ width:4.5em; text-align:right; color:var(--muted) }}
.track {{ flex:1; display:flex; height:12px; border-radius:2px; overflow:hidden; background:var(--s-missing) }}
.seg.in-gxd, .sw.in-gxd {{ background:var(--s-in-gxd) }} .seg.in-mr, .sw.in-mr {{ background:var(--s-in-mr) }}
.seg.ready, .sw.ready {{ background:var(--s-ready) }} .seg.need-image, .sw.need-image {{ background:var(--s-need-image) }}
.seg.missing, .sw.missing {{ background:var(--s-missing) }}
.legend {{ display:flex; flex-wrap:wrap; gap:14px; font:13px system-ui, sans-serif; margin:8px 0 }}
.key {{ display:inline-flex; align-items:center; gap:6px }} .sw {{ width:12px; height:12px; border-radius:2px; display:inline-block }}
.pill {{ font-size:12px; padding:1px 6px; border-radius:9px; color:#fff; white-space:nowrap }}
.pill.in-gxd {{ background:var(--s-in-gxd) }} .pill.in-mr {{ background:var(--s-in-mr) }} .pill.ready {{ background:var(--s-ready); color:#1d1d1b }}
.pill.need-image {{ background:var(--s-need-image) }} .pill.missing {{ background:var(--s-missing); color:var(--fg) }}
.filters {{ display:flex; flex-wrap:wrap; gap:8px; margin:8px 0; font:14px system-ui, sans-serif }}
input, select {{ font:inherit; padding:4px 8px; background:var(--card); color:var(--fg); border:1px solid var(--line); border-radius:4px }}
footer {{ margin-top:48px; font:13px system-ui, sans-serif; color:var(--muted) }}
</style></head><body><main>
<h1>Boston Globe Crosswords</h1>
<p class="lede">The Globe has printed crosswords since February 25, 1917. We're collecting every one into an archive
for research and preservation. Since 1980 we have <b>{have:,}</b> of {len(sundays):,} known Sunday puzzles. Here's what's missing, and how you can help.</p>

<div class="cta"><b>How you can help</b>
<ol>
<li><b>Find a missing puzzle.</b> Look up one of the Sundays below on Newspapers.com, a library database or your own copy of the paper.</li>
<li><b>Clip it.</b> Clip the puzzle page and the page with its solution (the puzzle page says where, e.g. "Solutions on page 76"). Note the title, constructor and the 1-Across clue.</li>
<li><b>Send it.</b> Open a <a href="{BLITZ}">blitz request</a> with the date, the clipping links and what you noted. Please share clipping links rather than uploading page images; the request page is public.</li>
</ol>
<p class="muted" style="margin:8px 0 0">Constructors: if you have your own files for Globe puzzles, we'd love to hear from you too.</p></div>

<h2>Scans wanted: puzzles we know about</h2>
<p>These ran in print, and we know their titles, but we have no copy we can use.</p>
<div class="scroll"><table><thead><tr><th>Date</th><th>Which</th><th>Title</th><th>Constructor</th><th>Notes</th></tr></thead><tbody>
{wanted_rows()}
</tbody></table></div>

<h2>Sundays not found yet</h2>
<p>Every Sunday since 1980 with no copy found yet. The 1990s are missing entirely.</p>
{missing_years()}

<h2>What to look for</h2>
<h3>Double issues</h3>
<p>From 2015 to 2020 (and at least once before, in 2004) some Sundays had <b>two</b> full-size crosswords on facing pages,
headed <i>The Globe Puzzle / Harder</i> and <i>The Globe Puzzle / Easier</i>. The cover usually promises "extra puzzles".
From 2017 the Harder one is often Brendan Emmett Quigley's "Themeless Challenger" and the Easier one is by Emily Cox and Henry Rathvon.
The Globe's website carried only the Harder one, so the Easier ones exist only in print. If you see a pair, send both.</p>
<h3>Identifying a puzzle</h3>
<p>Titles repeat (there are many "Themeless Challenger"s), so the 1-Across clue is the quickest way to tell puzzles apart. Dates matter too:
some copies of these puzzles were syndicated and dated weeks later, so please give the date of the Globe issue itself.</p>
<h3>Earlier series</h3>
<p>Before the Globe Magazine there were several series: a Sunday puzzle from 1917, a Saturday puzzle from 1923,
a Wednesday puzzle in 1924, and a daily from October 1924 that was still running in 1970.
We're still mapping when each started and stopped. See the <a href="{CATALOG}">catalog entry</a> for what's known and the open questions.</p>
<div class="scroll"><table><thead><tr><th>Series</th><th>Days</th><th>From</th><th>To</th><th>Status</th></tr></thead><tbody>
{series_rows()}
</tbody></table></div>

<h2>Progress, Sundays since 1980</h2>
<div class="legend">{legend()}</div>
{bars()}

<h2>Every puzzle</h2>
<div class="filters"><input id="q" type="search" placeholder="Search date, title, constructor…">
<select id="st"><option value="">All states</option>{''.join(f'<option value="{s}">{lab}</option>' for s, lab, _ in STATES)}</select></div>
<div class="scroll"><table id="all"><thead><tr><th>Date</th><th>Slot</th><th>State</th><th>Title</th><th>Constructor</th><th>Archive id</th><th>Notes</th></tr></thead><tbody>
{table_rows()}
</tbody></table></div>

<footer>Part of the <a href="https://github.com/EveryPuzzleProject">Every Puzzle Project</a>. Data: <a href="{REPO}">{REPO.split('github.com/')[1]}</a>
(status.tsv). The archive is the xd crossword corpus, which is private for rights reasons; puzzles themselves aren't published here.
Generated {dt.date.today().isoformat()}.</footer>
</main>
<script>
const q=document.getElementById('q'), st=document.getElementById('st'), rows=[...document.querySelectorAll('#all tbody tr')];
function f(){{const t=q.value.toLowerCase(), s=st.value; for(const r of rows) r.hidden=(s&&r.dataset.state!==s)||(t&&!r.textContent.toLowerCase().includes(t));}}
q.addEventListener('input',f); st.addEventListener('change',f);
</script>
</body></html>
"""
    out = ROOT / "site"
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    print(f"site/index.html: {len(rows)} rows, {len(wanted)} wanted, {sum(map(len, missing.values()))} Sundays not found")


if __name__ == "__main__":
    main()
