# maestro-scenario-author

ユーザーと対話しながら、Maestro の E2E シナリオ(flow YAML)を作成・検証するプラグイン。実機画面の要素を確認しつつ、1 ステップずつ組み立てて、通ることを確かめる。

提供するもの:
- スキル: `maestro-scenario-author`([SKILL.md](skills/maestro-scenario-author/SKILL.md))
- MCP: `maestro`(`maestro mcp --no-viewer`。[.mcp.json](.mcp.json))。Maestro MCP の `inspect_screen` で要素を確認し、`run` で flow を実行する

CI への組み込みは、`maestro-ci-setup` を使う。

## 使う側に求めること

| 要件 | 内容 |
|---|---|
| `maestro` | 必須(`command -v maestro`)。無い場合、スキルは https://docs.maestro.dev/getting-started/installing-maestro を案内する(勝手にインストールしない)。Java 17 以上が必要 |
| エミュレータ / シミュレータと対象アプリ | 起動済みで、アプリがインストール済みであること。起動やインストールは `android-emulator-operate` / `ios-simulator-operate` があれば、それに従う |
| 対象アプリの情報 | `appId`(Android の application id と iOS の bundle id は、異なることが多い)、既存 flow の置き場所と命名 |

### MCP サーバーについて

- **Claude Code では、プラグインを有効化した後、MCP サーバーを認識させるために再起動(または `/mcp` で確認)が必要。** Codex は `.codex-plugin/plugin.json` の `mcpServers`、Devin はプラグイン直下の `.mcp.json` で、同じサーバーを読む。
- MCP のツールが見つからないときは、CLI(`maestro hierarchy` / `maestro test`)で同じことをする。
- Bash ツールのサンドボックス内では、`simctl` / `adb` / Maestro がデバイスと通信できないことがある。その場合は `dangerouslyDisableSandbox: true` で実行する。

## 使い方

次のような依頼で動く。

- 「Maestro のシナリオを作って」「E2E テストを書きたい」
- 「このフローを Maestro にして」「Maestro の flow を直して」

## 注意

- **flow やアプリを Maestro Cloud に送信しない**(ユーザーが明示した場合を除く)。クラウド系のツール(`run_on_cloud` など)は使わない。
- 認証情報・トークンは flow に直書きせず、`env`(`maestro test -e KEY=VALUE`)で渡す。
- 破壊的な操作(課金・本番データの削除・外部への送信)を含む flow は、テスト用の環境・アカウントでだけ動かす前提かを確認する。
- 通っていない flow は、確認済みとして渡さず、現状と原因を明記する。

## Decision AI(任意): ステップ後の進行確認

手順 3 の各ステップの後に、「目的の画面になっているか」「権限ダイアログなどが前面に出ていないか」を、スクリーンショットから OpenAI Decisions API で判定できる(`SKILL.md` の手順 3.5)。目視確認のための `take_screenshot` を、自分で読まずに済ませる用途。

- 有効になる条件は、`ui-core-verify` と同じ。環境変数 `DECISION_AI`(利用するプロジェクトの `settings.json` の `env`)と `OPENAI_API_KEY`(リポジトリの外。direnv など)の**両方**がそろったときだけ。そろわなければ従来どおり動く。要件(キーの置き場所・送信されるデータ・料金・キーの確認方法)は、[ui-core-verify の README](../ui-core-verify/README.md) を参照。
- キーの存在確認は `python3 -I scripts/decide.py --check`(値を出さず、終了コードだけで返す)。`env`・`printenv`・`echo "$OPENAI_API_KEY"` は使わない。
- 画像が OpenAI に送られる。個人情報・秘密情報が写る画面では使わない。
- `scripts/decide.py` と `scripts/normalize-image.sh` は、`ui-core-verify` と同じものを置いている(プラグインは互いのファイルを参照できないため)。変えるときは 3 か所を揃える(`ui-core-verify` のテストが、同一かを確認する)。
- 画面の保存に、`android-emulator-operate` / `ios-simulator-operate` の手順(`adb` / `simctl`)を使う。これらのプラグインが無ければ、この機能は使わない。
- 判定結果は `proceed`(次のステップへ進む)、`inspect`(自分で確かめる)。`inspect_screen` と、最後に flow を通す実行(`maestro test`)は省かない。
- 効果が出るのは、画像を読む回数が多いシナリオ。短いシナリオでは、ほとんど変わらない。
