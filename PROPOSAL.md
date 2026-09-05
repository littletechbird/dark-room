# Proposal: Dark Room for agent-watched desktops

**From:** Brent Spink (@littletechbird)  
**To:** Cursor / Grok Bot creators (SendFeedback, Poteto-facing)  
**Repo concept:** `dark-room` — inverse sandbox for agent-watched desktops  
**Status:** public reference + working local prototype (not production)

## Five bullets

1. **Problem.** Desktop agents that screenshot and drive UI inevitably ingest secrets typed or pasted into the watched session. Once a key is in model context, revoke is theater.
2. **Idea.** A host-OS **Dark Room** modal excluded from AI capture/input channels, plus a **local vault** that mints opaque handles (`dr_sec_<id>`). Agents orchestrate with handles; a local resolver expands plaintext only at fill/submit/egress.
3. **Prior art.** Stripe Elements, passkeys, Windows `WDA_EXCLUDEFROMCAPTURE`, macOS Secure Event Input, Cursor Runtime Secrets, Infisical-style brokering — Dark Room composes these patterns for *agent* threat models.
4. **Threats we call out.** Post-fill DOM leakage, length/timing side channels, ScreenCaptureKit bypasses, wrong-origin handle use. The SPEC documents these; the prototype proves the handle/metadata boundary.
5. **Ask.** Adopt (or co-design) a Dark Room / Agent Elements primitive in the agent runtime: capture-excluded secret entry, handle-only agent APIs, audited resolve-at-egress, origin allowlists.

## Ask for prototype adoption

Please review [SPEC.md](SPEC.md) and the runnable prototype (`python -m darkroom.cli`). We are asking for:

- Design feedback from Cursor Runtime / secrets owners
- A path to pilot **handle-only** credentials in agent tool APIs
- Guidance on first-class OS capture exclusion in the desktop agent host

We are **not** asking to ship this Python spike as-is. We are asking to treat Dark Room as a named product/RFC direction and to green-light a deeper prototype inside the real agent stack.

Contact / attribution: Brent Spink — GitHub @littletechbird.
