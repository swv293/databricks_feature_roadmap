"""Monthly task: read each feature's Databricks doc page and propose limitation and doc-link updates.

Each unique doc page (and up to two dedicated limitations pages it links to) is fetched once.
The LLM is asked per feature, and only when the evidence text changed since the last check.
Decisions come from docs.decide_*(): empty limitations are filled (AUTO), replacing curated
text is HELD, a moved page updates the link (AUTO), a dead link is HELD. Writes doc_checks
and doc_proposals; apply_doc_changes writes features.

Serverless needs outbound HTTPS to docs.databricks.com (same as ingest_feed)."""
import sys
sys.path.insert(0, sys.argv[sys.argv.index("--src") + 1])

import datetime as dt  # noqa: E402
import hashlib  # noqa: E402
import time  # noqa: E402
import urllib.error  # noqa: E402
import urllib.request  # noqa: E402

from feature_tracker import docs  # noqa: E402
from feature_tracker.common import args, spark  # noqa: E402

a = args({"--use-llm": {"default": "true"}, "--llm-endpoint": {"required": True}})
s = spark()
UA = {"User-Agent": "databricks-feature-tracker/1.0 (monthly docs check)"}

features = [r.asDict() for r in s.sql(f"""
    SELECT f.feature_key, f.name, f.doc_link, f.limitations, p.name AS parent
    FROM {a.fq}.features f LEFT JOIN {a.fq}.features p ON p.feature_id = f.parent_id
    WHERE f.doc_link LIKE 'https://{docs.DOCS_HOST}/%'""").collect()]
prev = {r.feature_key: r for r in s.sql(f"""
    SELECT feature_key, content_hash, llm_limitations, llm_confidence FROM {a.fq}.doc_checks
    WHERE llm_confidence IS NOT NULL
    QUALIFY row_number() OVER (PARTITION BY feature_key ORDER BY checked_at DESC) = 1""").collect()}
# A value a person already held, rejected, or accepted is not proposed again.
seen = {(r.feature_key, r.field, r.new_value) for r in s.sql(f"""
    SELECT feature_key, field, new_value FROM {a.fq}.doc_proposals
    WHERE decision IN ('HELD', 'REJECTED', 'ACCEPTED')""").collect()}

pages = {}


def fetch(url):
    """(status, final_url, text, links), cached per URL. Never raises."""
    if url in pages:
        return pages[url]
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
            text, links = docs.page_text(r.read().decode("utf-8", "replace"))
            pages[url] = (r.status, r.geturl(), text, links)
    except urllib.error.HTTPError as e:
        pages[url] = (e.code, url, "", [])
    except Exception as e:  # DNS, timeout, egress blocked
        print(f"fetch failed {url}: {type(e).__name__}: {e}")
        pages[url] = (None, url, "", [])
    time.sleep(0.3)  # be polite to the docs site
    return pages[url]


now = dt.datetime.now(dt.timezone.utc)
checks, prompts = {}, []
for f in features:
    status, final_url, text, links = fetch(f["doc_link"])
    lurls = docs.limits_links(links, final_url) if text else []
    ev = docs.evidence(text, [fetch(u)[2] for u in lurls]) if text else ""
    h = docs.content_hash(f"{f['name']}|{ev}") if ev else None
    c = {"run_id": a.run_id, "checked_at": now, "feature_key": f["feature_key"], "doc_link": f["doc_link"],
         "http_status": status, "final_url": final_url, "limits_urls": lurls, "content_hash": h,
         "llm_limitations": None, "llm_confidence": None,
         "error": None if text else f"no page text (HTTP {status})"}
    p = prev.get(f["feature_key"])
    if h and p and p.content_hash == h:     # unchanged evidence: reuse last month's answer
        c["llm_limitations"], c["llm_confidence"] = p.llm_limitations, p.llm_confidence
    elif h:
        prompts.append({"feature_key": f["feature_key"], "prompt": docs.prompt(
            f["name"], f["parent"], f["limitations"], final_url, ev)})
    checks[f["feature_key"]] = c
print(f"{len(pages)} pages fetched for {len(features)} features; {len(prompts)} need the LLM")

if a.use_llm == "true" and prompts:
    s.createDataFrame(prompts).createOrReplaceTempView("doc_prompts")
    try:
        out = s.sql(f"""SELECT feature_key, ai_query('{a.llm_endpoint}', prompt, failOnError => false) AS r
                        FROM doc_prompts""").collect()
    except Exception as e:  # endpoint missing or not enabled for batch: record the checks only
        print(f"LLM unavailable ({type(e).__name__}: {str(e)[:300]}); link checks only")
        out = []
    for row in out:
        c = checks[row.feature_key]
        try:
            c["llm_limitations"], c["llm_confidence"] = docs.parse_answer(row.r.result or "")
        except Exception as e:
            c["error"] = f"llm answer unusable: {str(e)[:200]}"

by_key = {f["feature_key"]: f for f in features}
proposals = []


def propose(key, field, old, new, url, conf, decision, reason):
    if (key, field, new) in seen:
        return
    proposals.append({
        "proposal_id": hashlib.sha1(f"{a.run_id}|{key}|{field}".encode()).hexdigest()[:16],
        "run_id": a.run_id, "feature_key": key, "field": field, "old_value": old, "new_value": new,
        "evidence_url": url, "confidence": conf, "decision": decision, "reason": reason,
        "decided_by": None, "created_at": now, "applied_at": None})


for key, c in checks.items():
    f = by_key[key]
    link = docs.decide_link(f["doc_link"], c["http_status"], c["final_url"])
    if link:
        propose(key, link[0], f["doc_link"], link[1], f["doc_link"], None, link[2], link[3])
    if c["llm_confidence"] is not None:
        text = docs.clean(c["llm_limitations"])
        lim = docs.decide_limitations(f["limitations"], text, c["llm_confidence"])
        if lim:
            propose(key, "limitations", f["limitations"] or "", text, c["final_url"], c["llm_confidence"], *lim)

target = s.table(f"{a.fq}.doc_checks")
s.createDataFrame(list(checks.values()), schema=target.schema).write.mode("append").saveAsTable(f"{a.fq}.doc_checks")
if proposals:
    target = s.table(f"{a.fq}.doc_proposals")
    s.createDataFrame(proposals, schema=target.schema).createOrReplaceTempView("new_doc_proposals")
    s.sql(f"""MERGE INTO {a.fq}.doc_proposals t USING new_doc_proposals n ON t.proposal_id = n.proposal_id
              WHEN NOT MATCHED THEN INSERT *""")
auto = sum(p["decision"] == "AUTO" for p in proposals)
print(f"{len(proposals)} doc proposals ({auto} auto, {len(proposals) - auto} held)")
