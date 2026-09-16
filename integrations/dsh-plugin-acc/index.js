import Schema from '@deepseek-ai/schemastery'
import { defineTool } from '@deepseek-ai/dsh-tools'

export const name = 'acc-integration'
export const inject = ['tools']

export const Config = Schema.object({
  baseUrl: Schema.string().default('http://127.0.0.1:8765'),
  requestTimeoutMs: Schema.number().min(250).max(30000).default(5000),
})

function normalizedBaseUrl(value) {
  const url = new URL(value)
  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    throw new Error('ACC baseUrl must use http or https')
  }
  return url.toString().replace(/\/$/, '')
}

async function readInventory(baseUrl, timeoutMs) {
  const signal = AbortSignal.timeout(timeoutMs)
  const response = await fetch(`${baseUrl}/api/plugins`, { signal })
  if (!response.ok) throw new Error(`ACC returned HTTP ${response.status}`)
  const value = await response.json()
  if (typeof value !== 'object' || value === null || !Array.isArray(value.plugins)) {
    throw new Error('ACC returned an invalid plugin inventory')
  }
  return value
}

export function apply(ctx, config) {
  const baseUrl = normalizedBaseUrl(config.baseUrl)
  ctx.tools.register(defineTool({
    name: 'acc_overview',
    description: 'Inspect Agent Control Center and list its installed feature plugins.',
    parameters: {},
    output: {
      schema: {
        type: 'object',
        properties: {
          online: { type: 'boolean', required: true },
          url: { type: 'string', required: true },
          count: { type: 'integer', required: true },
          plugins: { type: 'array', items: { type: 'string' }, required: true },
          error: { type: 'string' },
        },
        additionalProperties: false,
      },
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value) }],
    },
    async execute() {
      try {
        const inventory = await readInventory(baseUrl, config.requestTimeoutMs)
        return {
          online: true,
          url: baseUrl,
          count: inventory.plugins.length,
          plugins: inventory.plugins.map(plugin => String(plugin.name ?? plugin.id)),
          error: '',
        }
      } catch (error) {
        return {
          online: false,
          url: baseUrl,
          count: 0,
          plugins: [],
          error: error instanceof Error ? error.message : String(error),
        }
      }
    },
  }))
}
