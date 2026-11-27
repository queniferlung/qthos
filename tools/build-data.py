#!/usr/bin/env python3
"""Rebuild data.json for the qthos.co dashboard.

Usage:
    python3 tools/build-data.py VIEWS.html FOLLOWERS.html [CONTENT.csv]

VIEWS.html and FOLLOWERS.html are the daily "Views by day" and "Followers by
day" tables from the stats email.

CONTENT.csv is an Instagram "Content insights" export. When given, it sets:
  - "content": views per publish day (the sum of the Views column for
    everything posted that day, zero for days with no posts). This feeds the
    "Views" tile. Rows with a blank Views cell count as zero.
  - "monthly": the newest publish month is set to that month's Views sum.
    Older months are left alone, so hand-filled figures survive.
Without CONTENT.csv both are carried over unchanged from data.json.
"""
import csv, json, os, re, sys
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data.json")
SINCE = "2026-07-15"
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


def content_views(csv_path):
    """{publish day: views} from a Content insights CSV."""
    days = {}
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            day = (row.get("Publish date") or "")[:10]
            if DAY.fullmatch(day):
                days[day] = days.get(day, 0) + int((row.get("Views") or "0").strip() or 0)
    if not days:
        sys.exit("No rows found in the content CSV.")
    return days


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

    monthly, content, lifetime = [], [], None
    if os.path.exists(OUT):
        previous = json.load(open(OUT, encoding="utf-8"))
        monthly = previous.get("monthly", [])
        lifetime = previous.get("lifetimeViews")
        content = previous.get("content", [])

    if content_path:
        days = content_views(content_path)
        updated = max(views[-1][0], followers[-1][0])
        day, last = date.fromisoformat(SINCE), date.fromisoformat(max(updated, max(days)))
        content = []
        while day <= last:
            content.append([day.isoformat(), days.get(day.isoformat(), 0)])
            day += timedelta(days=1)
        month = max(days)[:7]
        total = sum(v for d, v in days.items() if d.startswith(month))
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
        "since": SINCE,
        "viewsLump": {"from": "2026-07-15", "to": _day_before(views[0][0]), "views": lump},
        "views": views,
        "followers": followers,
        "content": content,
        "monthly": monthly,
    }
    if lifetime:
        # Lifetime total as Instagram shows it, set by hand in data.json. The
        # page fits the early no-daily-data period to make the graph reach it.
        data["lifetimeViews"] = lifetime
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
