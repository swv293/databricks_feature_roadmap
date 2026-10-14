# Databricks Feature Tracker

Internal tracker of Databricks features for a healthcare payer platform team, on two axes:
the Databricks release phase (Axis A) and the enterprise Tech Review Board status (Axis B).
A feature is **PHI-eligible only when it is GA *and* TRB-Approved.** That value is always
computed and never hand-set.

The deliverable is one self-contained page, `index.html`, built from `data/*.json`.

## Layout

| Path | What it is | Who changes it |
|---|---|---|
| `index.html` | Built page (committed so it opens without a build) | `scripts/build_site.py` only |
| `site/template.html` | Page markup, styles, and render code, with data placeholders | Developers |
| `data/features.json` | Seed catalog (231 features); the curated fields are blurb, use cases, priority, limitations, objections | Platform team, through PRs |
| `data/domains.json`, `data/feed.json` | Domain list; seed "recent changes" items | Platform team |
| `scripts/build_site.py` | Validates data and injects it into the template | — |
| `assets/` | Official Databricks logo SVGs (inlined into the page) | — |
| `databricks.yml`, `refresh-job/` | Weekly refresh job (Asset Bundle, serverless) | Developers |
| `trb/table/` | TRB register DDL and synthetic sample data (Genie space source) | TRB / platform team |
| `trb/docs/` | TRB document templates and synthetic samples (Knowledge Assistant corpus) | TRB secretariat |
| `trb/CANONICAL.md` | Facts the synthetic table rows and documents must agree on | — |
| `trb/RESEARCH.md` | Public sources behind the TRB document and field design | — |
| `trb/data/reviews_extended.json` | Content for reviews TRB-2026-010..035 (validated) | TRB / platform team |
| `trb/docs/pdf/` | The 74 documents as PDFs (Knowledge Assistant corpus) | `render_pdfs.py` only |
| `trb/ka/` | Knowledge Assistant provisioning, eval questions, eval script | Developers |
| `trb/genie/` | Review Board Genie agent: generator, SQL runner, build and validate script, `genie_agent.json`, benchmarks, `DELIVERABLE.md` | Developers |

## Build locally

```bash
scripts/pull_live_data.sh <profile>    # data/*.json <- the last published build's inputs; rebuild; check parity
python3 scripts/build_site.py          # data/*.json + site/template.html -> index.html
python3 refresh-job/src/dry_run.py --days 7   # what this week's feed would change
uvx pytest refresh-job/tests
```

## Recreate this project from scratch

Everything needed is in this repo. Do the steps in order; details are in the sections below.

**Prerequisites** in your Databricks workspace:
- A Unity Catalog **catalog** you can use, with `USE CATALOG` and `CREATE SCHEMA` (the jobs create the
  `feature_tracker` and `trb` schemas in it).
- **Serverless** jobs, and a **serverless SQL warehouse** (Genie needs one).
- A foundation-model endpoint that supports batch `ai_query` (default `databricks-claude-sonnet-4-5`).
- **Agent Bricks Knowledge Assistant** access, for the documents assistant (optional).
- **Outbound access** from serverless to `docs.databricks.com` (and `learn.microsoft.com` for the Azure feed).
  See [Release-notes feed per cloud](#release-notes-feed-per-cloud).
- Locally: the Databricks CLI (v1.20 or later), Python 3.10 or later, and `uvx` for the tests.

**Steps** (`C` = your catalog, `P` = your CLI profile, `W` = your serverless warehouse id):

1. **Clone and check:** `uvx pytest refresh-job/tests` and `python3 scripts/build_site.py`.
2. **Set your values** in `.databricks/bundle/dev/variable-overrides.json` (see
   [Set up your environment](#set-up-your-environment)): at least `catalog` and `genie_warehouse_id`.
3. **Generate the TRB data and Genie definition for your catalog:**
   ```bash
   python3 trb/genie/generate_extended.py --catalog $C
   python3 trb/genie/build_genie.py --catalog $C --profile $P --warehouse-id $W --no-validate
   ```
4. **Deploy:** `databricks bundle deploy -t dev --profile $P`. This creates the four jobs and the Genie agent.
5. **Run the weekly job once:** `databricks bundle run feature_tracker_weekly_refresh -t dev --profile $P`.
   It creates `$C.feature_tracker`, seeds 257 features, reads the feed, and publishes the page to the volume
   `$C.feature_tracker.site`.
6. **Create the TRB register:** `databricks bundle run review_board_setup -t dev --profile $P`.
7. **Restore the Genie benchmarks:** `databricks bundle run review_board_genie_maintenance -t dev --profile $P`.
   Repeat after every deploy.
8. **Knowledge Assistant (optional):** `python3 trb/ka/provision_ka.py --profile $P --catalog $C --wait`, then
   `python3 trb/ka/eval_ka.py --profile $P --endpoint <ka endpoint it prints>`.
9. **Point the page's buttons at your agents:** set `genie_url` (the agent's URL in your workspace) and `ka_url`
   (its serving-endpoint page) in the overrides file, deploy, repeat step 7, and run the weekly job again.
   If they're empty, the page says "Not configured".
10. **Hosting (optional):** for GitHub Pages, set `github_repo` and the token secret (see [Hosting](#hosting)).
    Otherwise copy `index.html` from the volume to your internal host.
11. **Monthly docs check (optional):** `databricks bundle run feature_tracker_monthly_docs -t dev --profile $P`.
12. **Turn the schedules on** when ready: deploy the `prod` target, or set `schedule_pause: UNPAUSED`.
    Before real TRB data goes in, set `mockup_banner` to `off` and host the page internally.

> **Not yet tested in an empty catalog:** step 4 creates the Genie agent before step 6 creates the tables it
> reads. Recreation was verified only in a catalog that already had the TRB tables. If step 4 fails on the agent,
> move `trb/resources/review_board.genie.yml` and `trb/resources/review_board_genie_maintenance.job.yml` out of
> `trb/resources/`, deploy, run steps 5 and 6, move both files back, deploy again, then run step 7.

The PDFs for the Knowledge Assistant are committed and name no catalog, so `trb/genie/render_pdfs.py` is only
needed after you edit a TRB document. It uses a Databricks-internal converter; elsewhere, set `MARKDOWN_TO_PDF`
to any script that takes `--input <md> --output <pdf>`.

## Weekly refresh job

A one-page summary of both jobs (tasks, cost, what is and isn't Databricks, internal hosting) is in
[refresh-job/JOBS.md](refresh-job/JOBS.md).

Runs Mondays at 06:00 America/New_York on serverless. Deploys **PAUSED**. The `prod` target unpauses it.

```
ensure_tables ─┬─ ingest_feed ── detect_changes ── apply_changes ── publish_site ── publish_github
               └─ snapshot_posture
```

1. **ensure_tables**: creates `platform.feature_tracker.*` and seeds `features` from `data/features.json` on the first run.
2. **ingest_feed**: appends new RSS items to `feed_items` from `var.feed_url` (AWS by default; Azure and GCP feeds work too, see [Release-notes feed per cloud](#release-notes-feed-per-cloud)).
3. **snapshot_posture**: records compliance security profile and related settings (informational).
4. **detect_changes**: matches items to features (name, then feed category, then `ai_query`) and writes `proposed_changes`.
5. **apply_changes**: applies AUTO rows and ACCEPTED held rows. It only writes Axis A.
6. **publish_site**: rebuilds the page from Unity Catalog with live TRB status, open TRB questions (from `trb.reviews`), and 92 days of change history per refresh date (`refresh_runs` + `proposed_changes`, see `feature_tracker/history.py`) and writes it to `/Volumes/platform/feature_tracker/site/`.
7. **publish_github**: commits `index.html` to the public GitHub Pages repo. Skips if the token secret is missing.

> **Remove in production:** the page shows a bold mock-up / synthetic-TRB-data banner. Set the bundle
> variable `mockup_banner` to `off` (see `databricks.yml`) once the page carries real TRB data.
> Locally: `python3 scripts/build_site.py --mockup-banner off`.

**Safety rules** (in `refresh-job/src/feature_tracker/rules.py`, unit-tested):
- The job never writes TRB status.
- A phase change that would make a feature PHI-eligible is **HELD** until a person accepts it:
  ```sql
  UPDATE platform.feature_tracker.proposed_changes
  SET decision = 'ACCEPTED', decided_by = current_user()
  WHERE change_id = '<id>';   -- applied on the next run
  ```
- Losing eligibility (for example, a deprecation) applies immediately.
- Capabilities of an existing feature become child rows. New rows enter as Not Reviewed / Low.

## Monthly documentation check

Runs the first Monday of each month at 07:00 America/New_York (after the weekly run). Deploys **PAUSED**
with the same `schedule_pause` variable.

```
ensure_tables ── check_docs ── apply_doc_changes ── publish_site ── publish_github
```

1. **check_docs**: fetches each unique doc page once (plus up to two dedicated limitations pages it links
   to), asks `ai_query` per feature for the limitations that apply to that feature, and records the result in
   `doc_checks`. The LLM is called again only when a page's text changes. Writes `doc_proposals`.
2. **apply_doc_changes**: applies AUTO and ACCEPTED rows to `features.limitations` / `features.doc_link`.

**Rules** (in `refresh-job/src/feature_tracker/docs.py`, unit-tested):
- Empty limitations are filled automatically (confidence ≥ 0.7; filler such as "none documented" is dropped).
- Replacing limitations someone already wrote is **HELD**. A redirect to another docs page updates the link;
  a dead link (404, or a redirect to a landing page) is **HELD**. Accept with:
  ```sql
  UPDATE platform.feature_tracker.doc_proposals
  SET decision = 'ACCEPTED', decided_by = current_user()   -- for a dead link, also SET new_value = '<new url>'
  WHERE proposal_id = '<id>';   -- applied on the next monthly run
  ```
- A value that was held, rejected, or accepted is not proposed again.

## Set up your environment

The bundle has no workspace-specific values. Before the first deploy, create
`.databricks/bundle/<target>/variable-overrides.json` (the `.databricks/` folder is gitignored, so it stays
on your machine):

```json
{
  "catalog": "<your catalog>",
  "genie_warehouse_id": "<serverless SQL warehouse id>",
  "github_repo": "<owner>/<pages repo>",
  "genie_url": "https://<workspace host>/genie/rooms/<space id>",
  "ka_url": "https://<workspace host>/ml/endpoints/<ka endpoint>"
}
```

- `github_repo` is optional: leave it out and `publish_github` skips (the page still goes to the volume).
- `genie_url` and `ka_url` are the page's "Open Genie agent" / "Open Knowledge Assistant" buttons. Leave them
  out until the agents exist; the page then says "Not configured".
- `notify_email` defaults to the deploying user in `dev`; set it for other targets.
- `genie_parent_path` defaults to `/Workspace/Users/<you>/feature_tracker`.
- The workspace comes from `--profile <profile>` on every command; `databricks.yml` names no profile or host.
- Without the file, `bundle validate` stops with "no value assigned to required variable genie_warehouse_id".
- The generated TRB assets (`trb/table/extended_data.sql`, `trb/genie/*.json`) name a catalog. Regenerate
  them for yours, as in [Review Board Genie agent](#review-board-genie-agent) below.

Deploy (choose the profile explicitly):

```bash
databricks bundle validate -t dev --profile <profile>
databricks bundle deploy   -t dev --profile <profile>
databricks bundle run feature_tracker_weekly_refresh -t dev --profile <profile>
databricks bundle run feature_tracker_monthly_docs  -t dev --profile <profile>
```

Prerequisites: serverless egress to `docs.databricks.com` (and `learn.microsoft.com` for the Azure feed); a foundation-model endpoint for
`var.llm_endpoint`; `USE CATALOG`/`CREATE SCHEMA` on the catalog for the job's run-as identity.

## Release-notes feed per cloud

The demo deployment uses the **AWS** feed (the default). Set `feed_url` per target for another cloud:

| Cloud | `feed_url` | Host serverless must reach |
|---|---|---|
| AWS (default, demo) | `https://docs.databricks.com/aws/en/feed.xml` | `docs.databricks.com` |
| Azure | `https://learn.microsoft.com/en-us/azure/databricks/feed.xml` | `learn.microsoft.com` |
| GCP | `https://docs.databricks.com/gcp/en/feed.xml` | `docs.databricks.com` |

All three use the same RSS format. The parser was checked against the live AWS and Azure feeds on 2026-10-13.

**Allow the pages for serverless compute.** The jobs run on serverless and fetch the feed and doc pages
over public HTTPS. If the workspace has a serverless network policy (egress control), add the feed's host
to its allowed domains, plus `docs.databricks.com` for the monthly docs check. Otherwise `ingest_feed`
fails and no changes are found. Check from your own machine first:

```bash
python3 refresh-job/src/dry_run.py --days 28 --feed-url <feed_url>
```

**Switching feeds on an existing deployment** (for example, AWS to Azure):

1. Pick the switch date (today).
2. In the target, set both variables in the same change:
   ```yaml
   targets:
     prod:
       variables:
         feed_url: https://learn.microsoft.com/en-us/azure/databricks/feed.xml
         feed_baseline_date: "2026-10-13"   # the switch date
   ```
   Feed items are identified by their URL, and each cloud's URLs differ. Without the new baseline date,
   every recent item from the new feed looks new and is proposed again as a duplicate.
3. Allow the new host for serverless (above).
4. `databricks bundle deploy`, then run the Genie benchmark sync job (every deploy wipes the benchmarks).
5. Run the weekly job once and check `proposed_changes` for that run: it should hold only items published
   after the switch date.

A fresh deployment needs no special steps: set `feed_url` and use today as `feed_baseline_date`.

The monthly docs check reads only `docs.databricks.com` pages. Azure customers can keep those doc links,
since the content is the same; links on `learn.microsoft.com` are skipped.

## Hosting

Published at **https://swv293.github.io/databricks-feature-tracker/** from the public repo
`swv293/databricks-feature-tracker`, which holds only `index.html` (set it as `github_repo`). The
`publish_github` task commits each week's page there. This repo holds the code and the synthetic TRB corpus.

⚠ **GitHub Pages is public on the internet.** Publish only content that is safe to be public.
Before real TRB decisions go in, host the page internally behind SSO (an internal web server or
SharePoint): see [refresh-job/JOBS.md](refresh-job/JOBS.md#hosting-it-internally).

One-time token setup (fine-grained PAT, repository access = only `databricks-feature-tracker`,
permission Contents: Read and write):

```bash
databricks secrets create-scope feature_tracker --profile <profile>
databricks secrets put-secret feature_tracker github_token --profile <profile>   # paste the PAT
```

Without the secret, `publish_github` skips and the page is published to the volume only.

## Review Board Genie agent

**Feature Tracker Review Board Analytics Space**, managed by this bundle (open it from **Genie** in your
workspace). It queries `<catalog>.trb` (7 assets: metric view, PHI view, 5 tables). Benchmarks: 20/20.

| Bundle resource | File | What it does |
|---|---|---|
| `genie_spaces.review_board_agent` | `trb/resources/review_board.genie.yml` | The agent; definition from `trb/genie/review_board.geniespace.json` |
| `jobs.review_board_setup` | `trb/resources/review_board_setup.job.yml` | Creates the TRB register in an empty catalog (tables, data, views, 74 documents). Refuses if data exists |
| `jobs.review_board_genie_maintenance` | `trb/resources/review_board_genie_maintenance.job.yml` | Re-posts the 17 benchmarks. **Run after every deploy:** deploys wipe them |

Recreate everything in a new catalog or workspace:

```bash
C=<catalog>; P=<profile>; W=<serverless warehouse id>
python3 trb/genie/generate_extended.py --catalog $C        # catalog-specific rows + documents
python3 trb/genie/build_genie.py --catalog $C --profile $P --warehouse-id $W --no-validate   # agent definition
databricks bundle deploy -t <target> --profile $P           # creates the agent + jobs
databricks bundle run feature_tracker_weekly_refresh -t <target> --profile $P   # creates feature_tracker.features
databricks bundle run review_board_setup -t <target> --profile $P               # TRB tables, data, views, documents
databricks bundle run review_board_genie_maintenance -t <target> --profile $P   # benchmarks
python3 trb/genie/build_genie.py --catalog $C --profile $P --warehouse-id $W    # optional: validate every SQL
```

Set `catalog`, `genie_warehouse_id` and `genie_parent_path` per target. To adopt an existing agent instead
of creating one: `databricks bundle deployment bind review_board_agent <space_id> -t <target>`.
Recreation was verified on 2026-10-12: a fresh agent was deployed from the bundle, answered "which features
are approved for PHI" correctly (20), and was destroyed.

Score the agent: `run_benchmarks.py` from the workspace genie-benchmarks-eval skill, with `trb/genie/benchmarks.json`
(includes 3 negative questions). The 8-section deliverable is in `trb/genie/DELIVERABLE.md`.

## Review Board Knowledge Assistant

**Feature Tracker Review Board Knowledge Assistant** (Agent Bricks; `provision_ka.py` prints its id and
serving endpoint `ka-<id>-endpoint`). In the workspace: **Agents** → that name. It answers from the full text of the
74 TRB documents rendered as PDFs in `<catalog>.trb.corpus_pdf`, citing the PDF and page.
Eval: 11/11 (`trb/ka/eval_questions.json`).

```bash
python3 trb/genie/render_pdfs.py                          # optional (PDFs are committed): markdown -> branded PDFs (trb/docs/pdf/), document-control table on page 1
databricks fs cp -r trb/docs/pdf dbfs:/Volumes/$C/trb/corpus_pdf --overwrite --profile $P
python3 trb/ka/provision_ka.py --profile $P --catalog $C   # create or update, attach source, sync (idempotent)
python3 trb/ka/eval_ka.py --profile $P --endpoint <ka-endpoint>
```

Asset Bundles (CLI v1.20) have no Knowledge Assistant resource, so `provision_ka.py` is the source of truth.
`review_board_setup` copies the PDFs into the volume when recreating the register.
Division of labor: the **Genie agent** answers live status, counts, and lists from the register. The **Knowledge
Assistant** answers "why" and "what does the document say" with citations, and sends current-status questions to Genie.

## Data sources of truth

- **Axis A (phase)**: `platform.feature_tracker.features`, maintained by the job.
- **Axis B (TRB)**: `platform.trb.reviews` and related tables, curated by people. The page reads the latest review per `feature_key`, and falls back to the seed value
  (see [Updating TRB reviews and status](#updating-trb-reviews-and-status)).
- **Curated text**: `data/features.json` in git is the seed. After the first run, edit the curated columns in `features`
  (see [Editing curated feature text](#editing-curated-feature-text)).

## Updating TRB reviews and status

TRB decisions live in `<catalog>.trb`, and the TRB secretariat updates them with SQL. The jobs only read these
tables and never write TRB status, so no automated run can approve a feature for PHI. Each feature shows its
newest review, picked by `latest_review_date` (`refresh-job/src/feature_tracker/common.py`). A feature with no
review shows its seed status.

A feature can have several reviews over time (a first review, then a re-review after GA or a rejection), and
`review_id` is the key. Update one review, not every row for the feature.

```sql
/* 1. Find the feature's current review. */
SELECT review_id, feature_key, current_trb_status, latest_review_date
FROM <catalog>.trb.reviews
WHERE feature_key = 'Genie One@SQL & BI Analytics'
ORDER BY latest_review_date DESC;

/* 2. Update that review. Naming the feature too means a wrong id changes 0 rows. */
UPDATE <catalog>.trb.reviews
SET current_trb_status = 'Approved',   /* Not Reviewed | Under Review | Approved with Conditions | Approved | Rejected | Retired */
    latest_review_date = current_date(),   /* always bump: it decides which review the page shows */
    decision_date      = current_date(),
    open_questions     = NULL,             /* '; '-separated list shown in the drawer */
    updated_at         = current_timestamp()
WHERE review_id   = 'TRB-2026-005'
  AND feature_key = 'Genie One@SQL & BI Analytics';

/* 3. Keep the audit trail: one row per change. */
INSERT INTO <catalog>.trb.review_history
VALUES (uuid(), 'TRB-2026-005', current_date(), 'status_change', 'Approved with Conditions', 'Approved',
        'TRB Chair', 'All conditions verified closed', NULL, current_timestamp());
```

- **PHI-eligible = GA and exactly `Approved`.** "Approved with Conditions" does not count. Close the review's
  rows in `trb.approval_conditions` (`verification_status = 'Closed'`) first, then set the status to `Approved`.
- `feature_key` must match the tracker exactly: `Name@Domain`, e.g. `Model Serving@AI / ML`.
- **New review:** insert a row into `trb.reviews` with a new `review_id` and today's `latest_review_date`
  (see `trb/table/ddl.sql` for the columns).
- **When it shows up:** the Genie agent sees it immediately. The page shows it after the next `publish_site`
  (the Monday run, or a manual run). The Knowledge Assistant reads only documents: add new minutes or decision
  records as PDFs to `trb.corpus_pdf` and re-run `trb/ka/provision_ka.py`.

## Editing curated feature text

After the first run, the curated columns (`limitations`, `blurb`, `doc_link`, `priority`, `use_cases`,
`objections`) live in `<catalog>.feature_tracker.features`. Correct them with SQL. The page shows the change after
the next publish (the Monday run, or a manual run).

```sql
/* 1. Find the exact feature_key. */
SELECT feature_key, limitations, doc_link
FROM <catalog>.feature_tracker.features
WHERE name ILIKE '%model serving%';

/* 2. Update it. */
UPDATE <catalog>.feature_tracker.features
SET limitations = '1000 endpoints per workspace; 300K QPS per endpoint with route optimization; 16 MB payload limit (4 MB for agents); 597s max execution time; limited region availability',
    updated_at  = current_timestamp()
WHERE feature_key = 'Model Serving@AI / ML';

/* 3. Check it. */
SELECT feature_key, limitations, updated_at
FROM <catalog>.feature_tracker.features
WHERE feature_key = 'Model Serving@AI / ML';
```

Other curated fields work the same way:

```sql
UPDATE <catalog>.feature_tracker.features
SET blurb      = 'Serve models as low-latency APIs, e.g. real-time risk scoring on incoming claims.',
    doc_link   = 'https://docs.databricks.com/aws/en/machine-learning/model-serving/',
    priority   = 'High',                                  /* High | Medium | Low */
    use_cases  = array('Risk scoring APIs', 'Fraud detection'),
    updated_at = current_timestamp()
WHERE feature_key = 'Model Serving@AI / ML';
```

- `feature_key` must match exactly: `Name@Domain`, including spaces and capitals. Step 1 gives you the value.
- Separate limitations with `; `. The card subtitle shows the first one, and the drawer lists them all.
- Escape apostrophes with a backslash (`metastore\'s`), or put the string in double quotes.
- Keep limitations under about 300 characters, the length the monthly docs check works with.
- The monthly docs check won't overwrite this text. Once limitations aren't empty, any difference it finds in
  the docs is **HELD** for a person (see [Monthly documentation check](#monthly-documentation-check)).
- Don't edit `dbx_phase` here. The weekly job owns it, and a phase change can make a feature PHI-eligible.
  Accept or reject the held row in `proposed_changes` instead.
- To make sure nobody changed the row since you looked, add `AND limitations = '<current text>'` to the `WHERE`.
- To fix a mistake, use Delta time travel: `DESCRIBE HISTORY <catalog>.feature_tracker.features`, then
  `RESTORE TABLE ... TO VERSION AS OF <n>`. That restores the whole table, so check what else changed since.
