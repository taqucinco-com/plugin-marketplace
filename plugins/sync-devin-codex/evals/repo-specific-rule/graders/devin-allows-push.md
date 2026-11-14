---
type: regex
target: { source: file, path: .devin/config.json }
pattern: 'git push'
match: not_contains
arm: both
---
