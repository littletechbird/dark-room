# CAPTURE_NOTES: OS exclude-from-capture for Dark Room

**Product decision:** OS exclude applies to the **Dark Room modal window
only** — not a global screenshot kill for the agent host. Host redaction
(`darkroom.redact` + geometry JSON) remains **defense-in-depth**, especially
on Linux where portable OS exclude is unavailable.

**Rule:** even with perfect capture exclusion, plaintext must never enter
model context via tools, transcripts, or agent-readable files.

## CaptureShield (wired)

`darkroom.capture.CaptureShield`:

- Context manager / `enter(window_id)` / `exit()`
- Tracks HWND / NSWindow / XID for restore on `exit()`
- `status()` → `{active, supported, engaged, system, mechanism, note, python}`
- `engaged` is True only when the last `enter()` successfully engaged OS APIs

```python
from darkroom.capture import CaptureShield

shield = CaptureShield()
shield.enter(tk_root)   # Tk root, HWND, or NSWindow
print(shield.status())
shield.exit()
```

CLI: `python -m darkroom.cli shield-status`

Modal stub wires this on map/visible and shows:

- `OS exclude: ENGAGED` when the binding succeeds
- `OS exclude: UNAVAILABLE (linux stub — use host Electron setContentProtection)` on Linux

## Production host path (preferred)

Electron / Chromium hosts (Grok Bot, Cursor) SHOULD call:

```js
darkRoomWindow.setContentProtection(true) // Dark Room BrowserWindow only
```

See [examples/electron-host-sketch.md](examples/electron-host-sketch.md).
This maps to real OS APIs on Windows and macOS for that window alone.

## Windows

### Primary API

```c
// winuser.h
BOOL SetWindowDisplayAffinity(HWND hWnd, DWORD dwAffinity);

#define WDA_NONE                  0x00000000
#define WDA_EXCLUDEFROMCAPTURE    0x00000011  // Win10 2004+
```

`CaptureShield` binding (ctypes):

1. Resolve HWND from Tk via `wm_frame()` / `winfo_id()`, then climb with
   `user32.GetParent` to the top-level frame (Tk’s `winfo_id()` alone is often wrong).
2. `SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)` → `supported`/`engaged` True on success.
3. On `exit()`: restore `WDA_NONE`.

### Notes

- Excludes the window from most screenshot/capture APIs used by apps.
- Does not stop kernel-mode or specialized capture drivers.
- Pair with not mirroring the field into other HWNDs that remain capturable.
- Prefer Electron `setContentProtection(true)` when the host owns the HWND.

### Optional hardening

- Secure Desktop (like UAC) for entry of extremely sensitive material.
- Disable clipboard redirect into agent-observed clips during modal.

## macOS

### Window sharing (optional pyobjc)

```objc
window.sharingType = NSWindowSharingNone;  // 0
```

`CaptureShield` tries `AppKit` via pyobjc if installed; if missing, returns
`False` with a clear status note (no hard dependency). Prefer host Electron
`setContentProtection(true)`.

This reduced capture in older sharing APIs. It is **not** a complete defense
against modern **ScreenCaptureKit** pipelines; researchers and vendors have
documented bypass / inconsistency cases. Treat window flags as defense-in-depth,
not a sole control.

### Secure Event Input

Legacy Carbon `EnableSecureEventInput()` / related APIs attempt to shield
keystrokes from other event taps. Modern stacks should verify current
supported equivalents and TCC implications.

### Residual risks

- ScreenCaptureKit bypasses and system status-bar / overlay captures.
- Continuity / sidecar / replaykit edge cases.
- Always assume a determined local process may still image pixels; therefore
  **handle-only agent channels remain mandatory**.

## Linux

### Reality

There is no single cross-desktop “exclude from capture” API.

| Stack | Possible approaches |
| --- | --- |
| X11 | Limited; compositor/screenshot tools often see all; `_NET_WM_STATE` / XShape do **not** equal capture exclude |
| Wayland + Mutter | Private / exclusive surfaces depend on GNOME version and portals |
| Wayland + KWin | Similar compositor-specific behavior |
| wlroots | Varies by compositor; may need custom protocol |
| Electron host | `setContentProtection(true)` — may still be compositor-dependent |

### Prototype stance

`CaptureShield` on Linux:

- Best-effort: may probe window XID (e.g. via `xprop`); documents that X11
  shape/state hints are **not** capture exclude.
- `supported` stays **False** unless a real mechanism works.
- Status note honestly says UNAVAILABLE and points at Electron
  `setContentProtection` for production Grok Bot / Cursor hosts.
- Still useful: stdin mint, masked `fill-sim`, origin checks, audit, geometry redaction.

## Plug-in sequence for a real host (Cursor / Grok Bot)

1. Agent host detects need for secret entry (`need_credential` tool).
2. Host opens Dark Room `BrowserWindow` with `setContentProtection(true)`.
3. User enters secret locally; vault returns `dr_sec_…` to agent.
4. Agent proceeds with handle only.
5. At HTTP/browser fill, host resolver expands handle inside non-logged path.
6. Host never attaches plaintext to tool result payloads.
7. If OS exclude unavailable (Linux): redact modal bounds from geometry before vision.

## Testing capture exclusion (manual)

- Windows: Xbox Game Bar / Snipping Tool / agent screenshot — Dark Room
  HWND should be blank or omitted when affinity set.
- macOS: compare `screencapture` vs ScreenCaptureKit sample apps; document
  failures honestly in release notes.
- Linux: expect UNAVAILABLE; record compositor name; degrade to redaction +
  handle-only protocol.

## Modal geometry + host redaction pipeline

The Tkinter stub (`darkroom.modal_stub`) writes:

```json
{"x": 120, "y": 120, "w": 480, "h": 280}
```

to `/tmp/darkroom-geometry.json` (override with `DARKROOM_GEOMETRY_PATH`) on every
move/resize. A host agent runtime SHOULD:

1. Grab the desktop frame as usual.
2. Read the geometry file (if present and fresh).
3. Run `darkroom.redact.redact_file(shot, geometry, out)` — black rectangle.
4. Only then hand the frame to vision / OCR / model tools.

CLI:

```bash
python -m darkroom.redact /tmp/shot.png -g /tmp/darkroom-geometry.json -o /tmp/shot-redacted.png
```

### Drag / resize / always-on-top

| Behavior | Stub | Production |
| --- | --- | --- |
| Drag via title bar | yes | yes |
| Resize via window edges | yes (Tk) | yes |
| Always-on-top | default on (`--no-topmost` to disable) | optional policy |
| OS exclude-from-capture | Win/macOS bindings; Linux UNAVAILABLE | Electron `setContentProtection` on modal only |
| Geometry publish | yes | yes (or privileged IPC) |

### Residual risks (redaction path)

- Stale geometry if the window moves between capture and redact.
- Multi-monitor / HiDPI coordinate mismatches.
- Compositor shadows / animations outside the reported HWND bounds.
- Attacker reading the secret via non-screenshot channels (argv, a11y, files).

Redaction is **defense-in-depth**, not a substitute for OS exclusion when the
OS provides it. On Linux CI boxes, expect **raw screenshot FAIL** and
**redaction sim PASS** — see `attacks/ATTACKS.md`.

## Summary

| OS | CaptureShield | Production path |
| --- | --- | --- |
| Windows | ctypes `WDA_EXCLUDEFROMCAPTURE` | same, or Electron `setContentProtection` |
| macOS | optional pyobjc `sharingType=None` | Electron `setContentProtection` (+ SCK threat notes) |
| Linux | honest UNAVAILABLE stub | Electron + compositor; redaction fallback |

Capture exclusion is necessary but not sufficient. The **vault handle boundary**
is the load-bearing control for agent threat models.
