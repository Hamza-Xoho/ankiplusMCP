"""Dependency checks: what is missing, whether it matters, and the command that fixes it."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from . import settings
from .store import DomainError

FIXES = {
    'tesseract': 'Install Tesseract: macOS `brew install tesseract`; Debian/Ubuntu `sudo apt-get install -y tesseract-ocr`.',
    'chromium': 'Run `npx ankiplusmcp setup` (or `ankiplusmcp setup`) to install Chromium for previews.',
}
MISSING = {
    'tesseract': 'OCR needs the Tesseract program, which was not found on PATH.',
    'chromium': 'Card previews need Playwright and its Chromium browser, which are not installed.',
}
PACKAGES = (('mcp', 'mcp'), ('pymupdf', 'PyMuPDF'), ('pillow', 'pillow'))
_chromium_found = False


def have(name):
    """Whether an optional system tool is usable. `tesseract` or `chromium`."""
    global _chromium_found
    if name == 'tesseract':
        return shutil.which('tesseract') is not None
    if name == 'chromium':
        if _chromium_found:
            return True
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as playwright:
                _chromium_found = Path(playwright.chromium.executable_path).exists()
        except Exception:  # not installed, or its driver cannot start
            return False
        return _chromium_found
    raise ValueError(name)


def require(name):
    if not have(name):
        raise DomainError('DEPENDENCY', MISSING[name], FIXES[name])


def _writable(path):
    """True when `path` exists and is writable, or its nearest existing ancestor is a writable directory."""
    probe = Path(path).expanduser()
    if probe.exists():
        return probe.is_dir() and os.access(probe, os.W_OK)
    for parent in probe.parents:
        if parent.exists():
            return parent.is_dir() and os.access(parent, os.W_OK)
    return False


def run_checks(workspace_root):
    """One record per prerequisite: name, status ok|missing, required, detail, fix."""
    checks = []

    def add(name, ok, required, detail, fix=''):
        checks.append({'name': name, 'status': 'ok' if ok else 'missing', 'required': required,
                       'detail': detail, 'fix': '' if ok else fix})

    version = '.'.join(map(str, sys.version_info[:3]))
    add('python', sys.version_info >= (3, 12), True, version, 'Use Python 3.12 or newer.')
    for name, distribution in PACKAGES:
        try:
            add(name, True, True, importlib.metadata.version(distribution))
        except importlib.metadata.PackageNotFoundError:
            add(name, False, True, 'not installed', 'Reinstall ankiplusmcp.')
    add('workspace_root', _writable(workspace_root), True, str(workspace_root),
        'Choose a writable directory with --workspace-root or ANKIPLUS_WORKSPACE_ROOT.')
    for name in ('tesseract', 'chromium'):
        found = have(name)
        add(name, found, False, 'available' if found else MISSING[name], FIXES[name])
    return checks


def doctor_main(argv):
    """Exit 0 when everything is present, 1 when only optional tools are missing, 2 when a required item is."""
    parser = argparse.ArgumentParser(prog='ankiplusmcp doctor', description='Check what AnkiPlus MCP needs to run.')
    parser.add_argument('--json', action='store_true', help='Machine-readable output on stdout.')
    parser.add_argument('--workspace-root', default=os.environ.get('ANKIPLUS_WORKSPACE_ROOT') or str(settings.default_workspace_root()))
    args = parser.parse_args(argv)
    checks = run_checks(args.workspace_root)
    required_missing = any(c['status'] == 'missing' and c['required'] for c in checks)
    optional_missing = any(c['status'] == 'missing' and not c['required'] for c in checks)
    if args.json:
        print(json.dumps({'ok': not required_missing, 'version': importlib.metadata.version('ankiplusmcp'), 'checks': checks}))
    else:
        for check in checks:
            if check['status'] == 'ok':
                print(f"ok       {check['name']}: {check['detail']}")
            else:
                kind = 'required' if check['required'] else 'optional'
                print(f"MISSING  {check['name']} ({kind}): {check['detail']} Fix: {check['fix']}")
    return 2 if required_missing else 1 if optional_missing else 0


def setup_main(argv):
    """Install Chromium for previews, after asking. Exit 3 when it cannot ask and --yes was not given."""
    parser = argparse.ArgumentParser(prog='ankiplusmcp setup', description='Install the Chromium browser used for card previews.')
    parser.add_argument('--yes', action='store_true', help='Do not ask before downloading.')
    parser.add_argument('--json', action='store_true', help='Machine-readable result on stdout.')
    args = parser.parse_args(argv)
    say = lambda text: print(text, file=sys.stderr)
    if not args.yes and not sys.stdin.isatty():
        say('ankiplusmcp setup: pass --yes to run without a prompt.')
        return 3
    say('Card previews use a Chromium browser that Playwright downloads into its own cache (roughly 150 MB or more).')
    say('OCR uses Tesseract, which this command cannot install. ' + FIXES['tesseract'])
    code = 0
    if have('chromium'):
        say('Chromium is already installed.')
    else:
        if not args.yes and input('Download Chromium now? [y/N] ').strip().lower() not in ('y', 'yes'):
            say('Nothing was downloaded.')
            return 1
        try:
            import playwright  # noqa: F401
        except ImportError:
            say('Playwright is not installed. Install ankiplusmcp with the render extra: ankiplusmcp[render].')
            code = 2
        else:
            # Progress goes to stderr so stdout stays clean for --json.
            code = subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium'], stdout=sys.stderr).returncode
    if args.json:
        tesseract = have('tesseract')
        print(json.dumps({'chromium': {'installed': have('chromium')},
                          'tesseract': {'available': tesseract, 'fix': '' if tesseract else FIXES['tesseract']}}))
    return code
