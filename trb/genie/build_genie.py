"""Build the Review Board Genie agent definition, validate every SQL, and write artifacts.

    python3 trb/genie/build_genie.py --catalog C --profile P --warehouse-id W [--no-validate]

Writes trb/genie/genie_agent.json (parsed serialized_space), trb/genie/benchmarks.json, and
trb/genie/DELIVERABLE.md (the 8-section deliverable). Provision with the workspace
genie-provisioning scripts (create_space.py, then sync_benchmarks.py after EVERY PATCH).
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from run_sql import run  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
TITLE = "Feature Tracker Review Board Analytics Space"
DESCRIPTION = ("Answers questions about the Tech Review Board (TRB, also called the Architecture Review Board) "
               "decisions on Databricks features at Acme Health Plan: review status, PHI eligibility, approval "
               "conditions, exceptions, control mappings, meetings, and governance documents. For the platform "
               "team, security, privacy, and compliance reviewers. Data is synthetic.")


def hid(kind, n):
    return hashlib.md5(f"{kind}_{n}".encode()).hexdigest()


def lines(s):
    return [l + "\n" for l in s.strip("\n").split("\n")]


def spec(C):
    T = f"{C}.trb"
    tables = {
        f"{T}.approval_conditions": ["condition_id", "condition_title", "due_date", "verification_method", "verification_status"],
        f"{T}.control_mappings": ["control_framework", "control_id", "control_name", "implementation_status"],
        f"{T}.documents": ["doc_date", "doc_id", "doc_type", "meeting_id", "title"],
        f"{T}.exceptions": ["exception_id", "exception_status", "exception_type", "requested_by_role"],
        f"{T}.mv_trb_reviews": ["approved_scope", "business_unit", "current_dbx_phase", "decision_quarter", "domain",
                                "is_phi_eligible", "reviewer_role", "trb_status"],
        f"{T}.reviews": ["approval_meeting_id", "approved_scope", "current_trb_status", "decision_date", "domain",
                         "feature_name", "primary_reviewer_role", "requesting_business_unit", "review_id"],
        f"{T}.v_feature_phi_eligibility": ["blocking_reason", "current_dbx_phase", "current_trb_status", "domain",
                                           "feature_name", "is_phi_eligible"],
    }
    no_match = {"due_date", "decision_date", "doc_date", "decision_quarter", "is_phi_eligible"}
    data_sources = {"tables": [
        {"identifier": t, "column_configs": [
            {"column_name": c, "enable_format_assistance": True, "enable_entity_matching": c not in no_match}
            for c in sorted(cols)]}
        for t, cols in sorted(tables.items())]}

    text = f"""# PURPOSE
Answers questions about Acme Health Plan's Tech Review Board (TRB; also called the Architecture Review Board, ARB, or review board) decisions on Databricks features. Synthetic data.
# ROUTING
- PHI questions ("can we use X with PHI", "approved for PHI") -> v_feature_phi_eligibility: is_phi_eligible and blocking_reason. Never infer PHI eligibility from TRB status alone.
- Counts, rates, breakdowns by domain/status/business unit/quarter -> MEASURE() on mv_trb_reviews. Prefer MEASURE() over recomputing from reviews.
- Why a decision was made -> reviews.decision_rationale, identified_risks, mitigations, open_questions; cite documents (doc_id, summary) where array_contains(documents.review_ids, reviews.review_id).
- Conditions -> approval_conditions (open = verification_status <> 'Closed'; due_date NULL = ongoing).
- Exceptions or waivers -> exceptions joined to reviews on review_id.
- Meeting questions -> reviews.approval_meeting_id = 'TRBM-YYYY-MM-DD' and documents with doc_type = 'minutes'.
# DEFINITIONS
- PHI-eligible = current Databricks phase GA AND TRB status 'Approved'. 'Approved with Conditions' is NOT PHI-eligible.
- Pending = current_trb_status 'Under Review'. Decided = Approved, Approved with Conditions, Rejected.
- Match a feature with feature_name ILIKE '%term%'. Always return feature_name and review_id.
# CLARIFICATION RULES
- "Approved" when PHI use may be meant: ask "Do you mean approved by the TRB for any scope, or approved for PHI use (GA and fully approved)?"
- A term matching several features (e.g. "Genie" -> Genie One, AI/BI Genie): ask which one.
- If the tables cannot answer, say what is missing. Do not invent a query.
# SCOPE BOUNDARY
REFUSE questions about members, claims, providers, other PHI, Databricks pricing, or non-Databricks products. Generate no SQL and reply: "This cannot be answered here: this agent covers TRB review decisions on Databricks features only."
"""

    sample_questions = [
        "Which Databricks features are approved for PHI?",
        "Can we use Genie One with PHI data?",
        "Which reviews are still pending a TRB decision?",
        "What open conditions does Serverless compute have?",
        "Why was Kafka-compatible APIs rejected?",
        "What did the TRB decide at the June 16, 2026 meeting?",
        "What is the TRB approval rate by domain?",
        "Which exceptions were denied?",
        "Which HIPAA controls are mapped to Customer-managed keys?",
        "Which pending reviews came from Clinical Analytics?",
        "What documents exist for the SQL Server connector review?",
        "How long does the TRB take to reach a decision on average?",
    ]

    ex = [
        dict(q=["What is the TRB status and PHI eligibility of a feature?", "Can we use <feature> with PHI?"],
             sql=f"""SELECT review_id, feature_name, current_trb_status, current_dbx_phase, approved_scope, is_phi_eligible, blocking_reason
FROM {T}.v_feature_phi_eligibility
WHERE feature_name ILIKE concat('%', :feature_name, '%')""",
             params=[("feature_name", "STRING", "Feature name or part of it, e.g. 'Genie One', 'Unity Catalog'", "Genie One")]),
        dict(q=["Which features are approved for PHI?", "List PHI-eligible features"],
             sql=f"""SELECT review_id, feature_name, domain, approved_scope
FROM {T}.v_feature_phi_eligibility
WHERE is_phi_eligible
ORDER BY domain, feature_name""", params=[]),
        dict(q=["Why did the TRB make its decision on a feature?", "What risks did the TRB raise about <feature>?"],
             sql=f"""SELECT r.review_id, r.feature_name, r.current_trb_status, r.approval_meeting_id, r.decision_rationale,
       r.identified_risks, r.mitigations, r.open_questions, d.doc_id, d.summary
FROM {T}.reviews r
LEFT JOIN {T}.documents d
  ON array_contains(d.review_ids, r.review_id) AND d.doc_type = 'decision_record'
WHERE r.feature_name ILIKE concat('%', :feature_name, '%')""",
             params=[("feature_name", "STRING", "Feature name or part of it", "Kafka")]),
        dict(q=["What open conditions does a feature have?", "Which conditions are still open for <feature>?"],
             sql=f"""SELECT r.review_id, r.feature_name, c.condition_id, c.condition_title, c.verification_status, c.due_date
FROM {T}.approval_conditions c
JOIN {T}.reviews r ON c.review_id = r.review_id
WHERE c.verification_status <> 'Closed'
  AND r.feature_name ILIKE concat('%', :feature_name, '%')
ORDER BY c.condition_id""",
             params=[("feature_name", "STRING", "Feature name or part of it", "Serverless compute")]),
        dict(q=["What did the TRB decide at a meeting?", "What was decided on <date>?"],
             sql=f"""SELECT r.review_id, r.feature_name, r.current_trb_status, r.approved_scope, d.doc_id AS minutes_doc, d.summary AS minutes_summary
FROM {T}.reviews r
LEFT JOIN {T}.documents d ON d.meeting_id = r.approval_meeting_id AND d.doc_type = 'minutes'
WHERE r.decision_date = :meeting_date
ORDER BY r.review_id""",
             params=[("meeting_date", "DATE", "Meeting date, e.g. 2026-06-16", "2026-06-16")]),
        dict(q=["Approval rate by domain", "How many reviews per domain and how many were approved?"],
             sql=f"""SELECT domain, MEASURE(review_count) AS reviews, MEASURE(approved_count) AS approved,
       MEASURE(approval_rate_pct) AS approval_rate_pct
FROM {T}.mv_trb_reviews
GROUP BY ALL
ORDER BY reviews DESC""", params=[]),
        dict(q=["Which reviews are pending for a business unit?", "What is <business unit> waiting on from the TRB?"],
             sql=f"""SELECT review_id, feature_name, initial_submission_date, next_review_date, open_questions
FROM {T}.reviews
WHERE current_trb_status = 'Under Review' AND requesting_business_unit = :business_unit
ORDER BY initial_submission_date""",
             params=[("business_unit", "STRING", "Requesting business unit, e.g. 'Clinical Analytics', 'Data Governance', 'Enterprise Data Platform'", "Clinical Analytics")]),
        dict(q=["Exceptions by status", "Which exceptions were <status>?"],
             sql=f"""SELECT e.exception_id, r.feature_name, e.exception_type, e.exception_status, e.description,
       e.decision_meeting_id, e.exception_end_date
FROM {T}.exceptions e
JOIN {T}.reviews r ON e.review_id = r.review_id
WHERE e.exception_status = :exception_status""",
             params=[("exception_status", "STRING", "One of: Requested, Approved, Denied, Expired, Withdrawn", "Denied")]),
        dict(q=["Which controls are mapped to a feature?", "What HIPAA or NIST controls does <feature> satisfy?"],
             sql=f"""SELECT r.feature_name, m.control_framework, m.control_id, m.control_name, m.implementation_status
FROM {T}.control_mappings m
JOIN {T}.reviews r ON m.review_id = r.review_id
WHERE r.feature_name ILIKE concat('%', :feature_name, '%')
ORDER BY m.control_framework, m.control_id""",
             params=[("feature_name", "STRING", "Feature name or part of it", "Customer-managed keys")]),
        dict(q=["What documents exist for a feature?", "Show the TRB documents for <feature>"],
             sql=f"""SELECT d.doc_id, d.doc_type, d.doc_date, d.title, d.summary, d.volume_path
FROM {T}.documents d
JOIN {T}.reviews r ON array_contains(d.review_ids, r.review_id)
WHERE r.feature_name ILIKE concat('%', :feature_name, '%')
ORDER BY d.doc_date""",
             params=[("feature_name", "STRING", "Feature name or part of it", "SQL Server")]),
    ]
    examples = []
    for i, e in enumerate(ex, 1):
        item = {"id": hid("example", i), "question": e["q"], "sql": lines(e["sql"])}
        if e["params"]:
            item["parameters"] = [{"name": n, "type_hint": t, "description": [dsc], "default_value": {"values": [dv]}}
                                  for n, t, dsc, dv in e["params"]]
        examples.append(item)

    def snip(kind, n, **kw):
        d = {"id": hid(kind, n)}
        for k, v in kw.items():
            d[k] = v if k in ("alias", "display_name", "synonyms") else [v]
        return d

    sql_snippets = {
        "measures": sorted([
            snip("measure", 1, alias="open_condition_total", display_name="Open conditions",
                 sql="COUNT_IF(approval_conditions.verification_status <> 'Closed')",
                 comment="Approval conditions not yet verified closed (Open or In Progress).",
                 instruction="Use for 'how many conditions are open/outstanding'. Grain: one row per condition.",
                 synonyms=["number of open conditions", "how many conditions are open", "open condition count"]),
            snip("measure", 2, alias="phi_eligible_features", display_name="PHI-eligible features",
                 sql="COUNT_IF(v_feature_phi_eligibility.is_phi_eligible)",
                 comment="Features that are GA and fully TRB-approved.",
                 instruction="Use for 'how many features can be used with PHI'. Never count Approved with Conditions.",
                 synonyms=["number of PHI-eligible features", "how many features can use PHI", "PHI-eligible count"]),
            snip("measure", 3, alias="pending_reviews", display_name="Pending reviews",
                 sql="COUNT_IF(reviews.current_trb_status = 'Under Review')",
                 comment="Reviews awaiting a TRB decision.",
                 instruction="Use for 'how many reviews are pending / in review / waiting on the board'.",
                 synonyms=["number of pending reviews", "how many reviews are pending", "pending review count"]),
        ], key=lambda x: x["id"]),
        "filters": sorted([
            snip("filter", 1, display_name="Open conditions only", sql="approval_conditions.verification_status <> 'Closed'",
                 comment="Conditions not yet verified closed.", instruction="Apply when the user asks about open, outstanding, or unresolved conditions.",
                 synonyms=["open conditions", "outstanding", "not closed"]),
            snip("filter", 2, display_name="Pending TRB decision", sql="reviews.current_trb_status = 'Under Review'",
                 comment="Reviews awaiting a decision.", instruction="Apply for pending, in review, or awaiting-decision questions.",
                 synonyms=["pending", "under review", "awaiting decision"]),
            snip("filter", 3, display_name="PHI-eligible", sql="v_feature_phi_eligibility.is_phi_eligible = TRUE",
                 comment="GA and fully TRB-approved features.", instruction="Apply for 'approved for PHI', 'PHI-eligible', 'cleared for PHI'.",
                 synonyms=["approved for PHI", "PHI eligible", "cleared for PHI"]),
            snip("filter", 4, display_name="Denied exceptions", sql="exceptions.exception_status = 'Denied'",
                 comment="Exception requests the TRB denied.", instruction="Apply for denied, rejected, or refused exception or waiver questions.",
                 synonyms=["denied waivers", "rejected exceptions", "refused exceptions"]),
        ], key=lambda x: x["id"]),
        "expressions": sorted([
            snip("expr", 1, alias="decision_quarter", display_name="Decision quarter",
                 sql="DATE_TRUNC('QUARTER', reviews.decision_date)", comment="Quarter of the TRB decision.",
                 instruction="Use to group decisions by quarter.", synonyms=["quarter decided", "decision period"]),
            snip("expr", 2, alias="days_to_decision", display_name="Days to decision",
                 sql="DATEDIFF(reviews.decision_date, reviews.initial_submission_date)",
                 comment="Days from intake submission to TRB decision; NULL while undecided.",
                 instruction="Use for turnaround or cycle-time questions about a single review.",
                 synonyms=["turnaround", "cycle time", "time to decision"]),
        ], key=lambda x: x["id"]),
    }

    ss = {
        "version": 2,
        "config": {"sample_questions": [{"id": hid("sample", i), "question": [q]} for i, q in enumerate(sample_questions, 1)]},
        "data_sources": data_sources,
        "instructions": {
            "text_instructions": [{"id": hid("text", 1), "content": lines(text)}],
            "example_question_sqls": sorted(examples, key=lambda x: x["id"]),
            "sql_snippets": sql_snippets,
        },
    }
    ss["config"]["sample_questions"].sort(key=lambda x: x["id"])

    B = []  # benchmarks: static SQL, one binding each

    def bm(question, sql, negative=False, must=None):
        B.append({"question_text": question, "answer_text": sql.strip(), "negative": negative,
                  **({"must_reference": must} if must else {})})

    phi = lambda name: f"SELECT review_id, feature_name, is_phi_eligible, blocking_reason FROM {T}.v_feature_phi_eligibility WHERE feature_name ILIKE '%{name}%'"
    bm("Can we use Genie One with PHI data?", phi("Genie One"), must=["v_feature_phi_eligibility"])
    bm("Is Unity Catalog approved for PHI?", phi("Unity Catalog"), must=["v_feature_phi_eligibility"])
    bm("Is the SQL Server connector PHI-eligible?", phi("SQL Server"), must=["v_feature_phi_eligibility"])
    bm("Which features are approved for PHI?",
       f"SELECT review_id, feature_name FROM {T}.v_feature_phi_eligibility WHERE is_phi_eligible", must=["v_feature_phi_eligibility"])
    bm("How many features are PHI-eligible?",
       f"SELECT MEASURE(phi_eligible_count) AS phi_eligible FROM {T}.mv_trb_reviews", must=["mv_trb_reviews", "v_feature_phi_eligibility"])
    bm("Which reviews are pending a TRB decision?",
       f"SELECT review_id, feature_name FROM {T}.reviews WHERE current_trb_status = 'Under Review'", must=["reviews", "mv_trb_reviews"])
    bm("What open conditions does Serverless compute have?",
       f"SELECT c.condition_id, c.condition_title, c.verification_status FROM {T}.approval_conditions c JOIN {T}.reviews r ON c.review_id = r.review_id WHERE c.verification_status <> 'Closed' AND r.feature_name ILIKE '%Serverless compute%'", must=["approval_conditions"])
    bm("What open conditions does Genie One have?",
       f"SELECT c.condition_id, c.condition_title, c.verification_status FROM {T}.approval_conditions c JOIN {T}.reviews r ON c.review_id = r.review_id WHERE c.verification_status <> 'Closed' AND r.feature_name ILIKE '%Genie One%'", must=["approval_conditions"])
    bm("How many approval conditions are still open?",
       f"SELECT COUNT(*) AS open_conditions FROM {T}.approval_conditions WHERE verification_status <> 'Closed'", must=["approval_conditions", "mv_trb_reviews"])
    bm("Why was Kafka-compatible APIs rejected?",
       f"SELECT review_id, feature_name, current_trb_status, decision_rationale FROM {T}.reviews WHERE feature_name ILIKE '%Kafka%'", must=["reviews"])
    bm("What did the TRB decide at the 2026-06-16 meeting?",
       f"SELECT review_id, feature_name, current_trb_status FROM {T}.reviews WHERE decision_date = DATE '2026-06-16'", must=["reviews"])
    bm("What is the TRB approval rate by domain?",
       f"SELECT domain, MEASURE(approval_rate_pct) AS approval_rate_pct FROM {T}.mv_trb_reviews GROUP BY ALL", must=["mv_trb_reviews"])
    bm("How many reviews does each domain have?",
       f"SELECT domain, MEASURE(review_count) AS reviews FROM {T}.mv_trb_reviews GROUP BY ALL", must=["mv_trb_reviews"])
    bm("What is the average number of days from submission to TRB decision?",
       f"SELECT MEASURE(avg_days_to_decision) AS avg_days FROM {T}.mv_trb_reviews", must=["mv_trb_reviews", "reviews"])
    bm("Which exceptions were denied?",
       f"SELECT exception_id, review_id, exception_status FROM {T}.exceptions WHERE exception_status = 'Denied'", must=["exceptions"])
    bm("Which pending reviews came from Clinical Analytics?",
       f"SELECT review_id, feature_name FROM {T}.reviews WHERE current_trb_status = 'Under Review' AND requesting_business_unit = 'Clinical Analytics'", must=["reviews"])
    bm("Which HIPAA controls are mapped to Customer-managed keys?",
       f"SELECT m.control_id, m.control_name FROM {T}.control_mappings m JOIN {T}.reviews r ON m.review_id = r.review_id WHERE r.feature_name ILIKE '%Customer-managed keys%' AND m.control_framework = 'HIPAA-Security-Rule'", must=["control_mappings"])
    # Negative: clarification and refusal (expect no SQL)
    bm("Is Genie approved?", "-- expect clarification: Genie One vs AI/BI Genie, and TRB approval vs PHI approval", negative=True)
    bm("What is the claims denial rate for Medicare Advantage members?", "-- expect refusal: out of scope (claims/PHI)", negative=True)
    bm("How much does Databricks serverless compute cost per DBU?", "-- expect refusal: out of scope (pricing)", negative=True)
    return ss, B, text, sample_questions, ex, tables


def validate(profile, wh, ss, B, ex):
    bad = 0
    for i, e in enumerate(ex, 1):
        sql = e["sql"]
        for n, t, _, dv in e["params"]:
            sql = sql.replace(f":{n}", f"DATE '{dv}'" if t == "DATE" else "'" + dv.replace("'", "''") + "'")
        r = run(profile, wh, sql)
        rows = len((r.get("result") or {}).get("data_array") or [])
        ok = r["status"]["state"] == "SUCCEEDED" and rows > 0
        bad += not ok
        print(f"example {i:>2}: {r['status']['state']:<9} rows={rows:<3} {e['q'][0][:60]}"
              + ("" if ok else "  <-- " + r["status"].get("error", {}).get("message", "no rows")[:200]))
    for b in B:
        if b["negative"]:
            continue
        r = run(profile, wh, b["answer_text"])
        rows = len((r.get("result") or {}).get("data_array") or [])
        ok = r["status"]["state"] == "SUCCEEDED" and rows > 0
        bad += not ok
        print(f"bench    : {r['status']['state']:<9} rows={rows:<3} {b['question_text'][:60]}"
              + ("" if ok else "  <-- " + r["status"].get("error", {}).get("message", "no rows")[:200]))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--profile", required=True)
    ap.add_argument("--warehouse-id", required=True)
    ap.add_argument("--no-validate", action="store_true")
    a = ap.parse_args()
    ss, B, text, samples, ex, tables = spec(a.catalog)
    chars = len(text)
    print(f"text block: {chars} chars ({'OK' if chars <= 2000 else 'OVER 2000'}); "
          f"{len(ex)} examples, {len(B)} benchmarks ({sum(b['negative'] for b in B)} negative), {len(tables)} tables")
    if chars > 2000:
        sys.exit("text instruction block exceeds 2000 chars")
    ids = [x["id"] for x in ss["config"]["sample_questions"] + ss["instructions"]["example_question_sqls"]
           + ss["instructions"]["text_instructions"]]
    assert len(ids) == len(set(ids)) and all(re.fullmatch(r"[0-9a-f]{32}", i) for i in ids)
    if not a.no_validate:
        bad = validate(a.profile, a.warehouse_id, ss, B, ex)
        if bad:
            sys.exit(f"{bad} SQL checks failed")
    (HERE / "genie_agent.json").write_text(json.dumps(ss, indent=1, ensure_ascii=False))
    # Same definition for the Asset Bundle genie_spaces resource (file_path must be *.geniespace.json).
    (HERE / "review_board.geniespace.json").write_text(json.dumps(ss, indent=1, ensure_ascii=False))
    (HERE / "benchmarks.json").write_text(json.dumps(B, indent=1, ensure_ascii=False))
    # Answerable set for the Benchmarks tab (negatives have no SQL; run_benchmarks.py scores them).
    (HERE / "benchmarks_sync.json").write_text(json.dumps(
        [{"question_text": b["question_text"], "answer_text": b["answer_text"]} for b in B if not b["negative"]], indent=1))
    print("wrote genie_agent.json, review_board.geniespace.json, benchmarks.json")


if __name__ == "__main__":
    main()
