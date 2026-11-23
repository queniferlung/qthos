#!/usr/bin/env python3
"""Build the @queniferlung dashboard data (v2, graph-first).

Sources:
- 90-day account time series (analytics-account-insights --include-time-series):
  daily Views, Viewers, Net followers, Interactions, Aug 24-Nov 22, 2026.
- Jul 18-Nov 22 window totals (account-insights --start-date/--end-date).
- Daily snapshot payloads Nov 12-22 (30 most recent reels + account totals).
- Fresh per-reel insights for the top reels published on/after Jul 18
  (top-reels-fresh.json, from individual-post-insights).

Instagram only keeps 90 days of daily history, so daily charts start Aug 24
even though the dashboard range starts Jul 18; reel-level data covers Jul 18.
"""
import json, glob, os

BASE = "/home/hatch/workspace/goals/instagram-reels-tracker/files"
DASH = "/home/hatch/workspace/instagram-dashboard"
OUT = DASH

def first_val(lst):
    if isinstance(lst, list) and lst and isinstance(lst[0], dict):
        return lst[0].get("value")
    return None

# ---- 90-day daily series ----
ts = json.load(open(f"{BASE}/2026-11-22-account-90d-timeseries.json"))
acct = ts["accounts"][0]
daily = {
    "views": acct.get("views_over_time", []),
    "viewers": acct.get("viewers_over_time", []),
    "interactions": acct.get("interactions_over_time", []),
    "netFollowers": acct.get("net_followers_over_time", {}).get("overall", []),
    "follows": acct.get("net_followers_over_time", {}).get("follows", []),
    "unfollows": acct.get("net_followers_over_time", {}).get("unfollows", []),
}

# ---- Jul 18 - Nov 22 window totals ----
jul = json.load(open(f"{BASE}/2026-11-22-account-jul18-nov22.json"))
window_totals = {
    "start": "2026-07-18",
    "end": "2026-11-22",
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

# ---- Nov 12-22 snapshot series (30 most recent reels) ----
payloads = []
for f in sorted(glob.glob(f"{BASE}/2026-11-*-snapshot-payload.json")):
    payloads.append(json.load(open(f)))
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

# Fisher vs vulnerability race
race = {"dates": [], "fisher": [], "vulnerability": []}
for d in payloads:
    by_cap = {}
    for r in d["reels"]:
        c = (r.get("caption") or "").lower()
        if "fisher" in c:
            by_cap["fisher"] = r.get("views")
        if "vulnerability as a weakness" in c:
            by_cap["vulnerability"] = r.get("views")
    if "fisher" in by_cap and "vulnerability" in by_cap:
        race["dates"].append(d["captured_at"][:10])
        race["fisher"].append(by_cap["fisher"])
        race["vulnerability"].append(by_cap["vulnerability"])

# ---- Top reels (published on/after Jul 18), fresh insights ----
raw68 = json.load(open("/home/hatch/workspace/all_68_reels_views.json"))
by_id = {r["post_id"]: r for r in raw68["reels"]}
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

latest = payloads[-1]
data = {
    "generatedAt": latest["captured_at"],
    "username": "queniferlung",
    "displayName": "Quen",
    "bio": "helping you become a systems thinker — turning messy ideas into diagrams",
    "rangeStart": "2026-07-18",
    "daily": daily,
    "windowTotals": window_totals,
    "series": series,
    "race": race,
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

os.makedirs(OUT, exist_ok=True)
with open(f"{OUT}/data.json", "w") as f:
    json.dump(data, f, indent=1)

print("daily views points:", len(daily["views"]), daily["views"][0], "->", daily["views"][-1])
print("daily net followers points:", len(daily["netFollowers"]))
print("window totals:", window_totals)
print("top reel:", top[0]["caption"], top[0]["views"])
print("top reels:", len(top))
print("data.json written")
