#!/usr/bin/env python3
"""Rebuild status.tsv: one row per expected Boston Globe puzzle and how far it has got.

Run locally (CI can't see gxd, which is private):

    python tools/build_status.py --gxd ../gxd-upstream --harvest ../xword-ocr/harvests/bostonglobe

Expected puzzles: every Sunday from 1980 (the Globe Magazine puzzle; two rows,
harder and easier, on double-issue Sundays from notes/double-issues.tsv) and
the Themeless Week puzzles in data/puzzmo-index.json. States come from, in
order: gxd master and the open merge requests (git refs, fetched beforehand),
sources ready to export (Puzzmo, the Wayback harvest), known print puzzles
(double issues), then manual.tsv, which overrides everything for its rows.
"""
import argparse
import csv
import datetime as dt
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIRST_SUNDAY = dt.date(1980, 1, 6)
COLUMNS = ["id", "date", "series", "slot", "state", "title", "author", "gxd", "mr", "source", "note"]
# git refs for gxd master and each open merge request touching bostonglobe/, newest last.
REFS = [("origin/master", ""), ("origin/fix-bostonglobe-dates", "155"), ("origin/import-bostonglobe-wayback", "150")]


def git(gxd: Path, *args: str, data: bytes | None = None) -> bytes:
    return subprocess.run(["git", "-C", str(gxd), *args], input=data, capture_output=True, check=True).stdout


def tree(gxd: Path, ref: str) -> dict[str, str]:
    """{bostonglobe path: blob id} at ref."""
    out = {}
    for line in git(gxd, "ls-tree", "-r", ref, "bostonglobe").decode().splitlines():
        meta, path = line.split("\t", 1)
        if path.endswith(".xd"):
            out[path] = meta.split()[2]
    return out


def headers(gxd: Path, blobs: set[str]) -> dict[str, dict[str, str]]:
    """{blob: {header: value}} for the given blobs, read in one git cat-file call."""
    order = sorted(blobs)
    raw = git(gxd, "cat-file", "--batch", data="".join(b + "\n" for b in order).encode())
    out, pos = {}, 0
    for blob in order:
        nl = raw.index(b"\n", pos)
        size = int(raw[pos:nl].split()[2])
        body = raw[nl + 1 : nl + 1 + size].decode("utf-8", errors="replace")
        pos = nl + 1 + size + 1
        parts = re.split(r"\n\s*\n", body.strip())
        out[blob] = {k.strip(): v.strip() for k, v in (l.split(":", 1) for l in parts[0].splitlines() if ":" in l)}
        out[blob]["_grid"] = parts[1].strip().upper() if len(parts) > 1 else ""
    return out


def norm(title: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", title.upper())


def gxd_files(gxd: Path) -> dict[str, dict]:
    """Every bostonglobe file as it will be once the open merge requests land:
    {xdid: {path, title, author, mr}}. mr is '' when the file is already in master as is."""
    trees = {ref: tree(gxd, ref) for ref, _ in REFS}
    master = trees["origin/master"]
    final: dict[str, tuple[str, str, str]] = {}  # path -> (blob, mr)
    for path, blob in master.items():
        final[path] = (blob, "")
    for ref, mr in REFS[1:]:
        t = trees[ref]
        for path, blob in t.items():
            if master.get(path) != blob:
                final[path] = (blob, mr)
        if mr == "155":  # the re-dating also removes or moves master files
            for path in set(master) - set(t):
                if final.get(path, ("", ""))[1] == "":
                    del final[path]
    meta = headers(gxd, {b for b, _ in final.values()} | set(master.values()))
    out = {}
    for path, (blob, mr) in final.items():
        xdid = Path(path).stem
        h = meta[blob]
        edited = ""
        if mr and path in master and meta[master[path]]["_grid"] == h["_grid"]:
            mr, edited = "", f"!{mr} edits this file"  # same puzzle already in master; the MR only corrects it
        out[xdid] = {"path": path, "title": h.get("Title", ""), "author": h.get("Author", ""), "mr": mr, "edited": edited}
    return out


def read_tsv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return list(csv.DictReader(open(path, encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gxd", default="../gxd-upstream", help="gxd checkout with the REFS fetched")
    ap.add_argument("--harvest", default="../xword-ocr/harvests/bostonglobe", help="epp globe-wayback output")
    ap.add_argument("--today", default=dt.date.today().isoformat())
    a = ap.parse_args()

    files = gxd_files(Path(a.gxd))
    doubles = {r["date"]: r for r in read_tsv(ROOT / "notes" / "double-issues.tsv")}
    puzzmo = json.loads((ROOT / "data" / "puzzmo-index.json").read_text(encoding="utf-8"))
    wayback = {r["sunday"]: r for r in read_tsv(Path(a.harvest) / "wayback-sundays.tsv") if r["status"].startswith("found")}
    manual = {(r["date"], r["slot"]): r for r in read_tsv(ROOT / "manual.tsv")}

    rows: dict[tuple[str, str], dict] = {}

    def row(date: str, series: str, slot: str, **kw) -> dict:
        r = rows.setdefault((date, slot), {c: "" for c in COLUMNS} | {"date": date, "series": series, "slot": slot, "state": "missing"})
        r.update({k: v for k, v in kw.items() if v})
        return r

    # Expected Sundays, with two rows on double-issue Sundays.
    end = dt.date.fromisoformat(a.today)
    d = FIRST_SUNDAY
    while d <= end:
        day = d.isoformat()
        if day in doubles:
            dbl = doubles[day]
            row(day, "sunday", "harder", title=dbl["harder_title"], author=dbl["harder_author"], note="double issue")
            row(day, "sunday-easier", "easier", title=dbl["easier_title"], author=dbl["easier_author"], note="double issue")
        else:
            row(day, "sunday", "")
        d += dt.timedelta(days=7)

    # Themeless Weeks from the Puzzmo queue (Globe originals on weekdays).
    for p in puzzmo:
        day = p["publishDate"][:10]
        if re.search(r"THEMELESS (WEEK|FRIDAY)", p["name"].upper()):
            row(day, "themeless-week", "", title=p["name"], author=", ".join(x.get("name", "") for x in p["authors"]),
                state="ready", source="puzzmo")

    # gxd, as it will be after the open merge requests.
    for xdid, f in files.items():
        day, suffix = xdid[2:12], xdid[12:]
        if day in doubles:
            dbl = doubles[day]
            slot = "harder" if norm(f["title"]) == norm(dbl["harder_title"]) else "easier" if norm(f["title"]) == norm(dbl["easier_title"]) else suffix or "?"
        else:
            slot = suffix
        weekday = dt.date.fromisoformat(day).weekday()
        series = "sunday" if weekday == 6 else "other"
        r = row(day, series, slot, title=f["title"], author=f["author"])
        r.update(state="in-mr" if f["mr"] else "in-gxd", gxd=xdid, mr=f["mr"] and f"!{f['mr']}", source=r["source"] or "gxd")
        if f["edited"]:
            r["note"] = "; ".join(x for x in (r["note"], f["edited"]) if x)
        if day in doubles:
            want = "" if slot == "harder" else "a"
            if suffix != want:
                r["note"] = f"double issue; named {xdid}, rule Harder=plain/Easier=a would make it bg{day}{want}"

    # Sources ready to export, for Sundays gxd doesn't have.
    for p in puzzmo:
        day = p["publishDate"][:10]
        if dt.date.fromisoformat(day).weekday() == 6:
            r = row(day, "sunday", "", title=p["name"], author=", ".join(x.get("name", "") for x in p["authors"]))
            if r["state"] == "missing":
                r.update(state="ready", source="puzzmo")
    for day, w in wayback.items():
        slot = "harder" if day in doubles else ""
        r = rows.get((day, slot))
        if r and r["state"] == "missing":
            xd = Path(a.harvest) / "bostonglobe" / day[:4] / f"bg{day}.xd"
            m = re.search(r"^Author: (.*)$", xd.read_text(encoding="utf-8"), re.M) if xd.exists() else None
            r.update(state="ready", source="wayback", title=w["title"], author=r["author"] or (m.group(1) if m else ""))

    # Known in print but not yet captured.
    for (day, slot), r in rows.items():
        if r["state"] == "missing" and day in doubles:
            r["state"] = "need-image"

    # manual.tsv rows replace what was computed for that puzzle (blank fields clear it).
    for (day, slot), m in manual.items():
        r = row(day, rows.get((day, slot), {}).get("series") or "sunday", slot)
        r.update({k: m.get(k, "") for k in ("state", "title", "author", "note")})
        if r["state"] not in ("in-gxd", "in-mr"):
            r.update(gxd="", mr="", source="print" if r["state"] == "need-image" else "")

    for r in rows.values():
        r["id"] = r["gxd"] or f"bg{r['date']}" + ("a" if r["slot"] in ("easier", "a") else "")
    out = sorted(rows.values(), key=lambda r: (r["date"], r["slot"]))
    with open(ROOT / "status.tsv", "w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(COLUMNS) + "\n")  # plain TSV: no quoting; fields never contain tabs
        f.writelines("\t".join(r[c] for c in COLUMNS) + "\n" for r in out)
    counts: dict[str, int] = {}
    for r in out:
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    print(f"status.tsv: {len(out)} rows", counts)


if __name__ == "__main__":
    main()
