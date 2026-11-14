# plugin-marketplace

Claude Code のプラグインマーケットプレイス。

## 使い方
```
/plugin marketplace add taqucinco-com/plugin-marketplace
/plugin install sync-devin-codex@plugin-marketplace
```
ローカルでは、リポジトリのルートで `claude plugin marketplace add ./` を実行すると追加できます。

### Codex
```
codex plugin marketplace add taqucinco-com/plugin-marketplace
codex plugin add sync-devin-codex@plugin-marketplace
```
Codex 用の定義は `.agents/plugins/marketplace.json` と各プラグインの `.codex-plugin/plugin.json`。

### Devin
各プラグインは `.devin-plugin/plugin.json`(`.claude-plugin/plugin.json` へのシンボリックリンク)を持つ。
```
devin plugins install taqucinco-com/plugin-marketplace#plugins/sync-devin-codex
devin plugins install --local ./plugins/sync-devin-codex   # ローカル確認
```
Devin は `marketplace.json` を読まず、プラグイン単位でインストールする。

## プラグイン
各プラグインの詳細(提供するもの・使う側に求めること)は、名前のリンク先の README.md を参照。

| 名前 | 内容 |
|---|---|
| [`sync-devin-codex`](plugins/sync-devin-codex/README.md) | `.claude/` の skills・agents・rules・permissions・MCP を Devin と Codex 用に変換・同期する(`/sync-devin-codex:sync`) |
| [`android-emulator-operate`](plugins/android-emulator-operate/README.md) | Android エミュレータを adb で操作(起動・アプリのインストールと起動・スクリーンショット・要素取得・タップ)する手順を提供する |
| [`ios-simulator-operate`](plugins/ios-simulator-operate/README.md) | iOS シミュレータを idb と xcrun simctl で操作(起動・スクリーンショット・要素取得・タップ)する手順を提供する |
| [`ui-core-verify`](plugins/ui-core-verify/README.md) | Android・iOS 共通の UI 検証ループ(ui-checker agent・Figma MCP・画像/座標の標準サイズ正規化・結果保存)を提供する共有プラグイン。任意で OpenAI Decisions API による高速な事前判定(後述)を使える |
| [`ui-android-emu-verify`](plugins/ui-android-emu-verify/README.md) | Android エミュレータ上のアプリの UI を検証する(操作は `android-emulator-operate`、評価ループは `ui-core-verify` を利用) |
| [`ui-ios-sim-verify`](plugins/ui-ios-sim-verify/README.md) | iOS シミュレータ上のアプリの UI を検証する(操作は `ios-simulator-operate`、評価ループは `ui-core-verify` を利用) |
| [`pr-ui-evidence`](plugins/pr-ui-evidence/README.md) | PR の差分から影響する画面を推定し、before/after のスクリーンショットを撮って PR 説明文に載せる |
| [`maestro-scenario-author`](plugins/maestro-scenario-author/README.md) | ユーザーと対話しながら Maestro の E2E シナリオ(flow YAML)を作成・検証する |
| [`maestro-ci-setup`](plugins/maestro-ci-setup/README.md) | Maestro の E2E を GitHub Actions の Android エミュレータ / iOS シミュレータで実行する CI を整える |

## Decision AI(任意)

`ui-core-verify` の修正ループ、`pr-ui-evidence` の変更判定、`maestro-scenario-author` のステップ後の進行確認は、環境変数 `DECISION_AI` と `OPENAI_API_KEY` の**両方**がそろったときだけ、OpenAI の Decisions API で事前判定を高速化できる。そろわなければ従来どおり動く。要件(キーの置き場所・送信されるデータ・料金など)は、[ui-core-verify の README](plugins/ui-core-verify/README.md) に一本化している。
