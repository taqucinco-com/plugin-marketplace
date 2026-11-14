# plugin-marketplace

Claude Code のプラグインマーケットプレイス。

## 使い方
```
/plugin marketplace add <owner>/plugin-marketplace
/plugin install hello-plugin@plugin-marketplace
```
ローカルでは `claude plugin marketplace add ./` で追加できます。

### Codex
```
codex plugin marketplace add <owner>/plugin-marketplace
codex plugin add sync-devin-codex@plugin-marketplace
```
Codex 用の定義は `.agents/plugins/marketplace.json` と各プラグインの `.codex-plugin/plugin.json`。

### Devin
各プラグインは `.devin-plugin/plugin.json`(`.claude-plugin/plugin.json` へのシンボリックリンク)を持つ。
```
devin plugins install <owner>/plugin-marketplace#plugins/sync-devin-codex
devin plugins install --local ./plugins/sync-devin-codex   # ローカル確認
```
Devin は `marketplace.json` を読まず、プラグイン単位でインストールする。

## プラグイン
| 名前 | 内容 |
|---|---|
| `sync-devin-codex` | `.claude/` の skills・agents・rules・permissions・MCP を Devin と Codex 用に変換・同期する(`/sync-devin-codex:sync`) |
