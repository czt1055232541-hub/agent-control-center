# Codex Provider Switching

`E:\codeX` remains the real Codex home. Provider scripts only edit `E:\codeX\config.toml`; they do not move sessions, rewrite sqlite databases, or modify rollout files.

## Switch Provider

```powershell
.\codex\Switch-CodexProvider.ps1 -Mode native
.\codex\Switch-CodexProvider.ps1 -Mode moonbridge
```

MoonBridge mode requires `http://127.0.0.1:38440/v1/models` to be reachable unless `-AllowUnavailableMoonBridge` is passed.

Each successful switch keeps only the newest `config.toml.bak-switch-*` file. Goal baseline backups are preserved.

## Start Services

```powershell
.\scripts\start-all.ps1 -CodexMode native
.\scripts\start-all.ps1 -CodexMode moonbridge
.\scripts\start-all.ps1 -CodexMode current
```

`native` starts OpenClaw and Codex Feishu Agent, and skips MoonBridge.

`moonbridge` starts OpenClaw, MoonBridge, and Codex Feishu Agent.

`current` reads `E:\codeX\config.toml` and starts MoonBridge only when the active provider is MoonBridge.

## Verified Status

Last local verification: 2026-06-18.

- `native`: `codex doctor --summary` loaded config and auth, reached the active provider over HTTP, and reported no failures.
- `moonbridge`: `codex doctor --summary` loaded config, did not require OpenAI auth for the active provider, reached the active provider over HTTP, and reported no failures.
- Remaining doctor warnings are unrelated to the switch scripts: Codex WebSocket fallback in native mode and two historical thread rows pointing at missing rollout files.

Because Codex Desktop was running during the setup, live `resume` / `fork` cross-provider validation is intentionally left for manual confirmation.

## Conversation Continuity

Projects and sessions share the same `CODEX_HOME`, but Codex Desktop may not seamlessly continue an existing UI thread across provider changes because rollout metadata records the original `model_provider`.

When Codex Desktop is not actively using the target session, use:

```powershell
.\codex\Test-CodexProviderThread.ps1 -SessionId <session-id> -TargetModel moonbridge
```

The test records whether `resume` or `fork` can cross providers. Treat this as a manual validation step until you confirm it on a quiet Codex Desktop session.

If direct continuation fails, use:

```powershell
.\codex\Continue-CodexThreadWithProvider.ps1 -SessionId <session-id> -TargetModel moonbridge
```

That tool first attempts direct fork. If it fails, it creates a new provider run using a summary migration prompt from the prior rollout tail.
