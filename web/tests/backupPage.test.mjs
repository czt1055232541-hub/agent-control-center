import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

const require = createRequire(import.meta.url);
const source = await readFile(new URL("../src/modules/backup-migration/BackupPage.tsx", import.meta.url), "utf8");
let { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.React },
});
outputText = outputText.replace('from "react"', `from ${JSON.stringify(pathToFileURL(require.resolve("react")).href)}`);
const fakeApi = "data:text/javascript," + encodeURIComponent("export async function readJson() { throw new Error('Rendering must not perform operations'); }");
outputText = outputText.replace('from "../../api"', `from ${JSON.stringify(fakeApi)}`);
const { BackupPage } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`);

test("backup cleanup requires explicit confirmation even with a control token", () => {
  const html = renderToStaticMarkup(React.createElement(BackupPage, { token: "test-only" }));
  assert.match(html, /<button[^>]*disabled=""[^>]*>清理旧备份<\/button>/);
  assert.match(html, /<button[^>]*disabled=""[^>]*>开始迁移<\/button>/);
  assert.match(html, /确认按保留策略删除过期备份/);
});
