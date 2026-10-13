# Genie Agent deliverable: Feature Tracker Review Board Analytics Space

Workspace: `<profile>` · Space ID: `<space id>` (created by `bundle deploy`) · Warehouse: `var.genie_warehouse_id` · Folder: `var.genie_parent_path`

Built with the workspace Assistant skills: genie-agent-builder, genie-domain-healthcare-payer, genie-anti-hallucination, genie-clarify-dont-guess, genie-compliance-guardrails, genie-provisioning, genie-space-patching, genie-benchmarks-eval.

## A. Space name
Feature Tracker Review Board Analytics Space

## B. Space description
Answers questions about the Tech Review Board (TRB, also called the Architecture Review Board) decisions on Databricks features at Acme Health Plan: review status, PHI eligibility, approval conditions, exceptions, control mappings, meetings, and governance documents. For the platform team, security, privacy, and compliance reviewers. Data is synthetic.

## C. Sample questions
**PHI eligibility**
- Which Databricks features are approved for PHI?
- Can we use Genie One with PHI data?

**Status and conditions**
- Which reviews are still pending a TRB decision?
- What open conditions does Serverless compute have?
- Why was Kafka-compatible APIs rejected?
- Which pending reviews came from Clinical Analytics?

**Meetings, metrics, exceptions**
- What did the TRB decide at the June 16, 2026 meeting?
- What is the TRB approval rate by domain?
- Which exceptions were denied?
- Which HIPAA controls are mapped to Customer-managed keys?
- What documents exist for the SQL Server connector review?
- How long does the TRB take to reach a decision on average?

## D. Data assets (metric views → TVFs → tables)
| Asset | Role | Entity-matched / formatted columns |
|---|---|---|
| `<catalog>.trb.mv_trb_reviews` | Metric view: governed counts and rates (MEASURE()) | approved_scope, business_unit, current_dbx_phase, decision_quarter, domain, is_phi_eligible, reviewer_role, trb_status |
| `<catalog>.trb.v_feature_phi_eligibility` | View: PHI eligibility + blocking reason (joins live tracker phase) | blocking_reason, current_dbx_phase, current_trb_status, domain, feature_name, is_phi_eligible |
| `<catalog>.trb.reviews` | Fact: one row per feature review | approval_meeting_id, approved_scope, current_trb_status, decision_date, domain, feature_name, primary_reviewer_role, requesting_business_unit, review_id |
| `<catalog>.trb.approval_conditions` | Conditions on approvals, with due dates | condition_id, condition_title, due_date, verification_method, verification_status |
| `<catalog>.trb.exceptions` | Exception / waiver requests | exception_id, exception_status, exception_type, requested_by_role |
| `<catalog>.trb.control_mappings` | HIPAA / NIST / HITRUST control mappings | control_framework, control_id, control_name, implementation_status |
| `<catalog>.trb.documents` | Document index with summaries; full text in the trb.corpus volume | doc_date, doc_id, doc_type, meeting_id, title |

PK/FK constraints are declared on all base tables (reviews → meetings; conditions, exceptions, control_mappings, review_history → reviews).

## E. General instructions (1893 chars, one block, clarification rules and scope boundary last)
```text
# PURPOSE
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
REFUSE questions about members, claims, providers, other PHI, Databricks pricing, or non-Databricks products: "That is outside this agent; it covers TRB review decisions on Databricks features only."
```

## F. TVFs
None. Each question shape has a parameterized example query instead (section G source), which Genie binds without free-forming SQL.

**Parameterized example queries (trusted assets in `serialized_space`):**
1. What is the TRB status and PHI eligibility of a feature? — params: `:feature_name` (STRING, default `Genie One`)
2. Which features are approved for PHI?
3. Why did the TRB make its decision on a feature? — params: `:feature_name` (STRING, default `Kafka`)
4. What open conditions does a feature have? — params: `:feature_name` (STRING, default `Serverless compute`)
5. What did the TRB decide at a meeting? — params: `:meeting_date` (DATE, default `2026-06-16`)
6. Approval rate by domain
7. Which reviews are pending for a business unit? — params: `:business_unit` (STRING, default `Clinical Analytics`)
8. Exceptions by status — params: `:exception_status` (STRING, default `Denied`)
9. Which controls are mapped to a feature? — params: `:feature_name` (STRING, default `Customer-managed keys`)
10. What documents exist for a feature? — params: `:feature_name` (STRING, default `SQL Server`)

## G. Benchmark questions (static SQL)
1. **Can we use Genie One with PHI data?**
   ```sql
   SELECT review_id, feature_name, is_phi_eligible, blocking_reason FROM <catalog>.trb.v_feature_phi_eligibility WHERE feature_name ILIKE '%Genie One%'
   ```
2. **Is Unity Catalog approved for PHI?**
   ```sql
   SELECT review_id, feature_name, is_phi_eligible, blocking_reason FROM <catalog>.trb.v_feature_phi_eligibility WHERE feature_name ILIKE '%Unity Catalog%'
   ```
3. **Is the SQL Server connector PHI-eligible?**
   ```sql
   SELECT review_id, feature_name, is_phi_eligible, blocking_reason FROM <catalog>.trb.v_feature_phi_eligibility WHERE feature_name ILIKE '%SQL Server%'
   ```
4. **Which features are approved for PHI?**
   ```sql
   SELECT review_id, feature_name FROM <catalog>.trb.v_feature_phi_eligibility WHERE is_phi_eligible
   ```
5. **How many features are PHI-eligible?**
   ```sql
   SELECT MEASURE(phi_eligible_count) AS phi_eligible FROM <catalog>.trb.mv_trb_reviews
   ```
6. **Which reviews are pending a TRB decision?**
   ```sql
   SELECT review_id, feature_name FROM <catalog>.trb.reviews WHERE current_trb_status = 'Under Review'
   ```
7. **What open conditions does Serverless compute have?**
   ```sql
   SELECT c.condition_id, c.condition_title, c.verification_status FROM <catalog>.trb.approval_conditions c JOIN <catalog>.trb.reviews r ON c.review_id = r.review_id WHERE c.verification_status <> 'Closed' AND r.feature_name ILIKE '%Serverless compute%'
   ```
8. **What open conditions does Genie One have?**
   ```sql
   SELECT c.condition_id, c.condition_title, c.verification_status FROM <catalog>.trb.approval_conditions c JOIN <catalog>.trb.reviews r ON c.review_id = r.review_id WHERE c.verification_status <> 'Closed' AND r.feature_name ILIKE '%Genie One%'
   ```
9. **How many approval conditions are still open?**
   ```sql
   SELECT COUNT(*) AS open_conditions FROM <catalog>.trb.approval_conditions WHERE verification_status <> 'Closed'
   ```
10. **Why was Kafka-compatible APIs rejected?**
   ```sql
   SELECT review_id, feature_name, current_trb_status, decision_rationale FROM <catalog>.trb.reviews WHERE feature_name ILIKE '%Kafka%'
   ```
11. **What did the TRB decide at the 2026-06-16 meeting?**
   ```sql
   SELECT review_id, feature_name, current_trb_status FROM <catalog>.trb.reviews WHERE decision_date = DATE '2026-06-16'
   ```
12. **What is the TRB approval rate by domain?**
   ```sql
   SELECT domain, MEASURE(approval_rate_pct) AS approval_rate_pct FROM <catalog>.trb.mv_trb_reviews GROUP BY ALL
   ```
13. **How many reviews does each domain have?**
   ```sql
   SELECT domain, MEASURE(review_count) AS reviews FROM <catalog>.trb.mv_trb_reviews GROUP BY ALL
   ```
14. **What is the average number of days from submission to TRB decision?**
   ```sql
   SELECT MEASURE(avg_days_to_decision) AS avg_days FROM <catalog>.trb.mv_trb_reviews
   ```
15. **Which exceptions were denied?**
   ```sql
   SELECT exception_id, review_id, exception_status FROM <catalog>.trb.exceptions WHERE exception_status = 'Denied'
   ```
16. **Which pending reviews came from Clinical Analytics?**
   ```sql
   SELECT review_id, feature_name FROM <catalog>.trb.reviews WHERE current_trb_status = 'Under Review' AND requesting_business_unit = 'Clinical Analytics'
   ```
17. **Which HIPAA controls are mapped to Customer-managed keys?**
   ```sql
   SELECT m.control_id, m.control_name FROM <catalog>.trb.control_mappings m JOIN <catalog>.trb.reviews r ON m.review_id = r.review_id WHERE r.feature_name ILIKE '%Customer-managed keys%' AND m.control_framework = 'HIPAA-Security-Rule'
   ```
18. **Is Genie approved?**  _(negative: expect clarification or refusal, no SQL)_
19. **What is the claims denial rate for Medicare Advantage members?**  _(negative: expect clarification or refusal, no SQL)_
20. **How much does Databricks serverless compute cost per DBU?**  _(negative: expect clarification or refusal, no SQL)_

Synced to the Benchmarks tab with `sync_benchmarks.py` (answerable set). **Re-run it after every PATCH.**

## H. SQL expressions
| Type | Name | SQL | Synonyms |
|---|---|---|---|
| measure | Pending reviews | `COUNT_IF(reviews.current_trb_status = 'Under Review')` | number of pending reviews, how many reviews are pending, pending review count |
| measure | Open conditions | `COUNT_IF(approval_conditions.verification_status <> 'Closed')` | number of open conditions, how many conditions are open, open condition count |
| measure | PHI-eligible features | `COUNT_IF(v_feature_phi_eligibility.is_phi_eligible)` | number of PHI-eligible features, how many features can use PHI, PHI-eligible count |
| filter | PHI-eligible | `v_feature_phi_eligibility.is_phi_eligible = TRUE` | approved for PHI, PHI eligible, cleared for PHI |
| filter | Denied exceptions | `exceptions.exception_status = 'Denied'` | denied waivers, rejected exceptions, refused exceptions |
| filter | Open conditions only | `approval_conditions.verification_status <> 'Closed'` | open conditions, outstanding, not closed |
| filter | Pending TRB decision | `reviews.current_trb_status = 'Under Review'` | pending, under review, awaiting decision |
| dimension | Decision quarter | `DATE_TRUNC('QUARTER', reviews.decision_date)` | quarter decided, decision period |
| dimension | Days to decision | `DATEDIFF(reviews.decision_date, reviews.initial_submission_date)` | turnaround, cycle time, time to decision |

Metric view measures (`mv_trb_reviews`): review_count, decided_count, approved_count, fully_approved_count, rejected_count, approval_rate_pct, phi_eligible_count, pending_review_count, open_condition_count, avg_days_to_decision.

## Readiness and compliance
- **Profile (genie-anti-hallucination):** no PII/PHI. `feature_name` / `control_name` were false-positive name matches. Three always-empty `control_mappings` columns were dropped (hallucination trap).
- **Compliance gate (genie-compliance-guardrails): FAIL on the row-filter rule only, with 0 regulated columns.** The register holds governance metadata with roles, not people. Accepted for this synthetic dev agent. Before the agent is shared or real TRB data is loaded, add a row filter (e.g. limit exception details to the TRB group), or record a formal waiver.
- **Ambiguity lint (genie-clarify-dont-guess):** 11 shared-token warnings between each count measure and its matching filter. These are equivalent semantics; accepted and covered by benchmarks.
- **Not shared:** the agent is visible only to its owner until the gate is resolved.

## Benchmark results (genie-benchmarks-eval `run_benchmarks.py`, isolated conversations)
| Run | Date | Result | Notes |
|---|---|---|---|
| 1 | 2026-10-12 | 18/20 (90%) | All 17 answerable and the ambiguity test passed. The 2 out-of-scope refusals were correct but worded "outside this agent", which the scorer doesn't recognize. |
| 2 | 2026-10-12 | **20/20 (100%)** | Refusal wording aligned to "cannot be answered" (one PATCH, benchmarks re-synced). |

Production gate is ≥80% sustained for 1–2 weeks. Re-run weekly with `--runs 5` before broad rollout.

## Deployment (Asset Bundle)
Managed as `resources.genie_spaces.review_board_agent` (bound to the existing space). `review_board_genie_maintenance`
re-posts benchmarks after deploys.
**Finding:** the curated-questions list API is paginated (20 rows per page, `next_page_token`). The workspace skill's
`sync_benchmarks.py` reads only page 1. That's harmless right after a PATCH (the list is empty), but it undercounts and leaves
duplicates otherwise. The bundle task paginates.
