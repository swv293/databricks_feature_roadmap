"""Generate TRB rows and documents from one source, so tables and documents cannot disagree.

    python3 trb/genie/generate_extended.py --catalog <catalog>

Inputs:  trb/data/reviews_extended.json (TRB-2026-010..035, validated)
         CANONICAL_ENRICH below (fields the 9 canonical rows were loaded without)
         trb/docs/samples/*.md front-matter (document index)
Outputs: trb/docs/samples/{INT,DR,CAL,MIN}-*.md for the extended reviews
         trb/table/extended_data.sql (inserts for 010..035, canonical enrichment,
         and a full rebuild of the documents index from the markdown front-matter)
"""
import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "trb" / "docs" / "samples"
FEATURES = {f"{f['name']}@{f['domain']}": f for f in json.loads((ROOT / "data" / "features.json").read_text())}
BOARD = "CISO,Chief Privacy Officer,Enterprise Architect,Platform Engineering Lead,Data Governance Lead,Compliance Officer"
CLASSIFICATION = "Internal – Synthetic Sample"

# Fields the canonical rows (TRB-2026-001..009) were loaded without. Facts follow trb/CANONICAL.md.
CANONICAL_ENRICH = {
    "TRB-2026-001": dict(bu="Information Security", uc=["PHI minimization", "Member-level access control"],
        scope="PHI", trigger="Annual re-review", next="2027-07-14", oq=[],
        why="Row filters and column masks are the primary UC control for HIPAA minimum-necessary access. Masks and filters are evaluated at query time for the querying user, so they also apply in downstream tools. Approved for PHI with no conditions."),
    "TRB-2026-002": dict(bu="Data Governance", uc=["Tag-driven PHI policies", "Scaling row and column security"],
        scope="None", trigger="Governed-tag design and IdP attribute sync approved", next="2026-10-20",
        oq=["Which system is the source of truth for governed tags?", "How are IdP attributes synced and kept current?"],
        why="Deferred at 07-28 and still open at 08-25: the TRB will not approve tag-based policies until the governed-tag source of truth and the identity-provider attribute sync are designed and tested."),
    "TRB-2026-003": dict(bu="Claims Operations", uc=["Claims ingestion", "Provider data sync"],
        scope="Non-PHI only", trigger="Databricks phase -> GA", next="2026-12-01", oq=[],
        why="Approved for non-PHI sources only while the connector is in Public Preview, which Databricks marks as subject to compliance restrictions. Conditions COND-003-1 and COND-003-2 are closed. Re-review when the connector reaches GA."),
    "TRB-2026-004": dict(bu="Clinical Analytics", uc=["Real-time eligibility events"],
        scope="None", trigger="Databricks phase -> GA", next=None, oq=[],
        why="Rejected: Beta features are out of compliance scope and carry no SLA. Schema-evolution gaps and offset tracking were also unresolved. Resubmit when the capability reaches GA."),
    "TRB-2026-005": dict(bu="Member Experience", uc=["Self-service claims analytics", "Operational KPI Q&A"],
        scope="PHI (after all conditions close)", trigger="All conditions closed, then move to Approved", next="2026-10-15", oq=[],
        why="Approved with conditions: Genie One runs queries under each user's UC permissions, so row filters and masks apply. The TRB required audit logging, identity testing, response sampling with small-cell suppression, and user training first. COND-005-3 is in progress and COND-005-4 is open, so it is not yet PHI-eligible."),
    "TRB-2026-006": dict(bu="Clinical Analytics", uc=["Benefits and policy document Q&A"],
        scope="Sandbox only (synthetic data)", trigger="Databricks phase -> GA", next="2026-11-11",
        oq=["How are source documents permissioned and retired?", "What retrieval and answer logs are retained?"],
        why="Under review while the feature is in Beta. A sandbox pilot on synthetic or non-PHI documents runs under EXC-2026-002 until 2026-11-11. No production or PHI use."),
    "TRB-2026-007": dict(bu="Provider Network", uc=["Partner data exchange", "Provider directory sharing"],
        scope="Non-PHI only", trigger="Any PHI share request (requires BAA under COND-007-1)", next="2026-10-25", oq=[],
        why="Approved with conditions for non-PHI partner exchange. A PHI share needs a signed BAA with the recipient first (COND-007-1), plus token lifetime and IP limits (COND-007-2) and share-access audit (COND-007-3). All three conditions are open."),
    "TRB-2026-008": dict(bu="Enterprise Data Platform", uc=["Internal data apps"],
        scope="None", trigger="App-auth and egress test results", next="2026-10-20",
        oq=["Should apps act as the user or as a service principal for PHI data?", "How is outbound network egress from apps restricted?"],
        why="Under review: the TRB asked for testing of user versus service-principal authorization and of app egress controls before any PHI-bearing app."),
    "TRB-2026-009": dict(bu="Clinical Analytics", uc=["Agent tool access to internal systems"],
        scope="None", trigger="Intake triage", next="2026-10-20", oq=["Triage pending: scope of servers and data reached"],
        why="Not yet reviewed. Intake submitted 2026-09-22 and scheduled for triage."),
}
CANONICAL_CONTROLS = {
    "TRB-2026-001": [("HIPAA-Security-Rule", "45 CFR 164.312(a)(1)", "Access control", "Satisfied"),
                     ("NIST-800-53-R5", "AC-3", "Access enforcement", "Satisfied")],
    "TRB-2026-003": [("HIPAA-Security-Rule", "45 CFR 164.312(e)(1)", "Transmission security", "Satisfied"),
                     ("NIST-800-53-R5", "SC-8", "Transmission confidentiality and integrity", "Satisfied")],
    "TRB-2026-005": [("HIPAA-Security-Rule", "45 CFR 164.312(b)", "Audit controls", "Partially Satisfied"),
                     ("NIST-800-53-R5", "AU-2", "Event logging", "Satisfied")],
    "TRB-2026-007": [("HIPAA-Privacy-Rule", "45 CFR 164.502(e)", "Business associate disclosures", "Not Addressed"),
                     ("NIST-800-53-R5", "IA-5", "Authenticator management", "Partially Satisfied")],
}
CANONICAL_DUE = {"COND-003-1": "2026-08-14", "COND-003-2": "2026-09-14", "COND-005-1": "2026-09-15",
                 "COND-005-2": "2026-09-15", "COND-005-3": None, "COND-005-4": "2026-09-15",
                 "COND-007-1": None, "COND-007-2": "2026-10-25", "COND-007-3": "2026-10-25"}
# Summaries for the 20 hand-written documents (generated documents carry their own).
CANONICAL_SUMMARIES = {
    "CHARTER-2026": "TRB charter: membership, authority, quorum (4 members including CISO or CPO), biweekly cadence, review lifecycle, and the PHI rule (GA and Approved only). Effective 2026-04-01, revised 2026-07-01.",
    "MIN-TRBM-2026-07-14": "Approved Row filters & column masks (PHI). Approved the SQL Server connector for non-PHI only while in Public Preview. Rejected Kafka-compatible APIs (Beta, out of compliance scope).",
    "MIN-TRBM-2026-07-28": "Approved Genie One with four conditions (COND-005-1..4). Introduced ABAC and deferred it pending the governed-tag and IdP attribute design.",
    "MIN-TRBM-2026-08-11": "Introduced Knowledge Assistant (Beta) and approved a sandbox pilot under EXC-2026-002. Introduced Databricks Apps; both remain Under Review.",
    "MIN-TRBM-2026-08-25": "Approved Databricks-to-Open sharing with conditions (COND-007-1..3; BAA required for PHI). ABAC and Databricks Apps follow-ups: both still Under Review.",
    "MIN-TRBM-2026-09-08": "Denied EXC-2026-001 (PHI through the Public Preview SQL Server connector). Reviewed Genie One condition verification status.",
    "MIN-TRBM-2026-09-22": "Received the MCP servers intake (TRB-2026-009, Not Reviewed). Status check on ABAC, Knowledge Assistant, and Databricks Apps.",
    "INT-TRB-2026-006": "Intake request for Knowledge Assistant (Beta) from Clinical Analytics: document Q&A over benefits and policy content, limited to a non-PHI sandbox pilot.",
    "INT-TRB-2026-009": "Intake request for MCP servers: agent access to internal systems and external APIs. Submitted 2026-09-22; awaiting triage.",
    "RA-TRB-2026-005": "Security and privacy risk assessment for Genie One: data access under user UC permissions, row filters and masks, audit through system tables, small-cell suppression. Open items pending account-team confirmation.",
    "RA-TRB-2026-007": "Risk assessment for Databricks-to-Open sharing: bearer-token and OIDC recipient auth, token lifetime, recipient IP access lists, BAA before PHI, and share-access audit.",
    "DR-2026-001": "Decision record: Row filters & column masks approved for PHI with no conditions.",
    "DR-2026-003": "Decision record: SQL Server connector approved for non-PHI only while in Public Preview; conditions COND-003-1..2; re-review at GA.",
    "DR-2026-004": "Decision record: Kafka-compatible APIs rejected. Beta is out of compliance scope; resubmit at GA.",
    "DR-2026-005": "Decision record: Genie One approved with conditions COND-005-1..4; not PHI-eligible until all close.",
    "DR-2026-007": "Decision record: Databricks-to-Open sharing approved with conditions COND-007-1..3; non-PHI only until a recipient BAA is signed.",
    "CAL-TRB-2026-005": "Conditional approval letter for Genie One listing COND-005-1..4 with due dates and verification methods.",
    "CAL-TRB-2026-007": "Conditional approval letter for Databricks-to-Open sharing listing COND-007-1..3.",
    "EXC-2026-001": "Exception request from Finance to ingest member name and ID (PHI) through the Public Preview SQL Server connector. DENIED at TRBM-2026-09-08; alternatives offered.",
    "EXC-2026-002": "Exception approving a sandbox pilot of the Beta Knowledge Assistant on synthetic or non-PHI documents only; expires 2026-11-11.",
}


def q(v):
    """SQL literal."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, dt.date):
        return f"DATE '{v.isoformat()}'"
    if isinstance(v, list):
        return "array(" + ", ".join(q(x) for x in v) + ")" if v else "CAST(array() AS ARRAY<STRING>)"
    return "'" + str(v).replace("\\", "\\\\").replace("'", "''") + "'"


def d(s):
    return dt.date.fromisoformat(s) if s and s != "ongoing" else None


def mdate(meeting_id):
    return dt.date.fromisoformat(meeting_id[5:]) if meeting_id else None


def front_matter(**kw):
    lines = ["---"]
    for k, v in kw.items():
        if v is None:
            lines.append(f"{k}: null")
        elif isinstance(v, list):
            lines.append(f"{k}: " + json.dumps(v, ensure_ascii=False))
        elif k == "date":
            lines.append(f"{k}: {v}")
        else:
            lines.append(f'{k}: "{v}"')
    return "\n".join(lines + ["---", ""])


def bullets(xs):
    return "\n".join(f"- {x}" for x in xs) if xs else "- None"


def write_docs(R):
    out = []  # (doc_id, summary) for generated documents
    for r in R:
        n = r["review_id"][-3:]
        f = FEATURES[r["feature_key"]]
        intro = r["introduced_meeting_id"]
        # Intake request
        doc_id = f"INT-TRB-2026-{n}"
        body = f"""# Review Intake Request: {f['name']}

**Review ID:** {r['review_id']} · **Feature:** `{r['feature_key']}` · **Databricks phase at submission:** {r['dbx_phase_at_decision']}
**Requesting business unit:** {r['requesting_business_unit']} · **Submitted:** {r['initial_submission_date']} · **Scheduled for:** {intro}
**Primary reviewer:** {r['primary_reviewer_role']}

## Business need
{r['review_context']}

## Intended use cases
{bullets(r['use_cases'])}

## Risks identified by the requester
{bullets(r['identified_risks'])}

## Proposed mitigations
{bullets(r['mitigations'])}

## Reference
- Databricks documentation: {f.get('docLink') or 'n/a'}
- Known limitations (tracker): {f.get('limitations') or 'none recorded'}
"""
        summ = f"Intake request from {r['requesting_business_unit']} for {f['name']} ({r['dbx_phase_at_decision']}): {r['review_context'].split('. ')[0].rstrip('.')}."
        (SAMPLES / f"{doc_id}.md").write_text(front_matter(
            doc_type="Review Intake Request", doc_id=doc_id, review_ids=[r["review_id"]], feature_keys=[r["feature_key"]],
            meeting_id=intro, date=r["initial_submission_date"], status="Submitted", classification=CLASSIFICATION) + body)
        out.append((doc_id, summ))

        if r["decision_meeting_id"] is None:
            continue
        # Decision record
        doc_id = f"DR-2026-{n}"
        conds = r["conditions"]
        cond_md = "\n".join(f"| COND-{n}-{i} | {c['title']} | {c['due_date']} | {c['verification_status']} |"
                            for i, c in enumerate(conds, 1))
        body = f"""# Decision Record {doc_id}: {f['name']}

**Status:** {r['status']} · **Approved scope:** {r['approved_scope']} · **Decided at:** {r['decision_meeting_id']}
**Review:** {r['review_id']} · **Feature:** `{r['feature_key']}` · **Databricks phase at decision:** {r['dbx_phase_at_decision']}

## Context
{r['review_context']}

## Decision
{r['decision_rationale']}

## Risks considered
{bullets(r['identified_risks'])}

## Mitigations relied on
{bullets(r['mitigations'])}

## Control mappings
{bullets([f"{c['framework']} {c['control_id']} ({c['control_name']}): {c['status']}" for c in r['controls']])}
"""
        if conds:
            body += f"\n## Conditions\n| ID | Condition | Due | Status |\n|---|---|---|---|\n{cond_md}\n"
        body += f"\n## Re-review\nTrigger: {r['rereview_trigger']} · Next review: {r['next_review_date']}\n"
        summ = f"Decision record: {f['name']} {r['status'].lower()} (scope: {r['approved_scope']}) at {r['decision_meeting_id']}. {r['decision_rationale'].split('. ')[0].rstrip('.')}."
        (SAMPLES / f"{doc_id}.md").write_text(front_matter(
            doc_type="Decision Record", doc_id=doc_id, review_ids=[r["review_id"]], feature_keys=[r["feature_key"]],
            meeting_id=r["decision_meeting_id"], date=r["decision_meeting_id"][5:], status="Accepted",
            classification=CLASSIFICATION) + body)
        out.append((doc_id, summ))

        if conds:
            doc_id = f"CAL-TRB-2026-{n}"
            rows = "\n".join(f"| COND-{n}-{i} | {c['title']} | {c['text']} | {c['verification_method']} | {c['due_date']} |"
                             for i, c in enumerate(conds, 1))
            body = f"""# Conditional Approval Letter: {f['name']}

To: {r['requesting_business_unit']} · From: Tech Review Board · Re: {r['review_id']} · Date: {r['decision_meeting_id'][5:]}

The TRB approved **{f['name']}** with conditions at {r['decision_meeting_id']}. The approval does **not** permit PHI use
until every condition below is verified closed and the TRB moves the review to Approved.

| ID | Condition | Requirement | Verification | Due |
|---|---|---|---|---|
{rows}

Rationale: {r['decision_rationale']}
"""
            summ = f"Conditional approval letter for {f['name']} listing {len(conds)} conditions (COND-{n}-1..{len(conds)}); PHI use waits until all close."
            (SAMPLES / f"{doc_id}.md").write_text(front_matter(
                doc_type="Conditional Approval Letter", doc_id=doc_id, review_ids=[r["review_id"]],
                feature_keys=[r["feature_key"]], meeting_id=r["decision_meeting_id"], date=r["decision_meeting_id"][5:],
                status="Active", classification=CLASSIFICATION) + body)
            out.append((doc_id, summ))

    # Minutes for the new meetings
    meetings = sorted({r["introduced_meeting_id"] for r in R} | {r["decision_meeting_id"] for r in R if r["decision_meeting_id"]})
    notes = {}
    for m in meetings:
        decided = [r for r in R if r["decision_meeting_id"] == m]
        introduced = [r for r in R if r["introduced_meeting_id"] == m and r["decision_meeting_id"] != m]
        sec = []
        for r in decided:
            sec.append(f"### {r['review_id']}: {FEATURES[r['feature_key']]['name']} → **{r['status']}** (scope: {r['approved_scope']})\n"
                       f"Presented by {r['requesting_business_unit']}; lead reviewer {r['primary_reviewer_role']}.\n\n{r['decision_rationale']}\n")
        for r in introduced:
            sec.append(f"### {r['review_id']}: {FEATURES[r['feature_key']]['name']} → introduced, **Under Review**\n"
                       f"{r['review_context']}\n\nOpen questions:\n{bullets(r['open_questions'])}\n")
        extra = ""
        if m == "TRBM-2026-10-06":
            extra = ("\n## Status checks\n- TRB-2026-005 Genie One: COND-005-3 in progress, COND-005-4 open; remains Approved with Conditions.\n"
                     "- TRB-2026-034 Serverless compute: conditions COND-034-1..3 not yet closed.\n"
                     "- TRB-2026-009 MCP servers: triage scheduled for the next meeting.\n")
        title = "Platform baseline review" if mdate(m) < dt.date(2026, 7, 1) else "Regular session"
        doc_id = f"MIN-{m}"
        body = f"""# TRB Meeting Minutes: {m[5:]} ({title})

**Attendees:** {BOARD.replace(',', ', ')} · **Quorum:** met · **Format:** hybrid

## Decisions and introductions
{chr(10).join(sec)}{extra}"""
        ids = sorted({r["review_id"] for r in decided + introduced} | ({"TRB-2026-005", "TRB-2026-009", "TRB-2026-034"} if extra else set()))
        parts = []
        if decided:
            parts.append("Decided: " + "; ".join(f"{FEATURES[r['feature_key']]['name']} ({r['status']})" for r in decided))
        if introduced:
            parts.append("Introduced (Under Review): " + ", ".join(FEATURES[r['feature_key']]['name'] for r in introduced))
        summ = ". ".join(parts) + "."
        notes[m] = summ
        (SAMPLES / f"{doc_id}.md").write_text(front_matter(
            doc_type="Meeting Minutes", doc_id=doc_id, review_ids=ids,
            feature_keys=[next((x["feature_key"] for x in R if x["review_id"] == i), None) or i for i in ids],
            meeting_id=m, date=m[5:], status="Final", classification=CLASSIFICATION) + body)
        out.append((doc_id, summ))
    return out, meetings, notes


def parse_front_matter(p):
    t = p.read_text()
    fm = t.split("---", 2)[1]
    meta = {}
    for line in fm.splitlines():
        m = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if not m:
            continue
        k, v = m.groups()
        v = v.strip()
        if v.startswith("["):
            v = json.loads(v)
        elif v == "null":
            v = None
        else:
            v = v.strip('"')
        meta[k] = v
    title = next((l[2:].strip() for l in t.split("---", 2)[2].splitlines() if l.startswith("# ")), p.stem)
    return meta, title


DOC_TYPE = {"TRB Charter": "charter", "Meeting Minutes": "minutes", "Review Intake Request": "intake",
            "Security & Privacy Risk Assessment": "risk_assessment", "Decision Record": "decision_record",
            "Conditional Approval Letter": "approval_letter", "Exception Request": "exception"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    a = ap.parse_args()
    C = f"{a.catalog}.trb"
    R = json.loads((ROOT / "trb" / "data" / "reviews_extended.json").read_text())
    gen_summaries, meetings, notes = write_docs(R)
    summaries = {**CANONICAL_SUMMARIES, **dict(gen_summaries)}
    sql = ["-- GENERATED by trb/genie/generate_extended.py. Do not edit by hand.",
           "-- Run after ddl.sql, sample_data.sql, and ddl_v2.sql. Idempotent: deletes then reinserts its own rows."]

    ext_ids = [r["review_id"] for r in R]
    idlist = ", ".join(q(i) for i in ext_ids)
    for t in ("review_history", "control_mappings", "approval_conditions"):
        sql.append(f"DELETE FROM {C}.{t} WHERE review_id IN ({idlist})")
    sql.append(f"DELETE FROM {C}.control_mappings WHERE review_id IN ({', '.join(q(i) for i in CANONICAL_CONTROLS)})")
    sql.append(f"DELETE FROM {C}.reviews WHERE review_id IN ({idlist})")
    sql.append(f"DELETE FROM {C}.meetings WHERE meeting_id IN ({', '.join(q(m) for m in meetings)})")

    # Meetings
    rows = [f"({q(m)}, {q(mdate(m))}, 'hybrid', 'Boardroom A / video', {q(BOARD)}, TRUE, {q(notes[m])}, "
            f"{q(f'/Volumes/{a.catalog}/trb/corpus/MIN-{m}.md')}, current_timestamp())" for m in meetings]
    sql.append(f"INSERT INTO {C}.meetings (meeting_id, meeting_date, meeting_type, meeting_location, attendees, "
               f"quorum_met, meeting_notes, minutes_url, created_at) VALUES\n  " + ",\n  ".join(rows))

    # Reviews
    cols = ("review_id, feature_key, feature_name, domain, dbx_phase_at_decision, current_trb_status, approved_scope, "
            "initial_submission_date, latest_review_date, decision_date, primary_reviewer_role, approval_meeting_id, "
            "rereview_trigger, next_review_date, requesting_business_unit, use_cases, review_context, identified_risks, "
            "mitigations, open_issue_count, closed_issue_count, created_at, updated_at, decision_rationale, open_questions")
    rows = []
    for r in R:
        f = FEATURES[r["feature_key"]]
        dm = r["decision_meeting_id"]
        latest = mdate(dm) if dm else mdate(r["introduced_meeting_id"])
        open_c = sum(c["verification_status"] != "Closed" for c in r["conditions"])
        closed_c = len(r["conditions"]) - open_c
        rows.append("(" + ", ".join([
            q(r["review_id"]), q(r["feature_key"]), q(f["name"]), q(f["domain"]), q(r["dbx_phase_at_decision"]),
            q(r["status"]), q(r["approved_scope"]), q(d(r["initial_submission_date"])), q(latest), q(mdate(dm)),
            q(r["primary_reviewer_role"]), q(dm), q(r["rereview_trigger"]), q(d(r["next_review_date"])),
            q(r["requesting_business_unit"]), q(r["use_cases"]), q(r["review_context"]),
            q("; ".join(r["identified_risks"])), q("; ".join(r["mitigations"])),
            q(len(r["open_questions"]) + open_c), q(closed_c), "current_timestamp()", "current_timestamp()",
            q(r["decision_rationale"]), q("; ".join(r["open_questions"]))]) + ")")
    sql.append(f"INSERT INTO {C}.reviews ({cols}) VALUES\n  " + ",\n  ".join(rows))

    # Canonical enrichment
    for rid, e in CANONICAL_ENRICH.items():
        sql.append(f"UPDATE {C}.reviews SET requesting_business_unit = {q(e['bu'])}, use_cases = {q(e['uc'])}, "
                   f"approved_scope = {q(e['scope'])}, rereview_trigger = {q(e['trigger'])}, "
                   f"next_review_date = {q(d(e['next']))}, decision_rationale = {q(e['why'])}, "
                   f"open_questions = {q('; '.join(e['oq']))}, updated_at = current_timestamp() WHERE review_id = {q(rid)}")
    for cid, due in CANONICAL_DUE.items():
        sql.append(f"UPDATE {C}.approval_conditions SET due_date = {q(d(due))} WHERE condition_id = {q(cid)}")

    # Conditions (034 only)
    rows = []
    for r in R:
        n = r["review_id"][-3:]
        for i, c in enumerate(r["conditions"], 1):
            closed = c["verification_status"] == "Closed"
            rows.append("(" + ", ".join([
                q(f"COND-{n}-{i}"), q(r["review_id"]), str(i), q(c["title"]), q(c["text"]), q(c["rationale"]), "'GA'",
                q(c["verification_method"]), q(c["verification_status"]), "NULL", q(r["primary_reviewer_role"] if closed else None),
                "NULL", "current_timestamp()", "current_timestamp()", q(d(c["due_date"]))]) + ")")
    if rows:
        sql.append(f"INSERT INTO {C}.approval_conditions (condition_id, review_id, condition_number, condition_title, "
                   "condition_text, condition_rationale, applicable_at_phase, verification_method, verification_status, "
                   "verification_date, verified_by_role, verification_notes, created_at, updated_at, due_date) VALUES\n  "
                   + ",\n  ".join(rows))

    # Control mappings
    rows = []
    allc = {r["review_id"]: [(c["framework"], c["control_id"], c["control_name"], c["status"]) for c in r["controls"]] for r in R}
    for rid, cs in {**CANONICAL_CONTROLS, **allc}.items():
        for fw, cid, name, st in cs:
            mid = hashlib.md5(f"{rid}|{fw}|{cid}".encode()).hexdigest()[:16]
            rows.append(f"({q(mid)}, {q(rid)}, {q(fw)}, {q(cid)}, {q(name)}, {q(st)}, current_timestamp(), current_timestamp())")
    sql.append(f"INSERT INTO {C}.control_mappings (mapping_id, review_id, control_framework, control_id, control_name, "
               "implementation_status, created_at, updated_at) VALUES\n  " + ",\n  ".join(rows))

    # Review history
    rows = []
    for r in R:
        n = r["review_id"][-3:]
        ev = [(d(r["initial_submission_date"]), "submitted", None, "Not Reviewed", r["requesting_business_unit"] + " lead",
               f"Intake submitted by {r['requesting_business_unit']}"),
              (mdate(r["introduced_meeting_id"]), "meeting_presented", "Not Reviewed", "Under Review", r["primary_reviewer_role"],
               f"Presented at {r['introduced_meeting_id']}")]
        if r["decision_meeting_id"]:
            ev.append((mdate(r["decision_meeting_id"]), "status_change", "Under Review", r["status"], "CISO",
                       f"Status moved to {r['status']} at {r['decision_meeting_id']}"))
        for k, (date_, et, old, new, who, s) in enumerate(ev, 1):
            rows.append(f"({q(f'evt-{n}-{k:03d}')}, {q(r['review_id'])}, {q(date_)}, {q(et)}, {q(old)}, {q(new)}, {q(who)}, {q(s)}, NULL, current_timestamp())")
    sql.append(f"INSERT INTO {C}.review_history (history_id, review_id, event_date, event_type, old_status, new_status, "
               "changed_by_role, summary, details, created_at) VALUES\n  " + ",\n  ".join(rows))

    # Documents index: rebuilt from the markdown front-matter of every sample document.
    sql.append(f"DELETE FROM {C}.documents")
    rows, missing = [], []
    for p in sorted(SAMPLES.glob("*.md")):
        meta, title = parse_front_matter(p)
        did = meta["doc_id"]
        if did not in summaries:
            missing.append(did)
        rows.append("(" + ", ".join([
            q(did), q(DOC_TYPE.get(meta.get("doc_type"), "other")), q(title), q(d(str(meta.get("date"))[:10])),
            q(meta.get("meeting_id") or None), q(f"/Volumes/{a.catalog}/trb/corpus/{p.name}"),
            q(meta.get("review_ids") or []), "current_timestamp()", q(summaries.get(did)),
            q(f"/Volumes/{a.catalog}/trb/corpus_pdf/{p.stem}.pdf")]) + ")")
    sql.append(f"INSERT INTO {C}.documents (doc_id, doc_type, title, doc_date, meeting_id, volume_path, review_ids, "
               "created_at, summary, pdf_path) VALUES\n  " + ",\n  ".join(rows))

    out = ROOT / "trb" / "table" / "extended_data.sql"
    out.write_text(";\n\n".join(sql) + ";\n")
    print(f"wrote {out.name}: {len(R)} reviews, {len(meetings)} meetings, {len(rows)} documents indexed")
    print(f"generated {len(gen_summaries)} documents; documents without a summary: {missing or 'none'}")


if __name__ == "__main__":
    main()
