---
type: regex
target: { source: file, path: .codex/config.toml }
pattern: '"secrets/\*\*"\s*=\s*"deny"'
arm: both
---
