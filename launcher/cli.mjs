#!/usr/bin/env node
// Argument routing only. While serving, nothing here may write to stdout:
// stdout belongs to the MCP protocol.
import { homedir } from 'node:os';
import { findUv, MISSING_UV } from './lib/uv.mjs';
import { pySpec, VERSION } from './lib/spec.mjs';
import { run, uvArgs } from './lib/serve.mjs';

const USAGE = `ankiplusmcp ${VERSION}

  npx ankiplusmcp [serve] [flags]   Start the MCP server on stdio (the default).
  npx ankiplusmcp doctor [--json]   Check Node, uv, Tesseract and Chromium.
  npx ankiplusmcp setup [--yes]     Install Chromium for card previews.
  npx ankiplusmcp --version

Server flags: --workspace-root DIR, --source-root DIR (repeatable), --profile NAME, --config FILE.
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

async function main() {
  const argv = process.argv.slice(2);
  const [first, ...rest] = argv;
  switch (first) {
    case 'doctor': return doctor(rest);
    case 'setup': return (await python(['setup', ...rest])).code;
    case '--version': case '-v': return version();
    case '--help': case '-h': case 'help': process.stdout.write(USAGE); return 0;
    case 'serve': return (await python(rest)).code;
    default: return (await python(argv)).code;
  }
}

main().then((code) => { process.exitCode = code; });
