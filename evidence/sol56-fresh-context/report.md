# SOL 5.6 fresh-context skill evaluation

Status: final repaired version passed fresh-context SOL 5.6 orchestration and independent observer checks in attempt 4.

## Method

Each attempt uses gpt-5.6-sol/high as orchestration subagent with fork_turns=none. Only the installed skill path, new synthetic fixture's raw specs, user-approved roles/budgets/gates and authorization boundaries are supplied. The observer does not coach the orchestrator during execution. The external Codex roles are gpt-5.6-sol medium/high/xhigh for primary/reviewer/fallback. Orchestration is tested through a fresh collaboration subagent, not a separately opened desktop chat.

Scope: two sequential Python library tasks, then final integration review; timeout 600 seconds/call, 30 calls, 5400 active seconds, one infrastructure retry. Unknown context/cost data remain unknown. Claude remains untested against a real CLI.

## Attempt 1 — blocked, not passed

Fresh SOL agent `/root/sol56_fresh_orchestrator_v1`, fixture `/private/tmp/implement-spec-smoke-2maxuqp0`. It read specifications, verified model settings, measured baseline, recorded the user's confirmation and bound distinct task managers. The first external invocation failed when the host sandbox denied mandatory ps process inspection. No provider output, session or source changes were produced. SOL honestly retained WAITING_FOR_USER and did not claim completion.

Recorded use: 1/30 calls, 0.224781 active seconds. Task 1.1 WAITING_FOR_USER; task 1.2 and final READY; zero effective review rounds. Archive: attempt-01-fixture and attempt-01-preflight. Exact initial skill hashes: attempt-01.json.

## Repair between attempts

Preflight now probes the actual runner environment's process inspection capability. The runner checks before starting a provider or charging a call and rejects nonzero/empty process identity results. Documentation explains ordinary host-tool approval within existing user authorization, passing the verified execution environment to managers, and respecting denied approvals. External CLI sandbox/approval flags are unchanged.

A behavioral regression failed before the repair because provider launch occurred before the permission check (repair-red.txt), then passed (repair-green.txt). Complete suite: 94 test executions passed, including inherited invariant cases; not 94 unique requirements. Skill structure validator passed. Source and installed copies were hash-equal (repair-installation.json).

## Attempt 2

Fresh SOL agent `/root/sol56_fresh_orchestrator_v2`, fixture `/private/tmp/implement-spec-smoke-59296sn_`. Exact tested skill hashes: attempt-02.json. The observer acceptance suite observer_check.py is not disclosed to the tested agent. Final acceptance, evidence audit and result will be appended after execution.

Attempt 2 was interrupted by an orchestration-model usage limit after task 1.1 verification and task 1.2 implementation/gates. On the user’s explicit continue, the same orchestrator was resumed with its existing context and persisted run. The observer supplied no implementation or review guidance. This interruption is part of the measured attempt, not a new fresh-context attempt.

## Attempt 2 completed and independently audited

All original tasks and final gate VERIFIED, one effective round each, 9 calls / 537.244 active seconds. Observer checked 59 checksummed journal frames, all 10 test-output hashes, six distinct manager identities, explicit reviewer-session reuse for reconciliation, task ordering, candidate/gate/review alignment, original specification hashes, true RED-before-GREEN chronology and unchanged installed skill hashes. The 10-test fixture suite and 7 undisclosed acceptance checks passed. See observer-audit.json, observer-acceptance.txt and observer-fixture-suite.txt. Archive: attempt-02-fixture.

The manager-created temporary input contaminated one task 1.2 review snapshot. SOL independently removed only its own file, checkpointed the event, discarded the contaminated session and reran a fresh review on the original candidate; the invalid review remains in the journal and counted in call use but not an effective round. Observer gave no repair guidance.

Retrospective defects: make_fixture.py --help created a repository, aggregate status lagged implementation state, and a pending independent review could be replaced without explicit invalidation while unaccounted source drift was admitted. Four reproduced behavioral failures were repaired; added invalidation tests confirm findings, budgets, history and abandoned session identity are retained. Complete suite: 100 executions passed. New invalidation is an explicit journaled runner operation, not a source-drift approval or round reset. These final changes require the next fresh-context test before final delivery.

## Attempt 3 — incomplete after usage-limit interruption

The final repaired version began from another fresh SOL 5.6/high context. Task 1.1 implementation, meaningful RED/GREEN and full gate passed; aggregate REVIEWING state was correct. An orchestration usage limit interrupted it before completion. On the next user continuation (2026-09-30), the temporary fixture/run no longer existed. The observer does not reconstruct missing evidence or claim this attempt passed. A separately numbered attempt 4 uses a persistent workspace directory to survive interruptions.

## Attempt 4 — final repaired version passed

The orchestrator was gpt-5.6-sol/high, started with fork_turns=none and only raw specifications, installed skill and approved settings. Its repository and canonical run are now persistent under attempt-04-workspace. Primary CLI used medium, reviewer high; configured fallback xhigh was not needed. Six distinct management agents were created across tasks 1.1, 1.2 and final integration.

All three states are VERIFIED, one effective review each. Both implementation tasks have meaningful RED-before-GREEN evidence. The full fixture suite passed 9 tests; the observer's undisclosed acceptance checks passed all 7. Final integration's extra primary CLI check made no source changes. Changes are limited to lib.py and its two new test files; no push, commit, merge or deployment occurred.

Usage: 10/30 external CLI calls, 1105.874632/5400 recorded active seconds. One task 1.2 review call failed with the provider message “Selected model is at capacity” (exit 1, not timeout). The approved single infrastructure retry succeeded using the same configured model/effort; the failed call earned zero review credit. A later orchestration usage-limit interruption occurred before final review; the user's continue resumed the same context/run. There was no observer guidance on implementation or review and no candidate contamination in this attempt.

Observer audit passed: 62 checksummed journal frames and their state projection, 10 test-output hashes, unchanged original specification hashes, unchanged installed skill throughout the attempt, candidate/gate/review consistency, acceptance coverage, RED/GREEN chronology, manager identities, reviewer session continuity and finite budgets. Configuration remained identical to the initial run configuration. Current context occupancy and cost remain unavailable; cumulative tokens are not treated as context occupancy.

Evidence:
- attempt-04.json: exact starting skill hashes and interruption record.
- attempt-04-observer-audit.json: machine-readable independent audit.
- attempt-04-observer-acceptance.txt: 7 observer tests passed.
- attempt-04-observer-suite.txt: 9 fixture tests passed.
- attempt-04-workspace/.spec-runs/20260930T010011+0800-2e60c700: canonical discussion.md, decisions.md, summary.md, reports, raw CLI output and capture receipts.

## Interpretation and remaining limits

SOL 5.6 successfully orchestrated this small synthetic, sequential spec-to-implementation workflow from a fresh starting context using the repaired installed skill. The result includes explicit user-authorized resumption after an account usage limit, rather than an uninterrupted run. This does not establish reliability for arbitrary project complexity. Claude is still simulated-only. Real defect-driven fallback convergence, high-risk extra reviews and the five-round stopping path were not triggered here; their previously documented simulated coverage remains distinct. No unknown usage value is reported as zero or inferred context capacity.

Attempts 1–3 are preserved honestly: first environment failure, second successful workflow with subsequently repaired defects, third incomplete run lost from temporary storage after a quota interruption. Final runtime/workflow code is the version exercised by attempt 4; any final documentation-only update records these results without changing execution behavior.

The SOL orchestrator’s final retrospective confirmed all stages VERIFIED and reported no concrete remaining skill defect. It also reran the installed 100-test suite: restricted-sandbox ps failures were expected environment restrictions; the unchanged suite passed in the required host process-inspection environment. No additional runtime or workflow changes were needed. Final installation source/hash equality is recorded in final-installation.json.
