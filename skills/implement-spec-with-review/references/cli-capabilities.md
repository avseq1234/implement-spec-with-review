# Capability verification

Verified locally at build preflight: Codex CLI `0.158.0-alpha.2.1`, ChatGPT login. `exec`, explicit `exec resume SESSION_ID`, stdin `-`, `--json`, `--output-schema`, `--output-last-message`, model and config flags were confirmed in local help. The locally verified --no-daemon flag keeps external Codex work out of the shared background daemon so process cancellation belongs to the runner. Both new and resume invocations inherit the root sandbox/approval flags. No permission-bypass flags are used. `-a never` denies operations requiring additional approval instead of granting them; managers surface the blocker.

Local models_cache.json lists `gpt-5.6-sol` efforts low, medium, high, xhigh, max, ultra. The build smoke chooses medium/high/xhigh independently. This cache is evidence about the current installation, not a permanent universal catalog. Refresh capability evidence each project launch. Official API documentation can differ from the installed Codex CLI's surface; do not replace the selected CLI setting on that basis.

Sources read during build:
- https://developers.openai.com/api/docs/models/gpt-5.6-sol
- https://learn.chatgpt.com/docs/non-interactive-mode
- https://code.claude.com/docs/en/cli-reference
- https://code.claude.com/docs/en/model-config

Claude CLI was not found on PATH or usual local locations. The adapter follows official noninteractive `-p`, JSON/schema, model/effort and explicit resume documentation, but is FAKE-TESTED ONLY. Do not mark Claude locally usable until its actual version/help/auth, model/effort behavior, structured output, resume and permission policy pass a real isolated test. Claude can cap/downgrade effort or inherit provider fallbacks; reject unverified capability settings and inspect actual result behavior. No alias such as sonnet may silently select a different model.

For diagrams, verify the actual provider can consume them. Codex local help supports image attachments on both initial and resume calls. Raster attachment paths alone in a text prompt are not proof of image reading. Unsupported formats/providers require a user-approved readable representation. Never claim diagrams were understood merely because a file was accessible.

Run `python3 scripts/probe.py` to emit read-only local capability evidence. It never installs providers or prints authentication secrets. Authentication status and account model access still require the appropriate provider checks/smoke.

## Host permissions before provider launch

The runner requires `ps -p PID -o lstart=` for process identity, safe cancellation and recovery. `probe.py` reports `runtime.process_inspection`; a BLOCKED result is an incomplete preflight even when CLI help and login pass. Run the probe and runner under the same host-tool permission environment. The runner also checks its own process identity before launching any CLI or charging a call, and rejects an empty/nonzero process identity result.

When the user already authorized this local fixture/project and real CLI access, use the host tool's ordinary permission request (for example `exec_command` with `sandbox_permissions="require_escalated"` and a specific justification) for the required process inspection, provider connectivity and session persistence. This is a tool approval request, not a new specification decision. Keep the external CLI's configured sandbox and approval flags. Do not remove checks, use bypass flags or seek another route around a denied approval. If auto-review denies the request, inspect the stated reason; retry only with genuinely relevant evidence or a safer scope. Explain any unresolved denial to the user.

Communicate the verified runner execution environment to both management agents; otherwise their default sandbox may differ from the orchestrator's preflight. If a provider already started before a failure, preserve its evidence and apply the recovery rules—never infer that writes are absent or blindly retry. Missing authority, ambiguous recovery choices, and unavailable permission tooling still require user input.
