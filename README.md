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
- Opens pull requests for human review and never merges them.
- Surfaces decisions and blocked work in a human queue.

## Start a product repository

1. Create a repository from this GitHub template and clone it.
2. Install OpenCode V2, GitHub CLI (`gh`), Git, and Bash.
3. Authenticate: `gh auth login` and configure your OpenAI provider in OpenCode.
4. Run `scripts/factory-setup` to create the label vocabulary.
5. Start `opencode` in the repository. The `factory` agent is selected by default.
6. Describe a feature, invoke `/factory-intake`, or ask for `/factory-status`.

The coordinator, workers, and reviewer default to
`openai/gpt-5.6-luna#high`. Their Markdown definitions can be changed
independently.

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

Upstream sources and commits are recorded in `upstream-lock.json`. Vendored
licenses remain beside their sources.
