"""Local preview of what the weekly job would propose, with no Databricks access needed.

    python3 refresh-job/src/dry_run.py --days 28 [--feed /path/feed.xml | --feed-url <url>]

Uses deterministic name matching only; on Databricks the job also asks an LLM to
match items this pass leaves unmatched.
"""
import argparse
import collections
import datetime as dt
import json
import pathlib
import sys
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from feature_tracker import feed, rules  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--feed", type=pathlib.Path)
    ap.add_argument("--feed-url", default=feed.FEED_URL)
    ap.add_argument("--as-of", type=dt.date.fromisoformat, default=dt.date.today())
    a = ap.parse_args()

    raw = a.feed.read_bytes() if a.feed else urllib.request.urlopen(a.feed_url, timeout=30).read()
    features = json.loads((ROOT / "data" / "features.json").read_text())
    by_key = {f"{f['name']}@{f['domain']}": f for f in features}

    items = [i for i in feed.parse_feed(raw) if (a.as_of - i["pub_date"]).days <= a.days]
    tally = collections.Counter()
    print(f"{len(items)} unique feed items in the last {a.days} days\n")
    for i in sorted(items, key=lambda x: x["pub_date"], reverse=True):
        if feed.is_noise(i["title"]):
            tally["skipped (model catalog / version churn)"] += 1
            continue
        phase = feed.detect_phase(i["title"], i["description"], i["categories"])
        if not phase:
            tally["skipped (no phase signal)"] += 1
            continue
        domain = feed.map_domain(i["categories"])
        key, coverage = rules.name_match(i["title"], features, domain)
        relation = rules.relation_from_coverage(coverage) if key else None
        if not key:
            key = rules.category_parent(i["categories"], features)
            relation = "child" if key else None
        f = by_key.get(key)
        ctype, decision, reason = rules.decide(phase, f, f["enterpriseStatus"] if f else None, relation, 1.0)
        tally[f"{ctype} / {decision}"] += 1
        print(f"{i['pub_date']}  {phase:<15} {decision:<5} {ctype:<12} {key or '—'}")
        print(f"            {i['title'][:100]}\n            -> {reason}")
    print("\nSummary:", dict(tally))


if __name__ == "__main__":
    main()
