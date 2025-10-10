#!/usr/bin/env python3
"""
unzlib.py — Extract zlib-compressed data (and friends)
- Auto-detects zlib, gzip, or raw DEFLATE.
- Streams in chunks (no RAM faceplant on big files).
"""

import argparse
import sys
from pathlib import Path
import zlib
import gzip

CHUNK = 1024 * 1024  # 1 MiB, because we're not animals.

def detect_format(head: bytes) -> str:
    """
    Return 'zlib', 'gzip', or 'deflate' (raw) based on magic bytes.
    """
    if len(head) >= 2 and head[0] == 0x1F and head[1] == 0x8B:
        return "gzip"
    if len(head) >= 2 and head[0] == 0x78 and head[1] in (0x01, 0x5E, 0x9C, 0xDA, 0x20):
        # 0x78 + common FLG values for zlib (CMF/FLG combos)
        return "zlib"
    # Could be zlib with uncommon flags; we'll try zlib first then raw.
    return "unknown"

def make_default_output(in_path: Path) -> Path:
    # Drop known extensions, otherwise append .out
    for ext in (".zlib", ".zz", ".z", ".deflate", ".gz"):
        if in_path.name.lower().endswith(ext):
            return in_path.with_suffix("")
    return in_path.with_suffix(in_path.suffix + ".out")

def decompress_zlib_stream(in_fh, out_fh) -> None:
    decomp = zlib.decompressobj()  # zlib wrapper
    while True:
        chunk = in_fh.read(CHUNK)
        if not chunk:
            break
        out_fh.write(decomp.decompress(chunk))
    out_fh.write(decomp.flush())

def decompress_raw_deflate(in_fh, out_fh) -> None:
    # wbits=-15 means "raw" deflate with no zlib/gzip wrapper
    decomp = zlib.decompressobj(wbits=-15)
    while True:
        chunk = in_fh.read(CHUNK)
        if not chunk:
            break
        out_fh.write(decomp.decompress(chunk))
    out_fh.write(decomp.flush())

def decompress_gzip_stream(in_fh, out_fh) -> None:
    with gzip.GzipFile(fileobj=in_fh, mode="rb") as gz:
        while True:
            chunk = gz.read(CHUNK)
            if not chunk:
                break
            out_fh.write(chunk)

def main():
    p = argparse.ArgumentParser(description="Extract zlib/gzip/deflate streams without drama.")
    p.add_argument("input", help="Input file path or '-' for stdin")
    p.add_argument("-o", "--output", help="Output file path (defaults next to input or stdout if input is '-')")
    args = p.parse_args()

    # Open input
    if args.input == "-":
        in_fh = sys.stdin.buffer
        head = in_fh.peek(2)[:2] if hasattr(in_fh, "peek") else in_fh.read(2)
        if not hasattr(in_fh, "peek"):
            # put the 2 bytes back into a BytesIO wrapper
            from io import BytesIO
            rest = in_fh.read()
            in_fh = BytesIO(head + rest)
        out_fh = sys.stdout.buffer if not args.output else open(args.output, "wb")
        close_out = args.output is not None
        fmt = detect_format(head)
    else:
        in_path = Path(args.input)
        if not in_path.exists() or not in_path.is_file():
            p.error(f"Input file not found: {in_path}")
        with open(in_path, "rb") as f:
            head = f.read(2)
        fmt = detect_format(head)
        # Determine output path
        if args.output:
            out_path = Path(args.output)
        else:
            out_path = make_default_output(in_path)
        in_fh = open(in_path, "rb")
        out_fh = open(out_path, "wb")
        close_out = True

    try:
        # Try the most likely format first, fall back if it blows up.
        if fmt == "gzip":
            decompress_gzip_stream(in_fh, out_fh)
        elif fmt == "zlib":
            try:
                decompress_zlib_stream(in_fh, out_fh)
            except zlib.error:
                # Some weird headers slip through; try raw deflate as a fallback.
                in_fh.seek(0)
                decompress_raw_deflate(in_fh, out_fh)
        else:
            # Unknown: try zlib then raw deflate
            pos = in_fh.tell()
            try:
                decompress_zlib_stream(in_fh, out_fh)
            except zlib.error:
                in_fh.seek(pos)
                decompress_raw_deflate(in_fh, out_fh)

    except (zlib.error, OSError, EOFError) as e:
        # Clean up partial output on failure (don’t leave junk lying around).
        if close_out and hasattr(out_fh, "name"):
            try:
                out_name = out_fh.name
                out_fh.close()
            except Exception:
                out_name = None
            if out_name:
                try:
                    Path(out_name).unlink(missing_ok=True)
                except Exception:
                    pass
        msg = f"Decompression failed: {e}"
        print(msg, file=sys.stderr)
        sys.exit(2)
    finally:
        if args.input != "-":
            in_fh.close()
        if close_out:
            out_fh.close()

if __name__ == "__main__":
    main()
