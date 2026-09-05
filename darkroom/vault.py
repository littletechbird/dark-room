"""
Local encrypted vault that mints opaque handles and resolves them only
at controlled fill/submit/egress points.

CRITICAL: Plaintext secrets must never enter model context. The vault
stores ciphertext on disk; list/metadata APIs never return plaintext;
resolve() returns plaintext only to the caller's local process memory
for immediate use (e.g. writing a form field), never to stdout meant
for agents.
"""

from __future__ import annotations

import json
import os
import secrets
import stat
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional

from cryptography.fernet import Fernet, InvalidToken


HANDLE_PREFIX = "dr_sec_"
DEFAULT_VAULT_DIR = Path.home() / ".darkroom"
KEY_FILENAME = "machine.key"
STORE_FILENAME = "vault.enc.json"
AUDIT_FILENAME = "audit.log"


@dataclass
class SecretMeta:
    """Metadata only — never includes plaintext."""

    handle: str
    label: str
    created_at: float
    revoked: bool = False
    allowlisted_origins: Optional[list[str]] = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "handle": self.handle,
            "label": self.label,
            "created_at": self.created_at,
            "revoked": self.revoked,
            "allowlisted_origins": list(self.allowlisted_origins or []),
        }


class VaultError(Exception):
    """Base vault error."""


class HandleNotFound(VaultError):
    """Handle does not exist."""


class HandleRevoked(VaultError):
    """Handle was revoked."""


class OriginNotAllowed(VaultError):
    """Handle used against a non-allowlisted origin."""


class Vault:
    """
    Encrypted local-file vault.

    Machine-local Fernet key lives in ``~/.darkroom/machine.key``
    (mode 0600). Ciphertext store is ``~/.darkroom/vault.enc.json``.
    """

    def __init__(self, vault_dir: Optional[Path] = None) -> None:
        self.vault_dir = Path(vault_dir) if vault_dir else DEFAULT_VAULT_DIR
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.vault_dir, stat.S_IRWXU)  # 0700
        except OSError:
            pass
        self._key_path = self.vault_dir / KEY_FILENAME
        self._store_path = self.vault_dir / STORE_FILENAME
        self._audit_path = self.vault_dir / AUDIT_FILENAME
        self._fernet = Fernet(self._load_or_create_key())
        self._entries: dict[str, dict[str, Any]] = self._load_store()

    def _load_or_create_key(self) -> bytes:
        if self._key_path.exists():
            key = self._key_path.read_bytes().strip()
            return key
        key = Fernet.generate_key()
        self._key_path.write_bytes(key)
        try:
            os.chmod(self._key_path, stat.S_IRUSR | stat.S_IWUSR)  # 0600
        except OSError:
            pass
        self._audit("key_created", {})
        return key

    def _load_store(self) -> dict[str, dict[str, Any]]:
        if not self._store_path.exists():
            return {}
        raw = self._store_path.read_bytes()
        if not raw:
            return {}
        try:
            decrypted = self._fernet.decrypt(raw)
        except InvalidToken as exc:
            raise VaultError("vault store decrypt failed; wrong key?") from exc
        data = json.loads(decrypted.decode("utf-8"))
        if not isinstance(data, dict):
            raise VaultError("corrupt vault store")
        return data

    def _save_store(self) -> None:
        payload = json.dumps(self._entries, separators=(",", ":")).encode("utf-8")
        token = self._fernet.encrypt(payload)
        tmp = self._store_path.with_suffix(".tmp")
        tmp.write_bytes(token)
        try:
            os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass
        tmp.replace(self._store_path)

    def _audit(self, event: str, fields: dict[str, Any]) -> None:
        """Append audit line. Never log plaintext secrets."""
        record = {
            "ts": time.time(),
            "event": event,
            **fields,
        }
        # Defense: refuse if any field looks like it might contain a secret body
        for k, v in fields.items():
            if k in ("secret", "plaintext", "password", "token_value"):
                raise VaultError(f"refusing to audit sensitive field: {k}")
            if isinstance(v, str) and not v.startswith(HANDLE_PREFIX) and len(v) > 200:
                # Truncate long non-handle strings in audit (side-channel hygiene)
                record[k] = v[:32] + "…"
        line = json.dumps(record, separators=(",", ":")) + "\n"
        with open(self._audit_path, "a", encoding="utf-8") as fh:
            fh.write(line)

    @staticmethod
    def _mint_handle() -> str:
        # Opaque, non-guessable id; prefix is the public format marker.
        return HANDLE_PREFIX + secrets.token_urlsafe(18)

    def mint(
        self,
        secret: str,
        label: str,
        allowlisted_origins: Optional[list[str]] = None,
    ) -> str:
        """
        Encrypt ``secret``, store it, return opaque handle ``dr_sec_<id>``.

        ``secret`` must come from stdin/TTY or an in-process buffer —
        never from argv, env, or agent-visible logs.
        """
        if not secret:
            raise VaultError("secret must be non-empty")
        if not label or not label.strip():
            raise VaultError("label must be non-empty")
        handle = self._mint_handle()
        ciphertext = self._fernet.encrypt(secret.encode("utf-8")).decode("ascii")
        self._entries[handle] = {
            "label": label.strip(),
            "created_at": time.time(),
            "revoked": False,
            "allowlisted_origins": list(allowlisted_origins or []),
            "ciphertext": ciphertext,
        }
        self._save_store()
        self._audit(
            "mint",
            {
                "handle": handle,
                "label": label.strip(),
                "origins": list(allowlisted_origins or []),
            },
        )
        return handle

    def resolve(
        self,
        handle: str,
        origin: Optional[str] = None,
    ) -> str:
        """
        Expand handle to plaintext for local fill/submit only.

        Callers MUST NOT print the return value to agent-visible stdout,
        screenshots, or tool transcripts. Wrong-origin use raises.
        """
        if not handle.startswith(HANDLE_PREFIX):
            raise HandleNotFound(f"invalid handle format: {handle!r}")
        entry = self._entries.get(handle)
        if entry is None:
            self._audit("resolve_miss", {"handle": handle})
            raise HandleNotFound(f"unknown handle: {handle}")
        if entry.get("revoked"):
            self._audit("resolve_revoked", {"handle": handle})
            raise HandleRevoked(f"handle revoked: {handle}")
        allowed = entry.get("allowlisted_origins") or []
        if allowed and origin is not None and origin not in allowed:
            self._audit(
                "resolve_origin_denied",
                {"handle": handle, "origin": origin or ""},
            )
            raise OriginNotAllowed(
                f"origin {origin!r} not allowlisted for {handle}"
            )
        try:
            plaintext = self._fernet.decrypt(
                entry["ciphertext"].encode("ascii")
            ).decode("utf-8")
        except InvalidToken as exc:
            raise VaultError("ciphertext decrypt failed") from exc
        self._audit(
            "resolve_ok",
            {"handle": handle, "origin": origin or "", "label": entry["label"]},
        )
        return plaintext

    def revoke(self, handle: str) -> None:
        if handle not in self._entries:
            raise HandleNotFound(f"unknown handle: {handle}")
        self._entries[handle]["revoked"] = True
        # Zero ciphertext on revoke (best-effort)
        self._entries[handle]["ciphertext"] = ""
        self._save_store()
        self._audit("revoke", {"handle": handle})

    def list_metadata(self) -> list[dict[str, Any]]:
        """Return metadata only — never plaintext or ciphertext."""
        out: list[dict[str, Any]] = []
        for handle, entry in self._entries.items():
            meta = SecretMeta(
                handle=handle,
                label=entry["label"],
                created_at=entry["created_at"],
                revoked=bool(entry.get("revoked")),
                allowlisted_origins=list(entry.get("allowlisted_origins") or []),
            )
            out.append(meta.to_public_dict())
        return out

    def get_meta(self, handle: str) -> dict[str, Any]:
        entry = self._entries.get(handle)
        if entry is None:
            raise HandleNotFound(f"unknown handle: {handle}")
        return SecretMeta(
            handle=handle,
            label=entry["label"],
            created_at=entry["created_at"],
            revoked=bool(entry.get("revoked")),
            allowlisted_origins=list(entry.get("allowlisted_origins") or []),
        ).to_public_dict()
