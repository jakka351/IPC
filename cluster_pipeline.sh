#!/usr/bin/env bash
set -euo pipefail
# cluster_pipeline.sh
# This is more of a theoretical script at the moment of what
# the ultimate end process could be for editing and repacking
# the firmware.
# Usage: ./cluster_pipeline.sh path/to/firmware.vbf
# If you already have a .bin -> pass that instead.

INPUT="$1"
WORKDIR="$(pwd)/cluster_work"
mkdir -p "$WORKDIR"
echo "[*] workdir: $WORKDIR"

# 1) Install / build helpers (only if not present) - quick checks
command -v binwalk >/dev/null 2>&1 || { echo "Install binwalk (apt/yum/pip)."; exit 1; }
command -v dumpifs >/dev/null 2>&1 || echo "[!] dumpifs not found in PATH — use your dumpifs binary path."

# Optional: build kzbTools if not present in ./kzbTools
if [ ! -d "$WORKDIR/kzbTools" ]; then
  echo "[*] Cloning kzbTools (if you already have it, skip by creating $WORKDIR/kzbTools)..."
  git clone --depth 1 https://github.com/bigunclemax/kzbTools.git "$WORKDIR/kzbTools" || true
  if [ -d "$WORKDIR/kzbTools" ]; then
    mkdir -p "$WORKDIR/kzbTools/build"
    pushd "$WORKDIR/kzbTools/build" >/dev/null
      cmake .. || true
      make -j$(nproc) || true
    popd >/dev/null
    echo "[*] Built kzbTools (or left repo for you to build)."
  fi
fi

# 2) If input is a .vbf, extract .bin using python-VBF.py or binwalk method
BASE="$(basename "$INPUT")"
EXT="${BASE##*.}"
BINPATH=""
if [ "$EXT" = "vbf" ]; then
  echo "[*] Detected .vbf — extracting .bin (looking for python-VBF.py script)."
  # Try python-VBF.py in PATH or working dir
  if command -v python-VBF.py >/dev/null 2>&1; then
    python-VBF.py "$INPUT" -o "$WORKDIR" || echo "[!] python-VBF failed; check script usage."
    BINPATH=$(ls -1 "$WORKDIR"/*.bin 2>/dev/null | head -n1 || true)
  else
    echo "[!] python-VBF.py not found; try extracting with binwalk or provide the .bin directly."
  fi
fi

# If user passed a .bin or python step worked, detect it:
if [ -z "$BINPATH" ]; then
  if [ "$EXT" = "bin" ]; then
    BINPATH="$INPUT"
  else
    # try find .bin in workdir
    BINPATH=$(ls -1 "$WORKDIR"/*.bin 2>/dev/null | head -n1 || true)
  fi
fi
if [ -z "$BINPATH" ]; then
  echo "[ERROR] No .bin found. Provide a .bin or install/execute python-VBF.py first."; exit 2
fi
echo "[*] Using bin: $BINPATH"

# 3) Use dumpifs to list and extract kanzi .kzb from the bitmaps image
KZB_OUTDIR="$WORKDIR/kzb_extracted"
mkdir -p "$KZB_OUTDIR"
echo "[*] Running dumpifs -v to list contents (you probably already ran this)."
# dumpifs output varies; this will try to extract files
if command -v dumpifs >/dev/null 2>&1; then
  dumpifs -v "$BINPATH" > "$WORKDIR/dumpifs_listing.txt" || true
  # Try to extract all files to KZB_OUTDIR (dumpifs supports extract in some builds)
  # If your dumpifs supports extraction flag (some forks: dumpifs -x), change below:
  if dumpifs --help 2>&1 | grep -q "extract\|-x"; then
    dumpifs -x "$BINPATH" -o "$KZB_OUTDIR" || true
  else
    echo "[!] Your dumpifs may not support -x; you may need to use the GUI or a different fork."
  fi
else
  echo "[!] dumpifs not found. Manual step: run dumpifs on bitmaps.bin and pull out cluster.kzb into $KZB_OUTDIR"
fi

# 4) Carve out any .kzb or png assets using binwalk as fallback
echo "[*] Running binwalk carving for common assets inside bin..."
BINWALK_DIR="$WORKDIR/binwalk_extracted"
mkdir -p "$BINWALK_DIR"
binwalk -e "$BINPATH" -C "$BINWALK_DIR" || true
echo "[*] Check $BINWALK_DIR for cluster.kzb or carved PNGs/ZIPs."

# 5) If you have cluster.kzb, unpack it with kzbTools (replace binary path as needed)
# search common locations:
KZB_FILE="$(find "$KZB_OUTDIR" "$BINWALK_DIR" -type f -iname '*.kzb' 2>/dev/null | head -n1 || true)"
if [ -z "$KZB_FILE" ]; then
  echo "[!] No .kzb found automatically. Look under $KZB_OUTDIR and $BINWALK_DIR and place cluster.kzb there."
  echo "Exiting — place cluster.kzb in one of those dirs and re-run."
  exit 0
fi
echo "[*] Found kzb: $KZB_FILE"

# Attempt to use kzbTools unpacker (binary names may differ)
KZBTOOLS_BIN="$WORKDIR/kzbTools/build/kzbextract" # example; update for your build
if [ -f "$KZBTOOLS_BIN" ]; then
  KZB_UNPACK_DIR="$WORKDIR/kzb_unpacked"
  mkdir -p "$KZB_UNPACK_DIR"
  echo "[*] Running kzbTools unpack: $KZBTOOLS_BIN $KZB_FILE $KZB_UNPACK_DIR"
  "$KZBTOOLS_BIN" "$KZB_FILE" "$KZB_UNPACK_DIR" || echo "[!] kzbTools unpack failed — check CLI name and usage in repo."
else
  echo "[!] kzbTools binary not present at $KZBTOOLS_BIN. Inspect $WORKDIR/kzbTools/build for available binaries."
  echo "You can still inspect $KZB_FILE with binwalk or carve PNGs from it."
fi

# 6) Replace assets: example flow (this just shows automation intent)
REPLACEMENTS_DIR="$WORKDIR/replacements"
mkdir -p "$REPLACEMENTS_DIR"
# Place new PNGs in $REPLACEMENTS_DIR with exact filenames as in the unpacked kzb_unpacked assets
echo "[*] To replace images: drop PNGs into $REPLACEMENTS_DIR with the same filenames as inside the kzb unpack dir."
echo "Example: cp new_boot.png $REPLACEMENTS_DIR/boot_logo.png"

# 7) Repack step (placeholder) - you must use the kzbTools repack CLI (name varies)
echo "[*] REPACK STEP (manual):"
echo " - Use your kzbTools repacker (example: kzbpack <unpacked_dir> <out.kzb>)"
echo " - Verify file sizes and checksums. Some clusters require exact metadata and checksums to match."
echo " - Reinsert cluster.kzb into bitmaps.bin using the inverse of dumpifs packing (or file overwrite at the correct offset)."
echo " - Recreate .vbf with python-VBF.py (or vendor tools)."

echo "[*] Pipeline finished (partial). Inspect $WORKDIR for extracted files and follow the REPACK STEP notes."
echo "If you want, I can now: (A) produce a more specific repack script for your built kzbTools binary, or (B) write a small Python tool to search/replace PNG assets automatically inside unpacked folders and rebuild. Say which one and I'll spit out the exact code."
