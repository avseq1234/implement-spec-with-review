# Validation record

Build decisions: `build-decisions.md`. Machine-readable result and test outputs: `../validation/`.

## Automated behavioral coverage

Full suite currently executes 100 unittest cases (including inherited invariant suites repeated under different fixture setups). These are not 100 distinct requirements. Run from skill root:

```sh
python3 -m unittest discover -s tests -v
```

OS process-identity tests require permission to read `ps`. If a sandbox denies that read, run under an approved environment that permits process inspection; never disable CLI sandbox permissions to hide the limitation.

| Requested behavior | Executable evidence |
|---|---|
| Independent role model/effort; provider mapping; unsupported effort refusal | test_primitives + test_adapters |
| Preserve this-run settings; no implicit previous config reuse | PrimitiveTests role resolution cases |
| Per-task manager binding/replacement; original task ID/path | EngineTests manager/original-id cases; real fixture manager events |
| Explicit resume; provider/session/role binding; no latest shortcut | AdapterTests resume; EngineTests wrong-session/cross-role cases |
| Round 3 fresh; second-round fallback; five-round stop | EngineTests round3/five-round/fallback cases |
| High-risk additional independent review counts within cap | EngineTests high-risk reload regression |
| Context/manager replacement preserves rounds | EngineTests manager replacement and wait/answer cases |
| ACCEPT/REBUT; reviewer-only verification; stable/reopened findings | EngineTests implementation/rebuttal/regression/downgrade cases |
| NEEDS_USER_INPUT; affected work pause; decisions persistence and recovery | PrimitiveTests question validation; EngineTests wait/answer; RuntimeTests fake question |
| Current candidate required; untracked/dirty/modes included; logs excluded | PrimitiveTests snapshots; EngineTests stale review; RuntimeTests invalidation/log cases |
| Timeout/nonzero/malformed output cannot pass or consume effective round | AdapterTests invalid output; RuntimeTests process failure cases |
| No simultaneous writer; uncertain writes not blindly rerun | RuntimeTests writer/recovery; RecoveryTests live sidecar |
| Child timeout cleanup; preserve existing input directories | RecoveryTests descendant timeout; RuntimeTests preserve-inputs |
| Tracked ignored files and deleted source supported in reviewer copy | RecoveryTests isolation case |
| Per-round evidence and reports survive reloading | EngineTests high-risk persistence + runtime fixture logs |
| Missing valid RED provenance: actual full gates and truthful test-after, no pause solely for provenance | RuntimeTests missing-test-first policy case |
| Task passes but final not passed => overall incomplete | EngineTests final-gate case + independent forward test |

Fake CLI cases exercise real OS processes and runner behavior, not a provider model. Claude argv/JSON contract is simulated only.

## Independent verification

Two independently delegated evaluations were used:
- Control-plane reviewer independently reproduced five state/session/ledger defects. Regression tests were added and all five were independently reverified fixed.
- Runtime inspection found file-preservation, descendant timeout, crash-sidecar and reviewer-copy deletion issues. They were repaired and covered by regression tests.
- Skill forward evaluator followed documented commands in its own `/private/tmp/skill-forward-w77fbeaw` fixture: init, baseline, approve, bind, context, implement, gates, fresh review, reconcile. It observed task VERIFIED/round 1 while overall remained READY because final was incomplete; test-after was honestly disclosed; no confirmed usability defect remained. Evidence path is retained in the build report. It did not test real providers or full multi-task lifecycle.

## TDD honesty

The skill's development included test-first primitive/adapter behavior and regressions, and test-after runner integration/recovery checks. Initial primitive placeholder failures included shape errors, so those errors are not counted as valid TDD RED. The user expressly authorized continuing with truthful test-after disclosure. No existing user source was deleted for TDD. The real implementation fixture has separate observed RED/GREEN receipts; do not infer their status from the build process.

## Provider and platform limits

- Codex real fixture and protocol results are recorded in `../validation/build-summary.json` with exact run paths and counts when finished.
- Claude CLI was unavailable and was not installed under the user's chosen scope. Its adapter is fake-tested and MUST NOT be described as real-verified.
- Runner targets the current POSIX/macOS environment and a Git repository. No Windows execution claim.
- Schemas/templates enforce observable contracts; they cannot prove a model understood a requirement. Required independent review and user clarification remain part of the skill.
- Multiple-image resume, symlink materialization and unverified CLI versions require preflight clarification/support verification, not silent approximations.
- Token/cost/current-context values unavailable from a provider remain null. Per-invocation usage is retained; no unsupported aggregate billing claim is made.

## Completed real run

Tasks 1.1, 1.2 and final gate VERIFIED, one effective round each; full fixture suite 8/8. Calls 12, recorded active seconds 515.13. Durable evidence: `/Users/weihongda/projects/choreshandling/output/implement-spec-with-review-validation/fixture/.spec-runs/20260927T000412+0800-086903e0`. See `/Users/weihongda/projects/choreshandling/output/implement-spec-with-review-validation/report.md`. No real defect required fallback; fresh fallback protocol and simulated convergence are explicitly distinguished.

## Fresh-context SOL orchestration validation (2026-09-29)

Fresh `gpt-5.6-sol/high` orchestration was exercised using collaboration agents with `fork_turns=none`, raw fixture specifications and user-approved settings. The first attempt stopped honestly at a host process-inspection permission failure. The probe/runner preflight and host-tool permission documentation were repaired; a second fresh attempt completed tasks 1.1, 1.2 and final integration, one effective review each, with 9 real CLI calls and 537.244 recorded active seconds. It resumed the same context after a model-usage limit and user continuation. Both tasks retained genuine RED/GREEN evidence; 10 fixture tests and 7 undisclosed observer checks passed.

The second attempt independently detected and recovered a manager-created temporary file contaminating a candidate snapshot. Its retrospective identified additional defects in fixture --help side effects, aggregate status after implementation, and pending independent-review replacement/source-drift admission. These now have behavioral regression tests, explicit review invalidation with preserved findings/session history/budgets, and a passing 100-test suite. The final repaired version passed a further fresh-context run (attempt 4): tasks 1.1, 1.2 and final VERIFIED, one effective round each; 9 fixture tests and 7 undisclosed observer tests passed. Ten real CLI calls included one provider-capacity failure and its approved successful retry, using 1105.875 recorded active seconds. The same orchestration context resumed after a user-authorized usage-limit interruption. The observer verified 62 journal frames, 10 test-output hashes, six distinct manager identities, session continuity and snapshot alignment. Attempt 3 remains incomplete because its temporary fixture disappeared after a quota interruption. Attempt 4 uses persistent storage. No runtime/workflow changes followed this passing run; this paragraph only records the outcome.

Durable per-attempt hashes, unsuccessful attempts, repairs and observer evidence: `/Users/weihongda/projects/choreshandling/output/implement-spec-with-review-validation/sol56-fresh-context/report.md`. This is a small synthetic workflow test, not a guarantee for arbitrary repositories or models. Claude and untriggered fallback/high-risk/fifth-round paths retain their existing validation limits.
