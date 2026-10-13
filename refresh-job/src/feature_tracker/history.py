"""Change history for the "History" panel: one entry per refresh date, newest first.

No Spark import, so the job (publish_site), local snapshots, and tests share it."""
import json

KEEP_DAYS = 92  # about 3 months of weekly runs

DECISIONS = {"APPLIED": "applied", "HELD": "held for sign-off", "ACCEPTED": "accepted, applies next run",
             "REJECTED": "rejected", "AUTO": "pending apply"}

def sql(fq, run_id=None, days=KEEP_DAYS):
    """Runs from the last `days` days plus the current run, if given (refresh_runs gets
    its row only after publish_site), each joined to the changes it proposed."""
    current = (f"""
          UNION
          SELECT {int(run_id)}, to_date(from_utc_timestamp(current_timestamp(), 'America/New_York'))"""
               if run_id is not None else "")
    return f"""
        WITH runs AS (
          SELECT run_id, to_date(from_utc_timestamp(started_at, 'America/New_York')) AS run_date
          FROM {fq}.refresh_runs WHERE started_at >= current_timestamp() - INTERVAL {int(days)} DAYS{current}
        ),
        changes AS (
          SELECT run_id, change_type, new_feature_name, feature_key, domain, old_phase, new_phase,
                 decision, guid, CAST(NULL AS STRING) AS new_value, CAST(NULL AS STRING) AS evidence_url
          FROM {fq}.proposed_changes WHERE change_type <> 'CONFIRM'
          UNION ALL   /* monthly documentation check */
          SELECT d.run_id, IF(d.field = 'limitations', 'DOC_LIMITATIONS', 'DOC_LINK'), NULL, d.feature_key,
                 f.domain, NULL, 'Docs', d.decision, NULL, d.new_value, d.evidence_url
          FROM {fq}.doc_proposals d LEFT JOIN {fq}.features f ON f.feature_key = d.feature_key
          WHERE d.decision <> 'SUPERSEDED'
        )
        SELECT r.run_date, r.run_id, c.change_type, c.new_feature_name, c.feature_key, c.domain,
               c.old_phase, c.new_phase, c.decision, i.title, coalesce(i.link, c.evidence_url) AS link,
               i.pub_date, c.new_value
        FROM runs r
        LEFT JOIN changes c ON c.run_id = r.run_id
        LEFT JOIN {fq}.feed_items i ON i.guid = c.guid
        ORDER BY r.run_date DESC, i.pub_date DESC NULLS LAST, c.feature_key"""


def _name(feature_key):
    return (feature_key or "").split("@")[0]


def group(rows):
    """rows: dicts with the columns of sql(). Returns
    [{"date", "runs", "changes": [{"type", "name", "parent", "domain", "old", "new",
                                   "decision", "title", "link", "noteDate", "value"}]}].
    DOC_LIMITATIONS / DOC_LINK rows come from the monthly docs check; "value" is the new text."""
    by_date = {}
    for r in rows:
        d = str(r["run_date"])
        e = by_date.setdefault(d, {"date": d, "runIds": set(), "changes": []})
        e["runIds"].add(str(r["run_id"]))
        if not r.get("change_type"):
            continue
        new_item = r["change_type"] in ("NEW_CHILD", "NEW_FEATURE")
        e["changes"].append({
            "type": r["change_type"],
            "name": r["new_feature_name"] if new_item else _name(r["feature_key"]),
            "parent": _name(r["feature_key"]) if r["change_type"] == "NEW_CHILD" else "",
            "domain": r.get("domain") or "",
            "old": r.get("old_phase") or "", "new": r["new_phase"],
            "decision": DECISIONS.get(r["decision"], (r["decision"] or "").lower()),
            "title": r.get("title") or "", "link": r.get("link") or "",
            "noteDate": str(r["pub_date"]) if r.get("pub_date") else "",
            "value": r.get("new_value") or "",
        })
    out = []
    for d in sorted(by_date, reverse=True):
        e = by_date[d]
        out.append({"date": d, "runs": len(e.pop("runIds")), "changes": e["changes"]})
    return out


if __name__ == "__main__":
    # Rebuild data/history.json from a Statement Execution API result on stdin:
    #   databricks api post /api/2.0/sql/statements --json '{..."statement": "<sql()>"}' \
    #     | python3 refresh-job/src/feature_tracker/history.py > data/history.json
    import sys
    res = json.load(sys.stdin)
    cols = [c["name"] for c in res["manifest"]["schema"]["columns"]]
    rows = [dict(zip(cols, r)) for r in res["result"].get("data_array", [])]
    print(json.dumps(group(rows), indent=1))
