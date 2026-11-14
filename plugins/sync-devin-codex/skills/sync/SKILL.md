---
name: sync
description: Claude Code の .claude/ 配下(skills・agents・rules・settings.json の permissions.deny・.mcp.json)を Devin と Codex 用の設定へ変換・同期する。.claude/ を変更した後や、リポジトリを Devin・Codex に対応させたいとき、同期の差分を確認したいときに使う。
argument-hint: "[--check] [--target devin|codex|all]"
---

`.claude/` を実体(正)として、Devin(`.devin/`)と Codex(`.codex/`、`.agents/`)の設定を派生させる。Claude Code 側の設定は Devin・Codex のために変更しない。

## 手順

変換スクリプトは、このファイルから見て `../../scripts/sync.py`(プラグインルートの `scripts/sync.py`)にある。以下では、その絶対パスを `<sync.py>` と書く。Claude Code では `${CLAUDE_PLUGIN_ROOT}/scripts/sync.py` と同じ。Codex・Devin ではこのファイルの場所から解決する。

1. リポジトリのルートで、先に差分を確認する。

   ```
   python3 -I <sync.py> --check $ARGUMENTS
   ```

2. 出力の `警告:` を確認する。変換できなかったルール(表現できない glob、別名の環境変数参照など)が書かれている。内容を要約してユーザーに伝える。
3. 差分があれば、`--check` を外して実行し、書き込む。

   ```
   python3 -I <sync.py> $ARGUMENTS
   ```

4. `git status` と `git diff` で生成物を確認し、変更内容をユーザーに報告する。コミットはユーザーが求めたときだけ行う。

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
- CI で同期漏れを検知するには、`python3 -I <sync.py> --check` を実行する(例: `references/ci-example.yml`)。
