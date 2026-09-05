# CAPTURE_NOTES: OS exclude-from-capture for Dark Room

How a real exclude-from-capture layer would plug into Dark Room, and what the
prototype stub does today.

**Rule:** even with perfect capture exclusion, plaintext must never enter
model context via tools, transcripts, or agent-readable files.

## Prototype stub

`darkroom.capture.CaptureShield`:

- Context manager / `enter()` / `exit()`
- `supported` is always `False` in this spike
- **Linux:** intentional no-op (no portable compositor API)
- **Windows / macOS:** commented binding sites; returns `False` until wired

```python
from darkroom.capture import CaptureShield

with CaptureShield():
    # show Dark Room modal; mint secret from TTY
    ...
```

CLI: `python -m darkroom.cli shield-status`

## Windows

### Primary API

```c
// winuser.h
BOOL SetWindowDisplayAffinity(HWND hWnd, DWORD dwAffinity);

#define WDA_NONE                  0x00000000
#define WDA_MONITOR               0x00000001
#define WDA_EXCLUDEFROMCAPTURE    0x00000011  // Win10 2004+
```

Integration sketch:

1. Create Dark Room top-level HWND (borderless modal).
2. `SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)`.
3. Enter secret; mint handle; destroy window.
4. Restore `WDA_NONE` on exit (or destroy HWND).

### Notes

- Excludes the window from most screenshot/capture APIs used by apps.
- Does not stop kernel-mode or specialized capture drivers.
- Pair with not mirroring the field into other HWNDs that remain capturable.
- Python binding: `ctypes.windll.user32.SetWindowDisplayAffinity`.

### Optional hardening

- Secure Desktop (like UAC) for entry of extremely sensitive material.
- Disable clipboard redirect into agent-observed clips during modal.

## macOS

### Historical window sharing

```objc
window.sharingType = NSWindowSharingNone;
```

This reduced capture in older sharing APIs. It is **not** a complete defense
against modern **ScreenCaptureKit** pipelines; researchers and vendors have
documented bypass / inconsistency cases. Treat window flags as defense-in-depth,
not a sole control.

### Secure Event Input

Legacy Carbon `EnableSecureEventInput()` / related APIs attempt to shield
keystrokes from other event taps. Modern stacks should verify current
supported equivalents and TCC implications.

### Integration sketch

1. Present NSPanel / NSWindow for Dark Room.
2. Set strongest available sharing/capture exclusion.
3. Enable secure input while the field is focused.
4. Mint via vault; tear down panel; disable secure input.

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
| X11 | Limited; compositor/screenshot tools often see all; some `_NET` hints ignored |
| Wayland + Mutter | Private / exclusive surfaces depend on GNOME version and portals |
| Wayland + KWin | Similar compositor-specific behavior |
| wlroots | Varies by compositor; may need custom protocol |

### Prototype stance

`CaptureShield` on Linux is a **documented no-op**:

- Still useful: stdin mint, masked `fill-sim`, origin checks, audit.
- Production Linux would negotiate with the active compositor or run the
  Dark Room UI in a nested trusted session (e.g. separate seat / VT) — heavy.

### Suggested future interface

```python
class CaptureShield(Protocol):
    def enter(self, window_id: Any | None = None) -> bool: ...
    def exit(self) -> None: ...
    @property
    def supported(self) -> bool: ...
```

Platform modules:

- `darkroom.capture_win`
- `darkroom.capture_macos`
- `darkroom.capture_linux` (no-op or portal experiment)

## Plug-in sequence for a real host (Cursor / Grok Bot)

1. Agent host detects need for secret entry (`need_credential` tool).
2. Host opens Dark Room UI under CaptureShield (OS binding).
3. User enters secret locally; vault returns `dr_sec_…` to agent.
4. Agent proceeds with handle only.
5. At HTTP/browser fill, host resolver expands handle inside non-logged path.
6. Host never attaches plaintext to tool result payloads.

## Testing capture exclusion (manual)

- Windows: use Xbox Game Bar / Snipping Tool / agent screenshot — Dark Room
  HWND should be blank or omitted when affinity set.
- macOS: compare `screencapture` vs ScreenCaptureKit sample apps; document
  failures honestly in release notes.
- Linux: record compositor name + whether exclusion is available; degrade
  gracefully to handle-only protocol.

## Summary

| OS | Prototype | Production path |
| --- | --- | --- |
| Windows | stub + comments | `WDA_EXCLUDEFROMCAPTURE` |
| macOS | stub + comments | sharingType + secure input + SCK threat notes |
| Linux | no-op | compositor-specific or nested trusted UI |

Capture exclusion is necessary but not sufficient. The **vault handle boundary**
is the load-bearing control for agent threat models.
