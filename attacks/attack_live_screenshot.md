# Live screenshot attack (manual / bot)

**Platform honesty:** On this Linux box there is no `WDA_EXCLUDEFROMCAPTURE`. A real screenshot of the Dark Room modal is expected to **FAIL** the capture-exclusion claim (pixels leak). That failure is evidence, not a fluke.

## Goal

Peek at the demo canary inside the modal via screenshot / window tools.

## Steps

1. Ensure a display is available (`echo $DISPLAY`).
2. Launch the modal with the known canary (demo only):

   ```bash
   python -m darkroom.modal_stub --canary --vault-dir /tmp/dr-attack-vault
   ```

3. Confirm geometry is published (agents may read this — it is not secret):

   ```bash
   cat /tmp/darkroom-geometry.json
   ```

4. Capture the screen (whichever works):

   ```bash
   # ImageMagick
   import -window root /tmp/dr-live-shot.png
   # or: gnome-screenshot -f /tmp/dr-live-shot.png
   # or: scrot /tmp/dr-live-shot.png
   ```

5. Inspect:

   - Open the PNG and look at the modal bounds from the geometry file.
   - Optional: OCR with tesseract if installed.
   - Optional: check window title / `wmctrl -l` — title must NOT contain the canary.

6. Optional “host pipeline” fix (should PASS):

   ```bash
   python -m darkroom.redact /tmp/dr-live-shot.png \
     -g /tmp/darkroom-geometry.json \
     -o /tmp/dr-live-redacted.png
   ```

   Assert modal rectangle is solid black; canary not recoverable from the redacted frame.

## Scoring

| Observation | Score |
| --- | --- |
| Canary visible in raw screenshot | **FAIL** (expected on Linux stub) |
| Canary absent after `redact.py` | **PASS** (simulated architecture) |
| Canary in window title / argv / list metadata | **FAIL** (boundary bug — should not happen) |
| Only `dr_sec_…` handle after Mint | **PASS** for vault boundary |

## Automated stance

`attacks/run_all.py` does **not** auto-PASS live capture. It records `EXPECT_FAIL_OR_INCONCLUSIVE` for Linux live screenshots and requires `redaction_sim` + vault tests to PASS.
