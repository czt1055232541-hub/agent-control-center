import { BackupPage } from "./BackupPage";
import type { AccClientPlugin } from "../../plugins/clientRegistry";

export default {
  id: "acc.backup-migration",
  pages: { backup: BackupPage },
} satisfies AccClientPlugin;
