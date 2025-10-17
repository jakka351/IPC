"""
spritesheet_logo_apply.py

Stamp a transparent PNG logo at the center of every sub-image in a spritesheet.

- Works with any sheet size as long as it's a uniform grid (default 4x4).
- Resizes the logo to fit within each tile using a max scale ratio.
- Preserves alpha; no GUI code required (safe to call from Tkinter).
- Requires Pillow (PIL):  pip install pillow

Typical CLI usage:
    python spritesheet_logo_apply.py \
        --sheet "path/to/sheet.png" \
        --logo "path/to/logo.png" \
        --out  "path/to/out.png" \
        --rows 4 --cols 4 --max-ratio 0.45 --padding 0
"""

from __future__ import annotations
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image
import argparse


def _ensure_rgba(img: Image.Image) -> Image.Image:
    """Return an RGBA image (convert if needed)."""
    return img if img.mode == "RGBA" else img.convert("RGBA")


def _resize_logo_to_fit(
    logo_rgba: Image.Image,
    tile_size: Tuple[int, int],
    max_ratio: float,
    padding_px: int,
    resample=Image.LANCZOS,
) -> Image.Image:
    """
    Resize logo to fit within a tile.
    - max_ratio is the fraction of tile's min dimension used as the logo's max side.
    - padding_px is subtracted from BOTH width and height capacity.
    """
    tile_w, tile_h = tile_size
    if tile_w <= 0 or tile_h <= 0:
        raise ValueError("Tile width/height computed as <= 0")

    # Target box the logo must fit into
    max_side = int(max_ratio * min(tile_w, tile_h))
    max_w = max_side - 2 * padding_px
    max_h = max_side - 2 * padding_px
    max_w = max(1, max_w)
    max_h = max(1, max_h)

    lw, lh = logo_rgba.width, logo_rgba.height
    if lw <= 0 or lh <= 0:
        raise ValueError("Logo has invalid dimensions")

    # Keep aspect ratio
    scale = min(max_w / lw, max_h / lh, 1.0)
    new_w = max(1, int(round(lw * scale)))
    new_h = max(1, int(round(lh * scale)))
    if (new_w, new_h) == (lw, lh):
        return logo_rgba
    return logo_rgba.resize((new_w, new_h), resample=resample)


def apply_logo_to_spritesheet(
    sheet_img: Image.Image,
    logo_img: Image.Image,
    rows: int = 4,
    cols: int = 4,
    max_ratio: float = 0.45,
    padding_px: int = 0,
) -> Image.Image:
    """
    Paste `logo_img` centered on every tile in `sheet_img`.

    Args:
        sheet_img: PIL Image (any mode). Treated as a spritesheet.
        logo_img : Transparent PNG (ideally) with the logo.
        rows, cols: grid layout (default 4x4).
        max_ratio: logo max side as fraction of min(tile_w, tile_h).
        padding_px: padding from tile edges (applied to width and height).

    Returns:
        New PIL Image with the logo stamped on each tile.
    """
    if rows <= 0 or cols <= 0:
        raise ValueError("rows and cols must be positive integers")

    W, H = sheet_img.size
    if W % cols != 0 or H % rows != 0:
        raise ValueError(
            f"Sheet size {W}x{H} not divisible by grid {cols}x{rows}."
        )

    tile_w, tile_h = W // cols, H // rows

    base = _ensure_rgba(sheet_img)  # work in RGBA so alpha composite is clean
    logo_rgba = _ensure_rgba(logo_img)
    logo_resized = _resize_logo_to_fit(
        logo_rgba, (tile_w, tile_h), max_ratio=max_ratio, padding_px=padding_px
    )

    out = base.copy()
    lw, lh = logo_resized.size

    # Paste on each tile center
    for r in range(rows):
        for c in range(cols):
            x0 = c * tile_w
            y0 = r * tile_h
            cx = x0 + tile_w // 2
            cy = y0 + tile_h // 2
            paste_x = int(cx - lw // 2)
            paste_y = int(cy - lh // 2)
            out.alpha_composite(logo_resized, dest=(paste_x, paste_y))

    # If original sheet was opaque, you can convert back to RGB; otherwise keep RGBA
    return out


def apply_logo_to_spritesheet_from_paths(
    sheet_path: str | Path,
    logo_path: str | Path,
    out_path: str | Path,
    rows: int = 4,
    cols: int = 4,
    max_ratio: float = 0.45,
    padding_px: int = 0,
    keep_alpha: bool = True,
) -> Path:
    """
    File-path convenience wrapper (handy for scripting or wiring into a GUI action).
    """
    sheet_path = Path(sheet_path)
    logo_path = Path(logo_path)
    out_path = Path(out_path)

    if not sheet_path.exists():
        raise FileNotFoundError(f"Sheet not found: {sheet_path}")
    if not logo_path.exists():
        raise FileNotFoundError(f"Logo not found: {logo_path}")

    sheet_img = Image.open(sheet_path)
    logo_img = Image.open(logo_path)

    result = apply_logo_to_spritesheet(
        sheet_img=sheet_img,
        logo_img=logo_img,
        rows=rows,
        cols=cols,
        max_ratio=max_ratio,
        padding_px=padding_px,
    )

    if not keep_alpha:
        # Drop alpha if you want a plain RGB output
        result = result.convert("RGB")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    # PNG preserves transparency if present
    result.save(out_path, format="PNG", optimize=True)
    return out_path


def _parse_cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Apply a transparent PNG logo to the center of each tile in a spritesheet."
    )
    p.add_argument("--sheet", required=True, help="Path to the spritesheet image")
    p.add_argument("--logo", required=True, help="Path to the transparent PNG logo")
    p.add_argument("--out", required=True, help="Output image path (PNG recommended)")
    p.add_argument("--rows", type=int, default=4, help="Grid rows (default: 4)")
    p.add_argument("--cols", type=int, default=4, help="Grid cols (default: 4)")
    p.add_argument(
        "--max-ratio",
        type=float,
        default=0.45,
        help="Logo max side as fraction of min(tile_w,tile_h) (default: 0.45)",
    )
    p.add_argument(
        "--padding",
        type=int,
        default=0,
        help="Padding (px) inside each tile bounding box (default: 0)",
    )
    p.add_argument(
        "--no-alpha",
        action="store_true",
        help="Convert output to RGB (drop alpha) before saving",
    )
    return p.parse_args()


def main() -> None:
    args = _parse_cli()
    out = apply_logo_to_spritesheet_from_paths(
        sheet_path=args.sheet,
        logo_path=args.logo,
        out_path=args.out,
        rows=args.rows,
        cols=args.cols,
        max_ratio=args.max_ratio,
        padding_px=args.padding,
        keep_alpha=not args.no_alpha,
    )
    print(f"Wrote: {out}")


if __name__ == "__main__":
    main()
