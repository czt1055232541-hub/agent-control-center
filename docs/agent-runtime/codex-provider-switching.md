# Codex Provider Switching

Provider state is now split by runtime:

- ChatGPT/Codex App keeps using the App Codex home, usually `E:\codeX`, and its provider config is `E:\codeX\config.toml`.
- Feishu Codex Agent uses an independent Codex home, by default `{ACC_ROOT}\agent-runtime\codex-home`, and its provider config is `{ACC_ROOT}\agent-runtime\codex-home\config.toml`.

Provider scripts edit only the selected runtime's `config.toml`; they do not move sessions, rewrite sqlite databases, or modify rollout files. When the Agent config does not exist yet, ACC bootstraps it from the App config and copies the model catalog needed for MoonBridge. During bootstrap, ACC also rewrites Agent `CODEX_HOME` and `CODEX_CLI_PATH` so the Agent follows its independent config while still using the current app-managed Codex CLI binary.

## Switch Provider

```bash
python scripts/stack.py switch-provider native
python scripts/stack.py switch-provider moonbridge
```

The legacy CLI switch command targets the App config. In the ACC frontend, the "ChatGPT/Codex App Provider" and "Feishu Codex Agent Provider" cards call separate API routes and can be switched independently. Switching the Agent provider restarts a running `codex-agent` process so the new `CODEX_HOME` is inherited by future Codex CLI child processes.

MoonBridge mode requires `http://127.0.0.1:38440/v1/models` to be reachable unless `-AllowUnavailableMoonBridge` is passed.

Each successful switch keeps only the newest `config.toml.bak-switch-*` file. Goal baseline backups are preserved.

## Start Services

```bash
python scripts/stack.py stack start-native
python scripts/stack.py stack start-moonbridge
python scripts/stack.py status
```

`native` starts OpenClaw and Codex Feishu Agent, and skips MoonBridge.

`moonbridge` starts OpenClaw, MoonBridge, and Codex Feishu Agent.

Stack start actions now switch only the Feishu Codex Agent provider. They intentionally leave the ChatGPT/Codex App provider unchanged.

Stack start actions restart `codex-agent` even when it is already running. This is intentional: provider choice is read from environment/config at process start, so a running Agent must be refreshed after switching between Native and MoonBridge.

`status` reports both App and Agent provider configs so operators can confirm they are intentionally different.

## Verified Status

Last local verification: 2026-06-18.

- `native`: `codex doctor --summary` loaded config and auth, reached the active provider over HTTP, and reported no failures.
- `moonbridge`: `codex doctor --summary` loaded config, did not require OpenAI auth for the active provider, reached the active provider over HTTP, and reported no failures.
- Remaining doctor warnings are unrelated to the switch scripts: Codex WebSocket fallback in native mode and two historical thread rows pointing at missing rollout files.

Cross-provider validation was run on 2026-06-18 with native session `019ed8ed-2bb4-7d01-91d1-a3cce908c7d7` and target model/provider `moonbridge`.

- `codex exec resume <session_id> -m moonbridge` accepted the native session and started with `model: moonbridge`, `provider: moonbridge`, and the original session id. Codex logged: `resuming session with different model: previous=gpt-5.5, current=moonbridge`.
- `codex exec resume <session_id> -c model="moonbridge" -c model_provider="moonbridge"` also started with `model: moonbridge`, `provider: moonbridge`, and the original session id.
- Both non-interactive resume runs were stopped after the configured timeout before a final assistant response was produced.
- `codex fork ...` cannot be validated from a hidden non-interactive process because the CLI requires a terminal and exits with `stdin is not a terminal`.

Conclusion: CLI resume can attach the previous native session to the MoonBridge provider without manually editing Codex DB or rollout files. Full response completion and interactive `fork` should still be manually confirmed in a real terminal/Codex UI.

## Conversation Continuity

Projects and sessions share the same `CODEX_HOME`, but Codex Desktop may not seamlessly continue an existing UI thread across provider changes because rollout metadata records the original `model_provider`.

When Codex Desktop is not actively using the target session, use:

```bash
python scripts/stack.py migrate-thread --session-id <session-id> --target-provider moonbridge
```

The test records whether `resume` or `fork` can cross providers. Headless `fork` is expected to fail unless it has a real terminal.

If direct continuation fails, use:

```bash
python scripts/stack.py migrate-thread --session-id <session-id> --target-provider moonbridge
```

That tool first attempts bounded `codex exec resume`. If it fails or times out, it creates a new provider run using a summary migration prompt from the prior rollout tail. The tool writes stdout/stderr logs under `runtime\logs`, which is intentionally ignored by git.
