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
