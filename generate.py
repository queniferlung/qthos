#!/usr/bin/env python3
"""Build the @queniferlung dashboard data (v4).

Range: Jul 15, 2026 onwards (all data from Jul 15).

Sources:
- Daily follower counts Jul 15-now (analytics-follower-count-delta --days 140,
  merged with the previous data.json so the Jul 15 start is never lost as the
  rolling window slides).
- 90-day account time series (analytics-account-insights --include-time-series):
  daily Views, Viewers, Interactions, Aug 27-now (Instagram keeps 90 days).
- Jul 15-now window totals (account-insights --start-date 2026-07-15).
- Daily snapshot payloads Nov 12-now (30 most recent reels + account totals).
- Fresh per-reel insights for the top reels published on/after Jul 15
  (top-reels-fresh.json) + thumbnails (thumbnails.json).
- Full feed list (all_68_reels_views.json) + latest snapshot payload for
  monthly average views per reel by posting month.
- Profile (latest *-profile.json): posts count, bio, verified badge.

Lifetime views chart is cumulative: the Jul 15-Aug 26 lump (window total
minus the sum of daily views) plus the running sum of daily views from
Aug 27, so the line ends at the true window total.
"""
import base64, json, glob, os
from datetime import date, timedelta
from collections import Counter, defaultdict

BASE = "/home/hatch/workspace/goals/instagram-reels-tracker/files"
DASH = "/home/hatch/workspace/instagram-dashboard"
START = "2026-07-15"

def first_val(lst):
    if isinstance(lst, list) and lst and isinstance(lst[0], dict):
        return lst[0].get("value")
    return None

def latest(pattern):
    return sorted(glob.glob(pattern))[-1]

# ---- Daily follower counts, Jul 15-now (merge with previous data.json) ----
fds = json.load(open(latest(f"{BASE}/*-follower-daily-series.json")))
fresh_fd = {
    p["date"]: {"date": p["date"], "followers": p["followers_count"], "change": p.get("daily_change")}
    for p in fds["accounts"][0]["daily_series"]
}
merged_fd = {}
old_path = f"{DASH}/data.json"
if os.path.exists(old_path):
    try:
        old = json.load(open(old_path))
        for p in old.get("followersDaily", []):
            merged_fd[p["date"]] = p
    except Exception:
        pass
merged_fd.update(fresh_fd)
followers_daily = [merged_fd[d] for d in sorted(merged_fd) if d >= START]

# ---- 90-day daily series (latest pull) ----
ts = json.load(open(latest(f"{BASE}/*-account-90d-timeseries.json")))
acct = ts["accounts"][0]
daily = {
    "views": acct.get("views_over_time", []),
    "viewers": acct.get("viewers_over_time", []),
    "interactions": acct.get("interactions_over_time", []),
    "netFollowers": acct.get("net_followers_over_time", {}).get("overall", []),
}

# ---- Jul 15-now window totals (latest pull) ----
jul = json.load(open(latest(f"{BASE}/*-account-jul15-*.json")))
window_totals = {
    "start": START,
    "end": None,  # displayed as "to now"; see latest snapshot date below
    "contentViews": first_val(jul.get("content_views")),
    "viewers": first_val(jul.get("viewers")),
    "likes": first_val(jul.get("likes")),
    "comments": first_val(jul.get("comments")),
    "shares": first_val(jul.get("shares")),
    "saves": first_val(jul.get("saves")),
    "profileVisits": first_val(jul.get("profile_visits")),
    "engagedAccounts": first_val(jul.get("engaged_accounts")),
    "totalInteractions": first_val(jul.get("total_interactions")),
}

# ---- Snapshot series (30 most recent reels) ----
payloads = [json.load(open(f)) for f in sorted(glob.glob(f"{BASE}/2026-11-*-snapshot-payload.json"))]
series = []
for d in payloads:
    a = d["account"]
    reels = d["reels"]
    series.append({
        "date": d["captured_at"][:10],
        "followers": a.get("follower_count"),
        "views28d": a.get("views_28d"),
        "viewers28d": a.get("viewers_28d"),
        "profileVisits28d": a.get("profile_visits_28d"),
        "followerGrowth28d": a.get("follower_growth_28d"),
        "totalViews30": sum((r.get("views") or 0) for r in reels),
        "totalLikes30": sum((r.get("likes") or 0) for r in reels),
    })
latest_date = series[-1]["date"]
window_totals["end"] = latest_date  # window runs Jul 15 to the latest snapshot ("to now")

# ---- Reels published per day, Jul 15-latest ----
raw68 = json.load(open("/home/hatch/workspace/all_68_reels_views.json"))
by_id = {r["post_id"]: r for r in raw68["reels"]}
counts = Counter()
for r in raw68["reels"]:
    dd = (r.get("date") or "")[:10]
    if START <= dd <= latest_date:
        counts[dd] += 1
reels_per_day = []
d = date(2026, 7, 15)
end = date.fromisoformat(latest_date)
while d <= end:
    ds = d.isoformat()
    reels_per_day.append({"date": ds, "count": counts.get(ds, 0)})
    d += timedelta(days=1)

# ---- Monthly average views per reel, by posting month (Jul-Nov) ----
# Combined set: full 68-reel list (Nov 7 vintage) overlaid with the latest
# snapshot's 30 most recent reels (fresh views). Average = lifetime views
# per reel posted that month, as of the latest snapshot.
combined = {}
for r in raw68["reels"]:
    combined[r["post_id"]] = {"date": (r.get("date") or "")[:10], "views": r.get("views") or 0}
for r in payloads[-1]["reels"]:
    combined[r["post_id"]] = {"date": (r.get("published_at") or "")[:10], "views": r.get("views") or 0}
by_month = defaultdict(list)
for r in combined.values():
    dd = r["date"]
    if START <= dd <= latest_date:
        by_month[dd[:7]].append(r["views"])
MONTH_NAMES = {"07": "Jul", "08": "Aug", "09": "Sep", "10": "Oct", "11": "Nov"}
MONTH_FULL = {"07": "July", "08": "August", "09": "September", "10": "October", "11": "November"}
monthly_avg = []
for ym in sorted(by_month):
    vals = by_month[ym]
    mm = ym[5:7]
    monthly_avg.append({
        "month": MONTH_NAMES.get(mm, mm),
        "label": f"{MONTH_FULL.get(mm, mm)} 2026",
        "avgViews": round(sum(vals) / len(vals)),
        "reels": len(vals),
    })

# ---- Lifetime views, cumulative (lump Jul 15-Aug 26 + daily from Aug 27) ----
daily_sum = sum((p.get("value") or 0) for p in daily["views"])
lump = (window_totals["contentViews"] or 0) - daily_sum
cum = lump
lifetime_cumulative = []
for p in daily["views"]:
    cum += p.get("value") or 0
    lifetime_cumulative.append({"date": p["date"], "value": cum})

# ---- Top reels (published on/after Jul 15), fresh insights + thumbnails ----
thumbs = json.load(open(f"{DASH}/thumbnails.json")) if os.path.exists(f"{DASH}/thumbnails.json") else {}
fresh = json.load(open(f"{DASH}/top-reels-fresh.json"))
fresh.sort(key=lambda r: r.get("views") or 0, reverse=True)
top = []
for i, r in enumerate(fresh[:10]):
    base = by_id.get(r["post_id"], {})
    views = r.get("views") or 0
    cap = (base.get("caption") or r.get("caption") or "").split("\n")[0].strip()[:80]
    top.append({
        "rank": i + 1,
        "date": (base.get("date") or "")[:10],
        "caption": cap,
        "url": base.get("url") or r.get("url"),
        "thumbnail": thumbs.get(r["post_id"]),
        "views": views,
        "viewers": r.get("viewers"),
        # Instagram's confirmed ranking-signal order (Mosseri, Jan 2025):
        # watch time first, then likes per reach, then sends per reach,
        # then saves, reposts, comments, follows.
        "avgWatchTimeMs": r.get("avg_watch_time_ms"),
        "skipRate": round(r["skip_rate"] * 100, 1) if r.get("skip_rate") is not None else None,
        "likes": r.get("likes"),
        "likeRate": round((r.get("likes") or 0) / views * 100, 1) if views else None,
        "shares": r.get("shares"),
        "shareRate": round((r.get("shares") or 0) / views * 100, 2) if views else None,
        # Per-reel saves come back as 0 from the insights endpoint even though
        # the account total is 143,196 for the same window, so the field is
        # effectively unpopulated per reel: show as unavailable, not zero.
        "saves": None,
        "reposts": r.get("reposts"),
        "comments": r.get("comments"),
        "follows": r.get("follows"),
    })

# ---- Profile (latest profile pull) ----
profile = {"posts": None, "bio": "helping you become a systems thinker — turning messy ideas into diagrams",
           "verified": False, "following": None}
prof_files = sorted(glob.glob(f"{BASE}/*-profile.json"))
if prof_files:
    try:
        p = json.load(open(prof_files[-1]))["profiles"][0]
        profile = {
            "posts": p.get("post_count"),
            "bio": p.get("bio") or profile["bio"],
            "verified": bool(p.get("is_verified")),
            "following": p.get("following_count"),
        }
    except Exception:
        pass
pic_b64 = None
pic_path = "/home/hatch/workspace/profile-images/user-profile-reference.jpg"
if os.path.exists(pic_path):
    pic_b64 = "data:image/jpeg;base64," + base64.b64encode(open(pic_path, "rb").read()).decode()

latest = payloads[-1]
data = {
    "generatedAt": latest["captured_at"],
    "username": "queniferlung",
    "displayName": "Quen",
    "bio": profile["bio"],
    "profile": {**profile, "profilePic": pic_b64},
    "rangeStart": START,
    "followersDaily": followers_daily,
    "reelsPerDay": reels_per_day,
    "daily": daily,
    "lifetimeCumulative": lifetime_cumulative,
    "monthlyAvgViews": monthly_avg,
    "windowTotals": window_totals,
    "series": series,
    "topReels": top,
    "medianReelViews": 11240,
    "latest": {
        "followers": latest["account"].get("follower_count"),
        "views28d": latest["account"].get("views_28d"),
        "viewers28d": latest["account"].get("viewers_28d"),
        "profileVisits28d": latest["account"].get("profile_visits_28d"),
        "followerGrowth28d": latest["account"].get("follower_growth_28d"),
        "totalViews30": series[-1]["totalViews30"],
        "totalLikes30": series[-1]["totalLikes30"],
    },
}

os.makedirs(DASH, exist_ok=True)
with open(f"{DASH}/data.json", "w") as f:
    json.dump(data, f, indent=1)

print("followers daily:", len(followers_daily), followers_daily[0], "->", followers_daily[-1])
print("reels per day points:", len(reels_per_day), "total reels:", sum(p["count"] for p in reels_per_day))
print("daily views points:", len(daily["views"]))
print("lifetime cumulative:", len(lifetime_cumulative), "lump Jul 15-Aug 26:", lump,
      "->", lifetime_cumulative[-1] if lifetime_cumulative else None)
print("monthly avg:", [(m["month"], m["avgViews"], m["reels"]) for m in monthly_avg])
print("profile:", {k: v for k, v in profile.items() if k != "bio"}, "| pic:", bool(pic_b64))
print("top reel:", top[0]["caption"], top[0]["views"], "| thumbs:", sum(1 for r in top if r["thumbnail"]), "of", len(top))
print("data.json written")
