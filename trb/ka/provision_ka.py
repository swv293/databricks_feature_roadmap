"""Create or update the Review Board Knowledge Assistant (Agent Bricks) over the TRB PDFs.

    python3 trb/ka/provision_ka.py --profile P --catalog C [--wait]

Idempotent: finds the KA by display name, creates it if missing, otherwise updates its
description and instructions; ensures the PDF volume is attached as a knowledge source; syncs.
Asset Bundles (CLI v1.20) have no Knowledge Assistant resource, so this script is the
source of truth. Re-run it after re-rendering PDFs (trb/genie/render_pdfs.py) to re-sync.
"""
import argparse
import json
import subprocess
import sys
import time

NAME = "Feature Tracker Review Board Knowledge Assistant"
DESCRIPTION = ("Answers 'why' and 'what does the document say' questions from the full text of Acme Health Plan's "
               "Tech Review Board (TRB, also called the Architecture Review Board) documents on Databricks features: "
               "charter, meeting minutes, intake requests, risk assessments, decision records, conditional approval "
               "letters, and exception requests. Cites the source document. Synthetic data.")
INSTRUCTIONS = """You answer questions about Acme Health Plan's Tech Review Board (TRB; also called the Architecture Review Board, ARB, or review board) using ONLY the TRB documents provided. Acme Health Plan is fictional and all documents are synthetic samples.

Always:
- Cite the document ID (e.g. DR-2026-005, MIN-TRBM-2026-09-08, EXC-2026-001) for every claim. Each PDF has a "Document control" table with its ID, review IDs, feature keys, date and status.
- Name the review ID (TRB-YYYY-NNN) and feature when you answer about a specific review.
- Quote conditions, rationale and risks as the documents state them; do not add requirements that are not in the documents.

The PHI rule: a feature is PHI-eligible only when its Databricks release phase is GA AND the TRB status is Approved. "Approved with Conditions" is not PHI-eligible until every condition is verified closed. Never state that a feature can be used with PHI unless a document says it is Approved for PHI scope.

Documents are point-in-time records. For CURRENT status, counts, or lists across many reviews (e.g. "how many features are PHI-eligible today", "which reviews are pending"), say that the Review Board Genie agent (Feature Tracker Review Board Analytics Space) holds the live register, and answer from the documents only with the date they describe.

If the documents do not contain the answer, say so plainly and do not guess. Do not answer questions about members, claims, providers or other PHI, Databricks pricing, or non-Databricks products: say they are out of scope for this assistant."""


def cli(profile, *args, check=True):
    r = subprocess.run(["databricks", *args, "--profile", profile, "-o", "json"], capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.exit(f"databricks {' '.join(args[:2])} failed: {r.stderr.strip()[:600]}")
    return json.loads(r.stdout) if r.stdout.strip() else {}


def as_list(d, key):
    return d if isinstance(d, list) else d.get(key, []) or []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True)
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--wait", action="store_true", help="poll until the KA reports a ready state")
    a = ap.parse_args()
    path = f"/Volumes/{a.catalog}/trb/corpus_pdf/"

    kas = as_list(cli(a.profile, "knowledge-assistants", "list-knowledge-assistants"), "knowledge_assistants")
    ka = next((k for k in kas if k.get("display_name") == NAME), None)
    if ka is None:
        ka = cli(a.profile, "knowledge-assistants", "create-knowledge-assistant", NAME, DESCRIPTION,
                 "--instructions", INSTRUCTIONS)
        print(f"created {ka['name']}")
    else:
        ka = cli(a.profile, "knowledge-assistants", "update-knowledge-assistant", ka["name"],
                 "display_name,description,instructions", NAME, DESCRIPTION, "--instructions", INSTRUCTIONS)
        print(f"updated {ka['name']}")
    name = ka["name"]

    sources = as_list(cli(a.profile, "knowledge-assistants", "list-knowledge-sources", name), "knowledge_sources")
    if not any((s.get("files") or {}).get("path", "").rstrip("/") == path.rstrip("/") for s in sources):
        src = cli(a.profile, "knowledge-assistants", "create-knowledge-source", name, "--json", json.dumps({
            "display_name": "TRB documents (PDF)",
            "description": "74 synthetic TRB documents: charter, minutes, intake requests, risk assessments, decision records, approval letters, exceptions.",
            "source_type": "files", "files": {"path": path}}))
        print(f"attached source {src.get('name', path)}")
    else:
        print(f"source already attached: {path}")

    cli(a.profile, "knowledge-assistants", "sync-knowledge-sources", name)
    print("sync started")
    while a.wait:
        cur = cli(a.profile, "knowledge-assistants", "get-knowledge-assistant", name)
        state = cur.get("state") or cur.get("status") or cur.get("endpoint_status")
        print(f"  state={state} endpoint={cur.get('endpoint_name')}")
        if str(state).upper() in ("ONLINE", "ACTIVE", "READY"):
            break
        time.sleep(30)
    print(json.dumps({k: v for k, v in cli(a.profile, "knowledge-assistants", "get-knowledge-assistant", name).items()
                      if k in ("name", "id", "display_name", "endpoint_name", "state", "status")}, indent=1))


if __name__ == "__main__":
    main()
