---
name: sync
description: Claude Code の .claude/ 配下(skills・agents・rules・settings.json の permissions.deny・.mcp.json)を Devin と Codex 用の設定へ変換・同期する。.claude/ を変更した後や、リポジトリを Devin・Codex に対応させたいとき、同期の差分を確認したいときに使う。
argument-hint: "[--check] [--quick] [--target devin|codex|all]"
---

`.claude/` を実体(正)として、Devin(`.devin/`)と Codex(`.codex/`、`.agents/`)の設定を派生させる。Claude Code 側の設定は Devin・Codex のために変更しない。

## 省力モード(`--quick`)

`--quick` を付けると、`sync.py` がデフォルトブランチを **fetch して最新にしてから**(リモートの `HEAD` を問い合わせてブランチ名を決めるので、ローカルの `origin/HEAD` が古くてもよい)、同期元(`.claude/`・`.mcp.json`・`AGENTS.md`・`CLAUDE.md`・`.devin/global_rules.md`)がデフォルトブランチとの共通の祖先から変わっているかを調べる。未コミットの変更と未追跡ファイルも含む。

- 変更が無ければ「同期を省略しました」と出力して終了する。**このとき手順の 1・3〜5 は行わない**(変換も報告も要らない)。その旨だけユーザーに伝える。
- 変更があれば、通常どおり下の手順を続ける。
- リモートが無い・fetch に失敗した・デフォルトブランチを特定できないときは、安全側に倒して通常どおり同期する(理由が出力される)。
- 生成物を手で編集した場合や、このプラグインの更新で出力形式が変わった場合は、同期元に変更が無くてもずれる。**確実に確認したいときは `--quick` を付けない**。省略した結果を「生成物が最新」と断定しない(「同期元に変更が無い」とだけ言う)。

## 手順

変換スクリプトは、このファイルから見て `../../scripts/sync.py`(プラグインルートの `scripts/sync.py`)にある。以下では、その絶対パスを `<sync.py>` と書く。Claude Code では `${CLAUDE_PLUGIN_ROOT}/scripts/sync.py` と同じ。Codex・Devin ではこのファイルの場所から解決する。

1. リポジトリ固有の同期ルール(変換しない deny ルールなど)が書かれていないか読む。書かれていれば、このスキルの既定の変換よりそちらを優先する。読む場所は次のとおり。
   - Devin 向け: `.devin/global_rules.md`(Devin が常時読み込むファイル。手書きで、このスキルは生成も上書きもしない)。`AGENTS.md`・`CLAUDE.md` に Devin 向けの記述があっても、`.devin/global_rules.md` と食い違えば `.devin/global_rules.md` を優先する。
   - Codex 向け、および両方に共通: `AGENTS.md`・`CLAUDE.md`。

   たとえば「Devin では git push を拒否しない」とあれば、該当の deny ルールを `--skip-deny 'devin:Bash(git push *)'` で変換対象から外す(ターゲットの接頭辞を省くと両方から外れる。`--skip-deny` は繰り返し指定できる)。以降の `--check` と書き込みのコマンドには、同じ `--skip-deny` を付ける。リポジトリ側に指定が無ければ、何も付けない。
2. リポジトリのルートで、先に差分を確認する。

   ```
   python3 -I <sync.py> --check $ARGUMENTS
   ```

3. 出力の `警告:` を確認する。変換できなかったルール(表現できない glob、別名の環境変数参照など)が書かれている。内容を要約してユーザーに伝える。
4. 差分があれば、`--check` を外して実行し、書き込む。

   ```
   python3 -I <sync.py> $ARGUMENTS
   ```

5. `git status` と `git diff` で生成物を確認し、変更内容をユーザーに報告する。コミットはユーザーが求めたときだけ行う。

## 生成されるもの

| `.claude/` の実体 | Devin | Codex |
|---|---|---|
| `skills/<name>/` | `.devin/skills/<name>`(リンク) | `.agents/skills/<name>`(リンク) |
| `agents/<name>.md` | `.devin/agents/<name>.md`(リンク) | `.codex/agents/<name>.toml`(変換) |
| `rules/*.md` | 対応なし(必要な指示は `AGENTS.md` に書く) | `.codex/hooks.json` の SessionStart フックで注入 |
| `settings.json` の `permissions.deny` | `.devin/config.json` | `.codex/config.toml` と `.codex/rules/deny.rules` |
| `.mcp.json` | `.devin/mcp_config.json`(リンク) | `.codex/config.toml` の `[mcp_servers.*]` |

生成物は手で編集しない。`.claude/` を変更したらこのスキルを実行し直す。`.claude/settings.ci.json` など CI 専用の設定は変換しない。変換規則の詳細と未確認の点は `../../references/conversion-rules.md` を読む。

## 注意

- `.codex/config.toml` は、`# >>> sync-devin-codex` で囲んだ区間だけを管理する。区間の外に書いた設定は残る。区間内を手で編集しない。
- 同名の実ファイルがある場所にはリンクを作らず、報告だけする。
- Codex の hooks は初回に `/hooks` でレビュー・信頼が必要。プロジェクトの `.codex/` は信頼済みの場合のみ読み込まれる。
- `.codex/config.toml` に、生成するテーブルと重複する定義があるとエラーになり、`config.toml` は更新されない。出力に従って手書きの定義を整理する。
- `Bash(cat .env*)` のような glob は、同期時点で存在するファイルに展開される。新しい秘密情報ファイルを足したら再同期する。
- リポジトリ固有のルールで変換しない deny は、Devin 向けは `.devin/global_rules.md`、それ以外は `AGENTS.md` などに、そのコマンド(`--skip-deny` 付き)ごと書いておく。次回以降もエージェントが同じ指定で同期できる。
- CI で同期漏れを検知するには、`--skip-deny` も含めて同じ引数で `python3 -I <sync.py> --check` を実行する(例: `references/ci-example.yml`)。
