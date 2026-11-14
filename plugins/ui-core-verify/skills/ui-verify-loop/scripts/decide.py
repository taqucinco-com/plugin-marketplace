#!/usr/bin/env python3
"""OpenAI Decisions API (POST /v1/decisions) で、質問への判定を1回行う。標準ライブラリのみ。

使い方:
  decide.py --check
      使えるかだけを確認する(通信しない)。結果は終了コードだけで伝える。
  decide.py [--questions q.json] [--element '画面で確認したい内容']... [--element-visual '...']... \
            [--text 'ラベル=ファイル']... [--image 'ラベル=ファイル']... [--raw]
      共有の入力(テキスト・画像)に対して質問を判定し、JSON を標準出力へ出す。
      --element は「画面に○○が表示されているか」という確認を1件ずつ渡す(predicate の質問を
      expect_01, expect_02, ... の名前で自動生成する)。q.json は共通の質問(screen_not_usable など)用。
      --element-visual は、文言のない要素(アイコン・点・ピンなど)の確認に使う。名前は expect_v01, ...。
      こちらが「無い」と出ても、構造情報(文言)では裏が取れず誤判定の影響が大きいので、
      修正に進まず ui-checker で確認させる(summary.missing_visual に列挙)。
      --raw を付けると、API の生のレスポンス(JSON)を標準エラーへ出す。標準出力は変わらない。
      リクエスト(画像・テキスト)とキーは出さない。Claude が実行する通常の手順では付けない。
      出力の summary.next が "fix" なら、文言のある期待の要素が明らかに欠けている(summary.missing に列挙)。
      "ui_checker" なら、この結果だけでは決められないので ui-checker に判定させる。

有効になる条件(両方そろったときだけ):
  1. 環境変数 DECISION_AI が 1 / true / on / yes のいずれか(settings.json の env で設定する)
  2. 環境変数 OPENAI_API_KEY が設定されている(リポジトリの外で設定する。direnv など)

API キーの扱い(厳守):
  - キーは os.environ から読むだけ。引数・ファイル・標準入力では受け取らない。
  - キーの値・長さ・一部(先頭や末尾の数文字)を、標準出力・標準エラー・例外メッセージに出さない。
    存在の有無も「終了コード」と固定の文言でしか伝えない。
  - リクエスト本文(画面上のテキストや画像)も出力しない。エラー時はステータスコードだけを出す。

終了コード:
  0   成功(--check では「使える」)
  2   引数・入力ファイルの不備
  3   DECISION_AI は有効だが OPENAI_API_KEY が未設定
  4   通信できない・タイムアウト(サンドボックスで api.openai.com が許可されていない場合など)
  5   API がエラーを返した(認証・入力不正など)。ステータスコードだけを出す
  6   応答の形が想定と違う
  10  DECISION_AI が無効(利用者が有効にしていない。異常ではない)
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request

ENDPOINT = "https://api.openai.com/v1/decisions"
MODEL = "gpt-6-luna"
TIMEOUT_SEC = 30
TRUTHY = {"1", "true", "on", "yes"}
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}

# 要素の確認(predicate の確率)のしきい値。暫定値。評価データで見直す。
MISSING_MAX = 0.2   # この値以下なら「画面に無い」と扱う
PRESENT_MIN = 0.8   # この値以上なら「画面にある」と扱う
UNUSABLE_MIN = 0.5  # screen_not_usable がこの値以上なら、評価できる画面ではないと扱う
ELEMENT_PREFIX = "expect_"
VISUAL_PREFIX = "expect_v"  # 文言のない要素(--element-visual)

EXIT_ARGS, EXIT_NO_KEY, EXIT_NETWORK, EXIT_API, EXIT_SHAPE, EXIT_DISABLED = 2, 3, 4, 5, 6, 10


def fail(code, message):
    print(message, file=sys.stderr)
    sys.exit(code)


def is_enabled(environ):
    return environ.get("DECISION_AI", "").strip().lower() in TRUTHY


def has_key(environ):
    # 値は評価するだけで、どこにも出さない
    return bool(environ.get("OPENAI_API_KEY", "").strip())


def gate(environ):
    """(終了コード, 固定の文言)を返す。値は含めない。"""
    if not is_enabled(environ):
        return EXIT_DISABLED, "Decision AI は無効です(DECISION_AI が未設定または無効)"
    if not has_key(environ):
        return EXIT_NO_KEY, "Decision AI は有効ですが、OPENAI_API_KEY が設定されていません"
    return 0, "Decision AI を使えます"


def split_labeled(spec):
    label, sep, path = spec.partition("=")
    if not sep or not label or not path:
        fail(EXIT_ARGS, "ラベル=ファイル の形式で指定してください")
    return label, path


def build_request(questions, texts, images):
    """texts: [(ラベル, 本文)]、images: [(ラベル, mime, base64文字列)]。

    共有の入力は、毎回変わらないものを先に置く(プロンプトキャッシュの接頭辞を長く保つため)。
    呼び出し側が渡す順序をそのまま保つ。
    """
    content = []
    for label, body in texts:
        content.append({"type": "input_text", "text": f"## {label}\n{body}"})
    for label, mime, b64 in images:
        content.append({"type": "input_text", "text": f"## {label}(次の画像)"})
        content.append({"type": "input_image", "image_url": f"data:{mime};base64,{b64}"})
    return {
        "model": MODEL,
        "input": [{"role": "user", "content": content}],
        "questions": questions,
    }


def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def element_verdict(value):
    if not is_number(value):
        return "uncertain"
    if value <= MISSING_MAX:
        return "missing"
    if value >= PRESENT_MIN:
        return "present"
    return "uncertain"


def summarize(answers):
    """次にどうするかを、数値のしきい値だけで決める(呼び出し側が確率を暗算しないため)。

    next:
      "fix"        文言のある期待の要素が明らかに欠けている(missing に列挙)。ui-checker を呼ばず修正へ進める
      "ui_checker" 決められない、全部そろっている、または文言のない要素だけが欠けて見える
                   (missing_visual。誤判定の影響が大きいので修正の前に ui-checker で確認する)
    """
    refused = any(a["type"] == "refusal" for a in answers)
    unusable = any(a["name"] == "screen_not_usable" and is_number(a.get("value")) and a["value"] >= UNUSABLE_MIN for a in answers)
    elements = [a for a in answers if str(a["name"]).startswith(ELEMENT_PREFIX)]
    missing = [a["name"] for a in elements if a.get("verdict") == "missing" and not a["name"].startswith(VISUAL_PREFIX)]
    missing_visual = [a["name"] for a in elements if a.get("verdict") == "missing" and a["name"].startswith(VISUAL_PREFIX)]
    uncertain = [a["name"] for a in elements if a.get("verdict") == "uncertain"]
    if refused:
        reason, nxt = "refusal", "ui_checker"
    elif unusable:
        reason, nxt = "screen_not_usable", "ui_checker"
    elif not elements:
        reason, nxt = "no_elements", "ui_checker"
    elif missing:
        reason, nxt = "missing", "fix"
    elif missing_visual:
        reason, nxt = "missing_visual", "ui_checker"
    elif uncertain:
        reason, nxt = "uncertain", "ui_checker"
    else:
        reason, nxt = "all_present", "ui_checker"
    return {"next": nxt, "reason": reason, "missing": missing, "missing_visual": missing_visual, "uncertain": uncertain}


def simplify(response, questions=()):
    """API の応答を、スキルが扱いやすい形に整える。"""
    answers = response.get("answers")
    if not isinstance(answers, list):
        raise ValueError("answers が配列ではありません")
    instructions = {q.get("name"): q.get("instructions") for q in questions if isinstance(q, dict)}
    out = []
    for a in answers:
        kind = a.get("type")
        item = {"name": a.get("name"), "type": kind}
        if kind == "predicate":
            item["value"] = a.get("probability")
            if str(item["name"]).startswith(ELEMENT_PREFIX):
                item["verdict"] = element_verdict(item["value"])
        elif kind in ("choice", "score"):
            item["value"] = a.get(kind)
            item["confidence"] = a.get("confidence")
            item["probabilities"] = a.get("probabilities")
        # refusal などは name と type だけを返す(呼び出し側がフォールバックする)
        if item.get("value") is not None:
            item["instructions"] = instructions.get(item["name"])
        out.append(item)
    return {"summary": summarize(out), "answers": out, "usage": response.get("usage")}


def element_questions(elements, visual=()):
    questions = []
    for prefix, texts in ((ELEMENT_PREFIX, elements), (VISUAL_PREFIX, visual)):
        for i, text in enumerate(texts, start=1):
            text = text.strip()
            if not text:
                fail(EXIT_ARGS, "--element の内容が空です")
            questions.append({"type": "predicate", "name": f"{prefix}{i:02d}", "instructions": text})
    return questions


def load_questions(path):
    try:
        with open(path, encoding="utf-8") as f:
            questions = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        fail(EXIT_ARGS, f"質問ファイルを読めません: {e.__class__.__name__}")
    if not isinstance(questions, list):
        fail(EXIT_ARGS, "質問ファイルは配列にしてください")
    return questions


def read_text(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError) as e:
        fail(EXIT_ARGS, f"テキストを読めません: {e.__class__.__name__}")


def read_image(path):
    ext = os.path.splitext(path)[1].lower()
    if ext not in MIME:
        fail(EXIT_ARGS, "画像は png / jpg / jpeg / webp のいずれかにしてください")
    try:
        with open(path, "rb") as f:
            return MIME[ext], base64.b64encode(f.read()).decode("ascii")
    except OSError as e:
        fail(EXIT_ARGS, f"画像を読めません: {e.__class__.__name__}")


def call_api(body, key):
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        # 応答本文は出さない(リクエスト内容が含まれうるため)
        fail(EXIT_API, f"API エラー: HTTP {e.code}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        fail(EXIT_NETWORK, f"通信できません: {e.__class__.__name__}")
    except json.JSONDecodeError:
        fail(EXIT_SHAPE, "応答が JSON ではありません")


def main():
    p = argparse.ArgumentParser(description="Decisions API で判定する")
    p.add_argument("--check", action="store_true", help="使えるかだけを確認する(通信しない)")
    p.add_argument("--questions", help="共通の質問の配列(JSON)")
    p.add_argument("--element", action="append", default=[], metavar="確認したい内容", help="画面に○○が表示されているか(1件ずつ)")
    p.add_argument("--element-visual", action="append", default=[], metavar="確認したい内容", help="文言のない要素(アイコン・点など)。無くても修正前に ui-checker で確認する")
    p.add_argument("--raw", action="store_true", help="API の生のレスポンスを標準エラーへ出す")
    p.add_argument("--text", action="append", default=[], metavar="ラベル=ファイル")
    p.add_argument("--image", action="append", default=[], metavar="ラベル=ファイル")
    args = p.parse_args()

    code, message = gate(os.environ)
    if args.check:
        print(message)
        sys.exit(code)
    if code != 0:
        fail(code, message)

    questions = (load_questions(args.questions) if args.questions else []) + element_questions(args.element, args.element_visual)
    if not 1 <= len(questions) <= 400:
        fail(EXIT_ARGS, "質問は1〜400件にしてください(--questions か --element が必要です)")
    texts = [(label, read_text(path)) for label, path in map(split_labeled, args.text)]
    images = [(label, *read_image(path)) for label, path in map(split_labeled, args.image)]
    if not texts and not images:
        fail(EXIT_ARGS, "--text か --image が必要です")

    # キーはここで初めて取り出し、リクエストのヘッダにだけ使う
    response = call_api(build_request(questions, texts, images), os.environ["OPENAI_API_KEY"].strip())
    if args.raw:
        # 応答だけを出す。リクエスト(画像・テキスト)とキーは出さない
        print(json.dumps(response, ensure_ascii=False, indent=2), file=sys.stderr)
    try:
        result = simplify(response, questions)
    except (ValueError, AttributeError):
        fail(EXIT_SHAPE, "応答の形が想定と違います")
    json.dump(result, sys.stdout, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
