"""Bundle task: re-post the Review Board agent's benchmarks.

Every update of a Genie agent's serialized_space (including `bundle deploy` of the
genie_spaces resource) silently deletes its BENCHMARK rows. Run this after every deploy:
    databricks bundle run review_board_genie_maintenance -t <target>
Writes go through the data-rooms API surface. Same logic as the workspace
genie-benchmarks-eval/scripts/sync_benchmarks.py, using the SDK's auth instead of the CLI.
"""
import argparse
import json
import pathlib

from databricks.sdk import WorkspaceClient

ap = argparse.ArgumentParser()
ap.add_argument("--bundle-root", required=True)
ap.add_argument("--space-id", required=True)
a = ap.parse_args()

w = WorkspaceClient()
base = f"/api/2.0/data-rooms/{a.space_id}/curated-questions"
bench = json.loads((pathlib.Path(a.bundle_root) / "trb" / "genie" / "benchmarks_sync.json").read_text())


def benchmarks():
    """All BENCHMARK rows. The list is paginated (20 per page, next_page_token);
    reading only the first page undercounts and leaves duplicates behind."""
    rows, token = [], None
    while True:
        r = w.api_client.do("GET", base, query={"page_token": token} if token else None) or {}
        rows += r.get("curated_questions", r.get("questions", [])) or []
        token = r.get("next_page_token")
        if not token:
            break
    kind = lambda q: q.get("question_type") or q.get("curated_question", {}).get("question_type")
    return [q for q in rows if kind(q) == "BENCHMARK"]


old = benchmarks()
for q in old:
    qid = q.get("id") or q.get("curated_question", {}).get("id")
    if qid:
        w.api_client.do("DELETE", f"{base}/{qid}")
for b in bench:
    w.api_client.do("POST", base, body={"curated_question": {
        "question_text": b["question_text"], "answer_text": b["answer_text"], "question_type": "BENCHMARK"}})
after = benchmarks()
print(f"deleted {len(old)}, posted {len(bench)}, now {len(after)} benchmarks on space {a.space_id}")
if len(after) != len(bench):
    raise RuntimeError("benchmark count mismatch after sync")
