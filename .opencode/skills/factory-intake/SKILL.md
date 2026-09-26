---
name: Factory Intake
description: Gate a requested change on an approved, sufficient specification and route missing decisions into the right planning flow
---

# Factory intake

Use this before implementation or ticket dispatch.

1. Find the feature issue from the user's reference, current branch, or GitHub
   search. If none exists, offer to create one with
   `factory:type:feature,factory:needs-spec`.
2. Read the entire issue and comments plus linked decision issues. Treat a spec
   as approved only when the feature has `factory:spec-approved`.
3. A sufficient spec names the problem and desired outcome, scope and
   non-goals, observable acceptance criteria, constraints, resolved or
   explicitly outstanding decisions, and validation expectations.
4. If sufficient and approved, proceed to `to-tickets` or dispatch existing
   implementation tickets.
5. If the route is clear enough to decide in one session, recommend
   `grill-with-docs`, followed by `to-spec`.
6. If the destination is known but the route genuinely needs multiple
   sessions, recommend `wayfinder`. Its tickets resolve decisions; after its
   map clears, run `to-spec` and only then `to-tickets`.
7. If only a specific human answer or action is missing, apply `factory:human`
   and post a concise checklist or question. Do not let a worker guess.

Never treat an open pull request, a Wayfinder map, or a collection of unresolved
decision tickets as an approved implementation spec.
