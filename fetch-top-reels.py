#!/usr/bin/env python3
"""Fetch fresh per-reel insights for the top reels published on/after 2026-07-18.

Candidates come from the full-feed pull (Nov 7) ranked by lifetime Views; fresh
individual-post-insights calls return current values, and generate.py ranks by
those fresh numbers. Saves to top-reels-fresh.json in this directory.
"""
import json, subprocess, sys

FBID = "17841420873672821"
DASH = "/home/hatch/workspace/instagram-dashboard"
CUTOFF = "2026-07-18"

raw = json.load(open("/home/hatch/workspace/all_68_reels_views.json"))
all_reels = raw["reels"] if isinstance(raw, dict) else raw
print("loaded", len(all_reels), "keys:", sorted(all_reels[0].keys()))

def pub(r):
    return (r.get("published_at") or r.get("published") or r.get("date") or "")[:10]

cands = [r for r in all_reels if pub(r) >= CUTOFF]
cands.sort(key=lambda r: r.get("views") or 0, reverse=True)
top = cands[:15]
print("candidates from Jul 18:", len(cands), "| fetching top", len(top))

WANT = ["views", "viewers", "likes", "comments", "shares", "saves", "reposts",
        "follows", "avg_watch_time_ms", "skip_rate", "initial_plays",
        "non_follower_views", "follower_views"]

def total(m, k):
    v = m.get(k)
    if isinstance(v, dict):
        return v.get("total")
    return v

def find_metrics(obj):
    """Map the raw individual-post-insights metrics block to flat fields."""
    d = obj.get("data") or obj
    m = d.get("metrics", {}) or {}
    vc = m.get("instagram_organic_media_content_views_count") or {}
    bd = vc.get("organic_follower_breakdown", {}) if isinstance(vc, dict) else {}
    return {
        "views": total(m, "instagram_organic_media_content_views_count"),
        "follower_views": bd.get("follower"),
        "non_follower_views": bd.get("non_follower"),
        "initial_plays": total(m, "ig_clips_play_count"),
        "viewers": m.get("instagram_organic_media_content_meta_viewer_count"),
        "likes": total(m, "ig_total_likes_count"),
        "comments": total(m, "ig_total_comments_count"),
        "shares": total(m, "ig_total_shares_count"),
        "saves": total(m, "ig_total_saves_count"),
        "reposts": total(m, "instagram_media_repost_count"),
        "interactions": total(m, "ig_total_media_interactions_count"),
        "avg_watch_time_ms": m.get("ig_reels_avg_watch_time"),
        "skip_rate": m.get("ig_reels_skip_rate"),
        "follows": total(m, "instagram_organic_media_follow_count"),
    }

results = []
for i, r in enumerate(top):
    pid = r.get("post_id") or r.get("media_id") or r.get("id")
    cmd = ["/opt/hatch/bin/instagram-cli", "individual-post-insights",
           "--account-id", FBID, "--post", pid]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except Exception as e:
        print(f"{i+1}/{len(top)} {pid} EXCEPTION {e}", flush=True)
        continue
    if p.returncode != 0:
        print(f"{i+1}/{len(top)} {pid} FAILED {p.stderr[:200]}", flush=True)
        continue
    try:
        data = json.loads(p.stdout)
    except Exception:
        print(f"{i+1}/{len(top)} {pid} BAD JSON", flush=True)
        continue
    m = find_metrics(data)
    if m.get("views") is None:
        print(f"{i+1}/{len(top)} {pid} NO VIEWS in {str(data)[:300]}", flush=True)
        continue
    m["post_id"] = pid
    m["url"] = r.get("url")
    m["caption"] = r.get("caption")
    m["published_at"] = r.get("published_at")
    results.append(m)
    print(f"{i+1}/{len(top)} {pid} OK views={m.get('views')}", flush=True)

with open(f"{DASH}/top-reels-fresh.json", "w") as f:
    json.dump(results, f, indent=1)
print("DONE", len(results), "of", len(top))
