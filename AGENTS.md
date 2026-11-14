# plugin-marketplace (エージェント向けガイド)

Claude Code のプラグインマーケットプレイス用リポジトリ。

## 構成
- `.claude-plugin/marketplace.json`: マーケットプレイス定義(プラグイン一覧)
- `plugins/<name>/`: 各プラグイン。`.claude-plugin/plugin.json` のみ `.claude-plugin/` 内、`skills/` `agents/` `commands/` `hooks/` はプラグイン直下に置く
- `.agents/plugins/marketplace.json`: Codex 用のマーケットプレイス定義(`.claude-plugin/marketplace.json` と同じプラグイン一覧にする)
- `.claude/`: このリポジトリ自体で Claude Code を使うための設定(settings.json, rules/, skills/, agents/, commands/)

## 規約
- プラグイン追加時は `plugins/<name>/` を作り、`marketplace.json` の `plugins` に `source: "./plugins/<name>"` で登録する
- プラグイン追加時は `plugins/<name>/README.md` も作る。何をするプラグインか、提供するもの(スキル・agent・MCP・スクリプト)、使う側に求めること(必須ツール・環境変数・依存プラグイン・実行環境の制約)を書く。手順の詳細は SKILL.md に任せ、重複して書かない。要件や提供するものを変えたら README も直す
- `decide.py` と `normalize-image.sh` は `ui-core-verify`・`pr-ui-evidence`・`maestro-scenario-author` に同じものを置く(プラグインは互いのファイルを参照できないため)。変更したら 3 か所を揃える。`python3 -m unittest discover -s plugins/ui-core-verify/tests` が同一かを確認する
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
- Codex プラグインの構成(`.mcp.json`・`.codex-plugin/plugin.json` など)は OpenAI の公式ドキュメント(https://developers.openai.com/plugins/build/plugins#plugin-creator-output)を参照する。プラグイン直下の `.mcp.json` は Codex 互換の形式で、ポータブル形式の `mcp.json` とは別物なのでリネームだけで流用しない
- スキル本文では `${CLAUDE_PLUGIN_ROOT}` に頼らず、SKILL.md からの相対パスで資材を参照する
- プラグイン直下に `.mcp.json` を置くプラグインは、`.codex-plugin/plugin.json` にも `"mcpServers": "./.mcp.json"` を書く(`skills` だけだと Codex は MCP サーバーを登録しない)。SKILL.md に「Codex・Devin では MCP が使えない」と書かない。プラグイン追加・MCP 追加時は、`.mcp.json` と Codex マニフェストの `mcpServers` が揃っているか確認する
- プラグイン同梱の MCP ツール名は `mcp__plugin_<プラグイン名>_<サーバー名>__<ツール名>`(例: `mcp__plugin_ui-core-verify_figma__get_figma_data`)。SKILL.md には `mcp__<サーバー名>__...` と書かず、この形で書く
- `.codex/`(sync-devin-codex の生成物)は `.gitignore` 済み。コミットしない
- MCP サーバーはプラグイン直下の `.mcp.json`(`mcpServers`)に宣言する。書き方は Devin の公式ドキュメント(https://docs.devin.ai/product-guides/plugin-mcp-setups#the-declaration)を参照する
- `devin plugins install/list/info` はログイン(`devin auth login`)が必須で、未認証では動かない。Devin のプラグイン検証は CI に入れず、手元で `devin plugins install --local ./plugins/<name>` を実行して確認する
