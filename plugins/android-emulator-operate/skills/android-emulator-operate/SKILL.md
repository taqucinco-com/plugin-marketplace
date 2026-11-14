---
name: android-emulator-operate
description: Androidエミュレータを adb（エミュレータの確認・アプリのインストールと起動・スクリーンショット・要素ツリー取得・タップ・スワイプ・文字入力）で操作する共通手順。エミュレータ上でアプリを動かして画面を確認・操作したいとき、UI検証や動作確認の前提として使う。adb未導入の場合はインストールを案内する。アプリの技術スタック（ネイティブ・クロスプラットフォーム等）には依存しない。
---

# Androidエミュレータ操作（adb）

Androidエミュレータを`adb`で操作するための共通手順。**エミュレータとアプリを操作する方法だけを扱い、結果（スクリーンショットや要素ツリー）をどう評価するかはこのスキルの範囲外**（呼び出し元が行う）。

## 0. 前提

- Android SDKの`platform-tools`（`adb`）と`emulator`が使えること。AVD（仮想デバイス）が1つ以上作成済みであること。
- スクリーンショットなどの成果物は、プロジェクトの`.gitignore`で除外されているディレクトリ（例: `work/screenshots/`）に保存する。保存先がなければユーザーに確認するか、一時ディレクトリを使い、リポジトリ直下に散らかさない。
- Bashツールのサンドボックスは、作業ディレクトリとセッション専用の`$TMPDIR`にしか書き込めない。ファイルを書き出すときは、裸の`/tmp`直下ではなく作業ディレクトリ配下か`$TMPDIR`を使う。

## 0.5 adbの有無を確認する（最初に必ず行う）

```bash
command -v adb emulator || ls "$ANDROID_HOME/platform-tools/adb" "$ANDROID_HOME/emulator/emulator"
```

### 見つからない場合: インストールを促す

勝手にインストールせず、**ユーザーに次のいずれかを案内して、導入するか確認する**。`adb`が無いとエミュレータの確認・アプリの操作・スクリーンショット取得がすべてできない、と理由も添える。

- **Android Studioを入れる**（エミュレータとAVDも含めて揃えるならこちら）: https://developer.android.com/studio をインストールし、SDK Managerで「Android SDK Platform-Tools」と「Android Emulator」を導入、Device ManagerでAVDを作成する。
- **adbだけ入れる**（実機やすでにあるエミュレータを操作するだけでよい場合）: `brew install --cask android-platform-tools`。公式の配布ページは https://developer.android.com/tools/releases/platform-tools 。

導入後、`adb version`で動作を確認する。SDKの場所は`$ANDROID_HOME`（未設定なら`~/Library/Android/sdk`が既定）で、`$ANDROID_HOME/platform-tools`と`$ANDROID_HOME/emulator`をPATHに通すか、フルパスで呼び出す。

### それでもインストールされない場合

ユーザーが導入しない・できないと答えた場合、**このスキルでできる操作はない**（`adb`以外にタップやスクリーンショットの手段がない）。`adb`コマンドを実行して失敗を繰り返さず、「adb未導入のためエミュレータを操作・検証できなかった」と結果に明記して呼び出し元に返す。確認できていない画面を確認済みとして報告しないこと。

## 1. エミュレータを起動する

まず`adb devices`で確認し、既に`emulator-5554`等が`device`状態で起動済みなら本節はスキップする。

```bash
adb devices
```

起動していない場合は、利用可能なAVDを確認して起動する。

```bash
"$ANDROID_HOME/emulator/emulator" -list-avds
nohup "$ANDROID_HOME/emulator/emulator" -avd <AVD名> > "$TMPDIR/emulator.log" 2>&1 &
disown
```

起動待ちは`run_in_background`付きBashで行い、完了通知を待つ（sleepループを直接待たない）。

```bash
until adb shell getprop sys.boot_completed 2>/dev/null | grep -q 1; do sleep 2; done
```

`adb devices`の一行目に`emulator-5554`のようなシリアルが出る。複数デバイス（実機や別エミュレータ）が同時に接続されていると、`-s`を省いたコマンドは「more than one device/emulator」で失敗するか、意図しないデバイスに実行される。**以降のコマンドは必ず`adb -s <シリアル>`で対象を明示する。**

## 2. アプリをインストールして起動する

ビルド済みのAPKがあれば、`adb`でインストール・起動する。

```bash
adb -s <シリアル> install -r /path/to/app-debug.apk
adb -s <シリアル> shell monkey -p <パッケージ名> -c android.intent.category.LAUNCHER 1
```

- ビルド方法はプロジェクトによって異なる（Gradle、各種フレームワークのCLIなど）。ビルド自体はこのスキルの範囲外で、呼び出し元のプロジェクトの手順に従う。
- 起動するActivityが分かっている場合は`adb -s <シリアル> shell am start -n <パッケージ名>/<Activity名>`でもよい。
- パッケージ名はAPKから取れる: `aapt dump badging app-debug.apk | grep package`（`$ANDROID_HOME/build-tools/<version>/aapt`）。
- アプリの終了・再起動・データ消去:

  ```bash
  adb -s <シリアル> shell am force-stop <パッケージ名>
  adb -s <シリアル> shell pm clear <パッケージ名>
  adb -s <シリアル> uninstall <パッケージ名>
  ```

- 長時間かかるビルドや起動待ちは`run_in_background`付きBashで行い、完了通知を待つ（sleepループを直接待たない）。

## 3. スクリーンショットを撮る

```bash
mkdir -p work/screenshots
adb -s <シリアル> exec-out screencap -p > work/screenshots/<name>.png
```

相対パスは現在のディレクトリ基準になる。意図しない場所に書き込まないよう、`cd`した後は絶対パスで書くか、元のディレクトリに戻って実行すること。

撮った画像は Read ツールで開いて目視確認する。画面録画が必要なら`adb -s <シリアル> shell screenrecord /sdcard/rec.mp4`（Ctrl+Cで停止）し、`adb pull`で取り出す。

## 4. タップ操作 — 座標は必ずuiautomatorで正確に取る

**Readツールで表示された画像を目視して「だいたいこの位置」とピクセル座標を目算し、表示倍率だけ掛け戻して`adb shell input tap`する方法は失敗しやすい。** 視認による見積もりは何度も外れうる（実際の要素位置が目算より数百px下にあった、など）。代わりに以下の手順で正確な実座標を取得すること。

```bash
adb -s <シリアル> shell uiautomator dump /sdcard/wd.xml
adb -s <シリアル> pull /sdcard/wd.xml work/wd.xml
# 1要素ぶんの <node ...> を取り出してから bounds を抜く（属性の途中に resource-id の "/" があっても止まらない）
grep -o '<node[^>]*text="対象テキスト"[^>]*>' work/wd.xml | grep -o 'bounds="\[[0-9,]*\]\[[0-9,]*\]"'
# content-desc で探す場合は text="..." を content-desc="..." に変える
```

保存先は作業ディレクトリ配下（例: `work/wd.xml`）にする。`cd`した状態だと相対パスが意図しない場所に書き込まれる点は3節と同様に注意すること。

`bounds="[x1,y1][x2,y2]"`はデバイスの実ピクセル座標そのもの（スケーリング不要）。中心 `((x1+x2)/2, (y1+y2)/2)` をそのまま`adb shell input tap`に渡す。中心の計算は暗算せず、コマンドで求める。

```bash
grep -o '<node[^>]*text="対象テキスト"[^>]*>' work/wd.xml | grep -o 'bounds="[^"]*"' | grep -o '[0-9]\+' | paste -sd' ' - | awk '{printf "%d %d\n", ($1+$3)/2, ($2+$4)/2}'
```

```bash
adb -s <シリアル> shell input tap <x> <y>
```

### その他の操作

```bash
adb -s <シリアル> shell input swipe <x1> <y1> <x2> <y2> [<ミリ秒>]   # スクロール・スワイプ
adb -s <シリアル> shell input text "hello"                          # 文字入力（スペースは %s、日本語は不可）
adb -s <シリアル> shell input keyevent KEYCODE_BACK                  # 戻る / KEYCODE_HOME / KEYCODE_ENTER
adb -s <シリアル> shell am start -a android.intent.action.VIEW -d "<url>"   # URLを開く（ディープリンクの検証など）
```

### ラベルが取れない要素

アクセシビリティラベル（`content-desc`）もテキストも持たないアイコンのみのビューは、dumpに現れないことがある。その場合は、アプリ側にラベルを一時的に付けるか、近傍の既知要素からの相対位置で見積もる。

## 5. タップが反応しない場合はヒットターゲットのサイズを疑う

小さいアイコン（14dp角など）に直接タップ処理を付けただけだと、正確な座標を渡しても反応しないことがある。タップが繰り返し無反応な場合、アプリのロジックを疑う前に、まず座標の取り方（4節）とヒットエリアの大きさ（目安は48dp以上）で切り分けること。

## 6. よくある環境要因の落とし穴

- **`INSTALL_FAILED_INSUFFICIENT_STORAGE`**: エミュレータの`/data`が埋まりやすい（プリインストールアプリ込みで数GB中数百MBしか空きが無いことがある）。`adb -s <シリアル> shell df /data`で確認し、埋まっていたら`adb -s <シリアル> emu kill`してから`-wipe-data`付きで再起動する。
- **プリインストールアプリの無関係なダイアログ**（例: "Messages isn't responding"）が前面に被ることがある。スクリーンショットに見慣れないダイアログが写っていたら、まずそれを閉じてから本来の検証を続ける。
- **`adb devices`が`offline`/`unauthorized`**: `adb kill-server && adb start-server`で再起動する。エミュレータが起動途中の場合は1節の`sys.boot_completed`を待つ。
