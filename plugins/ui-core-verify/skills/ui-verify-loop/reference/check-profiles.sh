#!/bin/sh
# decide.py の --profile pr-change / maestro-step を、実際の OpenAI Decisions API で確認する手動チェック。
# 使い方: sh check-profiles.sh
# 前提: 環境変数 OPENAI_API_KEY が設定済みであること(値はこのスクリプトでは扱わない・表示しない)。
#       jq が使えること。リポジトリのチェックアウト上で実行する(他のプラグインの質問ファイルを相対パスで参照する)。
# 注意: 実行すると画像が OpenAI に送られ、API の利用料金が発生する(4回の呼び出し)。
# 期待する結果: 4件すべて PASS。外れたものは FAIL と判定内容を表示し、終了コード 1 で終わる。
set -eu

REF="$(cd "$(dirname "$0")" && pwd)"
SKILL="$(dirname "$REF")"
PLUGINS="$(cd "$SKILL/../../.." && pwd)"
DECIDE="$SKILL/scripts/decide.py"
CHANGE_Q="$PLUGINS/pr-ui-evidence/skills/pr-ui-evidence/decision/change-questions.json"
STEP_Q="$PLUGINS/maestro-scenario-author/skills/maestro-scenario-author/decision/step-questions.json"

# キーの存在だけを確認する(値は出さない。終了コードで返る)
DECISION_AI=1 python3 -I "$DECIDE" --check || exit $?

# 正規化画像は一時ディレクトリに作り、終了時に消す(リポジトリに残さない)
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
bash "$SKILL/scripts/normalize-image.sh" "$REF/example_ok.png" "$TMP/ok.png"
bash "$SKILL/scripts/normalize-image.sh" "$REF/example_ng.png" "$TMP/ng.png"

FAIL=0

# check <名前> <期待する summary.next> <decide.py の引数...>
check() {
  name="$1"
  expected="$2"
  shift 2
  if ! out="$(DECISION_AI=1 python3 -I "$DECIDE" "$@")"; then
    echo "ERROR: $name (decide.py が失敗した。終了コードは上のメッセージを参照)"
    FAIL=1
    return 0
  fi
  actual="$(printf '%s' "$out" | jq -r '.summary.next')"
  if [ "$actual" = "$expected" ]; then
    echo "PASS: $name -> $actual"
  else
    echo "FAIL: $name: 期待 $expected / 実際 $actual"
    printf '%s' "$out" | jq -c '.summary, (.answers[] | {name, value})'
    FAIL=1
  fi
}

check "pr-change: Switch の有無が違う2枚" changed --profile pr-change \
  --questions "$CHANGE_Q" \
  --image 'before(変更前)='"$TMP/ok.png" --image 'after(変更後)='"$TMP/ng.png"

check "pr-change: 同じ画像2枚" unchanged --profile pr-change \
  --questions "$CHANGE_Q" \
  --image 'before(変更前)='"$TMP/ok.png" --image 'after(変更後)='"$TMP/ok.png"

check "maestro-step: 目的の画面になっている" proceed --profile maestro-step \
  --questions "$STEP_Q" \
  --element '見出し「メモ一覧」が画面の上部に表示されているか' \
  --image '現在の画面='"$TMP/ok.png"

check "maestro-step: 目的の要素が画面に無い" inspect --profile maestro-step \
  --questions "$STEP_Q" \
  --element '見出しの右側に、リストとマップを切り替えるSwitchが表示されているか' \
  --image '現在の画面='"$TMP/ng.png"

if [ "$FAIL" -ne 0 ]; then
  echo "NG: 期待と違う結果がある"
  exit 1
fi
echo "OK: すべて期待どおり"
