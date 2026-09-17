import { LocalToolsPage } from "./LocalToolsPage";
import type { AccClientPlugin } from "../../plugins/clientRegistry";

export default {
  id: "acc.local-tools",
  pages: { tools: LocalToolsPage },
} satisfies AccClientPlugin;
