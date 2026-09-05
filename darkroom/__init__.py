"""
dark-room: inverse sandbox for agent-watched desktops.

Plaintext secrets MUST NEVER enter model context (chat, screenshots,
tool logs, or agent reasoning). Agents may only see opaque handles
of the form ``dr_sec_<id>``.
"""

__version__ = "0.1.0"
__all__ = ["Vault", "CaptureShield"]

from darkroom.vault import Vault
from darkroom.capture import CaptureShield
