# ui-core-verify

Android・iOS 共通の UI 検証ループ(`ui-verify-loop`)と、その部品を提供する共有プラグイン。通常は `ui-android-emu-verify` / `ui-ios-sim-verify` から依存されて使う。単体では、エミュレータ・シミュレータの操作手段を持たない。

提供するもの:
- スキル: `ui-verify-loop`(検証ループ)、`ui-verify-result-save`(結果の保存)、`mobile-screen-vision-analyze` / `mobile-screen-vision-compare`(評価観点)
- agent: `ui-checker`(スクリーンショットの判定。判定のみで副作用なし)
- MCP: `figma`(Figma の画像と構造情報の取得)
- スクリプト: 画像・座標の標準サイズへの正規化、Decision AI の呼び出し(`decide.py`)

ループの手順は [skills/ui-verify-loop/SKILL.md](skills/ui-verify-loop/SKILL.md)、手元での動作確認は [skills/ui-verify-loop/README.md](skills/ui-verify-loop/README.md) を参照。

## 使う側に求めること

### 必須

| 要件 | 内容 |
|---|---|
| 操作スキルのプラグイン | Android は `android-emulator-operate`、iOS は `ios-simulator-operate`。通常は `ui-android-emu-verify` / `ui-ios-sim-verify` を入れれば、依存として一緒に入る。`--plugin-dir` でロードする場合は、依存先も含めて指定する(解決できないとプラグインごとロードされない) |
| 画像を伸縮できるツール | `sips`(macOS 標準)、ImageMagick、Python + Pillow のいずれか。どれも無いと、画像の正規化ができない |
| Python 3 | `scale-structure.py`(構造情報の座標の伸縮)と `decide.py` の実行に使う。標準ライブラリだけで動く |
| アプリのビルド・起動方法 | プロジェクトごとに違うため、このプラグインでは決めない。README や CLAUDE.md / AGENTS.md に書いておくと、聞き返されずに済む |
| 実行環境 | **Claude Code 前提。** `ui-checker` agent は Claude Code 専用で、Codex・Devin には配られない(agent が要る場合は `agents/ui-checker.md` を対象プロジェクトの `.claude/agents/` に置いて、`sync-devin-codex` で変換する) |

### Figma と比較する場合のみ

| 要件 | 内容 |
|---|---|
| `FIGMA_API_KEY` | Claude Code を起動した環境の環境変数に設定する。未設定でも MCP サーバーは接続済みと表示されるが、ツール呼び出しが認証エラーになる。依頼文に Figma への言及が無い場合は、Figma を呼ばないので不要 |
| `npx`(Node.js) | `figma` MCP サーバー(`figma-developer-mcp`)の起動に使う |

### Decision AI(OpenAI Decisions API)を使う場合のみ(任意)

修正ループ中の「期待の要素が画面に欠けていないか」の事前判定を高速化できる。**次の 2 つが両方そろったときだけ**有効になり、そろわなければ従来どおり `ui-checker` だけで動く。

1. **`DECISION_AI`**: 利用するプロジェクトの `.claude/settings.json` の `env` に設定する(秘密ではないのでコミットしてよい)。

   ```json
   { "env": { "DECISION_AI": "1" } }
   ```

2. **`OPENAI_API_KEY`**: OpenAI の API キー(https://platform.openai.com/api-keys で発行)。**リポジトリの外、または `.gitignore` 済みのファイルに置き、direnv などで環境変数に読み込む。** `settings.json`・`.mcp.json` などコミットされるファイルには書かない。

追加で必要になるもの・知っておくこと:

- **ネットワーク**: サンドボックスを使っている場合は、`api.openai.com` への通信の許可が必要(許可が無いと、通信できず従来方式にフォールバックする)。
- **データの送信先**: 画像(スクリーンショット・Figma のリファレンス画像)と、画面上のテキスト(期待・構造情報)が OpenAI に送られる。個人情報・秘密情報が写る可能性がある画面では有効にしない。ZDR などのデータの扱いは、OpenAI 側の契約・設定に依存する。
- **料金**: API の利用料金がかかる(入力は 100 万トークンあたり 0.10 ドル。正規化した画像 1 枚と短い期待で、1 回あたり入力 1,800 トークン前後)。
- **キー未設定の扱い**: `DECISION_AI` が有効でキーが無いと、スキルはユーザーに伝えたうえで、Decision AI なしで進めてよいか確認する(黙って切り替えない)。`DECISION_AI` が無効なら、キーがあっても通信しない。
- **キーの確認方法**: `python3 -I skills/ui-verify-loop/scripts/decide.py --check` を使う(値を出さず、終了コードだけで返す)。`env`・`printenv`・`echo "$OPENAI_API_KEY"` は使わない。
- **完了の判定は `ui-checker` が行う。** Decision AI は、要素が明らかに欠けている周回の高速化にだけ使い、全部そろっていても最終確認は `ui-checker` に任せる。

## テスト

```bash
python3 -m unittest discover -s plugins/ui-core-verify/tests -v
```

API キーは不要(`decide.py` は偽の応答でテストしている)。evals の実行は、リポジトリの [CONTRIBUTING.md](../../CONTRIBUTING.md) を参照。
