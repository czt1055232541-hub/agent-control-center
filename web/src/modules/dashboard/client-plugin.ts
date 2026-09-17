import { DashboardPage } from "./DashboardPage";
import type { AccClientPlugin } from "../../plugins/clientRegistry";
export default { id: "acc.dashboard", pages: { dashboard: DashboardPage } } satisfies AccClientPlugin;
