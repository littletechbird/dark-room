# Dark Room evidence summary (2026-09-05)

## Automated (Linux box)
- pytest: PASS (vault + capture mocks + redaction sim)
- attack suite automated: PASS
- Linux OS exclude: UNAVAILABLE (expected)

## Live red-team (Dark Room Tester bot)
- Raw screenshot of Tk modal: canary VISIBLE → capture FAIL without OS exclude
- Host redaction of modal bounds: canary NOT_VISIBLE → PASS
- Vault/handle/metadata/window title: no plaintext canary → PASS

## Windows Spinkatron OS exclude
- `SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)` → setOk=True
- GDI `CopyFromScreen` WITH exclude: lime canary pixels = 0
- GDI control WITHOUT exclude: lime canary pixels = 1602
- `PrintWindow` WITH exclude: lime canary pixels = 0

## Fill / agent-visible transcript
- `mint` / `list` / `fill-sim` stdout: canary CLEAN (masked `****` only)
- Privileged form file receives secret (resolver target) — must not be echoed to model/chat
- Vault on-disk store: no plaintext canary bytes

## Ask for Grok Bot host
- Dark Room BrowserWindow: Electron `setContentProtection(true)` / Win WDA / macOS sharingType
- Modal-only exclude (not global screenshot kill)
- Handle-only tool APIs; never return plaintext in tool results
- Redaction as defense-in-depth if a capture path bypasses OS exclude

Repo: https://github.com/littletechbird/dark-room
Thread: https://x.com/littletechbird/status/2096254752892051589
