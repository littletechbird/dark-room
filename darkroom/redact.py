"""
Host-side redaction pipeline for Dark Room.

Given a screenshot PNG and a geometry JSON (x, y, w, h), black out the
rectangle that corresponds to the Dark Room modal before any model /
vision pipeline sees the frame.

This is the *simulated* capture-exclusion path used on platforms without
WDA_EXCLUDEFROMCAPTURE (notably Linux). Production hosts SHOULD prefer
OS-level exclude-from-capture and still run redaction as defense-in-depth.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence, Union

from PIL import Image, ImageDraw

GeometryLike = Union[Mapping[str, Any], Sequence[int]]


def load_geometry(path: Union[str, Path]) -> dict[str, int]:
    """Load ``{x,y,w,h}`` (or ``width``/``height`` aliases) from JSON."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return normalize_geometry(data)


def normalize_geometry(geo: GeometryLike) -> dict[str, int]:
    """Normalize geometry to integer ``x, y, w, h``."""
    if isinstance(geo, Mapping):
        x = int(geo["x"])
        y = int(geo["y"])
        if "w" in geo:
            w = int(geo["w"])
        elif "width" in geo:
            w = int(geo["width"])
        else:
            raise KeyError("geometry missing w/width")
        if "h" in geo:
            h = int(geo["h"])
        elif "height" in geo:
            h = int(geo["height"])
        else:
            raise KeyError("geometry missing h/height")
        return {"x": x, "y": y, "w": w, "h": h}
    if isinstance(geo, Sequence) and len(geo) == 4:
        x, y, w, h = (int(v) for v in geo)
        return {"x": x, "y": y, "w": w, "h": h}
    raise TypeError(f"unsupported geometry type: {type(geo)!r}")


def redact_image(
    image: Image.Image,
    geometry: GeometryLike,
    *,
    fill: tuple[int, int, int] = (0, 0, 0),
) -> Image.Image:
    """
    Return a copy of ``image`` with the modal rectangle filled solid black
    (or ``fill``). Clips to image bounds.
    """
    g = normalize_geometry(geometry)
    out = image.convert("RGB").copy()
    draw = ImageDraw.Draw(out)
    x0 = max(0, g["x"])
    y0 = max(0, g["y"])
    x1 = min(out.width, g["x"] + g["w"])
    y1 = min(out.height, g["y"] + g["h"])
    if x1 > x0 and y1 > y0:
        draw.rectangle([x0, y0, x1 - 1, y1 - 1], fill=fill)
    return out


def redact_file(
    screenshot_path: Union[str, Path],
    geometry: GeometryLike | Union[str, Path],
    output_path: Union[str, Path],
) -> Path:
    """
    Load PNG, black out modal bounds, save redacted PNG.

    ``geometry`` may be a dict/list or a path to ``/tmp/darkroom-geometry.json``.
    """
    screenshot_path = Path(screenshot_path)
    output_path = Path(output_path)
    if isinstance(geometry, (str, Path)) and Path(geometry).exists():
        geo = load_geometry(geometry)
    else:
        geo = normalize_geometry(geometry)  # type: ignore[arg-type]

    with Image.open(screenshot_path) as im:
        redacted = redact_image(im, geo)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    redacted.save(output_path, format="PNG")
    return output_path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Black out Dark Room modal bounds in a screenshot PNG."
    )
    p.add_argument("screenshot", help="input PNG path")
    p.add_argument(
        "--geometry",
        "-g",
        default="/tmp/darkroom-geometry.json",
        help="geometry JSON path (default: /tmp/darkroom-geometry.json)",
    )
    p.add_argument(
        "--output",
        "-o",
        required=True,
        help="output redacted PNG path",
    )
    args = p.parse_args(argv)
    try:
        out = redact_file(args.screenshot, args.geometry, args.output)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
