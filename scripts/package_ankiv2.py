#!/usr/bin/env python3
"""Package the anki2 skill and its two reviewer agents as the public `ankiv2` skill.

Usage: .venv/bin/python scripts/package_ankiv2.py [--install] [--runtime all|claude|opencode|codex]
Builds dist/ankiv2/ and dist/ankiv2.zip. With --install, copies the skill and
agents to the selected runtime's user directories (existing copies are replaced).

The packaged skill calls `cards` from PATH. Install the CLI first, for example:
    uv tool install .
or
    pipx install .
Builds go to ./builds under the folder where the skill runs (or CARDS_BUILDS).
"""
import argparse
import json
import os
import re
import shutil
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HOME = Path.home()
SKILL_SRC = REPO / '.claude/skills/anki2'
AGENTS_SRC = REPO / '.claude/agents'
DIST = REPO / 'dist/ankiv2'

DESCRIPTION = (
    'Make reviewed Anki cloze and image-occlusion cards from one lecture PDF, or resume its build. '
    'Use /ankiv2 with an absolute PDF path in Codex, Claude Code or OpenCode. '
    'Requires the cards CLI and connected Anki MCP tools. Builds persist under ./builds or CARDS_BUILDS. '
    'Not for general Anki questions or editing unrelated existing cards.'
)

OPENCODE_AGENT_PERMISSIONS = """permissions:
  - action: edit
    resource: "*"
    effect: deny
  - action: edit
    resource: "**/review/**"
    effect: allow
  - action: shell
    resource: "*"
    effect: deny
"""


def rewrite(text: str) -> str:
    text = text.replace('.venv/bin/cards', 'cards')
    text = text.replace('Run from the Cards project root.', 'Run from any folder; builds go to ./builds (or CARDS_BUILDS).')
    text = text.replace('# Anki2', '# Ankiv2')
    text = text.replace('/anki2', '/ankiv2').replace('anki2', 'ankiv2')
    return text


def opencode_agent(text: str) -> str:
    """Convert a Claude Code agent file to an OpenCode subagent file."""
    match = re.match(r'^---\n(.*?)\n---\n(.*)$', text, re.S)
    assert match, 'agent frontmatter not found'
    front, body = match.groups()
    description = next((line.split(':', 1)[1].strip() for line in front.splitlines()
                        if line.startswith('description:')), 'Card reviewer')
    body = body.replace('.venv/bin/cards', 'cards')
    return (f'---\ndescription: {json.dumps(description)}\nmode: subagent\n'
            f'{OPENCODE_AGENT_PERMISSIONS}---\n{body}')


def build() -> None:
    if DIST.parent.exists():
        shutil.rmtree(DIST.parent)
    skill_out = DIST / 'skill'
    shutil.copytree(SKILL_SRC, skill_out, ignore=shutil.ignore_patterns('.DS_Store', '__pycache__'))
    for path in skill_out.rglob('*.md'):
        path.write_text(rewrite(path.read_text()))
    skill_md = skill_out / 'SKILL.md'
    text = skill_md.read_text()
    text, count = re.subn(r'^description: .*$', 'description: ' + json.dumps(DESCRIPTION), text, count=1, flags=re.M)
    assert count == 1, 'description line not found'
    # Model IDs are runtime/provider-specific; let the host choose or the user override.
    text = re.sub(r'^(?:model|effort): .*\n', '', text, flags=re.M)
    text = re.sub(r'^name: .*$', 'name: ankiv2', text, count=1, flags=re.M)
    skill_md.write_text(text)
    for runtime in ('claude', 'opencode'):
        agents_out = DIST / 'agents' / runtime
        agents_out.mkdir(parents=True)
        for agent in AGENTS_SRC.glob('anki-*.md'):
            source = rewrite(agent.read_text())
            (agents_out / agent.name).write_text(source if runtime == 'claude' else opencode_agent(source))
    with zipfile.ZipFile(DIST.parent / 'ankiv2.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for path in sorted(DIST.rglob('*')):
            if path.is_file():
                z.write(path, 'ankiv2/' + str(path.relative_to(DIST)))
    print(f'built {DIST} and {DIST.parent / "ankiv2.zip"}')


def config_home() -> Path:
    return Path(os.environ.get('XDG_CONFIG_HOME', HOME / '.config'))


def install(runtime: str) -> None:
    targets = []
    if runtime in ('all', 'claude'):
        targets.append((HOME / '.claude/skills/ankiv2', HOME / '.claude/agents', 'claude'))
    if runtime in ('all', 'opencode'):
        targets.append((config_home() / 'opencode/skills/ankiv2', config_home() / 'opencode/agents', 'opencode'))
    if runtime in ('all', 'codex'):
        skill = HOME / '.agents/skills/ankiv2'
        if skill.exists():
            shutil.rmtree(skill)
        shutil.copytree(DIST / 'skill', skill)
        print(f'installed codex skill to {skill} (uses host reviewer subagents)')
    for skill, agents, name in targets:
        if skill.exists():
            shutil.rmtree(skill)
        shutil.copytree(DIST / 'skill', skill)
        agents.mkdir(parents=True, exist_ok=True)
        for agent in (DIST / 'agents' / name).glob('anki-*.md'):
            shutil.copy2(agent, agents / agent.name)
        print(f'installed {name} skill to {skill} and agents to {agents}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--runtime', choices=('all', 'claude', 'opencode', 'codex'), default='all')
    args = parser.parse_args()
    build()
    if args.install:
        install(args.runtime)
