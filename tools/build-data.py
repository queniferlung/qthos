#!/usr/bin/env python3
"""Rebuild data.json for the qthos.co dashboard.

Usage:
    python3 tools/build-data.py VIEWS.html FOLLOWERS.html [CONTENT.csv]

VIEWS.html and FOLLOWERS.html are the daily "Views by day" and "Followers by
day" tables from the stats email.

"monthly" in data.json is the total views on everything posted in each month.
It is carried over unchanged unless CONTENT.csv is given: an Instagram
"Content insights" export (about the last 30 days). Its newest publish month is
then set to the sum of that month's Views column; older months are left alone,
because the export only covers part of them.
"""
import csv, json, os, re, sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data.json")
ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
DAY = re.compile(r"(\d{4}-\d{2}-\d{2})")


def num(text):
    return int(re.sub(r"[^\d-]", "", text))


def rows(path):
    html = open(path, encoding="utf-8").read()
    for row in ROW.findall(html):
        cells = [re.sub(r"<[^>]+>", "", c).strip() for c in CELL.findall(row)]
        if cells:
            yield cells


def month_total(csv_path):
    """(month, views) for the newest publish month in a Content insights CSV."""
    totals = {}
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            month = (row.get("Publish date") or "")[:7]
            if month:
                totals[month] = totals.get(month, 0) + int(row.get("Views") or 0)
    if not totals:
        sys.exit("No rows found in the content CSV.")
    newest = max(totals)
    return newest, totals[newest]


def main(views_path, followers_path, content_path=None):
    lump, views = 0, []
    for cells in rows(views_path):
        day = DAY.search(cells[0])
        if "lump" in cells[0].lower():
            lump = num(cells[1])
        elif day:
            views.append([day.group(1), num(cells[1])])

    followers = []
    for cells in rows(followers_path):
        day = DAY.search(cells[0])
        if day:
            followers.append([day.group(1), num(cells[1])])

    if not views or not followers:
        sys.exit("No rows found: check the two input files.")

    monthly = []
    if os.path.exists(OUT):
        monthly = json.load(open(OUT, encoding="utf-8")).get("monthly", [])

    if content_path:
        month, total = month_total(content_path)
        for entry in monthly:
            if entry["month"] == month:
                entry["views"] = total
                break
        else:
            monthly.append({"month": month, "views": total})
        monthly.sort(key=lambda entry: entry["month"])
        print(f"monthly: {month} set to {total:,}")

    data = {
        "updated": max(views[-1][0], followers[-1][0]),
        "since": "2026-07-15",
        "viewsLump": {"from": "2026-07-15", "to": _day_before(views[0][0]), "views": lump},
        "views": views,
        "followers": followers,
        "monthly": monthly,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))
        f.write("\n")
    total = lump + sum(v for _, v in views)
    print(f"data.json: {len(views)} view days, {len(followers)} follower days, "
          f"lifetime views {total:,}, followers {followers[-1][1]:,}")


def _day_before(iso):
    d = date.fromisoformat(iso)
    return date.fromordinal(d.toordinal() - 1).isoformat()


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    main(*sys.argv[1:])
