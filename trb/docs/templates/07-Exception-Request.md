# Exception Request (Waiver) – TRB Policy Override

**Exception ID:** EXC-YYYY-NNN  
**Requestor:** [Business Unit Lead / Department]  
**Date Submitted:** [YYYY-MM-DD]  
**Urgency:** [ ] Standard (30 days) | [ ] Expedited (14 days) | [ ] Emergency (72 hours)

---

## 1. What is Being Requested?

**Feature Name:**  
[e.g., "SQL Server Connector (cloud + on-prem)"]

**Current TRB Status:**  
[e.g., "Approved (non-PHI only until GA)"]

**Exception Request:**  
[Describe what you are asking TRB to approve that deviates from the standard decision. Be specific.]

**Example:**  
"We request a waiver to use SQL Server Connector with **non-sensitive member identifiers only** (member ID, DOB, region) for [specific project] before the feature reaches GA. This is non-PHI use, but outside the currently-approved scope (analytics team only). We need to expand to Claims Processing team."

---

## 2. Business Justification

**Why is this request important to Acme Health Plan?**

[Describe the business value, timeline pressure, strategic importance, and consequences of denial.]

**Example:**
"Our annual member retention analysis is due [date]. We cannot delay past [date] without impacting [business outcome]. Existing SQL connectors cannot efficiently join member demographics with claims; SQL Server connector is ideal. Without this, we face a [financial/strategic] impact of [quantified estimate]."

**Key Success Metrics:**
- [e.g., "Reduce query time from 60 minutes to <15 minutes"]
- [e.g., "Enable claims team to self-serve; reduce IT support backlog"]

---

## 3. Risk Analysis

**What TRB decision are you asking to override?**

[Reference the specific condition, approval criteria, or decision being waived.]

**Example:**
"We are asking TRB to approve use by Claims Processing team, which currently lacks PHI-handling training. This overrides the standard requirement (COND-XXX: only trained Analytics team authorized)."

### Proposed Mitigation

[For each overridden control, propose an alternative mitigation that TRB might accept.]

| Overridden Control | Original Risk | Proposed Mitigation | Residual Risk | Acceptability |
|-------------------|--------------|-------------------|---------------|--------------|
| [e.g., Claims team lacks PHI training] | [e.g., Unauthorized data access, compliance violation] | [e.g., Data access limited to non-sensitive member IDs only; no claims detail; limited query results (≤1000 rows)] | [e.g., Low—scope is narrow, no sensitive data] | [ ] Acceptable |
| | | | | |

**Risk Acceptance Statement:**  
"We understand the risk and accept responsibility for mitigation. We commit to [action], and we agree to suspend the feature if [escalation criteria] occur."

---

## 4. Timeline & Scope

**Project / Use Case:**  
[Name and brief description]

**Duration Needed:**  
- Start: [YYYY-MM-DD]  
- End: [YYYY-MM-DD] (or "until GA")  
- Rationale: [e.g., "Annual review period; scope resets after"]

**Users Affected:**  
- Count: [N teams / N people]
- Roles: [Titles / Departments]
- Training Status: [N% trained | % untrained]

**Data Scope:**  
- **Data Elements:** [List specific columns/tables, not "all PHI"]
- **Row Count:** [Estimated]
- **Sensitivity:** [Non-sensitive, Confidential, PHI, etc.]

**Example:**
"Claims Processing team (8 people, all Analysts); 90-day pilot through [date]. Data: member demographics table only (member_id, member_name, DOB, ZIP, region). No clinical or claims detail. ~500K rows. Non-PHI (per HIPAA, member ID without diagnosis is not PHI)."

---

## 5. Conditions Offered by Requestor

[What is the requestor willing to do to make this lower-risk for TRB?]

| Condition # | Offering / Commitment | Verification | Duration |
|------------|---------------------|--------------|----------|
| 1 | [e.g., Enhanced query logging—audit every query, not spot-checks] | [e.g., TRB reviews logs weekly] | [Duration] |
| 2 | [e.g., Rotate access—only 2 authorized users at a time] | [e.g., Weekly access review] | [Duration] |
| 3 | [e.g., Incident escalation—notify CISO within 1 hour of any suspicion] | [e.g., Incident report template + contact list] | [Duration] |

---

## 6. Compliance Certification

**Requestor Attestation:**

I certify that:
- ✓ The business justification above is accurate to the best of my knowledge.
- ✓ I have authority to commit [department/team] to the mitigation conditions listed above.
- ✓ I have reviewed the TRB Charter and understand the regulatory framework (HIPAA, Acme Health Plan policy).
- ✓ I accept responsibility for monitoring and escalating compliance issues during this exception period.

**Signature:**  
[Requestor Name / Title]  
_________________________ Date: [YYYY-MM-DD]

---

## 7. Supporting Documentation

Attach or reference:
- [ ] Risk assessment or threat analysis specific to this request (if not already provided)
- [ ] Project charter or business case (URL / Attachment)
- [ ] Email approval from [Department Head / Executive Sponsor]
- [ ] Training completion certificates (if applicable)

---

## For TRB Use Only

| Field | Value |
|-------|-------|
| **TRB Review Meeting** | TRBM-YYYY-MM-DD |
| **TRB Lead Reviewer** | [Architect/Privacy Officer] |
| **Assigned Verifier** | [Compliance Officer] |
| **Exception Status** | [ ] Approved | [ ] Approved with Modified Conditions | [ ] Denied | [ ] Deferred |
| **Expiration Date** | [Auto-calculated: start + duration] |
| **Sunset Trigger** | [ ] Manual review at [date] | [ ] Automatic expiration at [date] | [ ] Upon feature GA |

---

### TRB Vote & Rationale

**Unanimous Approval Required?** [Per charter: yes for PHI-related exceptions]

**Board Votes:**
- [ ] CISO: Approve / Reject / Abstain
- [ ] CPO: Approve / Reject / Abstain
- [ ] Enterprise Architect: Approve / Reject / Abstain
- [ ] [Other board members]: Approve / Reject / Abstain

**Rationale Summary:**  
[Why TRB voted to approve or deny. Include any conditions modified from requestor's offer.]

---

**Exception Approved By:**  
[CISO Signature] _________________ Date: [YYYY-MM-DD]

[CPO Signature] _________________ Date: [YYYY-MM-DD]

---

**Escalation on Denial:**  
If TRB denies this exception, requestor may escalate to [Executive Committee] within [5 business days] with additional evidence. [Executive Committee] may override TRB decision only with documented CISO concurrence and risk acceptance.

---

**Classification:** Internal – Synthetic Sample
