import { createClientRegistry, type AccClientPlugin } from "./clientRegistry";

const modules = import.meta.glob<{ default: AccClientPlugin }>(
  "../modules/*/client-plugin.ts", { eager: true },
);

export const clientRegistry = createClientRegistry(
  Object.keys(modules).sort().map((path) => modules[path].default),
);
