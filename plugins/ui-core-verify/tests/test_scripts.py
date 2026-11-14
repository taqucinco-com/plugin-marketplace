"""normalize-image.sh と scale-structure.py のテスト。標準ライブラリのみ。

実行: python3 -m unittest discover -s plugins/ui-core-verify/tests -v
画像の伸縮テストは sips / ImageMagick / Pillow のいずれも無い環境ではスキップする。
"""
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "ui-verify-loop" / "scripts"
NORMALIZE = SCRIPTS / "normalize-image.sh"
SCALE = SCRIPTS / "scale-structure.py"


def write_png(path, width, height, rgb=(200, 120, 60)):
    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    )


def png_size(path):
    data = path.read_bytes()
    return struct.unpack(">II", data[16:24])


def has_image_tool():
    if shutil.which("sips") or shutil.which("magick") or shutil.which("convert"):
        return True
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        return False


def run_scale(*args):
    return subprocess.run([sys.executable, "-I", str(SCALE), *map(str, args)], capture_output=True, text=True)


class TmpCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


@unittest.skipUnless(has_image_tool(), "画像を伸縮できるツールが無い")
class NormalizeImage(TmpCase):
    def run_normalize(self, *args):
        return subprocess.run(["bash", str(NORMALIZE), *map(str, args)], capture_output=True, text=True)

    def test_resizes_to_default_size_and_keeps_original(self):
        src = self.dir / "shot.png"
        write_png(src, 1080, 2400)
        before = src.read_bytes()
        out = self.dir / "out" / "shot-norm.png"
        r = self.run_normalize(src, out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(png_size(out), (480, 1040))
        self.assertEqual(src.read_bytes(), before, "元画像は変更しない")

    def test_explicit_size(self):
        src = self.dir / "shot.png"
        write_png(src, 1080, 2400)
        out = self.dir / "n.png"
        r = self.run_normalize(src, out, "360x780")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(png_size(out), (360, 780))

    def test_warns_when_aspect_ratio_differs_a_lot(self):
        src = self.dir / "shot.png"
        write_png(src, 1080, 2400)
        r = self.run_normalize(src, self.dir / "w.png", "480x640")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("警告", r.stderr)

    def test_no_warning_when_aspect_ratio_is_close(self):
        src = self.dir / "shot.png"
        write_png(src, 1080, 2400)
        r = self.run_normalize(src, self.dir / "n.png")
        self.assertNotIn("警告", r.stderr)

    def test_invalid_size_is_rejected(self):
        src = self.dir / "shot.png"
        write_png(src, 100, 200)
        r = self.run_normalize(src, self.dir / "n.png", "480*640")
        self.assertEqual(r.returncode, 2)

    def test_broken_image_fails_without_output(self):
        src = self.dir / "bad.png"
        src.write_text("not an image", encoding="utf-8")
        out = self.dir / "n.png"
        r = self.run_normalize(src, out)
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("->", r.stdout, "成功メッセージを出さない")
        self.assertFalse(out.exists(), "出力ファイルを残さない")

    def test_missing_input_is_rejected(self):
        r = self.run_normalize(self.dir / "none.png", self.dir / "n.png")
        self.assertEqual(r.returncode, 2)


class ScaleStructure(TmpCase):
    def test_android_xml_scales_bounds_and_autodetects_source_size(self):
        src = self.dir / "wd.xml"
        src.write_text(
            '<h><n bounds="[0,0][1080,2400]"><n bounds="[540,120][720,200]"/></n></h>', encoding="utf-8"
        )
        out = self.dir / "o.xml"
        r = run_scale(src, out, "--dst", "480x1040")
        self.assertEqual(r.returncode, 0, r.stderr)
        # 540*480/1080=240, 120*1040/2400=52, 720*480/1080=320, 200*1040/2400=86.67→87
        self.assertEqual(
            out.read_text(encoding="utf-8"),
            '<h><n bounds="[0,0][480,1040]"><n bounds="[240,52][320,87]"/></n></h>',
        )

    def test_ios_json_scales_frames_and_autodetects_from_application(self):
        src = self.dir / "ax.json"
        src.write_text(
            json.dumps(
                [
                    {"type": "Application", "AXLabel": "A", "frame": {"x": 0, "y": 0, "width": 402, "height": 874}},
                    {"type": "Button", "AXLabel": "設定", "frame": {"x": 140.2, "y": 230, "width": 121.6, "height": 48}},
                ]
            ),
            encoding="utf-8",
        )
        out = self.dir / "o.json"
        r = run_scale(src, out, "--dst", "480x1040")
        self.assertEqual(r.returncode, 0, r.stderr)
        app, button = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(app["frame"], {"x": 0.0, "y": 0.0, "width": 480.0, "height": 1040.0})
        # 140.2*480/402=167.4, 230*1040/874=273.7, 121.6*480/402=145.2, 48*1040/874=57.1
        self.assertEqual(button["frame"], {"x": 167.4, "y": 273.7, "width": 145.2, "height": 57.1})
        self.assertEqual(button["AXLabel"], "設定", "座標以外は変えない")

    # figma-developer-mcp の get_figma_data は、ノードに `layout: layout_XXXX` の参照だけを出し、
    # 実体を globalVars.styles にブロック形式の YAML(js-yaml の既定)で出す。
    FIGMA_YAML = (
        "nodes:\n"
        "  - id: '13:76'\n"
        "    name: Navigation\n"
        "    layout: layout_ABC123\n"
        "globalVars:\n"
        "  styles:\n"
        "    layout_ABC123:\n"
        "      mode: none\n"
        "      locationRelativeToParent:\n"
        "        x: 100\n"
        "        y: 50\n"
        "      dimensions:\n"
        "        width: 201\n"
        "        height: 437\n"
        "        aspectRatio: 0.46\n"
        "    other:\n"
        "      x: 7\n"
    )

    def test_figma_block_yaml_scales_layout_values_only(self):
        src = self.dir / "f.yaml"
        src.write_text(self.FIGMA_YAML, encoding="utf-8")
        out = self.dir / "o.yaml"
        r = run_scale(src, out, "--src", "402x874", "--dst", "480x1040")
        self.assertEqual(r.returncode, 0, r.stderr)
        text = out.read_text(encoding="utf-8")
        # 100*480/402=119.4, 50*1040/874=59.5, 201*480/402=240, 437*1040/874=520
        self.assertIn("        x: 119.4\n        y: 59.5\n", text)
        self.assertIn("        width: 240\n        height: 520\n", text)
        self.assertIn("aspectRatio: 0.46", text, "比率は伸縮しない")
        self.assertIn("layout: layout_ABC123", text, "参照はそのまま")
        self.assertIn("    other:\n      x: 7\n", text, "layout 以外の x は伸縮しない")

    def test_figma_flow_yaml_is_also_scaled(self):
        src = self.dir / "f.yaml"
        src.write_text("a:\n  locationRelativeToParent: { x: 100, y: 50 }\n  dimensions: { width: 201, height: 437 }\n", encoding="utf-8")
        out = self.dir / "o.yaml"
        r = run_scale(src, out, "--src", "402x874", "--dst", "480x1040")
        self.assertEqual(r.returncode, 0, r.stderr)
        text = out.read_text(encoding="utf-8")
        self.assertIn("locationRelativeToParent: { x: 119.4, y: 59.5 }".replace("{ ", "{").replace(" }", "}"), text.replace("{ ", "{").replace(" }", "}"))
        self.assertIn("width: 240", text)
        self.assertIn("height: 520", text)

    def test_figma_json_scales_layout_values(self):
        src = self.dir / "f.json"
        src.write_text(json.dumps({"globalVars": {"styles": {"layout_A": {
            "locationRelativeToParent": {"x": 100, "y": 50},
            "dimensions": {"width": 201, "height": 437, "aspectRatio": 0.46}}}}}), encoding="utf-8")
        out = self.dir / "o.json"
        r = run_scale(src, out, "--src", "402x874", "--dst", "480x1040")
        self.assertEqual(r.returncode, 0, r.stderr)
        layout = json.loads(out.read_text(encoding="utf-8"))["globalVars"]["styles"]["layout_A"]
        self.assertEqual(layout["locationRelativeToParent"], {"x": 119.4, "y": 59.5})
        self.assertEqual(layout["dimensions"], {"width": 240.0, "height": 520.0, "aspectRatio": 0.46})

    def test_bounds_never_collapse_when_shrinking(self):
        # 1px 幅の要素。左上を切り捨て・右下を切り上げるので 0 幅にならない。
        src = self.dir / "wd.xml"
        src.write_text('<n bounds="[0,0][1080,2400]"><n bounds="[100,100][101,101]"/></n>', encoding="utf-8")
        out = self.dir / "o.xml"
        r = run_scale(src, out, "--dst", "480x1040")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('bounds="[44,43][45,44]"', out.read_text(encoding="utf-8"))

    def test_bounds_rounding_is_exact_not_float_dependent(self):
        # 3*480/1080 = 1.333.. / 9*480/1080 = 4 ちょうど（浮動小数の誤差で 3 になってはいけない）
        src = self.dir / "wd.xml"
        src.write_text('<n bounds="[0,0][1080,2400]"><n bounds="[9,3][27,6]"/></n>', encoding="utf-8")
        out = self.dir / "o.xml"
        run_scale(src, out, "--dst", "480x1040")
        self.assertIn('bounds="[4,1][12,3]"', out.read_text(encoding="utf-8"))

    def test_yaml_requires_explicit_source_size(self):
        src = self.dir / "f.yaml"
        src.write_text("a:\n  dimensions:\n    width: 2\n    height: 2\n", encoding="utf-8")
        r = run_scale(src, self.dir / "o.yaml", "--dst", "480x1040")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--src", r.stderr)

    def test_unknown_format_fails_with_exit_code_4(self):
        src = self.dir / "e.json"
        src.write_text("[]", encoding="utf-8")
        r = run_scale(src, self.dir / "o.json", "--src", "1x1", "--dst", "2x2")
        self.assertEqual(r.returncode, 4)

    def test_invalid_size_is_rejected(self):
        src = self.dir / "e.json"
        src.write_text("[]", encoding="utf-8")
        r = run_scale(src, self.dir / "o.json", "--src", "1x1", "--dst", "2-2")
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
