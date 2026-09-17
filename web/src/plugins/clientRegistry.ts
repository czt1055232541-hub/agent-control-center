import type { ComponentType } from "react";
import type { AccPlugin } from "./types";

export type ClientPageProps = { token: string };
export type AccClientPlugin = {
  id: string;
  pages: Record<string, ComponentType<ClientPageProps>>;
};

export function createClientRegistry(contributions: AccClientPlugin[]) {
  const owners = new Set<string>();
  const pages = new Map<string, { owner: string; component: ComponentType<ClientPageProps> }>();
  for (const contribution of contributions) {
    if (owners.has(contribution.id)) throw new Error(`Duplicate client plugin: ${contribution.id}`);
    owners.add(contribution.id);
    for (const [page, component] of Object.entries(contribution.pages)) {
      if (pages.has(page)) throw new Error(`Duplicate client page: ${page}`);
      pages.set(page, { owner: contribution.id, component });
    }
  }
  return {
    resolve(page: string, enabledPlugins: AccPlugin[]) {
      const entry = pages.get(page);
      if (!entry) return null;
      const owner = enabledPlugins.find((plugin) => plugin.id === entry.owner);
      return owner?.cards.some((card) => card.page === page) ? entry.component : null;
    },
  };
}
