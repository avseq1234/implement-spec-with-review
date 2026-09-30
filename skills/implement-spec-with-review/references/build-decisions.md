# Accepted build decisions

Source: user's attached full requirements plus this conversation, 2026-09-26/27 Asia/Taipei.

- Python 3.11+ standard-library runner; name implement-spec-with-review. Source under /Users/weihongda/projects/choreshandling/tools/implement-spec-with-review; install under /Users/weihongda/.codex/skills/implement-spec-with-review.
- Fake CLI tests for both adapters; real Codex validation now. Claude remains explicitly untested. User explicitly selected this in the clarification response.
- Real smoke primary gpt-5.6-sol medium, reviewer gpt-5.6-sol high, fallback gpt-5.6-sol xhigh. These are smoke settings, not future defaults.
- Isolated Python Git fixture, tasks 1.1 scalar input validation and 1.2 dependent batch processing. Negative control cases can be injected for validation, clearly disclosed.
- CLI timeout 600 seconds; total active 5400 seconds; at most 30 calls; infrastructure retry 1; heartbeat 5 seconds. User wait measured separately. No dollar hard cap promised.
- Context policy checkpoint-resume, unknown capacity disclosed, checkpoint and reread on session changes. Existing budgets never reset.
- User amendment: keep existing code, never claim after-the-fact tests were test-first, but do not pause to ask solely about that deviation. Existing source is a valid modification baseline. New behavior still aims for TDD.
- User explicitly approved structural checks, scenario exercises and independent subagent evaluation for SKILL.md/prompts. Schema acceptance/rejection behavior remains executable-test covered.
- No push, merge, deployment, global model setting changes, or implicit installation of Claude.

These decisions apply to creating/testing this skill. Future project runs independently collect roles and approve their own preflight plan.

## User's decisive replies (verbatim)

> 第6點 ok，照你的建議
>
> 第7點: 保留原有程式碼，不把事後補測試說成 test-first，但不用停下來詢問我如何處理，已存在的專案程式碼本來就可以作為修改基礎，不會只因它早於這次測試而被判定違規

> 前1~5點 依據你的建議處理

Clarification selections:

> 採用：先驗證 Codex，Claude 保留未實測標示

> 同意此驗證方式

The final reply refers to structural checks, scenario exercises and independent subagent evaluation for SKILL.md/prompts, while schema acceptance/rejection behavior remains programmatically tested.
