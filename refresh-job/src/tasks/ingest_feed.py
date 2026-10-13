"""Task 1: fetch the release-notes RSS feed (--feed-url, bundle var feed_url) and append
unseen items to feed_items.

Serverless needs outbound HTTPS to the feed's host (docs.databricks.com, or
learn.microsoft.com for Azure). If the workspace uses serverless egress controls, add
that host to the network policy allowlist."""
import sys
sys.path.insert(0, sys.argv[sys.argv.index("--src") + 1])

import datetime as dt  # noqa: E402
import urllib.request  # noqa: E402

from feature_tracker import feed  # noqa: E402
from feature_tracker.common import args, spark  # noqa: E402

a = args({"--feed-url": {"default": feed.FEED_URL}})
s = spark()

print(f"feed: {a.feed_url}")
req = urllib.request.Request(a.feed_url, headers={"User-Agent": "databricks-feature-tracker/1.0"})
items = feed.parse_feed(urllib.request.urlopen(req, timeout=60).read())
now = dt.datetime.now(dt.timezone.utc)
rows = [{**i, "first_seen_run": a.run_id, "ingested_at": now} for i in items]

target = s.table(f"{a.fq}.feed_items")
s.createDataFrame(rows, schema=target.schema).createOrReplaceTempView("incoming")
s.sql(f"""
  MERGE INTO {a.fq}.feed_items t USING incoming i ON t.guid = i.guid
  WHEN NOT MATCHED THEN INSERT *
""")
new = s.sql(f"SELECT count(*) n FROM {a.fq}.feed_items WHERE first_seen_run = {a.run_id}").first().n
print(f"feed: {len(items)} unique items, {new} new this run")
