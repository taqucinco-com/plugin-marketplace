#!/bin/sh
# example_ng.png(切り替えSwitchが欠けた画面)に対して Decision AI の判定を実行する手動チェック。
# 使い方: sh check-example-ng.sh [--raw]   (--raw で API の生のレスポンスを標準エラーに出す)
# 期待する結果: next=fix / reason=missing(expect_02=見出しの右側のSwitch が missing)
#   文言のある要素が欠けているので、ui-checker を呼ばず修正に進む分岐になる。
exec bash "$(dirname "$0")/_check-example.sh" example_ng.png fix missing "$@"
