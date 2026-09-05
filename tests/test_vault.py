"""Tests proving secrets never leak via metadata APIs; revoke/wrong-handle work."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from darkroom.vault import (
    Vault,
    HandleNotFound,
    HandleRevoked,
    OriginNotAllowed,
    HANDLE_PREFIX,
)


SECRET = "super-secret-value-NEVER-IN-METADATA-xyz"


class VaultTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.vault_dir = Path(self._tmpdir.name)
        self.vault = Vault(vault_dir=self.vault_dir)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_mint_returns_opaque_handle(self) -> None:
        handle = self.vault.mint(SECRET, label="api-key")
        self.assertTrue(handle.startswith(HANDLE_PREFIX))
        self.assertNotIn(SECRET, handle)

    def test_list_metadata_never_contains_secret(self) -> None:
        handle = self.vault.mint(SECRET, label="db-pass")
        rows = self.vault.list_metadata()
        blob = json.dumps(rows)
        self.assertNotIn(SECRET, blob)
        self.assertNotIn("ciphertext", blob)
        self.assertEqual(rows[0]["handle"], handle)
        self.assertEqual(rows[0]["label"], "db-pass")
        self.assertFalse(rows[0]["revoked"])

    def test_get_meta_never_contains_secret(self) -> None:
        handle = self.vault.mint(SECRET, label="token")
        meta = self.vault.get_meta(handle)
        blob = json.dumps(meta)
        self.assertNotIn(SECRET, blob)
        self.assertNotIn("ciphertext", blob)

    def test_resolve_returns_plaintext_locally(self) -> None:
        handle = self.vault.mint(SECRET, label="x")
        self.assertEqual(self.vault.resolve(handle), SECRET)

    def test_wrong_handle_fails(self) -> None:
        self.vault.mint(SECRET, label="x")
        with self.assertRaises(HandleNotFound):
            self.vault.resolve("dr_sec_does_not_exist_zzzz")
        with self.assertRaises(HandleNotFound):
            self.vault.resolve("not-a-handle")

    def test_revoke_works(self) -> None:
        handle = self.vault.mint(SECRET, label="x")
        self.vault.revoke(handle)
        meta = self.vault.get_meta(handle)
        self.assertTrue(meta["revoked"])
        with self.assertRaises(HandleRevoked):
            self.vault.resolve(handle)
        # list still metadata-only, no secret
        blob = json.dumps(self.vault.list_metadata())
        self.assertNotIn(SECRET, blob)

    def test_origin_allowlist(self) -> None:
        handle = self.vault.mint(
            SECRET,
            label="stripe",
            allowlisted_origins=["https://checkout.example"],
        )
        self.assertEqual(
            self.vault.resolve(handle, origin="https://checkout.example"),
            SECRET,
        )
        with self.assertRaises(OriginNotAllowed):
            self.vault.resolve(handle, origin="https://evil.example")

    def test_audit_log_has_no_plaintext(self) -> None:
        handle = self.vault.mint(SECRET, label="audit-check")
        self.vault.resolve(handle)
        audit = (self.vault_dir / "audit.log").read_text(encoding="utf-8")
        self.assertNotIn(SECRET, audit)
        self.assertIn(handle, audit)
        self.assertIn("mint", audit)
        self.assertIn("resolve_ok", audit)

    def test_store_file_is_ciphertext(self) -> None:
        self.vault.mint(SECRET, label="enc")
        raw = (self.vault_dir / "vault.enc.json").read_bytes()
        # Fernet tokens are urlsafe-base64; plaintext must not appear
        self.assertNotIn(SECRET.encode("utf-8"), raw)


class CaptureShieldTests(unittest.TestCase):
    def test_stub_context_manager(self) -> None:
        from darkroom.capture import CaptureShield

        s = CaptureShield()
        self.assertFalse(s.supported)
        with s:
            self.assertTrue(s.active)
        self.assertFalse(s.active)
        st = s.status()
        self.assertIn("system", st)
        self.assertFalse(st["supported"])


if __name__ == "__main__":
    unittest.main()
