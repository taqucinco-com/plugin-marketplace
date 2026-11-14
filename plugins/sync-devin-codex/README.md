# sync-devin-codex

Claude Code の `.claude/` 配下の設定(skills・agents・rules・`settings.json` の `permissions.deny`・`.mcp.json`)を、Devin と Codex 用の設定へ変換・同期するプラグイン。`.claude/` を実体(正)として、Devin(`.devin/`)と Codex(`.codex/`、`.agents/`)の設定を派生させる。Claude Code 側の設定は、Devin・Codex のために変更しない。

提供するもの:
- スキル: `sync`([SKILL.md](skills/sync/SKILL.md))。`/sync-devin-codex:sync` として呼べる
- スクリプト: [scripts/sync.py](scripts/sync.py)(変換の本体。標準ライブラリのみ)
- 資材: [references/conversion-rules.md](references/conversion-rules.md)(変換規則と未確認の点)、[references/ci-example.yml](references/ci-example.yml)(同期漏れを検知する CI の例)、[assets/load-claude-rules.sh](assets/load-claude-rules.sh)(Codex の SessionStart フックが `rules` を注入するスクリプト)

## 生成されるもの

| `.claude/` の実体 | Devin | Codex |
|---|---|---|
| `skills/<name>/` | `.devin/skills/<name>`(リンク) | `.agents/skills/<name>`(リンク) |
| `agents/<name>.md` | `.devin/agents/<name>.md`(リンク) | `.codex/agents/<name>.toml`(変換) |
| `rules/*.md` | 対応なし(必要な指示は `AGENTS.md` に書く) | `.codex/hooks.json` の SessionStart フックで注入 |
| `settings.json` の `permissions.deny` | `.devin/config.json` | `.codex/config.toml` と `.codex/rules/deny.rules` |
| `.mcp.json` | `.devin/mcp_config.json`(リンク) | `.codex/config.toml` の `[mcp_servers.*]` |

生成物は手で編集しない。`.claude/` を変更したら、同期し直す。

## 使う側に求めること

| 要件 | 内容 |
|---|---|
| `python3` | `sync.py` の実行に使う(`python3 -I` で実行する。標準ライブラリのみ) |
| 実行場所 | 同期したいリポジトリのルート |
| 生成物の扱い | `.codex/` は、同期の生成物。リポジトリによっては `.gitignore` に入れる(このリポジトリでは入れている) |
| リポジトリ固有の同期ルール | 変換しない deny ルールなどは、Devin 向けは `.devin/global_rules.md`、それ以外は `AGENTS.md` / `CLAUDE.md` に書く。スキルがこれを読んで、`--skip-deny` を付ける |

## 使い方

```
/sync-devin-codex:sync                 # 差分を確認して、書き込む
/sync-devin-codex:sync --check         # 差分の確認だけ(書き込まない)
/sync-devin-codex:sync --quick         # デフォルトブランチを fetch して、同期元に変更が無ければ省略する
/sync-devin-codex:sync --target codex  # 対象を絞る(devin|codex|all)
```

`--quick` は、同期元に変更が無いことだけを根拠に省略する。生成物を手で編集した場合や、このプラグインの更新で出力形式が変わった場合はずれるので、確実に確認したいときは付けない。`--check` との併用はエラー。

## 注意

- Codex の hooks は、初回に `/hooks` でレビュー・信頼が必要。プロジェクトの `.codex/` は、信頼済みの場合のみ読み込まれる。
- `Bash(cat .env*)` のような glob は、同期時点で存在するファイルに展開される。新しい秘密情報ファイルを足したら、再同期する。
- コミットは、ユーザーが求めたときだけ行う。

## テスト・evals

```bash
python3 -m unittest discover -s plugins/sync-devin-codex/tests -v   # API 不要
claude plugin eval plugins/sync-devin-codex --trust-plugin --scaffold --allow-tools Bash --runs 1 --ablation none --no-publish   # ローカルのみ
```

evals の詳細は [CONTRIBUTING.md](../../CONTRIBUTING.md) を参照。
