# Agent Control Center Historical Plan

Last updated: 2026-07-13

This document originally described the temporary split between Agent Control Center and the former `feishu_agent` repository. That split is no longer the active architecture.

Current state:

- Single repository root: `{ACC_ROOT}`
- Public CLI: `python scripts/stack.py ...`
- Control plane: `{ACC_ROOT}/src` and `{ACC_ROOT}/web`
- Feishu runtime package: `{ACC_ROOT}/agent-runtime`
- Local runtime state: `{ACC_ROOT}/runtime`
- Local project workspaces: `{ACC_ROOT}/projects`
- Code executor workspace: `{ACC_ROOT}/workspaces/dev`
- Local config source of truth: `{ACC_ROOT}/config/stack.settings.local.json`

The former Feishu Agent workspace has been removed from this machine. Do not add new docs, scripts, or config that point to `{OLD_FEISHU_AGENT_ROOT}`.

Use these current references instead:

- [docs/ops/README.md](ops/README.md)
- [docs/ops/ARCHITECTURE.md](ops/ARCHITECTURE.md)
- [docs/ops/CONFIG.md](ops/CONFIG.md)
- [docs/ops/STARTUP.md](ops/STARTUP.md)
- [docs/ops/PHYSICAL-MERGE-2026-07-13.md](ops/PHYSICAL-MERGE-2026-07-13.md)

Compatibility note:

The Python package name remains `feishu_stack` for now. That name is code identity, not a filesystem path back to the old repository.
