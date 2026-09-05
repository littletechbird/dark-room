"""
SIMULATED host redaction pipeline — MUST PASS.

Draws a unique canary color pattern inside a modal rectangle on a synthetic
screenshot, runs darkroom.redact, and asserts the canary pattern is gone
(fully blacked out) inside the geometry bounds.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from darkroom.redact import redact_file, redact_image

# Unique canary: pure red (255,0,0) — not used elsewhere in the synthetic frame
CANARY_RGB = (255, 0, 0)
BG_RGB = (40, 40, 50)
OTHER_RGB = (0, 200, 80)


class RedactionSimTests(unittest.TestCase):
    def test_canary_pattern_gone_after_redact(self) -> None:
        # Synthetic "screenshot": 400x300, modal at (50,40,200,120)
        geo = {"x": 50, "y": 40, "w": 200, "h": 120}
        img = Image.new("RGB", (400, 300), BG_RGB)
        # Green marker outside modal (must survive)
        for x in range(10, 30):
            for y in range(10, 30):
                img.putpixel((x, y), OTHER_RGB)
        # Red canary pattern filling the modal rect
        for x in range(geo["x"], geo["x"] + geo["w"]):
            for y in range(geo["y"], geo["y"] + geo["h"]):
                # Checkerboard of pure red vs slightly darker red — both "canary"
                if (x + y) % 2 == 0:
                    img.putpixel((x, y), CANARY_RGB)
                else:
                    img.putpixel((x, y), (200, 0, 0))

        # Precondition: canary present
        self.assertEqual(img.getpixel((60, 50)), CANARY_RGB)

        redacted = redact_image(img, geo)

        # Inside modal: all black
        for x in range(geo["x"], geo["x"] + geo["w"]):
            for y in range(geo["y"], geo["y"] + geo["h"]):
                px = redacted.getpixel((x, y))
                self.assertEqual(
                    px,
                    (0, 0, 0),
                    f"canary residual at ({x},{y}): {px}",
                )

        # Outside modal: green marker intact
        self.assertEqual(redacted.getpixel((15, 15)), OTHER_RGB)
        # Background outside intact
        self.assertEqual(redacted.getpixel((350, 250)), BG_RGB)

    def test_redact_file_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            geo = {"x": 10, "y": 10, "w": 50, "h": 40}
            src = td_path / "shot.png"
            geo_path = td_path / "geo.json"
            out = td_path / "redacted.png"

            img = Image.new("RGB", (100, 80), (10, 10, 10))
            for x in range(10, 60):
                for y in range(10, 50):
                    img.putpixel((x, y), CANARY_RGB)
            img.save(src)
            geo_path.write_text(json.dumps(geo), encoding="utf-8")

            redact_file(src, geo_path, out)
            result = Image.open(out)
            self.assertEqual(result.getpixel((20, 20)), (0, 0, 0))
            # Corner outside modal still dark-gray bg
            self.assertEqual(result.getpixel((90, 70)), (10, 10, 10))
            result.close()

    def test_no_red_left_in_rect_scorecard_helper(self) -> None:
        """Helper used by run_all scorecard: count non-black pixels in rect."""
        geo = {"x": 0, "y": 0, "w": 20, "h": 20}
        img = Image.new("RGB", (20, 20), CANARY_RGB)
        redacted = redact_image(img, geo)
        non_black = sum(
            1
            for x in range(20)
            for y in range(20)
            if redacted.getpixel((x, y)) != (0, 0, 0)
        )
        self.assertEqual(non_black, 0)


if __name__ == "__main__":
    unittest.main()
