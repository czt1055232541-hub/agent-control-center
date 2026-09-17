import { RoutingRulesPage } from "./index";
import type { AccClientPlugin } from "../../plugins/clientRegistry";

export default {
  id: "acc.routing-rules",
  pages: { routing: RoutingRulesPage },
} satisfies AccClientPlugin;
