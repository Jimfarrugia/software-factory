# Software Factory

An interactive, GitHub-backed AI software factory for OpenCode V2. You work
with one coordinator while isolated workers implement ready tickets in the
background. Matt Pocock's planning skills provide the path from an idea to an
approved spec and tracer-bullet tickets; Ponytail keeps implementation small
without cutting safety.

## What it does

- Prompts for planning when implementation has no approved specification.
- Routes focused work through `grill-with-docs` and multi-session uncertainty
  through `wayfinder`.
- Stores specs, decisions, dependencies, and queue state in GitHub Issues.
- Dispatches at most two implementation workers into separate Git worktrees.
- Independently reviews pull requests and lets the coordinator merge them only
  after required checks pass.
- Surfaces decisions and blocked work in a human queue.

## Start a product repository

1. Create a repository from this GitHub template and clone it.
2. Install OpenCode V2, GitHub CLI (`gh`), Git, Bash, and `jq`.
3. Authenticate: `gh auth login` and configure your OpenAI provider in OpenCode.
4. Run `scripts/factory-setup` to create the label vocabulary.
5. Protect the default branch as described in `docs/factory/security.md`. Solo
   owners using one GitHub identity must allow self-merge by requiring zero
   approvals; installations with a separate worker bot should require one.
6. Start `opencode` in the repository. The `factory` agent is selected by default.
7. Describe a feature, invoke `/factory-intake`, or ask for `/factory-status`.

The coordinator, workers, and reviewer default to
`openai/gpt-5.6-luna#high`. Their Markdown definitions can be changed
independently.

## Using the factory

1. Start `opencode` and describe what you want: `Add team invitations`.
2. Let the coordinator check for a spec. If one is missing, use
   `/grill-with-docs` for work you can plan in one session or `/wayfinder` for a
   large effort with unresolved decisions.
3. Approve the resulting spec and implementation-ticket breakdown. The
   coordinator publishes them as GitHub Issues and dispatches ready,
   non-overlapping tickets to at most two workers.
4. Keep planning or queueing features while workers run. Ask
   `/factory-status` at any time to see ready, running, blocked, human-input,
   and review work.
5. Answer issues in the human queue when the factory needs a decision or
   privileged action.
6. The coordinator reviews completed PRs and may merge them after required
   checks pass and no blocking findings or human decisions remain. You can still
   review or merge any PR yourself.

Useful prompts:

```text
Plan this feature before building it: <idea>
Queue the approved spec in issue #12
What needs my input?
Show factory status
```

## Core flow

```text
idea -> grill-with-docs -> spec -> implementation tickets -> workers -> PR
  \-> wayfinder -> decision tickets -> spec --------------------/
```

See [`docs/factory/workflow.md`](docs/factory/workflow.md) for states and
dispatch rules, and [`docs/factory/security.md`](docs/factory/security.md) for
the required GitHub protections.

## Development

```sh
scripts/validate-template
```

Development validation also requires `shellcheck`.

Upstream sources and commits are recorded in `upstream-lock.json`. Vendored
licenses remain beside their sources.
