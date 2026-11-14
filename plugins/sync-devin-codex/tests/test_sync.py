"""sync.py と load-claude-rules.sh のテスト。標準ライブラリのみ。

実行: python3 -m unittest discover -s plugins/sync-devin-codex/tests -v
"""
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("sync", PLUGIN / "scripts" / "sync.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

AGENT = "---\nname: {name}\ndescription: {desc}\n{extra}---\n本文\n"


class Repo:
    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / ".claude").mkdir()

    def write(self, rel, text, mode=None):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(text.encode() if isinstance(text, str) else text)
        if mode:
            p.chmod(mode)
        return p

    def settings(self, deny):
        self.write(".claude/settings.json", json.dumps({"permissions": {"deny": deny}}))

    def sync(self, check=False, targets=("devin", "codex")):
        plan = sync.build_plan(self.root, set(targets))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = sync.apply(plan, check)
        return code, out.getvalue(), plan

    def read(self, rel):
        return (self.root / rel).read_text()

    def cleanup(self):
        self._tmp.cleanup()


class Base(unittest.TestCase):
    def setUp(self):
        self.r = Repo()
        self.addCleanup(self.r.cleanup)


class LegacyBashSyntax(Base):
    def test_colon_star_is_converted(self):  # 指摘1
        self.r.settings(["Bash(git push:*)", "Bash(rm:*)"])
        self.r.sync()
        deny = json.loads(self.r.read(".devin/config.json"))["permissions"]["deny"]
        self.assertEqual(deny, ["Exec(git push)", "Exec(rm)"])
        rules = self.r.read(".codex/rules/deny.rules")
        self.assertIn('pattern = ["git", "push"]', rules)
        self.assertIn('pattern = ["rm"]', rules)
        self.assertNotIn(":", rules.split("prefix_rule(")[1].split("justification")[0])


class DevinDenyOwnership(Base):
    def test_user_entries_kept_and_generated_removed(self):  # 指摘2
        self.r.settings(["Read(./.env)", "Bash(sudo *)"])
        self.r.sync()
        cfg = json.loads(self.r.read(".devin/config.json"))
        cfg["permissions"]["deny"].insert(0, "Read(./my-own)")
        self.r.write(".devin/config.json", json.dumps(cfg))
        self.r.sync()
        self.assertEqual(json.loads(self.r.read(".devin/config.json"))["permissions"]["deny"][0], "Read(./my-own)")
        self.r.settings([])  # Claude 側のルールをすべて消す
        code, _, _ = self.r.sync()
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(self.r.read(".devin/config.json"))["permissions"]["deny"], ["Read(./my-own)"])
        self.assertFalse((self.r.root / ".codex/rules/deny.rules").exists())
        self.assertFalse((self.r.root / sync.DEVIN_STATE).exists())
        self.assertEqual(self.r.sync(check=True)[0], 0)


class FrontmatterAndAgents(Base):
    def agent(self, fname, name="a", desc="d", extra="", raw=None):
        self.r.write(f".claude/agents/{fname}.md", raw or AGENT.format(name=name, desc=desc, extra=extra))

    def toml(self, name="a"):
        return self.r.read(f".codex/agents/{name}.toml")

    def test_quotes_are_stripped(self):  # 指摘3
        self.agent("a", desc='"Reviews code"')
        self.r.sync()
        self.assertIn('description = "Reviews code"', self.toml())

    def test_yaml_list_tools_are_read_only(self):  # 指摘3
        self.agent("a", extra="tools:\n  - Read\n  - Grep\n")
        self.agent("b", name="b", extra="tools: [Read, Glob]\n")
        self.r.sync()
        self.assertIn("使用できる操作の制限", self.toml("a"))
        self.assertIn("使用できる操作の制限", self.toml("b"))

    def test_other_tools_not_read_only(self):
        self.agent("a", extra="tools: Read, Bash\n")
        self.r.sync()
        self.assertNotIn("使用できる操作の制限", self.toml())

    def test_multiline_description(self):  # 指摘3
        self.agent("a", raw="---\nname: a\ndescription: >\n  一行目\n  二行目\ntools: Read\n---\n本文")
        self.r.sync()
        self.assertIn('description = "一行目 二行目"', self.toml())
        self.assertIn("使用できる操作の制限", self.toml())

    def test_crlf_and_no_trailing_newline(self):  # 指摘3
        self.agent("a", raw="---\r\nname: a\r\ndescription: d\r\ntools: Read\r\n---")
        code, out, _ = self.r.sync()
        self.assertTrue((self.r.root / ".codex/agents/a.toml").exists(), out)
        self.assertIn("使用できる操作の制限", self.toml())

    def test_unsafe_name_is_skipped(self):  # 指摘4
        self.agent("evil", name="../../evil")
        _, out, _ = self.r.sync()
        self.assertIn("nameに使えない文字", out)
        self.assertFalse((self.r.root / "evil.toml").exists())
        self.assertFalse(list((self.r.root / ".codex").rglob("*evil*")))

    def test_duplicate_name_is_skipped(self):  # 指摘4
        self.agent("one", name="same", desc="first")
        self.agent("two", name="same", desc="second")
        _, out, _ = self.r.sync()
        self.assertIn("重複", out)
        self.assertIn("first", self.toml("same"))


class CodexFilesystem(Base):
    def test_edit_only_is_read_only_and_read_is_deny(self):  # 指摘5
        self.r.settings(["Read(./.env)", "Edit(./.env)", "Edit(src/generated/**)", "Write(~/x)"])
        _, out, _ = self.r.sync()
        cfg = self.r.read(".codex/config.toml")
        self.assertIn('".env" = "deny"', cfg)
        self.assertIn('"src/generated/**" = "read"', cfg)
        self.assertIn('"**/src/generated/**" = "read"', cfg)
        self.assertNotIn("~", cfg)
        self.assertIn("~ や絶対パス", out)


class GlobSnapshot(Base):
    def test_warns_and_picks_up_after_resync(self):  # 指摘6
        self.r.write(".env", "")
        self.r.settings(["Bash(cat .env*)"])
        _, out, _ = self.r.sync()
        self.assertIn("同期時点", out)
        self.assertNotIn(".env.production", self.r.read(".codex/rules/deny.rules"))
        self.r.write(".env.production", "")
        self.assertEqual(self.r.sync(check=True)[0], 1)  # --check が新しい秘密ファイルを検知する
        self.r.sync()
        self.assertIn(".env.production", self.r.read(".codex/rules/deny.rules"))


class CodexConfigToml(Base):
    def test_duplicate_tables_are_rejected(self):  # 指摘7
        self.r.settings(["Read(./.env)"])
        self.r.write(".codex/config.toml", '[permissions.project]\nextends = ":workspace"\n')
        before = self.r.read(".codex/config.toml")
        code, out, _ = self.r.sync()
        self.assertEqual(code, 1)
        self.assertIn("permissions.project", out)
        self.assertEqual(self.r.read(".codex/config.toml"), before)

    def test_user_mcp_server_collision(self):  # 指摘7
        self.r.write(".mcp.json", json.dumps({"mcpServers": {"foo": {"command": "x"}}}))
        self.r.write(".codex/config.toml", '[mcp_servers.foo]\ncommand = "y"\n')
        code, out, _ = self.r.sync()
        self.assertEqual(code, 1)
        self.assertIn("mcp_servers.foo", out)

    def test_mcp_has_its_own_block(self):  # 指摘7
        self.r.write(".mcp.json", json.dumps({"mcpServers": {"foo": {"command": "x", "env": {"K": "${K}"}}}}))
        self.r.sync()
        cfg = self.r.read(".codex/config.toml")
        self.assertIn("sync-devin-codex (mcp-servers)", cfg)
        self.assertNotIn("permissions-tables", cfg)
        self.assertIn('env_vars = ["K"]', cfg)
        self.assertEqual(self.r.sync(check=True)[0], 0)

    def test_all_blocks_are_idempotent_from_the_first_run(self):
        self.r.settings(["Read(./.env)", "Edit(./x)"])
        self.r.write(".mcp.json", json.dumps({"mcpServers": {"foo": {"command": "x"}}}))
        self.r.write(".codex/config.toml", 'model = "x"\n')
        self.r.sync()
        first = self.r.read(".codex/config.toml")
        self.assertEqual(self.r.sync(check=True)[0], 0)
        self.r.sync()
        self.assertEqual(self.r.read(".codex/config.toml"), first)
        self.r.settings([])  # ルールを消すとブロックだけが消え、ユーザー設定は残る
        self.r.sync()
        cfg = self.r.read(".codex/config.toml")
        self.assertIn('model = "x"', cfg)
        self.assertNotIn("(permissions", cfg)
        self.assertIn("(mcp-servers)", cfg)

    def test_user_settings_outside_block_are_kept(self):
        self.r.settings(["Read(./.env)"])
        self.r.write(".codex/config.toml", 'model = "x"\n')
        self.r.sync()
        self.assertIn('model = "x"', self.r.read(".codex/config.toml"))
        self.assertEqual(self.r.sync(check=True)[0], 0)


class StaleCleanup(Base):
    def test_links_removed_when_source_dir_is_gone(self):  # 指摘8
        self.r.write(".claude/skills/demo/SKILL.md", "---\nname: demo\ndescription: d\n---\n")
        self.r.write(".claude/agents/a.md", AGENT.format(name="a", desc="d", extra=""))
        self.r.sync()
        self.assertTrue((self.r.root / ".devin/skills/demo").is_symlink())
        import shutil
        shutil.rmtree(self.r.root / ".claude/skills")
        shutil.rmtree(self.r.root / ".claude/agents")
        self.r.sync()
        for rel in (".devin/skills/demo", ".agents/skills/demo", ".devin/agents/a.md"):
            self.assertFalse((self.r.root / rel).is_symlink(), rel)

    def test_stale_codex_agent_is_reported_even_if_no_agents_left(self):  # 指摘8
        self.r.write(".claude/agents/a.md", AGENT.format(name="a", desc="d", extra=""))
        self.r.sync()
        (self.r.root / ".claude/agents/a.md").unlink()
        code, out, _ = self.r.sync(check=True)
        self.assertEqual(code, 1)
        self.assertIn(".codex/agents/a.toml", out)


class ExecutableBit(Base):
    def test_missing_exec_bit_is_detected_and_fixed(self):  # 指摘9
        self.r.write(".claude/rules/r.md", "本文\n")
        self.r.sync()
        hook = self.r.root / ".codex/hooks/load-claude-rules.sh"
        hook.chmod(0o644)
        code, out, _ = self.r.sync(check=True)
        self.assertEqual(code, 1)
        self.assertIn("実行ビット", out)
        self.r.sync()
        self.assertTrue(os.access(hook, os.X_OK))
        self.assertEqual(self.r.sync(check=True)[0], 0)


class RulesHookScript(Base):
    def run_hook(self):
        return subprocess.run(["bash", str(PLUGIN / "assets" / "load-claude-rules.sh")],
                              cwd=self.r.root, capture_output=True, text=True, check=True).stdout

    def test_crlf_frontmatter_is_parsed(self):  # 指摘10
        self.r.write(".claude/rules/a.md", b'---\r\npaths:\r\n  - "src/**"\r\n---\r\n\r\nBODY-A\r\n')
        out = self.run_hook()
        self.assertIn("適用対象パス: src/**", out)
        self.assertIn("BODY-A", out)
        self.assertNotIn("paths:", out)

    def test_trailing_space_after_dashes(self):  # 指摘10
        self.r.write(".claude/rules/b.md", "--- \npaths: [a/**, b/**]\n---  \nBODY-B\n")
        out = self.run_hook()
        self.assertIn("適用対象パス: a/**, b/**", out)
        self.assertNotIn("paths:", out)

    def test_no_frontmatter(self):
        self.r.write(".claude/rules/c.md", "BODY-C\n")
        out = self.run_hook()
        self.assertIn("BODY-C", out)
        self.assertNotIn("適用対象パス:", out)


if __name__ == "__main__":
    unittest.main()
