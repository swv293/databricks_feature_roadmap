"""Shared argument parsing and Spark helpers for the job's tasks."""
import argparse

from pyspark.sql import SparkSession


def args(extra=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="refresh-job/src in the deployed bundle")
    ap.add_argument("--bundle-root", required=True)
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--schema", required=True)
    ap.add_argument("--trb-schema", required=True)
    ap.add_argument("--run-id", required=True, type=int)
    for name, kw in (extra or {}).items():
        ap.add_argument(name, **kw)
    a = ap.parse_args()
    a.fq = f"{a.catalog}.{a.schema}"
    a.trb = f"{a.catalog}.{a.trb_schema}"
    return a


def spark():
    return SparkSession.builder.getOrCreate()


def table_exists(s, fq_name):
    return s.catalog.tableExists(fq_name)


def trb_status_by_key(s, a):
    """Current TRB status per feature_key: the latest trb.reviews row if the TRB
    tables exist, otherwise the seed value carried on the features table."""
    seed = {r.feature_key: r.seed_trb_status or "Not Reviewed"
            for r in s.sql(f"SELECT feature_key, seed_trb_status FROM {a.fq}.features").collect()}
    if table_exists(s, f"{a.trb}.reviews"):
        rows = s.sql(f"""
            SELECT feature_key, current_trb_status FROM {a.trb}.reviews
            QUALIFY row_number() OVER (PARTITION BY feature_key ORDER BY latest_review_date DESC) = 1
        """).collect()
        seed.update({r.feature_key: r.current_trb_status for r in rows})
    return seed


def trb_questions_by_key(s, a):
    """Open TRB questions per feature_key from the latest trb.reviews row, in the
    shape build_site.py reads from data/trb_questions.json."""
    if not table_exists(s, f"{a.trb}.reviews"):
        return {}
    rows = s.sql(f"""
        SELECT feature_key, review_id, open_questions FROM {a.trb}.reviews
        QUALIFY row_number() OVER (PARTITION BY feature_key ORDER BY latest_review_date DESC) = 1
    """).collect()
    out = {}
    for r in rows:
        qs = [q.strip() for q in (r.open_questions or "").split("; ") if q.strip()]
        if qs:
            out[r.feature_key] = {"review": r.review_id, "questions": qs}
    return out
