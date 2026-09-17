import { ConfigCenterPage } from "./index";
import type { AccClientPlugin } from "../../plugins/clientRegistry";

export default {
  id: "acc.config-center",
  pages: { config: ConfigCenterPage },
} satisfies AccClientPlugin;
