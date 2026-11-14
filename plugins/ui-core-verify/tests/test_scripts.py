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
DECIDE = SCRIPTS / "decide.py"
QUESTIONS = SCRIPTS.parent / "decision" / "base-questions.json"


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


SENTINEL = "sk-test-SENTINEL-must-never-be-printed"


def load_decide():
    import importlib.util

    spec = importlib.util.spec_from_file_location("decide", DECIDE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_decide(env_extra, *args):
    """親の環境変数を引き継がず、指定した変数だけで decide.py を実行する(実キーを使わない)。"""
    env = {"PATH": "/usr/bin:/bin", **env_extra}
    return subprocess.run([sys.executable, "-I", str(DECIDE), *map(str, args)], capture_output=True, text=True, env=env)


class DecideGate(TmpCase):
    def test_disabled_when_flag_missing_even_if_key_exists(self):
        r = run_decide({"OPENAI_API_KEY": SENTINEL}, "--check")
        self.assertEqual(r.returncode, 10)

    def test_disabled_when_flag_is_off_value(self):
        r = run_decide({"DECISION_AI": "0", "OPENAI_API_KEY": SENTINEL}, "--check")
        self.assertEqual(r.returncode, 10)

    def test_enabled_without_key_exits_3(self):
        r = run_decide({"DECISION_AI": "1"}, "--check")
        self.assertEqual(r.returncode, 3)

    def test_blank_key_counts_as_missing(self):
        r = run_decide({"DECISION_AI": "1", "OPENAI_API_KEY": "   "}, "--check")
        self.assertEqual(r.returncode, 3)

    def test_enabled_with_key_exits_0(self):
        r = run_decide({"DECISION_AI": "on", "OPENAI_API_KEY": SENTINEL}, "--check")
        self.assertEqual(r.returncode, 0)

    def test_check_never_prints_the_key(self):
        for env in ({}, {"DECISION_AI": "1"}, {"DECISION_AI": "1", "OPENAI_API_KEY": SENTINEL}, {"OPENAI_API_KEY": SENTINEL}):
            r = run_decide(env, "--check")
            self.assertNotIn(SENTINEL, r.stdout + r.stderr)

    def test_disabled_call_does_not_touch_network_or_files(self):
        r = run_decide({"OPENAI_API_KEY": SENTINEL}, "--questions", self.dir / "none.json")
        self.assertEqual(r.returncode, 10)
        self.assertNotIn(SENTINEL, r.stdout + r.stderr)


class DecideRequest(TmpCase):
    def test_question_template_is_valid(self):
        qs = json.loads(QUESTIONS.read_text(encoding="utf-8"))
        names = [q["name"] for q in qs]
        self.assertEqual(names, ["screen_not_usable"])
        self.assertEqual(qs[0]["type"], "predicate")

    def test_element_questions_are_numbered_predicates(self):
        d = load_decide()
        qs = d.element_questions(["見出しがあるか", " Switchがあるか "])
        self.assertEqual([q["name"] for q in qs], ["expect_01", "expect_02"])
        self.assertTrue(all(q["type"] == "predicate" for q in qs))
        self.assertEqual(qs[1]["instructions"], "Switchがあるか")

    def test_build_request_orders_shared_input_and_embeds_image(self):
        d = load_decide()
        body = d.build_request([{"type": "predicate", "name": "q", "instructions": "x"}], [("期待", "本文")], [("画像", "image/png", "QUJD")])
        self.assertEqual(body["model"], "gpt-6-luna")
        parts = body["input"][0]["content"]
        self.assertEqual([p["type"] for p in parts], ["input_text", "input_text", "input_image"])
        self.assertTrue(parts[2]["image_url"].startswith("data:image/png;base64,"))

    def test_simplify_handles_each_type_and_refusal(self):
        d = load_decide()
        out = d.simplify(
            {
                "answers": [
                    {"type": "predicate", "name": "a", "probability": 0.9},
                    {"type": "choice", "name": "b", "choice": "match", "confidence": 0.8, "probabilities": []},
                    {"type": "refusal", "name": "c"},
                ],
                "usage": {"input_tokens": 1},
            }
        )
        self.assertEqual(out["answers"][0]["value"], 0.9)
        self.assertEqual(out["answers"][1]["value"], "match")
        self.assertEqual(out["answers"][2], {"name": "c", "type": "refusal"})
        self.assertEqual(out["summary"]["next"], "ui_checker")
        with self.assertRaises(ValueError):
            d.simplify({"answers": None})

    def answers(self, **probs):
        return {"answers": [{"type": "predicate", "name": n, "probability": p} for n, p in probs.items()]}

    def test_summary_fix_when_an_element_is_clearly_missing(self):
        d = load_decide()
        out = d.simplify(self.answers(screen_not_usable=0.0, expect_01=1.0, expect_02=0.05))
        self.assertEqual(
            out["summary"], {"next": "fix", "reason": "missing", "missing": ["expect_02"], "missing_visual": [], "uncertain": []}
        )
        self.assertEqual(out["answers"][2]["verdict"], "missing")

    def test_summary_ui_checker_when_all_present_or_uncertain(self):
        d = load_decide()
        present = d.simplify(self.answers(screen_not_usable=0.0, expect_01=1.0, expect_02=0.8))
        self.assertEqual(present["summary"]["next"], "ui_checker")
        self.assertEqual(present["summary"]["reason"], "all_present")
        uncertain = d.simplify(self.answers(screen_not_usable=0.0, expect_01=1.0, expect_02=0.5))
        self.assertEqual(uncertain["summary"]["reason"], "uncertain")
        self.assertEqual(uncertain["summary"]["uncertain"], ["expect_02"])

    def test_summary_missing_boundary_and_unusable_screen(self):
        d = load_decide()
        self.assertEqual(d.simplify(self.answers(expect_01=0.2))["summary"]["next"], "fix")
        self.assertEqual(d.simplify(self.answers(expect_01=0.21))["summary"]["next"], "ui_checker")
        # 画面が評価できないなら、要素が欠けて見えても修正に進まない
        out = d.simplify(self.answers(screen_not_usable=0.5, expect_01=0.0))
        self.assertEqual(out["summary"]["next"], "ui_checker")
        self.assertEqual(out["summary"]["reason"], "screen_not_usable")

    def test_summary_visual_only_missing_goes_to_ui_checker(self):
        d = load_decide()
        out = d.simplify(self.answers(screen_not_usable=0.0, expect_01=1.0, expect_v01=0.0))
        self.assertEqual(out["summary"]["next"], "ui_checker")
        self.assertEqual(out["summary"]["reason"], "missing_visual")
        self.assertEqual(out["summary"]["missing_visual"], ["expect_v01"])
        self.assertEqual(out["summary"]["missing"], [])

    def test_summary_text_missing_wins_over_visual_missing(self):
        d = load_decide()
        out = d.simplify(self.answers(expect_01=0.0, expect_v01=0.0))
        self.assertEqual(out["summary"]["next"], "fix")
        self.assertEqual(out["summary"]["missing"], ["expect_01"])
        self.assertEqual(out["summary"]["missing_visual"], ["expect_v01"])

    def test_visual_questions_use_separate_numbering(self):
        d = load_decide()
        qs = d.element_questions(["a"], ["b", "c"])
        self.assertEqual([q["name"] for q in qs], ["expect_01", "expect_v01", "expect_v02"])

    def test_raw_prints_response_to_stderr_without_key_or_request(self):
        import io
        from unittest import mock

        d = load_decide()
        tdir = self.dir
        (tdir / "t.txt").write_text("画面の期待テキスト", encoding="utf-8")
        write_png(tdir / "i.png", 4, 4)
        fake = {"model": "m", "answers": [{"type": "predicate", "name": "expect_01", "probability": 1.0}], "usage": {"input_tokens": 1}}
        argv = ["decide.py", "--element", "あるか", "--text", f"期待={tdir / 't.txt'}", "--image", f"画像={tdir / 'i.png'}", "--raw"]
        out, err = io.StringIO(), io.StringIO()
        env = {"DECISION_AI": "1", "OPENAI_API_KEY": SENTINEL}
        with mock.patch.object(sys, "argv", argv), mock.patch.dict(d.os.environ, env, clear=True), mock.patch.object(
            d, "call_api", return_value=fake
        ), mock.patch.object(sys, "stdout", out), mock.patch.object(sys, "stderr", err):
            d.main()
        self.assertEqual(json.loads(err.getvalue()), fake)
        self.assertEqual(json.loads(out.getvalue())["summary"]["next"], "ui_checker")
        for text in (out.getvalue(), err.getvalue()):
            self.assertNotIn(SENTINEL, text)
            self.assertNotIn("画面の期待テキスト", text)

    def test_summary_ui_checker_without_elements(self):
        d = load_decide()
        self.assertEqual(d.simplify(self.answers(screen_not_usable=0.0))["summary"]["reason"], "no_elements")

    def test_summary_ui_checker_on_refusal(self):
        d = load_decide()
        resp = {"answers": [{"type": "predicate", "name": "expect_01", "probability": 0.0}, {"type": "refusal", "name": "expect_02"}]}
        self.assertEqual(d.simplify(resp)["summary"]["reason"], "refusal")

    def test_instructions_are_echoed_for_answers(self):
        d = load_decide()
        out = d.simplify(self.answers(expect_01=1.0), [{"name": "expect_01", "instructions": "見出しがあるか"}])
        self.assertEqual(out["answers"][0]["instructions"], "見出しがあるか")

    def test_http_error_prints_status_only(self):
        import io
        import urllib.error
        from unittest import mock

        d = load_decide()
        err = urllib.error.HTTPError(d.ENDPOINT, 401, "Unauthorized", {}, io.BytesIO(("body " + SENTINEL).encode()))
        stderr = io.StringIO()
        with mock.patch.object(d.urllib.request, "urlopen", side_effect=err), mock.patch.object(sys, "stderr", stderr):
            with self.assertRaises(SystemExit) as cm:
                d.call_api({}, SENTINEL)
        self.assertEqual(cm.exception.code, 5)
        self.assertIn("401", stderr.getvalue())
        self.assertNotIn(SENTINEL, stderr.getvalue())

    def test_network_error_exits_4_without_key(self):
        import io
        import urllib.error
        from unittest import mock

        d = load_decide()
        stderr = io.StringIO()
        with mock.patch.object(d.urllib.request, "urlopen", side_effect=urllib.error.URLError(SENTINEL)), mock.patch.object(sys, "stderr", stderr):
            with self.assertRaises(SystemExit) as cm:
                d.call_api({}, SENTINEL)
        self.assertEqual(cm.exception.code, 4)
        self.assertNotIn(SENTINEL, stderr.getvalue())

    def test_authorization_header_uses_key_only_in_header(self):
        import io
        from unittest import mock

        d = load_decide()
        seen = {}

        def fake_urlopen(req, timeout):
            seen["auth"] = req.get_header("Authorization")
            seen["url"] = req.full_url
            return io.BytesIO(b'{"answers": []}')

        with mock.patch.object(d.urllib.request, "urlopen", side_effect=fake_urlopen):
            d.call_api({"x": 1}, "k")
        self.assertEqual(seen["auth"], "Bearer k")
        self.assertEqual(seen["url"], "https://api.openai.com/v1/decisions")


PLUGINS = Path(__file__).resolve().parents[2]
COPIES = {
    "maestro-scenario-author": PLUGINS / "maestro-scenario-author" / "skills" / "maestro-scenario-author",
    "pr-ui-evidence": PLUGINS / "pr-ui-evidence" / "skills" / "pr-ui-evidence",
}


class SharedScriptCopies(unittest.TestCase):
    """プラグインは互いのファイルを参照できないため、同じスクリプトを複数のプラグインに置いている。ずれていないかを確認する。"""

    def test_copies_are_identical(self):
        for name, skill_dir in COPIES.items():
            for script in ("decide.py", "normalize-image.sh"):
                with self.subTest(plugin=name, script=script):
                    self.assertEqual(
                        (skill_dir / "scripts" / script).read_bytes(),
                        (SCRIPTS / script).read_bytes(),
                        f"{name} の {script} が ui-core-verify とずれている。コピーし直す",
                    )

    def test_question_templates_are_valid(self):
        checks = {
            COPIES["pr-ui-evidence"] / "decision" / "change-questions.json": {"changed", "same_screen"},
            COPIES["maestro-scenario-author"] / "decision" / "step-questions.json": {"screen_not_usable", "blocked_by_dialog"},
        }
        for path, names in checks.items():
            with self.subTest(path=path.name):
                qs = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual({q["name"] for q in qs}, names)
                self.assertTrue(all(q["type"] == "predicate" and q["instructions"] for q in qs))


class DecideProfiles(unittest.TestCase):
    def answers(self, **probs):
        return {"answers": [{"type": "predicate", "name": n, "probability": p} for n, p in probs.items()]}

    def nxt(self, profile, **probs):
        d = load_decide()
        return d.simplify(self.answers(**probs), (), profile)["summary"]

    # pr-change
    def test_pr_change_changed_unchanged_and_check(self):
        self.assertEqual(self.nxt("pr-change", changed=0.9, same_screen=1.0)["next"], "changed")
        self.assertEqual(self.nxt("pr-change", changed=0.1, same_screen=1.0)["next"], "unchanged")
        self.assertEqual(self.nxt("pr-change", changed=0.5, same_screen=1.0), {"next": "check", "reason": "uncertain"})

    def test_pr_change_boundaries(self):
        self.assertEqual(self.nxt("pr-change", changed=0.8, same_screen=1.0)["next"], "changed")
        self.assertEqual(self.nxt("pr-change", changed=0.2, same_screen=1.0)["next"], "unchanged")
        self.assertEqual(self.nxt("pr-change", changed=0.21, same_screen=1.0)["next"], "check")

    def test_pr_change_different_screen_or_missing_answer_needs_check(self):
        # 別の画面に見えるときは、変更なしと断定しない
        self.assertEqual(self.nxt("pr-change", changed=0.0, same_screen=0.5)["reason"], "not_same_screen")
        self.assertEqual(self.nxt("pr-change", changed=0.0)["reason"], "no_answer")

    def test_pr_change_refusal_needs_check(self):
        d = load_decide()
        resp = {"answers": [{"type": "refusal", "name": "changed"}, {"type": "predicate", "name": "same_screen", "probability": 1.0}]}
        self.assertEqual(d.simplify(resp, (), "pr-change")["summary"], {"next": "check", "reason": "refusal"})

    # maestro-step
    def test_maestro_step_proceeds_only_when_goal_reached_and_not_blocked(self):
        ok = self.nxt("maestro-step", screen_not_usable=0.0, blocked_by_dialog=0.0, expect_01=1.0)
        self.assertEqual(ok, {"next": "proceed", "reason": "goal_reached"})

    def test_maestro_step_inspects_on_any_doubt(self):
        self.assertEqual(self.nxt("maestro-step", screen_not_usable=0.0, blocked_by_dialog=0.9, expect_01=1.0)["next"], "inspect")
        self.assertEqual(self.nxt("maestro-step", screen_not_usable=0.0, blocked_by_dialog=0.21, expect_01=1.0)["next"], "inspect")
        self.assertEqual(self.nxt("maestro-step", screen_not_usable=0.6, blocked_by_dialog=0.0, expect_01=1.0)["next"], "inspect")
        self.assertEqual(self.nxt("maestro-step", screen_not_usable=0.0, blocked_by_dialog=0.0, expect_01=0.5)["next"], "inspect")
        self.assertEqual(self.nxt("maestro-step", screen_not_usable=0.0, blocked_by_dialog=0.0, expect_01=0.0)["next"], "inspect")

    def test_maestro_step_requires_all_goals_and_a_goal(self):
        self.assertEqual(
            self.nxt("maestro-step", screen_not_usable=0.0, blocked_by_dialog=0.0, expect_01=1.0, expect_02=0.5)["next"], "inspect"
        )
        self.assertEqual(self.nxt("maestro-step", screen_not_usable=0.0, blocked_by_dialog=0.0)["reason"], "no_goal")

    def test_maestro_step_missing_answers_inspect(self):
        self.assertEqual(self.nxt("maestro-step", expect_01=1.0)["next"], "inspect")

    def test_default_profile_is_ui_verify(self):
        d = load_decide()
        out = d.simplify(self.answers(screen_not_usable=0.0, expect_01=0.0))
        self.assertEqual(out["summary"]["next"], "fix")

    def test_unknown_profile_is_rejected_by_cli(self):
        r = run_decide({"DECISION_AI": "1", "OPENAI_API_KEY": SENTINEL}, "--profile", "nope", "--element", "x")
        self.assertEqual(r.returncode, 2)
        self.assertNotIn(SENTINEL, r.stdout + r.stderr)


class DecideRobustness(TmpCase):
    ENV = {"DECISION_AI": "1", "OPENAI_API_KEY": SENTINEL}

    def run_with_questions(self, questions_json):
        q = self.dir / "q.json"
        q.write_text(questions_json, encoding="utf-8")
        t = self.dir / "t.txt"
        t.write_text("期待", encoding="utf-8")
        return run_decide(self.ENV, "--questions", q, "--text", f"期待={t}")

    def test_reserved_question_name_is_rejected(self):
        r = self.run_with_questions('[{"type":"predicate","name":"expect_visible_header","instructions":"x"}]')
        self.assertEqual(r.returncode, 2)
        self.assertNotIn(SENTINEL, r.stdout + r.stderr)

    def test_question_without_string_name_is_rejected(self):
        self.assertEqual(self.run_with_questions('[{"type":"predicate","name":["a"],"instructions":"x"}]').returncode, 2)
        self.assertEqual(self.run_with_questions('["not a dict"]').returncode, 2)

    def run_main_with_response(self, fake_urlopen_result):
        import io
        from unittest import mock

        d = load_decide()
        t = self.dir / "t.txt"
        t.write_text("期待", encoding="utf-8")
        argv = ["decide.py", "--element", "あるか", "--text", f"期待={t}"]
        err = io.StringIO()
        with mock.patch.object(sys, "argv", argv), mock.patch.dict(d.os.environ, self.ENV, clear=True), mock.patch.object(
            d.urllib.request, "urlopen", return_value=fake_urlopen_result
        ), mock.patch.object(sys, "stderr", err), mock.patch.object(sys, "stdout", io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                d.main()
        self.assertNotIn(SENTINEL, err.getvalue())
        return cm.exception.code

    def test_non_utf8_body_exits_6_not_traceback(self):
        import io

        self.assertEqual(self.run_main_with_response(io.BytesIO(b"\x80\x81\x82")), 6)

    def test_answer_with_unhashable_name_exits_6_not_traceback(self):
        import io

        body = json.dumps({"answers": [{"type": "predicate", "name": ["x"], "probability": 1.0}]}).encode()
        self.assertEqual(self.run_main_with_response(io.BytesIO(body)), 6)

    def test_http_exception_is_a_network_error(self):
        import http.client
        from unittest import mock

        d = load_decide()
        with mock.patch.object(d.urllib.request, "urlopen", side_effect=http.client.IncompleteRead(b"")):
            with self.assertRaises(SystemExit) as cm:
                d.call_api({}, "k")
        self.assertEqual(cm.exception.code, 4)


@unittest.skipUnless(shutil.which("sips"), "sips が無い")
class NormalizeKeepsFormatMatchingExtension(TmpCase):
    def test_jpeg_input_to_png_output_is_really_png(self):
        png = self.dir / "in.png"
        write_png(png, 200, 400)
        jpg = self.dir / "in.jpg"
        subprocess.run(["sips", "-s", "format", "jpeg", str(png), "--out", str(jpg)], check=True, capture_output=True)
        out = self.dir / "out.png"
        r = subprocess.run(["bash", str(NORMALIZE), str(jpg), str(out)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(out.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_unreadable_image_reports_exit_3_with_message(self):
        bad = self.dir / "bad.png"
        bad.write_bytes(b"not an image")
        r = subprocess.run(["bash", str(NORMALIZE), str(bad), str(self.dir / "o.png")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 3)
        self.assertIn("画像", r.stderr)


def minimal_jpeg(width, height):
    """サイズだけを読めれば足りる、最小限の JPEG のヘッダ(SOI + SOF0)。"""
    sof = b"\xff\xc0\x00\x11\x08" + height.to_bytes(2, "big") + width.to_bytes(2, "big") + b"\x03" + b"\x01\x22\x00\x02\x11\x01\x03\x11\x01"
    return b"\xff\xd8" + sof + b"\xff\xd9"


class DecideImageSize(TmpCase):
    ENV = {"DECISION_AI": "1", "OPENAI_API_KEY": SENTINEL}

    def test_image_size_reads_png_and_jpeg(self):
        d = load_decide()
        png = self.dir / "a.png"
        write_png(png, 30, 70)
        self.assertEqual(d.image_size(png.read_bytes()), (30, 70))
        self.assertEqual(d.image_size(minimal_jpeg(480, 1040)), (480, 1040))

    def test_image_size_is_none_for_unknown_formats(self):
        d = load_decide()
        self.assertIsNone(d.image_size(b"RIFF....WEBPVP8 "))
        self.assertIsNone(d.image_size(b""))
        self.assertIsNone(d.image_size(b"\xff\xd8\xff"))  # 壊れた JPEG でも落ちない

    def test_different_sizes_exit_7_without_network(self):
        d = load_decide()
        images = [("before", "image/png", "x", (480, 1040)), ("after", "image/png", "x", (1206, 2622))]
        with self.assertRaises(SystemExit) as cm:
            d.check_same_size(images)
        self.assertEqual(cm.exception.code, 7)

    def test_same_sizes_and_unreadable_sizes_pass(self):
        d = load_decide()
        d.check_same_size([("a", "image/png", "x", (480, 1040)), ("b", "image/png", "x", (480, 1040))])
        # サイズを読めない画像(WebP など)は、確認の対象外
        d.check_same_size([("a", "image/png", "x", (480, 1040)), ("b", "image/webp", "x", None)])
        d.check_same_size([("only", "image/png", "x", (1, 1))])

    def test_cli_stops_with_7_before_any_request_and_hides_key(self):
        a, b = self.dir / "a.png", self.dir / "b.png"
        write_png(a, 480, 1040)
        write_png(b, 1206, 2622)
        t = self.dir / "t.txt"
        t.write_text("期待", encoding="utf-8")
        r = run_decide(self.ENV, "--element", "あるか", "--text", f"期待={t}", "--image", f"before={a}", "--image", f"after={b}")
        self.assertEqual(r.returncode, 7)
        self.assertIn("normalize-image.sh", r.stderr)
        self.assertIn("480x1040", r.stderr)
        self.assertNotIn(SENTINEL, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
