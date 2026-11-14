# plugin-marketplace (エージェント向けガイド)

Claude Code のプラグインマーケットプレイス用リポジトリ。

## 構成
- `.claude-plugin/marketplace.json`: マーケットプレイス定義(プラグイン一覧)
- `plugins/<name>/`: 各プラグイン。`.claude-plugin/plugin.json` のみ `.claude-plugin/` 内、`skills/` `agents/` `commands/` `hooks/` はプラグイン直下に置く
- `.agents/plugins/marketplace.json`: Codex 用のマーケットプレイス定義(`.claude-plugin/marketplace.json` と同じプラグイン一覧にする)
- `.claude/`: このリポジトリ自体で Claude Code を使うための設定(settings.json, rules/, skills/, agents/, commands/)

## 規約
- プラグイン追加時は `plugins/<name>/` を作り、`marketplace.json` の `plugins` に `source: "./plugins/<name>"` で登録する
- `plugin.json` の `name` は `marketplace.json` のエントリ名と一致させる(kebab-case)
- 変更後は `claude plugin validate .` で検証する

## レビュー
- レビュー観点は `REVIEW.md` を参照
- CI(`.github/workflows/validate.yml`)で `claude plugin validate` が実行される
- evals は CI では実行せず、ローカルだけで実行する。実行コマンドは `CONTRIBUTING.md` を参照

## Devin 対応
- 各プラグインは `.devin-plugin/plugin.json` を `.claude-plugin/plugin.json` へのシンボリックリンクとして持つ。プラグイン追加時はリンクも作る(`ln -s ../.claude-plugin/plugin.json plugins/<name>/.devin-plugin/plugin.json`)
- Devin の `name` は小文字英数字と単一の `-` `.` のみ

## Codex 対応
- 各プラグインは `.codex-plugin/plugin.json`(実ファイル。`skills` に `./skills/` を指定)を持つ。`name`・`version` は `.claude-plugin/plugin.json` と一致させる
- プラグイン追加時は `.agents/plugins/marketplace.json` にも登録する(`source` は `{"source": "local", "path": "./plugins/<name>"}`)
- スキル本文では `${CLAUDE_PLUGIN_ROOT}` に頼らず、SKILL.md からの相対パスで資材を参照する
- `devin plugins install/list/info` はログイン(`devin auth login`)が必須で、未認証では動かない。Devin のプラグイン検証は CI に入れず、手元で `devin plugins install --local ./plugins/<name>` を実行して確認する
