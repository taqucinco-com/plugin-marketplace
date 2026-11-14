# コントリビュート

## evals の実行(ローカルのみ)

evals は CI では実行しません。プラグインの挙動を変えたら、手元で実行してください。

```
claude plugin eval plugins/sync-devin-codex --trust-plugin --scaffold --allow-tools Bash --runs 1 --ablation none --no-publish
```
