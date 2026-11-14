#!/usr/bin/env python3
"""構造情報の座標を、標準サイズ(dst)の座標系へ伸縮する。

対象:
  - Android uiautomator dump の XML:  bounds="[x1,y1][x2,y2]"
  - iOS idb ui describe-all の JSON:  "frame": {"x": .., "y": .., "width": .., "height": ..}
  - Figma get_figma_data の YAML:     layout: { x: .., y: .., width: .., height: .. }（1行の flow 形式）

使い方:
  scale-structure.py <入力> <出力> --dst 480x1040 [--src 幅x高さ]
  --src は元の座標系の全体サイズ。XML は最初の bounds="[0,0][W,H]"、idb の JSON は
  最初の type=Application の frame から自動検出する。YAML は最上位フレームの
  width/height を --src に渡すこと。
置換件数を stderr に出力する。0件の場合は形式が想定と違うので、呼び出し側は座標を自分で
計算せず、座標なしで比較すること。
"""
import argparse, json, re, sys


def size(s):
    m = re.fullmatch(r"(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)", s)
    if not m:
        sys.exit(f"サイズは 幅x高さ で指定してください: {s}")
    return float(m.group(1)), float(m.group(2))


def fmt(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


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
    # --- iOS idb の JSON
    nodes = list(walk_frames(data))
    if a.src:
        sw, sh = size(a.src)
    else:
        app = next((x for x in nodes if x.get("type") == "Application"), None)
        if app is None:
            sys.exit("--src を指定してください（Application の frame から全体サイズを検出できません）")
        sw, sh = float(app["frame"]["width"]), float(app["frame"]["height"])
    fx, fy = dw / sw, dh / sh
    for node in nodes:
        f = node["frame"]
        f["x"], f["width"] = round(f["x"] * fx, 1), round(f["width"] * fx, 1)
        f["y"], f["height"] = round(f["y"] * fy, 1), round(f["height"] * fy, 1)
        n += 1
    out = json.dumps(data, ensure_ascii=False, indent=2)
else:
    # --- Android の XML / Figma の YAML
    b = re.compile(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"')
    y = re.compile(r"layout:\s*\{([^}]*)\}")
    if a.src:
        sw, sh = size(a.src)
    else:
        m = re.search(r'bounds="\[0,0\]\[(\d+),(\d+)\]"', text)
        if not m:
            sys.exit("--src を指定してください（全体サイズを自動検出できません）")
        sw, sh = float(m.group(1)), float(m.group(2))
    fx, fy = dw / sw, dh / sh

    def sb(m):
        global n
        n += 1
        x1, y1, x2, y2 = (int(v) for v in m.groups())
        return 'bounds="[%d,%d][%d,%d]"' % (round(x1 * fx), round(y1 * fy), round(x2 * fx), round(y2 * fy))

    def sy(m):
        global n
        body = m.group(1)
        for k, f in (("x", fx), ("width", fx), ("y", fy), ("height", fy)):
            body = re.sub(
                r"(\b%s:\s*)(-?\d+(?:\.\d+)?)" % k,
                lambda mm, f=f: mm.group(1) + fmt(float(mm.group(2)) * f),
                body,
            )
        n += 1
        return "layout: {" + body + "}"

    out = y.sub(sy, b.sub(sb, text))

open(a.output, "w", encoding="utf-8").write(out)
print(f"{a.input}: {n}件を {int(sw)}x{int(sh)} -> {int(dw)}x{int(dh)} に伸縮", file=sys.stderr)
if n == 0:
    sys.exit(4)
