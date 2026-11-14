#!/bin/sh
# example_ok.png(要素がそろった画面)に対して Decision AI の判定を実行する手動チェック。
# 使い方: sh check-example-ok.sh [--raw]   (--raw で API の生のレスポンスを標準エラーに出す)
# 期待する結果: next=ui_checker / reason=all_present(5件すべて present)
#   全部そろっていても完了とはせず、ui-checker で最終確認する設計のため ui_checker になる。
exec bash "$(dirname "$0")/_check-example.sh" example_ok.png ui_checker all_present "$@"
