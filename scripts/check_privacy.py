#!/usr/bin/env python3
"""Fail when tracked files contain personal home-directory paths or email addresses.

Usage: python scripts/check_privacy.py
Scans `git ls-files`. Prints `path:line: match` per finding; exits 1 if any.
"""
from pathlib import Path
import re
import subprocess
import sys

HOME_PATH = re.compile(r'/(?:Users|home)/([^/\s"\'`)]+)/')
PLACEHOLDER_USERS = {'<name>', 'user', 'me', 'app', 'runner'}
EMAIL = re.compile(r'(?<![A-Za-z0-9._%+-])[A-Za-z0-9][A-Za-z0-9._%+-]*@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}')
ALLOWED_EMAILS = {'noreply@anthropic.com'}
# Decorators and scoped package names look like addresses; these are not mail domains.
# Files that hold this checker's own made-up examples.
EXEMPT = {'tests/unit/test_privacy_check.py', 'docs/superpowers/plans/2026-11-10-npx-launcher.md'}
NOT_MAIL_SUFFIXES = ('.mark.skip', '.mark.skipif', '.mark.xfail', '.mark.parametrize', '.fixture')


def find_leaks(paths):
    """Return (path, line number, matched text) for every personal path or email."""
    leaks = []
    for path in paths:
        try:
            text = Path(path).read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue  # binary or unreadable: nothing textual to leak
        for number, line in enumerate(text.splitlines(), 1):
            for match in HOME_PATH.finditer(line):
                if match[1] not in PLACEHOLDER_USERS:
                    leaks.append((Path(path), number, match[0]))
            for match in EMAIL.finditer(line):
                found = match[0]
                if found.lower() in ALLOWED_EMAILS or found.endswith(NOT_MAIL_SUFFIXES):
                    continue
                leaks.append((Path(path), number, found))
    return leaks


def main():
    root = Path(__file__).resolve().parents[1]
    listed = subprocess.run(['git', 'ls-files', '-z'], cwd=root, capture_output=True, check=True).stdout
    paths = [root/name for name in listed.decode().split('\0') if name and name not in EXEMPT]
    leaks = find_leaks(paths)
    for path, number, found in leaks:
        print(f'{path.relative_to(root)}:{number}: {found}')
    return 1 if leaks else 0


if __name__ == '__main__':
    sys.exit(main())
