---
name: maestro-scenario-author
description: ユーザーと対話しながら、Maestro のE2Eシナリオ（flow YAML）を作成・検証する。実機画面の要素（`maestro hierarchy`）を確認しつつ1ステップずつ組み立て、`maestro test`で通ることを確かめる。「Maestroのシナリオを作って」「E2Eテストを書きたい」「このフローをMaestroにして」「Maestroのflowを直して」といった依頼で使う。CIへの組み込みは`maestro-ci-setup`を使う。
---

# Maestro シナリオ作成（対話式）

ユーザーが確認したい操作の流れを、動く Maestro flow（YAML）にする。**一度に全部書かず、1ステップずつ実機で確かめながら積み上げる。** 推測で書いた要素名は動かないことが多い。

## 前提

- `maestro`が使えること（`command -v maestro`）。無ければ https://docs.maestro.dev/getting-started/installing-maestro を案内して、導入するか確認する。勝手にインストールしない。MaestroはJava 17以上が必要。
- エミュレータ/シミュレータが起動していて、対象アプリがインストール済みであること。起動やインストールは`android-emulator-operate`/`ios-simulator-operate`があればそれに従う。`maestro list-devices`で認識されているか確認する。
- Bashツールのサンドボックス内では`simctl`/`adb`/Maestroがデバイスと通信できないことがある。その場合は`dangerouslyDisableSandbox: true`で実行する（アプリ側の異常ではない）。

## 手順

### 1. 何を確認するシナリオかを聞く（作る前に決める）

次を対話で確認する。分かっているものは聞き直さない。

- 目的（例: 「設定画面を開いてニックネームが表示される」）と、**成功の判定**（何が見えたら成功か）
- 対象プラットフォーム（Android / iOS / 両方）と`appId`（Androidのapplication id / iOSのbundle id。両者は異なることが多い）
- 開始状態（初回起動か、ログイン済みか、`clearState`してよいか）
- 既存のflowの置き場所と命名（例: `test/e2e/maestro/android/`・`ios/`）。既存flowがあれば**先に読んで**、命名・コメントの言語・書き方を合わせる

### 2. 画面の要素を見る

```bash
maestro hierarchy                  # 接続中のデバイスの要素ツリー（JSON）
maestro --udid <ID> hierarchy      # 複数デバイスがあるとき
```

- タップ対象は、見えている**テキスト**か**アクセシビリティid**（Androidは`resource-id`、iOSは`accessibilityIdentifier`）で指定する。座標指定(`point:`)は画面サイズ依存なので最後の手段にする。
- テキストが日本語・英語で変わる、同じ文言が複数ある、といった曖昧さがあれば、ユーザーに「アプリ側にidを付けられるか」を相談する。付けられるなら`id:`で指定するほうが壊れにくい。
- 画面外の要素は`scrollUntilVisible`が必要。

### 3. 1ステップずつ足して実行する

1. 先頭に`appId`とヘッダ(`---`)を書いたflowを作る。
2. 次の1〜2コマンドを足し、**その都度`maestro test <flow>`で実行**して通ることを確認する。失敗したら、直前に足した分だけを疑う。
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

### 4. 仕上げ

- `maestro check-syntax <flow>`で構文を確認し、最終的に`maestro test`で**最初から最後まで通して**成功を確認する。途中まで確かめた状態で完了とは言わない。
- Android/iOSで画面が同じなら、`appId`以外はなるべく同じ内容にする。差分はコメントで理由を書く。
- 不安定さ（実行のたびに成功・失敗が変わる）が疑われるなら、同じflowを2〜3回連続で実行して確認する。
- 書いたflowについて、何を確認しているか・開始状態・実行コマンドを、ユーザーに短く説明する。CIで流す場合は`maestro-ci-setup`を案内する。

## 注意

- 認証情報・トークンはflowに直書きしない。`env`（`maestro test -e KEY=VALUE`と`${KEY}`）で渡す。
- 破壊的な操作（課金・本番データの削除・外部への送信）を含むflowは、テスト用の環境・アカウントでだけ動かす前提かをユーザーに確認する。
- 実行できなかった・通らなかったflowは、確認済みとして渡さず、現状と原因（要素が見つからない等）を明記する。
