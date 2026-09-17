import { AgentPage } from "./AgentPage";
import type { AccClientPlugin } from "../../plugins/clientRegistry";

export default {
  id: "acc.agent-array",
  pages: { agents: AgentPage },
} satisfies AccClientPlugin;
