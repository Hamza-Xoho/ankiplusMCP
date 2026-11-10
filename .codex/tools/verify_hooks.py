#!/usr/bin/env python3
"""verify_hooks.py — fire every hook with real-shaped payloads and check the outcome.

Proves the scripts work (block, stay quiet, fail closed). It does NOT prove the
hooks are wired: that needs one real blocked action in Codex and in Claude Code
(HANDOVER, Setup step 6). Run from the repo root:

    python3 .codex/tools/verify_hooks.py
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CODEX = os.path.join(ROOT, ".codex", "hooks")
CLAUDE = os.path.join(ROOT, ".claude", "hooks")
results = []


BASH = shutil.which("bash")


def no_python_path():
    """A PATH with the shell tools the wrappers need but no python3, to prove they fail closed."""
    d = tempfile.mkdtemp(prefix="nopy-")
    for tool in ("bash", "dirname", "basename", "env"):
        src = shutil.which(tool)
        if src:
            os.symlink(src, os.path.join(d, tool))
    return d


def run(wrapper, script, payload, env_extra=None, args=(), raw=None, path_env=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    if path_env is not None:
        env["PATH"] = path_env
    data = raw if raw is not None else json.dumps(payload)
    p = subprocess.run([BASH, wrapper, script, *args], input=data, capture_output=True, text=True, env=env)
    return p.returncode, p.stderr.strip()


def check(name, got, want):
    ok = got[0] == want
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}  (exit {got[0]}, want {want})" + ("" if ok else f"\n      stderr: {got[1][:300]}"))


def patch(*ops):
    return "*** Begin Patch\n" + "\n".join(ops) + "\n*** End Patch\n"


def codex_tests():
    w = os.path.join(CODEX, "run.sh")
    repo = tempfile.mkdtemp(prefix="cx-")
    os.makedirs(os.path.join(repo, ".git"))
    os.makedirs(os.path.join(repo, ".codex"))
    os.makedirs(os.path.join(repo, "tests", "contract"))
    os.makedirs(os.path.join(repo, "src", "cards", "write"))
    frozen = "tests/contract/test_p0_foundations.py"
    with open(os.path.join(repo, frozen), "w") as f:
        f.write("def test_x():\n    assert True\n")
    digest = hashlib.sha256(open(os.path.join(repo, frozen), "rb").read()).hexdigest()
    with open(os.path.join(repo, ".codex", "contract.sha256"), "w") as f:
        f.write(f"{digest}  {frozen}\n")
    base = {"session_id": "s", "cwd": repo, "hook_event_name": "PreToolUse", "turn_id": "t", "tool_use_id": "u"}

    def ap(cmd):
        return {**base, "tool_name": "apply_patch", "tool_input": {"command": cmd}}

    def sh(cmd):
        return {**base, "tool_name": "Bash", "tool_input": {"command": cmd}}

    fc = "freeze_contract.py"
    check("codex freeze: edit frozen test blocked", run(w, fc, ap(patch(f"*** Update File: {frozen}", "@@", "-    assert True", "+    assert 1"))), 2)
    check("codex freeze: delete frozen test blocked", run(w, fc, ap(patch(f"*** Delete File: {frozen}"))), 2)
    check("codex freeze: absolute path to frozen test blocked", run(w, fc, ap(patch(f"*** Update File: {repo}/{frozen}", "+x"))), 2)
    check("codex freeze: edit .codex/hooks.json blocked", run(w, fc, ap(patch("*** Update File: .codex/hooks.json", "+{}"))), 2)
    check("codex freeze: skip marker in new contract test blocked",
          run(w, fc, ap(patch("*** Add File: tests/contract/test_p1_meter.py", "+import pytest", "+@pytest.mark.skip", "+def test_a(): pass"))), 2)
    check("codex freeze: new unfrozen contract test allowed",
          run(w, fc, ap(patch("*** Add File: tests/contract/test_p1_meter.py", "+def test_fr24_x():", "+    assert False"))), 0)
    check("codex freeze: normal src edit allowed", run(w, fc, ap(patch("*** Update File: src/cards/cli.py", "+x = 1"))), 0)
    check("codex freeze: rm frozen via Bash blocked", run(w, fc, sh(f"rm {frozen}")), 2)
    check("codex freeze: sed -i on contract via Bash blocked", run(w, fc, sh("sed -i 's/a/b/' tests/contract/test_p0_foundations.py")), 2)
    check("codex freeze: redirect into .codex via Bash blocked", run(w, fc, sh("echo x > .codex/contract.sha256")), 2)
    check("codex freeze: git checkout of contract blocked", run(w, fc, sh("git checkout -- tests/contract/")), 2)
    check("codex freeze: pytest on contract allowed (2>&1 not a write)", run(w, fc, sh("pytest tests/contract -q 2>&1 | tail -5")), 0)
    check("codex freeze: cat contract allowed", run(w, fc, sh("cat tests/contract/test_p0_foundations.py")), 0)
    check("codex freeze: ordinary command allowed", run(w, fc, sh("ls src && python -m pytest tests/unit")), 0)
    check("codex freeze: malformed payload fails closed", run(w, fc, None, raw="{not json"), 2)
    check("codex freeze: no python3 on PATH fails closed",
          run(w, fc, ap(patch("*** Update File: src/a.py", "+x")), path_env=no_python_path()), 2)

    nn = "no_network.py"
    check("codex no_network pre: requests import blocked",
          run(w, nn, ap(patch("*** Update File: src/cards/check/lint.py", "+import requests")), args=("pre",)), 2)
    check("codex no_network pre: urllib.request blocked",
          run(w, nn, ap(patch("*** Add File: src/cards/meter/x.py", "+from urllib.request import urlopen")), args=("pre",)), 2)
    check("codex no_network pre: direct.py allowed",
          run(w, nn, ap(patch("*** Add File: src/cards/write/direct.py", "+import urllib.request")), args=("pre",)), 0)
    check("codex no_network pre: tests may import http",
          run(w, nn, ap(patch("*** Add File: tests/unit/test_x.py", "+import http.server")), args=("pre",)), 0)
    check("codex no_network pre: plain import allowed",
          run(w, nn, ap(patch("*** Update File: src/cards/cli.py", "+import json")), args=("pre",)), 0)
    bad = os.path.join(repo, "src", "cards", "source.py")
    with open(bad, "w") as f:
        f.write("import json\nimport socket\n")
    check("codex no_network post: existing socket import in touched file caught",
          run(w, nn, {**ap(patch("*** Update File: src/cards/source.py", "+x = 1")), "hook_event_name": "PostToolUse"}, args=("post",)), 2)
    with open(bad, "w") as f:
        f.write("import json\n")
    check("codex no_network post: clean file quiet",
          run(w, nn, {**ap(patch("*** Update File: src/cards/source.py", "+x = 1")), "hook_event_name": "PostToolUse"}, args=("post",)), 0)

    rc, err = subprocess.run(["bash", w, "inject_invariants.py"], input="{}", capture_output=True, text=True,
                             env={**os.environ, "NONBLOCKING": "1"}).returncode, ""
    out = subprocess.run(["bash", w, "inject_invariants.py"], input="{}", capture_output=True, text=True,
                         env={**os.environ, "NONBLOCKING": "1"}).stdout
    ok = rc == 0 and "INV-1" in json.loads(out)["hookSpecificOutput"]["additionalContext"]
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  codex session start: injects invariants")
    shutil.rmtree(repo)


def claude_tests():
    w = os.path.join(CLAUDE, "run.sh")
    proj = tempfile.mkdtemp(prefix="cc-")
    env = {"CLAUDE_PROJECT_DIR": proj}
    base = {"session_id": "s", "cwd": proj, "hook_event_name": "PreToolUse", "tool_use_id": "u"}

    def call(tool, inp):
        return {**base, "tool_name": tool, "tool_input": inp}

    check("claude fork: fork blocked", run(w, "block_fork.py", call("Agent", {"subagent_type": "fork", "prompt": "x"}), env), 2)
    check("claude fork: anki-maintainer allowed", run(w, "block_fork.py", call("Agent", {"subagent_type": "anki-maintainer", "prompt": "x"}), env), 0)
    check("claude fork: Explore allowed", run(w, "block_fork.py", call("Agent", {"subagent_type": "Explore", "prompt": "x"}), env), 0)
    check("claude fork: malformed payload fails closed", run(w, "block_fork.py", None, env, raw="nope"), 2)

    pdf = call("Read", {"file_path": "/path/to/lectures/MED241_L006.PDF"})
    check("claude pdf: no active build, mode=build -> allowed (old /anki works)", run(w, "block_pdf_read.py", pdf, env), 0)
    check("claude pdf: mode=always -> blocked", run(w, "block_pdf_read.py", pdf, {**env, "CARDS_PDF_GUARD": "always"}), 2)
    os.makedirs(os.path.join(proj, "builds", "2026-11-05_MED241-L006"))
    with open(os.path.join(proj, "builds", ".current"), "w") as f:
        f.write("2026-11-05_MED241-L006\n")
    check("claude pdf: active build -> blocked (any case)", run(w, "block_pdf_read.py", pdf, env), 2)
    check("claude pdf: png allowed during build", run(w, "block_pdf_read.py", call("Read", {"file_path": "builds/x/source/pages/p10.png"}), env), 0)

    check("claude http: curl 127.0.0.1 blocked", run(w, "block_local_http.py", call("Bash", {"command": "curl -s http://127.0.0.1:3141/"}), env), 2)
    check("claude http: localhost:8765 blocked", run(w, "block_local_http.py", call("Bash", {"command": "python3 -c \"urlopen('http://localhost:8765')\""}), env), 2)
    check("claude http: cards command allowed", run(w, "block_local_http.py", call("Bash", {"command": ".venv/bin/cards check --build builds/x"}), env), 0)

    bdir = os.path.join(proj, "builds", "2026-11-05_MED241-L006")
    drafts = os.path.join(bdir, "drafts.jsonl")
    with open(drafts, "w") as f:
        f.write('{"id":"n001"}\n')
    add = call("mcp__anki__add_notes", {"deck_name": "x", "model_name": "ColdRecall Cloze", "notes": []})

    def state(status, h):
        with open(os.path.join(bdir, "build.json"), "w") as f:
            json.dump({"gate": {"status": status, "drafts_sha256": h}}, f)

    state("pending", None)
    check("claude write: blocked before gate", run(w, "require_review_before_write.py", add, env), 2)
    good = hashlib.sha256(open(drafts, "rb").read()).hexdigest()
    state("passed", good)
    check("claude write: allowed after gate", run(w, "require_review_before_write.py", add, env), 0)
    with open(drafts, "a") as f:
        f.write('{"id":"n002"}\n')
    check("claude write: blocked when drafts changed after gate", run(w, "require_review_before_write.py", add, env), 2)
    check("claude write: unrelated anki tool not guarded",
          run(w, "require_review_before_write.py", call("mcp__anki__find_notes", {"query": "x"}), env), 0)
    with open(os.path.join(bdir, "build.json"), "w") as f:
        f.write("{broken")
    check("claude write: unreadable build.json fails closed", run(w, "require_review_before_write.py", add, env), 2)
    os.remove(os.path.join(proj, "builds", ".current"))
    check("claude write: no active build -> allowed (manual use)", run(w, "require_review_before_write.py", add, env), 0)
    check("claude write: no python fails closed",
          run(w, "require_review_before_write.py", add, {**env, "CLAUDE_PROJECT_DIR": tempfile.mkdtemp()}, path_env=no_python_path()), 2)
    shutil.rmtree(proj)


if __name__ == "__main__":
    codex_tests()
    claude_tests()
    failed = results.count(False)
    print(f"\n{len(results) - failed}/{len(results)} hook checks passed")
    sys.exit(1 if failed else 0)
