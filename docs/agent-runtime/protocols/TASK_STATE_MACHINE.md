# Task State Machine

## States

`RECEIVED -> ACKNOWLEDGED -> IN_PROGRESS -> SELF_TESTED -> HANDOFF -> OPS_VALIDATED -> AUDITED -> ARCHIVED -> FINAL_SUMMARY`

## State Meanings

- `RECEIVED`: coordinator or downstream agent has received a task mention.
- `ACKNOWLEDGED`: assignee confirms scope, path, artifacts, and complexity.
- `IN_PROGRESS`: assignee is modifying files or running assigned local checks.
- `SELF_TESTED`: assignee completed role-appropriate self-tests.
- `HANDOFF`: assignee reports artifacts and evidence back to 项目调度官.
- `OPS_VALIDATED`: 运维验证官 completed runtime/environment validation.
- `AUDITED`: 质量审计官 completed quality audit with pass/fail conclusion.
- `ARCHIVED`: 项目档案官 recorded final artifacts after coordinator request.
- `FINAL_SUMMARY`: 项目调度官 posts the final group summary.

## Transition Rules

- Only 项目调度官 assigns the next downstream agent.
- Downstream agents report back to 项目调度官, not directly to the user.
- Failed ops validation or audit returns to 项目调度官 for rework scheduling.
- Same-session recovery resumes from the last state with local evidence.
