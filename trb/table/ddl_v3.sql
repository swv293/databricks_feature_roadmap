-- TRB register v3: drop always-empty columns from control_mappings (Genie hallucination trap,
-- flagged by the genie-anti-hallucination profiler). Requires column mapping. Run once.
ALTER TABLE ${catalog}.trb.control_mappings SET TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name', 'delta.minReaderVersion' = '2', 'delta.minWriterVersion' = '5');
ALTER TABLE ${catalog}.trb.control_mappings DROP COLUMNS (evidence_description, evidence_url, notes);
