// Run against an installed package so DSH's real defineTool and dependencies
// are exercised. No model calls, user configuration writes, or service stops.
import assert from 'node:assert/strict'
import { createServer } from 'node:http'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
import { createRequire } from 'node:module'
import { readFileSync } from 'node:fs'

const installed = process.argv[2]
if (!installed) throw new Error('Usage: node verify-installed.mjs <installed-package-directory> [live-ACC-url]')
const installedRequire = createRequire(resolve(installed, 'index.js'))
// Profile installs deliberately obtain host peers through DSH's fallback.
// Check actual resolution, not just pnpm's profile-local dependency report.
for (const name of ['@deepseek-ai/cordis', '@deepseek-ai/dsh-tools', '@deepseek-ai/dsh-client-ui-renderer', '@deepseek-ai/dsh-client-ui-tool', 'react']) {
  const manifest = JSON.parse(readFileSync(installedRequire.resolve(`${name}/package.json`), 'utf8'))
  console.log(`RESOLVED: ${name}@${manifest.version}`)
}
const { apply } = await import(pathToFileURL(resolve(installed, 'index.js')).href)
let mode = 'online'
const server = createServer((req, res) => {
  assert.equal(req.url, '/api/plugins')
  if (mode === 'timeout') return
  if (mode === 'http-error') { res.writeHead(503); res.end(); return }
  res.setHeader('Content-Type', 'application/json')
  res.end(mode === 'invalid' ? '{invalid' : JSON.stringify(mode === 'shape'
    ? { plugins: null } : { plugins: [{ id: 'independent.example', name: 'Independent example' }] }))
})
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
const baseUrl = `http://127.0.0.1:${server.address().port}`
function register(url) {
  let tool
  apply({ tools: { register(value) { assert.equal(tool, undefined); tool = value } } }, { baseUrl: url, requestTimeoutMs: 250 })
  assert.equal(tool.name, 'acc_overview')
  assert.deepEqual(tool.output.schema.required, ['online', 'url', 'count', 'plugins'])
  return tool
}
const tool = register(baseUrl)
try {
  const online = await tool.execute({}, {})
  assert.equal(online.online, true)
  assert.equal(online.count, 1)
  assert.deepEqual(online.plugins, ['Independent example'])
  assert.deepEqual(JSON.parse(tool.output.render({}, online)[0].text), online)
  console.log('PASS: real DSH schema, online inventory, rendered result')
  for (mode of ['http-error', 'invalid', 'shape', 'timeout']) {
    const result = await tool.execute({}, {})
    assert.equal(result.online, false)
    assert.equal(result.count, 0)
    assert.ok(result.error)
    console.log(`PASS: ${mode} returns offline without throwing`)
  }
} finally {
  server.closeAllConnections()
  await new Promise(resolve => server.close(resolve))
}
assert.equal((await tool.execute({}, {})).online, false)
console.log('PASS: stopped mock ACC returns offline')
if (process.argv[3]) {
  const live = await register(process.argv[3]).execute({}, {})
  assert.equal(live.online, true)
  console.log(`PASS: live ACC inventory has ${live.count} entries`)
}

// Exercise real Cordis ownership, rather than a fake register callback.
const { Context } = await import(pathToFileURL(installedRequire.resolve('@deepseek-ai/cordis')).href)
const { ToolRuntime, defineTool } = await import(pathToFileURL(installedRequire.resolve('@deepseek-ai/dsh-tools')).href)
const { default: SystemPrompt } = await import(pathToFileURL(installedRequire.resolve('@deepseek-ai/dsh-system-prompt')).href)
const ctx = new Context()
const promptFiber = await ctx.plugin(SystemPrompt, {})
const toolsFiber = await ctx.plugin(ToolRuntime, { mode: 'native' })
const sentinel = defineTool({
  name: 'acc_audit_sentinel', description: 'Independent test-only host tool', parameters: {},
  output: { schema: { type: 'string' }, render: (_args, value) => [{ type: 'text', text: value }] },
  async execute() { return 'untouched' },
})
const removeSentinel = ctx.tools.register(sentinel)
try {
  const plugin = await import(pathToFileURL(resolve(installed, 'index.js')).href)
  for (let cycle = 0; cycle < 2; cycle++) {
    const fiber = await ctx.plugin(plugin, { baseUrl, requestTimeoutMs: 250 })
    assert.ok(ctx.tools.get('acc_overview'))
    assert.equal(await ctx.tools.get('acc_audit_sentinel').execute({}, {}), 'untouched')
    await fiber.dispose()
    assert.equal(ctx.tools.get('acc_overview'), undefined)
    assert.equal(await ctx.tools.get('acc_audit_sentinel').execute({}, {}), 'untouched')
  }
  console.log('PASS: real Cordis install/dispose/reinstall removes only ACC tool')
} finally {
  removeSentinel()
  await toolsFiber.dispose()
  await promptFiber.dispose()
}
