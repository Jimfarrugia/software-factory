---
name: Factory Dispatch
description: Claim ready GitHub implementation tickets and launch at most two isolated OpenCode workers safely
---

# Factory dispatch

## Reconcile first

Run `scripts/factory-status`. For each `factory:running` issue, check its latest
`<!-- factory-claim ... -->` comment, branch, worktree, child session, and PR.
Move an issue with an open PR to `factory:review`. Return an abandoned claim to
`factory:ready` only after preserving and reporting any uncommitted work.

## Select the frontier

An issue is dispatchable only when all are true:

- open and labelled `factory:type:implementation` and `factory:ready`;
- linked to a parent feature labelled `factory:spec-approved`;
- all blocking issues are closed;
- no unresolved human decision remains;
- it does not overlap a running worker's likely files, schema, migration, or API.

Never dispatch a `factory:type:decision`, `wayfinder:map`, or
`wayfinder:*` issue. Keep no more than two writing workers active.

## Claim and isolate

The coordinator performs these writes in order:

1. Remove `factory:ready`, add `factory:running`.
2. Create branch `factory/<issue>-<slug>` from the current default branch.
3. Create a sibling worktree under `../<repo>-worktrees/<issue>-<slug>`.
4. Write the complete worker packet to a temporary prompt file outside the
   repository, then run
   `scripts/factory-start-worker <issue> <worktree> <prompt-file> <coordinator-session>`. This creates
   a `worker` session with the worktree as its explicit OpenCode `location`,
   verifies that binding, and starts its prompt asynchronously.
5. Post a machine-readable claim comment using the returned session ID:

   `<!-- factory-claim issue=<n> session=<id> branch=<branch> worktree=<absolute-path> claimed-at=<ISO-8601> -->`

6. Its packet must contain the
   issue and parent URLs, full acceptance criteria, decisions, absolute
   worktree, branch, allowed scope, required checks, and PR wording.

The worker must also confirm its location before editing. Do not replace the
explicit session location with a prompt to `cd`; that is not isolation. Session
state and logs under `.factory/sessions/` are disposable observations, not the
durable queue.

## Completion

Follow `docs/factory/completion-handoff.md`: keep explicit coordinator ownership,
monitor every new/resumed worker, and adopt existing sessions rather than
duplicating them. Completion wakes the coordinator to continue the authorized
queue. Attach observers to review and CI waits as well. Honor pause requests.

After a worker opens a PR, replace `factory:running` with `factory:review` and
launch `reviewer`. The coordinator may merge only after all required checks pass,
the independent review has no blocking findings, acceptance criteria are met,
the PR is mergeable and not a draft, and no human decision or conversation is
unresolved. Workers and reviewers never merge. On failure, preserve the branch
and worktree, post the blocker, and use `factory:blocked` or `factory:human` as
appropriate.
