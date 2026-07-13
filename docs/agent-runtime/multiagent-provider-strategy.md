# Multiagent Provider Strategy

This note records the operating differences observed between Codex Agent in MoonBridge mode and native mode.

## Current Finding

- MoonBridge mode tolerates `model_reasoning_effort = "max"` because MoonBridge maps that value to its own provider effort setting.
- Native `gpt-5.5` rejects `model_reasoning_effort = "max"` with `reasoning.effort invalid_value`.
- Native mode works after switching `model_reasoning_effort` to `high`.
- Native mode can be slower for code-generation tasks, so group polling should wait 2-5 minutes before treating codeX agent as stuck.
- Coordinator context can become too large and fail auto-compaction. When this happens, codeX agent may complete but the coordinator may stop advancing the handoff chain.

## Control Center Rules

- `switch-provider native` must write:
  - `model = "<codexNativeModel>"`
  - `model_reasoning_effort = "<codexNativeReasoningEffort>"`
  - no MoonBridge provider keys
- `switch-provider moonbridge` may keep MoonBridge-specific model/provider fields.
- `codexNativeReasoningEffort` defaults to `high`.
- A native-mode workflow should use smaller, single-purpose tasks and avoid mixing unrelated asks in one bot mention.

## Group Workflow Recovery

When native codeX agent completes but the coordinator does not continue:

1. Check the group for `Context is too large and auto-compaction could not recover this turn`.
2. Confirm the artifact exists locally.
3. Nudge the coordinator once with the task id and the next expected handoff.
4. If still silent, treat it as a cloud coordinator context/runtime issue, not a codeX agent failure.
5. Continue in the same group session unless the user explicitly allows a new session or context reset.

## Agent Reply Rules

- codeX agent should report only: path, changes, run method, self-test result, and the next coordinator handoff.
- codeX agent should not tell the user to run `lark-cli auth login` for group reporting.
- codeX agent should write `@项目调度官` when handing back; the sender layer converts it into Feishu post rich-text mention.
- Do not output literal `<at user_id="...">...</at>` as the handoff format.
