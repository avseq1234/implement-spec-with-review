# Review, findings and bounded recovery

An effective round reviews a definite full candidate and returns a complete report. Independent phase and reconciliation together count once. Round 1 fresh; round 2 resume; round 3 fresh; rounds 4–5 resume unless approved context/session rules require fresh. Stop as soon as quality gates pass. Failed infrastructure attempts have finite retries and total budgets; they do not consume an effective review. Waiting for the user consumes neither reviews nor active execution time.

After round 2, unresolved blocking findings or failed completion gates select fallback for the NEXT correction. A new fallback CLI session stays under the same Execution manager. Ambiguity, environment and permissions are clarified rather than “solved” by a different model. Fallback role can use the same model/effort; disclose that only the session is fresh in that case.

High-risk task classification is user-confirmed. Such tasks need an additional fresh independent review of the final candidate, within five rounds. A suitable round 3 may satisfy it; round 1 alone never does. Reserve budget. Any later source change requires renewed relevant verification; never reuse a high-risk approval for a different snapshot. Fifth review must match latest code; failure stops, without another unreviewed fix.

Fresh reviewers first independently read original specs, acceptance, latest code, cumulative changes and interfaces. Prior finding conclusions/ledgers are withheld. Runner saves those findings, then phase 2 reconciles old ledger/rebuttals. An independent issue cannot silently disappear or be downgraded. Closed findings that reappear are reopened. Technical evidence may resolve an issue; subjective unresolved disagreements go to the user.

Ledger states: OPEN, ACCEPTED, FIXED_PENDING_VERIFICATION, VERIFIED_FIXED, REBUTTED_PENDING_ADJUDICATION, DISMISSED_WITH_EVIDENCE, BLOCKED. CLI reports ACCEPT/REBUT with evidence; completed ACCEPT changes go to FIXED_PENDING_VERIFICATION. Only reviewer evidence moves to VERIFIED_FIXED/DISMISSED_WITH_EVIDENCE. No new reviewer is introduced as an arbitration vote.

A source snapshot includes tracked, dirty, untracked nonignored files, deletions, modes and symlink metadata, excluding runtime logs. Ignored source inputs must be explicitly identified and included in preflight; generated caches are not code evidence. Submodules and unsafe symlink materialization are not guessed: unsupported layouts stop for a user-approved approach. HEAD alone is insufficient. Gate commands must not alter source; changed snapshots invalidate their results.

Authorized later tasks legitimately extend the repository. Earlier task evidence remains tied to its accepted checkpoint; final integration review examines all accumulated work. Unaccounted changes discovered on recovery invalidate prior completion and require inspection. Never use an old test/review to approve a changed candidate.

The event journal is authoritative; atomic state/checkpoints/logs are projections. Each invocation records its unique ID, task, role, provider/model/effort, session, worktree, process identity and snapshots. Repository writer locking covers all runs sharing a Git common directory. Reviewer workspaces are separate; the source is checked unchanged. Do not concurrently resume a session. If an old process is still alive, it must stop before write ownership is handed off.

For context pressure or manager replacement, checkpoint original document hashes, constraints, decisions, task acceptance, candidate, unresolved ledger, rebuttals/dispositions, failures, test environment/evidence and next step. Reload originals after compaction. Session replacement never resets budgets. Metrics unavailable from CLI remain null/unavailable, including precise read time, startup decomposition or context occupancy; do not infer them from billed tokens.

Foreground CLI and ordinary descendant process groups are terminated before releasing writer ownership. Detached daemon/service lifecycles are outside this runner protocol and must be explicitly planned in preflight; do not start them implicitly. Codex runs with its verified --no-daemon flag.
