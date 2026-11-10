import { spawnSync } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
export const repoRoot = join(here, '..', '..');
export const cli = join(here, '..', 'cli.mjs');
export const fakeUv = join(here, 'fixtures', 'fake-uv');
export const tempDir = (prefix = 'ankiplusmcp-') => mkdtempSync(join(tmpdir(), prefix));

/** Run the launcher with a clean environment: fake uv, an empty home, and a log of uv's arguments. */
export function runCli(args, env = {}, options = {}) {
  const home = options.home ?? tempDir();
  const log = join(home, 'uv.log');
  const merged = { PATH: process.env.PATH, HOME: home, ANKIPLUSMCP_UV: fakeUv, ANKIPLUSMCP_PY_SPEC: 'SPEC', FAKE_UV_LOG: log, ...env };
  for (const key of Object.keys(merged)) if (merged[key] === undefined) delete merged[key];
  const result = spawnSync(process.execPath, [cli, ...args], { encoding: 'utf8', env: merged, cwd: options.cwd ?? home, input: options.input ?? '' });
  const calls = existsSync(log) ? readFileSync(log, 'utf8').split('\n').slice(0, -1) : [];
  return { status: result.status, stdout: result.stdout, stderr: result.stderr, calls, home };
}
