"""Render the TRB sample documents (markdown) to Databricks-branded PDFs for the Knowledge Assistant.

    python3 trb/genie/render_pdfs.py [--only DOC_ID ...]

Front-matter becomes a "Document control" table under the title, so document IDs, review IDs,
feature keys and dates are in the PDF text (KA retrieval and citations depend on them).
Uses the fe-specialized-agents markdown-to-pdf skill (WeasyPrint <67, offline: 67+ removed default_url_fetcher, which the script imports). Output: trb/docs/pdf/.

OPTIONAL: the 74 PDFs are committed and name no catalog, so you only need this after editing a document.
The converter is a Databricks-internal Claude Code plugin. Without it, point MARKDOWN_TO_PDF at any script
that takes --input <md> --output <pdf>.
"""
import argparse
import glob
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "trb" / "docs" / "samples"
OUT = ROOT / "trb" / "docs" / "pdf"
SCRIPT = os.environ.get("MARKDOWN_TO_PDF") or (sorted(glob.glob(os.path.expanduser(
    "~/.claude/plugins/cache/fe-vibe/fe-specialized-agents/*/skills/markdown-to-pdf/resources/markdown_to_pdf.py"))) or [None])[-1]


def split_front_matter(text):
    _, fm, body = text.split("---", 2)
    meta = {}
    for line in fm.splitlines():
        m = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if m:
            k, v = m.groups()
            v = v.strip()
            meta[k] = json.loads(v) if v.startswith("[") else (None if v == "null" else v.strip('"'))
    return meta, body.lstrip("\n")


def control_table(meta):
    rows = [("Document ID", meta.get("doc_id")), ("Document type", meta.get("doc_type")),
            ("Date", meta.get("date")), ("Status", meta.get("status")), ("Meeting", meta.get("meeting_id")),
            ("Review IDs", ", ".join(meta.get("review_ids") or []) or None),
            ("Feature keys", "; ".join(meta.get("feature_keys") or []) or None),
            ("Classification", meta.get("classification"))]
    return ("| Document control | |\n|---|---|\n" + "\n".join(f"| {k} | {v} |" for k, v in rows if v) + "\n")


def preprocess(text):
    meta, body = split_front_matter(text)
    lines = body.splitlines()
    i = next((n for n, l in enumerate(lines) if l.startswith("# ")), -1)
    table = control_table(meta)
    banner = "\n> Acme Health Plan is fictional. This is a synthetic sample document for the Databricks Feature Tracker.\n"
    if i >= 0:
        out = lines[:i + 1] + ["", table, banner] + lines[i + 1:]
    else:
        out = [f"# {meta.get('doc_id')}", "", table, banner] + lines
    return meta, "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    if not SCRIPT:
        sys.exit("No markdown-to-PDF converter found. The committed PDFs in trb/docs/pdf/ are current; to re-render, "
                 "set MARKDOWN_TO_PDF to a script that takes --input <md> --output <pdf>.")
    OUT.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "DYLD_FALLBACK_LIBRARY_PATH": "/opt/homebrew/lib"}
    files = sorted(SRC.glob("*.md"))
    if a.only:
        files = [f for f in files if f.stem in a.only]
    fails = []
    with tempfile.TemporaryDirectory() as tmp:
        for f in files:
            meta, md = preprocess(f.read_text())
            src = pathlib.Path(tmp) / f.name
            src.write_text(md)
            dst = OUT / f"{f.stem}.pdf"
            r = subprocess.run(["uvx", "--with", "weasyprint<67", "--with", "markdown", "--with", "pygments",
                                "python", "-I", SCRIPT, "--input", str(src), "--output", str(dst)],
                               capture_output=True, text=True, env=env)
            if r.returncode != 0 or not dst.exists():
                fails.append((f.stem, (r.stderr or r.stdout)[-400:]))
    print(f"rendered {len(files) - len(fails)}/{len(files)} PDFs to {OUT}")
    for stem, err in fails:
        print(f"FAILED {stem}: {err}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
