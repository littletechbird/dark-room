"""
Dark Room modal stub (Tkinter / stdlib).

Draggable (custom title bar), resizable, optional always-on-top dark UI
with a demo-secret text entry and a "Mint handle" button that writes an
opaque handle via the vault — never prints the secret.

Geometry ``{x,y,w,h}`` is written to ``/tmp/darkroom-geometry.json`` on
move/resize so a host redaction pipeline (see ``darkroom.redact``) can
black out the modal before frames reach a model.

This stub does NOT implement OS exclude-from-capture. On Linux a live
screenshot WILL see the modal contents — that is intentional and is
exercised by the attack suite. See CAPTURE_NOTES.md.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from typing import Optional

from darkroom.vault import Vault, VaultError

GEOMETRY_PATH = Path(os.environ.get("DARKROOM_GEOMETRY_PATH", "/tmp/darkroom-geometry.json"))
DEFAULT_CANARY = "CANARY_DARKROOM_SECRET_7f3a"

# Dark UI palette
BG = "#0d0d0f"
BG_TITLE = "#1a1a1f"
FG = "#e8e8ec"
FG_DIM = "#8a8a96"
ACCENT = "#5b8cff"
ENTRY_BG = "#16161a"
DANGER = "#ff6b6b"


class DarkRoomModal:
    """Always-on-top (optional) Dark Room window stub."""

    def __init__(
        self,
        *,
        vault_dir: Optional[Path] = None,
        geometry_path: Path = GEOMETRY_PATH,
        initial_secret: str = "",
        always_on_top: bool = True,
        title: str = "Dark Room",
    ) -> None:
        self.geometry_path = Path(geometry_path)
        self.vault_dir = Path(vault_dir) if vault_dir else Path(tempfile.mkdtemp(prefix="darkroom-modal-"))
        self._drag_x = 0
        self._drag_y = 0
        self._handle_var: Optional[tk.StringVar] = None

        self.root = tk.Tk()
        self.root.title(title)
        # Window title intentionally does NOT contain the secret.
        self.root.configure(bg=BG)
        self.root.geometry("480x280+120+120")
        self.root.minsize(320, 200)
        if always_on_top:
            self.root.attributes("-topmost", True)

        # Undecorated-ish custom chrome: keep native resize grips via overrideredirect=False
        # so the window stays resizable; drag via custom title bar.
        self._build_ui(initial_secret=initial_secret)
        self.root.bind("<Configure>", self._on_configure)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        # Initial geometry write
        self.root.after(50, self._write_geometry)

    def _build_ui(self, *, initial_secret: str) -> None:
        title = tk.Frame(self.root, bg=BG_TITLE, height=36)
        title.pack(fill=tk.X, side=tk.TOP)
        title.pack_propagate(False)

        lbl = tk.Label(
            title,
            text="  Dark Room  —  capture-excluded stub",
            bg=BG_TITLE,
            fg=FG,
            font=("Helvetica", 11, "bold"),
            anchor="w",
        )
        lbl.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        close_btn = tk.Button(
            title,
            text=" ✕ ",
            bg=BG_TITLE,
            fg=FG_DIM,
            activebackground=DANGER,
            activeforeground=FG,
            relief=tk.FLAT,
            borderwidth=0,
            command=self._on_close,
        )
        close_btn.pack(side=tk.RIGHT, padx=4)

        for w in (title, lbl):
            w.bind("<ButtonPress-1>", self._start_drag)
            w.bind("<B1-Motion>", self._on_drag)

        body = tk.Frame(self.root, bg=BG, padx=16, pady=12)
        body.pack(fill=tk.BOTH, expand=True)

        hint = tk.Label(
            body,
            text=(
                "Demo secret stays inside this window for the human.\n"
                "Agents should only receive an opaque dr_sec_ handle."
            ),
            bg=BG,
            fg=FG_DIM,
            justify=tk.LEFT,
            font=("Helvetica", 9),
        )
        hint.pack(anchor="w", pady=(0, 8))

        tk.Label(body, text="Demo secret", bg=BG, fg=FG, font=("Helvetica", 10)).pack(
            anchor="w"
        )
        self.secret_var = tk.StringVar(value=initial_secret)
        entry = tk.Entry(
            body,
            textvariable=self.secret_var,
            show="•",
            bg=ENTRY_BG,
            fg=FG,
            insertbackground=FG,
            relief=tk.FLAT,
            font=("Courier", 12),
        )
        entry.pack(fill=tk.X, pady=(4, 4), ipady=6)
        # Optional reveal for demos (still never printed to stdout)
        self._reveal = tk.BooleanVar(value=False)

        def _toggle_reveal() -> None:
            entry.config(show="" if self._reveal.get() else "•")

        tk.Checkbutton(
            body,
            text="Reveal (local UI only)",
            variable=self._reveal,
            command=_toggle_reveal,
            bg=BG,
            fg=FG_DIM,
            selectcolor=ENTRY_BG,
            activebackground=BG,
            activeforeground=FG,
        ).pack(anchor="w")

        btn_row = tk.Frame(body, bg=BG)
        btn_row.pack(fill=tk.X, pady=(12, 4))

        mint_btn = tk.Button(
            btn_row,
            text="Mint handle",
            bg=ACCENT,
            fg="#ffffff",
            activebackground="#3d6fd9",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=14,
            pady=6,
            font=("Helvetica", 10, "bold"),
            command=self._mint,
        )
        mint_btn.pack(side=tk.LEFT)

        self.status_var = tk.StringVar(value="Ready — geometry → " + str(self.geometry_path))
        status = tk.Label(
            body,
            textvariable=self.status_var,
            bg=BG,
            fg=FG_DIM,
            font=("Courier", 8),
            justify=tk.LEFT,
            wraplength=440,
            anchor="w",
        )
        status.pack(fill=tk.X, pady=(10, 0))

        self._handle_var = tk.StringVar(value="")
        handle_lbl = tk.Label(
            body,
            textvariable=self._handle_var,
            bg=BG,
            fg=ACCENT,
            font=("Courier", 10, "bold"),
            anchor="w",
        )
        handle_lbl.pack(fill=tk.X, pady=(4, 0))

        # Resize grip hint (native window borders handle resize)
        foot = tk.Label(
            self.root,
            text="drag title bar · resize via window edges · always-on-top optional",
            bg=BG_TITLE,
            fg=FG_DIM,
            font=("Helvetica", 8),
        )
        foot.pack(fill=tk.X, side=tk.BOTTOM)

    def _start_drag(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()

    def _on_drag(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.root.geometry(f"+{x}+{y}")
        self._write_geometry()

    def _on_configure(self, _event: tk.Event | None = None) -> None:  # type: ignore[type-arg]
        self._write_geometry()

    def _current_geometry(self) -> dict[str, int]:
        self.root.update_idletasks()
        return {
            "x": int(self.root.winfo_rootx()),
            "y": int(self.root.winfo_rooty()),
            "w": int(self.root.winfo_width()),
            "h": int(self.root.winfo_height()),
        }

    def _write_geometry(self) -> None:
        geo = self._current_geometry()
        try:
            self.geometry_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.geometry_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(geo) + "\n", encoding="utf-8")
            tmp.replace(self.geometry_path)
        except OSError as exc:
            self.status_var.set(f"geometry write failed: {exc}")

    def _mint(self) -> None:
        secret = self.secret_var.get()
        if not secret:
            self.status_var.set("error: empty secret")
            return
        try:
            vault = Vault(vault_dir=self.vault_dir)
            # Never print secret — only the opaque handle is shown in-UI / status.
            handle = vault.mint(secret, label="modal-demo")
        except VaultError as exc:
            self.status_var.set(f"mint error: {exc}")
            return
        assert self._handle_var is not None
        self._handle_var.set(handle)
        self.status_var.set(f"minted (secret not printed) vault={self.vault_dir}")
        # Also write handle to a sibling status file agents MAY read
        handle_path = Path("/tmp/darkroom-last-handle.txt")
        try:
            handle_path.write_text(handle + "\n", encoding="utf-8")
        except OSError:
            pass

    def _on_close(self) -> None:
        self._write_geometry()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Dark Room Tkinter modal stub")
    p.add_argument(
        "--vault-dir",
        default=None,
        help="vault directory (default: temp dir under /tmp)",
    )
    p.add_argument(
        "--geometry-path",
        default=str(GEOMETRY_PATH),
        help="where to write {x,y,w,h} JSON",
    )
    p.add_argument(
        "--secret",
        default="",
        help="optional demo secret preload (DEMO ONLY — prefer typing in UI)",
    )
    p.add_argument(
        "--canary",
        action="store_true",
        help=f"preload known canary {DEFAULT_CANARY!r} for attack tests",
    )
    p.add_argument(
        "--no-topmost",
        action="store_true",
        help="disable always-on-top",
    )
    args = p.parse_args(argv)
    initial = DEFAULT_CANARY if args.canary else (args.secret or "")
    # Warn on --secret: argv is agent-visible; canary flag is for tests only.
    if args.secret and not args.canary:
        print(
            "warning: --secret puts demo value on argv (agent-visible). "
            "Prefer typing in the UI or --canary for tests.",
            file=sys.stderr,
        )
    modal = DarkRoomModal(
        vault_dir=Path(args.vault_dir) if args.vault_dir else None,
        geometry_path=Path(args.geometry_path),
        initial_secret=initial,
        always_on_top=not args.no_topmost,
    )
    modal.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
