import { DiagnosticsPage } from "./DiagnosticsPage";
import type { AccClientPlugin } from "../../plugins/clientRegistry";
export default { id: "acc.logs-diagnostics", pages: { diagnostics: DiagnosticsPage } } satisfies AccClientPlugin;
