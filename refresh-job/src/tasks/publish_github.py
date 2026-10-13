"""Task 6: commit the freshly built page to the GitHub Pages branch.

The Pages branch holds only index.html (+ .nojekyll), so nothing else in the repo
is served. Auth is a fine-grained GitHub token (Contents: read/write on this one
repo) stored in a Databricks secret. If the secret is missing, the task skips
without failing, so the volume copy from publish_site is still the record."""
import sys
sys.path.insert(0, sys.argv[sys.argv.index("--src") + 1])

import base64  # noqa: E402
import datetime as dt  # noqa: E402
import json  # noqa: E402
import pathlib  # noqa: E402
import urllib.error  # noqa: E402
import urllib.request  # noqa: E402

from databricks.sdk import WorkspaceClient  # noqa: E402

from feature_tracker.common import args  # noqa: E402

a = args({"--github-repo": {"required": True}, "--pages-branch": {"default": "gh-pages"},
          "--secret-scope": {"required": True}, "--secret-key": {"required": True}})


# Not sys.exit(): Databricks runs this file in a notebook kernel, where SystemExit
# (even with code 0) marks the task as failed.
def main():
    if not a.github_repo:
        print("SKIPPED: github_repo is not set. The page is still published to the volume.")
        return
    try:
        token = base64.b64decode(WorkspaceClient().secrets.get_secret(a.secret_scope, a.secret_key).value).decode()
    except Exception as e:
        print(f"SKIPPED: no GitHub token in secret {a.secret_scope}/{a.secret_key} ({type(e).__name__}). "
              "The page is still published to the volume.")
        return

    api = f"https://api.github.com/repos/{a.github_repo}/contents/index.html"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "databricks-feature-tracker"}

    def call(method, url, body=None):
        req = urllib.request.Request(url, method=method, headers=headers,
                                     data=json.dumps(body).encode() if body else None)
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())

    page = pathlib.Path(f"/Volumes/{a.catalog}/{a.schema}/site/index.html").read_bytes()
    try:
        current = call("GET", f"{api}?ref={a.pages_branch}")
        sha = current["sha"]
        if base64.b64decode(current["content"]) == page:
            print("GitHub Pages already up to date; no commit")
            return
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        sha = None

    body = {"message": f"Weekly refresh {dt.date.today().isoformat()} (run {a.run_id})",
            "content": base64.b64encode(page).decode(), "branch": a.pages_branch}
    if sha:
        body["sha"] = sha
    res = call("PUT", api, body)
    print(f"committed {res['commit']['sha'][:7]} to {a.github_repo}@{a.pages_branch}")


main()
