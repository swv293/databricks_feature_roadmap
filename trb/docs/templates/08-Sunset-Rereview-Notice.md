# Re-Review / Sunset Notice – Technology Review Board

**Notice ID:** SR-YYYY-NNN  
**Original Review ID:** TRB-YYYY-NNN  
**Feature Name:** [Feature Name]  
**Date Issued:** [YYYY-MM-DD]  
**Action Required By:** [YYYY-MM-DD]  

---

## Purpose

This notice informs [Requestor / Business Unit] of a **scheduled re-review** or **sunset date** for a previously-approved Databricks feature. This ensures continued compliance monitoring and allows the TRB to assess whether conditions remain appropriate or whether the feature should be retired.

---

## Current Status

| Field | Value |
|-------|-------|
| **Feature** | [Feature Name] |
| **Databricks Phase** | [GA / Public Preview / etc.] |
| **Current TRB Status** | [Approved / Approved with Conditions / etc.] |
| **Last Approved** | [YYYY-MM-DD] |
| **Approval Duration** | [e.g., "2 years"] |
| **Current Users/Teams** | [Estimated count] |

---

## Notice Type

### Type A: Scheduled Re-Review (Continuation)

**What:** A periodic compliance check to ensure conditions remain met and risk profile unchanged.

**When:** [e.g., "2 years after initial approval; or if organizational policy changes; or if Databricks release phase changes"]

**Action Required:** Requestor must submit a brief re-certification form (below) by [YYYY-MM-DD] confirming:
- Current usage level and user count
- Any incidents or anomalies
- Status of all conditions (COND-XXX-1, etc.)
- Any changes in data scope, geography, or compliance requirements

**TRB Review:** If re-certification is timely and shows no changes, TRB will issue a renewal approval letter (valid another 2 years). If issues identified, TRB may require a full re-review (intake + risk assessment + board meeting).

**Result:** [ ] Renewed approval | [ ] Requires full re-review | [ ] Conditional renewal with updated conditions

---

### Type B: Sunset Notice (Feature Retirement)

**What:** The feature is being retired and access must be suspended by [YYYY-MM-DD].

**Why:** [Reason: e.g., "Databricks end-of-life for this product", "Acme Health Plan compliance policy changed", "Feature found to have residual risk that cannot be mitigated", "Replaced by superior alternative"]

**Action Required:** Requestor must:
1. **By [YYYY-MM-DD]:** Migrate workloads to approved alternative (list below).
2. **By [YYYY-MM-DD]:** Revoke all user access; confirm deactivation to TRB.
3. **By [YYYY-MM-DD]:** Archive all historical data and audit logs per [compliance policy].

**Alternative Features:** [List approved features that provide similar functionality]

**Enforcement:** After [YYYY-MM-DD], TRB will audit to confirm feature is disabled. Non-compliance will result in security incident escalation and account suspension.

---

## Re-Certification Form (Type A Only)

**Complete this section if Type A (Scheduled Re-Review):**

| Field | Response |
|-------|----------|
| **Feature Still in Use?** | [ ] Yes | [ ] No (please describe replacement) |
| **Active Teams/Users** | [Count] |
| **Usage (Monthly Query Count)** | [Estimate] |
| **Any Incidents?** | [ ] No | [ ] Yes—describe: [link to incident report] |
| **All Conditions Met?** | [ ] Yes | [ ] Partially [describe] | [ ] No [describe] |
| **Data Scope Changed?** | [ ] No | [ ] Yes—describe: [new scope] |
| **Compliance/Policy Changes?** | [ ] No | [ ] Yes—describe: [internal policy changes affecting feature] |
| **Any New Risks Identified?** | [ ] No | [ ] Yes—describe: [risk, mitigation] |
| **Certification** | [Requestor signature required] |

**Re-Certification Submitted By:**  
[Name / Title] _________________ Date: [YYYY-MM-DD]

---

## Sunset Timeline (Type B Only)

| Date | Milestone | Owner | Status |
|------|-----------|-------|--------|
| [Today] | Sunset notice issued | TRB | ✓ |
| [+30 days] | Requests for extension must be submitted (exception process) | Requestor | |
| [+60 days] | All workloads migrated to alternative; user access revoked | Requestor | |
| [+90 days] | Data archival completed; TRB verifies feature is disabled | Requestor + TRB | |
| [+120 days] | Final audit & closure; archives sealed | TRB | |

**Extension Request:** If you cannot meet [+60 day] deadline, submit an exception request (see Exception Request template) by [date]. Extensions may be granted for up to 90 additional days if strong business justification and mitigation plan provided.

---

## Compliance Obligations (Both Types)

### Ongoing Monitoring
- **Quarterly Audits Continue:** TRB will audit usage logs until feature renewed or retired.
- **Incident Escalation:** Any security incident, data breach, or unauthorized access must be reported to [CISO / Compliance Officer] within [1 hour].
- **No Scope Expansion:** You may not extend the feature to new teams, geographies, or data types without TRB re-review.

### Documentation Retention
- All audit logs, incident reports, and condition verification records must be retained for [7 years] per compliance policy.
- Historical TRB decisions are archived at [location] and available to auditors.

---

## Questions or Concerns?

- **Re-certification Questions (Type A):** Contact [TRB Lead] at [email]
- **Sunset Timeline Questions (Type B):** Contact [CISO] at [email]
- **Extension / Waiver Requests:** Submit exception request per [Exception Request template]

---

## Appendix: Condition Status Tracking

**Current Conditions (if Type A – Renewal):**

| Condition ID | Original Requirement | Verified Status | Last Checked | Notes |
|--------------|-------------------|-----------------|--------------|-------|
| COND-XXX-1 | [Requirement] | [ ] Met | [Date] | [e.g., "Logging enabled; no gaps"] |
| COND-XXX-2 | [Requirement] | [ ] Met | [Date] | [e.g., "Masking working; tested monthly"] |

---

**Notice Issued By:**  
[CISO / Compliance Officer Name]  
Title: [Title]  

Signature: _________________________ Date: [YYYY-MM-DD]

---

**cc:**  
- [Requestor / Business Unit Lead]
- [Enterprise Architect]
- [Chief Privacy Officer]
- [Executive Sponsor (if critical feature)]

---

**Classification:** Internal – Synthetic Sample

**Related Documents:**
- Original Decision Record: DR-YYYY-NNN
- Original Risk Assessment: [Link]
- Audit Trail: [Link to audit logs repository]
