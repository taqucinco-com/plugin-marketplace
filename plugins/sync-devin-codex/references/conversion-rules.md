# 変換規則

`scripts/sync.py` が実装している規則。`.claude/` を実体とし、Devin・Codex 側は派生物として扱う。

## skills / agents

- skills: `.devin/skills/<name>` と `.agents/skills/<name>` に `.claude/skills/<name>` へのシンボリックリンクを置く。Devin は `.claude/skills/` も読むが、Codex は `.agents/skills/` だけを検索する。
- agents(Devin): `.devin/agents/<name>.md` に `.claude/agents/<name>.md` へのシンボリックリンクを置く。Devin の subagents は `.devin/agents/` を検索対象とし `.claude/agents/` は対象に含まれない。
- agents(Codex): `.codex/agents/<name>.toml` に変換する。Codex は 1 ファイル 1 エージェントの TOML を要求する。
  1. frontmatter の `name`・`description` を使う。引用符、`>`・`|` の複数行、CRLF に対応する。ファイル名は `<name>.toml`。`name` は `[A-Za-z0-9][A-Za-z0-9._-]*` に限り、`..` を含むものや、他のエージェントと重複するものは警告してスキップする。
  2. 本文を `developer_instructions` に TOML のリテラル複数行文字列(`'''`)で入れる。本文に `'''` が含まれる場合は `"""` に切り替えてエスケープする。
  3. `tools`(カンマ区切り、`[a, b]`、`- a` のリストのいずれも可)が `Read`・`Grep`・`Glob` のみの場合、本文末尾に読み取り専用の注記を追加する。Codex のカスタムエージェントは `sandbox_mode` 等をファイルで上書きできず、読み取り専用の制限は指示文でしか表現できない。それ以外の `tools` は変換先が無いため捨てる。
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
- `Bash(cmd *)` は `Exec(cmd)`。`Exec` は単語単位の前方一致で glob を使えないため、末尾の `*` を落とす。`--force*` のようにトークン末尾に付いた `*` も落とす。旧形式の `Bash(cmd:*)` は `Bash(cmd *)` として扱う。
- `Bash(cat .env*)` のように、ファイル読み取りコマンド(`cat`・`less`・`more`・`head`・`tail`・`bat`)の引数に glob を含むルールは、リポジトリ内で一致する実在ファイルを列挙して `Exec(cat .env)`、`Exec(cat .env.local)` のような完全一致に置き換える。一致するファイルが無い glob は警告して捨てる。この展開は同期時点のスナップショットなので、新しい秘密情報ファイルを追加したらスキルを再実行する。CI で `--check` を実行すると、同期漏れを検知できる(`references/ci-example.yml`)。主な防御はパスのルール(`Read`、Codex の filesystem)で、この展開は補助。対象は上記の読み取りコマンドだけで、`grep`・`cp` などは対象外。
- 上記以外で glob が残るルールは警告してスキップする。
- リポジトリ固有のルール(変換しない deny)は既定の変換より優先する。Devin 向けは `.devin/global_rules.md`(Devin の常時適用ルール。同名の `.windsurf/global_rules.md` より優先される)、Codex 向けと共通のものは `AGENTS.md`・`CLAUDE.md` に明記する。Devin 向けの記述が食い違えば `.devin/global_rules.md` を優先する。`.devin/global_rules.md` はこのスキルが生成も上書きもしない。`--skip-deny '[devin:|codex:]ルール'` で、該当ルールをそのターゲットの生成物から外す(例: `devin:Bash(git push *)`)。ルールは `settings.json` の `permissions.deny` の文字列と完全一致で指定する。
- `settings.json` の他のキーを書き換えない。`.devin/config.json` の `permissions.deny` は `.claude/settings.json` から毎回全置換して生成する。`.devin/config.json` に手で足した deny 項目は、再同期で消える。`permissions` 以外のキーは残す。`.claude/` 側のルールをすべて消すと、`deny` も消える。旧版が作っていた状態ファイル `.devin/.sync-devin-codex.json` は参照せず、あれば再同期時に削除する。

### Codex

- `config.toml`: `[permissions.project.filesystem.":workspace_roots"]` に変換する。`Read`・`Edit`・`Write` のパスはいずれも `"glob" = "deny"` にする。Codex のファイル権限は読み取りと書き込みを分けられず、`deny` は両方を拒否する。先頭の `./` と `**/` を外した形と、`**/` 付きの形を併記する(`**/` 付きの glob はワークスペース直下のファイルに一致しない可能性があるため)。`~` で始まるパスと絶対パスは表現できないため、警告してスキップする。`default_permissions = "project"` も設定する。
- `config.toml` は、`# >>> sync-devin-codex (名前) >>>` で囲んだ区間(`permissions`、`permissions-tables`、`mcp-servers`)だけを管理し、既存の区間はその位置で置き換える。区間の外に、生成するテーブルや `default_permissions` と同じ定義があると、TOML が重複して Codex が設定を読めなくなるため、エラーにして `config.toml` を更新しない。
- `sandbox_mode` と併用できない。`config.toml` に `sandbox_mode` があると `default_permissions` は無視されるため、警告する。
- `.codex/rules/deny.rules`: `Bash(...)` のルールを Starlark の `prefix_rule(..., decision = "forbidden")` に変換する。`pattern` は引数列の完全なトークン単位の前方一致で、`*` を使えないため落とす。`match` と `not_match` の例を付ける(読み込み時に検証される)。ファイル読み取りコマンドの glob は、列挙したファイル名の選択肢(`./` 付きの形も含む)にする。
- 位置を指定しない一致は表現できない(例: `git push origin feature --force` は一致しない)。元の Claude 側のルールも同じ挙動。
- 複数のルールに一致した場合は `forbidden` > `prompt` > `allow` の順で最も厳しい決定が適用される。
- `.claude/` 側に `Bash` のルールが無くなると、生成した `deny.rules`(先頭の注記で判別)は削除する。
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

## 同期の動作
- `--quick`: デフォルトブランチ(`git ls-remote --symref origin HEAD` で決め、`origin` から fetch して最新にする)との共通の祖先から、同期元(`.claude/`・`.mcp.json`・`AGENTS.md`・`CLAUDE.md`・`.devin/global_rules.md`。未コミット・未追跡を含む)に差分が無ければ何もせず終了する。判断できないとき(リモート無し・fetch 失敗など)は通常どおり同期する。生成物の手編集によるずれは検知しない。
- 生成物が `.claude/` から消えた場合の古いリンクは、入力ディレクトリごと消えたときも含めて削除する。`.codex/agents/` に対応する md が無い `.toml` は、報告だけして削除しない。
- `--check` は、内容の差分に加えて、フックの実行ビットの欠落も差分として報告する。
- `settings.json` の `hooks`(Devin は直接読む。Codex へは変換しない)。
