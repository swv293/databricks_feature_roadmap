"""Bundle task: create the TRB register in a catalog from the repo's SQL and documents.

Runs on serverless. Order: schema/volume -> tables -> canonical sample data -> v2/v3
migrations -> extended data -> Genie views -> copy documents into the corpus volume.

Safety: refuses to run if <catalog>.trb.reviews already holds rows (pass
--allow-existing to rerun only the idempotent steps: views and documents).
extended_data.sql is generated per catalog: regenerate it with
trb/genie/generate_extended.py --catalog <catalog> before deploying to a new catalog.
"""
import argparse
import pathlib
import re
import shutil
import sys

from pyspark.sql import SparkSession

ap = argparse.ArgumentParser()
ap.add_argument("--bundle-root", required=True)
ap.add_argument("--catalog", required=True)
ap.add_argument("--allow-existing", default="false")
a = ap.parse_args()
root = pathlib.Path(a.bundle_root)
sys.path.insert(0, str(root / "trb" / "genie"))
from run_sql import split_sql  # noqa: E402

s = SparkSession.builder.getOrCreate()
T = root / "trb" / "table"


def run(name):
    text = (T / name).read_text().replace("${catalog}", a.catalog)
    if name == "extended_data.sql" and f"{a.catalog}.trb." not in text:
        sys.exit(f"extended_data.sql was generated for another catalog; regenerate it for {a.catalog}")
    stmts = split_sql(text)
    for n, stmt in enumerate(stmts, 1):
        s.sql(stmt)
    print(f"{name}: {len(stmts)} statements")


s.sql(f"CREATE SCHEMA IF NOT EXISTS {a.catalog}.trb")
exists = s.catalog.tableExists(f"{a.catalog}.trb.reviews") and \
    s.sql(f"SELECT 1 FROM {a.catalog}.trb.reviews LIMIT 1").count() > 0
if exists and a.allow_existing != "true":
    sys.exit(f"{a.catalog}.trb.reviews already has rows; refusing to reload. "
             "Use --allow-existing true to refresh only views and documents.")

steps = ["00_schema.sql", "genie_views.sql"] if exists else \
    ["00_schema.sql", "ddl.sql", "sample_data.sql", "ddl_v2.sql", "ddl_v3.sql", "ddl_v4.sql", "extended_data.sql", "genie_views.sql"]
for f in steps:
    run(f)

src = root / "trb" / "docs" / "samples"
dst = pathlib.Path(f"/Volumes/{a.catalog}/trb/corpus")
n = 0
for p in sorted(src.glob("*.md")):
    shutil.copy(p, dst / p.name)
    n += 1
print(f"copied {n} documents to {dst}")
pdf_src, pdf_dst = root / "trb" / "docs" / "pdf", pathlib.Path(f"/Volumes/{a.catalog}/trb/corpus_pdf")
pdfs = sorted(pdf_src.glob("*.pdf"))
for p in pdfs:
    shutil.copy(p, pdf_dst / p.name)
print(f"copied {len(pdfs)} PDFs to {pdf_dst}")
if len(pdfs) != n:
    sys.exit("PDF count differs from markdown count; run trb/genie/render_pdfs.py")
# Guard against documents and index drifting apart.
indexed = s.sql(f"SELECT count(*) c FROM {a.catalog}.trb.documents").first().c
print(f"documents indexed: {indexed}; files: {n}")
if indexed != n:
    sys.exit("documents table and corpus files disagree; regenerate extended_data.sql")
