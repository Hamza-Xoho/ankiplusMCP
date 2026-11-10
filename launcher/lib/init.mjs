// `init` registers the server in an AI host and installs the skill; `uninstall`
// reverses exactly what `init` recorded. Every change is shown before it is
// made, nothing existing is replaced without --force, and with no terminal and
// no --yes the command stops at once instead of waiting for an answer.
import { cpSync, existsSync, mkdirSync, readFileSync, readdirSync, renameSync, rmSync, statSync, unlinkSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { deleteAt, getAt, readStrictJson, sameValue, setAt, timestamp, writeWithBackup } from './configfile.mjs';
import { HOSTS, SERVER } from './hosts.mjs';
import { run, uvArgs } from './serve.mjs';
import { npxRef, pySpec, VERSION } from './spec.mjs';
import { findUv, MISSING_UV } from './uv.mjs';

const SKILL_SOURCE = fileURLToPath(new URL('../../skills/ankiplusmcp', import.meta.url));
const VALUE_FLAGS = new Set(['--host', '--scope', '--workspace-root', '--profile']);
const INIT_SWITCHES = new Set(['--yes', '--dry-run', '--force', '--print', '--json', '--no-warmup']);
const UNINSTALL_SWITCHES = new Set(['--yes', '--dry-run', '--json']);

class UsageError extends Error {}

function parse(argv, switches) {
  const flags = { sourceRoots: [] };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (switches.has(arg)) { flags[arg.slice(2)] = true; continue; }
    if (arg === '--source-root' || VALUE_FLAGS.has(arg)) {
      const value = argv[i += 1];
      if (value === undefined) throw new UsageError(`${arg} needs a value.`);
      if (arg === '--source-root') flags.sourceRoots.push(value); else flags[arg.slice(2)] = value;
      continue;
    }
    throw new UsageError(`Unknown option ${arg}.`);
  }
  return flags;
}

/** Hosts start servers from their own directory, so paths written to config must be absolute. */
function absolute(path, io) {
  const expanded = path === '~' || path.startsWith('~/') ? join(io.homedir, path.slice(1)) : path;
  return resolve(io.cwd, expanded);
}

function serverEntry(flags, io) {
  const args = ['-y', npxRef(io.env), 'serve'];
  if (flags['workspace-root']) args.push('--workspace-root', absolute(flags['workspace-root'], io));
  for (const root of flags.sourceRoots) args.push('--source-root', absolute(root, io));
  if (flags.profile) args.push('--profile', flags.profile);
  return { command: 'npx', args };
}

function dataDir(io) {
  if (io.platform === 'darwin') return join(io.homedir, 'Library', 'Application Support', SERVER);
  return join(io.env.XDG_DATA_HOME || join(io.homedir, '.local', 'share'), SERVER);
}
const manifestPath = (io) => join(dataDir(io), 'install-manifest.json');

function readManifest(io) {
  const read = readStrictJson(manifestPath(io));
  return read.ok && Array.isArray(read.data.installs) ? read.data : { installs: [] };
}

function writeManifest(io, manifest) {
  const file = manifestPath(io);
  if (manifest.installs.length === 0) { if (existsSync(file)) unlinkSync(file); return; }
  mkdirSync(dirname(file), { recursive: true });
  writeFileSync(file, JSON.stringify(manifest, null, 2) + '\n');
}

function files(dir, prefix = '') {
  return readdirSync(dir).sort().flatMap((name) => {
    const full = join(dir, name);
    return statSync(full).isDirectory() ? files(full, join(prefix, name)) : [join(prefix, name)];
  });
}

function sameDir(a, b) {
  const [left, right] = [files(a), files(b)];
  return sameValue(left, right) && left.every((name) => readFileSync(join(a, name)).equals(readFileSync(join(b, name))));
}

const nested = (keyPath, value) => keyPath.reduceRight((inner, key) => ({ [key]: inner }), value);
const target = (change) => ({
  json: () => `${change.file}  ${change.keyPath.join('.')}`,
  command: () => change.argv.join(' '),
  skill: () => change.to,
  manual: () => 'manual step',
}[change.kind]());

/** Decide what would happen to one change without doing it. */
function evaluate(change, { force, previous, io }) {
  if (change.kind === 'manual') return { status: 'manual', manual: change.text };
  if (change.kind === 'json') {
    const read = readStrictJson(change.file);
    if (!read.ok && read.reason === 'not-json') {
      return { status: 'refused', why: 'the file is not plain JSON, so it was left untouched',
        manual: `Add this to ${change.file} by hand:\n\n${JSON.stringify(nested(change.keyPath, change.value), null, 2)}\n` };
    }
    const current = read.ok ? getAt(read.data, change.keyPath) : undefined;
    if (current === undefined) return { status: 'planned' };
    if (sameValue(current, change.value)) return { status: 'unchanged' };
    return force ? { status: 'planned', replaces: true } : { status: 'refused', why: `a different ${SERVER} entry already exists; --force replaces it (a backup is kept)` };
  }
  if (change.kind === 'command') {
    if (previous?.some((done) => done.kind === 'command' && sameValue(done.argv, change.argv))) return { status: 'unchanged' };
    if (io.exec(change.exists).status !== 0) return { status: 'planned' };
    return force ? { status: 'planned', replaces: true } : { status: 'refused', why: `the host already has an ${SERVER} server; --force replaces it` };
  }
  if (!existsSync(change.to)) return { status: 'planned' };
  if (sameDir(change.from, change.to)) return { status: 'unchanged' };
  return force ? { status: 'planned', replaces: true } : { status: 'refused', why: 'a different copy of the skill is already there; --force replaces it (the old copy is kept beside it)' };
}

function apply(change, verdict, io) {
  if (change.kind === 'json') {
    const read = readStrictJson(change.file);
    const data = read.ok ? read.data : {};
    setAt(data, change.keyPath, change.value);
    const backup = writeWithBackup(change.file, data);
    return { kind: 'json', file: change.file, keyPath: change.keyPath, value: change.value, backup, created: !read.ok };
  }
  if (change.kind === 'command') {
    if (verdict.replaces) io.exec(change.undo);
    const result = io.exec(change.argv);
    if (result.status !== 0) throw new Error(`${change.argv.slice(0, 3).join(' ')} exited with ${result.status}.`);
    return { kind: 'command', argv: change.argv, undo: change.undo };
  }
  let backup = null;
  if (existsSync(change.to)) { backup = `${change.to}.ankiplusmcp-backup-${timestamp()}`; renameSync(change.to, backup); }
  mkdirSync(dirname(change.to), { recursive: true });
  cpSync(change.from, change.to, { recursive: true });
  return { kind: 'skill', to: change.to, backup };
}

async function confirmed(question, flags, io) {
  if (flags.yes) return true;
  return ['y', 'yes'].includes((await io.ask(`${question} [y/N] `)).trim().toLowerCase());
}

/** Start the server once so the first start inside the host is not the slow one, and report what is missing. */
async function warmUp(io, json) {
  const uv = findUv(io.env, io.homedir);
  if (!uv) { io.err(MISSING_UV); return { ok: false, reason: 'uv not found' }; }
  if (!json) io.err('Starting the server once so its first start in the host is quick (this can take a minute)...\n');
  const result = await run(uv, uvArgs(pySpec(io.env), ['doctor', '--json']), { captureStdout: true });
  let doctor = null;
  try { doctor = JSON.parse(result.stdout); } catch { /* it failed before reporting */ }
  if (!json && doctor) {
    for (const check of doctor.checks.filter((c) => c.status === 'missing')) {
      io.out(`  missing ${check.name}${check.required ? '' : ' (optional)'}: ${check.fix}\n`);
    }
  }
  return { ok: result.code === 0 || result.code === 1, doctor };
}

function chooseHost(flags, io) {
  if (flags.host) {
    if (!HOSTS[flags.host]) throw new UsageError(`Unknown host ${flags.host}. Choose one of: ${Object.keys(HOSTS).join(', ')}.`);
    return flags.host;
  }
  const found = Object.keys(HOSTS).filter((id) => HOSTS[id].detect(io));
  if (found.length === 1) return found[0];
  if (found.length === 0) throw new UsageError(`No supported host was found. Pass --host (${Object.keys(HOSTS).join(', ')}) or use --print.`);
  return { ambiguous: found };
}

export async function initMain(argv, io) {
  let flags; let host;
  try {
    flags = parse(argv, INIT_SWITCHES);
    if (flags.print) {
      io.out(JSON.stringify({ mcpServers: { [SERVER]: serverEntry(flags, io) } }, null, 2) + '\n');
      return 0;
    }
    host = chooseHost(flags, io);
  } catch (error) {
    if (!(error instanceof UsageError)) throw error;
    io.err(`ankiplusmcp init: ${error.message}\n`);
    return 2;
  }
  if (host.ambiguous) {
    io.err(`ankiplusmcp init: several hosts were found (${host.ambiguous.join(', ')}). Pass --host to choose one.\n`);
    return 3;
  }
  const adapter = HOSTS[host];
  const scope = flags.scope ?? 'user';
  if (!adapter.scopes.includes(scope)) {
    io.err(`ankiplusmcp init: ${adapter.label} supports --scope ${adapter.scopes.join(' or ')}.\n`);
    return 2;
  }
  if (!flags.yes && !flags['dry-run'] && !io.isTTY) {
    io.err('ankiplusmcp init: pass --yes to run without a prompt, or --dry-run to preview.\n');
    return 3;
  }

  const context = { ...io, scope, entry: serverEntry(flags, io) };
  const changes = [adapter.plan(context)];
  const skillTo = adapter.skillDir(context);
  if (skillTo && changes[0].kind !== 'manual') changes.push({ kind: 'skill', from: SKILL_SOURCE, to: skillTo });

  const manifest = readManifest(io);
  const sameInstall = (entry) => entry.host === host && entry.scope === scope && (scope !== 'project' || entry.cwd === io.cwd);
  const previous = manifest.installs.find(sameInstall)?.changes;
  const verdicts = changes.map((change) => evaluate(change, { force: flags.force, previous, io }));
  const report = changes.map((change, i) => ({ kind: change.kind, target: target(change), status: verdicts[i].status }));
  const manual = verdicts.find((verdict) => verdict.manual)?.manual ?? null;
  const say = (text) => { if (!flags.json) io.out(text); };
  const finish = (code, warmup = null) => {
    if (flags.json) io.out(JSON.stringify({ host, scope, changes: report, manual, warmup }) + '\n');
    return code;
  };

  say(`${adapter.label} (${scope} scope)\n`);
  changes.forEach((change, i) => {
    const verdict = verdicts[i];
    say(`  ${verdict.status.padEnd(9)} ${target(change)}${verdict.why ? `\n            ${verdict.why}` : ''}\n`);
  });
  if (manual) say(`\n${manual}`);
  if (verdicts.some((verdict) => verdict.status === 'refused' || verdict.status === 'manual')) {
    say('\nNothing was changed.\n');
    return finish(3);
  }
  if (flags['dry-run']) { say('\nDry run: nothing was changed.\n'); return finish(0); }

  const pending = changes.map((change, i) => [change, verdicts[i], i]).filter(([, verdict]) => verdict.status === 'planned');
  if (pending.length > 0) {
    if (!(await confirmed('Make these changes?', flags, io))) { say('Nothing was changed.\n'); return finish(1); }
    const records = (previous ?? []).filter((done) => !pending.some(([change]) => change.kind === done.kind));
    try {
      for (const [change, verdict, index] of pending) {
        records.push(apply(change, verdict, io));
        report[index].status = 'applied';
      }
    } catch (error) {
      io.err(`ankiplusmcp init: ${error.message}\n`);
      return finish(2);
    } finally {
      manifest.installs = [...manifest.installs.filter((entry) => !sameInstall(entry)), { host, scope, cwd: scope === 'project' ? io.cwd : null, version: VERSION, changes: records }];
      writeManifest(io, manifest);
    }
    say('Done. Restart the host so it picks up the new server.\n');
  } else {
    say('Already set up; nothing to change.\n');
  }
  return finish(0, flags['no-warmup'] ? null : await warmUp(io, flags.json));
}

function reverse(done, io, dryRun) {
  if (done.kind === 'json') {
    const read = readStrictJson(done.file);
    if (!read.ok) return 'gone';
    if (!sameValue(getAt(read.data, done.keyPath), done.value)) return 'kept (changed since install)';
    if (dryRun) return 'planned';
    deleteAt(read.data, done.keyPath);
    if (done.created && Object.keys(read.data).length === 0) unlinkSync(done.file); else writeWithBackup(done.file, read.data);
    return 'removed';
  }
  if (done.kind === 'command') {
    if (dryRun) return 'planned';
    return io.exec(done.undo).status === 0 ? 'removed' : 'failed';
  }
  if (!existsSync(done.to)) return 'gone';
  if (!sameDir(SKILL_SOURCE, done.to)) return 'kept (changed since install)';
  if (dryRun) return 'planned';
  rmSync(done.to, { recursive: true });
  return 'removed';
}

export async function uninstallMain(argv, io) {
  let flags;
  try { flags = parse(argv, UNINSTALL_SWITCHES); } catch (error) {
    if (!(error instanceof UsageError)) throw error;
    io.err(`ankiplusmcp uninstall: ${error.message}\n`);
    return 2;
  }
  const manifest = readManifest(io);
  const chosen = manifest.installs.filter((entry) => (!flags.host || entry.host === flags.host) && (!flags.scope || entry.scope === flags.scope));
  const say = (text) => { if (!flags.json) io.out(text); };
  if (chosen.length === 0) {
    say('Nothing installed by `ankiplusmcp init` was found.\n');
    if (flags.json) io.out(JSON.stringify({ changes: [] }) + '\n');
    return 0;
  }
  if (!flags.yes && !flags['dry-run'] && !io.isTTY) {
    io.err('ankiplusmcp uninstall: pass --yes to run without a prompt, or --dry-run to preview.\n');
    return 3;
  }
  if (!flags['dry-run'] && !(await confirmed(`Remove ${SERVER} from ${chosen.map((entry) => HOSTS[entry.host]?.label ?? entry.host).join(', ')}?`, flags, io))) {
    say('Nothing was changed.\n');
    return 1;
  }
  const report = [];
  for (const entry of chosen) {
    for (const done of entry.changes) {
      const status = reverse(done, io, flags['dry-run']);
      report.push({ host: entry.host, kind: done.kind, target: target({ ...done, argv: done.undo ?? done.argv }), status });
      say(`  ${status.padEnd(9)} ${report.at(-1).target}\n`);
    }
  }
  if (!flags['dry-run']) {
    manifest.installs = manifest.installs.filter((entry) => !chosen.includes(entry));
    writeManifest(io, manifest);
  }
  if (flags.json) io.out(JSON.stringify({ changes: report }) + '\n');
  return report.some((item) => item.status === 'failed') ? 2 : 0;
}
