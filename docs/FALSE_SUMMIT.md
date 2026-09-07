# Dark Room — design false-summit

**Product:** Dark Room  
**Author:** Brent Spink (@littletechbird)  
**Locked:** 2026-09-06  
**Status:** Design false-summit locked 2026-09-06 — ready for implementation plan after Brent GO.  
**Scope of this document:** product locks only. Do **not** treat this file as an implementation plan or a license to start the viewer.

This is the **product north star** for Dark Room: a **local document vault** plus a **sealed PDF mini-viewer**. It supersedes older “what is Dark Room *for*” framing in [SPEC.md](../SPEC.md) without deleting that RFC.

---

## What a false-summit is

A false-summit is a **locked destination**, not a climb plan. The decisions below are authoritative product constraints. Implementation, APIs, and UX details that are *not* listed here remain open until an implementation plan is written after Brent GO.

Do **not** implement the sealed viewer from this document.

---

## Product identity

**Name:** Dark Room.

Dark Room is a **separate sibling** from Spend. Do **not** merge the two products, repos, or runtimes. Shared taste or shared author is not a reason to fold vault/viewer work into Spend, or Spend into Dark Room.

Naming alternatives in older docs (Blind Vault, Agent Elements) remain historical. Ship name is **Dark Room**.

---

## Core use case

Hold a **PDF of secrets** (or any other smuggled document) as **ciphertext in a local vault**.

A **human** unlocks and reads it in a **sealed mini-viewer**.

**Agents never receive:**

- pixels from the viewer
- plaintext
- filesystem path to the vault object
- keys, unlock tokens, or capability material

Agents receive only **opaque handles** of the form `dr_sec_<id>`.

A human **may** share or move:

- the **encrypted** blob, or
- a **receive link** (still unreadable to agents)

Sharing never means sharing plaintext, a screenshot, or a path the agent can open.

---

## Language (authoritative)

| Term | Meaning |
| --- | --- |
| **in the light** | Normal local storage any agent could read (Downloads, Desktop, USB, chat attachments, agent-visible temp). |
| **burnt** | Once plaintext existed in the light, that copy is burnt. Dark Room does not un-burn it. |
| **vault** | Local ciphertext store. Unreadable as plaintext to agents. |
| **smuggle** | True ingress: content enters the vault with **no plaintext spool** in the light. |
| **tainted convenience** | Browse-from-Downloads / USB import. Allowed as a convenience path; it is **not** true ingress. The light copy stays burnt. |
| **sealed mini-viewer** | Capture-excluded, in-process PDF surface. Humans see plaintext. Agents see none of it. |
| **opaque handle** | `dr_sec_<id>` — safe for agents, logs, and tickets. Not a path, not a key, not ciphertext. |

### Ingress

- **True ingress = smuggle** into the vault (mail “Open in Dark Room”, share sheet, receive link) with **no plaintext spool**.
- Browse-from-Downloads / USB is **tainted convenience only**. Prefer smuggle.

---

## Format lock

**All smuggled content flattens to PDF in the vault**, including images.

- One vault object type for readable documents: **PDF**.
- **One PDF viewer path** across desktop, laptop, iPhone, and Android.
- **Excel is still out** of v1 (no spreadsheet surface, no Excel-in-the-vault exception).

This lock exists so every device shares a single sealed decoder/viewer, not a zoo of document apps.

---

## Viewer UX (product lock, not a build ticket)

The viewer is a **sealed mini-viewer**:

- **In-process decoders only.** Never shell out to Windows Photos, Preview, Chrome, or any system PDF/image app.
- **Visible rotate.**
- **Pinch / ctrl-scroll zoom.**
- **Many tabs.** Desktop: hotkey + scroll to cycle tabs.
- **Light annotate:** highlight (color / size) and width-growing text blocks.
- Annotate **saves stay in the vault only** (ciphertext). Annotations do not spill into the light.

The viewer is the only place plaintext pixels are allowed to exist, and only for the human, and only inside a capture-excluded process.

---

## Copy lock

The viewer shows plaintext to the **human only**.

- **No plaintext clipboard.**
- “Copy” and share mean **ciphertext export** or a **receive link**.
- There is no “copy text for the agent” convenience. If an agent needs to *refer* to a vault object, it gets a handle.

---

## Import default (light → vault)

When a human imports from the light (tainted convenience):

- **Leave the original in the light.**
- **Copy** into the vault (do not consume/move/delete the light file as the default).
- The original **stays burnt**. Vaulting it does not cleanse the light copy.

Prefer the **smuggle** path so plaintext never hits the light at all.

---

## Unlock v1

**Device-bound unlock:**

- Windows Hello / machine-local key (platform equivalents on other OSes).
- Success mints a **short-lived local capability / session token** that the **sealed viewer** may use.
- **Optional PIN on every open** is **deferred** (not v1).

**Bots never receive** the session token, the machine key, or the filesystem path.

Unlock is a human-to-viewer ceremony. It is not an agent tool.

---

## Crypto

- **Everything in the vault is encrypted at rest.**
- Plaintext exists only in **capture-excluded viewer process memory**.
- Agents get **opaque handles** only (`dr_sec_<id>`).
- Encrypted blobs and receive links remain ciphertext in transit. Agents may move those bytes; they must not be able to read them.

Soft policy (“please don’t read this folder”) is **not** a vault. The store must be **unreadable as plaintext** to agents even if they list files or exfiltrate the directory.

Prototype crypto in this repo (Fernet + machine-local key file) is a spike, not the v1 bar. The product lock is: encrypted at rest, plaintext only in the sealed viewer, handles only for agents.

---

## Agent contract (unchanged shape, new object)

Agents may:

- hold and pass `dr_sec_<id>`
- see non-secret metadata (label, created time, revoked, *not* path or plaintext)
- help a human *point at* a vault object (“open the tax PDF handle”)

Agents must never:

- receive pixels, OCR, or frames from the sealed viewer
- receive plaintext, keys, session tokens, or filesystem paths
- open the vault object in a system viewer or “in the light” preview
- copy plaintext to clipboard, chat, argv, or tool output

The older fill/submit/egress resolver in [SPEC.md](../SPEC.md) remains a **credential** story. This false-summit’s object is a **document**. Do not silently reuse fill-sim as a PDF viewer.

---

## Anti-jobs / non-goals for v1

Not in v1:

- A full VM or isolated OS
- Multi-tenant cloud KMS
- Excel / spreadsheet viewing or editing
- Plaintext clipboard convenience
- Soft “don’t read this folder” policy as the security boundary
- Merging Dark Room into Spend (or Spend into Dark Room)
- Implementing the sealed viewer from this document alone

v1 **is**: local encrypted vault + device-bound unlock + sealed in-process PDF viewer + handle-only agent surface + ciphertext-only share.

---

## Relationship to SPEC.md

[SPEC.md](../SPEC.md) is the **older, credential-fill oriented** RFC: capture-excluded modal, local vault, opaque handles, resolve-at-fill/egress. Keep it. Do not delete or silently rewrite it.

| Document | Role |
| --- | --- |
| **This file** (`docs/FALSE_SUMMIT.md`) | Newer **document-vault + sealed PDF viewer** product north star. Authoritative for *what Dark Room is now*. |
| **SPEC.md** | Older **credential-fill** design + mapping to the current Python prototype. Still valid for handle/vault/capture-exclude mechanics. |
| **PROPOSAL.md** | One-page ask to agent-runtime owners (handles + capture-excluded modal). |
| **CAPTURE_NOTES.md** | OS exclude-from-capture (modal/viewer window only). |

Shared primitives that survive both stories:

- opaque handles `dr_sec_<id>`
- local vault; agents never see plaintext
- capture exclusion of the Dark Room surface only (not a global screenshot kill)
- machine-local key material; no multi-tenant cloud KMS in v1

What this false-summit **changes**:

- Primary object: **smuggled PDF** (not a typed password/API key as the headline use case)
- Primary human surface: **sealed PDF mini-viewer** (not only a secret-entry modal)
- Share: **ciphertext blob / receive link**, never plaintext clipboard

Prototype code in `darkroom/` still matches SPEC more than this document. That gap is expected until an implementation plan is approved.

---

## Ready-for-plan gate

**Status:** Design false-summit locked 2026-09-06 — ready for implementation plan after Brent GO.

After GO, write an implementation plan. Until then: no viewer, no new vault object type, no smuggle pipeline in code.
