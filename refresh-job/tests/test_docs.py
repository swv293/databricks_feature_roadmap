import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from feature_tracker import docs  # noqa: E402

PAGE = """<html><nav>menu Limitations</nav><article>
<h1>Salesforce connector<a href="#x">​</a></h1><p>Ingest Salesforce data.</p>
<h2>Limitations</h2><ul><li>Formula fields are snapshots.</li><li>No compound fields.</li></ul>
<h2>Next steps</h2><p>Create a pipeline.</p>
<a href="/aws/en/ingestion/salesforce-limits">See limitations</a>
<a href="aws/ja/ingestion/salesforce-limits">日本語</a>
<a href="https://example.com/limits">external</a></article><script>var x=1</script></html>"""
URL = "https://docs.databricks.com/aws/en/ingestion/salesforce"


def test_page_text_keeps_article_and_marks_headings():
    text, links = docs.page_text(PAGE)
    assert "menu" not in text and "var x" not in text and "​" not in text
    assert "## Limitations" in text and "Formula fields are snapshots." in text


def test_limitation_sections_only():
    sec = docs.limitation_sections(docs.page_text(PAGE)[0])
    assert "No compound fields." in sec and "Create a pipeline" not in sec


def test_limits_links_same_locale_and_host_only():
    _, links = docs.page_text(PAGE)
    assert docs.limits_links(links, URL) == ["https://docs.databricks.com/aws/en/ingestion/salesforce-limits"]


def test_fill_empty_but_hold_replacement_of_curated_text():
    assert docs.decide_limitations("", "No compound fields.", 0.9)[0] == "AUTO"
    assert docs.decide_limitations("—", "No compound fields.", 0.9)[0] == "AUTO"
    assert docs.decide_limitations("Read-only.", "No compound fields.", 0.9)[0] == "HELD"


def test_no_proposal_when_same_empty_or_unsure():
    assert docs.decide_limitations("No compound fields", "no compound fields.", 0.9) is None
    assert docs.decide_limitations("", "", 0.9) is None
    assert docs.decide_limitations("", "Something.", 0.5) is None


def test_link_rules():
    assert docs.decide_link(URL, 200, URL + "/") is None
    assert docs.decide_link(URL, 404, URL)[2] == "HELD"
    assert docs.decide_link(URL, None, URL)[2] == "HELD"
    moved = docs.decide_link(URL, 200, "https://docs.databricks.com/aws/en/ingestion/lakeflow-connect/salesforce")
    assert moved[1:3] == ("https://docs.databricks.com/aws/en/ingestion/lakeflow-connect/salesforce", "AUTO")
    assert docs.decide_link(URL, 200, "https://docs.databricks.com/aws/en/")[2] == "HELD"


def test_parse_answer():
    assert docs.parse_answer('```json\n{"limitations": "A; B", "confidence": 0.8}\n```') == ("A; B", 0.8)
    assert docs.parse_answer('{"limitations": "", "confidence": 0.95}\nThe page lists none.') == ("", 0.95)
    with pytest.raises(ValueError):
        docs.parse_answer("not json")


def test_clean_drops_filler_and_cuts_at_clause_boundary():
    assert docs.clean("Beta availability; no specific size, rate, or region limits documented") == ""
    assert docs.clean("Resource limits detailed in separate rate limits documentation") == ""
    long = "; ".join(f"limit number {i} applies here" for i in range(30))
    out = docs.clean(long)
    assert len(out) <= docs.MAX_LIMITATIONS_CHARS and out.endswith("applies here")
