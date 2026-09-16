import React from "react";

import { readJson } from "../api";
import type { AccPlugin, PluginInventory } from "../plugins/types";

export function usePluginInventory() {
  const [plugins, setPlugins] = React.useState<AccPlugin[]>([]);
  const [error, setError] = React.useState<string | null>(null);

  const refreshPlugins = React.useCallback(async () => {
    try {
      const inventory = await readJson<PluginInventory>("/api/plugins");
      setPlugins(inventory.plugins);
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  }, []);

  React.useEffect(() => {
    refreshPlugins().catch(() => {});
  }, [refreshPlugins]);

  return { plugins, pluginsError: error, refreshPlugins };
}
