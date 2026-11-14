#!/usr/bin/env python3
"""構造情報の座標を、標準サイズ(dst)の座標系へ伸縮する。

対象:
  - Android uiautomator dump の XML:  bounds="[x1,y1][x2,y2]"
  - iOS idb ui describe-all の JSON:   "frame": {"x": .., "y": .., "width": .., "height": ..}
  - Figma get_figma_data の YAML/JSON: globalVars.styles 配下の layout 実体
        locationRelativeToParent: {x, y}   (親からの相対位置)
        dimensions: {width, height}        (aspectRatio は比率なので伸縮しない)
    figma-developer-mcp は、ノードの layout を `layout: layout_XXXX` という参照にし、実体を
    globalVars.styles に出す。YAML はブロック形式で出るが、1行の flow 形式も受け付ける。
    相対座標も一様な倍率で伸縮すれば整合する（伸縮は線形）。

使い方:
  scale-structure.py <入力> <出力> --dst 480x1040 [--src 幅x高さ]
  --src は元の座標系の全体サイズ。XML は最初の bounds="[0,0][W,H]"、idb の JSON は
  最初の type=Application の frame から自動検出する。Figma の出力にはルートフレームの
  寸法が含まれないため、--src が必須（ダウンロードした画像のサイズ ÷ pngScale。
  pngScale=1 で取得すれば画像サイズそのもの）。

丸め: 計算は分数（Fraction）で厳密に行う。XML の bounds は、左上を切り捨て・右下を切り上げて、
縮小しても要素の幅・高さが 0 にならないようにする。JSON/YAML は小数第1位に四捨五入する。
置換件数を stderr に出力する。0件の場合は形式が想定と違うので、呼び出し側は座標を自分で
計算せず、座標なしで比較すること。
"""
import argparse
import json
import math
import re
import sys
from fractions import Fraction

NUM = r"-?\d+(?:\.\d+)?"


def size(s):
    m = re.fullmatch(r"(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)", s)
    if not m:
        sys.exit(f"サイズは 幅x高さ で指定してください: {s}")
    return Fraction(m.group(1)), Fraction(m.group(2))


def round1(v):
    """小数第1位への四捨五入（half up）。v は Fraction。"""
    return Fraction(math.floor(v * 10 + Fraction(1, 2)), 10)


def fmt(v):
    return f"{float(v):.1f}".rstrip("0").rstrip(".")


def frac(x):
    return Fraction(str(x))


def walk_frames(node):
    """JSON 内の frame(x,y,width,height) を持つ dict を再帰的に列挙する。"""
    if isinstance(node, dict):
        f = node.get("frame")
        if isinstance(f, dict) and all(isinstance(f.get(k), (int, float)) for k in ("x", "y", "width", "height")):
            yield node
        for v in node.values():
            yield from walk_frames(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk_frames(v)


FIGMA_KEYS = {"locationRelativeToParent": (("x", 0), ("y", 1)), "dimensions": (("width", 0), ("height", 1))}


def walk_figma(node):
    """JSON 内の locationRelativeToParent / dimensions の dict を (キー, dict) で列挙する。"""
    if isinstance(node, dict):
        for k, v in node.items():
            if k in FIGMA_KEYS and isinstance(v, dict):
                yield k, v
            else:
                yield from walk_figma(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk_figma(v)


def scale_yaml(text, fx, fy):
    """Figma の YAML を伸縮する。(出力, 置換した値の数) を返す。"""
    factor = {"x": fx, "width": fx, "y": fy, "height": fy}
    count = 0

    # flow 形式: locationRelativeToParent: { x: 1, y: 2 }
    def flow(m):
        nonlocal count
        body = m.group(2)
        for k in FIGMA_KEYS[m.group(1)]:
            name = k[0]

            def one(mm, name=name):
                nonlocal count
                count += 1
                return mm.group(1) + fmt(round1(frac(mm.group(2)) * factor[name]))

            body = re.sub(r"(\b%s:\s*)(%s)" % (name, NUM), one, body)
        return "%s: {%s}" % (m.group(1), body)

    text = re.sub(r"\b(locationRelativeToParent|dimensions):\s*\{([^}]*)\}", flow, text)

    # ブロック形式: 見出し行の下に、より深くインデントされた x/y/width/height が続く
    out, block_indent, block_key = [], None, None
    head = re.compile(r"^(\s*)(locationRelativeToParent|dimensions):\s*$")
    item = re.compile(r"^(\s+)(x|y|width|height):(\s*)(%s)\s*$" % NUM)
    for line in text.split("\n"):
        h = head.match(line)
        if h:
            block_indent, block_key = len(h.group(1)), h.group(2)
            out.append(line)
            continue
        if block_indent is not None and line.strip():
            indent = len(line) - len(line.lstrip())
            if indent <= block_indent:
                block_indent = block_key = None
        i = item.match(line) if block_indent is not None else None
        if i and i.group(2) in dict(FIGMA_KEYS[block_key]):
            count += 1
            out.append("%s%s:%s%s" % (i.group(1), i.group(2), i.group(3), fmt(round1(frac(i.group(4)) * factor[i.group(2)]))))
        else:
            out.append(line)
    return "\n".join(out), count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--dst", required=True)
    ap.add_argument("--src")
    a = ap.parse_args()
    text = open(a.input, encoding="utf-8").read()
    dw, dh = size(a.dst)
    n = 0

    try:
        data = json.loads(text)
    except ValueError:
        data = None

    if data is not None:
        frames = list(walk_frames(data))
        figma = list(walk_figma(data))
        if a.src:
            sw, sh = size(a.src)
        else:
            app = next((x for x in frames if x.get("type") == "Application"), None)
            if app is None:
                sys.exit("--src を指定してください（Application の frame から全体サイズを検出できません）")
            sw, sh = frac(app["frame"]["width"]), frac(app["frame"]["height"])
        fx, fy = dw / sw, dh / sh
        for node in frames:
            f = node["frame"]
            for k, ratio in (("x", fx), ("width", fx), ("y", fy), ("height", fy)):
                f[k] = float(round1(frac(f[k]) * ratio))
            n += 1
        for key, d in figma:
            for name, axis in FIGMA_KEYS[key]:
                if isinstance(d.get(name), (int, float)):
                    d[name] = float(round1(frac(d[name]) * (fx if axis == 0 else fy)))
                    n += 1
        out = json.dumps(data, ensure_ascii=False, indent=2)
    else:
        b = re.compile(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"')
        if a.src:
            sw, sh = size(a.src)
        else:
            m = re.search(r'bounds="\[0,0\]\[(\d+),(\d+)\]"', text)
            if not m:
                sys.exit("--src を指定してください（全体サイズを自動検出できません）")
            sw, sh = Fraction(m.group(1)), Fraction(m.group(2))
        fx, fy = dw / sw, dh / sh

        def sb(m):
            nonlocal n
            n += 1
            x1, y1, x2, y2 = (Fraction(v) for v in m.groups())
            # 左上は切り捨て、右下は切り上げ（縮小しても幅・高さが 0 にならない）
            return 'bounds="[%d,%d][%d,%d]"' % (
                math.floor(x1 * fx), math.floor(y1 * fy), math.ceil(x2 * fx), math.ceil(y2 * fy))

        out = b.sub(sb, text)
        out, k = scale_yaml(out, fx, fy)
        n += k

    open(a.output, "w", encoding="utf-8").write(out)
    print(f"{a.input}: {n}件を {fmt(sw)}x{fmt(sh)} -> {fmt(dw)}x{fmt(dh)} に伸縮", file=sys.stderr)
    if n == 0:
        sys.exit(4)


main()
