import { FeishuConnectionPage } from "./index";
import type { AccClientPlugin } from "../../plugins/clientRegistry";

export default {
  id: "acc.feishu-connection",
  pages: { feishu: FeishuConnectionPage },
} satisfies AccClientPlugin;
