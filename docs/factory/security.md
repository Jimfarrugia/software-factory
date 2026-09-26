# Security and autonomy boundaries

OpenCode prompt and shell permission rules reduce accidents; they are not a
host sandbox. Enforce the important boundary at GitHub.

## Required repository rules

Protect the default branch:

- require pull requests;
- require at least one human approval;
- require configured status checks;
- block force pushes and branch deletion;
- do not grant the worker identity a ruleset bypass;
- prevent direct pushes to the default branch.

Prefer a dedicated worker identity with only the repository access needed to
push feature branches and open pull requests. Never place credentials in issue
bodies, prompts, claim comments, branches, or committed configuration.

## Agent boundaries

Workers cannot create subagents, merge PRs, force push, hard-reset, clean
untracked files, or push the conventional default branch names. Reviewers are
read-only. The coordinator is the sole queue claimant and never merges.

Shell command matching is defense in depth and cannot prevent every equivalent
command. GitHub rulesets and token permissions are the enforcement boundary.

## Human queue

Use `factory:human` for product decisions, account provisioning, credentialed
actions, external approval, or destructive work. State what is needed without
including secrets. Resume only after the human records a safe resolution.
