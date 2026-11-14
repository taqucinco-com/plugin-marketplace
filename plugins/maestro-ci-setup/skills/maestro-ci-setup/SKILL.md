---
name: maestro-ci-setup
description: MaestroのE2EをGitHub Actions上で動かすCI環境（Androidエミュレータ=ubuntu、iOSシミュレータ=macOS）を整える。アプリのビルドとMaestro実行のjob分離、エミュレータ/シミュレータの起動、Maestroのzip導入とキャッシュ、画面録画、JUnitレポートとartifactの保存までを含むワークフローを、プロジェクトに合わせて生成する。「MaestroをCIで動かしたい」「E2EのGitHub Actionsを作って」「エミュレータ/シミュレータでMaestroを回すworkflowが欲しい」といった依頼で使う。シナリオ(flow)自体の作成は`maestro-scenario-author`を使う。
---

# Maestro CI 環境の構築（GitHub Actions）

`templates/`のワークフロー雛形を、対象プロジェクトに合わせて埋めて`.github/workflows/`に置く。雛形は実運用で動いている構成を一般化したもので、**プロジェクトごとに違う部分（ビルド手順・appId・flowの場所）は`__TODO__`で残してある**。

- `templates/android_emulator_maestro_test.yaml`: ubuntu。APKビルド → エミュレータ起動 → Maestro
- `templates/ios_simulator_maestro_test.yaml`: macOS。シミュレータ向けビルド → シミュレータ起動 → Maestro

## 構成の方針（雛形が守っていること。崩すときは理由を説明する）

- **ビルドとMaestro実行はjobを分ける。** 同じrunnerだとディスクを食い合い`no space left`になりうる。成果物（APK / `Runner.app`）はartifactで受け渡す。
- **Maestroはビルドしない。** インストール済みのアプリを`appId`で起動するだけ。だからインストール直後に「flowの`appId`と実際のアプリが一致するか」を検証するステップを置き、不一致なら早く失敗させる（AndroidのapplicationIdとiOSのbundle idは異なるので、flowもプラットフォーム別に分ける）。
- **Maestroはbrewではなくリリースzipを直接展開する。** brewのformulaはopenjdkを別途入れようとするため。`~/maestro`をキャッシュする。JavaはMaestroの要件（17以上）を満たすものをrunner側で用意する。
- **iOSはシミュレータの起動待ちを遅らせる。** 新規作成したシミュレータの初回起動はData Migrationで数分かかる。`simctl boot`の直後ではなく、アプリをインストールする直前に`simctl bootstatus`で待つ。ランタイムとデバイスは固定せず、利用可能なものから選ぶ。
- **画面録画・JUnitレポート・debug-outputをartifactに保存する。** 失敗の調査材料なので、保存系ステップは`if: always()`にする。
- 失敗時にエミュレータ/シミュレータのログを出す。

## 手順

### 1. 現状を調べる（聞く前に調べる）

- 既存の`.github/workflows/`（命名・使っているactionのバージョン・`environment`・secretsの扱い）
- Maestroのflowの場所（無ければ`maestro-scenario-author`を案内）と、`appId`
- アプリのビルド方法（Flutter / React Native / ネイティブ等）と、既存CIのビルドステップ（流用できるもの）

### 2. ユーザーに確認する（調べて分からなかったものだけ）

- 対象プラットフォーム（Android / iOS / 両方）
- トリガー。雛形は`workflow_dispatch`（手動）のみ。E2EはCIコストが高い（特にmacOSランナーは割高）ので、`pull_request`や`schedule`へ広げるか、ラベル/パス条件を付けるかを確認する。**勝手に自動実行のトリガーを足さない。**
- ビルドに必要なsecretsと`environment`名。**値は聞かない・書かない。** 名前だけ決めて、登録はユーザーに依頼する。
- Maestroのバージョン（既定は雛形の`MAESTRO_VERSION`。最新は https://github.com/mobile-dev-inc/maestro/releases で確認する）

### 3. 雛形を埋めて配置する

1. 雛形を`.github/workflows/`へコピーする（ファイル名はプロジェクトの慣習に合わせてよい）。
2. `__TODO__`を全て埋める。ビルドjobの中身はプロジェクトの既存ビルド手順に置き換える。最終的に`grep -n "__TODO" <file>`が空になることを確認する。
3. 使うactionのバージョンは、プロジェクトの既存workflowに合わせる。無ければ最新の安定版を確認して固定する。
4. `actionlint`があれば実行する（`command -v actionlint`）。無ければ導入を案内するだけにして、勝手に入れない。

### 4. 動作確認

- ワークフローは**ローカルでは完全には検証できない**。`workflow_dispatch`で実際に1回走らせてもらうのが確実。実行にはpush・実行権限・コストが伴うので、こちらから勝手に起動せず、ユーザーに依頼するか許可を取る。
- 実行して失敗した場合のよくある原因: appIdの不一致、AVD/シミュレータの起動タイムアウト、ビルド成果物のパス違い、secrets未登録、`timeout-minutes`不足。ログを見て、原因を特定してから直す。
- 走らせていない状態では「CIで動作を確認済み」とは言わない。「雛形に基づいて作成した。未実行」と正確に報告する。

## 注意

- secretsは`${{ secrets.NAME }}`で参照し、値をログに出さない（`echo`しない）。
- デバッグ用keystore等をsecretsからデコードする場合も、ファイルをartifactに含めない。
- iOS実機向けの署名が必要なビルドは対象外。シミュレータ向けビルドは署名不要。
