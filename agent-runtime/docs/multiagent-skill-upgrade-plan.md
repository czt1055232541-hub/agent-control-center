# Multiagent Skill Upgrade Plan

## Purpose

This plan records reusable lessons from the Feishu/OpenClaw/Codex multiagent setup so future upgrades do not depend on chat history.

Target outcome:

- Codex has reusable skills for local diagnosis, Python-first operations, and privacy-safe Git closeout.
- OpenClaw agents share explicit collaboration protocols instead of relying on loose prompt context.
- The five-agent Feishu workflow can complete task dispatch, development, ops validation, quality audit, archive, and final summary in one group session.

## Current System

The working team contains five local agents:

| Agent | Runtime | Responsibility |
|---|---|---|
| 项目调度官 | OpenClaw | Task intake, decomposition, handoff, progress state, final summary |
| 代码执行官 | Codex Agent | Local code implementation, fixes, and self-test |
| 运维验证官 | OpenClaw | Runtime, environment, reproducibility, and deployment validation |
| 质量审计官 | OpenClaw main agent | Requirement coverage, defect/risk review, rework decision |
| 项目档案官 | OpenClaw | Delivery record, artifact summary, archive metadata |

Do not store real Feishu `open_id`, `chat_id`, `app_id`, app secrets, tokens, or group transcripts in committed docs. Read them from local ignored config.

## Design Principles

- Prefer protocol over memory. Shared rules should live in files that every agent can load.
- Prefer same-session recovery. Continue the same group conversation and TASK-ID unless the user explicitly allows a new session or reset.
- Prefer Python-first operations. Use Python CLIs and `subprocess([...])` argv arrays before shell strings.
- Prefer evidence over assumption. Check logs, message positions, PID/port state, status commands, and actual group replies.
- Keep local artifacts separate. Runtime replies, generated demos, logs, summaries, and backup configs must stay out of Git.
- Use role boundaries. Agents should not perform another agent's job merely because they can.

## Upgrade Tracks

### Track A: Codex Skills

#### A1. Update `ai-project-delivery-workflow-version1.5`

Path:

```text
E:\codeX\skills\ai-project-delivery-workflow-version1.5\SKILL.md
```

Add reusable patterns:

- **Python-First Windows Operations**
  - Prefer Python wrapper scripts for operational commands.
  - Use `subprocess.run([...])` with argv arrays to avoid shell quoting issues.
  - Treat shell launchers as last-resort wrappers for Windows-native entrypoints.

- **Privacy-Preserving Git Closeout**
  - Scan staged diffs and tracked files before commit.
  - Exclude runtime logs, generated replies, group transcripts, local config, backup config, tokens, app secrets, `open_id`, and `chat_id`.
  - If sensitive material enters local commits before push, use a local history rewrite such as `git reset --soft <safe-base>` and recommit a clean snapshot.
  - Delete sensitive remote temporary branches after pushing a clean main branch.

- **Same-Session Recovery**
  - For multiagent workflows, continue with the same TASK-ID and group session first.
  - Use a minimal nudge to the coordinator with current state and next expected handoff.
  - Do not create a new session unless explicitly allowed.

#### A2. Create `feishu-openclaw-multiagent-ops`

Recommended path:

```text
E:\codeX\skills\feishu-openclaw-multiagent-ops\SKILL.md
```

Trigger scope:

- checking or repairing Feishu/OpenClaw/Codex multiagent configuration;
- verifying five-agent group collaboration;
- diagnosing A2A mention failures, stale names, wrong IDs, or stuck handoff chains;
- inspecting OpenClaw gateway, codex-agent, Agent Control Center, and Feishu bot state.

Core content:

- configuration inventory checklist;
- status and log inspection workflow;
- Feishu group bot ID verification;
- same-session nudge workflow;
- A2A mention troubleshooting;
- privacy-safe commit checklist.

Recommended bundled scripts:

```text
scripts/check_multiagent_config.py
scripts/scan_sensitive_git_state.py
scripts/send_group_nudge.py
```

These scripts should read local ignored config and should not hardcode real IDs.

#### A3. Maintain `agents/feishu-codex-agent/SKILL.md`

Path:

```text
F:\1AI\feishu_agent\agents\feishu-codex-agent\SKILL.md
```

Keep these rules explicit:

- The code executor only implements, fixes, and self-tests local code.
- It does not create Feishu Apps, Miaoda/Spark Apps, task lists, or cloud resources unless the user explicitly requests that specific action.
- It reports only artifact path, changes, run method, self-test result, and next handoff suggestion.
- It should not tell the user to run `lark-cli auth login` for group reporting unless the task truly requires user-authenticated Feishu API calls.
- Slow native responses are expected; observe 2-5 minutes before marking stuck.

### Track B: OpenClaw Shared Protocols

Create shared protocol files in the OpenClaw workspace or the repo that mirrors OpenClaw agent prompts.

Recommended logical files:

```text
TEAM_PROTOCOL.md
A2A_MENTION_PROTOCOL.md
TASK_STATE_MACHINE.md
ROLE_BOUNDARIES.md
GIT_PRIVACY_POLICY.md
```

If stored under OpenClaw, place them in a shared workspace folder and reference them from each agent's identity/skill files. If stored in this repo, keep them under:

```text
F:\1AI\feishu_agent\docs\protocols\
```

#### B1. `A2A_MENTION_PROTOCOL.md`

Required rules:

- Bot-to-bot handoff in Feishu group must be `msg_type=post`.
- Mention must use rich text `tag: "at"` with target `user_id` and `user_name`.
- Plain text `@名字` is not enough unless a sender layer reliably converts it into rich text.
- Literal `<at user_id="...">名字</at>` is display text and must not be treated as a guaranteed bot trigger.
- Use group mention IDs verified from `chat.members.bots` for Feishu group mentions.
- Do not assume `bot/v3/info` IDs are interchangeable with group mention IDs.
- If a sent message has empty `mentions`, treat that handoff as failed and retry with a real post mention.

#### B2. `TASK_STATE_MACHINE.md`

Required coordinator state flow:

```text
RECEIVED_USER_TASK
ASSIGNED_TO_CODE_EXECUTOR
CODE_DONE
ASSIGNED_TO_OPS
OPS_DONE
ASSIGNED_TO_AUDIT
AUDIT_DONE
ASSIGNED_TO_ARCHIVE
ARCHIVE_DONE
FINAL_SUMMARY
```

Coordinator rules:

- Include TASK-ID in every handoff.
- Assign exactly one downstream agent at a time.
- Move only to the next legal state.
- Do not wait for "老板继续" unless the user explicitly pauses.
- If a downstream reply clearly indicates completion but lacks a valid mention, continue the workflow and record the mention-format defect.
- Never implement, validate, audit, or archive work directly.

#### B3. `ROLE_BOUNDARIES.md`

Role boundaries:

- 项目调度官: coordinate only.
- 代码执行官: implement and self-test local code only.
- 运维验证官: verify run method and runtime only.
- 质量审计官: audit and request rework/pass only.
- 项目档案官: record and archive only.

Each agent should hand results back to 项目调度官 unless a protocol explicitly says otherwise.

### Track C: OpenClaw Agent Prompt Upgrades

#### C1. 项目调度官

Add:

- TASK-ID state machine.
- one-agent-at-a-time dispatch.
- final summary after archive completion.
- same-session recovery behavior.
- mention failure detection.

Expected final summary fields:

- TASK-ID;
- artifact path;
- code execution result;
- ops validation result;
- quality audit result;
- archive result;
- workflow defects and fixes;
- final status.

#### C2. 运维验证官

Add fixed validation report format:

- validation object;
- environment;
- run command;
- verification steps;
- pass/fail items;
- risks;
- conclusion;
- handoff back to 项目调度官.

It must not audit quality or archive.

#### C3. 质量审计官

Add fixed audit checklist:

- requirement coverage;
- UI and interaction usability;
- invalid input and boundary behavior;
- runtime instructions;
- safety/security risks;
- rework decision.

Allowed conclusions:

- `通过，可归档`
- `不通过，需返工`

It must send rework decisions to 项目调度官, not directly bypass the coordinator.

#### C4. 项目档案官

Add fixed archive report format:

- TASK-ID;
- project name;
- artifact path;
- code execution conclusion;
- ops validation conclusion;
- quality audit conclusion;
- archive files or metadata;
- final status.

It must report back to 项目调度官 with a real Feishu post mention.

#### C5. 质量审计官 as OpenClaw Main Agent

Keep main/default OpenClaw binding explicit. Previous discovery failed when the Feishu bot chat plugin did not include the root/default Feishu channel as a valid account. Future checks must confirm:

- main/default account is discovered;
- `质量审计官` receives Feishu group messages;
- gateway logs show all expected OpenClaw agents active.

### Track D: Runtime And Tooling

#### D1. Python status replacement

Replace remaining shell-first status scripts with Python wrappers.

Preferred command surface:

```text
python scripts/stack.py status --json
python scripts/stack.py restart openclaw
python scripts/stack.py restart codex-agent
python scripts/lark_multiagent_probe.py recent-summary
```

Compatibility wrappers should call Python directly and must not carry runtime logic.

#### D2. Multiagent config checker

Implement a Python checker that verifies:

- OpenClaw gateway is live;
- codex-agent is running;
- Codex provider mode is expected;
- OpenClaw agent names match local A2A names;
- Feishu A2A bot names are canonical;
- old names are absent from current behavior-affecting prompt files;
- generated/runtime artifacts are ignored by Git;
- no real Feishu IDs are committed to tracked docs except approved placeholders or tests.

#### D3. Group workflow probe

Maintain a Python probe that can:

- send a test task to 项目调度官;
- poll slowly, with configurable interval;
- summarize message positions, senders, mentions, and content preview;
- detect missing rich-text mention;
- continue with same TASK-ID and same group session.

## Implementation Phases

### Phase 1: Planning Artifacts

- Save this plan.
- Create `docs/protocols/` drafts for shared protocols.
- Decide whether OpenClaw agents should read protocols from this repo or from OpenClaw workspaces.

Exit criteria:

- planning files exist;
- no secrets or real Feishu IDs are committed.

### Phase 2: Codex Skill Updates

- Patch `ai-project-delivery-workflow-version1.5`.
- Create `feishu-openclaw-multiagent-ops`.
- Update `agents/feishu-codex-agent/SKILL.md` if needed.

Validation:

- skill frontmatter valid;
- skill body concise;
- no real IDs or secrets;
- run any available skill validation scripts.

### Phase 3: Shared Protocol Drafts

- Add `A2A_MENTION_PROTOCOL.md`.
- Add `TASK_STATE_MACHINE.md`.
- Add `ROLE_BOUNDARIES.md`.
- Add `GIT_PRIVACY_POLICY.md`.

Validation:

- each protocol has a clear owner and trigger;
- every OpenClaw agent can reference the same rules;
- no duplicated real IDs.

### Phase 4: OpenClaw Prompt Migration

- Update 项目调度官 prompt/workspace files.
- Update 运维验证官 prompt/workspace files.
- Update 质量审计官 prompt/workspace files.
- Update 项目档案官 prompt/workspace files.
- Restart only required OpenClaw services.

Validation:

- gateway discovers all OpenClaw agents;
- group messages dispatch to expected `agent:*:feishu:group:*` sessions;
- no old names appear in active prompts.

### Phase 5: End-To-End Workflow Test

Run one small task in the existing group:

- user task to 项目调度官;
- code execution;
- ops validation;
- quality audit;
- archive;
- final summary.

Validation:

- at least three valid bot-to-bot post mentions;
- no invalid handoff blocks workflow;
- one audit pass or rework decision is handled;
- final summary includes all required fields.

### Phase 6: Git Closeout

- Run tests.
- Run privacy scan.
- Commit only source, protocol, skill, and docs.
- Exclude runtime artifacts and local config.
- Push only clean main branch.
- Delete temporary branches that contain sensitive intermediate history.

## Non-Goals

- Do not hardcode production Feishu IDs into committed docs.
- Do not require a new conversation/session to recover ordinary workflow stalls.
- Do not make code executor responsible for ops, audit, archive, or Feishu app creation.
- Do not keep cloud-agent assumptions now that the five agents are local.
- Do not migrate every legacy wrapper at once; prioritize operational paths used by agents.

## Open Questions

- Should shared protocols live primarily in `F:\1AI\feishu_agent\docs\protocols\` and be copied into OpenClaw workspaces, or should OpenClaw read them directly from a shared path?
- Should OpenClaw internal agent IDs be renamed from historical ids such as `orchestrator`, or kept stable while only display names change?
- Should the Feishu mention renderer use `A2A_BOTS` as the single canonical source for display name to group mention ID mapping?
- Should typing status be added to codex-agent now, or kept as a later UX-only improvement after workflow stability?

## Verification Checklist For Future Upgrades

- `git status --short` is reviewed before edits.
- Config values are read from ignored local files or environment variables.
- No real Feishu IDs, secrets, tokens, or group transcripts are committed.
- Python wrappers are used before shell launchers.
- OpenClaw gateway and codex-agent are running after changes.
- The same TASK-ID is used throughout a workflow test.
- Feishu messages show non-empty `mentions` for bot-to-bot handoff.
- Final report records test commands, runtime state, and residual risks.
