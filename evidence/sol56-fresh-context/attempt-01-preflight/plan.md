# Confirmed implementation plan

- Source mapping: task 1.1 implements R1/AC1, then task 1.2 implements R2/AC2 and depends on 1.1. `_final` verifies both contracts together. Original IDs and ordering are preserved; no task split or independent work after a block is allowed.
- Observable acceptance: 1.1 covers a positive built-in int, zero, negative int, bool, float, string, None, and another non-int type. 1.2 covers empty and valid built-in lists, a newly allocated ordered result, invalid element exception propagation, non-list input, first-invalid behavior, and input preservation.
- Gate for each task and `_final`: `/Library/Developer/CommandLineTools/usr/bin/python3 -m unittest discover -s tests -v`. There is no separate lint or typecheck tool in this minimal repository.
- TDD: new behavior should produce meaningful RED evidence before implementation and GREEN evidence after it. If implementation precedes tests, label the evidence test-after and still run the full gate; no TDD exception is approved.
- Roles: primary `gpt-5.6-sol/medium`; reviewer `gpt-5.6-sol/high`; fallback `gpt-5.6-sol/xhigh`, all through authenticated Codex CLI 0.158.0-alpha.2.1 with workspace-write or read-only sandbox selected by the runner. No bypass flags.
- Review: fresh round 1, resumed round 2, fresh round 3, at most five effective rounds; fallback is selected for the next fix after unresolved round-2 blockers or failed completion gates. Each original task and `_final` gets a distinct Execution manager and Review manager.
- Limits: 600 seconds per CLI call, 30 calls total, 5400 active seconds total, one infrastructure retry, five-second heartbeat.
- Context: checkpoint-resume; current occupancy and billed tokens remain unknown unless the CLI reports them. Before every invocation, record the bounded relevant read set and resume/fresh decision. Fresh sessions reread the approved documents and current task evidence.
- Baseline: no exceptions. A failing baseline will stop implementation and require a new decision. The run is local under `.spec-runs`; no push, merge, deployment, network feature, or production data access is in scope.
- Risks: the first real provider invocation is the final capability/access check. Any new specification ambiguity, permission failure, unsupported model/effort, or uncertain write becomes `NEEDS_USER_INPUT` with saved evidence.
