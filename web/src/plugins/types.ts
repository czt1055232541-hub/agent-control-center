export type AccPluginCard = {
  id: string;
  title: string;
  description: string;
  page: string;
  icon: string;
  order: number;
};

export type AccPlugin = {
  id: string;
  name: string;
  version: string;
  description: string;
  kind: "framework" | "feature" | "integration";
  state: "native" | "transitional";
  requires: string[];
  capabilities: string[];
  cards: AccPluginCard[];
};

export type PluginInventory = {
  plugins: AccPlugin[];
  count: number;
};
