#!/usr/bin/env bash
set -euo pipefail
git init -q
mkdir -p work/screenshots
touch work/screenshots/home-app.png work/screenshots/home-figma.png
cat > work/screenshots/checker-output.json <<'JSON'
{
  "screen": "home",
  "figma_node_id": "2:2",
  "criteria": [
    { "aspect": "layout_structure", "verdict": "match", "diff": null },
    { "aspect": "element_presence", "verdict": "minor_diff", "diff": "検索アイコンの種類が異なる" },
    { "aspect": "arrangement_order", "verdict": "match", "diff": null },
    { "aspect": "text_labels", "verdict": "match", "diff": null },
    { "aspect": "state_representation", "verdict": "not_applicable", "diff": null }
  ],
  "overall_verdict": "close_match",
  "fatal": false,
  "fatal_reason": null
}
JSON
