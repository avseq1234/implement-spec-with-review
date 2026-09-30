# Decisions

## Decision 1 · 2026-09-28T17:08:38.318147+00:00
採用以上設定，完成 preflight 無新問題後執行

Confirmed scope: orchestration SOL 5.6/high; external Codex CLI primary gpt-5.6-sol/medium, reviewer gpt-5.6-sol/high, fallback gpt-5.6-sol/xhigh. Per-call timeout 600 seconds, max 30 calls, active runtime 5400 seconds, infrastructure retry 1, heartbeat 5 seconds. Context checkpoint-resume with unknown occupancy kept unknown. Original tasks execute sequentially as 1.1 then 1.2, followed by final integration. Both tasks ordinary risk; no baseline or TDD exceptions; no splitting or reordering. Full gate is python3 -m unittest discover -s tests -v using the resolved interpreter. No extra lint/typecheck configured. Fresh management pair per task and final. Existing code is a valid starting point; preserve it and disclose test-after truthfully without asking solely for that deviation. New behavior uses TDD. No push, merge, deployment, or real project changes.

Scope: ["1.1", "1.2", "_final"]
Questions: ["Initial plan, roles, gates, budgets, exceptions and session policy"]
