#!/usr/bin/env python3
"""Fail when the npm launcher and the Python package disagree on the version.

The launcher installs the Python package tagged with its own version, so the
two numbers must move together.

Usage: python scripts/check_versions.py
"""
import json
from pathlib import Path
import sys
import tomllib


def versions(root):
    root = Path(root)
    return {
        'package.json': json.loads((root/'package.json').read_text())['version'],
        'pyproject.toml': tomllib.loads((root/'pyproject.toml').read_text())['project']['version'],
    }


def main(root=None):
    found = versions(root or Path(__file__).resolve().parents[1])
    if len(set(found.values())) == 1:
        return 0
    for name, version in found.items():
        print(f'{name}: {version}')
    return 1


if __name__ == '__main__':
    sys.exit(main())
