"""Ask the Review Board Knowledge Assistant each eval question and check the answer.

    python3 trb/ka/eval_ka.py --profile P --endpoint ka-<id>-endpoint [--gate 0.8]

A question passes when the answer contains at least one expected fact (case-insensitive) and,
when expect_doc is set, cites at least one of those document IDs anywhere in the answer text.
The KA serving endpoint speaks the OpenAI-style responses format. Citations arrive as url_citation
annotations whose URL holds the PDF file name (DOC-ID.pdf), so the whole payload is searched.
"""
import argparse
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent


def ask(profile, endpoint, q):
    body = {"input": [{"role": "user", "content": q}]}
    # REST invocations, not `serving-endpoints query`: the CLI query command drops the `input` field.
    r = subprocess.run(["databricks", "api", "post", f"/serving-endpoints/{endpoint}/invocations",
                        "--json", json.dumps(body), "--profile", profile], capture_output=True, text=True)
    if r.returncode != 0:
        return f"ERROR: {r.stderr.strip()[:300]}"
    return json.dumps(json.loads(r.stdout))  # search the whole payload: text + citations


def text_of(raw):
    try:
        d = json.loads(raw)
    except ValueError:
        return raw
    out = []
    for item in d.get("output") or []:
        for c in item.get("content") or []:
            if c.get("text"):
                out.append(c["text"])
    return "\n".join(out) or raw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True)
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--gate", type=float, default=0.8)
    a = ap.parse_args()
    qs = json.loads((HERE / "eval_questions.json").read_text())
    passed = 0
    for i, q in enumerate(qs, 1):
        raw = ask(a.profile, a.endpoint, q["question"])
        low = raw.lower()
        fact = any(f.lower() in low for f in q["expect_any"])
        cited = not q["expect_doc"] or any(d.lower() in low for d in q["expect_doc"])
        ok = fact and cited and not raw.startswith("ERROR")
        passed += ok
        print(f"[{'PASS' if ok else 'FAIL'}] {i:>2}. {q['question'][:70]:<70} fact={fact} cited={cited}")
        if not ok:
            print("      answer:", " ".join(text_of(raw).split())[:400])
    rate = passed / len(qs)
    print(f"Pass rate: {passed}/{len(qs)} = {rate:.0%} (gate {a.gate:.0%})")
    sys.exit(0 if rate >= a.gate else 1)


if __name__ == "__main__":
    main()
