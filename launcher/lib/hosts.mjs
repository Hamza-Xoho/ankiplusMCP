// One adapter per AI host: where its MCP config and skills live, and how a
// stdio server is registered there. Formats checked on 2026-11-10 against
// `claude mcp add --help`, an OpenCode v2 config, the Codex config reference
// and the Hermes Agent MCP config reference.
import { accessSync, constants, existsSync } from 'node:fs';
import { delimiter, join } from 'node:path';

export const SERVER = 'ankiplusmcp';

function onPath(name, env) {
  for (const dir of (env.PATH ?? '').split(delimiter).filter(Boolean)) {
    try { accessSync(join(dir, name), constants.X_OK); return true; } catch { /* keep looking */ }
  }
  return false;
}

const quote = (value) => JSON.stringify(value);
const shellLine = (argv) => argv.map((part) => (/^[\w@%+=:,./#-]+$/.test(part) ? part : `'${part.replaceAll("'", `'\\''`)}'`)).join(' ');

/**
 * plan() returns one change:
 *   {kind: 'json', file, keyPath, value}          edit a strict-JSON config file
 *   {kind: 'command', argv, undo, exists}         run the host's own CLI
 *   {kind: 'manual', text}                        nothing safe to automate; show what to add
 */
export const HOSTS = {
  'claude-code': {
    label: 'Claude Code',
    scopes: ['user', 'project'],
    detect: ({ env, homedir }) => onPath('claude', env) || existsSync(join(homedir, '.claude')),
    plan({ scope, entry, cwd, env }) {
      if (scope === 'project') {
        return { kind: 'json', file: join(cwd, '.mcp.json'), keyPath: ['mcpServers', SERVER], value: { type: 'stdio', ...entry } };
      }
      const argv = ['claude', 'mcp', 'add', '--scope', 'user', '--transport', 'stdio', SERVER, '--', entry.command, ...entry.args];
      if (!onPath('claude', env)) return { kind: 'manual', text: `Run this once the claude command is available:\n  ${shellLine(argv)}` };
      return { kind: 'command', argv, undo: ['claude', 'mcp', 'remove', '--scope', 'user', SERVER], exists: ['claude', 'mcp', 'get', SERVER] };
    },
    skillDir: ({ scope, cwd, homedir }) => join(scope === 'project' ? cwd : homedir, '.claude', 'skills', SERVER),
  },

  'claude-desktop': {
    label: 'Claude Desktop',
    scopes: ['user'],
    detect: ({ homedir, platform }) => existsSync(join(homedir, ...desktopDir(platform))),
    plan: ({ entry, homedir, platform }) => ({
      kind: 'json', file: join(homedir, ...desktopDir(platform), 'claude_desktop_config.json'), keyPath: ['mcpServers', SERVER], value: { ...entry },
    }),
    skillDir: () => null,
  },

  codex: {
    label: 'Codex',
    scopes: ['user'],
    detect: ({ env, homedir }) => onPath('codex', env) || existsSync(join(homedir, '.codex')),
    plan({ entry, env }) {
      const argv = ['codex', 'mcp', 'add', SERVER, '--', entry.command, ...entry.args];
      if (!onPath('codex', env)) {
        return { kind: 'manual', text: `Add this to ~/.codex/config.toml:\n\n[mcp_servers.${SERVER}]\ncommand = ${quote(entry.command)}\nargs = [${entry.args.map(quote).join(', ')}]\n` };
      }
      return { kind: 'command', argv, undo: ['codex', 'mcp', 'remove', SERVER], exists: ['codex', 'mcp', 'get', SERVER] };
    },
    skillDir: ({ homedir }) => join(homedir, '.codex', 'skills', SERVER),
  },

  opencode: {
    label: 'OpenCode',
    scopes: ['user', 'project'],
    detect: ({ env, homedir }) => onPath('opencode', env) || existsSync(join(homedir, '.config', 'opencode')),
    plan: ({ scope, entry, cwd, homedir }) => ({
      kind: 'json',
      file: scope === 'project' ? join(cwd, 'opencode.json') : join(homedir, '.config', 'opencode', 'opencode.json'),
      keyPath: ['mcp', 'servers', SERVER], // OpenCode v2; v1 keeps servers directly under "mcp"
      value: { type: 'local', command: [entry.command, ...entry.args], enabled: true },
    }),
    skillDir: ({ scope, cwd, homedir }) => (scope === 'project' ? join(cwd, '.opencode', 'skills', SERVER) : join(homedir, '.config', 'opencode', 'skills', SERVER)),
  },

  hermes: {
    label: 'Hermes Agent',
    scopes: ['user'],
    detect: ({ homedir }) => existsSync(join(homedir, '.hermes')),
    // Its config is YAML, which this dependency-free launcher will not rewrite.
    plan: ({ entry }) => ({
      kind: 'manual',
      text: `Add this to ~/.hermes/config.yaml:\n\nmcp_servers:\n  ${SERVER}:\n    command: ${quote(entry.command)}\n    args: [${entry.args.map(quote).join(', ')}]\n`,
    }),
    skillDir: () => null,
  },
};

function desktopDir(platform) {
  return platform === 'darwin' ? ['Library', 'Application Support', 'Claude'] : ['.config', 'Claude'];
}
