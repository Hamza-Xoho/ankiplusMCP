import { test } from 'node:test';
import assert from 'node:assert/strict';
import { chmodSync, existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { repoRoot, runCli, tempDir } from './helpers.mjs';
import { HOSTS } from '../lib/hosts.mjs';

const REF = 'github:Hamza-Xoho/ankiplusMCP#v0.2.0';
const OTHER = { mcpServers: { other: { type: 'http', url: 'https://example.test/mcp' } } };
const read = (file) => JSON.parse(readFileSync(file, 'utf8'));
const backups = (dir) => readdirSync(dir).filter((name) => name.includes('.ankiplusmcp-backup-'));

/** A project folder holding a Claude Code .mcp.json; returns the paths a test needs. */
function project(content) {
  const cwd = tempDir(); const home = tempDir();
  const file = join(cwd, '.mcp.json');
  if (content !== undefined) writeFileSync(file, typeof content === 'string' ? content : JSON.stringify(content, null, 2) + '\n');
  return { cwd, home, file };
}
const init = (p, extra = [], env = {}) =>
  runCli(['init', '--host', 'claude-code', '--scope', 'project', '--no-warmup', ...extra], env, { cwd: p.cwd, home: p.home });

test('dry run shows the change and writes nothing', () => {
  const p = project();
  const r = init(p, ['--dry-run']);
  assert.equal(r.status, 0);
  assert.equal(existsSync(p.file), false);
  assert.match(r.stdout, /\.mcp\.json/);
  assert.match(r.stdout, /mcpServers\.ankiplusmcp/);
});

test('project scope writes the entry, keeps other servers and backs up', () => {
  const p = project(OTHER);
  const original = readFileSync(p.file, 'utf8');
  const r = init(p, ['--yes']);
  assert.equal(r.status, 0, r.stderr);
  const data = read(p.file);
  assert.deepEqual(data.mcpServers.other, OTHER.mcpServers.other);
  assert.equal(data.mcpServers.ankiplusmcp.command, 'npx');
  assert.deepEqual(data.mcpServers.ankiplusmcp.args.slice(0, 3), ['-y', REF, 'serve']);
  const kept = backups(p.cwd);
  assert.equal(kept.length, 1);
  assert.equal(readFileSync(join(p.cwd, kept[0]), 'utf8'), original);
});

test('source root with spaces is one array element', () => {
  const p = project(OTHER);
  init(p, ['--yes', '--source-root', '/tmp/My Drive/Lectures', '--profile', 'coldrecall']);
  const args = read(p.file).mcpServers.ankiplusmcp.args;
  assert.equal(args[args.indexOf('--source-root') + 1], '/tmp/My Drive/Lectures');
  assert.equal(args[args.indexOf('--profile') + 1], 'coldrecall');
});

test('second run changes nothing', () => {
  const p = project(OTHER);
  init(p, ['--yes']);
  const r = init(p, ['--yes', '--json']);
  assert.equal(r.status, 0);
  assert.ok(JSON.parse(r.stdout).changes.every((change) => change.status === 'unchanged'));
  assert.equal(backups(p.cwd).length, 1);
});

test('existing different entry is refused without force', () => {
  const mine = { mcpServers: { ankiplusmcp: { command: '/my/own/ankiplusmcp', args: [] } } };
  const p = project(mine);
  const before = readFileSync(p.file, 'utf8');
  assert.equal(init(p, ['--yes']).status, 3);
  assert.equal(readFileSync(p.file, 'utf8'), before);
  assert.equal(init(p, ['--yes', '--force']).status, 0);
  assert.equal(read(p.file).mcpServers.ankiplusmcp.command, 'npx');
});

test('non-JSON config is left alone and the snippet is offered', () => {
  const withComments = '{\n  // my servers\n  "mcpServers": {},\n}\n';
  const p = project(withComments);
  const r = init(p, ['--yes', '--json']);
  assert.equal(r.status, 3);
  assert.equal(readFileSync(p.file, 'utf8'), withComments);
  assert.match(JSON.parse(r.stdout).manual, /"ankiplusmcp"/);
});

test('no TTY without --yes exits 3 at once', () => {
  const p = project(OTHER);
  const before = readFileSync(p.file, 'utf8');
  const r = init(p);
  assert.equal(r.status, 3);
  assert.match(r.stderr, /--yes/);
  assert.equal(readFileSync(p.file, 'utf8'), before);
});

test('skill is installed and a differing copy is refused', () => {
  const p = project(OTHER);
  assert.equal(init(p, ['--yes']).status, 0);
  const installed = join(p.cwd, '.claude', 'skills', 'ankiplusmcp', 'SKILL.md');
  assert.equal(readFileSync(installed, 'utf8'), readFileSync(join(repoRoot, 'skills', 'ankiplusmcp', 'SKILL.md'), 'utf8'));
  const q = project(OTHER);
  mkdirSync(join(q.cwd, '.claude', 'skills', 'ankiplusmcp'), { recursive: true });
  writeFileSync(join(q.cwd, '.claude', 'skills', 'ankiplusmcp', 'SKILL.md'), 'my own edits\n');
  assert.equal(init(q, ['--yes']).status, 3);
  assert.equal(read(q.file).mcpServers.ankiplusmcp, undefined);
  assert.equal(init(q, ['--yes', '--force']).status, 0);
});

test("command hosts run the host's own command", () => {
  const home = tempDir(); const bin = join(home, 'bin'); mkdirSync(bin);
  const log = join(home, 'claude.log');
  writeFileSync(join(bin, 'claude'), `#!/bin/sh\nif [ "$2" = "get" ]; then exit 1; fi\nfor a in "$@"; do printf '%s\\n' "$a" >> "${log}"; done\n`);
  chmodSync(join(bin, 'claude'), 0o755);
  const r = runCli(['init', '--host', 'claude-code', '--scope', 'user', '--yes', '--no-warmup'], { PATH: `${bin}:${process.env.PATH}` }, { home, cwd: home });
  assert.equal(r.status, 0, r.stderr);
  assert.deepEqual(readFileSync(log, 'utf8').trim().split('\n'),
    ['mcp', 'add', '--scope', 'user', '--transport', 'stdio', 'ankiplusmcp', '--', 'npx', '-y', REF, 'serve']);
});

test('uninstall restores the original', () => {
  const p = project(OTHER);
  init(p, ['--yes']);
  const r = runCli(['uninstall', '--yes'], {}, { cwd: p.cwd, home: p.home });
  assert.equal(r.status, 0, r.stderr);
  assert.deepEqual(read(p.file), OTHER);
  assert.equal(existsSync(join(p.cwd, '.claude', 'skills', 'ankiplusmcp')), false);
});

test('print emits only the snippet', () => {
  const p = project();
  const r = runCli(['init', '--print', '--source-root', '/a'], {}, { cwd: p.cwd, home: p.home });
  assert.equal(r.status, 0);
  const entry = JSON.parse(r.stdout).mcpServers.ankiplusmcp;
  assert.equal(entry.command, 'npx');
  assert.deepEqual(entry.args, ['-y', REF, 'serve', '--source-root', '/a']);
  assert.equal(existsSync(p.file), false);
});

test('claude-desktop config path follows the platform', () => {
  const entry = { command: 'npx', args: [] };
  const mac = HOSTS['claude-desktop'].plan({ scope: 'user', entry, homedir: '/h', platform: 'darwin', env: {}, cwd: '/c' });
  const linux = HOSTS['claude-desktop'].plan({ scope: 'user', entry, homedir: '/h', platform: 'linux', env: {}, cwd: '/c' });
  assert.equal(mac.file, '/h/Library/Application Support/Claude/claude_desktop_config.json');
  assert.equal(linux.file, '/h/.config/Claude/claude_desktop_config.json');
  assert.deepEqual(mac.keyPath, ['mcpServers', 'ankiplusmcp']);
});

test('opencode entry is a local command array under mcp.servers', () => {
  const change = HOSTS.opencode.plan({ scope: 'user', entry: { command: 'npx', args: ['-y', REF, 'serve'] }, homedir: '/h', platform: 'linux', env: {}, cwd: '/c' });
  assert.equal(change.file, '/h/.config/opencode/opencode.json');
  assert.deepEqual(change.keyPath, ['mcp', 'servers', 'ankiplusmcp']);
  assert.deepEqual(change.value, { type: 'local', command: ['npx', '-y', REF, 'serve'], enabled: true });
});

test('hermes is a manual step with a YAML snippet', () => {
  const home = tempDir();
  const r = runCli(['init', '--host', 'hermes', '--yes', '--no-warmup', '--json'], {}, { home, cwd: home });
  assert.equal(r.status, 3);
  assert.match(JSON.parse(r.stdout).manual, /mcp_servers:\n  ankiplusmcp:\n    command: "npx"/);
});
