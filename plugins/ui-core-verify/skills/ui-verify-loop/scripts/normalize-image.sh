#!/usr/bin/env bash
# 画像を比較用の標準サイズへ伸縮して保存する（元画像は変更しない）。
# 使い方: normalize-image.sh <入力画像> <出力画像> [幅x高さ]
#   サイズ省略時は環境変数 UI_VERIFY_SIZE、それも無ければ 480x1040。
# 縦横比を保たずに指定サイズへ伸縮する（Figma側とアプリ側で同じ変換をかけるため）。
# 元画像と標準サイズの縦横比が10%以上ずれる場合は警告を出す（歪みが大きく文字の判読性が落ちる）。
set -euo pipefail

in=${1:?入力画像を指定してください}
out=${2:?出力画像を指定してください}
size=${3:-${UI_VERIFY_SIZE:-480x1040}}
[[ $size =~ ^([0-9]+)x([0-9]+)$ ]] || { echo "サイズは 幅x高さ で指定してください: $size" >&2; exit 2; }
W=${BASH_REMATCH[1]}; H=${BASH_REMATCH[2]}
[[ -f $in ]] || { echo "入力画像が見つかりません: $in" >&2; exit 2; }
mkdir -p "$(dirname "$out")"

if command -v sips >/dev/null 2>&1; then
  sw=$(sips -g pixelWidth "$in" | awk '/pixelWidth/{print $2}')
  sh=$(sips -g pixelHeight "$in" | awk '/pixelHeight/{print $2}')
  sips -z "$H" "$W" "$in" --out "$out" >/dev/null
elif command -v magick >/dev/null 2>&1 || command -v convert >/dev/null 2>&1; then
  im=$(command -v magick || command -v convert)
  if command -v magick >/dev/null 2>&1; then ident=(magick identify); else ident=(identify); fi
  dims=$("${ident[@]}" -format '%w %h' "$in") || { echo "画像のサイズを取得できません: $in" >&2; exit 3; }
  read -r sw sh <<<"$dims"
  "$im" "$in" -resize "${W}x${H}!" "$out"
elif python3 -c 'import PIL' 2>/dev/null; then
  dims=$(python3 -c 'import sys;from PIL import Image;print(*Image.open(sys.argv[1]).size)' "$in") || { echo "画像のサイズを取得できません: $in" >&2; exit 3; }
  read -r sw sh <<<"$dims"
  python3 -c 'import sys;from PIL import Image;Image.open(sys.argv[1]).convert("RGB").resize((int(sys.argv[3]),int(sys.argv[4])),Image.LANCZOS).save(sys.argv[2])' "$in" "$out" "$W" "$H"
else
  echo "画像を伸縮できるツールがありません（sips / ImageMagick / Python+Pillow のいずれかが必要）" >&2
  exit 3
fi

[[ ${sw:-} =~ ^[0-9]+$ && ${sh:-} =~ ^[0-9]+$ && $sw -gt 0 && $sh -gt 0 ]] || { echo "画像のサイズを取得できません: $in" >&2; rm -f "$out"; exit 3; }

awk -v sw="$sw" -v sh="$sh" -v W="$W" -v H="$H" 'BEGIN{
  r=(sw/sh)/(W/H); if (r<1) r=1/r
  if (r>1.10) printf "警告: 縦横比のずれが大きい（元 %dx%d → %dx%d, 比 %.2f倍）。文字が歪んで判読しづらくなるため、標準サイズの縦横比を元画像に近づけること\n", sw,sh,W,H,r > "/dev/stderr"
}'
echo "$in (${sw}x${sh}) -> $out (${W}x${H})"
