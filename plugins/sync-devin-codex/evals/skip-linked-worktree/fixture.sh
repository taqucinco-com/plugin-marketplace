#!/usr/bin/env bash
set -euo pipefail
git init -q
mkdir -p .claude wt
cat > .claude/settings.json <<'JSON'
{
  "permissions": {
    "deny": ["Bash(cat .env*)", "Bash(cat **/.env*)"]
  }
}
JSON
echo "A=1" > .env
echo "A=1" > .env.sample
# linked worktree は .git が「ファイル」になっている
echo "gitdir: ../.git/worktrees/wt" > wt/.git
echo "B=2" > wt/.env.sample
