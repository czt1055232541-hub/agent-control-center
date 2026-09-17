import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { runInNewContext } from 'node:vm';
import test from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const source = await readFile(new URL('../../integrations/dsh-plugin-acc/client.js', import.meta.url), 'utf8');
let registration;
runInNewContext(source, { URL, window: { __ModuleLoader__: { load(value) { registration = value; } } } });
assert.equal(registration.id, 'dsh-plugin-acc');
const { apply } = registration.factory(name => {
  assert.equal(name, 'react');
  return React;
});
let Card;
apply({ slots: {
  inject(name, register) { assert.equal(name, 'tool.call.toolview'); register(); },
  register(options, component) { assert.equal(options.key, 'acc_overview'); Card = component; },
} });
const render = block => renderToStaticMarkup(React.createElement(Card, { block }));
const result = value => ({ kind: 'tool', content: [{ type: 'text', text: JSON.stringify(value) }] });

test('DSH card renders online, offline and pending results', () => {
  const online = render(result({ online: true, url: 'http://127.0.0.1:8765', count: 1, plugins: ['Example'] }));
  assert.match(online, /点击打开 ACC/);
  assert.match(online, /Example/);
  assert.doesNotMatch(online, /disabled=""/);
  assert.match(render(result({ online: false, error: 'Unavailable' })), /disabled=""/);
  assert.match(render({ name: 'acc_overview' }), /连接中/);
});

test('DSH card survives malformed result content', () => {
  for (const block of [null, {}, { kind: 'tool' }, { kind: 'tool', content: [null, { type: 'text', text: 42 }] }, result(null)]) {
    assert.doesNotThrow(() => render(block));
  }
});

test('DSH card never enables unsafe or credential-bearing destinations', () => {
  for (const url of ['javascript:alert(1)', 'data:text/html,test', 'file:///C:/', '//example.org', 'https://user:password@example.org', '']) {
    assert.match(render(result({ online: true, url })), /disabled=""/);
  }
});
