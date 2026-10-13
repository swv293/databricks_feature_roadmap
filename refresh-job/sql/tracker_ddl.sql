-- Databricks Feature Tracker: tables owned by the weekly refresh job.
-- Target: ${catalog}.${schema} (default platform.feature_tracker). TRB tables live in
-- ${catalog}.trb and are human-curated (see trb/table/ddl.sql). This job never writes them.
-- Statements are separated by ";\n" so ensure_tables.py can run them one at a time.

CREATE SCHEMA IF NOT EXISTS ${catalog}.${schema}
  COMMENT 'Databricks Feature Tracker: Databricks release phase (Axis A) per feature, maintained weekly from the release-notes feed';

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.features (
  feature_key      STRING  NOT NULL COMMENT 'Stable key: "<name>@<domain>". Joins to trb.reviews.feature_key',
  feature_id       STRING  NOT NULL COMMENT 'Short id used for parent/child links (seed ids like "uc", or generated)',
  name             STRING  NOT NULL COMMENT 'Feature name as shown on the tracker',
  domain           STRING  NOT NULL COMMENT 'One of the 11 tracker domains, e.g. "Ingestion", "SQL & BI Analytics"',
  parent_id        STRING           COMMENT 'feature_id of the parent feature; NULL for top-level features',
  dbx_phase        STRING  NOT NULL COMMENT 'Databricks release phase: Upcoming, Private Preview, Beta, Public Preview, GA, Deprecated',
  expected         STRING           COMMENT 'Expected date or window for Upcoming features, e.g. "Nov 18 2026"',
  doc_link         STRING           COMMENT 'docs.databricks.com page for the feature',
  blurb            STRING           COMMENT 'Plain-language, healthcare-payer-specific description (curated)',
  use_cases        ARRAY<STRING>    COMMENT 'Payer use cases this feature supports (curated)',
  priority         STRING           COMMENT 'TRB review priority: High, Medium, Low (curated)',
  limitations      STRING           COMMENT 'Known limitations (curated)',
  objections       STRING           COMMENT 'Open objections summary (curated)',
  seed_trb_status  STRING           COMMENT 'TRB status from the original seed. Used only when trb.reviews has no row for the feature',
  phase_source     STRING  NOT NULL COMMENT 'Where dbx_phase came from: seed, feed, manual',
  phase_evidence   STRING           COMMENT 'Release-note URL that set or confirmed dbx_phase',
  is_new           BOOLEAN NOT NULL COMMENT 'True for features the job inserted that nobody has curated yet',
  first_seen       DATE    NOT NULL COMMENT 'Date the feature entered the tracker',
  last_verified    DATE    NOT NULL COMMENT 'Last date the phase was confirmed by seed, feed, or a person',
  updated_at       TIMESTAMP NOT NULL,
  CONSTRAINT pk_features PRIMARY KEY (feature_key)
) COMMENT 'One row per tracked Databricks feature or sub-feature. Axis A (Databricks phase) is job-maintained; blurb, use_cases, priority, limitations, and objections are curated'
TBLPROPERTIES (delta.enableChangeDataFeed = true);

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.feed_items (
  guid             STRING  NOT NULL COMMENT 'RSS guid (release-note URL with anchor)',
  title            STRING  NOT NULL,
  link             STRING,
  pub_date         DATE    NOT NULL,
  description      STRING           COMMENT 'Description text with HTML stripped',
  categories       ARRAY<STRING>,
  first_seen_run   BIGINT  NOT NULL COMMENT 'Job run_id that first ingested the item',
  ingested_at      TIMESTAMP NOT NULL,
  CONSTRAINT pk_feed_items PRIMARY KEY (guid)
) COMMENT 'Raw Databricks release-notes RSS items, deduplicated, append-only';

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.proposed_changes (
  change_id        STRING  NOT NULL COMMENT 'run_id + guid hash',
  run_id           BIGINT  NOT NULL,
  guid             STRING  NOT NULL COMMENT 'FK to feed_items.guid',
  change_type      STRING  NOT NULL COMMENT 'NEW_FEATURE, NEW_CHILD, PHASE_CHANGE, CONFIRM',
  feature_key      STRING           COMMENT 'Matched feature (PHASE_CHANGE/CONFIRM) or parent (NEW_CHILD)',
  new_feature_name STRING           COMMENT 'Name for NEW_FEATURE / NEW_CHILD rows',
  domain           STRING,
  old_phase        STRING,
  new_phase        STRING  NOT NULL,
  match_method     STRING  NOT NULL COMMENT 'name, category, llm',
  confidence       DOUBLE  NOT NULL,
  decision         STRING  NOT NULL COMMENT 'AUTO or HELD (set by the job); ACCEPTED or REJECTED (set by a person on HELD rows); APPLIED once written',
  reason           STRING  NOT NULL COMMENT 'Why the job chose this decision',
  decided_by       STRING           COMMENT 'User who accepted or rejected a HELD row',
  created_at       TIMESTAMP NOT NULL,
  applied_at       TIMESTAMP,
  CONSTRAINT pk_proposed_changes PRIMARY KEY (change_id)
) COMMENT 'Weekly triage queue. To accept a held change: UPDATE ... SET decision = ''ACCEPTED'', decided_by = current_user(). The next run applies it';

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.posture_snapshots (
  run_id           BIGINT  NOT NULL,
  captured_at      TIMESTAMP NOT NULL,
  setting          STRING  NOT NULL COMMENT 'Workspace setting name, e.g. compliance_security_profile',
  value_json       STRING           COMMENT 'Setting payload as JSON',
  error            STRING           COMMENT 'Set when the read failed (e.g. permission denied)'
) COMMENT 'Workspace security posture read through the settings API on each run';

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.refresh_runs (
  run_id           BIGINT  NOT NULL,
  started_at       TIMESTAMP NOT NULL,
  new_feed_items   INT,
  auto_applied     INT,
  held             INT,
  published_path   STRING,
  CONSTRAINT pk_refresh_runs PRIMARY KEY (run_id)
) COMMENT 'One row per weekly run, for the "last refreshed" stamp and audit';

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.doc_checks (
  run_id           BIGINT  NOT NULL COMMENT 'Monthly docs-check job run',
  checked_at       TIMESTAMP NOT NULL,
  feature_key      STRING  NOT NULL,
  doc_link         STRING  NOT NULL COMMENT 'Link as stored on features at check time',
  http_status      INT              COMMENT 'NULL when the request failed outright',
  final_url        STRING           COMMENT 'URL after redirects',
  limits_urls      ARRAY<STRING>    COMMENT 'Dedicated limitations pages linked from the doc page, also read',
  content_hash     STRING           COMMENT 'Hash of the evidence text; the LLM is asked again only when it changes',
  llm_limitations  STRING           COMMENT 'What the LLM extracted for this feature (empty = nothing specific)',
  llm_confidence   DOUBLE,
  error            STRING
) COMMENT 'Monthly read of each feature''s Databricks doc page, one row per feature per run';

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.doc_proposals (
  proposal_id      STRING  NOT NULL COMMENT 'run_id + feature_key + field hash',
  run_id           BIGINT  NOT NULL,
  feature_key      STRING  NOT NULL,
  field            STRING  NOT NULL COMMENT 'limitations or doc_link',
  old_value        STRING,
  new_value        STRING           COMMENT 'Empty for a dead doc link (a person must find the new page)',
  evidence_url     STRING  NOT NULL COMMENT 'Doc page the proposal came from',
  confidence       DOUBLE,
  decision         STRING  NOT NULL COMMENT 'AUTO or HELD (set by the job); ACCEPTED or REJECTED (set by a person on HELD rows); APPLIED once written; SUPERSEDED when a newer proposal for the same field was applied',
  reason           STRING  NOT NULL,
  decided_by       STRING,
  created_at       TIMESTAMP NOT NULL,
  applied_at       TIMESTAMP,
  CONSTRAINT pk_doc_proposals PRIMARY KEY (proposal_id)
) COMMENT 'Monthly docs-check queue. Empty limitations are filled automatically; replacing curated text is HELD. To accept: UPDATE ... SET decision = ''ACCEPTED'', decided_by = current_user()';

CREATE VOLUME IF NOT EXISTS ${catalog}.${schema}.site
  COMMENT 'Published tracker pages: index.html (latest) and archive/index-YYYY-MM-DD.html'
