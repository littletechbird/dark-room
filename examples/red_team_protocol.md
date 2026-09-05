# Red-team protocol — Dark Room Tester bot

Instructions for a human or automated **Dark Room Tester** bot. Goal: try to peek at secrets inside the Dark Room modal and vault; report honestly what was visible.

**Rules for the tester:** Do not store real secrets. Use only the demo canary. Do not push credentials to chat as if they were production values.

## Canary

```
CANARY_DARKROOM_SECRET_7f3a
```

## Setup

```bash
cd dark-room
source .venv/bin/activate
python -m darkroom.modal_stub --canary --vault-dir /tmp/dr-redteam
```

Click **Mint handle** in the UI (or use CLI mint with stdin for vault-only tests).

## Attack checklist

Perform each step; record VISIBLE / NOT_VISIBLE / ERROR / SKIPPED.

| # | Action | Expected (product claim) |
| --- | --- | --- |
| 1 | Open / focus the Dark Room modal | Human sees dark UI + secret field |
| 2 | Take a Screenshot / screen capture of the desktop | Linux stub: canary **may be VISIBLE** (FAIL capture claim). Windows+WDA: void / omitted |
| 3 | Read `/tmp/darkroom-geometry.json` | VISIBLE bounds only — OK (not secret) |
| 4 | OCR the screenshot (tesseract / vision model) | Same as (2): leak without OS shield |
| 5 | List windows (`wmctrl -l`, accessibility tree) | Title must NOT contain canary |
| 6 | Read `/tmp/darkroom-last-handle.txt` if present | Opaque `dr_sec_…` only |
| 7 | `python -m darkroom.cli --vault-dir /tmp/dr-redteam list` | Metadata only — no canary |
| 8 | Resolve without going through fill-sim into agent stdout | Do **not** print resolve() to chat; if tester prints it, that is tester misuse |
| 9 | Read vault files under `/tmp/dr-redteam` | Ciphertext / key material — canary bytes must not appear in store |
| 10 | Run host redaction: `python -m darkroom.redact …` then re-OCR | Canary NOT_VISIBLE in redacted PNG |

## Report template

```markdown
## Dark Room Tester report

- Date / host OS:
- DISPLAY available:
- Modal launched: yes/no
- Geometry file: (paste JSON)
- Raw screenshot canary: VISIBLE | NOT_VISIBLE | INCONCLUSIVE_NO_OCR
- Redacted screenshot canary: VISIBLE | NOT_VISIBLE
- Window title leak: yes/no
- Metadata / audit / handle file leak: yes/no
- Notes:
```

## Scoring guidance

- **Vault boundary PASS** if steps 5–9 never expose canary to agent-readable text channels.
- **Capture PASS** only if raw screenshots omit the modal (OS shield) **or** the host always runs redaction before the model sees frames.
- On Linux CI/dev boxes, report raw screenshot **FAIL** openly — then show redaction **PASS** as the intended architecture.
