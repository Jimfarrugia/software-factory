# Continuing an authorized queue

One `factory` session in the product root owns execution. Once the human
authorizes the queue, a progress report does not cancel that authorization.
Workers remain workers. Never switch an implementation session into a coordinator.

Launch with the owning coordinator's actual session ID:

```sh
scripts/factory-start-worker 12 /absolute/worktree /absolute/packet.md ses_owner
```

The launcher starts a monitor, not just a prompt-submission process. The monitor
submits the packet, waits for a new idle timestamp and no active worker loop,
and queues a completion message that resumes the owner. Idle is not proof of
success: the coordinator must inspect results, permissions, errors, and GitHub.

Resume a worker after review with the same monitored path (run this as a
background shell tool so the coordinator remains available):

```sh
python3 scripts/factory-monitor ses_owner ses_worker --prompt-file /absolute/fixes.md
```

Adopt an existing running or completed worker without sending it more work:

```sh
python3 scripts/factory-monitor ses_owner ses_worker
```

Run from the product root. State lives in `.factory/handoffs/`; a per-worker
file lock excludes duplicate monitors, and the last notified idle timestamp
prevents repeat completion delivery. Ownership cannot silently transfer.

## Delivery model

Posting is not consumption. The monitor queues the completion message in the
coordinator's inbox and exits; the message can wait there until the
coordinator's current turn ends, so a delivery may surface late. The monitor
cannot force consumption and does not try to. Making that wait visible and
harmless is the goal; a restart-persistent scheduler and exactly-once network
delivery are out of scope.

Every delivery decision appends one JSON line to `deliveries.jsonl` in the
monitor's state directory (`.factory/handoffs/` by default, `--state-dir`
otherwise). It is written for every decision — `delivered`, `suppressed`, or
`failed` — and records the worker session, issue number, branch, PR, observed
idle timestamp, worker outcome, decision, reason, and time. The record lives
outside the session transcript, so it survives compaction; the transcript alone
cannot be audited for deliveries.

Before treating a completion as actionable, the monitor reads the worker's issue
and branch from the `sessions` sibling of the state directory (by default
`.factory/sessions/<worker>.json`, written by `scripts/factory-start-worker`) and
checks the linked GitHub state: the issue via
`gh issue view <n> --json state`, and the branch's PRs via
`gh pr list --head <branch> --state all --json state,url`. A closed issue or a
merged PR suppresses the delivery: the decision and reason are recorded and
nothing actionable is queued. When the state cannot be determined — no `gh`, no
network, a command error, or unparseable output — the monitor fails closed: it
records `failed` with the reason and queues nothing. A suppressed or failed
decision sets no `notified` timestamp, so a later monitor run re-checks the same
idle worker once the state is knowable.

A delivered notification names the issue number, branch, and PR in addition to
the worker session and outcome, so the coordinator can judge it without looking
up a session ID.

## Stop and recovery

On a stop request, create `.factory/handoffs/<coordinator-session>.paused`.
This stops submissions/notifications when the monitor next observes the file;
it cannot cancel a request already starting or in flight, running workers, or
already-queued messages. The coordinator must respect the latest stop request
even when an older completion message arrives. Remove the pause file only after
explicit authorization to resume, then reattach monitors for existing workers.

If the monitor exits, inspect its log and state. A `failed` observation can be
reattached. For `submitting`, `delivering`, or `delivery-uncertain`, inspect the
worker/coordinator inbox and history before repairing state: do not blindly
retry an API request whose response may have been lost. No exactly-once network
delivery guarantee is claimed. Monitors require the local machine and OpenCode
service to remain available; this is not a restart-persistent scheduler.

## Coordinator continuation

On completion: inspect results, independently review, route fixes through the
monitor again, wait for required CI via a background shell/check watcher, and
merge only after existing gates pass. Use native background reviewer completion
notifications. Do not finish responsibility for the queue merely because a
worker or check is pending. Attach its completion observer first.

After two unsuccessful fix/review cycles for the same blocker, escalate it with
evidence instead of retrying indefinitely. Continue unrelated authorized work.
Stop when the queue is complete, explicitly paused, or has only human-blocked
work. Status questions report a snapshot without revoking execution intent.
