-- TRB register v2: columns the Genie agent needs to answer "why" and "when" questions.
-- Run once after ddl.sql (ADD COLUMNS is not idempotent).

ALTER TABLE ${catalog}.trb.reviews ADD COLUMNS (
  decision_rationale STRING COMMENT 'Why the TRB decided as it did. For Under Review: what is still open and what the TRB asked the requester for',
  open_questions STRING COMMENT 'Unresolved questions the TRB raised, separated by "; ". Empty when nothing is open'
);

ALTER TABLE ${catalog}.trb.approval_conditions ADD COLUMNS (
  due_date DATE COMMENT 'Date the condition must be verified by. NULL means ongoing (recurring) or per engagement'
);

ALTER TABLE ${catalog}.trb.documents ADD COLUMNS (
  summary STRING COMMENT 'Two-to-three sentence summary of the document: what it covers and what it decided. Full text is in volume_path'
);
