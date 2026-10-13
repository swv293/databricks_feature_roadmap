"""Monthly task: apply AUTO and ACCEPTED doc proposals to features.

Writes only limitations and doc_link. A dead-link proposal has no new value until a
person fills one in when accepting it, so those are skipped until then."""
import sys
sys.path.insert(0, sys.argv[sys.argv.index("--src") + 1])

from feature_tracker.common import args, spark  # noqa: E402

a = args()
s = spark()
T, P = f"{a.fq}.features", f"{a.fq}.doc_proposals"

s.sql(f"""CREATE OR REPLACE TEMP VIEW doc_todo AS
  SELECT * FROM {P}
  WHERE decision IN ('AUTO', 'ACCEPTED') AND field IN ('limitations', 'doc_link')
    AND NOT (field = 'doc_link' AND coalesce(new_value, '') = '')
  QUALIFY row_number() OVER (PARTITION BY feature_key, field ORDER BY created_at DESC) = 1""")
n = s.sql("SELECT count(*) n FROM doc_todo").first().n

for field in ("limitations", "doc_link"):
    s.sql(f"""MERGE INTO {T} f USING (SELECT * FROM doc_todo WHERE field = '{field}') c
              ON f.feature_key = c.feature_key
              WHEN MATCHED THEN UPDATE SET {field} = c.new_value, updated_at = current_timestamp()""")
s.sql(f"""MERGE INTO {P} p USING doc_todo t ON p.proposal_id = t.proposal_id
          WHEN MATCHED THEN UPDATE SET decision = 'APPLIED', applied_at = current_timestamp()""")
# Older AUTO/ACCEPTED rows for the same feature and field must never be applied later.
s.sql(f"""MERGE INTO {P} p USING (SELECT DISTINCT feature_key, field FROM doc_todo) t
          ON p.feature_key = t.feature_key AND p.field = t.field AND p.decision IN ('AUTO', 'ACCEPTED')
          WHEN MATCHED THEN UPDATE SET decision = 'SUPERSEDED'""")
print(f"applied {n} doc proposals")
