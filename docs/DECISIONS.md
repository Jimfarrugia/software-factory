# Decisions

## ADR-0001: Executable dispatch predicate

The dispatch eligibility predicate is executable and authoritative in
`scripts/factory-frontier`. `docs/factory/workflow.md` and the dispatch skill
describe its use; they do not independently define the predicate.

## ADR-0002: Body-first relationships

Parent and blocker relationships are read from issue-body conventions, with
native GitHub relationships unioned when present. The body remains the durable
encoding until a migration is deliberately chosen. This diverges from
`docs/agents/issue-tracker.md`, which prefers native relationships: nothing
currently populates those relationships, while every existing ticket uses the
body form.

## ADR-0003: Positional relationship fields

Relationship fields are recognised by position, not Markdown block analysis.
Flat fields come only from the body's leading block at column 0, with blank
lines permitted between fields; section fields come only from a column-0
heading. Fenced- and indented-code detection is deliberately absent. Three
review cycles of heuristic block detection each produced a new defect, while
this anchored contract is smaller and total. The accepted residual is that a
fenced example whose content begins with a known heading at column 0 can still
satisfy the section form.
