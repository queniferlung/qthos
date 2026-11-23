# @queniferlung — Account Dashboard

A public dashboard of Instagram account performance for @queniferlung (Quen).

## What it shows

- **Followers**, **Aggregated account level views from IG and FB** (last 28 days), **Viewers**, **Profile visits**, and **Follower growth** (last 28 days)
- Daily trend charts, Nov 12–22, 2026
- The race for 4th place by lifetime Views: the Sep 23 Fisher reel vs the Nov 12 vulnerability reel
- Top 10 reels by lifetime Views, with Likes, Shares, Follows, and Reels skip rate
- Overnight movement per daily refresh (like-for-like)

## Data

- Per-reel figures are lifetime figures from Instagram's owned-post insights.
- Account totals cover the last 28 days as a rolling window — falls in that line usually mean big days sliding out of the window, not a drop in daily performance.
- Daily changes are like-for-like across the reels present in both snapshots.
- Data is refreshed from the daily 7:41am ET tracker snapshot. `data.json` holds the numbers behind the page; `generate.py` rebuilds it from the daily snapshot payloads.

## Updating

Re-run `generate.py` after each daily snapshot lands, then commit and push.
