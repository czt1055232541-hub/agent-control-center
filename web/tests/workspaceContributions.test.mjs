import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/plugins/workspaceContributions.ts', import.meta.url), 'utf8');
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } });
const { visibleDashboardPanels } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);
test('dashboard contributions disappear with their feature owners', () => {
  const items = ['config-health', 'watchdog', 'agent-diagnostics', 'infrastructure', 'unknown'].map(id => ({ id }));
  assert.deepEqual(visibleDashboardPanels(items, []), []);
  assert.deepEqual(visibleDashboardPanels(items, ['acc.dashboard']), [items[3]]);
  assert.deepEqual(visibleDashboardPanels(items, ['acc.config-center', 'acc.agent-array']), [items[0]]);
  assert.deepEqual(visibleDashboardPanels([{ id: 'agent-topology' }], ['acc.agent-array']), [{ id: 'agent-topology' }]);
});
