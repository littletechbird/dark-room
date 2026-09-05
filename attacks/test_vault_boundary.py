"""
Vault boundary wrapper — runs existing unit tests and adds file-exfil checks.

PASS means: canary / demo secret not readable via metadata, env, or
agent-visible status files that the modal is allowed to publish.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

# Re-export / load the canonical vault suite
from tests.test_vault import CaptureShieldTests, VaultTests  # noqa: F401

from darkroom.vault import Vault, HANDLE_PREFIX

CANARY = "CANARY_DARKROOM_SECRET_7f3a"


class AttackFileExfilTests(unittest.TestCase):
    """attack_file_exfil style: try to read canary from vault surfaces."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.vault_dir = Path(self._tmpdir.name)
        self.vault = Vault(vault_dir=self.vault_dir)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_canary_not_in_metadata_or_audit(self) -> None:
        handle = self.vault.mint(CANARY, label="canary-demo")
        self.assertTrue(handle.startswith(HANDLE_PREFIX))
        meta_blob = json.dumps(self.vault.list_metadata())
        self.assertNotIn(CANARY, meta_blob)
        audit = (self.vault_dir / "audit.log").read_text(encoding="utf-8")
        self.assertNotIn(CANARY, audit)
        store = (self.vault_dir / "vault.enc.json").read_bytes()
        self.assertNotIn(CANARY.encode("utf-8"), store)

    def test_handle_file_has_handle_not_secret(self) -> None:
        handle = self.vault.mint(CANARY, label="canary-demo")
        # Simulate modal writing last-handle status (agent-readable)
        path = Path(self._tmpdir.name) / "last-handle.txt"
        path.write_text(handle + "\n", encoding="utf-8")
        text = path.read_text(encoding="utf-8")
        self.assertIn(HANDLE_PREFIX, text)
        self.assertNotIn(CANARY, text)

    def test_env_should_not_hold_canary(self) -> None:
        # Boundary: process env must not be used for secrets
        for k, v in os.environ.items():
            if "DARKROOM" in k.upper() or "SECRET" in k.upper():
                self.assertNotIn(CANARY, v)


if __name__ == "__main__":
    unittest.main()
