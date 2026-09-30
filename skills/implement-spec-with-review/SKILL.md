---
name: implement-spec-with-review
description: Implement a high-level design and OpenSpec task specification through per-task management subagents and external Codex or Claude CLI sessions, with TDD evidence, bounded review and fallback, resumable logs, and final integration gates. Use for executing an existing implementation spec, not for inventing missing requirements.
---

# Implement spec with review

Use the Codex App agent as orchestrator. Each original task gets one Execution subagent and one Review subagent; they manage external CLI processes through `scripts/runner.py`. Keep those managers through fixes/fallback; create a new pair for the next task. Do not pretend Python can create App subagents. Do not have managers duplicate the CLI's full implementation/review. If subagents are unavailable, ask before substituting direct management.

## Before implementation

Read [workflow](references/workflow.md) and [CLI capabilities](references/cli-capabilities.md). Read every supplied original design, OpenSpec proposal/design/tasks/spec/scenario and diagram, check AGENTS.md and existing changes. Preserve original IDs and ordering. Build requirements → tasks → acceptance → named gates/tests mapping; record document hashes. Do not infer unclear diagram contents.

Every launch collect primary, reviewer and fallback **external CLI** model+effort independently; preserve settings supplied this time, and reuse previous settings only on explicit request. Run `scripts/probe.py` in the intended runner execution environment, including its required process-inspection check. Resolve authorized host-tool permissions as described in [CLI capabilities](references/cli-capabilities.md) before starting a provider. Probe actual local CLI version/help, capability metadata and authentication; verify IDs/efforts instead of translating App labels by guess. No silent model/effort downgrade. Three CLI settings do not select App or manager models.

Present one concrete plan covering mappings, order, gates, risks, exceptions, session/context strategy, finite budgets, baseline failures, log location and unresolved questions. Await user confirmation before implementation. Use [runner protocol](references/runner-protocol.md) to initialize the run and record the actual answer. A preflight policy is not implicit permission to resolve future uncertainties.

## Uncertainty and decisions

Read-only verification is allowed. Remaining ambiguity, missing information, conflicting specs or new authority must produce `NEEDS_USER_INPUT` with question, evidence, options/impacts and affected tasks. Orchestrator asks the user; pause affected work and dependencies. Runner saves the answer in decisions/discussion and includes it in subsequent CLI packets. Never substitute another reviewer's subjective vote for a user decision. Do not ask whether to continue after each task/round.

## Execute and verify

Use the approved runner protocol: bind real manager IDs, assess context, invoke CLI, run gates, review, and reconcile. Keep manager temporary inputs outside the candidate repository. Runner exclusively writes canonical logs. Saved independent reviews must be reconciled or explicitly invalidated through the runner before replacement. Agents may only provide structured results or isolated capture receipts. Fresh reviewer sees specs/current code first; runner saves independent findings before revealing the prior ledger. Round 1 fresh, round 2 resume, round 3 fresh; maximum five effective reviews. Round 2 incomplete gates require fallback for the next fix. High-risk tasks require an additional final-candidate independent review within the same cap. Read [review and recovery rules](references/review-recovery.md) before retries, rebuttals or session replacement.

For new behavior use TDD; consult the pinned [TDD adoption rules](references/tdd.md). Never delete existing user code to satisfy TDD. If implementation preceded tests, preserve it, add meaningful tests, label test-after truthfully and continue verification without asking solely about that deviation. Existing code is a valid starting point. Other ambiguities still require user input.

CLI success alone is not completion. Every task needs matching candidate/review/test evidence, acceptance coverage, no unresolved blocking findings or uncertainty, and all confirmed gates. A changed candidate invalidates related evidence. After all tasks, bind a fresh pair for `_final`, run full integration gates and a fresh selected-reviewer session. Final review has its own five-round cap and second-round fallback rule. When the fifth round blocks, save evidence and ask the user for the next step; do not raise the cap or create new tasks to reset exhausted budgets.

## Recovery and delivery

Resume only an explicit `.spec-runs/<run-id>` through `recover`. Never use last/latest session, concurrently resume one session, or rerun uncertain writes. Save checkpoints at each round/session replacement. Distinguish context occupancy from billed tokens; unknown stays unknown. Re-read original constraints and decisions after compaction. Logs are locally excluded from Git and excluded from snapshots.

Before declaring completion, run `status` and confirm tasks **and final gate** are VERIFIED. Report original IDs/status, changes, acceptance coverage, TDD/test-after and integration results, finding dispositions/rebuttals, decisions, fallback/context/session events, baseline exceptions, limitations, elapsed/available usage, and exact paths to `discussion.md`, `summary.md`, `decisions.md`, and the run directory. No implicit push/merge/deploy.

## Skill validation

Run `python3 -m unittest discover -s tests -v` from this skill directory. For isolated real validation use `scripts/make_fixture.py`; see [validation record](references/validation.md) for measured coverage and remaining provider limitations. The original requested rules and accepted amendments are retained in [requirements](references/user-requirements.txt) and [decisions](references/build-decisions.md).
