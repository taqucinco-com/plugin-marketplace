# ui-android-emu-verify

Android エミュレータ上で動くアプリの UI 実装の妥当性を、スクリーンショットと `uiautomator dump` の構造をもとに検証するプラグイン。Figma デザインとの比較、または依頼文の期待との比較ができる。

提供するもの:
- スキル: `ui-android-emu-verify`([SKILL.md](skills/ui-android-emu-verify/SKILL.md))。Android 固有の読み替えだけを定める薄いスキルで、評価の進め方は `ui-core-verify` の `ui-verify-loop` に委ねる

## 依存するプラグイン

| プラグイン | 役割 |
|---|---|
| `android-emulator-operate` | エミュレータとアプリの操作(起動・スクリーンショット・構造取得・タップ) |
| `ui-core-verify` | 評価ループ(標準サイズへの正規化・`ui-checker` による判定・結果保存・Figma 比較) |

Claude Code では、マーケットプレイスからインストールすれば、依存先も一緒に入る。**Codex・Devin ではプラグイン単位の依存を解決できない**ため、`android-emulator-operate` と `ui-core-verify` を個別にインストールする(`ui-core-verify` の agent と MCP は Claude Code 専用)。

## 使う側に求めること

依存先の要件がそのまま必要になる。

- `adb` と `emulator`、AVD(→ [android-emulator-operate](../android-emulator-operate/README.md))
- 画像を伸縮できるツール、Python 3、(Figma と比較する場合)`FIGMA_API_KEY` など(→ [ui-core-verify](../ui-core-verify/README.md))
- アプリのビルド・起動方法(プロジェクトごとに違うため、README や CLAUDE.md / AGENTS.md に書いておく)

任意で、`ui-core-verify` の Decision AI(`DECISION_AI` と `OPENAI_API_KEY`)も使える。要件と注意点は `ui-core-verify` の README を参照。

## 使い方

次のような依頼で動く。

- 「Android で動作確認して」「エミュレータで見た目を確認して」
- 「デザイン通りか確認して」「Figma とどれくらい近づいたか教えて」

iOS / シミュレータ / idb への言及がある場合は、`ui-ios-sim-verify` を使う。
