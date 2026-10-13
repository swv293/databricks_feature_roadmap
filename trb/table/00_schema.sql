CREATE SCHEMA IF NOT EXISTS ${catalog}.trb
  COMMENT 'Tech Review Board (also called the Architecture Review Board, ARB) register: reviews of Databricks features, approval conditions, exceptions, control mappings, and governance documents. Human-curated; synthetic sample data for Acme Health Plan.';
CREATE VOLUME IF NOT EXISTS ${catalog}.trb.corpus
  COMMENT 'TRB/ARB governance documents (markdown): charter, minutes, intake requests, risk assessments, decision records, approval letters, exceptions. Source corpus for the Knowledge Assistant.';
