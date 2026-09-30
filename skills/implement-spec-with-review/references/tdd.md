# Adopted TDD rules

Pinned source: https://github.com/obra/superpowers/blob/5bf4e78011075bcfc0dc295f0724994cd123ee71/skills/test-driven-development/SKILL.md

Commit: `5bf4e78011075bcfc0dc295f0724994cd123ee71`
SHA-256 of fetched source: `64b03fce4aee5a97a93160cea8111f3ba13a17b7c001db4bd5836d67fd10705d`

Adopt behavior-first regression/acceptance tests, observed meaningful RED, minimal implementation, GREEN and optional refactor with full suite preserved. An import/syntax/environment error is not meaningful RED. Tests assert real observable behavior; mocks are reserved for unavoidable external boundaries such as deterministic fake CLI failures. Do not assert merely that a mock was called or that generated instruction wording matches.

User-approved precedence over upstream deletion rules: keep original code. Existing code is a valid modification baseline. If tests were added after implementation, explicitly record test-after and continue full verification; do not stop to ask solely about the process deviation, and do not pretend it was TDD. Never delete user code for compliance. New behavior should still follow test-first. Other genuine uncertainty is not waived.

Documentation/config/generated-code exceptions need initial user confirmation and an explicit alternative validation method. For building this skill, the user approved structural checks, realistic exercises and independent subagent evaluation for SKILL.md/prompts. Schema behavior still receives executable acceptance/rejection tests. All project tests must run at delivery; named baseline failures are disclosed and only specifically approved exceptions may pass. Do not weaken assertions, delete necessary tests, skip failures or silently substitute a single file for the full suite.

Before designing nontrivial tests, consult the pinned upstream companion writing-good-tests.md when relevant. If upstream guidance conflicts with these accepted user amendments, the amendments govern; unresolved new conflicts are questions for the user.
