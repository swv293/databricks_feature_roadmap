"""Render the self-contained tracker page from data/*.json.

    python3 scripts/build_site.py                 # data/ -> index.html
    python3 scripts/build_site.py --data-dir X --out Y

The weekly job writes fresh data/*.json from Unity Catalog and calls this same
script, so local builds and job builds produce identical pages.
"""
import argparse
import datetime as dt
import html
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

PHASES = {"Upcoming", "Private Preview", "Beta", "Public Preview", "GA", "Deprecated"}
TRB = {"Not Reviewed", "Under Review", "Approved with Conditions", "Approved", "Rejected", "Retired"}
FEED_PHASES = PHASES | {"EOL"}


def validate(domains, features, feed):
    errs = []
    keys = set()
    for f in features:
        k = f"{f['name']}@{f['domain']}"
        if k in keys:
            errs.append(f"duplicate feature_key {k}")
        keys.add(k)
        if f["domain"] not in domains:
            errs.append(f"{k}: unknown domain")
        if f["dbxPhase"] not in PHASES:
            errs.append(f"{k}: bad dbxPhase {f['dbxPhase']!r}")
        if f["enterpriseStatus"] not in TRB:
            errs.append(f"{k}: bad enterpriseStatus {f['enterpriseStatus']!r}")
    for i in feed:
        if i["p"] not in FEED_PHASES:
            errs.append(f"feed item {i.get('t', '')[:40]!r}: bad phase {i['p']!r}")
    return errs


def feed_html(item):
    """Feed entries are rendered with innerHTML. Items from the RSS job carry plain
    'title'/'domain' fields and are escaped here; legacy seed items already hold HTML in 't'."""
    if "title" in item:
        t = f"<b>{html.escape(item['title'])}</b>"
        if item.get("domain"):
            t += f" ({html.escape(item['domain'])})"
        if item.get("link", "").startswith("https://docs.databricks.com/"):
            t += f' <a href="{html.escape(item["link"])}">docs ↗</a>'
        return {"date": item["date"], "p": item["p"], "t": t}
    return item


HISTORY_DAYS = 92  # about 3 months of weekly runs; matches refresh-job history.KEEP_DAYS


def history_html(history, today):
    """data/history.json -> [{date, runs, changes: [{p, t}]}] with escaped HTML in 't'.
    Dates older than HISTORY_DAYS are dropped (a local snapshot ages between pulls)."""
    cutoff = (today - dt.timedelta(days=HISTORY_DAYS)).isoformat()
    out = []
    for h in history:
        if h["date"] < cutoff:
            continue
        changes = []
        for c in h["changes"]:
            e = html.escape
            if c["type"] == "NEW_CHILD":
                t = f"New capability of <b>{e(c['parent'])}</b>: {e(c['name'])}"
            elif c["type"] == "NEW_FEATURE":
                t = f"New feature: <b>{e(c['name'])}</b>"
            elif c["type"] == "DOC_LIMITATIONS":
                t = f"<b>{e(c['name'])}</b>: limitations from docs: “{e(c.get('value', ''))}”"
            elif c["type"] == "DOC_LINK":
                t = (f"<b>{e(c['name'])}</b>: doc link moved" if c.get("value")
                     else f"<b>{e(c['name'])}</b>: doc link is broken")
            else:
                t = f"<b>{e(c['name'])}</b>: {e(c['old'] or '?')} → {e(c['new'])}"
            if c.get("domain"):
                t += f" ({e(c['domain'])})"
            if c.get("link", "").startswith("https://docs.databricks.com/"):
                label = "docs" if c["type"].startswith("DOC_") else "release note"
                t += f' <a href="{e(c["link"])}" target="_blank">{label} ↗</a>'
            t += f' <span class="hdec">{e(c["decision"])}</span>'
            changes.append({"p": c["new"], "t": t})
        out.append({"date": h["date"], "runs": h["runs"], "changes": changes})
    return out


def js(obj):
    # "</" would close the <script> tag early if it appeared inside a string.
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def assistant_link(url, el_id, label, var):
    if not url:
        return f'<span class="cta" id="{el_id}">Not configured: set the bundle variable <code>{var}</code></span>'
    return f'<a class="cta" href="{html.escape(url)}" id="{el_id}" target="_blank" rel="noopener">{label} ↗</a>'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=ROOT / "data", type=pathlib.Path)
    ap.add_argument("--template", default=ROOT / "site" / "template.html", type=pathlib.Path)
    ap.add_argument("--out", default=ROOT / "index.html", type=pathlib.Path)
    ap.add_argument("--mockup-banner", default="on", choices=["on", "off"],
                    help="'off' drops the mock-up / synthetic-TRB-data notice (production only)")
    a = ap.parse_args()

    domains = json.loads((a.data_dir / "domains.json").read_text())
    features = json.loads((a.data_dir / "features.json").read_text())
    feed = json.loads((a.data_dir / "feed.json").read_text())
    meta_path = a.data_dir / "meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    meta.setdefault("builtAt", dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
    h_path = a.data_dir / "history.json"
    hist = history_html(json.loads(h_path.read_text()) if h_path.exists() else [], dt.date.today())

    # Open TRB questions per feature_key, from the latest trb.reviews row (optional file).
    q_path = a.data_dir / "trb_questions.json"
    questions = json.loads(q_path.read_text()) if q_path.exists() else {}
    for f in features:
        q = questions.get(f"{f['name']}@{f['domain']}")
        f["trbReview"] = q["review"] if q else ""
        f["trbQuestions"] = q["questions"] if q else []

    errs = validate(domains, features, feed)
    if errs:
        sys.exit("validation failed:\n  " + "\n  ".join(errs))

    page = a.template.read_text()
    start, end = "<!--@@MOCKUP_BANNER-->", "<!--@@/MOCKUP_BANNER-->"
    if page.count(start) != 1 or page.count(end) != 1:
        sys.exit(f"template must contain {start} ... {end} exactly once")
    if a.mockup_banner == "off":
        page = page[:page.index(start)] + page[page.index(end) + len(end):]
    for token, value in {
        # Workspace links come from the bundle variables genie_url / ka_url (via meta.json).
        "<!--@@GENIE_LINK@@-->": assistant_link(meta.get("genieUrl"), "genie-link", "Open Genie agent", "genie_url"),
        "<!--@@KA_LINK@@-->": assistant_link(meta.get("kaUrl"), "ka-link", "Open Knowledge Assistant", "ka_url"),
        "/*@@DOMAINS@@*/[]": js(domains),
        "/*@@FEATURES@@*/[]": js(features),
        "/*@@META@@*/{}": js(meta),
        "/*@@FEED@@*/[]": js([feed_html(i) for i in feed]),
        "/*@@HISTORY@@*/[]": js(hist),
    }.items():
        if page.count(token) != 1:
            sys.exit(f"template must contain {token} exactly once")
        page = page.replace(token, value)

    a.out.write_text(page)
    print(f"wrote {a.out} ({len(page):,} bytes, {len(features)} features, {len(feed)} feed items)")


if __name__ == "__main__":
    main()
