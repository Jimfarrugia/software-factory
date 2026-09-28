# Factory workflow

## Durable artifacts

GitHub holds all durable orchestration state:

- feature issue: canonical approved spec;
- decision issue: one question resolved by Wayfinder or a human;
- implementation issue: one verifiable vertical slice;
- pull request: implementation delivery and review conversation;
- claim comment: issue-to-session/worktree binding.

OpenCode sessions and worktrees are execution resources, not queue databases.

## Planning lanes

Use `grill-with-docs -> to-spec` when the work can be settled in one session.
Use `wayfinder -> decision frontier -> to-spec` when the destination is known
but the route requires several sessions. Both lanes converge before
`to-tickets`; implementation never starts directly from a Wayfinder map.

An approved spec includes the outcome, scope and non-goals, acceptance
criteria, constraints, resolved decisions, and validation expectations. Mark
its feature issue with `factory:spec-approved`.

## Types and states

Exactly one type applies:

- `factory:type:feature`
- `factory:type:implementation`
- `factory:type:decision`

At most one active state applies:

- `factory:needs-triage`
- `factory:needs-spec`
- `factory:ready`
- `factory:human`
- `factory:running`
- `factory:blocked`
- `factory:review`
- `factory:wontfix`

Closed issues are terminal; there is no redundant done label.

State labels describe implementation tickets. A feature issue keeps its
`factory:type:feature` label, uses `factory:spec-approved` once its spec is
approved, and must never carry `factory:ready`, `factory:running`, or
`factory:review`. A decision issue never carries `factory:ready` either. If a
feature needs human input, use `factory:human`; if it needs more specification,
use `factory:needs-spec`. A `factory:ready` issue without
`factory:type:implementation` is mislabeled and is excluded from the frontier.

Typical implementation flow:

```text
needs-spec -> ready -> running -> review -> closed
                    \-> blocked -> ready
                    \-> human -> ready
```

## Dispatch contract

Only an open `factory:type:implementation` issue in `factory:ready` can enter
the worker frontier. Its parent must have `factory:spec-approved`, every blocker
must be closed, and no human decision may remain. The coordinator claims work,
creates `factory/<issue>-<slug>` and a sibling worktree, posts the claim, then
launches one worker in that location. `scripts/factory-start-worker` creates the
OpenCode session with an explicit location, verifies the returned location, and
submits the packet asynchronously. This mechanism was verified against
OpenCode V2.0.15; re-run an isolation spike after an OpenCode API upgrade.

Concurrency defaults to two, but dependency, migration, schema, API, and likely
file overlap override that limit. One writer owns one worktree. If child-session
location isolation has not been verified for the installed OpenCode version,
run one worker only.

## Recovery

At startup and before dispatch:

- open PR for a running issue: move it to `factory:review`;
- closed/merged PR: close the implementation issue if acceptance criteria pass;
- closed blockers: make an otherwise eligible issue ready;
- running issue without a live session: inspect branch and worktree, then mark
  blocked or safely return it to ready;
- stale worktree with changes: report it; never delete or reset automatically.

The coordinator may merge a non-draft PR after every required check passes, its
independent review has no blocking findings, acceptance criteria are met, no
human decision or conversation remains unresolved, and GitHub reports the PR
mergeable. Workers and reviewers never merge. A merged PR may close its linked
implementation issue, but never silently closes the parent feature until all
feature acceptance criteria are met.
