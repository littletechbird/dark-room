# Dark Room attack suite

Honest pass/fail tests for the two product claims:

1. **Vault boundary** — agents only see opaque handles; metadata/audit/store never leak plaintext.
2. **Capture exclusion** — screenshots / AI vision should not see modal contents.

## How to run

```bash
cd dark-room
source .venv/bin/activate   # or: python3 -m venv .venv && pip install -r requirements.txt
python attacks/run_all.py   # prints scorecard JSON; exit 0 iff automated PASS
# or individually:
pytest tests/test_vault.py attacks/test_vault_boundary.py attacks/test_redaction_sim.py -q
```

Manual / bot live peek: [attack_live_screenshot.md](attack_live_screenshot.md)  
Red-team protocol for a tester bot: [../examples/red_team_protocol.md](../examples/red_team_protocol.md)

## What PASS / FAIL means

| Test | Expected | Meaning |
| --- | --- | --- |
| `vault_unit` / `vault_boundary_exfil` | **PASS** | Canary not in metadata, audit, ciphertext file, handle status file, or Dark Room env |
| `redaction_sim` | **PASS** | Synthetic frame with canary pattern in modal rect → `darkroom.redact` → no canary pixels left |
| Live screenshot on Linux (manual) | **FAIL / leak** (without OS shield) | Proves why host `WDA_EXCLUDEFROMCAPTURE` / compositor integration matters |
| Live screenshot + host redaction | **PASS** (architecture) | Host blacks out geometry from `/tmp/darkroom-geometry.json` before model sees frame |

## Design of the two capture tests

### A) REAL screenshot attack (expect FAIL on Linux)

Open `python -m darkroom.modal_stub --canary`, take a root/`import` screenshot, inspect pixels or OCR. Without OS exclusion the canary is visible. **Do not mark the product PASS on Linux stub alone.**

### B) SIMULATED host redaction (expect PASS)

`attacks/test_redaction_sim.py` builds a composite image, applies `darkroom.redact.redact_image`, asserts the unique red canary pattern is fully black inside the modal rectangle. This is the intended Cursor/Grok host pipeline when OS capture APIs are missing or as defense-in-depth.

## Canary

```
CANARY_DARKROOM_SECRET_7f3a
```

Demo-only. Never store real secrets in the prototype vault.
