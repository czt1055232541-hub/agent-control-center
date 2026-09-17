import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import ts from "typescript";

const source = await readFile(new URL("../src/plugins/clientRegistry.ts", import.meta.url), "utf8");
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
});
const { createClientRegistry } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`);

const Page = () => null;
const contribution = { id: "example", pages: { example: Page } };

test("renders only the page advertised by its enabled owner", () => {
  const registry = createClientRegistry([contribution]);
  assert.equal(registry.resolve("example", [{ id: "example", cards: [{ page: "example" }] }]), Page);
  assert.equal(registry.resolve("example", []), null);
  assert.equal(registry.resolve("example", [{ id: "other", cards: [{ page: "example" }] }]), null);
  assert.equal(registry.resolve("example", [{ id: "example", cards: [] }]), null);
  assert.equal(registry.resolve("unknown", [{ id: "example", cards: [{ page: "unknown" }] }]), null);
});

test("rejects ambiguous plugin and page ownership", () => {
  assert.throws(() => createClientRegistry([contribution, contribution]), /Duplicate client plugin/);
  assert.throws(() => createClientRegistry([contribution, { id: "other", pages: { example: Page } }]), /Duplicate client page/);
});
