# pr-ui-evidence

PR の差分から、見た目が変わる画面を推定し、ベース(変更前)と PR ブランチ(変更後)をエミュレータ / シミュレータで動かして、同じ画面の before / after のスクリーンショットを撮り、PR 説明文に載せる証跡(Markdown)を作るプラグイン。

**撮影と整理が役割で、見た目の良し悪しの判定はしない**(判定が必要なら `ui-core-verify` の `ui-verify-loop` を使う)。

提供するもの:
- スキル: `pr-ui-evidence`([SKILL.md](skills/pr-ui-evidence/SKILL.md))

## 依存するプラグイン

| プラグイン | 役割 |
|---|---|
| `android-emulator-operate` | Android での起動・スクリーンショット・操作 |
| `ios-simulator-operate` | iOS での起動・スクリーンショット・操作 |

対象のプラットフォームの操作スキルが使えれば足りる。Codex・Devin ではプラグイン単位の依存を解決できないので、必要な操作プラグインを個別にインストールする。

## 使う側に求めること

| 要件 | 内容 |
|---|---|
| `git` と `gh` | PR の取得(`gh pr view` / `gh pr checkout`)とブランチの切り替えに使う |
| 作業ツリーの状態 | 未コミットの変更があると、ブランチ切り替えで失われうる。スキルが先にユーザーへ確認する |
| 対象プラットフォームの操作環境 | `android-emulator-operate` / `ios-simulator-operate` の要件を参照 |
| アプリのビルド・起動方法 | プロジェクトごとに違う。README や CLAUDE.md / AGENTS.md に書いておく。分からなければスキルがユーザーに聞く |
| 証跡の保存先 | `.gitignore` 済みのディレクトリ(例: `work/pr-evidence/<PR番号>/`)。無ければスキルがユーザーに確認する |

## 使い方

次のような依頼で動く。

- 「PR にスクリーンショットを付けて」「UI 変更の証跡を作って」「before/after を撮って」

影響する画面の候補と到達手順は、撮影の前にユーザーに提示して確認する。

## 注意

- **画像を PR に載せる(外部への公開)前に、方法をユーザーに確認する。** 公開リポジトリでは画像も公開される。
- スクリーンショットに、個人情報・秘密情報(メールアドレス、トークン、本番データ)が写っていないかを、公開前に確認する。
- PR 本文を更新するときは、既存の本文を残したまま、証跡セクションを追記する。実行前に最終的な本文をユーザーに見せる。

## Decision AI(任意): before / after の変更判定

画面ごとに、before と after が実質的に変わっているかを、OpenAI Decisions API で判定できる(`SKILL.md` の手順 3.5)。

- 有効になる条件は、`ui-core-verify` と同じ。環境変数 `DECISION_AI`(利用するプロジェクトの `settings.json` の `env`)と `OPENAI_API_KEY`(リポジトリの外。direnv など)の**両方**がそろったときだけ。そろわなければ従来どおり動く。要件(キーの置き場所・送信されるデータ・料金・キーの確認方法)は、[ui-core-verify の README](../ui-core-verify/README.md) を参照。
- キーの存在確認は `python3 -I scripts/decide.py --check`(値を出さず、終了コードだけで返す)。`env`・`printenv`・`echo "$OPENAI_API_KEY"` は使わない。
- 画像が OpenAI に送られる。個人情報・秘密情報が写る画面では使わない。
- `scripts/decide.py` と `scripts/normalize-image.sh` は、`ui-core-verify` と同じものを置いている(プラグインは互いのファイルを参照できないため)。変えるときは 3 か所を揃える(`ui-core-verify` のテストが、同一かを確認する)。
- 判定結果は `changed`(変更あり)、`unchanged`(変更なし)、`check`(決められない。自分で2枚を見る)。**`unchanged` でも、画面を証跡から外さず**、「変わっていない(自動判定)」と明記して載せる(変化の見落としを防ぐため)。
- 個人情報の写り込みの確認は、この判定とは別に、従来どおり公開前に人が行う。

## evals(ローカルのみ)

依存するプラグインを読み込む必要があるため、リポジトリ直下の `evals/` にある。実行方法は [CONTRIBUTING.md](../../CONTRIBUTING.md) を参照。

```bash
claude plugin eval . --trust-plugin --scaffold --allow-tools Write --runs 1 --ablation none --no-publish --case 'pr-evidence-*'
```
