# Crossword Puzzles in the Boston Globe

The Boston Globe ran its first crossword on February 25, 1917, barely three
years after the first crossword ever. This is the Every Puzzle Project's home
for indexing all of them: which series ran when, which puzzles we've found,
and which we still need.

**Status page: https://everypuzzleproject.github.io/bostonglobe/**

## How you can help

We need copies of the Sundays listed on the status page, especially the
1990s, which are missing entirely, and the second puzzle of each "double
issue" (two crosswords on facing pages, headed *The Globe Puzzle / Harder*
and *Easier*, 2015–2020).

1. Find the puzzle on Newspapers.com, in a library database or in a paper copy.
2. Clip the puzzle page and the page with its solution, and note the title,
   constructor and 1-Across clue.
3. Open a [blitz request](https://github.com/EveryPuzzleProject/blitz/issues/new?template=request-blitz.yml)
   with the date and the clipping links. Please don't upload page images:
   requests are public.

Already have puzzles as files? A .puz (Across Lite), .ipuz, .jpz or .xd file
is just as welcome as a scan. Open a request saying which puzzles you have and
we'll arrange a private way to send them (please don't attach puzzle files to
the public request). Constructors with their own files: we'd love to hear
from you.

What's known about each series, with sources, is in the
[catalog entry](https://github.com/EveryPuzzleProject/catalog/blob/main/publications/boston-globe.md).

## What's here

| File | What it is |
|---|---|
| `status.tsv` | One row per expected puzzle: every Sunday since 1980 (two on double-issue Sundays) and the Globe's Themeless Week puzzles. Built by `tools/build_status.py`. |
| `manual.tsv` | Hand-kept rows that override `status.tsv` for things a script can't see: print sightings, review results, exceptions. |
| `series.tsv` | The series and runs we know about, with dates and what's left to research. |
| `notes/` | Research data, e.g. `double-issues.tsv`. |
| `data/puzzmo-index.json` | The Globe's Puzzmo puzzle list since 2024 (titles, dates, constructors). |
| `tools/render.py` | Builds the status page from the TSVs; runs on every push. |

States, in order: `missing` (nothing found), `need-image` (known in print,
needs a scan), `ready` (we have a digital copy to submit), `in-mr` (submitted
to the archive, under review), `in-gxd` (in the archive). The archive is the
xd crossword corpus, which is private for rights reasons; this repo holds only
metadata (dates, titles, constructors), never the puzzles or page images.

## Updating

```bash
python tools/build_status.py --gxd ../gxd-upstream --harvest ../xword-ocr/harvests/bostonglobe
python tools/render.py   # optional: preview site/index.html locally
```

`build_status.py` reads gxd master and the open merge request branches, so
fetch them first (`git -C ../gxd-upstream fetch origin`), and update its
`REFS` list when a merge request opens or lands. Commit `status.tsv`; the page
rebuilds on push.
