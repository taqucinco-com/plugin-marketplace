---
name: ui-android-emu-verify
description: Androidエミュレータ上で動くアプリのUI実装の妥当性を、スクリーンショットと`uiautomator dump`の構造をもとに検証する。Figmaデザインとの比較、または依頼文の期待との比較ができる。「Androidで動作確認して」「エミュレータで見た目を確認して」「デザイン通りか確認して」「Figmaとどれくらい近づいたか教えて」等の依頼で使う（iOS/シミュレータ/idbへの言及がある場合は`ui-ios-sim-verify`を使う）。操作は`android-emulator-operate`、評価ループは`ui-verify-loop`に委ねる。
---

# Android UI検証

Androidエミュレータで動くアプリのUIを検証する。**評価の進め方（標準サイズへの正規化、Figma比較、`ui-checker`によるループ、結果保存）はAndroid/iOSで共通なので、`ui-verify-loop`スキル（`ui-core-verify`プラグイン）に従う。** このスキルは、Android固有の部分だけを定める。重複して定義しない。

## 前提

- `android-emulator-operate`スキル（`android-emulator-operate`プラグイン）と`ui-verify-loop`スキル（`ui-core-verify`プラグイン）が使えること。このプラグインは両方に依存しているため、マーケットプレイスからインストールすれば揃う。使えない場合はインストールをユーザーに案内する。
- adbが無い場合の案内や、複数デバイス接続時の`adb -s`指定は`android-emulator-operate`に従う。
- Codex・Devinでは、プラグイン単位の依存関係を解決できない。使う場合は、`android-emulator-operate`と`ui-core-verify`を個別にインストールする（`ui-core-verify`のagentとMCPはClaude Code専用。詳細は`ui-verify-loop`の前提を参照）。

## `ui-verify-loop`の読み替え

`ui-verify-loop`の「操作スキル」「構造情報」は、Androidでは次のとおり。

| `ui-verify-loop`の記述 | Androidでの内容 |
|---|---|
| 操作スキル | `android-emulator-operate` |
| スクリーンショットの取得 | `adb -s <シリアル> exec-out screencap -p`（同スキル3節） |
| 構造情報の取得 | `uiautomator dump`でtext/content-desc/boundsを取得（同スキル4節） |
| 構造情報の座標 | `bounds`は実ピクセル。`ui-verify-loop`の`scale-structure.py`が全体サイズを自動検出して伸縮する（スクリプトの場所の解決は`ui-verify-loop`の手順1に従う） |
| アプリの再インストール・起動 | `adb install -r`と`monkey`/`am start`（同スキル2節） |
| 環境要因の切り分け | 同スキル6節（ストレージ不足、無関係なダイアログなど） |

## 手順

1. 上の読み替えに従い、`ui-verify-loop`スキルの手順を最初から最後まで実施する。
2. エミュレータが起動していない・adbが使えないなど操作の前提が崩れている場合は、`ui-verify-loop`の`fatal`の考え方に従い、無理に進めず依頼者へ報告する。
