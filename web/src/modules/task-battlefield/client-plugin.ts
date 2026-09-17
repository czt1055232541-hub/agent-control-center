import TaskDashboardPage from "./TaskDashboardPage";
import type { AccClientPlugin } from "../../plugins/clientRegistry";

export default {
  id: "acc.task-battlefield",
  pages: { tasks: TaskDashboardPage },
} satisfies AccClientPlugin;
