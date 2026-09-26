# Software Factory instructions

This repository is an OpenCode V2 template. Keep it useful when copied into a
product repository; do not hard-code this template repository's owner or URL in
runtime workflows.

## Factory operating rules

- GitHub Issues are the durable source of truth for specs, decisions, queue
  state, and implementation tickets. Pull requests are delivery artifacts.
- Do not implement work without an approved spec. Use `factory-intake` to check
  readiness and route unclear work into `grill-with-docs` or `wayfinder`.
- Wayfinder issues are decision tickets, never implementation queue items.
- Only issues labelled `factory:type:implementation` and `factory:ready`, with
  all blockers closed and an approved parent spec, may be dispatched.
- The coordinator is the sole queue claimant. Run no more than two writing
  workers, with one branch, worktree, and OpenCode child session per issue.
- Workers may commit, push their assigned branch, and open or update a pull
  request. Agents must never merge a pull request or push to the default branch.
- Treat `docs/factory/workflow.md` and `docs/agents/*.md` as the workflow contract.
- Run `scripts/validate-template` after changing factory configuration or
  vendored files. Run project-specific checks for product changes.

## Ponytail code policy

Be efficient, not careless. Read the task and trace the affected flow before
choosing a solution. Stop at the first rung that holds:

1. Do not build it if it is unnecessary.
2. Reuse what the codebase already has.
3. Prefer the standard library.
4. Prefer a native platform feature.
5. Prefer an already-installed dependency.
6. Use one line when one clear, correct line is enough.
7. Otherwise write the minimum code that works.

No speculative abstractions, avoidable dependencies, or unrequested
boilerplate. Prefer deletion to addition and boring to clever. Fix root causes,
not one reported call path. Never economize away understanding, trust-boundary
validation, data-loss prevention, security, accessibility, or explicitly
requested behavior. Non-trivial logic needs the smallest runnable check that
would fail if it broke. The pinned upstream policy is in
`vendor/ponytail/AGENTS.md`.

## Upstream skills

Files under `vendor/` are pinned upstream material. Do not edit them directly.
Factory-specific behavior belongs in `.opencode/skills/`, `.opencode/agents/`,
or `docs/factory/`. Follow `docs/factory/upstream-updates.md` when updating pins.
