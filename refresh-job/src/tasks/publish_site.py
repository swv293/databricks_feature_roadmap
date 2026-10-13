"""Task 5: rebuild the tracker page from Unity Catalog and publish it to the site volume.

Exports features (with live TRB status and open TRB questions), domains, the recent-changes feed,
about 3 months of change history, and run metadata as JSON, then runs scripts/build_site.py, the same builder used locally.
The tiles are computed in the browser from FEATURES, so they update with the data."""
import sys
sys.path.insert(0, sys.argv[sys.argv.index("--src") + 1])

import datetime as dt  # noqa: E402
import json  # noqa: E402
import pathlib  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402

from feature_tracker import history  # noqa: E402
from feature_tracker.common import args, spark, trb_questions_by_key, trb_status_by_key  # noqa: E402

a = args({"--feed-days": {"default": "60"},
          "--mockup-banner": {"default": "on", "choices": ["on", "off"]}})
s = spark()
root = pathlib.Path(a.bundle_root)
trb = trb_status_by_key(s, a)

features = []
for r in s.sql(f"SELECT * FROM {a.fq}.features ORDER BY domain, parent_id NULLS FIRST, name").collect():
    features.append({
        "id": r.feature_id, "name": r.name, "domain": r.domain, "parent": r.parent_id,
        "dbxPhase": r.dbx_phase, "enterpriseStatus": trb.get(r.feature_key, "Not Reviewed"),
        "priority": r.priority or "Low", "useCases": list(r.use_cases or []), "docLink": r.doc_link,
        "limitations": r.limitations or "", "objections": r.objections or "", "expected": r.expected,
        "blurb": r.blurb or "", "lastVerified": r.last_verified.isoformat(), "isNew": r.is_new,
    })

feed = [{"date": r.pub_date.isoformat(), "p": r.new_phase, "title": r.title, "link": r.link, "domain": r.domain}
        for r in s.sql(f"""
          SELECT i.pub_date, c.new_phase, i.title, i.link, c.domain
          FROM {a.fq}.proposed_changes c JOIN {a.fq}.feed_items i USING (guid)
          WHERE c.change_type <> 'CONFIRM' AND c.decision <> 'REJECTED'
            AND i.pub_date >= date_sub(current_date(), {int(a.feed_days)})
          ORDER BY i.pub_date DESC LIMIT 40""").collect()]

held = s.sql(f"SELECT count(*) n FROM {a.fq}.proposed_changes WHERE decision = 'HELD'").first().n
now = dt.datetime.now(dt.timezone.utc)
# builtAt is fixed here (not by build_site) so a local rebuild from the same data is byte-identical.
meta = {"refreshedAt": now.isoformat(timespec="seconds"), "builtAt": now.isoformat(timespec="seconds"),
        "runId": a.run_id, "heldForTriage": held}

work = pathlib.Path(tempfile.mkdtemp())
data = work / "data"
data.mkdir()
shutil.copy(root / "data" / "domains.json", data / "domains.json")
(data / "features.json").write_text(json.dumps(features))
(data / "feed.json").write_text(json.dumps(feed))
(data / "meta.json").write_text(json.dumps(meta))
(data / "trb_questions.json").write_text(json.dumps(trb_questions_by_key(s, a)))
hist = history.group([r.asDict() for r in s.sql(history.sql(a.fq, a.run_id)).collect()])
(data / "history.json").write_text(json.dumps(hist))
out = work / "index.html"
subprocess.run([sys.executable, str(root / "scripts" / "build_site.py"), "--data-dir", str(data),
                "--template", str(root / "site" / "template.html"), "--out", str(out),
                "--mockup-banner", a.mockup_banner], check=True)

vol = pathlib.Path(f"/Volumes/{a.catalog}/{a.schema}/site")
(vol / "archive").mkdir(parents=True, exist_ok=True)
shutil.copy(out, vol / "index.html")
shutil.copy(out, vol / "archive" / f"index-{now.date().isoformat()}.html")
(vol / "features.json").write_text(json.dumps(features, indent=1))
# The exact build inputs, so scripts/pull_live_data.sh can bring the repo's data/ to parity.
(vol / "data").mkdir(exist_ok=True)
for f in data.iterdir():
    shutil.copy(f, vol / "data" / f.name)

s.sql(f"""INSERT INTO {a.fq}.refresh_runs
  SELECT {a.run_id}, current_timestamp(),
         (SELECT count(*) FROM {a.fq}.feed_items WHERE first_seen_run = {a.run_id}),
         (SELECT count(*) FROM {a.fq}.proposed_changes WHERE run_id = {a.run_id} AND decision = 'APPLIED'),
         {held}, '{vol}/index.html'""")
print(f"published {len(features)} features, {len(feed)} feed items, {held} held -> {vol}/index.html")
