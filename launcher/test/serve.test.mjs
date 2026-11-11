import { test } from 'node:test';
import assert from 'node:assert/strict';
import { chmodSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { repoRoot, runCli, tempDir } from './helpers.mjs';
import { findUv } from '../lib/uv.mjs';

const MISSING_UV = `ankiplusmcp: uv was not found. Install it, then run this again:
  curl -LsSf https://astral.sh/uv/install.sh | sh
or: brew install uv
`;
const PREFIX = ['tool', 'run', '--from', 'SPEC', 'ankiplusmcp'];

test('serve passes flags through as single arguments', () => {
  const r = runCli(['--source-root', '/tmp/My Drive/Lectures', '--workspace-root', '/w']);
  assert.equal(r.status, 0);
  assert.deepEqual(r.calls, [...PREFIX, '--source-root', '/tmp/My Drive/Lectures', '--workspace-root', '/w']);
});

test('explicit serve word is dropped', () => {
  const r = runCli(['serve', '--workspace-root', '/w']);
  assert.deepEqual(r.calls, [...PREFIX, '--workspace-root', '/w']);
});

test('no arguments serves with no flags', () => {
  assert.deepEqual(runCli([]).calls, PREFIX);
});

test("stdout is exactly the child's", () => {
  const r = runCli([], { FAKE_UV_STDOUT: '{"jsonrpc":"2.0"}' });
  assert.equal(r.stdout, '{"jsonrpc":"2.0"}');
});

test('child failure is forwarded', () => {
  const r = runCli([], { FAKE_UV_EXIT: '7', FAKE_UV_STDERR: 'boom' });
  assert.equal(r.status, 7);
  assert.match(r.stderr, /boom/);
  assert.equal(r.stdout, '');
});

test('missing uv prints the install command and exits 127', () => {
  const r = runCli(['--workspace-root', '/w'], { ANKIPLUSMCP_UV: '/nonexistent/uv' });
  assert.equal(r.status, 127);
  assert.equal(r.stdout, '');
  assert.equal(r.stderr, MISSING_UV);
});

test('default spec pins the tag', () => {
  const r = runCli([], { ANKIPLUSMCP_PY_SPEC: undefined });
  assert.equal(r.calls[3], 'ankiplusmcp[all] @ git+https://github.com/Hamza-Xoho/ankiplusMCP@v0.3.0');
});

test('doctor --json without uv reports it and exits 2', () => {
  const r = runCli(['doctor', '--json'], { ANKIPLUSMCP_UV: '/nonexistent/uv' });
  assert.equal(r.status, 2);
  const data = JSON.parse(r.stdout);
  assert.equal(data.launcher.uv, null);
  assert.equal(data.python, null);
  assert.equal(data.launcher.node_ok, true);
});

test('doctor --json wraps the python doctor and keeps its exit code', () => {
  const r = runCli(['doctor', '--json'], { FAKE_UV_STDOUT: '{"ok":true,"checks":[]}', FAKE_UV_EXIT: '1' });
  assert.equal(r.status, 1);
  assert.deepEqual(r.calls, [...PREFIX, 'doctor', '--json']);
  assert.deepEqual(JSON.parse(r.stdout).python, { ok: true, checks: [] });
});

test('setup hands its flags to the python setup', () => {
  assert.deepEqual(runCli(['setup', '--yes']).calls, [...PREFIX, 'setup', '--yes']);
});

test('--version prints the launcher version first', () => {
  const r = runCli(['--version'], { FAKE_UV_STDOUT: 'ankiplusmcp 0.3.0\n' });
  assert.equal(r.stdout, 'ankiplusmcp-launcher 0.3.0\nankiplusmcp 0.3.0\n');
});

test('findUv: explicit override is the only place looked', () => {
  assert.equal(findUv({ ANKIPLUSMCP_UV: '/nonexistent/uv', PATH: process.env.PATH }, tempDir(), []), null);
});

test('findUv: PATH first, then the installer location under home', () => {
  const home = tempDir(); const bin = join(home, 'pathdir'); const local = join(home, '.local', 'bin');
  for (const dir of [bin, local]) { mkdirSync(dir, { recursive: true }); writeFileSync(join(dir, 'uv'), '#!/bin/sh\n'); chmodSync(join(dir, 'uv'), 0o755); }
  assert.equal(findUv({ PATH: bin }, home, []), join(bin, 'uv'));
  assert.equal(findUv({ PATH: '' }, home, []), join(local, 'uv'));
  assert.equal(findUv({ PATH: '' }, tempDir(), []), null);
});

test('package has no runtime dependencies', () => {
  const pkg = JSON.parse(readFileSync(join(repoRoot, 'package.json'), 'utf8'));
  assert.equal(pkg.dependencies, undefined);
  assert.equal(pkg.bin.ankiplusmcp, 'launcher/cli.mjs');
  assert.equal(pkg.version, '0.3.0');
});
