// Start the Python program through uv and get out of its way.
import { spawn } from 'node:child_process';
import { constants } from 'node:os';

export function uvArgs(spec, args) {
  return ['tool', 'run', '--from', spec, 'ankiplusmcp', ...args];
}

/**
 * Run uv to completion. stdio is inherited by default so the MCP protocol on
 * stdin/stdout passes through untouched; the launcher itself prints nothing there.
 * @returns {Promise<{code: number, stdout: string}>} stdout is filled only when captured.
 */
export function run(uv, args, { captureStdout = false } = {}) {
  return new Promise((resolve) => {
    const child = spawn(uv, args, { stdio: ['inherit', captureStdout ? 'pipe' : 'inherit', 'inherit'] });
    let stdout = '';
    if (captureStdout) child.stdout.on('data', (chunk) => { stdout += chunk; });
    const forward = (signal) => () => { try { child.kill(signal); } catch { /* already gone */ } };
    const handlers = { SIGINT: forward('SIGINT'), SIGTERM: forward('SIGTERM') };
    for (const [signal, handler] of Object.entries(handlers)) process.on(signal, handler);
    const finish = (code) => {
      for (const [signal, handler] of Object.entries(handlers)) process.off(signal, handler);
      resolve({ code, stdout });
    };
    child.on('error', (error) => {
      process.stderr.write(`ankiplusmcp: could not start uv: ${error.message}\n`);
      finish(127);
    });
    child.on('close', (code, signal) => finish(signal ? 128 + (constants.signals[signal] ?? 0) : code ?? 1));
  });
}
