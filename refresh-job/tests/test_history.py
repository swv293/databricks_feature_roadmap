import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from feature_tracker import history  # noqa: E402

ROW = {"run_date": "2026-10-12", "run_id": 1, "change_type": "NEW_CHILD", "new_feature_name": "Pipeline parameters",
       "feature_key": "Lakeflow Declarative Pipelines (DLT)@Pipelines & Data Engineering", "domain": "Pipelines & Data Engineering",
       "old_phase": None, "new_phase": "GA", "decision": "APPLIED", "title": "t", "link": "https://docs.databricks.com/x",
       "pub_date": "2026-10-12"}


def test_groups_by_date_newest_first_and_counts_runs():
    rows = [ROW, {**ROW, "run_id": 2, "change_type": None},
            {"run_date": "2026-10-13", "run_id": 3, "change_type": None}]
    h = history.group(rows)
    assert [e["date"] for e in h] == ["2026-10-13", "2026-10-12"]
    assert h[0] == {"date": "2026-10-13", "runs": 1, "changes": []}
    assert h[1]["runs"] == 2 and len(h[1]["changes"]) == 1


def test_child_names_parent_and_phase_change_names_feature():
    child = history.group([ROW])[0]["changes"][0]
    assert (child["name"], child["parent"], child["decision"]) == (
        "Pipeline parameters", "Lakeflow Declarative Pipelines (DLT)", "applied")
    pc = history.group([{**ROW, "change_type": "PHASE_CHANGE", "new_feature_name": None,
                         "feature_key": "Lakebase (Postgres OLTP)@Storage & Formats", "old_phase": "Public Preview",
                         "decision": "HELD"}])[0]["changes"][0]
    assert (pc["name"], pc["parent"], pc["old"], pc["decision"]) == (
        "Lakebase (Postgres OLTP)", "", "Public Preview", "held for sign-off")


def test_current_run_is_optional_in_sql():
    assert "SELECT 42," not in history.sql("c.s")
    assert "SELECT 42," in history.sql("c.s", 42)
