---
type: regex
target: { source: file, path: .codex/config.toml }
pattern: '"src/generated/\*\*"\s*=\s*"deny"'
arm: both
---
