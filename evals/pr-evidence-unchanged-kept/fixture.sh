#!/usr/bin/env bash
set -euo pipefail
git init -q
mkdir -p work/pr-evidence/12
touch work/pr-evidence/12/home_before.png work/pr-evidence/12/home_after.png
cat > work/pr-evidence/12/decision-home.json <<'JSON'
{
  "summary": { "next": "unchanged", "reason": "unchanged" },
  "answers": [
    { "name": "changed", "type": "predicate", "value": 0.03 },
    { "name": "same_screen", "type": "predicate", "value": 1.0 }
  ]
}
JSON
