// Run against an installed package so DSH's real defineTool and dependencies
// are exercised. No model calls, user configuration writes, or service stops.
import assert from 'node:assert/strict'
import { createServer } from 'node:http'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

const installed = process.argv[2]
if (!installed) throw new Error('Usage: node verify-installed.mjs <installed-package-directory> [live-ACC-url]')
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
