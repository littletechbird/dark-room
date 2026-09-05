# Fill / transcript proof

Canary must never appear in agent-visible CLI stdout.

- mint stdout: CLEAN (opaque `dr_sec_*` only)
- list stdout: CLEAN (metadata only)
- fill-sim stdout: CLEAN (`value=****` mask only)
- form file (privileged resolver target): CONTAINS secret by design — must never be pasted into model/chat
- vault on-disk: no plaintext canary bytes
