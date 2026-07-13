# Git Privacy Policy

## Never Commit

- `.env` files containing real values.
- Feishu `open_id`, `chat_id`, `app_id`, `app_secret`, tokens, cookies, and session dumps.
- Raw webhook payloads, raw post message payloads, or debug logs with identifiers.
- Local browser state, credential caches, or generated auth files.
- Private conversation transcripts unless explicitly approved and sanitized.

## Safe Documentation

- Use role names instead of IDs.
- Use placeholders such as `<LOCAL_A2A_BOT_ID>` only when a field shape must be documented.
- Summarize errors by category without copying secret-bearing payloads.

## Pre-Closeout Scan

Run a local sensitive-state scan before commit or handoff. Report whether sensitive-looking patterns were found, but do not print secret values into group chat.

## History Rewrite

If sensitive content was committed:

1. stop all publish/push actions;
2. identify affected commits and paths locally;
3. ask for explicit confirmation before history rewrite;
4. rewrite with a bounded tool and path list;
5. rotate exposed credentials if they may have left the machine;
6. run a fresh scan before any publish action.
