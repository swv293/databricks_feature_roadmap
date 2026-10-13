# The jobs that keep the Feature Tracker page current

Two serverless Databricks jobs (Lakeflow Jobs), defined in the Asset Bundle (`databricks.yml`,
`refresh-job/resources/`). Both deploy **PAUSED**; the `prod` target unpauses them.

| Job | Schedule (America/New_York) | Typical run | Cost measured on the demo workspace |
|---|---|---|---|
| `feature_tracker_weekly_refresh` | Mondays 06:00 | ~3 min | 0.03–0.9 DBU per run (≈0.5 typical, first nine runs) |
| `feature_tracker_monthly_docs` | First Monday of the month, 07:00 | ~3.5 min | similar; LLM calls only for pages whose text changed |

LLM tokens (`ai_query`) are billed separately from the job DBUs. Both jobs call the LLM only on new
feed items or changed doc pages, so the token cost stays small.

## Weekly refresh: phase changes from the release notes

```
ensure_tables ─┬─ ingest_feed ── detect_changes ── apply_changes ── publish_site ── publish_github
               └─ snapshot_posture
```

| Task | What it does |
|---|---|
| `ensure_tables` | Creates the `feature_tracker` tables; seeds `features` from `data/features.json` on the first run |
| `ingest_feed` | Downloads the release-notes feed (bundle variable `feed_url`) and appends new items to `feed_items` |
| `snapshot_posture` | Records workspace settings such as the compliance security profile (informational; a failure does not block publishing) |
| `detect_changes` | Matches each item to a feature (name, then feed category, then `ai_query`) and writes `proposed_changes` |
| `apply_changes` | Applies AUTO rows and ACCEPTED held rows. Writes phase (Axis A) only |
| `publish_site` | Rebuilds the page from Unity Catalog with live TRB status, open TRB questions, and 92 days of history; writes it to the `site` volume |
| `publish_github` | Commits `index.html` to the public GitHub Pages repo (skips if the token secret is missing) |

## Monthly documentation check: limitations and doc links

```
ensure_tables ── check_docs ── apply_doc_changes ── publish_site ── publish_github
```

| Task | What it does |
|---|---|
| `check_docs` | Fetches each unique doc page once (plus up to two limitations pages it links to), asks `ai_query` for that feature's limitations, caches the answer by page-content hash in `doc_checks`, writes `doc_proposals` |
| `apply_doc_changes` | Applies AUTO and ACCEPTED rows to `features.limitations` and `features.doc_link` |
| `publish_site`, `publish_github` | Same as the weekly job |

## Choosing the feed for your cloud

Set the bundle variable `feed_url` per target:

| Cloud | `feed_url` |
|---|---|
| AWS (default) | `https://docs.databricks.com/aws/en/feed.xml` |
| Azure | `https://learn.microsoft.com/en-us/azure/databricks/feed.xml` |
| GCP | `https://docs.databricks.com/gcp/en/feed.xml` |

All three have the same format; the parser was checked against the live AWS and Azure feeds on 2026-10-13
(`refresh-job/tests/test_feed.py` keeps an Azure item as a regression test). Preview locally with
`python3 refresh-job/src/dry_run.py --days 28 --feed-url <url>`.

- **Switching feeds on an existing deployment:** item ids are URLs, so every recent item of the new feed
  looks new. Move `feed_baseline_date` to the switch date in the same deploy, or the job proposes duplicates.
- **The monthly docs check still reads `docs.databricks.com` pages** (`docs.DOCS_HOST`). Azure doc links on
  `learn.microsoft.com` would be treated as off-site and not checked.

## Safety rules

- The jobs never write TRB status. TRB decisions are only read from the `trb` schema.
- A phase change that would make a feature PHI-eligible is **HELD** until a person accepts it. Losing eligibility applies immediately.
- Empty limitations are filled automatically. Replacing text someone already wrote is **HELD**.
- A moved doc link is updated automatically; a dead link is **HELD**.
- Every change is a row in `proposed_changes` or `doc_proposals`, with who decided it and when. The page's History panel is built from these rows.
- Accept a held row with a SQL `UPDATE` (see the README); it is applied on the next run.

## What runs on Databricks, and what does not

| Piece | Where |
|---|---|
| Compute, scheduling, retries, email alerts | Databricks serverless Jobs |
| Features, change queue, history, TRB register | Unity Catalog Delta tables |
| Matching and limitation extraction | `ai_query` on a Databricks foundation-model endpoint (`var.llm_endpoint`) |
| Built page and its build inputs | Unity Catalog volume `feature_tracker.site` |
| Q&A | Genie agent (TRB register) and Knowledge Assistant (TRB documents) |
| Release notes and doc pages | Public HTTP reads of `docs.databricks.com`, or `learn.microsoft.com` for the Azure feed (needs serverless egress to that host) |
| Hosting | **GitHub Pages** (demo only: the data is synthetic) via `publish_github` and a PAT in secret `feature_tracker/github_token` |

## Hosting it internally

The page is one self-contained HTML file with no server code, so any internal host that serves
static files works. The job already writes `index.html` to the `site` volume, so only the last
task changes:

- **Internal web server or intranet static site** (behind SSO): replace `publish_github` with a task that copies `index.html` there.
- **SharePoint**: upload it with the Microsoft Graph API, using an app registration whose secret is stored in a Databricks secret scope. SharePoint Online often downloads `.html` files instead of rendering them, so check your tenant's settings, or embed the page in a SharePoint page.
- Whatever the host, turn the mock-up banner off (`mockup_banner: "off"`) only when the page carries real TRB data, and keep real TRB data off the public internet.

The Genie and Knowledge Assistant links work only for people with access to the workspace.
