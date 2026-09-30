# Runner protocol

Run Python from the installed skill directory or use its absolute path. Every mutation acquires run locking; implementation and gate calls additionally acquire the repository's shared writer lock. Never edit canonical JSON directly to make an action pass.

```sh
python3 scripts/runner.py init --repo /absolute/repo --config /tmp/config.json --manifest /tmp/manifest.json
python3 scripts/runner.py gates --run /absolute/repo/.spec-runs/EXPLICIT-ID --task 1.1 --phase baseline
python3 scripts/runner.py approve --run /absolute/repo/.spec-runs/EXPLICIT-ID --answer-file /tmp/actual-user-confirmation.txt
python3 scripts/runner.py bind --run /absolute/repo/.spec-runs/EXPLICIT-ID --task 1.1 --execution-agent ACTUAL-APP-ID --review-agent ACTUAL-APP-ID
python3 scripts/runner.py context --run /absolute/repo/.spec-runs/EXPLICIT-ID --task 1.1 --assessment /tmp/context.json
python3 scripts/runner.py invoke --run /absolute/repo/.spec-runs/EXPLICIT-ID --task 1.1 --kind implement
python3 scripts/runner.py gates --run /absolute/repo/.spec-runs/EXPLICIT-ID --task 1.1
```

Context file, after the user has approved unknown-context continuation:

```json
{"source":"CLI does not expose reliable current occupancy","capacity":null,"next_read_bytes":4200,"action":"resume","reason":"bounded relevant read set; no observed capacity failure"}
```

Record a new assessment before EACH invoke. Review uses `--kind review`, then after a fresh review `--kind reconcile`. This second CLI call is phase 2 of the SAME effective round. A resumed review that does not require independent stage can finish in one call. Round 3 automatically forces fresh. After fixes rerun gates before reviewing. `--kind fix` automatically chooses the selected fallback once triggered. No `--last` shortcut.

If a CLI returns NEEDS_USER_INPUT, use status to read questions, ask the user, and record the actual answer with `answer --answer-file ... --category requirement|adjudication`. Classify factual specification clarifications as requirement, and evidence-based dispositions of prior findings as adjudication. Managers receive every answer; independent reviewers receive requirement clarifications first and adjudications only during phase 2. The answer is included in subsequent relevant CLI handoffs. Do not write an invented approval. Model/effort changes, spec changes, baseline exceptions or task restructuring require a newly reviewed configuration/plan; do not patch state during a run.

`checkpoint --reason ...` saves recovery details. `recover` checks old process identity and snapshot; it never blindly reruns an invocation. An uncertain interrupted write pauses for evidence inspection. `cancel` signals only the recorded process group with matching process-start identity, waits for termination and the writer lock, then marks cancellation. OS process inspection must be available; permission restrictions are surfaced, never bypassed.

## Configuration contract

Use `make_fixture.py` for an inspectable concrete config/manifest example. A real run must explicitly provide:

- `roles`: primary/reviewer/fallback, each with display_name, provider, actual model, effort, cli, verified_efforts and capability_evidence. `model-default` is only valid if explicitly verified in verified_efforts; no guessing from a display label.
- `limits`: finite positive timeout_seconds, max_calls, active_seconds, heartbeat_seconds; finite retry_limit. Effective review cap is fixed at five and cannot be raised by config.
- `context_policy` (`ask` or `checkpoint-resume`) and `context_policy_confirmed=true` only after user confirmation.
- `baseline_exceptions`: explicitly approved objects with task, gate, output_sha256. `tdd_exceptions`: approved original task IDs, with reasoning in the initial decision.
- `allow_independent_after_block`: explicit initial-plan choice, normally false; do not silently infer.
- `manifest.documents`: original path, kind (high-level/tasks/spec required; proposal/design/supporting/diagram as applicable). Runner adds SHA-256.
- `manifest.tasks`: original id, requirements, acceptance, dependencies, high_risk and gates (id, argv). Put detailed requirement/scenario/test mapping in original specs or extra manifest fields.
- `manifest.final_gates`: full-suite, integration and other agreed argv.

## Evidence and reports

External CLI uses `capture.py --context <runner-created file> --phase red|green|test-after --gate ID [--expected literal]`. This runs approved test argv and records output, exit, duration and source snapshot in isolated spool. Runner imports validated receipts. Do not manually author receipts or skip full delivery gates. Test-after is allowed but disclosed; never relabel it test-first.

Report shape is `templates/report.schema.json`. Schema providers constrain format; runner independently validates semantics. Findings need stable ID/severity/blocking/file/line/requirement/trigger/impact/evidence/direction. Implementer replies ACCEPT or REBUT; only reviewer can verify/dismiss. Incomplete/malformed/nonzero/timeout outputs do not count as effective reviews, but attempts consume finite infrastructure/call/time budget.

## Recovery limits

`events.jsonl` is append-only and includes checksummed state frames. Atomic JSON/Markdown projections can be regenerated from the last complete event. A truncated/corrupt event tail intentionally stops for inspection instead of silently discarding possible writes. Process output is saved before applying a result; invocation IDs prevent pretending an unobserved retry was the original attempt. A failed write cannot be retried automatically merely because a process exited.

## Temporary inputs and explicit review invalidation

Keep manager context assessments, approval files and handoff inputs outside the candidate repository (for example in a separate temporary directory). An untracked manager file is still part of the candidate snapshot. Never change canonical logs by hand. Review admission rejects a snapshot different from the last runner-accounted candidate; inspect unexplained changes before proceeding. Restore only a proven manager-created temporary artifact when already authorized; preserve user changes and ask about ambiguity.

If a saved independent review must be abandoned because its session or evidence is invalid, use `runner.py invalidate-review --run RUN --task ORIGINAL_ID --reason "concrete evidence and recovery reason"` before another fresh review. This archives the previous result in the journal, retains its findings for reconciliation, excludes its session from reuse, clears the context assessment, and preserves all rounds/calls/budgets. It does not approve source drift, repair code, close findings or reset a completed review. Then assess context and perform a fresh review against the restored or otherwise properly authorized candidate. If a saved independent result is valid, use reconcile instead of replacing it.
