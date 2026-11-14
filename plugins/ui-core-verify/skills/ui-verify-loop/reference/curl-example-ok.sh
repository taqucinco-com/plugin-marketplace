#!/bin/sh
# check-example-ok.sh が decide.py 経由で OpenAI Decisions API に送るリクエストを、curl で再現する。
# 使い方: sh curl-example-ok.sh [--show-request]
#   --show-request  送るリクエスト(画像のデータは省略して表示)を標準エラーに出す
# 前提: 環境変数 OPENAI_API_KEY が設定済みであること(値はこのスクリプトでは表示しない)。
#       jq と curl(7.55 以降)が使えること。
# 注意: 質問の文言は _check-example.sh と同じにしてある。変えるときは両方を揃える。
# 結果: API の生のレスポンス(JSON)を標準出力に出す。
set -eu

REF="$(cd "$(dirname "$0")" && pwd)"
SKILL="$(dirname "$REF")"

# キーの存在だけを確認する(値は出さない)
if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "OPENAI_API_KEY が設定されていません" >&2
  exit 3
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# 1. 画像を 480x1040 に正規化して base64 にする(引数ではなくファイル経由で jq に渡す)
bash "$SKILL/scripts/normalize-image.sh" "$REF/example_ok.png" "$TMP/norm.png"
base64 -i "$TMP/norm.png" | tr -d '\n' > "$TMP/norm.b64"
[ -s "$TMP/norm.b64" ] || { echo "base64 が空です" >&2; exit 2; }

# 2. リクエストを作る(decide.py の build_request と同じ構造: 期待のテキスト → 画像の順)
jq -n \
  --rawfile expect "$REF/expect.txt" \
  --rawfile b64 "$TMP/norm.b64" \
  --slurpfile base "$SKILL/decision/base-questions.json" '
  def pred($name; $text): {type: "predicate", name: $name, instructions: $text};
  {
    model: "gpt-6-luna",
    input: [{
      role: "user",
      content: [
        {type: "input_text", text: ("## 比較対象の期待\n" + $expect)},
        {type: "input_text", text: "## 実装のスクリーンショット(次の画像)"},
        {type: "input_image", image_url: ("data:image/png;base64," + $b64)}
      ]
    }],
    questions: ($base[0] + [
      pred("expect_01"; "見出し「メモ一覧」が画面の上部に表示されているか"),
      pred("expect_02"; "見出しの右側に、リストとマップを切り替えるSwitchが表示されているか"),
      pred("expect_03"; "画面の真ん中のかなり広い領域を、地図が占めているか"),
      pred("expect_04"; "画面の下部にボトムナビゲーションが表示されているか"),
      pred("expect_v01"; "地図の右上に、ズームと現在地のアイコンボタンが表示されているか")
    ])
  }' > "$TMP/request.json"

if [ "${1:-}" = "--show-request" ]; then
  jq 'walk(if type == "string" and startswith("data:image") then "data:image/png;base64,...(省略)" else . end)' \
    "$TMP/request.json" >&2
fi

# 3. 呼ぶ。認証ヘッダは、コマンドライン(ps に見える)ではなく標準入力から渡す
printf 'Authorization: Bearer %s\n' "$OPENAI_API_KEY" | curl --fail-with-body --silent --show-error \
  https://api.openai.com/v1/decisions \
  -H @- \
  -H "Content-Type: application/json" \
  --data-binary @"$TMP/request.json"
echo
