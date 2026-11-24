# Local checkpoints

Run the bundled helper using its absolute skill-relative path:
`python3 <deliver-skill>/scripts/checkpoint.py --help`.

Every command takes `--project PATH --task SLUG` before its subcommand.
The default root is `$XDG_STATE_HOME/agent-workflows` or
`~/.local/state/agent-workflows`. The helper prints the checkpoint as JSON.

Examples (replace paths, slug, and user references with real values):

```bash
python3 <deliver-skill>/scripts/checkpoint.py --project /path/to/project --task retry-fix path
python3 <deliver-skill>/scripts/checkpoint.py --project /path/to/project --task retry-fix init --plan /path/to/plan.md --thread-ref current-thread-link
python3 <deliver-skill>/scripts/checkpoint.py --project /path/to/project --task retry-fix approve --user-ref approving-user-message
python3 <deliver-skill>/scripts/checkpoint.py --project /path/to/project --task retry-fix phase validating --evidence "Regression test passed"
python3 <deliver-skill>/scripts/checkpoint.py --project /path/to/project --task retry-fix phase awaiting_output_review --head <full-sha> --evidence "/path/to/task/qa-evidence.md: verified"
python3 <deliver-skill>/scripts/checkpoint.py --project /path/to/project --task retry-fix signoff --user-ref approving-output-message
python3 <deliver-skill>/scripts/checkpoint.py --project /path/to/project --task retry-fix status
```

Use the path command to locate a task directory for a local fallback plan.
Initialization requires an existing nonempty plan and starts awaiting_approval.
Approval stores a snapshot of the exact approved plan and the real user-message
reference. The helper cannot independently verify that reference.

After editing the plan:
- `amend --reason "..."` revokes approval and returns to awaiting_approval.
- `amend --within-scope --reason "..."` keeps the original scope approval and
  records the revision, but returns to implementing and clears old final evidence.
  Use it only for a correction already authorized by the original scope.

A changed plan is rejected by phase changes until an amendment or actual new
approval is recorded. Implementation always needs approval. Successful commands
write atomically under a local process lock. The lock serializes checkpoint
writes; it is not a cross-machine or whole-task execution lock.

Normal phases are implementing, validating, documenting, reviewing,
awaiting_output_review, publishing, watching, and ready.

Output sign-off: before the task's first publication, publishing requires a
recorded signoff for the current checkout head. Enter awaiting_output_review
with `--head` and `--evidence` (the QA evidence packet), then record the user's
actual sign-off with `signoff --user-ref`, which moves to publishing. From
awaiting_output_review, a requested change goes back to implementing; the new
head needs a new review and sign-off. Once a PR is tracked, in-scope repairs move
reviewing → publishing without a new sign-off. A scope amendment (without
`--within-scope`) clears the sign-off together with plan approval. Ready means green and still monitored until merged/closed;
it is not completion. Late suggestions or conflicts return to implementing,
then validation and review. Mark blocked with
`block --reason "..."`; `resume` restores the previous phase but still checks
the plan and approval. Watching and ready require evidence and a full head SHA;
ready also requires a PR URL. The host must verify those claims against GitHub.

After freshly observing the tracked PR merged or closed, use:

```bash
python3 <deliver-skill>/scripts/checkpoint.py --project /path/to/project --task retry-fix complete --outcome merged --head <observed-pr-head-sha> --evidence "Fresh PR state is MERGED; include merge details"
```

Use outcome closed for a PR closed without merge. This command requires a tracked
PR, a full observed head SHA, and evidence. It can record closure while blocked
or with an outdated plan/checkout, because external PR state is authoritative.
It does not perform a GitHub lookup; the caller must first verify the outcome.
Merged/closed checkpoints reject further mutations. Stop the T3 watch and notify
the user after recording the outcome. A reopened PR needs an explicit new task.
Terminal status remains readable if the plan has been archived or is unreadable;
plan_matches is null when its contents cannot be checked.

Checkpoint JSON and approved-plan snapshots are private local state, outside the
application and skill repositories. They contain no credentials. They are a
progress record, not a sandbox or an independently authenticated approval gate.
