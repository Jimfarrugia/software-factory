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
