"""Task 4: apply AUTO proposals and HELD proposals a person marked ACCEPTED.

Writes only Axis A columns (dbx_phase, phase_source, phase_evidence, last_verified)
and inserts new rows as Not Reviewed / Low. Curated columns and TRB tables are untouched."""
import sys
sys.path.insert(0, sys.argv[sys.argv.index("--src") + 1])

from feature_tracker.common import args, spark  # noqa: E402

a = args()
s = spark()
T, PC, FI = f"{a.fq}.features", f"{a.fq}.proposed_changes", f"{a.fq}.feed_items"

s.sql(f"""CREATE OR REPLACE TEMP VIEW todo AS
  SELECT c.*, i.link, i.pub_date FROM {PC} c JOIN {FI} i USING (guid)
  WHERE c.decision IN ('AUTO', 'ACCEPTED') AND c.applied_at IS NULL""")

# Phase changes and confirmations. If one feature has several items in a run, the latest note wins.
s.sql(f"""
  MERGE INTO {T} f
  USING (SELECT * FROM todo WHERE change_type IN ('PHASE_CHANGE', 'CONFIRM')
         QUALIFY row_number() OVER (PARTITION BY feature_key ORDER BY pub_date DESC) = 1) c
  ON f.feature_key = c.feature_key
  WHEN MATCHED THEN UPDATE SET
    dbx_phase      = c.new_phase,
    phase_source   = CASE WHEN c.change_type = 'PHASE_CHANGE' THEN 'feed' ELSE f.phase_source END,
    phase_evidence = c.link,
    last_verified  = greatest(f.last_verified, c.pub_date),
    updated_at     = current_timestamp()
""")

# New top-level features and children. Their keys come from the generated name; an
# existing key means the feature is already tracked, so nothing is inserted.
s.sql(f"""
  MERGE INTO {T} f
  USING (
    SELECT concat(t.new_feature_name, '@', t.domain) AS feature_key,
           concat('n', substr(t.change_id, 1, 10))   AS feature_id,
           t.new_feature_name AS name, t.domain,
           CASE WHEN t.change_type = 'NEW_CHILD' THEN p.feature_id END AS parent_id,
           t.new_phase AS dbx_phase, t.link, t.pub_date,
           coalesce(p.doc_link, t.link) AS doc_link
    FROM todo t LEFT JOIN {T} p ON p.feature_key = t.feature_key
    WHERE t.change_type IN ('NEW_FEATURE', 'NEW_CHILD') AND t.domain IS NOT NULL
    QUALIFY row_number() OVER (PARTITION BY concat(t.new_feature_name, '@', t.domain) ORDER BY t.pub_date DESC) = 1
  ) n
  ON f.feature_key = n.feature_key
  WHEN NOT MATCHED THEN INSERT (
    feature_key, feature_id, name, domain, parent_id, dbx_phase, expected, doc_link, blurb, use_cases,
    priority, limitations, objections, seed_trb_status, phase_source, phase_evidence, is_new,
    first_seen, last_verified, updated_at)
  VALUES (
    n.feature_key, n.feature_id, n.name, n.domain, n.parent_id, n.dbx_phase, NULL, n.doc_link, '',
    array(), 'Low', '', '', 'Not Reviewed', 'feed', n.link, true, n.pub_date, n.pub_date, current_timestamp())
""")

s.sql(f"""MERGE INTO {PC} c USING todo t ON c.change_id = t.change_id
          WHEN MATCHED THEN UPDATE SET decision = 'APPLIED', applied_at = current_timestamp()""")
n = s.sql(f"SELECT count(*) n FROM {PC} WHERE decision = 'APPLIED' AND run_id = {a.run_id}").first().n
print(f"applied {n} changes from this run")
