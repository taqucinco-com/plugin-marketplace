---
name: maestro-scenario-author
description: ユーザーと対話しながら、Maestro のE2Eシナリオ（flow YAML）を作成・検証する。Maestro MCP（`inspect_screen`・`run`）で実機画面の要素を確認しつつ1ステップずつ組み立て、通ることを確かめる（MCPが使えなければCLIで同じことをする）。「Maestroのシナリオを作って」「E2Eテストを書きたい」「このフローをMaestroにして」「Maestroのflowを直して」といった依頼で使う。CIへの組み込みは`maestro-ci-setup`を使う。
---

# Maestro シナリオ作成（対話式）

ユーザーが確認したい操作の流れを、動く Maestro flow（YAML）にする。**一度に全部書かず、1ステップずつ実機で確かめながら積み上げる。** 推測で書いた要素名は動かないことが多い。

## 前提

- `maestro`が使えること（`command -v maestro`）。無ければ https://docs.maestro.dev/getting-started/installing-maestro を案内して、導入するか確認する。勝手にインストールしない。MaestroはJava 17以上が必要。
- このプラグインは`.mcp.json`でMaestro MCPサーバー（`maestro mcp --no-viewer`）を登録する。**Claude Codeでプラグインを有効化した後、MCPサーバーを認識させるために再起動（または`/mcp`で確認）が必要。** Codexは`.codex-plugin/plugin.json`の`mcpServers`、Devinはプラグイン直下の`.mcp.json`で同じサーバーを読む。MCPツールが見当たらないときはCLI（`maestro hierarchy`/`maestro test`）で進める。
- エミュレータ/シミュレータが起動していて、対象アプリがインストール済みであること。起動やインストールは`android-emulator-operate`/`ios-simulator-operate`があればそれに従う。
- Bashツールのサンドボックス内では`simctl`/`adb`/Maestroがデバイスと通信できないことがある。その場合は`dangerouslyDisableSandbox: true`で実行する（アプリ側の異常ではない）。

## 使うMCPツール（Maestro 2.10.0で確認。バージョンで増減・改名する）

ツール名はプラグイン同梱のMCPなので`mcp__plugin_maestro-scenario-author_maestro__<名前>`として現れる（以下の表は`<名前>`部分）。ツールが見当たらなければ、`ToolSearch`で`maestro`を検索して読み込む。

| ツール | 用途 |
|---|---|
| `list_devices` | 接続中のデバイスとIDを調べる（以降の`device_id`に使う） |
| `inspect_screen` | 現在画面の要素ツリー。**セレクタは必ずここの値から決める** |
| `run` | `yaml`（インライン）/`files`/`dir`でMaestroコマンドやflowを実行する。探索・デバッグ中はインラインYAMLで1〜2コマンドずつ |
| `take_screenshot` | 画面の目視確認。保存先は指定できない |
| `cheat_sheet` | コマンドと書き方の一覧（失敗するときは下の注意を参照） |

`list_cloud_devices`・`run_on_cloud`などのクラウド系ツールはMaestro Cloudのアカウント用で、このスキルでは使わない。**ユーザーが明示しない限り、flowやアプリをクラウドへ送信しない。**

### MCPの落とし穴

- `inspect_screen`の要素キーは省略形（`txt`=text、`rid`=resource-id、`a11y`=accessibilityText）で、**そのままセレクタには使えない**。`tapOn`等で使えるのは`text`・`id`・`index`・位置指定（`below`/`above`/`leftOf`/`rightOf`）。`a11y`の値は`text:`に入れる。
- `text:`は**全文一致の正規表現（大文字小文字は無視）**。部分文字列では一致しない。文字列は`txt`の値を**コピーする**。スクリーンショットを見て文言を推測して書かない（アイコンが「お気に入り」に見えても、テキストは無いことがある）。
- ボタンが`tap_on`相当で押せない場合、アプリ側にラベルを付けられないかを相談する（FlutterならSemantics、ネイティブならaccessibilityIdentifier/contentDescription）。付けられないなら座標指定はやむを得ないが、最後の手段。
- スクリーンショットの保存先・画面録画・スワイプの専用ツールは無い。保存・録画は`xcrun simctl io`/`adb`で行い、スワイプは`run`のYAML（`swipe`・`scrollUntilVisible`）で書く。
- `cheat_sheet`などドキュメント系が`MAESTRO_CLOUD_API_KEY`関連のエラーで失敗することがある。その場合は無理に使わず、下のよく使うコマンドと https://docs.maestro.dev を参照する。APIキーをユーザーに要求・取得しない。
- 同じ失敗（構文エラー、要素の誤認）が別セッションで繰り返されがち。詰まった内容と解決策を、プロジェクトの既存ガイド（AGENTS.md/CLAUDE.mdやE2Eのドキュメント）に追記することをユーザーに提案する。勝手に書き込まない。

### 1. 何を確認するシナリオかを聞く（作る前に決める）

次を対話で確認する。分かっているものは聞き直さない。

- 目的（例: 「設定画面を開いてニックネームが表示される」）と、**成功の判定**（何が見えたら成功か）
- 対象プラットフォーム（Android / iOS / 両方）と`appId`（Androidのapplication id / iOSのbundle id。両者は異なることが多い）
- 開始状態（初回起動か、ログイン済みか、`clearState`してよいか）
- 既存のflowの置き場所と命名（例: `test/e2e/maestro/android/`・`ios/`）。既存flowがあれば**先に読んで**、命名・コメントの言語・書き方を合わせる

### 2. 画面の要素を見る

MCPが使えるなら`list_devices`でIDを調べ、`inspect_screen`で取得する。使えないときはCLI。

```bash
maestro hierarchy                  # 接続中のデバイスの要素ツリー（JSON）
maestro --udid <ID> hierarchy      # 複数デバイスがあるとき
```

- タップ対象は、見えている**テキスト**か**アクセシビリティid**（Androidは`resource-id`、iOSは`accessibilityIdentifier`）で指定する。座標指定(`point:`)は画面サイズ依存なので最後の手段にする。
- テキストが日本語・英語で変わる、同じ文言が複数ある、といった曖昧さがあれば、ユーザーに「アプリ側にidを付けられるか」を相談する。付けられるなら`id:`で指定するほうが壊れにくい。
- 画面外の要素は`scrollUntilVisible`が必要。

### 3. 1ステップずつ足して実行する

1. 先頭に`appId`とヘッダ(`---`)を書いたflowを作る。
2. 次の1〜2コマンドを足し、**その都度実行**して通ることを確認する。MCPなら`run`（まずインラインの`yaml`で試し、通ったらflowファイルへ書き写す。最後はファイルを`files`で実行する）、CLIなら`maestro test <flow>`。失敗したら、直前に足した分だけを疑う。
3. 画面遷移や非同期読み込みの後は、`assertVisible`で「到達できた」ことを確かめてから次へ進む。固定の`sleep`ではなく`waitForAnimationToEnd`や`assertVisible`（タイムアウト付きで待つ）を使う。
4. ユーザーに、今できているところまでの動作を報告して、次に何を確認したいか聞く。

よく使うコマンド:

```yaml
appId: com.example.app
---
- clearState                      # 初期状態にする（必要なときだけ）
- launchApp
- tapOn: "設定"                    # テキスト。id指定は `tapOn: { id: "settings_tab" }`
- assertVisible: "ニックネーム"
- inputText: "テスト"
- scrollUntilVisible:
    element: "ログアウト"
- waitForAnimationToEnd
- takeScreenshot: settings         # 証跡が欲しい箇所だけ
- assertNotVisible: "エラー"
```

### 3.5. ステップ後の進行確認を、Decision AIに任せる（任意。条件を満たすときだけ）

手順3で1〜2コマンドを実行するたびに、**目視確認のために`take_screenshot`の画像を自分で読んでいる**なら、その部分をOpenAI Decisions APIの判定に置き換えて速くできる。**次の条件がすべてそろったときだけ**使い、そろわなければ飛ばして従来どおり進める。

1. 環境変数`DECISION_AI`が`1`（`true`/`on`/`yes`も可）。利用者がプロジェクトの`settings.json`の`env`で有効にする。
2. 環境変数`OPENAI_API_KEY`が設定されている。キーはリポジトリの外に置くもので、このスキルは値を扱わない。
3. 画面をファイルに保存する手段がある。`take_screenshot`は保存先を指定できないので使えない。`android-emulator-operate` / `ios-simulator-operate`の手順（`adb exec-out screencap -p` / `xcrun simctl io <UDID> screenshot`）に従って、保存する。これらのプラグインが無ければ、この手順は使わない。

**使える範囲は限られる。**
- `inspect_screen`は、次に押す要素を決めるために必要なので省かない。省けるのは、目視確認のための`take_screenshot`だけ。
- **flowが通ったかの最終判断（手順4の、最初から最後まで通す実行）には使わない。** それは`maestro`の実行結果が唯一の正解。
- 要素の選択（セレクタの決定）にも使わない。
- 画像を読む回数が少ない短いシナリオでは、効果がほとんどない。

#### APIキーの確認方法（厳守。キーが会話・ログ・学習に流れないようにする）

存在確認は、次のコマンド**だけ**で行う。値には一切触れず、結果は終了コードと固定の文言で返る。`SCRIPTS`は、このSKILL.mdがあるディレクトリの`scripts/`を絶対パスにしたもの（スキルの読み込み時に示されるベースディレクトリで解決する）。

```bash
python3 -I "$SCRIPTS/decide.py" --check; echo "exit=$?"
```

| exit | 意味 | 対応 |
|---|---|---|
| 0 | 使える | 下の判定へ進む |
| 10 | `DECISION_AI`が無効 | 何も言わずこの手順を飛ばす（異常ではない） |
| 3 | 有効だがキー未設定 | ユーザーに伝え、使わずに進めてよいか確認する。設定方法は案内してよいが、**値は聞かない・貼らせない** |

**やってはいけないこと**: `env`・`printenv`・`export -p`・`set`・`declare -p`の実行、`echo "$OPENAI_API_KEY"`、キーの一部の表示、`.env`・`.envrc`・`~/.zshrc`・`settings*.json`を読んでキーを探すこと、`set -x`、キーをコマンドライン引数に渡すこと、キーの値・長さ・一部を返答やファイルに書くこと。`decide.py`が失敗したときは、リクエスト本文を出して原因を探らず、終了コードと1行のメッセージだけで判断する。

#### 判定の手順

1. 画面を保存し、標準サイズに正規化する。保存先は**リポジトリの外**（`$TMPDIR`）にする。`simctl`/`adb`がサンドボックスで動かない場合は、前提に書いたとおり`dangerouslyDisableSandbox: true`で実行する。

   ```bash
   bash "$SCRIPTS/normalize-image.sh" "$TMPDIR/step.png" "$TMPDIR/step-norm.png"
   ```

2. 判定する。`$SKILL_DIR`はこのSKILL.mdがあるディレクトリ。`--element`には、**このステップで到達しているはずの画面や状態**を、画面だけを見て「ある/ない」が答えられる形で書く（例: 「見出し『設定』が画面の上部に表示されているか」）。**画像のラベルは、質問文が参照している`現在の画面`のままにする。**

   ```bash
   python3 -I "$SCRIPTS/decide.py" --profile maestro-step \
     --questions "$SKILL_DIR/decision/step-questions.json" \
     --element '見出し「設定」が画面の上部に表示されているか' \
     --image '現在の画面='"$TMPDIR/step-norm.png"
   ```

3. **`summary.next`だけで分岐する**（確率を自分で読んで決めない）。
   - `proceed`: 目的の画面で、権限ダイアログなどの妨げも無い。`take_screenshot`の目視確認を省いて、次のステップへ進む。
   - `inspect`: それ以外（`summary.reason`: 曖昧、妨げる表示がある、評価できない画面、回答拒否など）。従来どおり、`inspect_screen`と`take_screenshot`で自分で確かめる。`decide.py`が0以外で終了した場合も同じ。
4. 画像がOpenAIに送られる。個人情報・秘密情報が写る画面（ログイン後の個人データなど）では使わない。サンドボックスで`api.openai.com`に通信できない（終了コード4）場合は、許可を依頼するか、使わずに進める。

### 4. 仕上げ

- `maestro check-syntax <flow>`で構文を確認し、最終的にflowファイルを`run`（`files`）または`maestro test`で**最初から最後まで通して**成功を確認する。途中まで確かめた状態で完了とは言わない。
- Android/iOSで画面が同じなら、`appId`以外はなるべく同じ内容にする。差分はコメントで理由を書く。
- 不安定さ（実行のたびに成功・失敗が変わる）が疑われるなら、同じflowを2〜3回連続で実行して確認する。
- 書いたflowについて、何を確認しているか・開始状態・実行コマンドを、ユーザーに短く説明する。CIで流す場合は`maestro-ci-setup`を案内する。

## 注意

- 認証情報・トークンはflowに直書きしない。`env`（`maestro test -e KEY=VALUE`と`${KEY}`）で渡す。
- 破壊的な操作（課金・本番データの削除・外部への送信）を含むflowは、テスト用の環境・アカウントでだけ動かす前提かをユーザーに確認する。
- 実行できなかった・通らなかったflowは、確認済みとして渡さず、現状と原因（要素が見つからない等）を明記する。
