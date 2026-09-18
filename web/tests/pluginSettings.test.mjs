import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

const require = createRequire(import.meta.url);
async function component(path) {
  const source = await readFile(new URL(path, import.meta.url), "utf8");
  let { outputText } = ts.transpileModule(source, {compilerOptions: {
    module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX,
  }});
  for (const name of ["react", "react/jsx-runtime", "lucide-react"]) {
    outputText = outputText.replace(`from "${name}"`, `from ${JSON.stringify(pathToFileURL(require.resolve(name)).href)}`);
  }
  const fakeApi = "data:text/javascript," + encodeURIComponent("export async function readJson() { throw new Error('SSR must not call APIs'); }");
  outputText = outputText.replace('from "../api"', `from ${JSON.stringify(fakeApi)}`);
  return import(`data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`);
}
const { PluginSettingsForm } = await component("../src/app/PluginSettingsPage.tsx");
const { Sidebar } = await component("../src/app/Sidebar.tsx");
const settings = {
  disabled: ["feature"], environment_override: false, restart_required: true,
  plugins: [
    {id:"framework", name:"框架", description:"", kind:"framework", requires:[], configured_enabled:true, next_start_enabled:true, running_enabled:true},
    {id:"feature", name:"测试功能", description:"", kind:"feature", requires:["framework"], configured_enabled:false, next_start_enabled:false, running_enabled:true},
  ],
};
function render(overrides={}) {
  return renderToStaticMarkup(React.createElement(PluginSettingsForm, {
    settings, disabled:["feature"], onToggle(){}, onSave(){}, busy:false, canSave:true, ...overrides,
  }));
}
test("framework is locked and restart boundary is visible", () => {
  const html=render();
  assert.match(html, /type="checkbox"[^>]*disabled=""[^>]*checked=""/);
  assert.match(html, /等待重启 ACC/);
  assert.match(html, /当前运行：已启用/);
  assert.match(html, /下次启动：停用/);
});
test("missing token and environment override prevent save", () => {
  assert.match(render({canSave:false}), /<button[^>]*disabled=""[^>]*>保存插件设置/);
  const html=render({settings:{...settings,environment_override:true}});
  assert.equal((html.match(/type="checkbox"[^>]*disabled=""/g)||[]).length,2);
  assert.match(html, /<button[^>]*disabled=""[^>]*>保存插件设置/);
});
test("settings navigation survives an empty feature inventory", () => {
  const html=renderToStaticMarkup(React.createElement(Sidebar, {activePage:"__settings__",onNavigate(){},plugins:[]}));
  assert.match(html, /设置 · 功能插件/);
  assert.match(html, /aria-current="page"/);
  assert.match(html, /不是第二套插件目录/);
});
