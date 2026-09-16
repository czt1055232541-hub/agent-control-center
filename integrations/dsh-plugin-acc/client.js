import React, { useMemo } from 'react'

export const inject = ['slots']

function resultText(block) {
  if (!('kind' in block)) return null
  return block.content.map(item => item.type === 'text' ? item.text : '').join('')
}

function parseOverview(block) {
  const text = resultText(block)
  if (text === null) return { running: true, online: false, url: '', count: 0, plugins: [], error: '' }
  try {
    const value = JSON.parse(text)
    return {
      running: false,
      online: value.online === true,
      url: typeof value.url === 'string' ? value.url : '',
      count: Number.isInteger(value.count) ? value.count : 0,
      plugins: Array.isArray(value.plugins) ? value.plugins.map(String) : [],
      error: typeof value.error === 'string' ? value.error : '',
    }
  } catch {
    return { running: false, online: false, url: '', count: 0, plugins: [], error: text }
  }
}

function AccOverviewCard({ block, inspect }) {
  const model = useMemo(() => parseOverview(block), [block])
  const accent = model.online ? 'var(--dsw-alias-success, #15803d)' : 'var(--dsw-alias-danger, #b91c1c)'
  const open = () => {
    if (model.online && model.url) window.open(model.url, '_blank', 'noopener,noreferrer')
  }
  return React.createElement('article', {
    'data-tool': 'acc_overview',
    style: {
      border: '1px solid var(--dsw-alias-border, #d8dee9)', borderRadius: 12,
      background: 'var(--dsw-alias-bg, #fff)', overflow: 'hidden', color: 'var(--dsw-alias-fg, #172033)',
    },
  },
  React.createElement('button', {
    type: 'button', onClick: open, disabled: !model.online,
    style: { width: '100%', border: 0, background: 'transparent', padding: 14, textAlign: 'left', cursor: model.online ? 'pointer' : 'default' },
  },
  React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 10 } },
    React.createElement('span', { style: { width: 10, height: 10, borderRadius: 999, background: accent, boxShadow: `0 0 0 4px color-mix(in srgb, ${accent} 16%, transparent)` } }),
    React.createElement('strong', { style: { fontSize: 14 } }, 'Agent Control Center'),
    React.createElement('span', { style: { marginLeft: 'auto', fontSize: 12, color: accent } }, model.running ? '连接中' : model.online ? '在线' : '离线'),
  ),
  React.createElement('p', { style: { margin: '9px 0 0', fontSize: 13, opacity: .72 } },
    model.running ? '正在读取 ACC 插件清单…' : model.online ? `${model.count} 个功能插件 · 点击打开 ACC` : model.error || 'ACC 当前不可用',
  ),
  model.plugins.length ? React.createElement('div', { style: { display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 10 } },
    ...model.plugins.slice(0, 6).map(name => React.createElement('span', { key: name, style: { padding: '3px 7px', borderRadius: 999, background: 'var(--dsw-alias-bg-subtle, #f1f5f9)', fontSize: 11 } }, name)),
  ) : null),
  inspect ? React.createElement('button', { type: 'button', onClick: inspect, style: { border: 0, borderTop: '1px solid var(--dsw-alias-border, #d8dee9)', width: '100%', padding: '8px 14px', background: 'transparent', textAlign: 'left', fontSize: 12, opacity: .65, cursor: 'pointer' } }, '查看调用详情') : null)
}

export function apply(ctx) {
  ctx.slots.inject('tool.call.toolview', () => ctx.slots.register(
    { name: 'tool.call.toolview', key: 'acc_overview' },
    AccOverviewCard,
  ))
}
