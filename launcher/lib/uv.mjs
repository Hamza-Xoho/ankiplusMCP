// Locate the `uv` binary. Hosts with a desktop UI often start servers with a
// short PATH, so the usual install locations are checked after PATH.
import { accessSync, constants } from 'node:fs';
import { delimiter, join } from 'node:path';

export const SYSTEM_DIRS = ['/opt/homebrew/bin', '/usr/local/bin'];

function executable(file) {
  try { accessSync(file, constants.X_OK); return true; } catch { return false; }
}

/**
 * @returns {string | null} Path to uv. ANKIPLUSMCP_UV, when set, is the only place looked.
 */
export function findUv(env, homedir, systemDirs = SYSTEM_DIRS) {
  if (env.ANKIPLUSMCP_UV) return executable(env.ANKIPLUSMCP_UV) ? env.ANKIPLUSMCP_UV : null;
  const name = process.platform === 'win32' ? 'uv.exe' : 'uv';
  const dirs = [
    ...(env.PATH ?? '').split(delimiter).filter(Boolean),
    join(homedir, '.local', 'bin'),
    join(homedir, '.cargo', 'bin'),
    ...systemDirs,
  ];
  for (const dir of dirs) {
    const candidate = join(dir, name);
    if (executable(candidate)) return candidate;
  }
  return null;
}

export const MISSING_UV = `ankiplusmcp: uv was not found. Install it, then run this again:
  curl -LsSf https://astral.sh/uv/install.sh | sh
or: brew install uv
`;
