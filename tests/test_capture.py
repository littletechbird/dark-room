"""CaptureShield unit tests — status shape + mocked Windows ctypes path.

Does not require a real Windows host to run in CI.
"""

from __future__ import annotations

import sys
import unittest
from typing import Any
from unittest.mock import MagicMock, patch

from darkroom.capture import (
    CaptureShield,
    WDA_EXCLUDEFROMCAPTURE,
    WDA_NONE,
    _resolve_hwnd_windows,
)


STATUS_KEYS = {"active", "supported", "engaged", "system", "mechanism", "note", "python"}


class CaptureShieldStatusTests(unittest.TestCase):
    def test_status_shape_default(self) -> None:
        shield = CaptureShield()
        st = shield.status()
        self.assertEqual(STATUS_KEYS, set(st.keys()))
        self.assertIsInstance(st["active"], bool)
        self.assertIsInstance(st["supported"], bool)
        self.assertIsInstance(st["engaged"], bool)
        self.assertIsInstance(st["system"], str)
        self.assertIsInstance(st["mechanism"], str)
        self.assertIsInstance(st["note"], str)
        self.assertIsInstance(st["python"], str)
        self.assertFalse(st["active"])
        self.assertFalse(st["engaged"])

    def test_linux_enter_unavailable(self) -> None:
        """On Linux (this CI box), enter must not claim OS exclude success."""
        shield = CaptureShield()
        if shield.status()["system"] != "Linux":
            self.skipTest("Linux-specific honest-unavailable check")
        ok = shield.enter(0x1234)
        self.assertFalse(ok)
        st = shield.status()
        self.assertTrue(st["active"])
        self.assertFalse(st["supported"])
        self.assertFalse(st["engaged"])
        self.assertIn("UNAVAILABLE", st["note"])
        self.assertIn("Electron", st["note"])
        shield.exit()
        self.assertFalse(shield.status()["active"])
        self.assertFalse(shield.status()["engaged"])

    def test_context_manager_toggles_active(self) -> None:
        with CaptureShield() as shield:
            self.assertTrue(shield.active)
        self.assertFalse(shield.active)


class CaptureShieldWindowsMockTests(unittest.TestCase):
    """Mock ctypes.windll.user32 so CI can exercise the Windows path."""

    def test_enter_windows_success(self) -> None:
        user32 = MagicMock()
        user32.GetParent.return_value = 0
        user32.SetWindowDisplayAffinity.return_value = 1

        fake_ctypes = MagicMock()
        fake_ctypes.windll.user32 = user32
        fake_ctypes.get_last_error.return_value = 0

        shield = CaptureShield()
        shield._system = "Windows"
        shield._active = True  # enter() sets this before platform branch
        with patch.dict(sys.modules, {"ctypes": fake_ctypes}):
            ok = shield._enter_windows(0xABC)
        self.assertTrue(ok)
        user32.SetWindowDisplayAffinity.assert_called_with(0xABC, WDA_EXCLUDEFROMCAPTURE)
        st = shield.status()
        self.assertTrue(st["engaged"])
        self.assertTrue(st["supported"])
        self.assertTrue(st["active"])
        self.assertEqual(st["mechanism"], "SetWindowDisplayAffinity")
        self.assertIn("WDA_EXCLUDEFROMCAPTURE", st["note"])

        with patch.dict(sys.modules, {"ctypes": fake_ctypes}):
            shield._system = "Windows"
            shield.exit()
        user32.SetWindowDisplayAffinity.assert_called_with(0xABC, WDA_NONE)
        self.assertFalse(shield.status()["engaged"])
        self.assertFalse(shield.status()["active"])

    def test_enter_windows_failure(self) -> None:
        user32 = MagicMock()
        user32.GetParent.return_value = 0
        user32.SetWindowDisplayAffinity.return_value = 0

        fake_ctypes = MagicMock()
        fake_ctypes.windll.user32 = user32
        fake_ctypes.get_last_error.return_value = 5

        shield = CaptureShield()
        shield._system = "Windows"
        with patch.dict(sys.modules, {"ctypes": fake_ctypes}):
            ok = shield._enter_windows(0x100)
        self.assertFalse(ok)
        st = shield.status()
        self.assertFalse(st["engaged"])
        self.assertFalse(st["supported"])
        self.assertIn("failed", st["note"])

    def test_enter_windows_no_hwnd(self) -> None:
        shield = CaptureShield()
        shield._system = "Windows"
        ok = shield._enter_windows(None)
        self.assertFalse(ok)
        self.assertIn("no HWND", shield.status()["note"])

    def test_resolve_hwnd_climbs_parent(self) -> None:
        user32 = MagicMock()

        def get_parent(h: int) -> int:
            return {0x10: 0x20, 0x20: 0}.get(h, 0)

        user32.GetParent.side_effect = get_parent
        fake_ctypes = MagicMock()
        fake_ctypes.windll.user32 = user32

        with patch.dict(sys.modules, {"ctypes": fake_ctypes}):
            top = _resolve_hwnd_windows(0x10)
        self.assertEqual(top, 0x20)


class CaptureShieldDarwinStubTests(unittest.TestCase):
    def test_darwin_without_pyobjc(self) -> None:
        shield = CaptureShield()
        shield._system = "Darwin"
        import builtins

        real_import = builtins.__import__

        def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "AppKit":
                raise ImportError("no pyobjc")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            ok = shield._enter_darwin(None)
        self.assertFalse(ok)
        st = shield.status()
        self.assertFalse(st["engaged"])
        self.assertFalse(st["supported"])
        self.assertIn("pyobjc", st["note"].lower())
        self.assertIn("setContentProtection", st["note"])


if __name__ == "__main__":
    unittest.main()
