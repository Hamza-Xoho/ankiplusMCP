#!/usr/bin/env node
// Argument routing only. While serving, nothing here may write to stdout:
// stdout belongs to the MCP protocol.
import { spawnSync } from 'node:child_process';
import { homedir } from 'node:os';
import { createInterface } from 'node:readline/promises';
import { findUv, MISSING_UV } from './lib/uv.mjs';
import { pySpec, VERSION } from './lib/spec.mjs';
import { run, uvArgs } from './lib/serve.mjs';

const USAGE = `ankiplusmcp ${VERSION}

  npx ankiplusmcp [serve] [flags]   Start the MCP server on stdio (the default).
  npx ankiplusmcp init [flags]      Register the server in an AI host and install the skill.
                                    --host claude-code|claude-desktop|codex|opencode|hermes
                                    --scope user|project  --source-root DIR  --workspace-root DIR
                                    --profile NAME  --dry-run  --yes  --force  --print  --json
  npx ankiplusmcp uninstall         Remove what init added.
  npx ankiplusmcp doctor [--json]   Check Node, uv, Tesseract and Chromium.
  npx ankiplusmcp setup [--yes]     Install Chromium for card previews.
  npx ankiplusmcp --version

Server flags: --workspace-root DIR, --source-root DIR (repeatable), --profile NAME, --config FILE, --browser VALUE (auto, chromium, chrome or a path).
`;

const env = process.env;
const uv = () => findUv(env, homedir());

/** Hand a Python subcommand its arguments; without uv, say how to get it. */
async function python(args, options) {
  const found = uv();
  if (!found) { process.stderr.write(MISSING_UV); return { code: 127, stdout: '' }; }
  return run(found, uvArgs(pySpec(env), args), options);
}

async function doctor(args) {
  const json = args.includes('--json');
  const found = uv();
  const nodeOk = Number(process.versions.node.split('.')[0]) >= 18;
  const launcher = { node: process.versions.node, node_ok: nodeOk, uv: found };
  if (!json) {
    process.stderr.write(`${nodeOk ? 'ok      ' : 'MISSING '} node: ${process.versions.node}${nodeOk ? '' : ' (18 or newer is required)'}\n`);
    if (found) process.stderr.write(`ok       uv: ${found}\n`);
  }
  if (!found) {
    if (json) process.stdout.write(JSON.stringify({ launcher, python: null }) + '\n');
    else process.stderr.write(MISSING_UV);
    return 2;
  }
  const result = await python(['doctor', ...args], { captureStdout: json });
  if (json) {
    let parsed = null;
    try { parsed = JSON.parse(result.stdout); } catch { /* the python side failed before reporting */ }
    process.stdout.write(JSON.stringify({ launcher, python: parsed }) + '\n');
  }
  return nodeOk ? result.code : 2;
}

async function version() {
  process.stdout.write(`ankiplusmcp-launcher ${VERSION}\n`);
  if (!uv()) { process.stderr.write(MISSING_UV); return 0; }
  return (await python(['--version'])).code;
}

/** Everything init/uninstall touch, gathered so tests can run them in a sandboxed home. */
function io() {
  return {
    env,
    homedir: homedir(),
    cwd: process.cwd(),
    platform: process.platform,
    isTTY: Boolean(process.stdin.isTTY),
    out: (text) => process.stdout.write(text),
    err: (text) => process.stderr.write(text),
    exec: (argv) => spawnSync(argv[0], argv.slice(1), { stdio: ['ignore', 'ignore', 'inherit'], env }),
    async ask(question) {
      const prompt = createInterface({ input: process.stdin, output: process.stderr });
      try { return await prompt.question(question); } finally { prompt.close(); }
    },
  };
}

async function main() {
  const argv = process.argv.slice(2);
  const [first, ...rest] = argv;
  switch (first) {
    case 'init': return (await import('./lib/init.mjs')).initMain(rest, io());
    case 'uninstall': return (await import('./lib/init.mjs')).uninstallMain(rest, io());
    case 'doctor': return doctor(rest);
    case 'setup': return (await python(['setup', ...rest])).code;
    case '--version': case '-v': return version();
    case '--help': case '-h': case 'help': process.stdout.write(USAGE); return 0;
    case 'serve': return (await python(rest)).code;
    default: return (await python(argv)).code;
  }
}

main().then((code) => { process.exitCode = code; });
