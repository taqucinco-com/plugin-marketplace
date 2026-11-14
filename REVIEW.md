# Review ガイドライン

このリポジトリは Claude Code プラグインのマーケットプレイスです。レビューでは以下を確認してください。

## 必須チェック
- `.claude-plugin/marketplace.json` の `plugins[].name` と、各プラグインの `plugin.json` の `name` が一致している
- `source` が `./` で始まり、`..` を含まない。参照先ディレクトリが実在する
- `plugin.json` 以外(skills/agents/commands/hooks)が `.claude-plugin/` の中に置かれていない
- 新規プラグインが `.claude-plugin/marketplace.json` と `.agents/plugins/marketplace.json` の両方に登録され、`.devin-plugin/plugin.json`(リンク)と `.codex-plugin/plugin.json` がある
- `.codex-plugin/plugin.json` の `name`・`version` が `.claude-plugin/plugin.json` と一致している
- `.mcp.json` を持つプラグインは、`.codex-plugin/plugin.json` に `"mcpServers": "./.mcp.json"` がある
- `claude plugin validate .` がエラーなしで通る(CI でも確認)

## プラグイン内容
- SKILL.md の `description` が、いつ使うかを具体的に説明している
- hooks やスクリプトに、秘密情報のハードコード、危険なコマンド(破壊的操作、外部への無断送信)がない
- 変更したプラグインは `plugin.json` の `version` を更新している

## 指摘しなくてよいこと
- 文言や書式の好みだけの指摘
- 生成物・ロックファイルの差分
