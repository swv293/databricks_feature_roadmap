"""Task 0: create the tracker tables if missing, and seed features from data/features.json
on the first run. Idempotent: an existing, non-empty features table is never reseeded."""
import sys
sys.path.insert(0, sys.argv[sys.argv.index("--src") + 1])

import datetime as dt  # noqa: E402
import json  # noqa: E402
import pathlib  # noqa: E402

from feature_tracker.common import args, spark  # noqa: E402

a = args()
s = spark()
root = pathlib.Path(a.bundle_root)

ddl = (root / "refresh-job" / "sql" / "tracker_ddl.sql").read_text()
ddl = ddl.replace("${catalog}", a.catalog).replace("${schema}", a.schema)
for stmt in ddl.split(";\n"):
    body = "\n".join(l for l in stmt.splitlines() if not l.strip().startswith("--")).strip()
    if body:
        s.sql(body)

if s.sql(f"SELECT 1 FROM {a.fq}.features LIMIT 1").count() == 0:
    seed = json.loads((root / "data" / "features.json").read_text())
    today = dt.date.today()
    now = dt.datetime.now(dt.timezone.utc)
    rows = [{
        "feature_key": f"{f['name']}@{f['domain']}", "feature_id": f["id"], "name": f["name"],
        "domain": f["domain"], "parent_id": f["parent"], "dbx_phase": f["dbxPhase"],
        "expected": f["expected"], "doc_link": f["docLink"], "blurb": f["blurb"],
        "use_cases": f["useCases"], "priority": f["priority"], "limitations": f["limitations"],
        "objections": f["objections"], "seed_trb_status": f["enterpriseStatus"],
        "phase_source": "seed", "phase_evidence": None, "is_new": False,
        "first_seen": today, "last_verified": dt.date.fromisoformat(f["lastVerified"]), "updated_at": now,
    } for f in seed]
    target = s.table(f"{a.fq}.features")
    s.createDataFrame(rows, schema=target.schema).write.mode("append").saveAsTable(f"{a.fq}.features")
    print(f"seeded {len(rows)} features")
else:
    print("features table already populated; no reseed")
