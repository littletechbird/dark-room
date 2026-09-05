"""
dark-room CLI.

Plaintext secrets are read from stdin/TTY only — never from argv —
so they cannot appear in process lists or agent-captured command lines.
"""

from __future__ import annotations

import argparse
import getpass
import json
import sys
from pathlib import Path

from darkroom.vault import (
    Vault,
    VaultError,
    HandleNotFound,
    HandleRevoked,
    OriginNotAllowed,
)
from darkroom.capture import CaptureShield


def _read_secret_from_stdin() -> str:
    """Read secret without echoing to agent-visible argv."""
    if sys.stdin.isatty():
        # getpass hides echo on TTY
        return getpass.getpass("secret (input hidden): ")
    # Piped stdin — still never put on argv
    data = sys.stdin.read()
    if data.endswith("\n"):
        data = data[:-1]
    return data


def cmd_mint(args: argparse.Namespace) -> int:
    vault = Vault(vault_dir=Path(args.vault_dir) if args.vault_dir else None)
    secret = _read_secret_from_stdin()
    if not secret:
        print("error: empty secret", file=sys.stderr)
        return 1
    origins = args.origin or []
    try:
        handle = vault.mint(secret, label=args.label, allowlisted_origins=origins)
    except VaultError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    # Only the opaque handle is printed — never the secret.
    print(handle)
    return 0


def _mask(s: str) -> str:
    """Length-hiding mask for confirmation (avoids length side channel)."""
    return "****"


def cmd_fill_sim(args: argparse.Namespace) -> int:
    """
    Simulate filling a form with a resolved secret.

    Writes the secret into a local fake form file only. Prints a masked
    confirmation to stdout so agents never see plaintext.
    """
    vault = Vault(vault_dir=Path(args.vault_dir) if args.vault_dir else None)
    form_path = Path(args.form_file)
    try:
        # CaptureShield would exclude the fill UI from screenshots
        with CaptureShield():
            plaintext = vault.resolve(args.handle, origin=args.origin)
            # Write to fake form — local file, not stdout
            form_path.parent.mkdir(parents=True, exist_ok=True)
            # Simple key=value form simulation
            existing: dict[str, str] = {}
            if form_path.exists():
                for line in form_path.read_text(encoding="utf-8").splitlines():
                    if "=" in line:
                        k, v = line.split("=", 1)
                        existing[k] = v
            field = args.field
            existing[field] = plaintext
            # CRITICAL: do not print plaintext
            form_path.write_text(
                "\n".join(f"{k}={v}" for k, v in existing.items()) + "\n",
                encoding="utf-8",
            )
            # Zero local ref as best-effort (Python strings are immutable;
            # this documents intent for integrators)
            del plaintext
    except (HandleNotFound, HandleRevoked, OriginNotAllowed, VaultError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    # Agent-visible output: masked only
    print(f"filled field={args.field!r} handle={args.handle} value={_mask('x')}")
    print(f"form_file={form_path}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    vault = Vault(vault_dir=Path(args.vault_dir) if args.vault_dir else None)
    rows = vault.list_metadata()
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        if not rows:
            print("(no entries)")
            return 0
        for r in rows:
            status = "REVOKED" if r["revoked"] else "active"
            origins = ",".join(r["allowlisted_origins"]) or "*"
            print(f"{r['handle']}\t{r['label']}\t{status}\torigins={origins}")
    return 0


def cmd_revoke(args: argparse.Namespace) -> int:
    vault = Vault(vault_dir=Path(args.vault_dir) if args.vault_dir else None)
    try:
        vault.revoke(args.handle)
    except HandleNotFound as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"revoked {args.handle}")
    return 0


def cmd_shield_status(args: argparse.Namespace) -> int:
    shield = CaptureShield()
    print(json.dumps(shield.status(), indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="darkroom",
        description=(
            "dark-room: inverse sandbox for agent-watched desktops. "
            "Mint opaque handles; resolve only at local fill/egress. "
            "Plaintext must never enter model context."
        ),
    )
    p.add_argument(
        "--vault-dir",
        default=None,
        help="override vault directory (default: ~/.darkroom)",
    )
    sub = p.add_subparsers(dest="command", required=True)

    mint = sub.add_parser("mint", help="mint handle; secret from stdin/TTY")
    mint.add_argument("--label", "-l", required=True, help="human label")
    mint.add_argument(
        "--origin",
        action="append",
        default=[],
        help="allowlisted origin (repeatable)",
    )
    mint.set_defaults(func=cmd_mint)

    fill = sub.add_parser(
        "fill-sim",
        help="resolve handle into fake form file; stdout is masked only",
    )
    fill.add_argument("--handle", "-H", required=True)
    fill.add_argument("--field", "-f", default="password")
    fill.add_argument(
        "--form-file",
        default="fake_form.txt",
        help="local file to write filled fields",
    )
    fill.add_argument("--origin", default=None, help="declared fill origin")
    fill.set_defaults(func=cmd_fill_sim)

    lst = sub.add_parser("list", help="list metadata only (no secrets)")
    lst.add_argument("--json", action="store_true")
    lst.set_defaults(func=cmd_list)

    rev = sub.add_parser("revoke", help="revoke a handle and wipe ciphertext")
    rev.add_argument("--handle", "-H", required=True)
    rev.set_defaults(func=cmd_revoke)

    sh = sub.add_parser("shield-status", help="CaptureShield OS-exclude status")
    sh.set_defaults(func=cmd_shield_status)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
