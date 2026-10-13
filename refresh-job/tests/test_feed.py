import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from feature_tracker import feed  # noqa: E402

# One item from the Azure feed (learn.microsoft.com/en-us/azure/databricks/feed.xml), 2026-10-13.
AZURE = b"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><title>Azure Databricks Release Notes</title>
<item>
  <title><![CDATA[Workspace-level package repositories for Databricks Apps will soon be available by default for workspaces with the compliance security profile enabled]]></title>
  <link>https://learn.microsoft.com/azure/databricks/release-notes/whats-coming#workspace-level-package-repositories</link>
  <guid>https://learn.microsoft.com/azure/databricks/release-notes/whats-coming#workspace-level-package-repositories</guid>
  <pubDate>Wed, 14 Oct 2026 00:00:00 GMT</pubDate>
  <description><![CDATA[<p>Starting November 13, 2026, workspace-level package repositories for Databricks Apps will be
  automatically enabled for workspaces with the <a href="/azure/databricks/security/privacy/security-profile">compliance
  security profile</a> enabled.</p>]]></description>
  <category>Product</category><category>Databricks Apps</category><category>whatscoming</category>
</item>
</channel></rss>"""


def test_parses_azure_feed_item():
    [i] = feed.parse_feed(AZURE)
    assert i["guid"].startswith("https://learn.microsoft.com/azure/databricks/")
    assert str(i["pub_date"]) == "2026-10-14"
    assert i["categories"] == ["Product", "Databricks Apps", "whatscoming"]
    assert "<" not in i["description"] and "compliance security profile" in i["description"]
    assert feed.detect_phase(i["title"], i["description"], i["categories"]) == "Upcoming"
    assert feed.map_domain(i["categories"]) == "Apps & Developer Tools"
