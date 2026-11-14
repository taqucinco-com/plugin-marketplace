#!/usr/bin/env bash
# check-example-ok.sh / check-example-ng.sh の共通処理。直接は実行しない。
# 使い方: bash _check-example.sh <画像ファイル名> <期待する next> <期待する reason> [decide.py の追加オプション(--raw など)]
# 判定が期待と違うときは、終了コード 1 で終わる。
# 前提: 環境変数 OPENAI_API_KEY が設定済みであること(値はこのスクリプトでは扱わない・表示しない)。
set -euo pipefail

IMAGE_NAME="$1"
EXPECT_NEXT="$2"
EXPECT_REASON="$3"
shift 3

REF="$(cd "$(dirname "$0")" && pwd)"
SKILL="$(dirname "$REF")"

# 正規化画像は一時ディレクトリに作り、終了時に消す(リポジトリに残さない)
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

bash "$SKILL/scripts/normalize-image.sh" "$REF/$IMAGE_NAME" "$TMP/norm.png"

RESULT="$(DECISION_AI=1 python3 -I "$SKILL/scripts/decide.py" "$@" \
  --questions "$SKILL/decision/base-questions.json" \
  --element '見出し「メモ一覧」が画面の上部に表示されているか' \
  --element '見出しの右側に、リストとマップを切り替えるSwitchが表示されているか' \
  --element '画面の真ん中のかなり広い領域を、地図が占めているか' \
  --element '画面の下部にボトムナビゲーションが表示されているか' \
  --element-visual '地図の右上に、ズームと現在地のアイコンボタンが表示されているか' \
  --text '比較対象の期待='"$REF/expect.txt" \
  --image '実装のスクリーンショット='"$TMP/norm.png")"

printf '%s' "$RESULT" | jq -c '.summary, (.answers[] | {name, value, verdict})'

ACTUAL_NEXT="$(printf '%s' "$RESULT" | jq -r '.summary.next')"
ACTUAL_REASON="$(printf '%s' "$RESULT" | jq -r '.summary.reason')"
if [ "$ACTUAL_NEXT" = "$EXPECT_NEXT" ] && [ "$ACTUAL_REASON" = "$EXPECT_REASON" ]; then
  echo "OK: next=$ACTUAL_NEXT reason=$ACTUAL_REASON(期待どおり)"
else
  echo "NG: 期待は next=$EXPECT_NEXT reason=$EXPECT_REASON だが、実際は next=$ACTUAL_NEXT reason=$ACTUAL_REASON" >&2
  exit 1
fi
