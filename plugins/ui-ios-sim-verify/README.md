# ui-ios-sim-verify

iOS シミュレータ上で動くアプリの UI 実装の妥当性を、スクリーンショットと `idb ui describe-all` の構造をもとに検証するプラグイン。Figma デザインとの比較、または依頼文の期待との比較ができる。

提供するもの:
- スキル: `ui-ios-sim-verify`([SKILL.md](skills/ui-ios-sim-verify/SKILL.md))。iOS 固有の読み替え(`frame` はポイント、スクリーンショットはピクセル、など)だけを定める薄いスキルで、評価の進め方は `ui-core-verify` の `ui-verify-loop` に委ねる

## 依存するプラグイン

| プラグイン | 役割 |
|---|---|
| `ios-simulator-operate` | シミュレータとアプリの操作(起動・スクリーンショット・構造取得・タップ) |
| `ui-core-verify` | 評価ループ(標準サイズへの正規化・`ui-checker` による判定・結果保存・Figma 比較) |

Claude Code では、マーケットプレイスからインストールすれば、依存先も一緒に入る。**Codex・Devin ではプラグイン単位の依存を解決できない**ため、`ios-simulator-operate` と `ui-core-verify` を個別にインストールする(`ui-core-verify` の agent と MCP は Claude Code 専用)。

## 使う側に求めること

依存先の要件がそのまま必要になる。

- macOS・Xcode(`xcrun simctl`)、`idb` と `jq`(→ [ios-simulator-operate](../ios-simulator-operate/README.md))。`idb` が無い場合は、構造情報を取れず、ディープリンクで到達できる画面に限られる
- 画像を伸縮できるツール、Python 3、(Figma と比較する場合)`FIGMA_API_KEY` など(→ [ui-core-verify](../ui-core-verify/README.md))
- アプリのビルド・起動方法(プロジェクトごとに違うため、README や CLAUDE.md / AGENTS.md に書いておく)
- デプロイ先は必ず UDID で明示する(物理 iPhone への誤デプロイを防ぐため)

任意で、`ui-core-verify` の Decision AI(`DECISION_AI` と `OPENAI_API_KEY`)も使える。要件と注意点は `ui-core-verify` の README を参照。

## 使い方

次のような依頼で動く。

- 「iOS で動作確認して」「シミュレータで見た目を確認して」
- 「iOS でデザイン通りか確認して」

Android エミュレータの場合は、`ui-android-emu-verify` を使う。
