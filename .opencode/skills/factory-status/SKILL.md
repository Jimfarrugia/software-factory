---
name: Factory Status
description: Reconcile and summarize ready, running, blocked, review, and human-input factory work from GitHub
---

# Factory status

Run `scripts/factory-status` for the queue snapshot, then reconcile it with
GitHub PRs, branches, worktrees, and active OpenCode child sessions.

Report five short sections:

1. **Ready frontier**: dispatchable implementation tickets and blockers.
2. **Running**: issue, worker/session, branch, elapsed time, and latest progress.
3. **Human queue**: the exact decision or action requested from the user.
4. **Review**: PR, checks, review findings, and merge owner.
5. **Blocked/stale**: cause and safest recovery action.

GitHub wins over remembered state. Do not delete stale worktrees or discard
uncommitted changes automatically. If the user asks to queue more work, keep
running workers alive and route the new request through `factory-intake`.
