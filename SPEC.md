# SPEC: Dark Room (RFC-style)

**Title:** Dark Room — inverse sandbox for agent-watched desktops  
**Author:** @littletechbird  
**Status:** Draft / reference  
**Intended audience:** Cursor / Grok Bot creators, desktop-agent runtime owners  
**Companion:** working prototype in this repository (`darkroom/`)

Naming alternatives: **Blind Vault**, **Agent Elements**.

---

## 1. Abstract

Dark Room is a design for keeping secrets out of AI agent context while still allowing agents to *orchestrate* authenticated actions on a watched desktop. It combines:

1. A **capture-excluded host modal** (OS-level exclude-from-capture / secure input).
2. A **local vault** that mints **opaque handles** and resolves them only at controlled fill/submit/egress.
3. **Allowlisted origins**, **audit logs**, and **revoke**.

Agents never receive plaintext. They receive handles of the form `dr_sec_<id>`.

---

## 2. Motivation

Modern coding and computer-use agents observe:

- Screenshots / video frames
- Accessibility trees / DOM
- Terminal scrollback and tool stdout
- Sometimes synthetic input streams

Any secret that appears on those channels is effectively disclosed to the model provider and to logs. Existing mitigations (user discipline, redaction heuristics, “don’t paste secrets”) fail under automation pressure.

We need a **primitive**: the agent can say “use credential X on origin Y” without ever seeing X.

---

## 3. Goals and non-goals

### Goals

- G1: Plaintext never enters model context (chat, vision, tool transcripts).
- G2: Stable, opaque handle format for agent APIs: `dr_sec_<id>`.
- G3: Resolve only at fill/submit/egress in a privileged local process.
- G4: Origin allowlists to reduce confused-deputy / wrong-form fills.
- G5: Audit mint/resolve/revoke without logging plaintext.
- G6: Clear OS integration path for exclude-from-capture (Win/macOS/Linux).
- G7: Draggable/resizable Dark Room modal + host redaction fallback when OS shield absent.

### Non-goals

- N1: Multi-tenant cloud KMS (local machine vault is the prototype scope).
- N2: Protecting secrets from malware that already has user keychain/disk access.
- N3: Eliminating all side channels (length, timing) in v0.
- N4: Replacing OS password managers; Dark Room *composes* with them.

---

## 4. Architecture

### 4.1 Components

| Component | Role |
| --- | --- |
| **Dark Room UI / modal** | Capture-excluded surface for human secret entry |
| **Vault** | Encrypt, mint handle, resolve, revoke, list metadata |
| **Resolver** | Expands handle at fill/submit; never prints plaintext to agent channels |
| **CaptureShield** | OS exclude-from-capture binding |
| **Audit log** | Append-only events without plaintext |
| **Agent runtime** | Speaks handles only; may call fill/submit APIs |

### 4.2 Data flow (steps)

1. User opens Dark Room modal (`CaptureShield.enter`).
2. User types or pastes secret; UI never mirrors into agent screenshot buffers.
3. Vault generates `handle = "dr_sec_" || urlsafe(random)`.
4. Vault encrypts secret with machine-local key; persists ciphertext + metadata.
5. Vault returns handle (+ label, origins) to agent-visible channel.
6. Agent schedules action: `fill(handle, field, origin)` or `egress(handle, destination)`.
7. Resolver checks handle exists, not revoked, origin allowlisted.
8. Resolver decrypts in-process; writes to form field / HTTP header / IPC.
9. Resolver zeros buffers where feasible; audit `resolve_ok`.
10. Optional: auto-revoke or TTL after single use.

### 4.3 Trust boundaries

```
[Agent model + logs]  --handles only-->  [Agent host runtime]
                                              |
                                              v
                                         [Resolver]
                                              |
                    plaintext (local memory / OS IPC only)
                                              |
                                              v
                                         [Target app / network]
```

Disk ciphertext + machine key are inside the user trust boundary, outside the model trust boundary.

---

## 5. Token / handle format

```
dr_sec_<id>
```

- Prefix: literal `dr_sec_` (Dark Room secret).
- `<id>`: cryptographically random, URL-safe, >= 128 bits entropy (prototype uses `secrets.token_urlsafe(18)` ≈ 144 bits).
- Handles are **not** self-describing ciphertexts; they are lookup keys into the local vault.
- Handles are safe to log, put in tickets, and show to models.
- Handles MUST NOT embed the secret or a recoverable encryption of it.

### 5.1 Metadata (agent-visible)

- `handle`
- `label` (human string, no secret)
- `created_at`
- `revoked` (bool)
- `allowlisted_origins` (list of strings; empty means “unrestricted” in prototype — production SHOULD require explicit origins)

### 5.2 Non-visible

- plaintext
- ciphertext
- machine key

---

## 6. Allowlisted origins

Each handle MAY carry `allowlisted_origins`.

On `resolve(handle, origin)`:

- If allowlist non-empty and `origin` not in list → deny (`OriginNotAllowed`), audit `resolve_origin_denied`.
- If allowlist empty → allow (prototype convenience; SPEC recommends production default deny-unless-listed).

Origins SHOULD be stable strings:

- Web: `https://checkout.example`
- Native: `app://com.example.client`
- CLI egress: `cli://gh` or similar namespaced ids

Wrong-origin handle use is a first-class threat (stolen handle pasted into attacker form).

---

## 7. Audit log rules

- Append-only local file (prototype: `~/.darkroom/audit.log`).
- Allowed fields: timestamp, event name, handle, label, origin, error class.
- **Forbidden fields:** `secret`, `plaintext`, `password`, raw token bodies, ciphertext.
- Events: `key_created`, `mint`, `resolve_ok`, `resolve_miss`, `resolve_revoked`, `resolve_origin_denied`, `revoke`.
- Production SHOULD support tamper-evident hashing / remote ship to SIEM without secret fields.

---

## 8. Cryptography (prototype)

- Algorithm: Fernet (AES-128-CBC + HMAC-SHA256) via `cryptography` package.
- Key: machine-local file `~/.darkroom/machine.key`, mode `0600`.
- Store: single encrypted JSON blob `vault.enc.json`.
- Revoke: set `revoked=true` and wipe ciphertext field.

Production upgrades (out of scope for spike): OS keychain/DPAPI for key wrap, per-secret keys, AEAD with AAD binding handle+origins, secure enclave.

---

## 9. Platform notes

### 9.1 Windows

- `SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)` for Dark Room HWND (wired in `CaptureShield` via ctypes; Tk HWND via `wm_frame`/`GetParent`).
- Consider Secure Desktop for ultra-sensitive entry (UAC-like).
- Affinity is not perfect against kernel or driver capture; document residual risk.

### 9.2 macOS

- `NSWindow.sharingType = .none` (optional pyobjc in `CaptureShield`; prefer Electron `setContentProtection`).
- **ScreenCaptureKit** and some system paths have bypassed older exclusions; treat as arms race — see CAPTURE_NOTES.md.
- Secure Event Input for keystrokes (legacy Carbon / modern equivalents).
- Prefer not relying on window exclusion alone; combine with never putting plaintext in agent pipes.

### 9.3 Linux

- No universal exclude-from-capture API across X11/Wayland compositors.
- Wayland: compositor protocols / private surfaces vary (Mutter, KWin, wlroots).
- `CaptureShield` on Linux is an **honest UNAVAILABLE** stub (`supported=False`);
  X11 `_NET_WM_STATE` / XShape do **not** equal capture exclude.
- Production Linux/desktop hosts SHOULD use Electron
  `BrowserWindow.setContentProtection(true)` on the **Dark Room window only**,
  plus geometry redaction as defense-in-depth.
- Still valuable without OS exclude: stdin mint + masked fill + handle-only protocol.

Details: [CAPTURE_NOTES.md](CAPTURE_NOTES.md), [examples/electron-host-sketch.md](examples/electron-host-sketch.md).

**Product decision:** OS exclude of the **modal window only** (not global screenshot kill).
Redaction remains defense-in-depth.

---

## 10. Agent integration contract

### MUST

- Pass secrets into vault via stdin/TTY/secure IPC — never argv.
- Show agents only handles + metadata.
- On fill, write plaintext only to target sink; stdout/UI confirmation masked (`****`).
- Enforce origin checks when provided.
- Comment and review any path that could echo plaintext into model context.

### MUST NOT

- Echo resolve() return value into chat tools.
- Read filled form files back into the agent transcript.
- Log ciphertext or plaintext in audit.
- Accept `--secret` CLI flags.

### MAY

- Single-use handles (auto-revoke after one successful resolve).
- TTL expiry.
- Broker to OS keychain instead of file vault.

---

## 11. Threat model

| Threat | Mitigation | Residual |
| --- | --- | --- |
| Screenshot of typed secret | CaptureShield + modal | OS bypasses (esp. macOS SCK) |
| Secret in argv / chat | stdin mint; handle-only agent API | User error / rogue tools |
| Metadata API leak | list returns meta only; tests assert | Bugs |
| Wrong-origin fill | allowlist | Empty allowlist in prototype |
| Post-fill DOM scrape | short-lived fields; prefer direct egress | Hard on open web |
| Length side channel | masked confirmations hide length | Timing still leaks |
| Stolen vault file | disk encryption + key perms | Malware with user access |
| Handle guessing | 128+ bit ids | N/A if entropy held |

---

## 12. Prototype mapping

| SPEC item | Code |
| --- | --- |
| Vault mint/resolve/revoke/list | `darkroom/vault.py` |
| CLI | `darkroom/cli.py` |
| CaptureShield (OS bindings) | `darkroom/capture.py` |
| Draggable/resizable modal stub | `darkroom/modal_stub.py` |
| Host redaction (geometry → blackout) | `darkroom/redact.py` |
| Electron host sketch | `examples/electron-host-sketch.md` |
| Agent narrative | `examples/agent_flow.md` |
| Red-team protocol | `examples/red_team_protocol.md` |
| Vault tests | `tests/test_vault.py` |
| Attack / capture suite | `attacks/` |

---

## 12.1 Modal UI requirements (stub + production)

The Dark Room surface MUST:

- Be **draggable** (custom title bar or equivalent) and **resizable**.
- Optionally stay **always-on-top** while open.
- Allow the human to enter / view a **demo secret** (text; image placeholder OK).
- Stay “inside” for the user (normal desktop window) while remaining out of agent vision channels.
- Publish **geometry** `{x,y,w,h}` to a host-readable status file (prototype: `/tmp/darkroom-geometry.json`) on move/resize for redaction pipelines.
- Expose **Mint handle** that calls the vault; show only `dr_sec_…` — never print plaintext to stdout or window titles.

Production MUST bind **CaptureShield** / Electron `setContentProtection(true)` on the **Dark Room modal only** (not a global screenshot kill). Linux hosts without a real OS shield MUST run **frame redaction** using published geometry before any model sees pixels. Redaction remains defense-in-depth on all platforms.

## 12.2 Capture exclusion + residual risks

| Layer | Requirement | Residual risk |
| --- | --- | --- |
| OS exclude-from-capture | Win `WDA_EXCLUDEFROMCAPTURE`; macOS strongest available sharing flags; Linux compositor-specific | Kernel/driver capture; macOS SCK bypasses |
| Host redaction pipeline | Black out modal bounds from geometry JSON before vision/OCR | Wrong/stale geometry; multi-monitor coords; race before update |
| Vault handle boundary | Agents only receive handles; no resolve to transcripts | User/tester misuse; post-fill DOM scrape |
| Geometry status file | Bounds only — not secret | Reveals that a Dark Room is open and where |

Honest test policy: on Linux **without** OS shield, a raw screenshot attack is expected to **FAIL** (leak). The simulated redaction suite MUST **PASS**. See `attacks/ATTACKS.md`.

---

## 13. Security disclosure note

This is a **reference/prototype**. Report design issues via the repository issue tracker. Do not file “I decrypted my own local vault” as a vulnerability — physical/local access is in-scope for the user, out-of-scope for the model isolation claim.

---

## 14. Changelog

- **0.3.0** — Real OS-level CaptureShield (Win ctypes / macOS pyobjc optional / Linux honest stub); Electron host sketch; modal OS-exclude status line.
- **0.2.0** — Modal stub (drag/resize), host redaction helper, attack suite + honest Linux capture notes.
- **0.1.0** — Initial public reference SPEC + Python prototype.
