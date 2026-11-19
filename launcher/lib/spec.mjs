// What to run and from where. The launcher's version decides the Python
// version, so the two cannot drift apart.
import { readFileSync } from 'node:fs';
import { isAbsolute, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const pkg = JSON.parse(readFileSync(new URL('../../package.json', import.meta.url), 'utf8'));
export const VERSION = pkg.version;
export const REPOSITORY = 'Hamza-Xoho/ankiplusMCP';

/** The Python requirement uv installs. ANKIPLUSMCP_PY_SPEC overrides it for development. */
export function pySpec(env) {
  return env.ANKIPLUSMCP_PY_SPEC || `ankiplusmcp[all] @ git+https://github.com/${REPOSITORY}@v${VERSION}`;
}

/** What host configs pass to `npx -y`. Becomes `ankiplusmcp@<version>` once published to npm. */
export function npxRef(env, cwd = process.cwd()) {
  const ref = env.ANKIPLUSMCP_NPX_REF || `github:${REPOSITORY}#v${VERSION}`;
  // npm exec treats a bare absolute tarball path as a command. Explicit file:
  // specs also keep relative paths independent of the host's working directory.
  if (ref.startsWith('file://')) return `file:${fileURLToPath(ref)}`;
  if (ref.startsWith('file:')) return `file:${resolve(cwd, ref.slice(5))}`;
  if (isAbsolute(ref) || ref.startsWith('./') || ref.startsWith('../') || (ref.endsWith('.tgz') && !/^[a-z][a-z\d+.-]*:/i.test(ref))) {
    return `file:${resolve(cwd, ref)}`;
  }
  return ref;
}
