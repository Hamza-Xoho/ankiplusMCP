// Careful edits to a host's JSON config: strict parsing only, a backup before
// every write, and no touching a file this code cannot fully understand.
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname } from 'node:path';
import { isDeepStrictEqual } from 'node:util';

/** @returns {{ok: true, data: object} | {ok: false, reason: 'missing' | 'not-json'}} */
export function readStrictJson(file) {
  if (!existsSync(file)) return { ok: false, reason: 'missing' };
  try {
    const data = JSON.parse(readFileSync(file, 'utf8'));
    if (data === null || typeof data !== 'object' || Array.isArray(data)) return { ok: false, reason: 'not-json' };
    return { ok: true, data };
  } catch {
    return { ok: false, reason: 'not-json' }; // comments, trailing commas, truncation
  }
}

export function timestamp(now = new Date()) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
}

/** Write JSON, first copying any existing file aside. @returns {string | null} the backup path */
export function writeWithBackup(file, data) {
  let backup = null;
  if (existsSync(file)) {
    backup = `${file}.ankiplusmcp-backup-${timestamp()}`;
    copyFileSync(file, backup);
  } else {
    mkdirSync(dirname(file), { recursive: true });
  }
  writeFileSync(file, JSON.stringify(data, null, 2) + '\n');
  return backup;
}

export function getAt(data, keyPath) {
  return keyPath.reduce((node, key) => (node !== null && typeof node === 'object' ? node[key] : undefined), data);
}

export function setAt(data, keyPath, value) {
  let node = data;
  for (const key of keyPath.slice(0, -1)) {
    if (node[key] === null || typeof node[key] !== 'object' || Array.isArray(node[key])) node[key] = {};
    node = node[key];
  }
  node[keyPath.at(-1)] = value;
}

/** Remove a key, then any parent objects that removal left empty. */
export function deleteAt(data, keyPath) {
  const parents = [data];
  for (const key of keyPath.slice(0, -1)) {
    const next = parents.at(-1)[key];
    if (next === null || typeof next !== 'object') return;
    parents.push(next);
  }
  delete parents.at(-1)[keyPath.at(-1)];
  for (let depth = parents.length - 1; depth > 0; depth -= 1) {
    if (Object.keys(parents[depth]).length > 0) break;
    delete parents[depth - 1][keyPath[depth - 1]];
  }
}

export const sameValue = isDeepStrictEqual;
