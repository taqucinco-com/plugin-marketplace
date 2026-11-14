# コントリビュート

## evals の実行(ローカルのみ)

evals は CI では実行しません。プラグインの挙動を変えたら、手元で実行してください。

```
claude plugin eval plugins/sync-devin-codex --trust-plugin --scaffold --allow-tools Bash --runs 1 --ablation none --no-publish
```

## ui-verify 系プラグインのテストと evals

### スクリプトのテスト(決定論的・API 不要)

```
python3 -m unittest discover -s plugins/ui-core-verify/tests -v
```

### 各プラグインの evals

```
claude plugin eval plugins/ui-core-verify --trust-plugin --scaffold --allow-tools Write --runs 1 --ablation none --no-publish
claude plugin eval plugins/ios-simulator-operate --trust-plugin --scaffold --runs 1 --ablation none --no-publish
claude plugin eval plugins/android-emulator-operate --trust-plugin --scaffold --runs 1 --ablation none --no-publish
```

### 複数プラグインにまたがる evals(ルーティング)

`ui-android-emu-verify` と `ui-ios-sim-verify` は他のプラグインに依存するため、評価時に依存先も読み込む必要がある。`plugins:` に指定できるのは対象の配下だけなので、リポジトリ直下の `evals/` に置き、リポジトリルートを対象にして実行する。**対象に `.` を指定すると全プラグインの evals が走る**ため、`--case` で絞ること。

```
claude plugin eval . --trust-plugin --scaffold --runs 1 --ablation none --no-publish --case 'routing-*'
```

- evals の `allowed_tools` に書けないツール(Bash・Write・Edit など)は、コマンド側の `--allow-tools` で許可する。`result-save` は `Write`、`sync-devin-codex` の evals は `Bash` が必要。
- 実機(エミュレータ・シミュレータ)が必要な検証ループ全体は、evals の対象外。手元の実機で確認する。
