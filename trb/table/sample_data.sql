-- =====================================================================
-- SYNTHETIC SAMPLE DATA FOR ACME HEALTH PLAN TRB (platform.trb schema)
--
-- CANONICAL.md is the single source of truth. All rows match exactly.
-- This is DEMONSTRATION DATA ONLY. Do not use in production.
--
-- Features: 9 reviews (TRB-2026-001 through 009)
-- Meetings: 6 biweekly meetings (2026-07-14 through 2026-09-22)
-- Conditions: 9 conditions total (COND-003-1/2, COND-005-1/2/3/4, COND-007-1/2/3)
-- Exceptions: 2 (EXC-2026-001 Denied, EXC-2026-002 Approved)
-- Documents: required set per CANONICAL.md
-- =====================================================================

-- feature_tracker.features is owned by the weekly refresh job. This file never writes it.

-- Meetings: TRB biweekly calendar (synthetic)
INSERT INTO ${catalog}.trb.meetings VALUES
  ('TRBM-2026-07-14', DATE '2026-07-14', 'in-person', 'Main building, Boardroom A',
   'CISO,Chief Privacy Officer,Enterprise Architect,Platform Engineering Lead',
   TRUE, 'Kickoff: approved Row filters & column masks, SQL Server CDC, rejected Kafka APIs for Beta.',
   'https://confluence/spaces/COMPLIANCE/pages/TRBM-2026-07-14', CURRENT_TIMESTAMP()),

  ('TRBM-2026-07-28', DATE '2026-07-28', 'virtual', 'Zoom',
   'CISO,Chief Privacy Officer,Enterprise Architect,Data Governance Lead',
   TRUE, 'Genie One approved with conditions. ABAC introduced, deferred pending attribute design.',
   'https://confluence/spaces/COMPLIANCE/pages/TRBM-2026-07-28', CURRENT_TIMESTAMP()),

  ('TRBM-2026-08-11', DATE '2026-08-11', 'hybrid', 'Teams (main office + 2 remote)',
   'Chief Privacy Officer,Enterprise Architect,Platform Engineering Lead,Compliance Officer',
   TRUE, 'Knowledge Assistant intro, EXC-2026-002 sandbox pilot approved. Databricks Apps intro.',
   'https://confluence/spaces/COMPLIANCE/pages/TRBM-2026-08-11', CURRENT_TIMESTAMP()),

  ('TRBM-2026-08-25', DATE '2026-08-25', 'virtual', 'WebEx',
   'CISO,Chief Privacy Officer,Enterprise Architect',
   TRUE, 'Mode: Databricks-to-Open approved with conditions. ABAC, Databricks Apps still under review.',
   'https://confluence/spaces/COMPLIANCE/pages/TRBM-2026-08-25', CURRENT_TIMESTAMP()),

  ('TRBM-2026-09-08', DATE '2026-09-08', 'virtual', 'Teams',
   'CISO,Chief Privacy Officer,Data Governance Lead',
   TRUE, 'EXC-2026-001 (SQL Server PHI early access) DENIED. Condition verification status update for 005.',
   'https://confluence/spaces/COMPLIANCE/pages/TRBM-2026-09-08', CURRENT_TIMESTAMP()),

  ('TRBM-2026-09-22', DATE '2026-09-22', 'virtual', 'Zoom',
   'Chief Privacy Officer,Enterprise Architect,Platform Engineering Lead,Compliance Officer',
   TRUE, 'MCP servers intake received. Status check on ABAC, Knowledge Assistant, Databricks Apps.',
   'https://confluence/spaces/COMPLIANCE/pages/TRBM-2026-09-22', CURRENT_TIMESTAMP());

-- Reviews: 9 features from CANONICAL.md
INSERT INTO ${catalog}.trb.reviews VALUES
  -- TRB-2026-001: Row filters & column masks (Approved, PHI)
  ('TRB-2026-001', 'Row filters & column masks@Platform & Governance', 'Row filters & column masks',
   'Platform & Governance', 'GA', 'Approved', 'PHI', DATE '2026-07-01', DATE '2026-07-14', DATE '2026-07-14',
   'Chief Privacy Officer', 'TRBM-2026-07-14', NULL, NULL, NULL,
   array(), 'Standard PHI minimization control for all healthcare use cases.',
   NULL, NULL, 0, 0, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),

  -- TRB-2026-002: ABAC (Under Review)
  ('TRB-2026-002', 'Attribute-based access control (ABAC)@Platform & Governance', 'Attribute-based access control (ABAC)',
   'Platform & Governance', 'GA', 'Under Review', 'None', DATE '2026-07-20', DATE '2026-08-25', NULL,
   'Enterprise Architect', NULL, 'Governed-tag source of truth; IdP attribute sync design', DATE '2026-10-25', 'Platform Engineering',
   array(), 'Deferred 07-28. Follow-up 08-25: still pending attribute source design and IdP integration.',
   'Attribute provenance chain; role hierarchy complexity', 'Attribute source-of-truth registry; quarterly audit', 2, 0, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),

  -- TRB-2026-003: SQL Server (Approved, Non-PHI only)
  ('TRB-2026-003', 'SQL Server (cloud + on-prem)@Ingestion', 'SQL Server (cloud + on-prem)',
   'Ingestion', 'Public Preview', 'Approved', 'Non-PHI only', DATE '2026-07-10', DATE '2026-07-14', DATE '2026-07-14',
   'Platform Engineering Lead', 'TRBM-2026-07-14', 'Databricks phase → GA', DATE '2026-12-31', NULL,
   array('EDW demographics', 'claims reconciliation'), 'CDC from legacy EDW and on-prem SQL instances.',
   'Public Preview compliance restrictions; CDC offset tracking', 'Network isolation; connector audit trail', 0, 2, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),

  -- TRB-2026-004: Kafka (Rejected)
  ('TRB-2026-004', 'Kafka-compatible APIs@Ingestion', 'Kafka-compatible APIs',
   'Ingestion', 'Beta', 'Rejected', 'None', DATE '2026-06-15', DATE '2026-07-14', DATE '2026-07-14',
   'CISO', 'TRBM-2026-07-14', NULL, NULL, NULL,
   array(), 'Beta phase; insufficient audit trail for PHI. Resubmit at GA.',
   'Schema evolution gaps; offset tracking not certified', NULL, 1, 0, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),

  -- TRB-2026-005: Genie One (Approved with Conditions, PHI after conditions close)
  ('TRB-2026-005', 'Genie One@SQL & BI Analytics', 'Genie One',
   'SQL & BI Analytics', 'GA', 'Approved with Conditions', 'PHI (after all conditions close)', DATE '2026-07-05', DATE '2026-07-28', DATE '2026-07-28',
   'Chief Privacy Officer', 'TRBM-2026-07-28', NULL, DATE '2026-10-15', NULL,
   array('BI analytics', 'ad-hoc exploration'), 'AI/BI copilot with guardrails and audit logging.',
   'LLM hallucination risk; prompt injection; audit trail completeness', 'Query guardrails; response sampling; small-cell suppression', 0, 4, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),

  -- TRB-2026-006: Knowledge Assistant (Under Review)
  ('TRB-2026-006', 'Knowledge Assistant@Generative AI & Agents', 'Knowledge Assistant',
   'Generative AI & Agents', 'Beta', 'Under Review', 'Sandbox only (synthetic data)', DATE '2026-08-01', DATE '2026-08-11', NULL,
   'CISO', NULL, NULL, DATE '2026-11-11', NULL,
   array(), 'LLM-based documentation assistant. Sandbox pilot under EXC-2026-002.',
   'Model vendor training data isolation; hallucination vectors; prompt injection', 'Synthetic-data-only sandbox; quarterly red-team', 2, 0, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),

  -- TRB-2026-007: Mode: Databricks-to-Open (Approved with Conditions, Non-PHI only)
  ('TRB-2026-007', 'Mode: Databricks-to-Open (bearer/OIDC)@Sharing & Collaboration', 'Mode: Databricks-to-Open (bearer/OIDC)',
   'Sharing & Collaboration', 'GA', 'Approved with Conditions', 'Non-PHI only (PHI requires a BAA per COND-007-1)', DATE '2026-08-01', DATE '2026-08-25', DATE '2026-08-25',
   'Enterprise Architect', 'TRBM-2026-08-25', NULL, DATE '2026-10-25', NULL,
   array('External Delta Sharing', 'Open Analytics'), 'OAuth bearer + OIDC federation for external recipients.',
   'Bearer token lifecycle; OIDC provider SLA; recipient vetting', 'Token rotation; SOC2 attestation; BAA signature', 0, 3, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),

  -- TRB-2026-008: Databricks Apps (Under Review)
  ('TRB-2026-008', 'Databricks Apps@Apps & Developer Tools', 'Databricks Apps',
   'Apps & Developer Tools', 'GA', 'Under Review', 'None', DATE '2026-09-01', DATE '2026-08-25', NULL,
   'Platform Engineering Lead', NULL, NULL, DATE '2026-10-25', NULL,
   array('BI dashboards', 'internal tooling'), 'Low-code Python Streamlit / R Shiny app builder.',
   'Custom code sandbox isolation; app auth (user vs service-principal); egress control', 'App-level network policy; user session isolation', 2, 0, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),

  -- TRB-2026-009: MCP servers (Not Reviewed)
  ('TRB-2026-009', 'MCP servers@Generative AI & Agents', 'MCP servers',
   'Generative AI & Agents', 'GA', 'Not Reviewed', 'None', DATE '2026-09-22', DATE '2026-09-22', NULL,
   NULL, NULL, NULL, NULL, NULL,
   array(), 'Model Context Protocol: LLM integration with external services. Intake submitted 2026-09-22.',
   NULL, NULL, 0, 0, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP());

-- Approval Conditions (9 total, verification statuses as of 2026-09-22 per CANONICAL.md)
INSERT INTO ${catalog}.trb.approval_conditions VALUES
  -- TRB-2026-003 conditions
  ('COND-003-1', 'TRB-2026-003', 1, 'Connector limited to non-PHI source tables; monthly audit',
   'SQL Server connector shall only ingest from non-PHI source tables. Monthly audit of connector source configuration.',
   'Public Preview phase restriction per Databricks compliance policy',
   'Public Preview', 'Configuration audit + monthly source table whitelist review', 'Closed', DATE '2026-08-14', 'Data Governance Lead',
   'Source tables audited; non-PHI whitelist enforced in connector config.', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),

  ('COND-003-2', 'TRB-2026-003', 2, 'On-prem TLS validation + encryption-in-transit audit',
   'On-premises SQL Server connections must use TLS 1.2+. Annual encryption audit required.',
   '45 CFR 164.312(a)(2)(iv) encryption in transit',
   'All Phases', 'Certificate pinning verification + network traffic inspection', 'Closed', DATE '2026-09-14', 'CISO',
   'TLS 1.2+ enforced; certificate pinning verified on on-prem endpoints.', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),

  -- TRB-2026-005 conditions (4 total; as of 2026-09-22: 1,2 Closed, 3 In Progress, 4 Open)
  ('COND-005-1', 'TRB-2026-005', 1, 'Query audit logging (prompt, generated SQL, row count) via system tables',
   'All Genie queries captured via system tables (system.access.audit for Genie events, system.query.history for generated SQL and row counts), and execution time.',
   'HIPAA 45 CFR 164.312(b) audit controls',
   'GA', 'System tables inspection + query log sampling', 'Closed', DATE '2026-09-15', 'Data Governance Lead',
   'System tables enabled; query logs verified in audit schema with 90-day retention.', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),

  ('COND-005-2', 'TRB-2026-005', 2, 'Row filters / column masks verified with 3 test identities',
   'Row filters and column masks must be tested with 3 distinct user identities (clinician, analyst, finance). Test results documented.',
   'NIST 800-53 AC-3 access enforcement',
   'GA', 'Identity-based testing + access control matrix review', 'Closed', DATE '2026-09-15', 'Enterprise Architect',
   'Row/column ACLs tested with 3 roles; no data leakage detected.', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),

  ('COND-005-3', 'TRB-2026-005', 3, 'Monthly response sampling; small-cell suppression (count < 5)',
   'Monthly statistical review of query results. Automatic suppression of counts < 5 to prevent PHI inference.',
   'HIPAA de-identification standard per 45 CFR 164.514',
   'GA', 'Monthly batch job + suppression rule audit', 'In Progress', NULL, NULL,
   'Suppression rules implemented; first 3 months reviewed; ongoing monthly process.', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),

  ('COND-005-4', 'TRB-2026-005', 4, 'User training (HIPAA minimum-necessary + Genie usage); annual refresh',
   'All Genie users must complete HIPAA minimum-necessary training and Genie usage best practices. Annual refresh required.',
   'HIPAA 45 CFR 164.308(a)(5)(ii) awareness training',
   'GA', 'Training completion attestation + annual LMS renewal', 'Open', NULL, NULL,
   'Training materials drafted; completion tracking not yet enabled. Due 2026-10-15.', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),

  -- TRB-2026-007 conditions (3 total; as of 2026-09-22: all Open)
  ('COND-007-1', 'TRB-2026-007', 1, 'Signed BAA with the recipient before any PHI share or token issuance',
   'A Data Processing Agreement / Business Associate Agreement must be signed with the recipient before any PHI is shared or OAuth tokens are issued.',
   'HIPAA BAA requirement per 45 CFR 164.502(e)',
   'All Phases', 'Legal attestation + BAA counter-signature', 'Open', NULL, NULL,
   'BAA template in compliance volume; awaiting recipient onboarding process.', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),

  ('COND-007-2', 'TRB-2026-007', 2, 'Token lifetime ≤ 30 days; recipient IP access list; quarterly rotation',
   'OAuth bearer tokens must expire within 30 days. Recipient must provide IP access list for token issuance. Quarterly token rotation audit.',
   'NIST 800-53 AC-2(9) account management',
   'GA', 'OAuth token TTL configuration audit + IP whitelist verification', 'Open', NULL, NULL,
   'Token TTL to be configured; IP access list process in design. Due 2026-10-25.', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),

  ('COND-007-3', 'TRB-2026-007', 3, 'Share-access audit logs retained 180 days; monthly anomaly review',
   'All Delta Sharing access events logged and retained for 180 days. Monthly automated anomaly detection (unusual download volume, non-business-hours access).',
   'HIPAA 45 CFR 164.312(b) audit controls',
   'GA', 'Audit log retention audit + anomaly report review', 'Open', NULL, NULL,
   'Audit logs configured; retention policy set to 180 days. Anomaly detection rules TBD. Due 2026-10-25.', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP());

-- Review History: Status transitions and events (following meeting timeline from CANONICAL.md)
INSERT INTO ${catalog}.trb.review_history VALUES
  -- TRB-2026-001: Approved at TRBM-2026-07-14
  ('evt-001-001', 'TRB-2026-001', DATE '2026-07-14', 'status_change', 'Not Reviewed', 'Approved',
   'Chief Privacy Officer', 'Status moved from Not Reviewed to Approved at TRBM-2026-07-14',
   'Standard PHI control; approved at first review.', CURRENT_TIMESTAMP()),

  -- TRB-2026-002: Introduced at TRBM-2026-07-28
  ('evt-002-001', 'TRB-2026-002', DATE '2026-07-28', 'status_change', 'Not Reviewed', 'Under Review',
   'Enterprise Architect', 'Status moved from Not Reviewed to Under Review at TRBM-2026-07-28',
   'Deferred: attribute source of truth and IdP sync design pending.', CURRENT_TIMESTAMP()),
  ('evt-002-002', 'TRB-2026-002', DATE '2026-08-25', 'meeting_presented', NULL, NULL,
   'Enterprise Architect', 'Follow-up presented at TRBM-2026-08-25', 'Still Under Review; attribute design deferred to next cycle.', CURRENT_TIMESTAMP()),

  -- TRB-2026-003: Approved at TRBM-2026-07-14
  ('evt-003-001', 'TRB-2026-003', DATE '2026-07-14', 'status_change', 'Not Reviewed', 'Approved',
   'Platform Engineering Lead', 'Status moved from Not Reviewed to Approved at TRBM-2026-07-14',
   'SQL Server CDC approved for non-PHI only (Public Preview). Re-review at GA.', CURRENT_TIMESTAMP()),

  -- TRB-2026-004: Rejected at TRBM-2026-07-14
  ('evt-004-001', 'TRB-2026-004', DATE '2026-07-14', 'status_change', 'Not Reviewed', 'Rejected',
   'CISO', 'Status moved from Not Reviewed to Rejected at TRBM-2026-07-14',
   'Beta phase; schema evolution and offset tracking insufficient for audit trail. Resubmit at GA.', CURRENT_TIMESTAMP()),

  -- TRB-2026-005: Approved with Conditions at TRBM-2026-07-28
  ('evt-005-001', 'TRB-2026-005', DATE '2026-07-28', 'status_change', 'Under Review', 'Approved with Conditions',
   'Chief Privacy Officer', 'Status moved from Under Review to Approved with Conditions at TRBM-2026-07-28',
   'Genie One approved with 4 audit logging, access control, and training conditions.', CURRENT_TIMESTAMP()),
  ('evt-005-002', 'TRB-2026-005', DATE '2026-09-15', 'condition_added', NULL, NULL,
   'Data Governance Lead', 'Conditions COND-005-1 and COND-005-2 verified and closed', 'Row/column masks tested; query audit logs enabled.', CURRENT_TIMESTAMP()),

  -- TRB-2026-006: Introduced at TRBM-2026-08-11
  ('evt-006-001', 'TRB-2026-006', DATE '2026-08-11', 'status_change', 'Not Reviewed', 'Under Review',
   'CISO', 'Status moved from Not Reviewed to Under Review at TRBM-2026-08-11',
   'Knowledge Assistant Beta introduced. Sandbox pilot under EXC-2026-002.', CURRENT_TIMESTAMP()),
  ('evt-006-002', 'TRB-2026-006', DATE '2026-09-22', 'meeting_presented', NULL, NULL,
   'Chief Privacy Officer', 'Status check at TRBM-2026-09-22', 'Still Under Review. LLM vendor training data audit pending.', CURRENT_TIMESTAMP()),

  -- TRB-2026-007: Approved with Conditions at TRBM-2026-08-25
  ('evt-007-001', 'TRB-2026-007', DATE '2026-08-25', 'status_change', 'Under Review', 'Approved with Conditions',
   'Enterprise Architect', 'Status moved from Under Review to Approved with Conditions at TRBM-2026-08-25',
   'Mode: Databricks-to-Open approved with 3 conditions on BAA, token lifecycle, and audit logs.', CURRENT_TIMESTAMP()),

  -- TRB-2026-008: Introduced at TRBM-2026-08-11
  ('evt-008-001', 'TRB-2026-008', DATE '2026-08-11', 'status_change', 'Not Reviewed', 'Under Review',
   'Platform Engineering Lead', 'Status moved from Not Reviewed to Under Review at TRBM-2026-08-11',
   'Databricks Apps introduced. BI dashboards requested.', CURRENT_TIMESTAMP()),
  ('evt-008-002', 'TRB-2026-008', DATE '2026-08-25', 'meeting_presented', NULL, NULL,
   'Platform Engineering Lead', 'Follow-up at TRBM-2026-08-25', 'Still Under Review. App-auth and egress testing pending.', CURRENT_TIMESTAMP()),
  ('evt-008-003', 'TRB-2026-008', DATE '2026-09-22', 'meeting_presented', NULL, NULL,
   'Platform Engineering Lead', 'Status check at TRBM-2026-09-22', 'Still Under Review.', CURRENT_TIMESTAMP()),

  -- TRB-2026-009: Intake at TRBM-2026-09-22
  ('evt-009-001', 'TRB-2026-009', DATE '2026-09-22', 'status_change', 'Not Reviewed', 'Not Reviewed',
   'Compliance Officer', 'Intake submitted at TRBM-2026-09-22', 'MCP servers GA feature; triage scheduled for next meeting.', CURRENT_TIMESTAMP());

-- Exceptions (exactly 2, per CANONICAL.md)
INSERT INTO ${catalog}.trb.exceptions VALUES
  -- EXC-2026-001: Denied
  ('EXC-2026-001', 'TRB-2026-003', 'PHI-Restriction',
   'Finance requests early PHI ingestion (member name + ID) through SQL Server connector before GA for annual reconciliation.',
   'Annual member reconciliation process needs updated demographics.',
   'Public Preview cannot carry PHI per Databricks compliance policy. Alternatives: (1) use existing GA ingestion path, (2) wait for GA + re-review.',
   'Denied', 'Finance Lead', 'CISO', 'TRBM-2026-09-08', NULL, NULL, NULL,
   CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),

  -- EXC-2026-002: Approved
  ('EXC-2026-002', 'TRB-2026-006', 'Production-Prohibition',
   'Sandbox pilot of Beta Knowledge Assistant using synthetic/non-PHI documents only.',
   'Proof-of-concept for internal documentation search before full deployment.',
   'LLM vendor training data isolation not yet SLA-certified. Hallucination risk mitigated by synthetic-only corpus and quarterly red-team.',
   'Approved', 'Data Science Lead', 'Chief Privacy Officer', 'TRBM-2026-08-11', DATE '2026-08-11', DATE '2026-11-11', DATE '2026-11-01',
   CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP());

-- Documents: Required set per CANONICAL.md
INSERT INTO ${catalog}.trb.documents VALUES
  ('CHARTER-2026', 'charter', 'Acme Health Plan TRB Charter and Governance Framework', DATE '2026-07-01', NULL,
   '/Volumes/platform/trb/corpus/CHARTER-2026.md', array(), CURRENT_TIMESTAMP()),

  ('MIN-TRBM-2026-07-14', 'minutes', 'TRB Meeting Minutes 2026-07-14', DATE '2026-07-14', 'TRBM-2026-07-14',
   '/Volumes/platform/trb/corpus/MIN-TRBM-2026-07-14.md', array('TRB-2026-001', 'TRB-2026-003', 'TRB-2026-004'), CURRENT_TIMESTAMP()),

  ('MIN-TRBM-2026-07-28', 'minutes', 'TRB Meeting Minutes 2026-07-28', DATE '2026-07-28', 'TRBM-2026-07-28',
   '/Volumes/platform/trb/corpus/MIN-TRBM-2026-07-28.md', array('TRB-2026-005', 'TRB-2026-002'), CURRENT_TIMESTAMP()),

  ('MIN-TRBM-2026-08-11', 'minutes', 'TRB Meeting Minutes 2026-08-11', DATE '2026-08-11', 'TRBM-2026-08-11',
   '/Volumes/platform/trb/corpus/MIN-TRBM-2026-08-11.md', array('TRB-2026-006', 'TRB-2026-008'), CURRENT_TIMESTAMP()),

  ('MIN-TRBM-2026-08-25', 'minutes', 'TRB Meeting Minutes 2026-08-25', DATE '2026-08-25', 'TRBM-2026-08-25',
   '/Volumes/platform/trb/corpus/MIN-TRBM-2026-08-25.md', array('TRB-2026-007', 'TRB-2026-002', 'TRB-2026-008'), CURRENT_TIMESTAMP()),

  ('MIN-TRBM-2026-09-08', 'minutes', 'TRB Meeting Minutes 2026-09-08', DATE '2026-09-08', 'TRBM-2026-09-08',
   '/Volumes/platform/trb/corpus/MIN-TRBM-2026-09-08.md', array('TRB-2026-005'), CURRENT_TIMESTAMP()),

  ('MIN-TRBM-2026-09-22', 'minutes', 'TRB Meeting Minutes 2026-09-22', DATE '2026-09-22', 'TRBM-2026-09-22',
   '/Volumes/platform/trb/corpus/MIN-TRBM-2026-09-22.md', array('TRB-2026-009', 'TRB-2026-002', 'TRB-2026-006', 'TRB-2026-008'), CURRENT_TIMESTAMP()),

  ('INT-006', 'intake', 'Knowledge Assistant Intake Form', DATE '2026-08-01', NULL,
   '/Volumes/platform/trb/corpus/INT-006.md', array('TRB-2026-006'), CURRENT_TIMESTAMP()),

  ('INT-009', 'intake', 'MCP Servers Intake Form', DATE '2026-09-22', NULL,
   '/Volumes/platform/trb/corpus/INT-009.md', array('TRB-2026-009'), CURRENT_TIMESTAMP()),

  ('RA-005', 'risk_assessment', 'Genie One Risk Assessment', DATE '2026-07-20', NULL,
   '/Volumes/platform/trb/corpus/RA-005.md', array('TRB-2026-005'), CURRENT_TIMESTAMP()),

  ('RA-007', 'risk_assessment', 'Mode: Databricks-to-Open Risk Assessment', DATE '2026-08-15', NULL,
   '/Volumes/platform/trb/corpus/RA-007.md', array('TRB-2026-007'), CURRENT_TIMESTAMP()),

  ('DR-2026-001', 'decision_record', 'Decision Record: Row filters & column masks', DATE '2026-07-14', NULL,
   '/Volumes/platform/trb/corpus/DR-2026-001.md', array('TRB-2026-001'), CURRENT_TIMESTAMP()),

  ('DR-2026-003', 'decision_record', 'Decision Record: SQL Server (Public Preview, Non-PHI only)', DATE '2026-07-14', NULL,
   '/Volumes/platform/trb/corpus/DR-2026-003.md', array('TRB-2026-003'), CURRENT_TIMESTAMP()),

  ('DR-2026-004', 'decision_record', 'Decision Record: Kafka-compatible APIs (Rejected, Beta phase)', DATE '2026-07-14', NULL,
   '/Volumes/platform/trb/corpus/DR-2026-004.md', array('TRB-2026-004'), CURRENT_TIMESTAMP()),

  ('DR-2026-005', 'decision_record', 'Decision Record: Genie One (Approved with Conditions)', DATE '2026-07-28', NULL,
   '/Volumes/platform/trb/corpus/DR-2026-005.md', array('TRB-2026-005'), CURRENT_TIMESTAMP()),

  ('DR-2026-007', 'decision_record', 'Decision Record: Mode: Databricks-to-Open (Approved with Conditions)', DATE '2026-08-25', NULL,
   '/Volumes/platform/trb/corpus/DR-2026-007.md', array('TRB-2026-007'), CURRENT_TIMESTAMP()),

  ('CAL-2026-005', 'approval_letter', 'Approval Letter: Genie One', DATE '2026-07-28', NULL,
   '/Volumes/platform/trb/corpus/CAL-2026-005.md', array('TRB-2026-005'), CURRENT_TIMESTAMP()),

  ('CAL-2026-007', 'approval_letter', 'Approval Letter: Mode: Databricks-to-Open', DATE '2026-08-25', NULL,
   '/Volumes/platform/trb/corpus/CAL-2026-007.md', array('TRB-2026-007'), CURRENT_TIMESTAMP()),

  ('EXC-2026-001', 'exception', 'Exception Request: SQL Server PHI early access (DENIED)', DATE '2026-09-08', NULL,
   '/Volumes/platform/trb/corpus/EXC-2026-001.md', array('TRB-2026-003'), CURRENT_TIMESTAMP()),

  ('EXC-2026-002', 'exception', 'Exception Request: Knowledge Assistant sandbox pilot (APPROVED)', DATE '2026-08-11', NULL,
   '/Volumes/platform/trb/corpus/EXC-2026-002.md', array('TRB-2026-006'), CURRENT_TIMESTAMP());
