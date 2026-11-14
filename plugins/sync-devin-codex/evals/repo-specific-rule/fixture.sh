#!/usr/bin/env bash
set -euo pipefail
git init -q
mkdir -p .claude
cat > .claude/settings.json <<'JSON'
{
  "permissions": {
    "deny": ["Read(./.env)", "Bash(git push *)", "Bash(sudo *)"]
  }
}
JSON
cat > AGENTS.md <<'MD'
# このリポジトリの方針

- Codex は `.claude/settings.json` の deny をそのまま反映する。
MD
mkdir -p .devin
cat > .devin/global_rules.md <<'MD'
- Devin はリモート環境で動くため、`git push` を使えるようにする(Devin の deny には入れない)。
MD
echo "KEY=dummy" > .env
