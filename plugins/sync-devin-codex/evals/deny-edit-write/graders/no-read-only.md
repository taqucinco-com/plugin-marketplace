---
type: regex
target: { source: file, path: .codex/config.toml }
pattern: '=\s*"read"'
match: not_contains
arm: both
---
