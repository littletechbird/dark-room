"""
CaptureShield — OS-level exclude-from-capture for the Dark Room modal window.

Product decision: exclude **only the Dark Room modal window** from OS/app
capture (not a global screenshot kill). Host redaction remains defense-in-depth.

Platform bindings:
  - Windows: ctypes user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
  - macOS:   optional pyobjc AppKit NSWindow.sharingType = NSWindowSharingNone
  - Linux:   best-effort X11 hints that do NOT equal capture exclude; prefer
             Electron BrowserWindow.setContentProtection(true) in the host

See CAPTURE_NOTES.md and examples/electron-host-sketch.md.
"""

from __future__ import annotations

import platform
import sys
from typing import Any, Optional


# Windows display affinity constants (winuser.h)
WDA_NONE = 0x00000000
WDA_EXCLUDEFROMCAPTURE = 0x00000011  # Win10 2004+


def _resolve_hwnd_windows(window_id: Any) -> Optional[int]:
    """
    Resolve a usable HWND from a Tk window id or raw HWND.

    On Windows, Tk's ``root.winfo_id()`` is often *not* the top-level HWND
    that SetWindowDisplayAffinity expects. Prefer climbing with GetParent,
    or use ``int(root.wm_frame(), 16)`` when the caller passes a frame hex.
    """
    if window_id is None:
        return None

    import ctypes

    user32 = ctypes.windll.user32  # type: ignore[attr-defined]

    hwnd: Optional[int] = None
    if isinstance(window_id, int):
        hwnd = window_id
    elif isinstance(window_id, str):
        s = window_id.strip()
        try:
            hwnd = int(s, 16) if s.lower().startswith("0x") or all(
                c in "0123456789abcdefABCDEF" for c in s
            ) and not s.isdigit() else int(s)
        except ValueError:
            return None
    else:
        # Tk widget: try wm_frame() then winfo_id()
        try:
            frame = window_id.wm_frame()  # type: ignore[union-attr]
            if frame:
                hwnd = int(frame, 16)
        except Exception:
            hwnd = None
        if hwnd is None:
            try:
                hwnd = int(window_id.winfo_id())  # type: ignore[union-attr]
            except Exception:
                return None

    if not hwnd:
        return None

    # Climb to the top-level parent HWND (Tk embeds under a frame).
    GetParent = user32.GetParent
    seen: set[int] = set()
    cur = int(hwnd)
    while cur and cur not in seen:
        seen.add(cur)
        parent = int(GetParent(cur) or 0)
        if not parent:
            break
        cur = parent
    return cur


class CaptureShield:
    """
    Modal / window exclusion from AI screenshot and OS capture pipelines.

    CRITICAL: Even with capture exclusion, plaintext must never be
    piped into model context via tools, clipboard monitors shared with
    agents, or log aggregation.
    """

    def __init__(self) -> None:
        self._active = False
        self._engaged = False
        self._supported = False
        self._system = platform.system()
        self._mechanism = "none"
        self._note = ""
        self._window_ref: Any = None  # HWND int, NSWindow, or XID
        self._prev_sharing_type: Any = None
        self._refresh_static_note()

    def _refresh_static_note(self) -> None:
        if self._system == "Windows":
            self._note = (
                "Windows: SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE=0x11) "
                "ready; call enter(hwnd) when the modal is mapped"
            )
            self._mechanism = "SetWindowDisplayAffinity"
        elif self._system == "Darwin":
            self._note = (
                "macOS: try pyobjc AppKit NSWindow.sharingType=NSWindowSharingNone; "
                "prefer Electron setContentProtection(true) in host. "
                "ScreenCaptureKit residual risk — see CAPTURE_NOTES.md"
            )
            self._mechanism = "NSWindow.sharingType"
        else:
            self._note = (
                "Linux: no portable OS exclude-from-capture. "
                "X11 _NET_WM_STATE / XShape hints are NOT capture exclude. "
                "Production Grok Bot / Cursor host should use Electron "
                "win.setContentProtection(true) for the Dark Room BrowserWindow."
            )
            self._mechanism = "linux-stub"

    @property
    def active(self) -> bool:
        return self._active

    @property
    def supported(self) -> bool:
        return self._supported

    @property
    def engaged(self) -> bool:
        """True if the last enter() successfully engaged OS exclusion."""
        return self._engaged

    def enter(self, window_id: Optional[Any] = None) -> bool:
        """
        Enter dark-room modal (exclude from capture).

        Returns True if OS exclusion engaged; False if unavailable / no-op.
        ``window_id`` is platform-specific (HWND, Tk root, NSWindow*, XID, …).
        """
        self._active = True
        self._engaged = False
        self._window_ref = None

        if self._system == "Windows":
            return self._enter_windows(window_id)
        if self._system == "Darwin":
            return self._enter_darwin(window_id)
        return self._enter_linux(window_id)

    def _enter_windows(self, window_id: Optional[Any]) -> bool:
        self._mechanism = "SetWindowDisplayAffinity"
        try:
            import ctypes
        except ImportError:
            self._supported = False
            self._note = "Windows: ctypes unavailable"
            return False

        hwnd = _resolve_hwnd_windows(window_id)
        if not hwnd:
            self._supported = False
            self._note = (
                "Windows: no HWND — pass Tk root (uses wm_frame/GetParent climb) "
                "or raw HWND to enter()"
            )
            return False

        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        ok = bool(user32.SetWindowDisplayAffinity(int(hwnd), WDA_EXCLUDEFROMCAPTURE))
        if ok:
            self._window_ref = int(hwnd)
            self._supported = True
            self._engaged = True
            self._note = (
                f"Windows: WDA_EXCLUDEFROMCAPTURE engaged on HWND={hwnd:#x}"
            )
            return True

        err = ctypes.get_last_error()
        self._supported = False
        self._engaged = False
        self._note = (
            f"Windows: SetWindowDisplayAffinity failed "
            f"(HWND={hwnd:#x}, GetLastError={err})"
        )
        return False

    def _enter_darwin(self, window_id: Optional[Any]) -> bool:
        self._mechanism = "NSWindow.sharingType"
        # Prefer documenting Electron host path; optional pyobjc binding.
        try:
            import AppKit  # type: ignore[import-untyped]
        except ImportError:
            self._supported = False
            self._engaged = False
            self._note = (
                "macOS: pyobjc/AppKit not installed — OS exclude unavailable from "
                "this Python process. Host should call Electron "
                "BrowserWindow.setContentProtection(true) for Dark Room. "
                "Optional: pip install pyobjc-framework-Cocoa"
            )
            return False

        ns_window = None
        if window_id is not None:
            # Accept an NSWindow instance directly, or an object with .window()
            if hasattr(window_id, "setSharingType_"):
                ns_window = window_id
            elif hasattr(window_id, "window"):
                try:
                    ns_window = window_id.window()
                except Exception:
                    ns_window = None

        if ns_window is None:
            # Fall back to key / main window if caller did not pass one
            try:
                app = AppKit.NSApplication.sharedApplication()
                ns_window = app.keyWindow() or app.mainWindow()
            except Exception:
                ns_window = None

        if ns_window is None:
            self._supported = False
            self._engaged = False
            self._note = (
                "macOS: AppKit present but no NSWindow — pass NSWindow to enter(), "
                "or use Electron setContentProtection(true)"
            )
            return False

        try:
            # NSWindowSharingNone = 0
            self._prev_sharing_type = ns_window.sharingType()
            ns_window.setSharingType_(0)
            self._window_ref = ns_window
            self._supported = True
            self._engaged = True
            self._note = (
                "macOS: NSWindow.sharingType=NSWindowSharingNone engaged. "
                "Not a complete ScreenCaptureKit defense — prefer host "
                "Electron setContentProtection(true); see CAPTURE_NOTES.md"
            )
            return True
        except Exception as exc:
            self._supported = False
            self._engaged = False
            self._note = f"macOS: setSharingType_ failed: {exc}"
            return False

    def _enter_linux(self, window_id: Optional[Any]) -> bool:
        """
        Best-effort X11 property / shape hints. These do NOT equal OS capture
        exclude. ``supported`` stays False unless a real mechanism works.
        """
        self._mechanism = "linux-stub"
        self._supported = False
        self._engaged = False
        xid = None
        if window_id is not None:
            try:
                if hasattr(window_id, "winfo_id"):
                    xid = int(window_id.winfo_id())
                else:
                    xid = int(window_id)
            except (TypeError, ValueError):
                xid = None
        self._window_ref = xid

        # Attempt soft X11 annotations (honest: not capture exclude).
        hint_note = ""
        if xid:
            try:
                # Document-only attempt via xprop if available; do not claim success.
                import shutil
                import subprocess

                if shutil.which("xprop"):
                    # Touch _NET_WM_STATE with a non-standard note atom is useless;
                    # we only probe that the window exists.
                    subprocess.run(
                        ["xprop", "-id", hex(xid), "WM_CLASS"],
                        capture_output=True,
                        timeout=2,
                        check=False,
                    )
                    hint_note = (
                        f" XID={xid:#x} probed via xprop (not exclude). "
                        "XShape/_NET_WM_STATE do NOT block screenshots."
                    )
            except Exception:
                hint_note = " X11 probe skipped."

        self._note = (
            "OS exclude: UNAVAILABLE (linux stub — use host Electron "
            "setContentProtection)." + hint_note
        )
        return False

    def exit(self) -> None:
        """Leave dark-room modal; restore normal capture eligibility."""
        if self._system == "Windows" and self._window_ref is not None:
            try:
                import ctypes

                user32 = ctypes.windll.user32  # type: ignore[attr-defined]
                user32.SetWindowDisplayAffinity(int(self._window_ref), WDA_NONE)
            except Exception:
                pass
        elif self._system == "Darwin" and self._window_ref is not None:
            try:
                prev = (
                    self._prev_sharing_type
                    if self._prev_sharing_type is not None
                    else 1  # NSWindowSharingReadOnly typical default
                )
                self._window_ref.setSharingType_(prev)
            except Exception:
                pass

        self._active = False
        self._engaged = False
        self._window_ref = None
        self._prev_sharing_type = None
        # Keep _supported / _mechanism reflecting platform capability after exit
        if self._system == "Windows":
            # supported was True only if enter succeeded; leave as-is for status
            self._note = "Windows: affinity restored to WDA_NONE (inactive)"
        elif self._system == "Darwin":
            self._note = "macOS: sharingType restored (inactive)"
        else:
            self._refresh_static_note()

    def __enter__(self) -> "CaptureShield":
        self.enter()
        return self

    def __exit__(self, *exc: object) -> None:
        self.exit()

    def status(self) -> dict[str, Any]:
        return {
            "active": self._active,
            "supported": self._supported,
            "engaged": self._engaged,
            "system": self._system,
            "mechanism": self._mechanism,
            "note": self._note,
            "python": sys.version.split()[0],
        }
