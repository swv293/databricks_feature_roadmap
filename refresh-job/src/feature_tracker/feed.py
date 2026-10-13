"""Parse the Databricks release-notes RSS feed and read phase signals from it.

Pure Python (stdlib only) so it is unit-testable off-cluster. FEED_URL is the AWS feed
(about 30 items/week, history back to Jan 2025) and the default for the job's --feed-url
(bundle var feed_url). The Azure feed (learn.microsoft.com/en-us/azure/databricks/feed.xml)
and GCP feed (docs.databricks.com/gcp/en/feed.xml) have the same format.
"""
import email.utils
import html
import re
import xml.etree.ElementTree as ET

FEED_URL = "https://docs.databricks.com/aws/en/feed.xml"

# Order matters: the first match wins. Deprecation is checked before GA because
# "the GA API is scheduled for retirement" is a retirement notice, not a GA launch.
PHASE_PATTERNS = [
    ("Deprecated", r"\b(deprecat\w*|scheduled for retirement|retir(?:ed|ing)|end[- ]of[- ](?:life|support)|legacy model)\b"),
    ("GA", r"\b(generally available|general availability|now GA|is GA)\b"),
    ("Public Preview", r"\bpublic preview\b"),
    ("Beta", r"\bbeta\b"),
    ("Private Preview", r"\bprivate preview\b"),
]

# Feed category -> tracker domain. Unmapped categories fall through to None and
# the item is still recorded; the matcher just gets no domain hint.
CATEGORY_TO_DOMAIN = {
    "Unity Catalog": "Platform & Governance", "Data Governance": "Platform & Governance",
    "Data governance": "Platform & Governance", "Governance": "Platform & Governance",
    "Lakehouse Federation": "Platform & Governance", "System tables & audit logs": "Platform & Governance",
    "Audit logs": "Platform & Governance", "Data Classification": "Platform & Governance",
    "Administration": "Platform & Governance", "Admin": "Platform & Governance",
    "Ingestion": "Ingestion", "Lakeflow Connect": "Ingestion", "Auto Loader": "Ingestion",
    "Data Ingestion": "Ingestion", "Data ingestion": "Ingestion", "Data Connectivity": "Ingestion",
    "Pipelines": "Pipelines & Data Engineering", "Jobs": "Pipelines & Data Engineering",
    "Data Engineering": "Pipelines & Data Engineering", "Lakeflow Designer": "Pipelines & Data Engineering",
    "Delta Lake": "Storage & Formats", "Lakebase": "Storage & Formats",
    "Formats (Delta/Iceberg)": "Storage & Formats", "Storage": "Storage & Formats",
    "dbsql": "SQL & BI Analytics", "Databricks SQL": "SQL & BI Analytics", "SQL": "SQL & BI Analytics",
    "aibi": "SQL & BI Analytics", "dashboards": "SQL & BI Analytics", "Dashboards": "SQL & BI Analytics",
    "genie": "SQL & BI Analytics", "Genie": "SQL & BI Analytics", "genieagents": "SQL & BI Analytics",
    "Genie Agents": "SQL & BI Analytics", "Data Warehousing": "SQL & BI Analytics",
    "Visualizations": "SQL & BI Analytics", "databricksone": "SQL & BI Analytics",
    "Machine Learning & AI": "AI / ML", "Machine Learning": "AI / ML", "MLflow": "AI / ML",
    "Model Serving": "AI / ML",
    "Generative AI": "Generative AI & Agents", "Gen AI": "Generative AI & Agents",
    "Unity Gateway": "Generative AI & Agents", "AI Gateway": "Generative AI & Agents",
    "Agent Framework": "Generative AI & Agents", "AI Search": "Generative AI & Agents",
    "Delta Sharing": "Sharing & Collaboration", "Marketplace": "Sharing & Collaboration",
    "Clean Rooms": "Sharing & Collaboration",
    "Security": "Security & Networking", "Networking": "Security & Networking",
    "Compliance": "Security & Networking", "Identity management": "Security & Networking",
    "Identity": "Security & Networking",
    "Databricks Apps": "Apps & Developer Tools", "Notebooks": "Apps & Developer Tools",
    "Notebook": "Apps & Developer Tools", "Bundles": "Apps & Developer Tools",
    "Git Folders": "Apps & Developer Tools", "Developers": "Apps & Developer Tools",
    "Developer Tools": "Apps & Developer Tools", "API": "Apps & Developer Tools",
    "Drivers": "Apps & Developer Tools", "Genie Code": "Apps & Developer Tools",
    "Integrations": "Apps & Developer Tools", "Partner Connect": "Apps & Developer Tools",
    "Compute": "Compute", "Serverless": "Compute", "Databricks Runtime": "Compute",
}

_TAG = re.compile(r"<[^>]+>")


def strip_html(s):
    return re.sub(r"\s+", " ", html.unescape(_TAG.sub(" ", s or ""))).strip()


def parse_feed(xml_bytes):
    """Return one dict per unique item. The feed repeats some items under two
    pages (e.g. product/2026/october and unity-gateway), so dedupe on title+date
    and keep the product release-notes link when both exist."""
    root = ET.fromstring(xml_bytes)
    out = {}
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        pub = email.utils.parsedate_to_datetime(it.findtext("pubDate")).date()
        cats = [c.text for c in it.findall("category") if c.text and c.text != "None"]
        rec = {
            "guid": (it.findtext("guid") or it.findtext("link") or "").strip(),
            "title": title,
            "link": (it.findtext("link") or "").strip(),
            "pub_date": pub,
            "description": strip_html(it.findtext("description")),
            "categories": cats,
        }
        key = (title.lower(), pub)
        if key not in out or "/release-notes/product/" in rec["link"]:
            out[key] = rec
    return list(out.values())


# Announcements of future changes ("will soon be generally available") describe
# where a feature is heading, not where it is today.
FUTURE = re.compile(r"\b(will soon|will be|coming soon|starting (?:on )?\w+ \d)", re.I)

# Model-catalog churn and version roll-outs are not platform features.
NOISE = re.compile(
    r"\b(models?\b.*\b(retire|retirement|legacy|available on|removed)|is now a legacy model|"
    r"scheduled for retirement$|supports? (priority )?pay-per-token|provisioned throughput|"
    r"Databricks SQL version|Databricks Runtime \d|serverless environment version|"
    r"(Claude|GPT|Gemini|Llama|DeepSeek|Qwen|Kimi|GLM|Mistral|gpt-oss)\b)", re.I)


def is_noise(title):
    return bool(NOISE.search(title))


def detect_phase(title, description="", categories=()):
    """Phase signal from an item, or None. Titles are authoritative; the description
    is used only for 'whats coming' items, which have no phase in the title."""
    if FUTURE.search(title) or "whatscoming" in categories:
        return "Upcoming"
    for phase, rx in PHASE_PATTERNS:
        if re.search(rx, title, re.I):
            return phase
    return None


_NAME_TAIL = re.compile(
    r"\s*(\((?:beta|public preview|private preview|ga)\)|"
    r"(?:is|are)(?: now)?(?: available)?(?: in)? (?:beta|public preview|private preview)|"
    r"(?:is|are)(?: now)? generally available.*|"
    r"(?:is|are) scheduled for retirement.*|"
    r"will soon be .*|(?:is|are) (?:now )?(?:deprecated|retired).*)\s*$", re.I)


def feature_name_from_title(title):
    """'GitLab connector is available in Beta' -> 'GitLab connector'. The LLM pass
    supplies a cleaner name on Databricks; this is the deterministic fallback."""
    name = _NAME_TAIL.sub("", title).strip(" .:-")
    name = re.sub(r"^(The|A|An|Use|New)\s+", "", name)
    return (name[:1].upper() + name[1:])[:120] if name else title[:120]


def map_domain(categories):
    for c in categories:
        if c in CATEGORY_TO_DOMAIN:
            return CATEGORY_TO_DOMAIN[c]
    return None
