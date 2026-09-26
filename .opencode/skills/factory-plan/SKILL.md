---
name: Factory Plan
description: Route a product idea through Matt Pocock's planning skills into an approved spec and implementation-ticket frontier
---

# Factory planning

Choose the lightest planning route that fits:

- One-session clarification: load `grill-with-docs`; when decisions are settled,
  load `to-spec`.
- More than one session with a foggy route: load `wayfinder`; resolve its
  decision frontier over separate sessions, then load `to-spec`.
- Decisions already settled in the conversation: load `to-spec` directly.

The resulting feature issue must contain the canonical spec and receive
`factory:type:feature` plus `factory:spec-approved`. Remove
`factory:needs-spec`. Then load `to-tickets` to create vertical implementation
slices. Label those `factory:type:implementation` and `factory:ready` only when
they have acceptance criteria and all declared blockers are closed.

Keep decision tickets and implementation tickets distinct. A cleared
Wayfinder map is planning input, not a build queue.
