#!/usr/bin/env bash
set -euo pipefail
git init -q
mkdir -p .claude src/generated
cat > .claude/settings.json <<'JSON'
{
  "permissions": {
    "deny": ["Read(./.env)", "Edit(./secrets/**)", "Write(src/generated/**)"]
  }
}
JSON
echo "KEY=dummy" > .env
