# Dark Room — research notes (2026-09-05)

## Verdict
Feasible. Combine host capture-exclusion + secure input + local vault opaque handles + fill/egress resolver. Plaintext must never enter model observation channels.

## Prior art (selected)
- Stripe Elements / single-use tokens
- Privacy.com virtual cards
- WebAuthn / Credential Management API
- macOS EnableSecureEventInput
- Windows SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)
- Android Private Space
- Cursor Cloud Agent Runtime Secrets [REDACTED]
- Infisical credential brokering for AI agents

## Remaining threats
Post-fill DOM/length/timing leakage; macOS ScreenCaptureKit fragility; network echo; wrong-origin handle use; shoulder surfing.

## Naming alts
Blind Vault, Agent Elements, Cloak Modal, Redacted Room, Handle Fill
