#!/usr/bin/env python3
"""Claude Code の `.claude/` 配下を実体として、Devin・Codex 用の設定を生成・同期する。

使い方（リポジトリ内で実行）:
  python3 -I sync.py                  生成して書き込む
  python3 -I sync.py --check          差分があれば終了コード1で終わる（書き込まない）
  python3 -I sync.py --target devin   Devin 用だけ（codex も指定可。既定は all）
  python3 -I sync.py --root PATH      対象リポジトリのルートを指定する

変換規則は references/conversion-rules.md を参照。標準ライブラリのみで動く。
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
HOOK_SRC = PLUGIN_ROOT / "assets" / "load-claude-rules.sh"

READ_ONLY_TOOLS = {"Read", "Grep", "Glob"}
READ_ONLY_NOTICE = (
    "## 使用できる操作の制限\n\n"
    "このエージェントが使ってよい操作は、ファイルの読み取りと検索（`Read`・`Grep`・`Glob`相当）のみ。"
    "ファイルの編集・作成・削除、コマンドの実行、外部サービスへの書き込みは行わない。"
)
# 引数のglobをファイル名の列挙に展開するコマンド（Devin・Codexの規則はglobを表現できないため）
FILE_READERS = {"cat", "less", "more", "head", "tail", "bat"}
SKIP_DIRS = {".git", "node_modules", "build", ".dart_tool", "Pods", ".venv", "venv", "__pycache__"}
HOOK_CMD = 'bash "$(git rev-parse --show-toplevel)/.codex/hooks/load-claude-rules.sh"'
BEGIN = "# >>> sync-devin-codex ({name}) >>>"
END = "# <<< sync-devin-codex ({name}) <<<"


class Plan:
    def __init__(self, root: Path):
        self.root = root
        self.files: dict[str, tuple[str, bool]] = {}
        self.links: dict[str, str] = {}
        self.link_dirs: set[str] = set()
        self.warnings: list[str] = []

    def file(self, rel: str, content: str, executable: bool = False) -> None:
        self.files[rel] = (content, executable)

    def link(self, rel: str, target: str) -> None:
        self.links[rel] = target

    def read(self, rel: str) -> str:
        p = self.root / rel
        return p.read_text() if p.is_file() else ""

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


# ---------- 共通 ----------

def parse_frontmatter(md: str) -> tuple[dict, str]:
    m = re.match(r"---\n(.*?)\n---\n(.*)\Z", md, re.S)
    if not m:
        raise ValueError("frontmatterがありません")
    meta = {}
    for line in m.group(1).split("\n"):
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, m.group(2).strip("\n")


def toml_key(name: str) -> str:
    return name if re.fullmatch(r"[A-Za-z0-9_-]+", name) else json.dumps(name, ensure_ascii=False)


def toml_str(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def toml_multiline(body: str) -> str:
    if "'''" not in body:
        return f"'''\n{body}\n'''"
    escaped = body.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    return f'"""\n{escaped}\n"""'


def set_block(text: str, name: str, content: str, top: bool) -> str:
    """text 内の管理ブロックを置き換える。content が空ならブロックを削除する。"""
    b, e = BEGIN.format(name=name), END.format(name=name)
    text = re.sub(re.escape(b) + r".*?" + re.escape(e) + r"\n?", "", text, flags=re.S)
    if not content:
        return text
    block = f"{b}\n{content.rstrip()}\n{e}\n"
    if top:
        return block + (("\n" + text.lstrip("\n")) if text.strip() else "")
    return (text.rstrip("\n") + "\n\n" if text.strip() else "") + block


def load_json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.is_file() else {}


# ---------- skills / agents ----------

def plan_skills(p: Plan, devin: bool, codex: bool) -> None:
    src = p.root / ".claude" / "skills"
    if not src.is_dir():
        return
    for d in sorted(src.iterdir()):
        if d.is_dir() and (d / "SKILL.md").is_file():
            if devin:
                p.link(f".devin/skills/{d.name}", f"../../.claude/skills/{d.name}")
            if codex:
                p.link(f".agents/skills/{d.name}", f"../../.claude/skills/{d.name}")
    if devin:
        p.link_dirs.add(".devin/skills")
    if codex:
        p.link_dirs.add(".agents/skills")


def convert_agent(md: str) -> tuple[str, str]:
    meta, body = parse_frontmatter(md)
    tools = {t.strip() for t in meta.get("tools", "").split(",") if t.strip()}
    if tools and tools <= READ_ONLY_TOOLS:
        body = f"{body}\n\n{READ_ONLY_NOTICE}"
    toml = (
        f"name = {toml_str(meta['name'])}\n"
        f"description = {toml_str(meta['description'])}\n"
        f"developer_instructions = {toml_multiline(body)}\n"
    )
    return meta["name"], toml


def plan_agents(p: Plan, devin: bool, codex: bool) -> None:
    src = p.root / ".claude" / "agents"
    if not src.is_dir():
        return
    for md in sorted(src.glob("*.md")):
        if devin:
            p.link(f".devin/agents/{md.name}", f"../../.claude/agents/{md.name}")
        if codex:
            try:
                name, toml = convert_agent(md.read_text())
            except (ValueError, KeyError) as exc:
                p.warn(f".claude/agents/{md.name}: 変換できません（{exc}。name・descriptionが必要）")
                continue
            p.file(f".codex/agents/{name}.toml", toml)
    if devin:
        p.link_dirs.add(".devin/agents")


# ---------- rules ----------

def plan_rules(p: Plan) -> None:
    rules = p.root / ".claude" / "rules"
    if not (rules.is_dir() and any(rules.rglob("*.md"))):
        return
    p.file(".codex/hooks/load-claude-rules.sh", HOOK_SRC.read_text(), executable=True)
    data = json.loads(p.read(".codex/hooks.json") or "{}")
    groups = data.setdefault("hooks", {}).setdefault("SessionStart", [])
    entry = {"type": "command", "command": HOOK_CMD, "additionalContextLimit": 20000}
    for g in groups:
        for h in g.get("hooks", []):
            if "load-claude-rules.sh" in h.get("command", ""):
                h.update(entry)
                break
        else:
            continue
        break
    else:
        groups.append({"hooks": [entry]})
    p.file(".codex/hooks.json", json.dumps(data, indent=2, ensure_ascii=False) + "\n")


# ---------- permissions ----------

def parse_rules(p: Plan) -> list[tuple[str, str]]:
    deny = load_json(p.root / ".claude" / "settings.json").get("permissions", {}).get("deny", [])
    out = []
    for r in deny:
        m = re.fullmatch(r"(\w+)\((.*)\)", r.strip())
        if m:
            out.append((m.group(1), m.group(2)))
        else:
            p.warn(f"permissions.deny の書式を解釈できません: {r}")
    return out


def find_files(root: Path, pattern: str) -> list[str]:
    """pattern（`**/x*` または `dir/x*` または `x*`）に一致するファイルの相対パスを返す。"""
    found: list[str] = []
    if pattern.startswith("**/") and "/" not in pattern[3:]:
        for cur, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            found += [str((Path(cur) / f).relative_to(root).as_posix())
                      for f in files if fnmatch.fnmatch(f, pattern[3:])]
    else:
        found = [m.relative_to(root).as_posix() for m in root.glob(pattern) if m.is_file()]
    return sorted(found)


def exec_specs(p: Plan, arg: str):
    """Bash(...) のルールを ('plain', tokens) または ('reader', cmd, paths) に変換する。"""
    raw = arg.split()
    if not raw:
        return None
    if raw[0] in FILE_READERS and any("*" in t for t in raw[1:]):
        paths: list[str] = []
        for g in raw[1:]:
            if g.endswith("*") and "*" not in g[:-1] and not g.startswith("**/"):
                paths.append(g[:-1])  # `.env*` の `.env` 自体
            paths += find_files(p.root, g) if "*" in g else [g]
        paths = list(dict.fromkeys(x for x in paths if x))
        if not paths:
            p.warn(f"Bash({arg}): 一致するファイルが無いため変換結果が空です")
            return None
        return ("reader", raw[0], paths)
    tokens = raw[:]
    if tokens[-1] == "*":
        tokens.pop()
    elif tokens[-1].endswith("*"):
        tokens[-1] = tokens[-1][:-1]
    if not tokens or any("*" in t for t in tokens):
        p.warn(f"Bash({arg}): 表現できないglobを含むためスキップしました")
        return None
    return ("plain", tokens)


def plan_permissions(p: Plan, devin: bool, codex: bool) -> tuple[str, str]:
    """Devin/Codexのpermissionsを計画し、config.toml用の (top, tables) 断片を返す。"""
    rules = parse_rules(p)
    specs = []
    for tool, arg in rules:
        if tool == "Bash":
            s = exec_specs(p, arg)
            if s:
                specs.append((arg, s))
        elif tool not in {"Read", "Edit", "Write"}:
            p.warn(f"{tool}({arg}): 変換対象外のツールです")

    if devin and rules:
        deny: list[str] = []
        for tool, arg in rules:
            if tool == "Read":
                deny.append(f"Read({arg})")
            elif tool in {"Edit", "Write"}:
                deny.append(f"Write({arg})")
        for _, s in specs:
            if s[0] == "plain":
                deny.append(f"Exec({' '.join(s[1])})")
            else:
                deny += [f"Exec({s[1]} {x})" for x in s[2]]
        deny = list(dict.fromkeys(deny))
        data = load_json(p.root / ".devin" / "config.json")
        data.setdefault("permissions", {})["deny"] = deny
        p.file(".devin/config.json", json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    top, tables = "", ""
    if codex and rules:
        paths: list[str] = []
        for tool, arg in rules:
            if tool in {"Read", "Edit", "Write"}:
                base = arg[2:] if arg.startswith("./") else arg
                base = base[3:] if base.startswith("**/") else base
                paths += [base, "**/" + base]
        paths = list(dict.fromkeys(paths))
        if paths:
            top = 'default_permissions = "project"'
            tables = (
                '[permissions.project]\nextends = ":workspace"\n\n'
                '[permissions.project.filesystem.":workspace_roots"]\n'
                + "".join(f"{toml_str(x)} = \"deny\"\n" for x in paths)
            )
        p.file(".codex/rules/deny.rules", build_deny_rules(specs)) if specs else None
    return top, tables


def build_deny_rules(specs) -> str:
    out = [
        "# sync-devin-codex が .claude/settings.json の permissions.deny から生成した。手で編集しない。",
        "# prefix_rule は引数列の前方一致で、位置を指定しない一致（引数の後ろに現れるフラグ等）は表現できない。",
        "",
    ]
    for arg, s in specs:
        if s[0] == "plain":
            tokens = s[1]
            pattern = tokens
            match = [" ".join(tokens)]
            not_match = [" ".join(tokens[:-1])] if len(tokens) > 1 else []
        else:
            _, cmd, paths = s
            alts = list(dict.fromkeys(paths + ["./" + x for x in paths if not x.startswith("./")]))
            pattern = [cmd, alts]
            match = [f"{cmd} {paths[0]}"]
            not_match = [f"{cmd} README.md"]
        out.append("prefix_rule(")
        out.append(f"    pattern = {json.dumps(pattern, ensure_ascii=False)},")
        out.append('    decision = "forbidden",')
        out.append(f"    justification = {toml_str(f'Claude Codeの permissions.deny に合わせて禁止: Bash({arg})')},")
        out.append(f"    match = {json.dumps(match, ensure_ascii=False)},")
        if not_match:
            out.append(f"    not_match = {json.dumps(not_match, ensure_ascii=False)},")
        out.append(")")
        out.append("")
    return "\n".join(out)


# ---------- MCP ----------

def plan_mcp(p: Plan, devin: bool, codex: bool) -> str:
    mcp = p.root / ".mcp.json"
    if not mcp.is_file():
        return ""
    if devin:
        p.link(".devin/mcp_config.json", "../.mcp.json")
    if not codex:
        return ""
    chunks = []
    for name, s in load_json(mcp).get("mcpServers", {}).items():
        lines = [f"[mcp_servers.{toml_key(name)}]"]
        if "command" in s:
            lines.append(f"command = {toml_str(s['command'])}")
            if s.get("args"):
                lines.append("args = [" + ", ".join(toml_str(a) for a in s["args"]) + "]")
        elif "url" in s:
            lines.append(f"url = {toml_str(s['url'])}")
            if s.get("headers"):
                p.warn(f"MCP {name}: headers はCodexへ変換できません。必要なら config.toml に手で設定してください")
        else:
            p.warn(f"MCP {name}: command も url も無いためスキップしました")
            continue
        env_vars, literal = [], {}
        for k, v in s.get("env", {}).items():
            m = re.fullmatch(r"\$\{(\w+)\}", str(v))
            if m and m.group(1) == k:
                env_vars.append(k)
            elif m:
                p.warn(f"MCP {name}: env {k}=${{{m.group(1)}}} は別名の参照のためCodexへ変換できません"
                       f"（{m.group(1)} を env_vars で転送するか、起動側で {k} を設定してください）")
            else:
                literal[k] = str(v)
        if env_vars:
            lines.append("env_vars = [" + ", ".join(toml_str(v) for v in env_vars) + "]")
        if literal:
            p.warn(f"MCP {name}: env にリテラル値があります。秘密情報ならコミットしないでください")
            lines.append(f"\n[mcp_servers.{toml_key(name)}.env]")
            lines += [f"{toml_key(k)} = {toml_str(v)}" for k, v in literal.items()]
        chunks.append("\n".join(lines))
    return "\n\n".join(chunks)


# ---------- 適用 ----------

def build_plan(root: Path, targets: set[str]) -> Plan:
    p = Plan(root)
    devin, codex = "devin" in targets, "codex" in targets
    plan_skills(p, devin, codex)
    plan_agents(p, devin, codex)
    top, tables = plan_permissions(p, devin, codex)
    mcp_tables = plan_mcp(p, devin, codex)
    if codex:
        plan_rules(p)
        existing = p.read(".codex/config.toml")
        if re.search(r"^\s*sandbox_mode\s*=", existing, re.M) and top:
            p.warn(".codex/config.toml に sandbox_mode があります。default_permissions は無視されます")
        text = set_block(existing, "permissions", top, top=True)
        text = set_block(text, "permissions-tables", "\n\n".join(x for x in [tables, mcp_tables] if x), top=False)
        if text != existing and (text.strip() or existing):
            p.file(".codex/config.toml", text)
    return p


def apply(p: Plan, check: bool) -> int:
    problems: list[str] = []
    root = p.root
    for rel, (content, executable) in sorted(p.files.items()):
        path = root / rel
        if not path.is_file() or path.read_text() != content:
            problems.append(f"差分あり: {rel}")
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
        if executable and not check and path.is_file():
            path.chmod(path.stat().st_mode | 0o111)
    for rel, target in sorted(p.links.items()):
        path = root / rel
        if path.is_symlink():
            if os.readlink(path) == target:
                continue
            problems.append(f"リンク先が違う: {rel}")
            if not check:
                path.unlink()
        elif path.exists():
            problems.append(f"実体があるためリンクにできない（手で確認）: {rel}")
            continue
        else:
            problems.append(f"リンク未作成: {rel}")
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(target, path)
    for d in sorted(p.link_dirs):
        base = root / d
        if not base.is_dir():
            continue
        for entry in sorted(base.iterdir()):
            rel = f"{d}/{entry.name}"
            if entry.is_symlink() and ".claude/" in os.readlink(entry) and rel not in p.links:
                problems.append(f"対応する.claude/側が無い古いリンク: {rel}")
                if not check:
                    entry.unlink()
    codex_agents = root / ".codex" / "agents"
    if codex_agents.is_dir():
        for t in sorted(codex_agents.glob("*.toml")):
            if f".codex/agents/{t.name}" not in p.files and any(k.startswith(".codex/agents/") for k in p.files):
                problems.append(f"対応する.claude/agents/が無い（手で削除）: .codex/agents/{t.name}")
    for w in p.warnings:
        print(f"警告: {w}")
    for x in problems:
        print(x)
    if check and problems:
        print("`python3 -I sync.py` を実行して同期してください。")
        return 1
    if not problems:
        print("差分なし")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--target", choices=["all", "devin", "codex"], default="all")
    ap.add_argument("--root")
    args = ap.parse_args()
    if args.root:
        root = Path(args.root).resolve()
    else:
        r = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        root = Path(r.stdout.strip()) if r.returncode == 0 else Path.cwd()
    if not (root / ".claude").is_dir():
        print(f"{root}/.claude が見つかりません", file=sys.stderr)
        return 2
    targets = {"devin", "codex"} if args.target == "all" else {args.target}
    return apply(build_plan(root, targets), args.check)


if __name__ == "__main__":
    sys.exit(main())
