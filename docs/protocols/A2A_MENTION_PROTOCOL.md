# A2A Mention Protocol

## Purpose

Ensure Feishu group mentions reliably wake the intended agent while keeping raw identifiers out of shared files.

## Rules

- Agent replies may write `@项目调度官` or another approved role name in plain text only because the outer sender converts it to Feishu post rich text.
- The delivered Feishu message must be `msg_type=post` and contain an `at` element for the target role.
- Do not output literal XML-like strings such as `<at user_id="...">名称</at>` as the handoff format.
- Mention at most one agent in a handoff reply.
- Treat real `open_id`, `chat_id`, `app_id`, secrets, and tokens as local-only configuration.

## Group Mention ID Validation

Validation checks should compare role names against local A2A mapping keys and report only:

- missing role mapping;
- duplicate role mapping;
- wrong target role;
- plain-text mention without rich-text conversion;
- callback/card body that did not trigger the coordinator.

Never paste the raw ID values into docs, commits, or group summaries.
