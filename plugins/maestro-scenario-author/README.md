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
