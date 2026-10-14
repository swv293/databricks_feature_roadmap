---
name: feature-tracker-gotchas
description: Known failure modes of the Databricks Feature Tracker (weekly refresh job, monthly docs check, Genie agent, Knowledge Assistant, site build). Load BEFORE running, deploying, or changing anything in this repo, and before reviewing doc_proposals or proposed_changes, so the same mistakes are not repeated.
---

# Feature Tracker gotchas

Read the section for what you are about to do. Each item is a real failure from this project.

## Reviewing monthly docs-check proposals (`doc_proposals`)

### 1. A redirected doc page can feed the LLM the WRONG content (the most dangerous one)
**What happened (2026-10-13, held rows 4 and 13):** "Delta Sharing / Open Sharing" and "Share volumes"
had doc links that now redirect to a broader page (`/aws/en/delta-sharing/` → `/aws/en/opensharing`).
`check_docs` read the page it landed on, plus a "limitations" page linked from it. That text was about
**Snowflake's Iceberg REST catalog and Cloudflare R2**, not about Delta Sharing. The LLM still produced
confident-looking limitations (confidence 0.85–0.95) such as *"Snowflake Iceberg REST Catalog: metadata
file doesn't automatically update…; R2 not supported"*.

**Why it was caught:** both features already had human-written limitations, so the change was HELD.
**Why it is still a risk:** for a feature with EMPTY limitations, the same wrong text is **AUTO-applied**.
High LLM confidence does not mean the text is about the right feature.

**How to apply:**
- Before accepting, check that the proposed text names the feature, or something clearly part of it.
  Reject any text about another product, partner, or storage system.
- After any run where `doc_link` proposals show redirects, spot-check the AUTO-applied limitations of the
  features that redirected:
  ```sql
  SELECT p.feature_key, p.new_value, p.evidence_url
  FROM <catalog>.feature_tracker.doc_proposals p
  WHERE p.field = 'limitations' AND p.run_id = <run>
    AND p.feature_key IN (SELECT feature_key FROM <catalog>.feature_tracker.doc_proposals
                          WHERE field = 'doc_link' AND run_id = <run>);
  ```
- Children share their parent's doc page (231 features → 64 unique links). The prompt tells the LLM to use
  only text about the named feature, but it does not always comply. Be extra careful with child rows.
- A proper code fix (not done yet): when the final URL differs from `doc_link`, use the redirect for the
  link update only, and skip limitation extraction until the link is fixed.

### 2. Other ways a proposal can be wrong
- **Reworded, not new:** e.g. Lakeflow Connect "coverage varies by source API" vs "…by source type". Reject.
- **Too narrow:** one edge case (R on Runtime 15.4) replacing the main limitation ("cannot nest"). Reject or merge.
- **Setup steps, not limitations:** e.g. "Requires Python 3.7…, a virtual environment…" for dbt. Reject.
- **Drops a curated fact:** e.g. "Max 10 collaborators", "GovCloud only", "cross-region needs Delta Sharing".
  Merge: set `decision = 'ACCEPTED'` and `new_value` = the combined text.
- **Dead link:** `new_value` is empty. Find the current page, confirm it returns 200, and set it as
  `new_value` when accepting. `apply_doc_changes` skips dead-link rows that have no `new_value`.

## LLM output (`ai_query`)
- The model often adds prose after the JSON. `docs.parse_answer` reads the first JSON object only; keep it that way.
- Filler answers ("no specific limits documented", "detailed in separate docs", just "Beta") are dropped by
  `docs.clean()`. Add new filler patterns there, with a test.
- Asked for at most 300 characters, the LLM sometimes stops at exactly 300, mid-word ("pivot() function not supp").
  `docs.clean()` drops the last clause of an answer at the cap. It also strips the LLM's notes about its source,
  such as "(specific regions not detailed in excerpt)" (`META_NOTE`). Both slipped through on the first monthly run.
- `databricks-claude-sonnet-5-5` is NOT enabled for batch `ai_query`; use `var.llm_endpoint` (sonnet-4-5).

## Running and deploying
- **Every `databricks bundle deploy` wipes the Genie agent's benchmarks** (the deploy shows "1 changed").
  Always run the job "Review Board: sync Genie benchmarks" afterwards.
- **Test changes to `check_docs` with a partial run first** (`run-now` with `"only": ["ensure_tables",
  "check_docs"]`), review `doc_proposals`, then delete that run's proposals before the real run. Otherwise
  its AUTO rows are applied by the next `apply_doc_changes`, and its HELD rows block re-proposal.
  Keep its `doc_checks` rows: they cache LLM answers by content hash, so the next run is nearly free.
- Use `/* */`, not `--`, for comments in SQL that might be collapsed onto one line (e.g. sent through the
  Statement Execution API). A `--` comment then swallows the rest of the query.
- Grep any agent-written SQL for TRUNCATE / DELETE / DROP before running it. An agent's `sample_data.sql`
  once truncated `feature_tracker.features`; it was restored from a Delta version.
- `sys.exit(0)` fails a Databricks Python file task; `return` or fall through instead.
- Changing `feed_url` (e.g. AWS -> Azure) on an existing deployment: feed guids are URLs, so the new feed's
  recent items all look new. Move `feed_baseline_date` to the switch date in the same deploy.
- A first run needs `feed_baseline_date`. Move it forward whenever a newer `data/features.json` is committed,
  or a fresh deployment re-adds feed items that are already in the seed.

## Site build and parity
- Never hand-edit `index.html`; change `site/template.html` or `data/*.json` and run `scripts/build_site.py`.
- To match local with live: `scripts/pull_live_data.sh <profile>` (pulls the last publish's inputs, rebuilds,
  and compares byte for byte). The job only uses the template after `bundle deploy`.
- Keep the mock-up banner block (`<!--@@MOCKUP_BANNER-->`) and the `mockup_banner` variable. It goes "off"
  only in production with real TRB data.
- Genie and Knowledge Assistant links on the public page work only when demoed (viewers have no workspace
  access). Keep the notes that say so.

## Git
- Push this project's private repo as GitHub account `swv293` (`gh auth status`; switch if needed).
