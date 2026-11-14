---
name: ios-simulator-operate
description: iOSシミュレータを idb（タップ・要素ツリー取得・スワイプ・文字入力）と xcrun simctl（起動・アプリのインストールと起動・スクリーンショット）で操作する共通手順。シミュレータ上でアプリを動かして画面を確認・操作したいとき、UI検証や動作確認の前提として使う。idb未導入の場合はインストールを案内し、導入されなければ simctl のみの操作に絞る。アプリの技術スタック（ネイティブ・クロスプラットフォーム等）には依存しない。
---

# iOSシミュレータ操作（idb / simctl）

iOSシミュレータを`idb`と`xcrun simctl`で操作するための共通手順。**シミュレータとアプリを操作する方法だけを扱い、結果（スクリーンショットや要素ツリー）をどう評価するかはこのスキルの範囲外**（呼び出し元が行う）。

## 0. 前提

- macOSでXcodeがインストール済みで、`xcrun simctl`が使えること。`idb`は画面操作（タップ・要素取得など）に必要だが**必須ではない**（次節の手順で有無を確認する）。

- **`simctl`と`idb`はBashツールのサンドボックス内では動かないことがある。** サンドボックスは`CoreSimulatorService`へのXPC接続と`/tmp/idb/state.lock`の作成を遮断するため、以下のエラーになる（アプリやシミュレータ側の異常ではない）。その場合は`dangerouslyDisableSandbox: true`で実行する。

  ```
  # simctl
  CoreSimulatorService connection became invalid. Simulator services will no longer be available.
  Unable to locate device set: ... Code=61 "Connection refused"
  # idb
  PermissionError: [Errno 1] Operation not permitted: '/tmp/idb/state.lock'
  ```

- スクリーンショットなどの成果物は、プロジェクトの`.gitignore`で除外されているディレクトリ（例: `work/screenshots/`）に保存する。保存先がなければユーザーに確認するか、一時ディレクトリを使い、リポジトリ直下に散らかさない。

## 0.5 idbの有無を確認する（最初に必ず行う）

操作を始める前に、`idb`と`jq`が使えるか確認する。

```bash
command -v idb idb_companion jq
```

### すべて見つかった場合

通常モードで進める。以降の全節が使える。

### 見つからないものがある場合: インストールを促す

勝手にインストールせず、**ユーザーに次の手順を案内して、導入するか確認する**。`idb`を入れると、要素ツリーの取得とラベル指定タップができるようになり、画面操作を伴う検証が可能になる、と理由も添える。

公式手順（https://fbidb.io/idb/installation/ ）に沿って、Homebrewの1つのformulaでcompanionとclientの両方を入れる。

```bash
brew tap meta/fb
brew trust meta/fb
brew install meta/fb/idb
brew install jq      # describe-all の出力整形に使用
```

- Homebrewが未導入なら https://brew.sh を参照。
- formulaは**ビルド済みのcompanionバイナリ**を入れる（コンパイルはしない）。要件は **arm64のMac、macOS 15以降、Xcode 26以降の完全版**（Command Line Toolsだけでは不可。App Storeから入れて`xcode-select`で選択済みであること）。要件を満たさない場合は導入できないので、下の「それでもインストールされない場合」へ進む。
- 以前に`facebook/fb`をtapしていた場合は、organization名の変更により`brew tap meta/fb`ではなく`brew update`を実行する。tapは`meta/fb`に移行されるがtrustは失われるため、`brew trust meta/fb`は引き続き必要。
- clientはpipでも入れられる（`pip3 install fb-idb`、Python 3.10以上が必要）。ただしcompanion（macOS専用、ターゲットのシミュレータごとに動く）は別途brewで必要になるため、基本はbrewのformulaだけでよい。
- 導入後、`command -v idb idb_companion jq`で見つかることを確認してから通常モードで進める。

### それでもインストールされない場合: idb操作を使わない

ユーザーが導入しない・できないと答えた場合は、**このスキルから`idb`を使う操作をすべて外し、`xcrun simctl`だけで進める**。idb未導入のまま`idb`コマンドを実行して失敗を繰り返さないこと。

使える操作（`simctl`のみ）:
- 1節のシミュレータの確認・起動（`xcrun simctl boot`、`open -a Simulator`。`idb connect`は行わない）
- 2節のアプリのインストール・起動・終了
- 3節のスクリーンショット・画面録画
- 4節末尾の`openurl`（ディープリンクによる画面遷移）、`privacy`、`push`
- 6節のうち`simctl`に関するもの（`erase`、`uninstall`など）

**使えなくなる操作**:
- 要素ツリーの取得（`idb ui describe-all` / `describe`）
- タップ・スワイプ・文字入力などの画面操作（`idb ui ...`）
- 4節・5節のうち`idb`を使う部分（ラベル指定タップ、座標換算、`ax`/`hid`の切り分け）

`simctl`には画面タップの手段がないため、画面遷移は`openurl`（ディープリンク）かアプリの起動引数（`xcrun simctl launch <UDID> <bundle-id> <args>`）に頼ることになる。それで到達できない画面は、スクリーンショットで確認できる範囲に留め、**「idb未導入のため操作・検証できなかった」と結果に明記して呼び出し元に返す**。確認できていない画面を確認済みとして報告しないこと。

## 1. シミュレータを起動し、idbを接続する

（idb未導入で進める場合、`idb`の行と`idb connect`は飛ばし、`simctl`の確認・起動だけ行う。）

起動済みのシミュレータとidbの接続状態を確認する。

```bash
xcrun simctl list devices booted
idb list-targets | grep Booted
```

`idb list-targets`の行末が`No Companion Connected`ではなく`/tmp/idb/<UDID>_companion.sock`になっていれば接続済み。以降はこのUDIDを使う。Bashツールはシェル状態を保持しないので、UDIDは各コマンドに直接書くか、コマンドごとに取得する。

```bash
UDID=$(xcrun simctl list devices booted -j | jq -r '.devices[][0].udid')
```

起動していない場合（利用可能なデバイスは`xcrun simctl list devices available`で確認）:

```bash
xcrun simctl boot <UDID>
open -a Simulator
idb connect <UDID>
```

`idb connect`はシミュレータを再起動するたびに必要になる。操作系コマンドが`No Companion Connected`や接続エラーで失敗したら、まずこれを疑う。

## 2. アプリをインストールして起動する

ビルド済みの`.app`バンドルがあれば、`simctl`でインストール・起動する。

```bash
xcrun simctl install <UDID> /path/to/MyApp.app
xcrun simctl launch <UDID> <bundle-id>
```

- ビルド方法はプロジェクトによって異なる（`xcodebuild`、各種フレームワークのCLIなど）。ビルド自体はこのスキルの範囲外で、呼び出し元のプロジェクトの手順に従う。
- `xcodebuild`で自前ビルドする場合は`-destination 'platform=iOS Simulator,id=<UDID>'`でシミュレータを明示し、`-derivedDataPath`を指定すると`.app`の場所が確定する（`<derivedDataPath>/Build/Products/Debug-iphonesimulator/*.app`）。
- **デプロイ先は必ずUDIDで明示する。** 物理iPhoneが接続されている環境では、デバイス指定を省くと実機側にデプロイされうる。
- バンドルIDが分からない場合は`.app`内の`Info.plist`から取れる。

  ```bash
  /usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' /path/to/MyApp.app/Info.plist
  ```

- 起動済みアプリの再起動・終了:

  ```bash
  xcrun simctl terminate <UDID> <bundle-id>
  xcrun simctl launch --terminate-running-process <UDID> <bundle-id>
  ```

- 長時間かかるビルドや起動待ちは`run_in_background`付きBashで行い、完了通知を待つ（sleepループを直接待たない）。

## 3. スクリーンショットを撮る

```bash
mkdir -p work/screenshots
xcrun simctl io <UDID> screenshot work/screenshots/<name>.png
```

相対パスは現在のディレクトリ基準になる。意図しない場所に書き込まないよう、`cd`した後は絶対パスで書くか、元のディレクトリに戻って実行すること。

`xcrun simctl screenshot <path>`という短縮形は**存在しないサブコマンド**で、usageが表示されるだけなので使わない（`io <UDID> screenshot`が正）。

撮った画像は Read ツールで開いて目視確認する。画面録画が必要なら`xcrun simctl io <UDID> recordVideo <path>.mp4`（Ctrl+C相当のSIGINTで停止）。

## 4. 要素の取得とタップ — 座標を目算しない

（この節の`idb`を使う操作は、idb導入済みの場合のみ。未導入の場合は末尾の`simctl`コマンドだけ使える。）

`idb ui describe-all`が画面全体のアクセシビリティツリーをJSONで返す。`jq`で要素名と座標の一覧にすると読みやすい。

```bash
idb ui describe-all --udid <UDID> \
  | jq -r '.[] | select(.AXLabel != null) | "\(.type)\t\(.AXLabel)\t\(.frame.x),\(.frame.y) \(.frame.width)x\(.frame.height)"'
```

```
Application	MyApp	0,0 402x874
Heading	設定	179,76 44x28
Button	アイコンを変更	140.2,230 121.6x48
StaticText	メモ一覧	70.6,818.5 45x40
```

特定の要素だけ見たい場合:

```bash
idb ui describe --udid <UDID> --match-key AXLabel "マップ"
```

### タップはラベル指定が第一選択

`idb ui tap`は座標だけでなく**アクセシビリティマーカー（文字列）**を直接受け取れる。座標計算を挟まない分こちらが確実なので、ラベルが取れる要素にはこれを使う。

```bash
idb ui tap --udid <UDID> --match-key AXLabel "メモ一覧"
```

座標でタップする場合は`describe-all`の`frame`の中心（`x + width/2`, `y + height/2`）をそのまま渡す。

```bash
idb ui tap --udid <UDID> 93 838
```

### 座標系の罠: スクリーンショットはピクセル、idbはポイント

**スクリーンショット画像の座標とidbに渡す座標は一致しない。** 例えばiPhone 17では画像が1206x2622ピクセル、`describe-all`/`tap`が扱うのは402x874ポイントで、**3倍のずれ**がある。

そのため、**スクリーンショットを目視してピクセル座標を目算し、そのまま`idb ui tap`に渡すのは必ず失敗する。** 座標は`describe-all`の`frame`から取り、画像から読む必要がある場合のみ`ピクセル ÷ スケール（Retina系は3、一部は2）`で換算する。スケールは`スクリーンショットの幅 ÷ describe-allのApplication要素のframe.width`で確認できる。

### ラベルが取れない要素

アクセシビリティラベルを持たないアイコンのみのビューは`describe-all`に現れないことがある。その場合は、アプリ側にアクセシビリティラベルを一時的に付けるか、近傍の既知要素からの相対位置で見積もる。座標が分かっている点に何があるかは`idb ui describe-point <x> <y>`で逆引きできる。

### その他の操作

`idb ui`のサブコマンドで一通りの操作ができる: `swipe` / `text`（文字入力） / `key` / `button`（ホームボタン等） / `pinch` / `drag-and-drop`（`idb ui --help`で確認）。詳細は`idb ui <subcommand> --help`。

URLを開く（ディープリンクの検証など）、権限の付与・リセット、プッシュ通知の送信は`simctl`で行う。

```bash
xcrun simctl openurl <UDID> "<url>"
xcrun simctl privacy <UDID> grant photos <bundle-id>     # reset も可
xcrun simctl push <UDID> <bundle-id> payload.json
```

## 5. タップが反応しない場合はヒットターゲットのサイズを疑う

（idb導入済みの場合のみ。）

小さいアイコン（14pt角など）に直接タップ処理を付けただけだと、正確な座標を渡しても反応しないことがある。タップが繰り返し無反応な場合、アプリのロジックを疑う前に、まず座標系（4節）とヒットエリアの大きさ（目安は44pt以上）で切り分けること。

`idb ui tap`の`--api`は、マーカー指定時が`ax`（アクセシビリティ経由の押下）、座標指定時が既定で`hid`（実際のタッチイベント）になる。**`ax`はヒットエリアの問題を迂回してしまう**ため、ヒットエリアの不具合を再現・検証したいときは座標指定（`hid`）で確認する。

## 6. よくある環境要因の落とし穴

- **`simctl`/`idb`のサンドボックスエラー**: 0節の通り`dangerouslyDisableSandbox: true`が必要。接続エラーを見たら、まずシミュレータの異常ではなくこれを疑う。
- **`idb connect`の切れ**: シミュレータ再起動やマシンのスリープ後に`No Companion Connected`になる。`idb connect <UDID>`で再接続する。
- **物理iPhoneへの誤デプロイ**: 2節の通り、デプロイ先は必ずUDIDで明示する。
- **シミュレータの状態汚れ**: `xcrun simctl erase <UDID>`で初期化できる（起動中なら先に`xcrun simctl shutdown <UDID>`）。アプリだけ入れ直したい場合は`xcrun simctl uninstall <UDID> <bundle-id>`。
