# Domain context

## Ubiquitous language

- **Factory**: the complete OpenCode and GitHub workflow installed in a product repository.
- **Coordinator**: the primary agent through which the human plans and dispatches work.
- **Worker**: one implementation subagent bound to one issue, branch, and worktree.
- **Reviewer**: a read-only subagent that checks a worker's diff against standards and spec.
- **Feature**: the parent GitHub issue containing an approved implementation spec.
- **Decision ticket**: a Wayfinder issue that resolves uncertainty; it is not build work.
- **Implementation ticket**: one independently verifiable tracer-bullet slice of a feature.
- **Frontier**: ready implementation tickets whose blockers are all closed.
- **Claim**: the coordinator's machine-readable issue comment linking a running session,
  branch, and worktree to a ticket.
- **Human queue**: issues that require a decision, access, approval, or other human action.

Avoid calling decision tickets "tasks" or treating pull requests as queue tickets.
