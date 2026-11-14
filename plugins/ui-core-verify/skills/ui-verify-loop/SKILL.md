---
name: ui-verify-loop
description: モバイルアプリ（Androidエミュレータ・iOSシミュレータ共通）のUI実装の妥当性を、標準サイズに正規化したスクリーンショットと構造情報から`ui-checker`agentで判定し、不一致があれば修正・再ビルドして再検証するループの共通手順。Figmaデザインまたは依頼文の期待との比較ができる。通常は`ui-android-emu-verify`/`ui-ios-sim-verify`スキルから参照されて使う。プラットフォーム固有の操作（起動・スクリーンショット・構造取得）は含まない。
---

# UI検証ループ（Android / iOS共通）

エミュレータ・シミュレータで動くアプリの見た目・挙動を、スクリーンショットと構造情報で検証する共通手順。**このスキルは、操作結果を「評価」してループを回す部分だけを扱う。** プラットフォーム固有の操作は、呼び出し元の`ui-android-emu-verify`/`ui-ios-sim-verify`スキルが指定する操作スキルに委ね、他の構成要素も重複して定義せず次のものに委ねる。

| 役割 | 担当 |
|---|---|
| エミュレータ/シミュレータの起動・アプリの起動・スクリーンショット・構造取得・タップ | 呼び出し元が指定する操作スキル（`android-emulator-operate`または`ios-simulator-operate`） |
| スクリーンショットの評価（判定のみ・副作用なし） | `ui-checker`agent（このプラグイン`ui-core-verify`の`agents/`） |
| Figmaの画像・構造情報の取得 | `figma`MCPサーバ（このプラグインの`.mcp.json`）。ツール名は`mcp__plugin_ui-core-verify_figma__download_figma_images`と`mcp__plugin_ui-core-verify_figma__get_figma_data` |
| 評価結果の保存 | `ui-verify-result-save`スキル |

## 0. 前提の確認

- 呼び出し元が指定する操作スキル（`android-emulator-operate`または`ios-simulator-operate`）が使えること。使えない場合は、そのプラグインのインストールをユーザーに案内する。adb・idbが無い場合の案内も各操作スキルに従う。
- Figmaと比較する場合のみ、上記の`figma`MCPツールが利用可能で、Claude Codeを起動した環境に環境変数`FIGMA_API_KEY`が設定されていること（未設定でもサーバー自体は接続済みと表示されるが、ツール呼び出しが認証エラーになる）。未設定・MCPが使えない場合は、ユーザーにその旨を伝え、Figma比較は行わず手順2-Bに切り替えてよいか確認する（勝手に切り替えて「Figmaと一致した」と報告しない）。
- アプリのビルド方法・パッケージ名は、呼び出し元のプロジェクトの手順に従う（このスキルでは決めない）。
- このプラグインは、プラットフォーム別プラグイン（`ui-android-emu-verify`/`ui-ios-sim-verify`）から依存される共有部品で、単体では操作手段を持たない。`--plugin-dir`でロードする場合は、依存先も含めて指定する（依存が解決できないとプラグインごとロードされない）。
- **Claude Code以外（Codex・Devin）では、そのままでは動かない。** `ui-checker`agentはClaude Code専用で、Codex・Devinには配られない。`figma`MCPはCodex用マニフェスト（`mcpServers`）とDevinの`.mcp.json`で宣言済みだが、この経路の動作は未検証。agentが要る場合は、`ui-core-verify/agents/ui-checker.md`を対象プロジェクトの`.claude/agents/`に置いたうえで`sync-devin-codex`で変換する。

## 画面の評価と`ui-checker`によるループ

評価そのものは専任agent`ui-checker`（判定のみで副作用ゼロ）に委ね、本体のClaude（このスキルを実行している自分自身）はその判定結果をもとに「コード修正→再ビルド→再検証」のループを回す。その場の印象で「だいたい合っている/動いている」と済ませたり、`ui-checker`を介さず自分で評価を確定させたりしないこと。**Figmaとの比較（手順2-A）を行うのは、依頼文で「Figma」「デザイン通り」「ワイヤーフレーム」など、Figmaへの言及が明示的にある場合に限る。** 言及が無い場合はFigmaを呼び出さず、手順2-Bの単純な構造分析を行う。

### 手順1. 比較用の標準サイズ（正規化）

デバイスごとにスクリーンショットのサイズが異なり、Figmaのフレームとも大きさが合わない。また高解像度のままVLMに渡すとトークン消費が大きい。そこで**`ui-checker`に渡す画像と構造情報は、すべて同じ標準サイズに伸縮してから渡す。**

- 標準サイズの既定は **480x1040**（縦長スマートフォンの縦横比に近い値。約700トークン相当）。変更する場合は環境変数`UI_VERIFY_SIZE`（例: `480x640`）か、スクリプトの第3引数で指定する。**縦横比が元画像から大きくずれると文字が歪んで判読できなくなる**（例: 9:19.5の画面を480x640にすると横に約1.6倍伸びる）ため、元の画面に近い縦横比を選ぶこと。スクリプトは10%以上ずれると警告する。
- 元のスクリーンショット（`<name>-app.png`・`<name>-figma.png`）は**加工せず残す**（人間の確認・結果保存・タップ座標の取得に使う）。正規化した画像は別名（`<name>-app-norm.png`・`<name>-figma-norm.png`）で保存する。
- **スクリプトの場所**: `scripts/`は、このSKILL.mdがあるディレクトリの下にある。Bashの作業ディレクトリは利用者のプロジェクトなので、`scripts/...`をそのまま実行しても見つからない。スキルの読み込み時に示されるベースディレクトリで絶対パスに解決し、以降`SCRIPTS`として使う。ベースディレクトリが分からない場合は、`find "$HOME/.claude/plugins" -type d -path '*ui-core-verify*/skills/ui-verify-loop/scripts' | head -1`で探す。
- 画像の正規化には`normalize-image.sh`を使う。`sips`（macOS）・ImageMagick・Python+Pillowのいずれかが必要で、どれも無ければ導入をユーザーに案内する。成功すると`<入力> (<元の幅>x<元の高さ>) -> <出力> (<幅>x<高さ>)`と元のサイズを表示する（Figma画像の元サイズは、後の構造情報の伸縮で使う）。

  ```bash
  bash "$SCRIPTS/normalize-image.sh" work/screenshots/<name>-app.png work/screenshots/<name>-app-norm.png
  ```

- 構造情報の座標も同じ標準サイズの座標系へ伸縮する（`scale-structure.py`）。対象は、Androidの`uiautomator dump`のXML（`bounds`）、iOSの`idb ui describe-all`のJSON（`frame`）、Figma `get_figma_data`のYAML/JSON（`globalVars.styles`配下の`locationRelativeToParent`と`dimensions`）。元の座標系の全体サイズは、XMLとidbのJSONは自動検出する。**Figmaの出力にはルートフレームの寸法が含まれない**ため`--src`が必須で、`pngScale: 1`で取得したFigma画像の元サイズ（`normalize-image.sh`が表示する値）を渡す。iOSの`frame`はポイント、スクリーンショットはピクセルで座標系が違うが、それぞれ標準サイズへ伸縮することで揃う。Figmaの位置は親からの相対値だが、一様な倍率で伸縮すれば整合する。

  ```bash
  python3 "$SCRIPTS/scale-structure.py" work/wd.xml work/wd-norm.xml --dst 480x1040          # Android
  python3 "$SCRIPTS/scale-structure.py" work/ax.json work/ax-norm.json --dst 480x1040        # iOS
  python3 "$SCRIPTS/scale-structure.py" work/figma.yaml work/figma-norm.yaml --src <Figma画像の幅>x<高さ> --dst 480x1040
  ```

  置換件数が0件でスクリプトが失敗した場合は、構造情報の形式が想定と違う。**座標を自分で計算して伸縮してはいけない**（LLMの暗算は、もっともらしいが誤った値を返すことがある。小数が出る計算は特に危険）。座標を使わず、要素名・順序・テキストだけで比較するよう`ui-checker`に伝える（座標が伸縮されていないことを必ず明記する）。形式が想定外だった場合は、`scale-structure.py`を直すようユーザーに報告する。

**数値計算の原則**: 座標・倍率・サイズ・縦横比などの数値の計算や変換は、このスキルのスクリプトか`python3`/`awk`などのコマンド実行で行い、結果をそのまま使う。画像を見て読み取った座標を、頭の中で掛け算・割り算して使うこともしない。

- `ui-checker`には、標準サイズ（幅x高さ）と、画像・構造情報がすべてそのサイズに揃っていることも併せて伝える。タップ座標が必要な操作（各操作スキル）には、**正規化前の元の座標**を使うこと。

### 手順2-A. Figmaに言及がある場合: 比較用の資料を用意する

1. 検証したい画面に対応するFigmaのfileKey（Figma URLの`/design/<fileKey>/...`部分）とnode-id（例: `2:2`）を、依頼文またはユーザーから確認する。分からなければユーザーに尋ねる。
2. `mcp__plugin_ui-core-verify_figma__download_figma_images`ツールで、`fileKey: "<fileKey>"`（必須）、`nodes: [{nodeId: "<node-id>", fileName: "<name>-figma.png"}]`、`localPath: "work/screenshots"`、`pngScale: 1`を指定してリファレンス画像を取得・保存する（＝「目指すべき成果物」）。`pngScale`の既定は2で、画像がフレームの2倍の大きさになる。1にすると画像サイズがフレームの寸法と一致し、構造情報の伸縮の元サイズとして使える。`localPath`はMCPサーバプロセスのカレントディレクトリからの相対パスとして解決される。
3. 同じ`fileKey`・`nodeId`で`mcp__plugin_ui-core-verify_figma__get_figma_data`も呼び出し、構造情報（YAML）を取得する。各ノードの`layout`は`layout_XXXX`という**参照**で、位置・寸法の実体は`globalVars.styles`にある。位置（`locationRelativeToParent`）は親からの相対値で、自動レイアウトの子には出ない。寸法（`dimensions`）も、伸縮する軸には出ない。**ルートフレームの寸法は含まれない**。そのため絶対座標での厳密な突き合わせはできず、要素名・階層・テキスト・並び順を主な根拠にし、座標は補助として使う。「要素の有無」「配置・順序」を画像の目視だけに頼らず裏付けるために使う。
4. 操作スキルの手順で、現状のスクリーンショットを`work/screenshots/<name>-app.png`として保存する（＝「現状」）。あわせて操作スキルの手順でアプリ側の構造（Android: `uiautomator dump`、iOS: `idb ui describe-all`）も取得し、Figmaの構造情報と突き合わせられるようにする。構造を取得できない場合（idb未導入など）は、スクリーンショットだけで比較し、構造情報が無いことを`ui-checker`に伝える。
5. 手順1で、Figma画像・アプリ画像・両方の構造情報を標準サイズに正規化する（Figmaの構造情報の`--src`には、Figma画像の元サイズを使う）。
6. 正規化した画像パス（`<name>-figma-norm.png`/`<name>-app-norm.png`）と構造情報が揃ったら手順3に進む。「比較対象」がFigmaであることを手順3の呼び出しで明示する。

### 手順2-B. Figmaに言及が無い場合: 単純な構造分析の材料を用意する

Figmaは呼び出さず、スクリーンショットと操作スキルで得られる構造だけを根拠に、**依頼文で言及された確認内容（例:「地図タブに切り替えたら地図が表示されるはず」「一覧にカードが並んでいるはず」等）に実装がどの程度応えているか**を`ui-checker`に判定させる。依頼文がUIの構造や見た目に触れていない場合（例: 単に「起動確認して」）は、クラッシュ・白画面・意図しないダイアログの有無など、最低限の起動確認のみでよい。

1. 操作スキルの手順で、スクリーンショットを`work/screenshots/<name>-app.png`として保存する。
2. 操作スキルの手順でアプリの構造（Android: `uiautomator dump`、iOS: `idb ui describe-all`）を取得する。取得できない場合はスクリーンショットだけで進める。
3. 手順1の手順でスクリーンショットと構造情報を標準サイズに正規化する。
4. 正規化した画像パスと構造情報が揃ったら手順3に進む。「比較対象」は依頼文で示された期待であることを手順3の呼び出しで明示する。

### 手順3. `ui-checker`を呼び出し、ループする

1. イテレーションカウンタを1にする（この会話内で本体のClaudeが保持する。`ui-checker`自体は状態を持たない）。
2. `Agent`ツールで`subagent_type: ui-core-verify:ui-checker`（プラグインのagentは`<プラグイン名>:<agent名>`の名前空間付きで登録される）を**同期的に（`run_in_background: false`を指定して）**呼び出す。手順2-A/手順2-Bで用意した**正規化済みの**画像パス・標準サイズ、（手順2-Aの場合）Figmaの構造情報、比較対象の期待（Figmaまたは依頼文）を渡す。**バックグラウンド（非同期）呼び出しは使わないこと。** 非対話的なセッション（CIなど）には後続ターンが無く、非同期呼び出しの完了通知を受け取れないため、判定結果を使えないままターンが終わってしまう。
3. 応答のJSON中の`fatal`でまず分岐する。**`pass`/`retry`という二値の「ループ制御判定」は`ui-checker`自体は返さない**（ループを続けるかはイテレーションカウンタという状態を持つ呼び出し元＝このスキル自身の責務のため）。
   - **`fatal: true`**: 直ちにループを中断する。それ以上コードの修正・再ビルドを試みず、`fatal_reason`と直近の`criteria`をそのまま依頼者への報告（人間へのエスカレーション）に含める。
   - **`fatal: false`**: `criteria`に`mismatch`の観点が1件でもあるかを確認する（この判定は呼び出し元が`criteria`から直接行い、agentの追加出力には頼らない）。
     - **`mismatch`が0件**: 検証完了。`loop_verdict: pass`として下記「評価結果の保存」に進んでループを正常終了する。
     - **`mismatch`が1件以上かつイテレーションカウンタ < 10**: `criteria`の`mismatch`指摘をもとにコードを修正し、プロジェクトの手順でアプリをビルドし直して操作スキルの手順でインストール・起動し、**スクリーンショットとアプリ側の構造情報（Android: `uiautomator dump`、iOS: `idb ui describe-all`）の両方を取り直して**、手順1の正規化（画像と構造情報の両方）をやり直す。古い構造情報を使い回すと、修正済みの要素を未実装と判定し続けたり、壊れた要素を存在すると判定したりする（Figma側は変わらないので再正規化は不要）。カウンタを+1して手順3の2.に戻る。
     - **`mismatch`が1件以上かつイテレーションカウンタ = 10**: それ以上ループしない。上限到達を理由に、直近の`criteria`を添えて依頼者へエスカレーションする。

`fatal: true`の具体例（`ui-checker`側の判断基準と共通）: 実行環境レベルの問題で改善しようがない、実装以前に破綻している仕様の瑕疵、コードの修正だけでは解決しない問題、エミュレータ/シミュレータがそもそも起動できていない。

### 評価結果の保存（Markdown + JSON）

保存の手順・フォーマット（Markdown/JSONの形式、`loop_verdict`の3値等）は`ui-verify-result-save`スキルに従う（重複して定義しない）。保存先ディレクトリは、スクリーンショットの保存先（`work/screenshots/`）と同じ場所にする。上限到達（`loop_verdict: retry_limit_reached`）または`fatal`（`loop_verdict: fatal`）でループを終えた場合も、その時点までに判明していた`criteria`を同様に保存する。
