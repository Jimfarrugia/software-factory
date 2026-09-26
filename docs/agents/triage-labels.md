# Triage labels

Matt Pocock's skills use five canonical roles. This template maps them to the
factory state vocabulary:

| Skill role | Repository label | Meaning |
| --- | --- | --- |
| `needs-triage` | `factory:needs-triage` | Coordinator or maintainer must classify it |
| `needs-info` | `factory:needs-spec` | More specification or product information is required |
| `ready-for-agent` | `factory:ready` | Fully specified and eligible for an AFK agent |
| `ready-for-human` | `factory:human` | A human decision or action is required |
| `wontfix` | `factory:wontfix` | Intentionally not actioned |

When an upstream skill names the left-hand role, apply the corresponding
right-hand label. An issue should have only one active factory state label.
