---
paths:
  - "plugins/**"
  - ".claude-plugin/**"
---

- プラグインのマニフェストは `<plugin>/.claude-plugin/plugin.json`。skills/agents/commands/hooks をその中に入れない。
- `marketplace.json` の `source` は `./` で始め、`..` を含めない。
