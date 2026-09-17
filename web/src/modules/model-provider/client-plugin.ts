import { ProviderPage } from "./ProviderPage";
import type { AccClientPlugin } from "../../plugins/clientRegistry";
export default { id: "acc.model-provider", pages: { provider: ProviderPage } } satisfies AccClientPlugin;
