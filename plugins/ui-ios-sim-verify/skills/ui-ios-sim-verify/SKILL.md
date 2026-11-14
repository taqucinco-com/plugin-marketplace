---
name: ui-ios-sim-verify
description: iOSシミュレータ上で動くアプリのUI実装の妥当性を、スクリーンショットと`idb ui describe-all`の構造をもとに検証する。Figmaデザインとの比較、または依頼文の期待との比較ができる。「iOSで動作確認して」「シミュレータで見た目を確認して」「iOSでデザイン通りか確認して」等、iOS/シミュレータ/idbへの言及がある依頼で使う（Androidエミュレータの場合は`ui-android-emu-verify`を使う）。操作は`ios-simulator-operate`、評価ループは`ui-verify-loop`に委ねる。
---

# iOS UI検証

iOSシミュレータで動くアプリのUIを検証する。**評価の進め方（標準サイズへの正規化、Figma比較、`ui-checker`によるループ、結果保存）はAndroid/iOSで共通なので、`ui-verify-loop`スキル（`ui-core-verify`プラグイン）に従う。** このスキルは、iOS固有の部分だけを定める。重複して定義しない。

## 前提

- `ios-simulator-operate`スキル（`ios-simulator-operate`プラグイン）と`ui-verify-loop`スキル（`ui-core-verify`プラグイン）が使えること。このプラグインは両方に依存しているため、マーケットプレイスからインストールすれば揃う。使えない場合はインストールをユーザーに案内する。
- `simctl`/`idb`がBashツールのサンドボックス内で動かない点（`dangerouslyDisableSandbox: true`が必要）、idb未導入時の案内は`ios-simulator-operate`に従う。

## `ui-verify-loop`の読み替え

`ui-verify-loop`の「操作スキル」「構造情報」は、iOSでは次のとおり。

| `ui-verify-loop`の記述 | iOSでの内容 |
|---|---|
| 操作スキル | `ios-simulator-operate` |
| スクリーンショットの取得 | `xcrun simctl io <UDID> screenshot`（同スキル3節） |
| 構造情報の取得 | `idb ui describe-all --udid <UDID>`でtype/AXLabel/frameのJSONを取得（同スキル4節） |
| 構造情報の座標 | `frame`は**ポイント**で、スクリーンショットの**ピクセル**とは別の座標系（例: 402x874pt と 1206x2622px）。それぞれを`scripts/scale-structure.py`と`scripts/normalize-image.sh`で標準サイズへ伸縮すれば揃う |
| アプリの再インストール・起動 | `xcrun simctl install`と`launch`（同スキル2節）。**デプロイ先は必ずUDIDで明示する** |
| 環境要因の切り分け | 同スキル6節（`idb connect`の切れ、物理iPhoneへの誤デプロイなど） |

## idbが使えない場合

idbを導入しない場合は、`ios-simulator-operate`の縮退モード（`simctl`のみ）で進める。この場合、**構造情報（`describe-all`）が取得できない**ため、`ui-verify-loop`の手順どおりスクリーンショットだけで比較し、構造情報が無いことを`ui-checker`に伝える。画面遷移もタップできないため、ディープリンク（`xcrun simctl openurl`）や起動引数で到達できる画面に限られる。到達できなかった画面は「idb未導入のため検証できなかった」と結果に明記し、確認済みとして報告しないこと。

## 手順

1. 上の読み替えに従い、`ui-verify-loop`スキルの手順を最初から最後まで実施する。
2. シミュレータが起動していない・idbが接続できないなど操作の前提が崩れている場合は、`ui-verify-loop`の`fatal`の考え方に従い、無理に進めず依頼者へ報告する。
