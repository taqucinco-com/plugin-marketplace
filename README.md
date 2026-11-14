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
| 名前 | 内容 |
|---|---|
| `sync-devin-codex` | `.claude/` の skills・agents・rules・permissions・MCP を Devin と Codex 用に変換・同期する(`/sync-devin-codex:sync`) |
| `android-emulator-operate` | Android エミュレータを adb で操作(起動・アプリのインストールと起動・スクリーンショット・要素取得・タップ)する手順を提供する |
| `ios-simulator-operate` | iOS シミュレータを idb と xcrun simctl で操作(起動・スクリーンショット・要素取得・タップ)する手順を提供する |
| `ui-core-verify` | Android・iOS 共通の UI 検証ループ(ui-checker agent・Figma MCP・画像/座標の標準サイズ正規化・結果保存)を提供する共有プラグイン |
| `ui-android-emu-verify` | Android エミュレータ上のアプリの UI を検証する(操作は `android-emulator-operate`、評価ループは `ui-core-verify` を利用) |
| `ui-ios-sim-verify` | iOS シミュレータ上のアプリの UI を検証する(操作は `ios-simulator-operate`、評価ループは `ui-core-verify` を利用) |
| `pr-ui-evidence` | PR の差分から影響する画面を推定し、before/after のスクリーンショットを撮って PR 説明文に載せる |
| `maestro-scenario-author` | ユーザーと対話しながら Maestro の E2E シナリオ(flow YAML)を作成・検証する |
| `maestro-ci-setup` | Maestro の E2E を GitHub Actions の Android エミュレータ / iOS シミュレータで実行する CI を整える |
