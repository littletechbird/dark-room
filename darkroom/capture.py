"""
CaptureShield — stub interface for OS exclude-from-capture.

On a production host this would wrap:
  - Windows: SetWindowDisplayAffinity(..., WDA_EXCLUDEFROMCAPTURE)
  - macOS:   NSWindow.sharingType = .none / ScreenCaptureKit exclusions
  - Linux:   compositor-dependent; typically a no-op stub

This prototype is Linux-first and provides a documented no-op with
hooks for future platform bindings. See CAPTURE_NOTES.md.
"""

from __future__ import annotations

import platform
import sys
from typing import Any, Optional


class CaptureShield:
    """
    Modal / window exclusion from AI screenshot and OS capture pipelines.

    CRITICAL: Even with capture exclusion, plaintext must never be
    piped into model context via tools, clipboard monitors shared with
    agents, or log aggregation.
    """

    def __init__(self) -> None:
        self._active = False
        self._system = platform.system()

    @property
    def active(self) -> bool:
        return self._active

    @property
    def supported(self) -> bool:
        # Prototype: no real OS binding yet
        return False

    def enter(self, window_id: Optional[Any] = None) -> bool:
        """
        Enter dark-room modal (exclude from capture).

        Returns True if OS exclusion engaged; False if no-op stub.
        ``window_id`` is platform-specific (HWND, NSWindow*, XID, …).
        """
        self._active = True
        if self._system == "Windows":
            # TODO: ctypes windll.user32.SetWindowDisplayAffinity(
            #     hwnd, WDA_EXCLUDEFROMCAPTURE=0x11)
            return False
        if self._system == "Darwin":
            # TODO: set NSWindow.sharingType = NSWindowSharingNone
            # Note: ScreenCaptureKit bypasses exist; see CAPTURE_NOTES.md
            return False
        # Linux / other: compositor plugins may exist; default no-op
        _ = window_id
        return False

    def exit(self) -> None:
        """Leave dark-room modal; restore normal capture eligibility."""
        self._active = False
        if self._system == "Windows":
            # TODO: SetWindowDisplayAffinity(hwnd, WDA_NONE=0x00)
            pass
        elif self._system == "Darwin":
            # TODO: restore NSWindow.sharingType
            pass

    def __enter__(self) -> "CaptureShield":
        self.enter()
        return self

    def __exit__(self, *exc: object) -> None:
        self.exit()

    def status(self) -> dict[str, Any]:
        return {
            "active": self._active,
            "supported": self.supported,
            "system": self._system,
            "python": sys.version.split()[0],
            "note": "prototype stub — OS exclusion not wired",
        }
