#!/usr/bin/env python3
"""Fill in thumbnail URLs for the top reels.

Sources, in order: the daily snapshot payloads (Nov 12-22, each reel carries
thumbnail_url), then a direct `post --id` lookup for any reel still missing
one. Saves thumbnails.json {post_id: thumbnail_url} in this directory.
Thumbnail URLs are Instagram CDN links; the daily 9am update re-fetches them
so they stay fresh.
"""
import json, subprocess, glob

FBID = "17841420873672821"
BASE = "/home/hatch/workspace/goals/instagram-reels-tracker/files"
DASH = "/home/hatch/workspace/instagram-dashboard"

thumbs = {}
for f in sorted(glob.glob(f"{BASE}/2026-11-*-snapshot-payload.json")):
    for r in json.load(open(f))["reels"]:
        if r.get("thumbnail_url"):
            thumbs[r["post_id"]] = r["thumbnail_url"]

fresh = json.load(open(f"{DASH}/top-reels-fresh.json"))
fresh.sort(key=lambda r: r.get("views") or 0, reverse=True)
need = [r for r in fresh[:10] if r["post_id"] not in thumbs]
print("have", len(thumbs), "from snapshots; need", len(need), "via post lookup")

def find_thumb(obj):
    if isinstance(obj, dict):
        if obj.get("thumbnail_url"):
            return obj["thumbnail_url"]
        for v in obj.values():
            t = find_thumb(v)
            if t:
                return t
    elif isinstance(obj, list):
        for v in obj:
            t = find_thumb(v)
            if t:
                return t
    return None

for r in need:
    pid = r["post_id"]
    try:
        p = subprocess.run(["/opt/hatch/bin/instagram-cli", "post", "--id", pid,
                            "--account-id", FBID],
                           capture_output=True, text=True, timeout=60)
        t = find_thumb(json.loads(p.stdout)) if p.returncode == 0 else None
    except Exception as e:
        t = None
        print(pid, "EXCEPTION", e)
    if t:
        thumbs[pid] = t
        print(pid, "OK")
    else:
        print(pid, "NO THUMBNAIL")

with open(f"{DASH}/thumbnails.json", "w") as f:
    json.dump(thumbs, f, indent=1)
top10 = [r["post_id"] for r in fresh[:10]]
print("top 10 covered:", sum(1 for p in top10 if p in thumbs), "of 10")
