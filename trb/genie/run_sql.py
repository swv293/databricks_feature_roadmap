"""Run a .sql file statement by statement on a SQL warehouse.

    python3 trb/genie/run_sql.py --profile P --warehouse-id W --catalog C file.sql [--skip-pattern REGEX]

Splits on semicolons outside quotes and comments, substitutes ${catalog}, and stops
at the first failing statement. Uses the Statement Execution API via the CLI.
"""
import argparse
import json
import re
import subprocess
import sys


def split_sql(text):
    out, buf, i, q = [], [], 0, None
    while i < len(text):
        c = text[i]
        if q:
            buf.append(c)
            if c == q:
                if i + 1 < len(text) and text[i + 1] == q:  # doubled quote escape
                    buf.append(text[i + 1]); i += 1
                else:
                    q = None
            elif c == "\\" and i + 1 < len(text):
                buf.append(text[i + 1]); i += 1
        elif c in ("'", '"', "`"):
            q = c; buf.append(c)
        elif text.startswith("--", i):
            j = text.find("\n", i)
            i = len(text) if j < 0 else j
            continue
        elif c == ";":
            s = "".join(buf).strip()
            if s:
                out.append(s)
            buf = []
        else:
            buf.append(c)
        i += 1
    s = "".join(buf).strip()
    if s:
        out.append(s)
    return out


def run(profile, warehouse, stmt):
    body = {"warehouse_id": warehouse, "statement": stmt, "wait_timeout": "50s", "on_wait_timeout": "CONTINUE"}
    r = json.loads(subprocess.check_output(
        ["databricks", "api", "post", "/api/2.0/sql/statements", "--profile", profile, "--json", json.dumps(body)], text=True))
    while r["status"]["state"] in ("PENDING", "RUNNING"):
        r = json.loads(subprocess.check_output(
            ["databricks", "api", "get", f"/api/2.0/sql/statements/{r['statement_id']}", "--profile", profile], text=True))
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True)
    ap.add_argument("--warehouse-id", required=True)
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--skip-pattern", help="skip statements matching this regex")
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    for f in a.files:
        stmts = split_sql(open(f).read().replace("${catalog}", a.catalog))
        for n, s in enumerate(stmts, 1):
            head = " ".join(s.split())[:90]
            if a.skip_pattern and re.search(a.skip_pattern, s, re.I | re.S):
                print(f"[{f} {n}/{len(stmts)}] SKIP  {head}")
                continue
            r = run(a.profile, a.warehouse_id, s)
            st = r["status"]["state"]
            print(f"[{f} {n}/{len(stmts)}] {st:<9} {head}")
            if st != "SUCCEEDED":
                print("   ", r["status"].get("error", {}).get("message", "")[:800])
                sys.exit(1)


if __name__ == "__main__":
    main()
