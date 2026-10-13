-- =====================================================================
-- STRUCTURED TECH REVIEW BOARD (TRB) DATA MODEL
-- For Acme Health Plan — Databricks Feature Tracker
--
-- Schemas: platform.trb (TRB governance tables)
--          platform.feature_tracker (weekly job — source of current dbx_phase)
--
-- PHI eligibility rule (CANONICAL.md):
-- PHI-eligible ⇔ current Databricks phase (from feature_tracker.features) = GA
--                AND TRB status = Approved
-- "Approved with Conditions" is NOT PHI-eligible until every condition closes.
--
-- Design principles:
-- - ADR-inspired: event audit trail, decision snapshots, immutable history
-- - Risk management: identified risks, mitigations, condition tracking
-- - Genie-friendly: clear joins, semantic comments, document lineage
-- =====================================================================

-- MEETINGS: TRB governance calendar
CREATE TABLE IF NOT EXISTS ${catalog}.trb.meetings (
  meeting_id STRING NOT NULL COMMENT "TRB meeting ID: TRBM-YYYY-MM-DD",
  meeting_date DATE NOT NULL COMMENT "Date of TRB meeting",
  meeting_type STRING NOT NULL COMMENT "Meeting type: in-person, virtual, hybrid",
  meeting_location STRING COMMENT "Location or platform of meeting",
  attendees STRING NOT NULL COMMENT "Comma-separated list of attendee roles (CISO, Chief Privacy Officer, Enterprise Architect, Platform Engineering Lead, Data Governance Lead, Compliance Officer)",
  quorum_met BOOLEAN NOT NULL COMMENT "Whether quorum was met for decisions",
  meeting_notes STRING COMMENT "Summary of meeting discussions",
  minutes_url STRING COMMENT "Link to detailed meeting minutes in UC volume",
  created_at TIMESTAMP NOT NULL COMMENT "Timestamp when record was created",
  CONSTRAINT pk_meetings PRIMARY KEY (meeting_id)
) USING DELTA
COMMENT "TRB biweekly meetings; governance calendar for review decisions";

-- REVIEWS: Main fact table — one row per feature review cycle
CREATE TABLE IF NOT EXISTS ${catalog}.trb.reviews (
  review_id STRING NOT NULL COMMENT "Unique review ID: TRB-YYYY-NNN (e.g., TRB-2026-001)",
  feature_key STRING NOT NULL COMMENT "Feature identifier: feature_name@domain (e.g., Genie One@SQL & BI Analytics)",
  feature_name STRING NOT NULL COMMENT "Human-readable feature name",
  domain STRING NOT NULL COMMENT "Databricks feature domain",
  dbx_phase_at_decision STRING NOT NULL COMMENT "Databricks release phase at time of decision (snapshot). Current phase comes from ${catalog}.feature_tracker.features",
  current_trb_status STRING NOT NULL COMMENT "Latest TRB status: Not Reviewed, Under Review, Approved with Conditions, Approved, Rejected, Retired",
  approved_scope STRING COMMENT "Scope of approval if Approved/Approved with Conditions: PHI, Non-PHI only, Sandbox only (synthetic data), None",
  initial_submission_date DATE NOT NULL COMMENT "Date feature was first submitted to TRB",
  latest_review_date DATE NOT NULL COMMENT "Most recent TRB review date",
  decision_date DATE COMMENT "Date final decision was made (only set when status = Approved/Rejected/Retired/Under Review after first presentation)",
  primary_reviewer_role STRING COMMENT "Primary reviewer role (CISO, Chief Privacy Officer, Enterprise Architect, Platform Engineering Lead, Data Governance Lead, Compliance Officer)",
  approval_meeting_id STRING COMMENT "Meeting ID where decision was made (FK to meetings)",
  rereview_trigger STRING COMMENT "Condition that would trigger a re-review (e.g., 'Databricks phase → GA')",
  next_review_date DATE COMMENT "Scheduled date for next review or condition verification",
  requesting_business_unit STRING COMMENT "Business unit requesting the feature",
  use_cases ARRAY<STRING> COMMENT "Use cases or business drivers for the review",
  review_context STRING NOT NULL COMMENT "Why was this feature submitted? Business need, risk assessment, or change trigger",
  identified_risks STRING COMMENT "Comma-separated list of identified risks or concerns",
  mitigations STRING COMMENT "Proposed or implemented mitigations",
  open_issue_count INT COMMENT "Number of open review issues or objections",
  closed_issue_count INT COMMENT "Number of resolved issues",
  created_at TIMESTAMP NOT NULL COMMENT "Record creation timestamp",
  updated_at TIMESTAMP NOT NULL COMMENT "Last update timestamp",
  CONSTRAINT pk_reviews PRIMARY KEY (review_id),
  CONSTRAINT fk_reviews_meeting FOREIGN KEY (approval_meeting_id) REFERENCES ${catalog}.trb.meetings(meeting_id)
) USING DELTA
COMMENT "Feature reviews: one row per TRB review cycle. Main table for Genie space queries. PHI eligibility computed via v_feature_phi_eligibility view.";

-- REVIEW_HISTORY: Event log of status transitions and decisions
CREATE TABLE IF NOT EXISTS ${catalog}.trb.review_history (
  history_id STRING NOT NULL COMMENT "Unique event ID (UUID)",
  review_id STRING NOT NULL COMMENT "FK to reviews.review_id",
  event_date DATE NOT NULL COMMENT "Date of status change or event",
  event_type STRING NOT NULL COMMENT "Event type: status_change, condition_added, condition_removed, issue_opened, issue_closed, reopened, meeting_presented, objection_raised, objection_resolved",
  old_status STRING COMMENT "Previous TRB status (if status_change)",
  new_status STRING COMMENT "New TRB status (if status_change)",
  changed_by_role STRING NOT NULL COMMENT "Role of person making the change",
  summary STRING NOT NULL COMMENT "What happened (e.g., 'Status moved from Under Review to Approved with Conditions')",
  details STRING COMMENT "Optional details or notes about the change",
  created_at TIMESTAMP NOT NULL COMMENT "Event creation timestamp",
  CONSTRAINT pk_review_history PRIMARY KEY (history_id),
  CONSTRAINT fk_review_history FOREIGN KEY (review_id) REFERENCES ${catalog}.trb.reviews(review_id)
) USING DELTA
COMMENT "Audit log: immutable record of every status change and decision event in the review lifecycle";

-- APPROVAL_CONDITIONS: Specific conditions attached to 'Approved with Conditions' decisions
CREATE TABLE IF NOT EXISTS ${catalog}.trb.approval_conditions (
  condition_id STRING NOT NULL COMMENT "Condition ID: COND-NNN-N (e.g., COND-005-1)",
  review_id STRING NOT NULL COMMENT "FK to reviews.review_id",
  condition_number INT NOT NULL COMMENT "Sequential number within a review (1, 2, 3, ...)",
  condition_title STRING NOT NULL COMMENT "Short title of the condition",
  condition_text STRING NOT NULL COMMENT "Full description of the condition",
  condition_rationale STRING NOT NULL COMMENT "Why was this condition imposed? (e.g., HIPAA or NIST control reference)",
  applicable_at_phase STRING NOT NULL COMMENT "Databricks phase at which condition applies: GA, Public Preview, All Phases",
  verification_method STRING NOT NULL COMMENT "How will compliance be verified? (e.g., Configuration audit, Code review, Third-party attestation)",
  verification_status STRING NOT NULL COMMENT "Verification status: Open, In Progress, Closed",
  verification_date DATE COMMENT "Date condition was verified/closed",
  verified_by_role STRING COMMENT "Role of person who verified compliance",
  verification_notes STRING COMMENT "Details of verification",
  created_at TIMESTAMP NOT NULL COMMENT "Condition creation timestamp",
  updated_at TIMESTAMP NOT NULL COMMENT "Last update timestamp",
  CONSTRAINT pk_conditions PRIMARY KEY (condition_id),
  CONSTRAINT fk_conditions FOREIGN KEY (review_id) REFERENCES ${catalog}.trb.reviews(review_id)
) USING DELTA
COMMENT "Approval conditions: specific requirements attached to 'Approved with Conditions' decisions. Review moves to 'Approved' only when all conditions verify to 'Closed'.";

-- CONTROL_MAPPINGS: Links reviews to security/compliance control frameworks
CREATE TABLE IF NOT EXISTS ${catalog}.trb.control_mappings (
  mapping_id STRING NOT NULL COMMENT "Unique mapping ID (UUID)",
  review_id STRING NOT NULL COMMENT "FK to reviews.review_id",
  control_framework STRING NOT NULL COMMENT "Framework: NIST-800-53-R5, HIPAA-Security-Rule, HIPAA-Privacy-Rule, HITRUST-CSF, SOC2, ISO27001",
  control_id STRING NOT NULL COMMENT "Framework-specific control ID (e.g., AC-2, 45 CFR 164.312(a)(2)(i))",
  control_name STRING NOT NULL COMMENT "Human-readable control name",
  implementation_status STRING NOT NULL COMMENT "Status: Satisfied, Partially Satisfied, Not Addressed, N/A, Compensating Control",
  evidence_description STRING COMMENT "How is this control satisfied?",
  evidence_url STRING COMMENT "Link to evidence or documentation",
  notes STRING COMMENT "Additional notes or caveats",
  created_at TIMESTAMP NOT NULL COMMENT "Mapping creation timestamp",
  updated_at TIMESTAMP NOT NULL COMMENT "Last update timestamp",
  CONSTRAINT pk_control_mappings PRIMARY KEY (mapping_id),
  CONSTRAINT fk_control_mappings FOREIGN KEY (review_id) REFERENCES ${catalog}.trb.reviews(review_id)
) USING DELTA
COMMENT "Control mappings: links each review to applicable NIST/HIPAA/HITRUST control requirements";

-- DOCUMENTS: TRB-related governance documents (minutes, decisions, risk assessments, etc.)
CREATE TABLE IF NOT EXISTS ${catalog}.trb.documents (
  doc_id STRING NOT NULL COMMENT "Document ID (e.g., DR-2026-001, MIN-TRBM-2026-07-14, INT-006, RA-005, CHARTER-2026, etc.)",
  doc_type STRING NOT NULL COMMENT "Document type: charter, minutes, intake, risk_assessment, decision_record, approval_letter, exception",
  title STRING NOT NULL COMMENT "Document title",
  doc_date DATE NOT NULL COMMENT "Date of document",
  meeting_id STRING COMMENT "Meeting ID if this document is from a meeting (FK to meetings)",
  volume_path STRING NOT NULL COMMENT "Path in UC volume: /Volumes/platform/trb/corpus/<file>.md",
  review_ids ARRAY<STRING> COMMENT "Array of review_ids referenced in this document",
  created_at TIMESTAMP NOT NULL COMMENT "Record creation timestamp",
  CONSTRAINT pk_documents PRIMARY KEY (doc_id),
  CONSTRAINT fk_documents_meeting FOREIGN KEY (meeting_id) REFERENCES ${catalog}.trb.meetings(meeting_id)
) USING DELTA
COMMENT "TRB governance documents (minutes, decisions, risk assessments). ARRAY<review_ids> allows Genie to find all documents for a review.";

-- EXCEPTIONS: Exceptions, waivers, and deviations from policy
CREATE TABLE IF NOT EXISTS ${catalog}.trb.exceptions (
  exception_id STRING NOT NULL COMMENT "Exception ID: EXC-YYYY-NNN (e.g., EXC-2026-001)",
  review_id STRING NOT NULL COMMENT "FK to reviews.review_id (required; every exception ties to a review)",
  exception_type STRING NOT NULL COMMENT "Type: PHI-Restriction, Production-Prohibition, Condition-Waiver, Control-Gap-Acceptance, Sunset-Waiver",
  description STRING NOT NULL COMMENT "What is the exception?",
  business_justification STRING NOT NULL COMMENT "Why is the exception necessary?",
  risk_assessment STRING COMMENT "Associated risks and compensating controls",
  exception_status STRING NOT NULL COMMENT "Status: Requested, Approved, Denied, Expired, Withdrawn",
  requested_by_role STRING NOT NULL COMMENT "Role of person requesting the exception",
  decided_by_role STRING COMMENT "Role of person who decided on the exception",
  decision_meeting_id STRING COMMENT "Meeting ID where exception was decided (FK to meetings)",
  exception_start_date DATE COMMENT "Date exception becomes effective (null if Requested or Denied)",
  exception_end_date DATE COMMENT "Date exception expires (null = no automatic sunset)",
  renewal_date DATE COMMENT "Date for next renewal review (null = never expires)",
  created_at TIMESTAMP NOT NULL COMMENT "Exception creation timestamp",
  updated_at TIMESTAMP NOT NULL COMMENT "Last update timestamp",
  CONSTRAINT pk_exceptions PRIMARY KEY (exception_id),
  CONSTRAINT fk_exceptions_review FOREIGN KEY (review_id) REFERENCES ${catalog}.trb.reviews(review_id),
  CONSTRAINT fk_exceptions_meeting FOREIGN KEY (decision_meeting_id) REFERENCES ${catalog}.trb.meetings(meeting_id)
) USING DELTA
COMMENT "Exceptions and waivers: approved/requested deviations from policy. Exception_status tracks the lifecycle (Requested → Approved/Denied).";

-- =====================================================================
-- VIEW: v_feature_phi_eligibility
--
-- Computed PHI eligibility for Genie queries. A feature is PHI-eligible
-- only when (1) current Databricks phase (from feature_tracker.features) = GA
-- AND (2) TRB status = Approved (not "with Conditions"; conditions must all close first).
-- =====================================================================
CREATE OR REPLACE VIEW ${catalog}.trb.v_feature_phi_eligibility
COMMENT "PHI eligibility per reviewed feature, with the blocking reason. PHI-eligible only when the CURRENT Databricks phase (from feature_tracker.features) is GA AND the TRB status is Approved. Use for any 'can we use X with PHI' question."
AS
WITH open_conds AS (
  SELECT review_id, COUNT(*) AS open_conditions_count
  FROM ${catalog}.trb.approval_conditions
  WHERE verification_status <> 'Closed'
  GROUP BY review_id
)
SELECT
  r.review_id,
  r.feature_key,
  r.feature_name,
  r.domain,
  f.dbx_phase AS current_dbx_phase,
  r.dbx_phase_at_decision,
  r.current_trb_status,
  r.approved_scope,
  (f.dbx_phase = 'GA' AND r.current_trb_status = 'Approved') AS is_phi_eligible,
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
  END AS blocking_reason,
  COALESCE(oc.open_conditions_count, 0) AS open_conditions_count,
  r.initial_submission_date,
  r.decision_date,
  r.next_review_date
FROM ${catalog}.trb.reviews r
LEFT JOIN ${catalog}.feature_tracker.features f ON r.feature_key = f.feature_key
LEFT JOIN open_conds oc ON r.review_id = oc.review_id;

-- =====================================================================
-- VIEW: v_open_conditions — conditions not yet verified closed
-- =====================================================================
CREATE OR REPLACE VIEW ${catalog}.trb.v_open_conditions
COMMENT "Conditions not yet verified closed (Open or In Progress), with their feature, for compliance follow-up."
AS
SELECT
  ac.condition_id, ac.review_id, r.feature_key, r.feature_name,
  ac.condition_title, ac.condition_text, ac.condition_rationale,
  ac.verification_method, ac.verification_status, ac.verification_date,
  ac.verified_by_role, ac.verification_notes
FROM ${catalog}.trb.approval_conditions ac
JOIN ${catalog}.trb.reviews r ON ac.review_id = r.review_id
WHERE ac.verification_status <> 'Closed';
