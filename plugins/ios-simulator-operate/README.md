# ios-simulator-operate

iOS シミュレータを `idb` と `xcrun simctl` で操作する共通手順を提供するプラグイン。シミュレータの起動、アプリのインストールと起動、スクリーンショット、要素ツリーの取得、タップ・スワイプ・文字入力を扱う。**操作の方法だけを扱い、結果の評価はしない**(評価は呼び出し元の `ui-core-verify` などが行う)。

提供するもの:
- スキル: `ios-simulator-operate`([SKILL.md](skills/ios-simulator-operate/SKILL.md))

## 使う側に求めること

| 要件 | 内容 |
|---|---|
| macOS と Xcode | 必須。`xcrun simctl` が使えること |
| `idb`(`idb`・`idb_companion`)と `jq` | **任意**。画面操作(タップ・要素ツリーの取得)に必要。無い場合、スキルは導入を案内する(勝手にインストールしない)。公式手順は https://fbidb.io/idb/installation/ 。ビルド済みの companion を入れる formula の要件は、arm64 の Mac・macOS 15 以降・Xcode 26 以降の完全版 |
| 成果物の保存先 | スクリーンショットなどは、`.gitignore` 済みのディレクトリ(例: `work/screenshots/`)に保存する。無ければスキルがユーザーに確認する |

`idb` を導入しない・できない場合は、`simctl` のみの操作に絞る。要素ツリーの取得と画面操作はできず、ディープリンク(`openurl`)などで到達できる画面に限られる。その旨(「idb 未導入のため操作・検証できなかった」)を結果に明記する。

### サンドボックスについて

Claude Code の Bash ツールのサンドボックス内では、`simctl` と `idb` が動かないことがある(`CoreSimulatorService` への接続や `/tmp/idb/state.lock` の作成が遮断される)。アプリやシミュレータの異常ではなく、`dangerouslyDisableSandbox: true` での実行が必要になる。詳細は SKILL.md の「前提」を参照。

## 使い方

通常は、`ui-ios-sim-verify` や `pr-ui-evidence` から呼ばれる。単独でも、シミュレータ上でアプリを動かして画面を確認・操作したいときに使える。

## evals

`idb` が無い環境での振る舞い(導入の案内・縮退モードの説明・虚偽の報告をしないこと)を確認する evals がある。実行方法は [CONTRIBUTING.md](../../CONTRIBUTING.md) を参照(ローカルのみ。CI では実行しない)。

```bash
claude plugin eval plugins/ios-simulator-operate --trust-plugin --scaffold --runs 1 --ablation none --no-publish
```
