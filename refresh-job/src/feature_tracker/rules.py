"""Match feed items to tracker features and decide what the weekly job may apply.

Policy (the reason this module exists):
  * The job only moves Axis A (Databricks phase). It never writes TRB status.
  * A change that would make a feature PHI-eligible (it becomes GA while TRB-Approved)
    is HELD for a human to accept. Changes that remove eligibility apply immediately,
    because failing closed is the safe direction.
  * Most feed items announce a capability OF an existing feature ("Lakebase snapshots
    API (Beta)"), not a phase change of it. Those become child features under the
    matched parent. Databricks does not move a GA feature back to Beta, so an apparent
    regression is always treated as a new child.
  * New features (top-level or child) are inserted as Not Reviewed / Low. They cannot
    be PHI-eligible until the TRB acts, so inserting them is safe.
  * Ambiguous deterministic matches and low-confidence LLM matches are HELD.
"""
import re

PHASE_ORDER = ["Upcoming", "Private Preview", "Beta", "Public Preview", "GA", "Deprecated"]
APPROVED = "Approved"  # only full approval counts toward PHI; "with Conditions" does not
LLM_MIN_CONFIDENCE = 0.8
SAME_FEATURE_COVERAGE = 0.85  # "Genie One memory is GA" (0.67) is a child; "Genie One is GA" (1.0) is the feature

STOP = set("""a an and are as at be by for from in into is it its now of on or the to
with will soon available generally general availability ga beta public private preview
supports support supported new can you your this that than via all
regions region workspaces workspace default enabled rolling out""".split())


def norm(s):
    s = re.sub(r"\([^)]*\)", " ", s.lower())  # drop "(cloud + on-prem)" style qualifiers
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def content_words(s):
    return [w for w in norm(s).split() if w not in STOP]


def name_match(title, features, domain_hint=None):
    """Best deterministic match: the longest normalized feature name contained in the
    title as whole words. Returns (feature_key, coverage) where coverage is the share
    of the title's content words accounted for by the feature name, or (None, 0)."""
    t = f" {norm(title)} "
    best, best_len = None, 0
    for f in features:
        n = norm(f["name"])
        if len(n) < 4 or f" {n} " not in t:
            continue
        length = len(n) + (5 if domain_hint and f["domain"] == domain_hint else 0)
        if length > best_len:
            best, best_len = f, length
    if not best:
        return None, 0.0
    tw = content_words(title)
    fw = set(content_words(best["name"]))
    coverage = sum(1 for w in tw if w in fw) / max(1, len(tw))
    return f"{best['name']}@{best['domain']}", round(coverage, 2)


def category_parent(categories, features):
    """Fallback when no feature name appears in the title: a feed category that is
    itself a tracked feature ("Lakeflow Connect", "Lakebase") is the parent."""
    names = {norm(f["name"]): f for f in features if not f.get("parent")}
    for c in categories:
        f = names.get(norm(c))
        if f:
            return f"{f['name']}@{f['domain']}"
    return None


def phi_eligible(phase, trb_status):
    return phase == "GA" and trb_status == APPROVED


def decide(new_phase, feature, trb_status, relation, confidence):
    """Return (change_type, decision, reason).

    relation: "same" (the item is about this feature), "child" (a capability of it),
              or None (no match). confidence: the LLM's confidence; 1.0 for deterministic matches.
    decision: AUTO (the job applies it) or HELD (waits in the triage queue)."""
    if feature is None:
        return "NEW_FEATURE", "AUTO", "new top-level feature, inserted as Not Reviewed / Low"
    old = feature["dbxPhase"]
    regression = (old in PHASE_ORDER and new_phase in PHASE_ORDER
                  and new_phase != "Deprecated"
                  and PHASE_ORDER.index(new_phase) < PHASE_ORDER.index(old))
    if relation == "child" or regression:
        return "NEW_CHILD", "AUTO", f"new {new_phase} capability under '{feature['name']}'"
    if confidence < LLM_MIN_CONFIDENCE:
        return "PHASE_CHANGE", "HELD", f"low-confidence match ({confidence:.2f}); triage"
    if new_phase == old:
        return "CONFIRM", "AUTO", "phase confirmed; last_verified refreshed"
    if not phi_eligible(old, trb_status) and phi_eligible(new_phase, trb_status):
        return "PHASE_CHANGE", "HELD", "would make the feature PHI-eligible; needs platform-team confirmation"
    return "PHASE_CHANGE", "AUTO", f"{old} -> {new_phase}"


def relation_from_coverage(coverage):
    """Deterministic stand-in for the LLM's relation judgement."""
    if coverage >= SAME_FEATURE_COVERAGE:
        return "same"
    return "child"
