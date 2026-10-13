import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from feature_tracker import feed, rules  # noqa: E402

FEATURES = [
    {"name": "Genie One", "domain": "SQL & BI Analytics", "dbxPhase": "GA", "parent": "genie"},
    {"name": "Lakebase (Postgres OLTP)", "domain": "Storage & Formats", "dbxPhase": "GA", "parent": None},
    {"name": "Lakeflow Connect", "domain": "Ingestion", "dbxPhase": "GA", "parent": None},
    {"name": "SQL Server (cloud + on-prem)", "domain": "Ingestion", "dbxPhase": "Public Preview", "parent": "lfc"},
    {"name": "Lakeflow Designer (no-code)", "domain": "Pipelines & Data Engineering", "dbxPhase": "Upcoming", "parent": None},
]
BY_KEY = {f"{f['name']}@{f['domain']}": f for f in FEATURES}


# --- phase detection -------------------------------------------------------
def test_phase_from_title():
    assert feed.detect_phase("Metric view window measures are generally available") == "GA"
    assert feed.detect_phase("GitLab connector is available in Beta") == "Beta"
    assert feed.detect_phase("Genie visualizations in Slack replies (Public Preview)") == "Public Preview"
    assert feed.detect_phase("Run Lakeflow pipelines as a group") is None


def test_future_announcement_is_upcoming_not_ga():
    t = "Webhook-triggered deployments for Databricks Apps will soon be generally available"
    assert feed.detect_phase(t) == "Upcoming"
    assert feed.detect_phase("Anything at all", categories=["Product", "whatscoming"]) == "Upcoming"


def test_retirement_beats_ga():
    assert feed.detect_phase("The GA v1 API is scheduled for retirement") == "Deprecated"


def test_model_churn_is_noise():
    assert feed.is_noise("Moonshot AI Kimi K2.7 is scheduled for retirement")
    assert feed.is_noise("Anthropic Claude Haiku 5.5 is now available on Unity Gateway")
    assert feed.is_noise("Databricks SQL version 2026.39 is rolling out in Current")
    assert not feed.is_noise("GitLab connector is available in Beta")


def test_feature_name_from_title():
    assert feed.feature_name_from_title("GitLab connector is available in Beta") == "GitLab connector"
    assert feed.feature_name_from_title("Lakebase snapshots API (Beta)") == "Lakebase snapshots API"
    assert feed.feature_name_from_title("The Databricks Excel Add-in is now generally available") == "Databricks Excel Add-in"


# --- matching ----------------------------------------------------------------
def test_capability_of_feature_is_child():
    key, cov = rules.name_match("Genie One memory is now generally available", FEATURES)
    assert key == "Genie One@SQL & BI Analytics"
    assert rules.relation_from_coverage(cov) == "child"


def test_feature_itself_is_same():
    key, cov = rules.name_match("Lakeflow Designer is now generally available", FEATURES)
    assert key == "Lakeflow Designer (no-code)@Pipelines & Data Engineering"
    assert rules.relation_from_coverage(cov) == "same"


def test_category_parent_fallback():
    cats = ["Product", "Ingestion", "Lakeflow Connect"]
    assert rules.name_match("Google Workspace connector is available in Beta", FEATURES)[0] is None
    assert rules.category_parent(cats, FEATURES) == "Lakeflow Connect@Ingestion"


# --- decision policy (PHI safety) ---------------------------------------------
def test_becoming_phi_eligible_is_held():
    f = BY_KEY["SQL Server (cloud + on-prem)@Ingestion"]
    ctype, decision, _ = rules.decide("GA", f, "Approved", "same", 1.0)
    assert (ctype, decision) == ("PHASE_CHANGE", "HELD")


def test_ga_without_full_approval_applies():
    f = BY_KEY["SQL Server (cloud + on-prem)@Ingestion"]
    for status in ("Not Reviewed", "Under Review", "Approved with Conditions"):
        assert rules.decide("GA", f, status, "same", 1.0)[1] == "AUTO"


def test_losing_eligibility_applies_immediately():
    f = BY_KEY["Genie One@SQL & BI Analytics"]
    ctype, decision, _ = rules.decide("Deprecated", f, "Approved", "same", 1.0)
    assert (ctype, decision) == ("PHASE_CHANGE", "AUTO")


def test_apparent_regression_becomes_child():
    f = BY_KEY["Lakebase (Postgres OLTP)@Storage & Formats"]
    assert rules.decide("Beta", f, "Approved", "same", 1.0)[0] == "NEW_CHILD"


def test_low_confidence_llm_match_is_held():
    f = BY_KEY["Lakeflow Designer (no-code)@Pipelines & Data Engineering"]
    assert rules.decide("GA", f, "Not Reviewed", "same", 0.55)[1] == "HELD"


def test_unknown_feature_is_inserted():
    assert rules.decide("Beta", None, None, None, 1.0)[:2] == ("NEW_FEATURE", "AUTO")
