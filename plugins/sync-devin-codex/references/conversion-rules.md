# 変換規則

`scripts/sync.py` が実装している規則。`.claude/` を実体とし、Devin・Codex 側は派生物として扱う。

## skills / agents

- skills: `.devin/skills/<name>` と `.agents/skills/<name>` に `.claude/skills/<name>` へのシンボリックリンクを置く。Devin は `.claude/skills/` も読むが、Codex は `.agents/skills/` だけを検索する。
- agents(Devin): `.devin/agents/<name>.md` に `.claude/agents/<name>.md` へのシンボリックリンクを置く。Devin の subagents は `.devin/agents/` を検索対象とし `.claude/agents/` は対象に含まれない。
- agents(Codex): `.codex/agents/<name>.toml` に変換する。Codex は 1 ファイル 1 エージェントの TOML を要求する。
  1. frontmatter の `name`・`description` をそのまま使う。ファイル名は `<name>.toml`。
  2. 本文を `developer_instructions` に TOML のリテラル複数行文字列(`'''`)で入れる。本文に `'''` が含まれる場合は `"""` に切り替えてエスケープする。
  3. `tools` が `Read`・`Grep`・`Glob` のみの場合、本文末尾に読み取り専用の注記を追加する。Codex のカスタムエージェントは `sandbox_mode` 等をファイルで上書きできず、読み取り専用の制限は指示文でしか表現できない。それ以外の `tools` は変換先が無いため捨てる。
  4. `model` 等の任意キーは設定しない。

## rules

- Devin: `.claude/rules/` を読むか未確認のため対応しない。Devin にも必要な指示は `AGENTS.md` に書く。
- Codex: `.codex/hooks.json` の SessionStart フックで `.codex/hooks/load-claude-rules.sh` を実行し、`.claude/rules/**/*.md` の本文を開発者コンテキストとして注入する。`paths` 付きのルールには、`paths` をカンマ区切り 1 行にして「適用対象パス」として添える。`paths` 以外の frontmatter は出力しない。
- `AGENTS.md` への `@` 取り込みや `AGENTS.override.md` は使わない(Claude Code が `AGENTS.md` も読むため二重になる)。
- フックは初回に `/hooks` でレビュー・信頼が必要で、変更するとハッシュが変わり再レビューまでスキップされる。出力が既定約 2,500 トークンを超えるため `additionalContextLimit` を 20000 にしている。
- `hooks.json` と `config.toml` のインライン `[hooks]` を併用すると警告が出るため、`config.toml` には `[hooks]` を書かない。

## permissions.deny

`.claude/settings.json` の `permissions.deny` が入力。

### Devin(`.devin/config.json`)

- `Read(glob)` はそのまま `Read(glob)`。
- `Edit(glob)`・`Write(glob)` は `Write(glob)` に統合し、重複を除く(Devin に `Edit` 相当が無い)。
- `Bash(cmd *)` は `Exec(cmd)`。`Exec` は単語単位の前方一致で glob を使えないため、末尾の `*` を落とす。`--force*` のようにトークン末尾に付いた `*` も落とす。
- `Bash(cat .env*)` のように、ファイル読み取りコマンド(`cat`・`less`・`more`・`head`・`tail`・`bat`)の引数に glob を含むルールは、リポジトリ内で一致する実在ファイルを列挙して `Exec(cat .env)`、`Exec(cat .env.local)` のような完全一致に置き換える。一致するファイルが無い glob は警告して捨てる。新しい秘密情報ファイルを追加したらスキルを再実行する。
- 上記以外で glob が残るルールは警告してスキップする。
- `settings.json` の他のキーを書き換えない。`.devin/config.json` の `permissions.deny` だけを置き換える。

### Codex

- `config.toml`: `Read`・`Edit`・`Write` のパスを `[permissions.project.filesystem.":workspace_roots"]` に `"glob" = "deny"` として統合する(Codex は読み取りも書き込みも拒否し、操作ごとに分けられない)。先頭の `./` と `**/` を外した形と、`**/` 付きの形を併記する(`**/` 付きの glob はワークスペース直下のファイルに一致しない可能性があるため)。`default_permissions = "project"` も設定する。
- `sandbox_mode` と併用できない。`config.toml` に `sandbox_mode` があると `default_permissions` は無視されるため、警告する。
- `.codex/rules/deny.rules`: `Bash(...)` のルールを Starlark の `prefix_rule(..., decision = "forbidden")` に変換する。`pattern` は引数列の完全なトークン単位の前方一致で、`*` を使えないため落とす。`match` と `not_match` の例を付ける(読み込み時に検証される)。ファイル読み取りコマンドの glob は、列挙したファイル名の選択肢(`./` 付きの形も含む)にする。
- 位置を指定しない一致は表現できない(例: `git push origin feature --force` は一致しない)。元の Claude 側のルールも同じ挙動。
- 複数のルールに一致した場合は `forbidden` > `prompt` > `allow` の順で最も厳しい決定が適用される。
- 確認: `codex execpolicy check --pretty --rules .codex/rules/deny.rules -- <コマンド>`。シェルのラッパー(`bash -lc`)は分割されないため、実行時とは異なる。変更後は Codex を再起動する。rules は実験的機能で、プロジェクトの `.codex/` が信頼済みの場合のみ読み込まれる。

## MCP(`.mcp.json`)

- Devin: `.devin/mcp_config.json` に `.mcp.json` へのリンクを置く。Devin CLI は `.mcp.json` も直接読むことを確認済みだが、`env` の `${VAR}` 展開は未確認のため専用ファイル側にも置く。
- Codex: `.mcp.json` を読まないため、`config.toml` の `[mcp_servers.<name>]` に変換する。
  - `command`・`args` はそのまま。`url` のサーバーは `url` に変換する(`headers` は変換できないため警告する)。
  - `env` の値が同名の環境変数への参照(`"K": "${K}"`)なら `env_vars = ["K"]` にする。Codex に `${VAR}` 展開の記載は無い。
  - リテラル値は `[mcp_servers.<name>.env]` に置く。秘密情報はコミットしない。
  - 別名の参照(`"A": "${B}"`)は変換できないため警告する。
- 確認: `codex mcp list`。

## 未確認の点

- Devin: `.claude/rules/` を読むか、`.mcp.json` の `env` の `${VAR}` 展開、クラウド版が `.mcp.json` を読むか。
- Codex: プロジェクトの `config.toml` の MCP が `~/.codex/config.toml` とどうマージされるか、`prefix_rule` が `bash -lc` 経由で期待どおり評価されるか。

## 変換しないもの

- `.claude/settings.ci.json` など CI 専用の設定と、それが参照する hooks。
- `settings.json` の `hooks`(Devin は直接読む。Codex へは変換しない)。
