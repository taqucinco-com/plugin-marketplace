# android-emulator-operate

Android エミュレータを `adb` で操作する共通手順を提供するプラグイン。エミュレータの確認・起動、アプリのインストールと起動、スクリーンショット、要素ツリーの取得、タップ・スワイプ・文字入力を扱う。**操作の方法だけを扱い、結果の評価はしない**(評価は呼び出し元の `ui-core-verify` などが行う)。

提供するもの:
- スキル: `android-emulator-operate`([SKILL.md](skills/android-emulator-operate/SKILL.md))

## 使う側に求めること

| 要件 | 内容 |
|---|---|
| Android SDK の `platform-tools`(`adb`)と `emulator` | 必須。無い場合、スキルは導入を案内する(勝手にインストールしない)。Android Studio を入れるか、`brew install --cask android-platform-tools` で `adb` だけ入れる |
| AVD(仮想デバイス) | 1 つ以上作成済みであること |
| 成果物の保存先 | スクリーンショットなどは、`.gitignore` 済みのディレクトリ(例: `work/screenshots/`)に保存する。無ければスキルがユーザーに確認する |

`adb` を導入しない・できない場合、このスキルでできる操作はない。その旨を結果に明記して呼び出し元に返す(確認できていない画面を、確認済みとして報告しない)。

## 使い方

通常は、`ui-android-emu-verify` や `pr-ui-evidence` から呼ばれる。単独でも、エミュレータ上でアプリを動かして画面を確認・操作したいときに使える。

## evals

`adb` が無い環境での振る舞い(導入の案内・虚偽の報告をしないこと)を確認する evals がある。実行方法は [CONTRIBUTING.md](../../CONTRIBUTING.md) を参照(ローカルのみ。CI では実行しない)。

```bash
claude plugin eval plugins/android-emulator-operate --trust-plugin --scaffold --runs 1 --ablation none --no-publish
```
