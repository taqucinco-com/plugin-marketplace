# maestro-ci-setup

Maestro の E2E を、GitHub Actions 上で動かす CI 環境(Android エミュレータ = ubuntu、iOS シミュレータ = macOS)を整えるプラグイン。アプリのビルドと Maestro 実行の job 分離、エミュレータ / シミュレータの起動、Maestro の導入とキャッシュ、画面録画、JUnit レポートと artifact の保存までを含むワークフローを、プロジェクトに合わせて生成する。

提供するもの:
- スキル: `maestro-ci-setup`([SKILL.md](skills/maestro-ci-setup/SKILL.md))
- ワークフローの雛形(`__TODO__` を埋めて使う):
  - [Android](skills/maestro-ci-setup/templates/android_emulator_maestro_test.yaml)
  - [iOS](skills/maestro-ci-setup/templates/ios_simulator_maestro_test.yaml)

シナリオ(flow)自体の作成は、`maestro-scenario-author` を使う。

## 使う側に求めること

| 要件 | 内容 |
|---|---|
| GitHub Actions を使うリポジトリ | `.github/workflows/` にワークフローを置く |
| Maestro の flow | あること(無ければ `maestro-scenario-author`)。`appId` が分かっていること |
| アプリのビルド方法 | Flutter / React Native / ネイティブなど。雛形のビルド job を、プロジェクトの既存ビルド手順に置き換える |
| ビルドに必要な secrets と `environment` | **名前だけ**決める。値の登録はユーザーが行う(スキルは値を聞かない・書かない) |
| `actionlint`(任意) | あれば、生成したワークフローの検証に使う。無ければ導入を案内するだけ |

## 使い方

次のような依頼で動く。

- 「Maestro を CI で動かしたい」「E2E の GitHub Actions を作って」
- 「エミュレータ / シミュレータで Maestro を回す workflow が欲しい」

## 注意

- **ワークフローは、ローカルでは完全には検証できない。** `workflow_dispatch` で実際に 1 回走らせて確認する。実行は push・実行権限・コストを伴うので、スキルが勝手に起動せず、ユーザーに依頼するか許可を取る。走らせていない状態は、「雛形に基づいて作成した。未実行」と報告する。
- 雛形のトリガーは `workflow_dispatch`(手動)のみ。E2E は CI コストが高い(特に macOS ランナー)ので、`pull_request` や `schedule` に広げるかは、ユーザーに確認する。
- secrets は `${{ secrets.NAME }}` で参照し、値をログに出さない。keystore などをデコードする場合も、artifact に含めない。
- iOS 実機向けの署名が必要なビルドは対象外(シミュレータ向けビルドは署名不要)。
