# Issue tracker: GitHub

Issues and specs live in the GitHub repository inferred from `git remote -v`.
Use `gh` for reads and writes. Pull requests deliver implementation; they are
not feature requests or queue tickets.

## Operations

- Read an issue and comments: `gh issue view <number> --comments`.
- List issues with labels: `gh issue list --state open --json number,title,body,labels,assignees,url`.
- Create: `gh issue create --title "..." --body-file <file> --label "..."`.
- Change state labels with `gh issue edit --add-label` and `--remove-label`.
- Comment: `gh issue comment <number> --body "..."`.
- Close only after its completion condition is met: `gh issue close <number>`.

GitHub shares number space between issues and PRs. Resolve ambiguous numbers by
trying `gh pr view <number>` and then `gh issue view <number>`.

## Relationships

Feature specs are parent issues. Implementation and decision issue bodies link
their parent using `Parent: #<number>`. Prefer GitHub native sub-issues and
dependencies when available. Otherwise, use the body conventions and verify
referenced issue states before dispatch.

- Native sub-issue API: `POST repos/{owner}/{repo}/issues/{parent}/sub_issues`
  with the child issue database ID.
- Native blocker API: `POST repos/{owner}/{repo}/issues/{issue}/dependencies/blocked_by`
  with the blocker issue database ID.
- Fallback blocker line: `Blocked by: #12, #13`, or `Blocked by: None`.

## Wayfinding operations

A map has `wayfinder:map`; children use exactly one of `wayfinder:research`,
`wayfinder:prototype`, `wayfinder:grilling`, or `wayfinder:task`. Wayfinder
children are decision work and must not receive `factory:type:implementation`.
An unassigned child with no open blocker is on the decision frontier. Claim it
by assignment before work and resolve at most one non-research ticket per
session.

## Factory claims

The coordinator is the only claimant. It posts a comment in this exact form:

```text
<!-- factory-claim issue=<n> session=<id> branch=<branch> worktree=<absolute-path> claimed-at=<ISO-8601> -->
```

GitHub is canonical; any local cache must be disposable and reconstructable.
