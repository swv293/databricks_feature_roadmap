"""Task 2: record workspace security posture through the settings API.

The account-console Previews page has no public API, so preview enrollment is not
readable here. These are the HIPAA-relevant workspace settings that are readable."""
import sys
sys.path.insert(0, sys.argv[sys.argv.index("--src") + 1])

import datetime as dt  # noqa: E402
import json  # noqa: E402

from databricks.sdk import WorkspaceClient  # noqa: E402

from feature_tracker.common import args, spark  # noqa: E402

a = args()
s = spark()
w = WorkspaceClient()

READS = {
    "compliance_security_profile": lambda: w.settings.compliance_security_profile.get(),
    "enhanced_security_monitoring": lambda: w.settings.enhanced_security_monitoring.get(),
    "automatic_cluster_update": lambda: w.settings.automatic_cluster_update.get(),
}
now = dt.datetime.now(dt.timezone.utc)
rows = []
for name, read in READS.items():
    try:
        rows.append({"setting": name, "value_json": json.dumps(read().as_dict()), "error": None})
    except Exception as e:  # a missing permission must not fail the weekly refresh
        rows.append({"setting": name, "value_json": None, "error": f"{type(e).__name__}: {e}"[:500]})

target = s.table(f"{a.fq}.posture_snapshots")
s.createDataFrame([{"run_id": a.run_id, "captured_at": now, **r} for r in rows],
                  schema=target.schema).write.mode("append").saveAsTable(f"{a.fq}.posture_snapshots")
for r in rows:
    print(r["setting"], "ERROR " + r["error"] if r["error"] else "ok")
