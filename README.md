# dark-room

**Subtitle:** inverse sandbox for agent-watched desktops

Public reference proposal and working prototype from [@littletechbird](https://github.com/littletechbird).

> **Status:** reference design + local prototype. **Not production security software.** Do not store real high-value secrets here without further hardening, review, and OS capture integration.

Full design: [SPEC.md](SPEC.md). One-page ask: [PROPOSAL.md](PROPOSAL.md). OS capture notes: [CAPTURE_NOTES.md](CAPTURE_NOTES.md).

## Pitch

AI desktop agents (Cursor, Grok Bot, computer-use runners) see screenshots, DOM, and often keystrokes. Today, pasting an API key or password into a watched session can put that secret into model context forever.

**Dark Room** flips the sandbox: instead of trying to hide the whole desktop from the agent, it provides a **host-OS modal excluded from AI screenshot/input channels**, plus a **local vault** that mints **opaque handles**. Agents only ever see handles like `dr_sec_<id>`. A privileged local resolver expands handle to secret **only at fill / submit / egress** — never into chat, tool logs, or screenshots.

Think Stripe Elements or passkeys, but for agent-watched desktops: the model orchestrates *where* to fill; the Dark Room holds *what* to fill.

## Problem

| Failure mode | Why it hurts |
| --- | --- |
| Secret in screenshot / ScreenCaptureKit | Lands in vision context and logs |
| Secret in argv / chat / tool output | Lands in transcripts and training-adjacent stores |
| Post-fill DOM / clipboard leakage | Secret re-enters agent-visible surfaces |
| Length / timing side channels | Handle ops leak secret size or content class |
| Wrong-origin handle use | Stolen or confused handle fills attacker form |

Prior art we draw on: Stripe Elements, WebAuthn/passkeys, Windows `WDA_EXCLUDEFROMCAPTURE`, macOS Secure Event Input, Cursor Runtime Secrets, Infisical-style credential brokering.

## How it works

1. **Human (or trusted local UI) enters the secret** inside a capture-excluded Dark Room modal (see CaptureShield).
2. **Vault mints** an opaque handle `dr_sec_<id>`, encrypts the secret with a machine-local key, stores ciphertext on disk.
3. **Agent receives only the handle** (and optional label / origin allowlist metadata).
4. At **fill / submit / egress**, a local resolver expands handle to plaintext in-process and writes it into the target field or egress channel — **without echoing plaintext to agent-visible stdout**.
5. **Audit log** records mint / resolve / revoke / origin denials — never plaintext.
6. **Revoke** marks the handle dead and wipes ciphertext.

```
  Human / TTY          Vault (local)           Agent                 Egress
  -----------          -------------           -----                 ------
  secret ──stdin──►    encrypt + mint
                       handle ────────────────► sees dr_sec_…
                       resolve(handle) ◄─────── fill-sim / submit
                       plaintext ──local only──────────────► form / API
```

## Threat model (summary)

**In scope (prototype + SPEC):** agent-visible screenshots and tool transcripts; accidental argv leakage; metadata APIs leaking plaintext; revoke; origin allowlists.

**Partially addressed:** OS exclude-from-capture (stubbed; see CAPTURE_NOTES.md); audit trail.

**Out of scope / known gaps:** post-fill DOM scrapers; sophisticated length/timing channels; macOS ScreenCaptureKit bypasses; malware with disk key access; multi-user shared hosts; production key management (HSM/KMS).

## Naming alternatives

- **Blind Vault**
- **Agent Elements** (Stripe Elements analogy)

## Quick start

```bash
cd dark-room
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Help
python -m darkroom.cli --help

# Mint (secret from stdin — never argv)
printf 'demo-secret' | python -m darkroom.cli --vault-dir /tmp/dr-demo mint --label demo

# List metadata only
python -m darkroom.cli --vault-dir /tmp/dr-demo list

# Fill simulation (stdout masked; secret written only to form file)
python -m darkroom.cli --vault-dir /tmp/dr-demo fill-sim \
  --handle dr_sec_… --field password --form-file /tmp/fake_form.txt

# Tests
python -m pytest tests/ attacks/ -q
python attacks/run_all.py
# or: python -m unittest discover -s tests -v
```

Agent-oriented walkthrough: [examples/agent_flow.md](examples/agent_flow.md).

## Package layout

```
darkroom/          vault, CLI, CaptureShield, modal stub, redact
attacks/           red-team suite + scorecard (run_all.py)
examples/          agent flow + red_team_protocol
tests/             metadata secrecy, wrong handle, revoke
SPEC.md            RFC-style design
PROPOSAL.md        SendFeedback / Poteto-facing ask
CAPTURE_NOTES.md   Win / macOS / Linux capture exclusion + redaction
```


## Attack suite

Automated boundary + capture-architecture tests live under `attacks/`.

```bash
python attacks/run_all.py   # JSON scorecard; exit 0 if automated tests PASS
```

| Check | Expected |
| --- | --- |
| Vault unit + file-exfil boundary | **PASS** — canary never in metadata/audit/store |
| Redaction simulation | **PASS** — canary pattern blacked out via `darkroom.redact` |
| Live screenshot on Linux (manual) | **FAIL / leak** without OS shield — documents why host integration matters |

Details: [attacks/ATTACKS.md](attacks/ATTACKS.md). Tester bot playbook: [examples/red_team_protocol.md](examples/red_team_protocol.md).

### Modal stub (drag / resize)

```bash
python -m darkroom.modal_stub --canary --vault-dir /tmp/dr-demo
# geometry published to /tmp/darkroom-geometry.json
# Mint handle → opaque dr_sec_… only (secret never printed)
```

### Host redaction helper

```bash
python -m darkroom.redact /tmp/shot.png -g /tmp/darkroom-geometry.json -o /tmp/shot-redacted.png
```

## License

MIT — see [LICENSE](LICENSE).

## Disclaimer

This repository is a **public reference proposal** for Cursor / Grok Bot creators and the broader agent-desktop community. It is intentionally small, auditable, and incomplete. Treat it as a design spike, not a vault product.
