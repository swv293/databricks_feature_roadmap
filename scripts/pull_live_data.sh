#!/usr/bin/env bash
# Bring data/ and index.html to parity with the live page: download the exact JSON the
# last publish_site run built from, rebuild, and compare with the published page.
#
#   scripts/pull_live_data.sh <profile> [catalog] [schema]
#
# catalog defaults to "catalog" in .databricks/bundle/dev/variable-overrides.json.
# data/features.json is also the seed for ensure_tables, so after a pull a fresh
# deployment starts from the current catalog instead of the original seed.
set -euo pipefail
PROFILE=${1:?usage: scripts/pull_live_data.sh <profile> [catalog] [schema]}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OVR="$ROOT/.databricks/bundle/dev/variable-overrides.json"
CATALOG=${2:-$( [ -f "$OVR" ] && python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("catalog",""))' "$OVR" || true )}
CATALOG=${CATALOG:?pass the catalog, or set it in .databricks/bundle/dev/variable-overrides.json}
SCHEMA=${3:-feature_tracker}
SRC="dbfs:/Volumes/$CATALOG/$SCHEMA/site"

for f in domains features feed meta trb_questions history; do
  databricks fs cp --overwrite --profile "$PROFILE" "$SRC/data/$f.json" "$ROOT/data/$f.json"
done
python3 "$ROOT/scripts/build_site.py"

tmp=$(mktemp)
databricks fs cp --overwrite --profile "$PROFILE" "$SRC/index.html" "$tmp"
if cmp -s "$tmp" "$ROOT/index.html"; then
  echo "parity: index.html matches the published page"
else
  echo "NOT in parity: index.html differs from $SRC/index.html (template or builder not deployed?)" >&2
  rm -f "$tmp"; exit 1
fi
rm -f "$tmp"
