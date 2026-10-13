-- TRB register v4: PDF corpus for the Knowledge Assistant. Run once.
CREATE VOLUME IF NOT EXISTS ${catalog}.trb.corpus_pdf
  COMMENT 'TRB/ARB governance documents rendered as PDF (one per document in trb.corpus). Knowledge source for the Review Board Knowledge Assistant.';
ALTER TABLE ${catalog}.trb.documents ADD COLUMNS (
  pdf_path STRING COMMENT 'PDF rendering of the document in the corpus_pdf volume; the file the Review Board Knowledge Assistant cites'
);
