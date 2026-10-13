"""Task 3: turn unprocessed post-baseline feed items into rows in proposed_changes.

Deterministic first (feature name in the title, then feed category = feature). With
--use-llm, ai_query then judges every phase-bearing item against that domain's
features and its answer replaces the deterministic one only if it names a real
feature_key (or none) and parses cleanly. All decisions go through rules.decide()."""
import sys
sys.path.insert(0, sys.argv[sys.argv.index("--src") + 1])

import datetime as dt  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402

from feature_tracker import feed, rules  # noqa: E402
from feature_tracker.common import args, spark, trb_status_by_key  # noqa: E402

a = args({"--use-llm": {"default": "true"}, "--llm-endpoint": {"required": True},
          # Items published on or before the seed's verification date are already reflected
          # in the seed. Without this, a first run would treat the whole feed history as new.
          "--baseline-date": {"required": True}})
s = spark()

features = [r.asDict() for r in s.sql(
    f"SELECT feature_key, name, domain, parent_id AS parent, dbx_phase AS dbxPhase FROM {a.fq}.features").collect()]
by_key = {f["feature_key"]: f for f in features}
trb = trb_status_by_key(s, a)
# Every post-baseline item without a proposal yet, not just this run's new items, so a
# failed run is retried next time. Items without a phase never get a proposal and are
# re-checked cheaply (no LLM call); the 60-day window bounds that.
items = [r.asDict() for r in s.sql(f"""
    SELECT i.* FROM {a.fq}.feed_items i
    LEFT ANTI JOIN {a.fq}.proposed_changes c ON c.guid = i.guid
    WHERE i.pub_date > DATE'{dt.date.fromisoformat(a.baseline_date)}'
      AND i.pub_date >= date_sub(current_date(), 60)""").collect()]

proposals = {}
for i in items:
    if feed.is_noise(i["title"]):
        continue
    phase = feed.detect_phase(i["title"], i["description"], i["categories"])
    if not phase:
        continue
    domain = feed.map_domain(i["categories"])
    key, coverage = rules.name_match(i["title"], features, domain)
    method, relation = "name", rules.relation_from_coverage(coverage) if key else None
    if not key:
        key = rules.category_parent(i["categories"], features)
        method, relation = ("category", "child") if key else ("name", None)
    proposals[i["guid"]] = dict(item=i, phase=phase, domain=domain, key=key, method=method,
                                relation=relation, confidence=1.0,
                                name=feed.feature_name_from_title(i["title"]))

PROMPT = """You maintain a catalog of Databricks platform features.
Release note:
  title: {title}
  categories: {cats}
  text: {desc}
Candidate catalog features (feature_key | phase):
{cands}

Decide how the release note relates to the catalog. Answer with JSON only:
{{"feature_key": <exact feature_key from the list, or null>,
  "relation": "same" if the note is about that feature itself, "child" if it announces a
              capability of that feature, "new" if no listed feature fits,
  "feature_name": short catalog-style name for the capability (for child/new),
  "confidence": 0.0-1.0}}"""

if a.use_llm == "true" and proposals:
    rows = []
    for guid, p in proposals.items():
        cands = [f for f in features if f["domain"] == p["domain"]] if p["domain"] else features
        rows.append({"guid": guid, "prompt": PROMPT.format(
            title=p["item"]["title"], cats=", ".join(p["item"]["categories"]),
            desc=p["item"]["description"][:1200],
            cands="\n".join(f"  {f['feature_key']} | {f['dbxPhase']}" for f in cands[:150]))})
    s.createDataFrame(rows).createOrReplaceTempView("prompts")
    try:
        out = s.sql(f"""SELECT guid, ai_query('{a.llm_endpoint}', prompt, failOnError => false) AS r
                        FROM prompts""").collect()
    except Exception as e:  # endpoint missing or not enabled for batch: use deterministic matches
        print(f"LLM matching unavailable ({type(e).__name__}: {str(e)[:300]}); deterministic only")
        out = []
    for row in out:
        p = proposals[row.guid]
        try:
            raw = row.r.result.strip().removeprefix("```json").removesuffix("```")
            j = json.loads(raw)
            k = j.get("feature_key")
            if k is not None and k not in by_key:
                raise ValueError(f"unknown feature_key {k!r}")
            rel = {"same": "same", "child": "child"}.get(j.get("relation"))
            p.update(key=k if rel else None, relation=rel, method="llm",
                     confidence=float(j.get("confidence", 0)),
                     name=(j.get("feature_name") or p["name"])[:120])
        except Exception as e:  # keep the deterministic proposal
            print(f"llm fallback for {row.guid}: {e}")

now = dt.datetime.now(dt.timezone.utc)
out_rows = []
for guid, p in proposals.items():
    f = by_key.get(p["key"])
    ctype, decision, reason = rules.decide(p["phase"], f, trb.get(p["key"]), p["relation"], p["confidence"])
    if ctype == "NEW_FEATURE" and not p["domain"]:
        decision, reason = "HELD", "no domain from feed categories; triage"
    out_rows.append({
        "change_id": hashlib.sha1(f"{a.run_id}|{guid}".encode()).hexdigest()[:16], "run_id": a.run_id,
        "guid": guid, "change_type": ctype, "feature_key": p["key"],
        "new_feature_name": p["name"] if ctype in ("NEW_FEATURE", "NEW_CHILD") else None,
        "domain": f["domain"] if f else p["domain"], "old_phase": f["dbxPhase"] if f else None,
        "new_phase": p["phase"], "match_method": p["method"], "confidence": p["confidence"],
        "decision": decision, "reason": reason, "decided_by": None, "created_at": now, "applied_at": None,
    })

if out_rows:
    target = s.table(f"{a.fq}.proposed_changes")
    s.createDataFrame(out_rows, schema=target.schema).createOrReplaceTempView("new_changes")
    s.sql(f"""MERGE INTO {a.fq}.proposed_changes t USING new_changes n ON t.change_id = n.change_id
              WHEN NOT MATCHED THEN INSERT *""")
held = sum(r["decision"] == "HELD" for r in out_rows)
print(f"{len(out_rows)} proposals ({held} held) from {len(items)} new items")
