# ui-verify-loop

モバイルアプリ(Android・iOS 共通)の UI 検証ループの手順。本体は [SKILL.md](SKILL.md)。このファイルは、人間がこのディレクトリの資材を手元で試すための案内で、スキルとしては読み込まれない。

## ディレクトリ

| パス | 内容 |
|---|---|
| `SKILL.md` | スキル本体(検証ループの手順) |
| `scripts/` | 画像・座標の正規化(`normalize-image.sh`、`scale-structure.py`)と、Decision AI の呼び出し(`decide.py`。`pr-ui-evidence` と `maestro-scenario-author` にも同じものを置いている。変えるときは 3 か所を揃える) |
| `decision/` | Decision AI に渡す共通の質問(`base-questions.json`) |
| `reference/` | Decision AI の動作を手元で確認するための画像・期待・スクリプト |

## Decision AI(任意)を使うための環境変数

`decide.py`(OpenAI Decisions API)を使う処理には、次の 2 つが**両方**必要。

| 環境変数 | 内容 |
|---|---|
| `DECISION_AI` | `1`(`true`/`on`/`yes` も可)。利用するプロジェクトの `settings.json` の `env` で有効にする。`reference/` のスクリプトは、スクリプト内で設定する |
| `OPENAI_API_KEY` | OpenAI の API キー(https://platform.openai.com/api-keys で発行)。**`reference/` のスクリプトを実行するには、これが必須** |

### `OPENAI_API_KEY` の設定

- **キーはリポジトリの外、または `.gitignore` 済みのファイルに置く。** `settings.json`・`.mcp.json`・スクリプト・SKILL.md には書かない。
- 例: リポジトリのルートの `.env`(`.gitignore` 済み)に `OPENAI_API_KEY=<キー>` を書き、direnv(`.envrc` に `dotenv`)で読み込んでから Claude Code やスクリプトを起動する。`.env` をコミットしないこと(`git check-ignore -v .env` で無視されていることを確認できる)。
- 設定されているかの確認は、**値を表示しない方法**で行う。

  ```bash
  python3 -I plugins/ui-core-verify/skills/ui-verify-loop/scripts/decide.py --check; echo "exit=$?"
  ```

  `exit=0` が使える、`3` が `DECISION_AI` は有効だがキー未設定、`10` が `DECISION_AI` が無効。`env`・`printenv`・`echo "$OPENAI_API_KEY"` は使わない(値が画面・ログ・会話に出る)。
- キー未設定のままスクリプトを実行すると、終了コード 3(`curl-example-ok.sh` は 3)で止まる。通信は行われない。

## `reference/` の動作確認スクリプト

リポジトリのルートで実行する。**実行すると画像と画面上のテキストが OpenAI に送られ、API の利用料金が発生する**(1 回あたり入力 1,800 トークン前後)。

```bash
sh plugins/ui-core-verify/skills/ui-verify-loop/reference/check-example-ok.sh   # 要素がそろった画面 → next=ui_checker / reason=all_present
sh plugins/ui-core-verify/skills/ui-verify-loop/reference/check-example-ng.sh   # Switch が欠けた画面 → next=fix / reason=missing
sh plugins/ui-core-verify/skills/ui-verify-loop/reference/curl-example-ok.sh    # OK の画面を curl で送る(API の生のレスポンスを見る)
```

- `check-example-*.sh` は、判定が期待と違うと終了コード 1 で終わる。`--raw` を付けると、API の生のレスポンスが標準エラーに出る。
- `curl-example-ok.sh` は `--show-request` で、送るリクエスト(画像は省略)を標準エラーに出す。`jq` と `curl`(7.55 以降)が必要。
- `_check-example.sh` は、OK/NG の共通処理(直接は実行しない)。質問の文言を変えるときは、`curl-example-ok.sh` の質問も揃える。
- `example_ok.png` / `example_ng.png` / `expect.txt` が入力。画像は元の大きさのまま置いてあり、スクリプトが一時ディレクトリで 480x1040 に正規化する(リポジトリには残らない)。

## テスト(API 不要)

```bash
python3 -m unittest discover -s plugins/ui-core-verify/tests -v
```

`decide.py` のゲート(キーの有無・フラグ)、リクエストの組み立て、判定(`summary`)、エラー時にキーを出力しないことは、偽の応答でテストしている。実際の API は呼ばない。
