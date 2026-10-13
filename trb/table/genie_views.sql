-- Genie-facing semantic layer for the TRB register. Run after ddl.sql / ddl_v2.sql.

-- PHI eligibility with column comments (views take comments inline, not via ALTER).
CREATE OR REPLACE VIEW ${catalog}.trb.v_feature_phi_eligibility (
  review_id COMMENT 'TRB review ID, TRB-YYYY-NNN',
  feature_key COMMENT 'Feature key "<name>@<domain>"; joins to reviews.feature_key',
  feature_name COMMENT 'Databricks feature name, e.g. "Genie One", "Unity Catalog"',
  domain COMMENT 'Tracker domain, e.g. "Security & Networking", "SQL & BI Analytics"',
  current_dbx_phase COMMENT 'CURRENT Databricks release phase from the weekly tracker job: Upcoming, Private Preview, Beta, Public Preview, GA, Deprecated',
  dbx_phase_at_decision COMMENT 'Databricks phase when the TRB decided (snapshot)',
  current_trb_status COMMENT 'TRB status: Not Reviewed, Under Review, Approved with Conditions, Approved, Rejected, Retired',
  approved_scope COMMENT 'What the approval allows: PHI, PHI (after all conditions close), Non-PHI only, Sandbox only (synthetic data), None',
  is_phi_eligible COMMENT 'TRUE only when current_dbx_phase = GA AND current_trb_status = Approved. The single answer to "can we use this with PHI?"',
  blocking_reason COMMENT 'Why the feature is not PHI-eligible (or "PHI-eligible")',
  open_conditions_count COMMENT 'Approval conditions not yet verified Closed (Open or In Progress)',
  initial_submission_date COMMENT 'Date the intake was submitted',
  decision_date COMMENT 'Date of the TRB decision; NULL while Under Review or Not Reviewed',
  next_review_date COMMENT 'Next scheduled re-review or condition check'
)
COMMENT 'PHI eligibility per reviewed Databricks feature, with the blocking reason. Use for any "can we use X with PHI" or "which features are approved for PHI" question.'
AS
WITH open_conds AS (
  SELECT review_id, COUNT(*) AS open_conditions_count
  FROM ${catalog}.trb.approval_conditions
  WHERE verification_status <> 'Closed'
  GROUP BY review_id
)
SELECT
  r.review_id, r.feature_key, r.feature_name, r.domain,
  f.dbx_phase, r.dbx_phase_at_decision, r.current_trb_status, r.approved_scope,
  (f.dbx_phase = 'GA' AND r.current_trb_status = 'Approved'),
  CASE
    WHEN f.dbx_phase = 'GA' AND r.current_trb_status = 'Approved' THEN 'PHI-eligible'
    WHEN r.current_trb_status = 'Rejected' THEN 'Rejected by TRB'
    WHEN r.current_trb_status = 'Retired' THEN 'Retired by TRB'
    WHEN f.dbx_phase IS NULL THEN 'Feature not in tracker'
    WHEN f.dbx_phase <> 'GA' THEN concat('Databricks phase is ', f.dbx_phase, ' (PHI requires GA)')
    WHEN r.current_trb_status = 'Approved with Conditions'
      THEN concat('Approved with conditions: ', CAST(COALESCE(oc.open_conditions_count, 0) AS STRING), ' not yet closed')
    WHEN r.current_trb_status = 'Under Review' THEN 'Pending TRB decision'
    ELSE 'Not reviewed by TRB'
  END,
  COALESCE(oc.open_conditions_count, 0),
  r.initial_submission_date, r.decision_date, r.next_review_date
FROM ${catalog}.trb.reviews r
LEFT JOIN ${catalog}.feature_tracker.features f ON r.feature_key = f.feature_key
LEFT JOIN open_conds oc ON r.review_id = oc.review_id;

-- Governed review metrics.
CREATE OR REPLACE VIEW ${catalog}.trb.mv_trb_reviews
WITH METRICS
LANGUAGE YAML
COMMENT 'Governed TRB review metrics: review counts, approval rate, PHI-eligible count, pending reviews, open conditions, days to decision. Query with MEASURE(); one row per review in the source.'
AS $$
version: 0.1
source: >
  SELECT r.review_id, r.feature_name, r.domain, r.current_trb_status, r.approved_scope,
         r.requesting_business_unit, r.primary_reviewer_role, r.decision_date,
         r.initial_submission_date, e.current_dbx_phase, e.is_phi_eligible, e.open_conditions_count
  FROM ${catalog}.trb.reviews r
  JOIN ${catalog}.trb.v_feature_phi_eligibility e ON r.review_id = e.review_id
dimensions:
  - name: domain
    expr: domain
  - name: trb_status
    expr: current_trb_status
  - name: approved_scope
    expr: approved_scope
  - name: business_unit
    expr: requesting_business_unit
  - name: reviewer_role
    expr: primary_reviewer_role
  - name: current_dbx_phase
    expr: current_dbx_phase
  - name: is_phi_eligible
    expr: is_phi_eligible
  - name: decision_quarter
    expr: DATE_TRUNC('QUARTER', decision_date)
  - name: decision_month
    expr: DATE_TRUNC('MONTH', decision_date)
measures:
  - name: review_count
    expr: COUNT(1)
  - name: decided_count
    expr: COUNT_IF(current_trb_status IN ('Approved', 'Approved with Conditions', 'Rejected'))
  - name: approved_count
    expr: COUNT_IF(current_trb_status IN ('Approved', 'Approved with Conditions'))
  - name: fully_approved_count
    expr: COUNT_IF(current_trb_status = 'Approved')
  - name: rejected_count
    expr: COUNT_IF(current_trb_status = 'Rejected')
  - name: approval_rate_pct
    expr: ROUND(100.0 * COUNT_IF(current_trb_status IN ('Approved', 'Approved with Conditions')) / NULLIF(COUNT_IF(current_trb_status IN ('Approved', 'Approved with Conditions', 'Rejected')), 0), 1)
  - name: phi_eligible_count
    expr: COUNT_IF(is_phi_eligible)
  - name: pending_review_count
    expr: COUNT_IF(current_trb_status = 'Under Review')
  - name: open_condition_count
    expr: SUM(open_conditions_count)
  - name: avg_days_to_decision
    expr: ROUND(AVG(DATEDIFF(decision_date, initial_submission_date)), 1)
$$;
