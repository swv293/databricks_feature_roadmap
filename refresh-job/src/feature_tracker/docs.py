"""Monthly documentation check: page text extraction, the LLM prompt, and decision rules.

No Spark import, so tasks and tests share it. A feature's limitations are curated text,
so the job only fills an EMPTY field on its own; replacing curated text is HELD for a
person, like a phase change that would grant PHI eligibility."""
import hashlib
import html
import json
import re
import urllib.parse
from html.parser import HTMLParser

DOCS_HOST = "docs.databricks.com"
LIMIT_WORDS = re.compile(r"limit|restriction|unsupported|not supported|known issue|requirement", re.I)
MAX_PROMPT_CHARS = 7000
MIN_CONFIDENCE = 0.7
MAX_LIMITATIONS_CHARS = 300


class _Article(HTMLParser):
    """Collects the text of <article> (or the whole page if there is none). Headings
    become '## ' lines; links are kept as (href, text)."""

    def __init__(self):
        super().__init__()
        self.depth = 0          # >0 while inside <article>
        self.saw_article = False
        self.skip = 0           # inside <script>/<style>/<nav>
        self.parts, self.all_parts, self.links = [], [], []
        self.heading = False
        self._href = None
        self._link_text = []

    def handle_starttag(self, tag, attrs):
        if tag == "article":
            self.depth += 1
            self.saw_article = True
        if tag in ("script", "style", "nav", "footer"):
            self.skip += 1
        if tag in ("h1", "h2", "h3"):
            self.heading = True
            self._emit("\n## ")
        if tag in ("p", "li", "tr", "br", "div"):
            self._emit("\n")
        if tag == "a":
            self._href, self._link_text = dict(attrs).get("href"), []

    def handle_endtag(self, tag):
        if tag == "article":
            self.depth -= 1
        if tag in ("script", "style", "nav", "footer"):
            self.skip = max(0, self.skip - 1)
        if tag in ("h1", "h2", "h3"):
            self.heading = False
            self._emit("\n")
        if tag == "a" and self._href:
            self.links.append((self._href, "".join(self._link_text).strip()))
            self._href = None

    def handle_data(self, data):
        if self._href is not None:
            self._link_text.append(data)
        self._emit(data)

    def _emit(self, s):
        if self.skip:
            return
        self.all_parts.append(s)
        if self.depth:
            self.parts.append(s)


def page_text(raw_html):
    """(text, links) for a docs page: article text with '## ' headings, zero-width
    characters removed and whitespace collapsed."""
    p = _Article()
    p.feed(raw_html)
    text = "".join(p.parts if p.saw_article else p.all_parts)
    text = html.unescape(text).replace("​", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text).strip()
    return text, p.links


def content_hash(text):
    return hashlib.sha1(text.encode()).hexdigest()[:16]


def limitation_sections(text):
    """Only the sections whose heading mentions limitations, restrictions, or requirements."""
    out, keep = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            keep = bool(LIMIT_WORDS.search(line))
        if keep:
            out.append(line)
    return "\n".join(out)


def limits_links(links, page_url):
    """Docs pages linked from this page that look like a dedicated limitations page,
    e.g. .../salesforce-limits. Same host only, fragments dropped, at most 2."""
    out = []
    locale = urllib.parse.urlparse(page_url).path.split("/")[1:3]   # e.g. ["aws", "en"]
    for href, text in links:
        if not href:
            continue
        url = urllib.parse.urljoin(page_url, href).split("#")[0]
        u = urllib.parse.urlparse(url)
        if u.netloc != DOCS_HOST or url.rstrip("/") == page_url.split("#")[0].rstrip("/"):
            continue
        seg = u.path.split("/")
        # same cloud and language only (drops the /ja/, /pt/ ... translations of the page)
        if seg[1:3] != locale or any(p in ("aws", "azure", "gcp") for p in seg[3:]):
            continue
        if re.search(r"limit", u.path, re.I) or re.search(r"\blimitations?\b", text, re.I):
            if url not in out:
                out.append(url)
    return out[:2]


def evidence(page_text_, limits_pages_text):
    """Text sent to the LLM: dedicated limits pages and limitation sections first, then the
    start of the page for context, capped at MAX_PROMPT_CHARS."""
    parts = [t for t in limits_pages_text if t]
    sec = limitation_sections(page_text_)
    if sec:
        parts.append(sec)
    parts.append(page_text_[:2500])
    return "\n\n".join(parts)[:MAX_PROMPT_CHARS]


PROMPT = """You keep a catalog of Databricks features up to date for a healthcare payer's platform team.
Feature: {name}
Parent feature: {parent}
Current limitations in the catalog: {current}

Below is text from the feature's Databricks documentation ({url}). The page may cover a broader
parent feature; use only statements that apply to "{name}" itself.
---
{text}
---
List the limitations that matter for adopting this feature: unsupported sources or types, size or
rate limits, missing capabilities, region or compute restrictions. Plain text, semicolon-separated,
at most {max_chars} characters, no marketing language. If the page states no limitation specific to
this feature, return an empty string. Answer with JSON only:
{{"limitations": "<text or empty>", "confidence": 0.0-1.0}}"""


def prompt(name, parent, current, url, text):
    return PROMPT.format(name=name, parent=parent or "none", current=current or "(none recorded)",
                         url=url, text=text, max_chars=MAX_LIMITATIONS_CHARS)


def parse_answer(raw):
    """LLM reply -> (limitations, confidence). Raises ValueError on anything malformed."""
    # The model sometimes adds prose after the JSON object; read the first object only.
    start = raw.find("{")
    if start < 0:
        raise ValueError("no JSON object in answer")
    j, _ = json.JSONDecoder().raw_decode(raw[start:])
    lim = (j.get("limitations") or "").strip()
    conf = float(j.get("confidence", 0))
    if not 0 <= conf <= 1:
        raise ValueError(f"confidence out of range: {conf}")
    return lim, conf


def _norm(s):
    return re.sub(r"[\W_]+", " ", (s or "").lower()).strip()


def is_empty(current):
    return _norm(current) == ""   # "", None, and "—" all count as empty


# Clauses that describe the docs instead of stating a limitation ("no specific limits documented").
FILLER = re.compile(r"\bno (specific|explicit|documented)\b|\bnot (documented|specified|stated|listed)\b"
                    r"|\b(detailed|described|documented|listed) (in|on) (a )?separate\b|^see\b|\brefer to\b"
                    # the phase alone is already on the page (Axis A)
                    r"|^(in )?(beta|public preview|private preview|preview)( availability| only| status)?$", re.I)


def clean(limitations):
    """Drop filler clauses and cut at a clause boundary within MAX_LIMITATIONS_CHARS."""
    out = []
    for clause in (c.strip(" .") for c in (limitations or "").split(";")):
        if not clause or FILLER.search(clause):
            continue
        if len("; ".join(out + [clause])) > MAX_LIMITATIONS_CHARS:
            break
        out.append(clause)
    return "; ".join(out)


def decide_limitations(current, proposed, confidence):
    """(decision, reason) for a limitations proposal, or None when there is nothing to propose.
    Call with clean(proposed)."""
    if not proposed or _norm(proposed) == _norm(current):
        return None
    if confidence < MIN_CONFIDENCE:
        return None
    if is_empty(current):
        return "AUTO", "filled empty limitations from the feature's docs"
    return "HELD", "docs differ from curated limitations; a person must accept the replacement"


def decide_link(doc_link, status, final_url):
    """(field, new_value, decision, reason) for a doc link problem, or None if the link is fine.
    A redirect inside docs.databricks.com is applied; a dead link is held for a person."""
    if status is None or status >= 400:
        return "doc_link", "", "HELD", f"doc link failed (HTTP {status}); find the current page"
    if final_url and final_url.rstrip("/") != doc_link.rstrip("/"):
        u = urllib.parse.urlparse(final_url)
        if u.netloc != DOCS_HOST or len([p for p in u.path.split("/") if p]) <= 2:
            # moved off docs, or dumped on a docs landing page: the page is gone
            return "doc_link", "", "HELD", f"doc link redirects to {final_url}; find the current page"
        return "doc_link", final_url, "AUTO", "doc page moved (redirect); link updated"
    return None
