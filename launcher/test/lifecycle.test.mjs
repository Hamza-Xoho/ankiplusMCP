import { test } from 'node:test';
import assert from 'node:assert/strict';
import { chmodSync, copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fakeUv, repoRoot, runCli, tempDir } from './helpers.mjs';
import { HOSTS } from '../lib/hosts.mjs';
import { npxRef } from '../lib/spec.mjs';

function desktop() {
  const home=tempDir(); const cwd=tempDir();
  const file=HOSTS['claude-desktop'].plan({homedir:home,platform:process.platform,env:{},entry:{}}).file;
  mkdirSync(join(file,'..'),{recursive:true});
  writeFileSync(file,JSON.stringify({mcpServers:{anki:{command:'keep',args:[]}},theme:'dark'}));
  return {home,cwd,file};
}
const read=file=>JSON.parse(readFileSync(file,'utf8'));
const init=(p,env={},extra=[])=>runCli(['init','--host','claude-desktop','--yes','--no-warmup',...extra],env,p);
const uninstall=(p,extra=[])=>runCli(['uninstall','--host','claude-desktop','--yes','--json',...extra],{},p);

// A registered process must work without the installer's shell environment.
test('Desktop persists only the Python override and discovered uv for a fresh host process',()=>{
  const p=desktop();const bin=join(p.cwd,'custom bin');mkdirSync(bin);
  const uv=join(bin,'uv');copyFileSync(fakeUv,uv);chmodSync(uv,0o755);
  const spec=join(p.cwd,'local wheel.whl');writeFileSync(spec,'fixture');
  const r=init(p,{ANKIPLUSMCP_UV:undefined,PATH:bin,ANKIPLUSMCP_PY_SPEC:spec,UNRELATED_SECRET:'do not copy'});
  assert.equal(r.status,0,r.stderr);
  const entry=read(p.file).mcpServers.ankiplusmcp;
  assert.deepEqual(entry.env,{ANKIPLUSMCP_PY_SPEC:spec,ANKIPLUSMCP_UV:uv});
  const log=join(p.cwd,'fresh-host.log');
  const child=spawnSync(process.execPath,[join(repoRoot,'launcher/cli.mjs'),'doctor','--json'],{
    env:{PATH:'/nonexistent',FAKE_UV_LOG:log,FAKE_UV_STDOUT:'{"checks":[]}',...entry.env},encoding:'utf8'});
  assert.equal(child.status,0,child.stderr);
  assert.ok(readFileSync(log,'utf8').includes(spec));
  assert.deepEqual(read(p.file).mcpServers.anki,{command:'keep',args:[]});
  assert.equal(uninstall(p).status,0);
  assert.deepEqual(read(p.file),{mcpServers:{anki:{command:'keep',args:[]}},theme:'dark'});
});

test('Desktop registration keeps explicit uv even outside standard locations',()=>{
  const p=desktop();const r=init(p,{ANKIPLUSMCP_UV:fakeUv,ANKIPLUSMCP_PY_SPEC:'local-spec'});
  assert.equal(r.status,0,r.stderr);
  assert.equal(read(p.file).mcpServers.ankiplusmcp.env.ANKIPLUSMCP_UV,fakeUv);
});

test('local launcher tarball references become absolute file: package specs',()=>{
  const cwd=tempDir();const file=join(cwd,'Install — اختبار','launcher.tgz');mkdirSync(join(file,'..'),{recursive:true});writeFileSync(file,'fixture');
  for(const ref of [file,'./Install — اختبار/launcher.tgz','file:./Install — اختبار/launcher.tgz']) {
    assert.equal(npxRef({ANKIPLUSMCP_NPX_REF:ref},cwd),'file:'+file);
  }
  assert.equal(npxRef({ANKIPLUSMCP_NPX_REF:'github:owner/repo#branch'},cwd),'github:owner/repo#branch');
});

test('uninstall reports modified config as incomplete and retains its record for retry',()=>{
  const p=desktop();assert.equal(init(p).status,0);
  const installed=read(p.file);const changed=structuredClone(installed);
  changed.mcpServers.ankiplusmcp.env={...changed.mcpServers.ankiplusmcp.env,EXTRA:'manual'};
  writeFileSync(p.file,JSON.stringify(changed));
  const first=uninstall(p);
  assert.equal(first.status,3,first.stdout);
  assert.match(JSON.parse(first.stdout).changes[0].status,/kept/);
  assert.deepEqual(read(p.file),changed);
  // Restoring the recorded entry permits a second uninstall; the manifest must survive.
  writeFileSync(p.file,JSON.stringify(installed));
  const retry=uninstall(p);assert.equal(retry.status,0,retry.stderr);
  assert.equal(read(p.file).mcpServers.ankiplusmcp,undefined);
  assert.deepEqual(read(p.file).mcpServers.anki,installed.mcpServers.anki);
});

test('uninstall preserves unreadable config and its retry record',()=>{
  const p=desktop();assert.equal(init(p).status,0);const installed=readFileSync(p.file,'utf8');
  writeFileSync(p.file,'{broken');
  assert.equal(uninstall(p).status,3);assert.equal(readFileSync(p.file,'utf8'),'{broken');
  writeFileSync(p.file,installed);assert.equal(uninstall(p).status,0);
  assert.equal(read(p.file).mcpServers.ankiplusmcp,undefined);
});

test('uninstall recognizes an already removed server without changing unrelated settings',()=>{
  const p=desktop();assert.equal(init(p).status,0);const state=read(p.file);delete state.mcpServers.ankiplusmcp;
  writeFileSync(p.file,JSON.stringify(state));
  const result=uninstall(p);assert.equal(result.status,0,result.stdout);
  assert.equal(JSON.parse(result.stdout).changes[0].status,'gone');assert.deepEqual(read(p.file),state);
});

for(const host of ['claude-code','codex','opencode','hermes']) {
  test(`${host} registration retains runtime dependencies in its native format`,()=>{
    const env={ANKIPLUSMCP_PY_SPEC:'local wheel',ANKIPLUSMCP_UV:'/custom/uv'};
    const change=HOSTS[host].plan({scope:'user',entry:{command:'npx',args:['-y','file:/test.tgz','serve'],env},homedir:tempDir(),cwd:tempDir(),platform:process.platform,env:{PATH:''}});
    if(host==='opencode') assert.deepEqual(change.value.environment,env);
    else if(host==='hermes') assert.match(change.text,/env:\n\s+ANKIPLUSMCP_PY_SPEC: "local wheel"/);
    else if(host==='codex') assert.match(change.text,/\[mcp_servers.ankiplusmcp.env\]/);
    else {
      assert.ok(change.text.includes('--env'));
      assert.ok(change.text.includes('ANKIPLUSMCP_UV=/custom/uv'));
    }
  });
}

test('re-init adopts runtime overrides only into an already tracked unchanged entry',()=>{
  const p=desktop();assert.equal(init(p).status,0);
  // Emulate an older installation receipt, followed by the documented manual workaround.
  const manifest=process.platform==='darwin'
    ? join(p.home,'Library','Application Support','ankiplusmcp','install-manifest.json')
    : join(p.home,'.local','share','ankiplusmcp','install-manifest.json');
  const receipt=read(manifest);delete receipt.installs[0].changes[0].value.env;
  writeFileSync(manifest,JSON.stringify(receipt));
  assert.equal(init(p).status,0);
  assert.equal(uninstall(p).status,0);
  assert.equal(read(p.file).mcpServers.ankiplusmcp,undefined);
});

test('remote tarball URLs and Git references are not rewritten into local paths',()=>{
  for(const ref of ['https://example.test/package.tgz','github:owner/repo#release.tgz']) {
    assert.equal(npxRef({ANKIPLUSMCP_NPX_REF:ref},'/tmp'),ref);
  }
});

test('a packed local launcher runs through npx using its normalized file: reference',()=>{
  const p=desktop();const output=join(p.cwd,'Install — اختبار');mkdirSync(output);
  const pack=spawnSync('npm',['pack','--offline','--ignore-scripts','--pack-destination',output],{cwd:repoRoot,encoding:'utf8'});
  assert.equal(pack.status,0,pack.stderr);
  const tarball=join(output,pack.stdout.trim().split('\n').at(-1));
  const reference=npxRef({ANKIPLUSMCP_NPX_REF:tarball},p.cwd);
  const result=spawnSync('npx',['--offline','--yes','--cache',join(p.cwd,'npm-cache'),reference,'init','--print'],{
    cwd:p.cwd,encoding:'utf8',env:{PATH:process.env.PATH,HOME:p.home,ANKIPLUSMCP_NPX_REF:tarball,ANKIPLUSMCP_PY_SPEC:'test-local-wheel',ANKIPLUSMCP_UV:fakeUv}});
  assert.equal(result.status,0,result.stderr);
  const entry=JSON.parse(result.stdout).mcpServers.ankiplusmcp;
  assert.equal(entry.args[1],reference);
  assert.equal(entry.env.ANKIPLUSMCP_PY_SPEC,'test-local-wheel');
  assert.equal(entry.env.ANKIPLUSMCP_UV,fakeUv);
});
