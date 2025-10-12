#!/usr/bin/env python3
"""
KZB Tools GUI - Graphical interface for packing and unpacking KZB/KZBF files
Thread-safe UI fixes: all Tk calls run on main thread.
"""

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import struct
from pathlib import Path
from typing import List
import queue
import hashlib

FZBF_SIGN = b'KZBF'
HEADER_SIZE = 0x4C

def file_to_bytes(p: Path) -> bytearray:
    with open(p, 'rb') as f:
        return bytearray(f.read())

def buffer_to_file(out_path: Path, buf: bytes):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(buf)

'''
def escape_path(p: str) -> Path:
    safe = p.replace('\\', '/')
    parts = []
    for seg in safe.split('/'):
        if seg in ('', '.', '..'):
            continue
        seg = (seg.replace(':', '_').replace('*', '_').replace('?', '_')
                    .replace('"', "'").replace('<', '(').replace('>', ')')
                    .replace('|', '_'))
        parts.append(seg)
    return Path(*parts)
'''
# ---- ADD: Windows-safe name sanitizers and a safe string reader ----

_WIN_RESERVED = {
    "CON","PRN","AUX","NUL",
    *(f"COM{i}" for i in range(1,10)),
    *(f"LPT{i}" for i in range(1,10)),
}

def _strip_controls(s: str) -> str:
    # kill NUL and other control chars
    return ''.join(ch for ch in s if ch != '\x00' and ord(ch) >= 32)

def _fix_reserved(seg: str) -> str:
    seg = seg.rstrip(" .")              # windows: no trailing dot/space
    if not seg or seg.upper() in _WIN_RESERVED:
        return f"_{seg or 'unnamed'}_"
    return seg

def sanitize_name(raw: str, fallback: str) -> str:
    s = _strip_controls(raw)
    # neutralize separators and other illegal chars
    s = (s.replace('\\', '/')
           .replace('/', '_')
           .replace(':', '_')
           .replace('*', '_')
           .replace('?', '_')
           .replace('"', "'")
           .replace('<', '(')
           .replace('>', ')')
           .replace('|', '_'))
    s = _fix_reserved(s.strip())
    return s if s else fallback

def sanitize_path(p: str) -> Path:
    p = p.replace('\\', '/')
    parts = []
    for seg in p.split('/'):
        if seg in ('', '.', '..'):
            continue
        parts.append(shorten_segment(sanitize_name(seg, "unnamed"), 80))
    return Path(*parts)

def shorten_segment(seg: str, limit: int = 80) -> str:
    if len(seg) <= limit:
        return seg
    h = hashlib.md5(seg.encode('utf-8', 'ignore')).hexdigest()[:8]
    base, dot, ext = seg.rpartition('.')
    if dot and base:
        keep = max(1, limit - len(h) - 1 - len(ext) - 1)  # base + '_' + hash + '.' + ext
        return f"{base[:keep]}_{h}.{ext}"
    keep = max(1, limit - 1 - len(h))
    return f"{seg[:keep]}_{h}"

def fit_path_under(base_dir: Path, rel_path: Path, max_total: int = 240) -> Path:
    # shrink each segment first
    parts = [shorten_segment(p, 80) for p in rel_path.parts]
    rel2 = Path(*parts)
    full = base_dir / rel2
    if len(str(full)) <= max_total:
        return rel2

    # aggressively shrink the filename
    original_last = parts[-1]
    for limit in (80, 64, 48, 32, 24):
        parts[-1] = shorten_segment(original_last, limit)
        rel2 = Path(*parts)
        if len(str(base_dir / rel2)) <= max_total:
            return rel2

    # last resort: use a hash as the filename
    h = hashlib.md5(original_last.encode('utf-8', 'ignore')).hexdigest()[:16]
    parts[-1] = h
    return Path(*parts)

def escape_path(p: str) -> Path:
    # keep compatibility with your existing calls
    return sanitize_path(p)

def read_be_string(buf: bytearray, idx: int, max_len: int = 0x400):
    if idx + 2 > len(buf):
        raise RuntimeError("EOF while reading string length")
    slen = be16(buf[idx:idx+2]); idx += 2
    slen_cap = min(slen, max_len)
    if idx + slen_cap > len(buf):
        slen_cap = max(0, len(buf) - idx)
    raw = bytes(buf[idx:idx+slen_cap]); idx += slen_cap
    nul = raw.find(b'\x00')
    if nul >= 0:
        raw = raw[:nul]
    try:
        txt = raw.decode('utf-8', errors='ignore')
    except Exception:
        txt = ''
    aligned_idx = align4_idx(idx)
    return txt, aligned_idx, slen


def _strip_control(s: str) -> str:
    # remove NULs and other controls except TAB (keep it simple)
    return ''.join(ch for ch in s if ch not in '\x00' and ord(ch) >= 32)

def _win_fix_reserved(seg: str) -> str:
    base = seg.rstrip(" .")  # Windows forbids trailing space/dot
    if base.upper() in _WIN_RESERVED or base == "":
        base = f"_{base or 'unnamed'}_"
    return base

def sanitize_name(raw: str, fallback: str) -> str:
    # strip controls, then kill path separators, then fix reserved names
    s = _strip_control(raw)
    # neutralize path traversal / separators (both platforms)
    s = s.replace('\\', '/')
    s = s.replace('/', '_')
    # kill other nasties
    for bad, rep in ((':','_'), ('*','_'), ('?','_'), ('"',"'"),
                     ('<','('), ('>',')'), ('|','_')):
        s = s.replace(bad, rep)
    s = s.strip()
    s = _win_fix_reserved(s)
    return s if s else fallback


def align4_idx(idx: int) -> int:
    return (idx + 3) & ~3

def be16(b: bytes) -> int:
    return struct.unpack('>H', b)[0]

def be32(b: bytes) -> int:
    return struct.unpack('>I', b)[0]

def put_be16(v: int) -> bytes:
    return struct.pack('>H', v & 0xFFFF)

def put_be32(v: int) -> bytes:
    return struct.pack('>I', v & 0xFFFFFFFF)

class KZBProcessor:
    def __init__(self, log_callback):
        self.log = log_callback
        self.G_extract = True
        self.G_extract_path = Path()
        self.G_idx = 0
        self.G_bin = bytearray()

    # ---------------- KZB helpers ----------------
    def extract_resource(self, resource_path: Path, address: int, size: int):
        start = address + 4
        end = start + size
        safe_rel = fit_path_under(self.G_extract_path, resource_path, 240)
        buffer_to_file(self.G_extract_path / safe_rel, self.G_bin[start:end])

    def parse_elements(self, prefix: Path, count: int, depth: int) -> int:
        for i in range(count):
            addr = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4
            size = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4
            unk1 = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4
            unk2 = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4

            raw_name, self.G_idx, _str_sz = read_be_string(self.G_bin, self.G_idx)
            safe_name = sanitize_name(raw_name, f"elem_{addr:08x}")

            file_path = prefix / escape_path(safe_name)
            self.log("\t"*depth + (
                f"File: raw='{raw_name}' -> safe='{safe_name}' "
                f"Addr=0x{addr:08x} Size={size} Unk1=0x{unk1:08x} Unk2=0x{unk2:08x}"
            ))

            if self.G_extract:
                self.extract_resource(file_path, addr, size)
        return 0  # <-- after the loop (you had this inside the loop before)

    def parse_folder(self, prefix: Path, depth: int) -> int:
        size = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4

        raw_name, self.G_idx, _ = read_be_string(self.G_bin, self.G_idx)
        safe_name = sanitize_name(raw_name, f"folder_{self.G_idx:08x}")

        count = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4
        last_folder = (count == 0)
        if last_folder:
            elem_count = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4
        else:
            elem_count = None

        folder_path = prefix / f"Folder_{safe_name}"
        self.log("\t"*depth + f"Folder: raw='{raw_name}' -> safe='{safe_name}' Size=0x{size:x} Count={count}")

        if self.G_extract:
            (self.G_extract_path / escape_path(str(folder_path))).mkdir(parents=True, exist_ok=True)

        if last_folder:
            self.parse_elements(folder_path, elem_count, depth+1)
        else:
            processed_size = 0
            for _ in range(count):
                processed_size += self.parse_folder(folder_path, depth+1)
            if processed_size != size:
                elem_count2 = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4
                self.log("\t"*depth + f"(mixed) elem_count={elem_count2}, processed_size=0x{processed_size:x} vs declared=0x{size:x}")
                self.parse_elements(folder_path, elem_count2, depth+1)

        return size



    def parse_kzb(self, in_file: Path):
        self.G_idx = HEADER_SIZE

        # root name
        str_sz = be16(self.G_bin[self.G_idx:self.G_idx+2]); self.G_idx += 2
        root_name = self.G_bin[self.G_idx:self.G_idx+str_sz].decode('utf-8', errors='ignore'); self.G_idx += str_sz
        self.G_idx = align4_idx(self.G_idx)

        # unk1,2,3, zero
        self.G_idx += 4 * 4
        count = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4

        self.log(f"Root: {root_name} (Folders: {count})")
        for _ in range(count):
            self.parse_folder(Path(), 1)

        self.log(f"Extraction completed at offset 0x{self.G_idx:x}")

    # ---------------- KZBF helpers ----------------
    def extract_resource_kzbf(self, resource_path: Path, address: int, size: int):
        safe_rel = fit_path_under(self.G_extract_path, resource_path, 240)
        path = (self.G_extract_path / safe_rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path = path.with_name('r_' + path.name)
        buffer_to_file(path, self.G_bin[address:address+size])

    def parse_kzbf(self, in_file: Path):
        # defensive bounds check
        def need(n: int):
            if self.G_idx + n > len(self.G_bin):
                raise RuntimeError("KZBF: unexpected EOF while parsing")

        # header-ish
        need(4)
        _unk = int.from_bytes(self.G_bin[self.G_idx:self.G_idx+4], 'little'); self.G_idx += 4
        need(4)
        str_sz = int.from_bytes(self.G_bin[self.G_idx:self.G_idx+4], 'little'); self.G_idx += 4
        need(str_sz)
        root_name = self.G_bin[self.G_idx:self.G_idx+str_sz].decode('utf-8', errors='ignore'); self.G_idx += str_sz
        need(4)
        count = int.from_bytes(self.G_bin[self.G_idx:self.G_idx+4], 'little'); self.G_idx += 4

        # nodes (NUL-terminated strings)
        nodes = []
        for _ in range(count):
            sbytes = []
            while self.G_idx < len(self.G_bin) and self.G_bin[self.G_idx] != 0:
                sbytes.append(self.G_bin[self.G_idx])
                self.G_idx += 1
            if self.G_idx >= len(self.G_bin):
                raise RuntimeError("KZBF: unterminated node string")
            self.G_idx += 1  # skip NUL
            node_raw = bytes(sbytes).decode('utf-8', errors='ignore')
            node = sanitize_name(node_raw, f"node_{len(nodes):04d}")
            nodes.append(node)

        self.log(f"KZBF Nodes count: {len(nodes)}")

        # elements table
        need(4)
        elem_count = int.from_bytes(self.G_bin[self.G_idx:self.G_idx+4], 'little'); self.G_idx += 4
        elems = []
        for _ in range(elem_count):
            need(24)
            idx, unk1, addr, size, unk4, unk5 = struct.unpack('<6I', self.G_bin[self.G_idx:self.G_idx+24])
            self.G_idx += 24
            if unk4 != 0:
                raise RuntimeError("kzbf: unk4 not zero")
            if unk5 != size:
                raise RuntimeError("kzbf: unk5 != size")
            elems.append((idx, unk1, addr, size))

        # list
        for i, node in enumerate(nodes):
            idx, _unk1, addr, size = elems[i]
            self.log(f"{idx:04d} 0x{addr:08x} 0x{size:08x} {node}")

        # extract
        for i, node in enumerate(nodes):
            _idx, _unk1, addr, size = elems[i]
            local = addr
            target = escape_path(node)
            if '.png' in node.lower():
                local += 5 * 4
                if self.G_extract:
                    self.extract_resource_kzbf(target, local, size - (5 * 4))
            else:
                if self.G_extract:
                    self.extract_resource_kzbf(target, local, size)

    # ---------------- entry point ----------------
    def unpack(self, in_file: Path) -> Path:
        self.G_extract = True
        self.G_extract_path = in_file.parent / f"{in_file.name}_unpacked"
        self.G_extract_path.mkdir(exist_ok=True)

        self.G_idx = 0
        self.G_bin = file_to_bytes(in_file)

        sign = bytes(self.G_bin[0:4])
        self.G_idx += 4
        if sign != FZBF_SIGN:
            self.parse_kzb(in_file)
        else:
            self.parse_kzbf(in_file)

        return self.G_extract_path


   

    def extract_resource_kzbf(self, resource_path: Path, address: int, size: int):
        path = (self.G_extract_path / resource_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path = path.with_name('r_' + path.name)
        buffer_to_file(path, self.G_bin[address:address+size])

    def parse_kzbf(self, in_file: Path):
        # Defensive bounds checks to avoid runaway loops
        def need(n):
            if self.G_idx + n > len(self.G_bin):
                raise RuntimeError("KZBF: unexpected EOF while parsing")

   


    def unpack(self, in_file: Path) -> Path:
        self.G_extract = True
        self.G_extract_path = in_file.parent / f"{in_file.name}_unpacked"
        self.G_extract_path.mkdir(exist_ok=True)

        self.G_idx = 0
        self.G_bin = file_to_bytes(in_file)

        sign = bytes(self.G_bin[0:4])
        self.G_idx += 4
        if sign != FZBF_SIGN:
            self.parse_kzb(in_file)
        else:
            self.parse_kzbf(in_file)

        return self.G_extract_path


class ElementInfo:
    def __init__(self, name: str, disk_path: Path, size: int):
        self.name = name
        self.disk_path = disk_path
        self.size = size

class FolderNode:
    def __init__(self, name: str):
        self.name = name
        self.children = []
        self.elements = []

class MetaFolderPH:
    def __init__(self, size_pos: int):
        self.size_pos = size_pos

class MetaElemPH:
    def __init__(self, addr_pos: int, element: ElementInfo):
        self.addr_pos = addr_pos
        self.element = element

def build_node_from_fs(p: Path) -> FolderNode:
    name = p.name
    if name.startswith('Folder_'):
        name = name[len('Folder_'):]
    node = FolderNode(name)
    entries = sorted(list(p.iterdir()), key=lambda x: x.name)
    for e in entries:
        if e.is_dir():
            node.children.append(build_node_from_fs(e))
        elif e.is_file():
            node.elements.append(ElementInfo(e.name, e, e.stat().st_size))
    return node

def compute_total_data_size(node: FolderNode) -> int:
    total = sum(4 + el.size for el in node.elements)
    for c in node.children:
        total += compute_total_data_size(c)
    return total

def write_root_header(root_name: str, top_count: int, meta: bytearray):
    meta += put_be16(len(root_name))
    meta += root_name.encode('utf-8', errors='ignore')
    while len(meta) % 4 != 0:
        meta += b'\x00'
    # unk1, unk2, unk3, zero
    meta += put_be32(0)
    meta += put_be32(0)
    meta += put_be32(0)
    meta += put_be32(0)
    meta += put_be32(top_count)

def write_folder_metadata(node: FolderNode, meta: bytearray,
                          folderPH: List[MetaFolderPH],
                          elemPH: List[MetaElemPH]):
    folderPH.append(MetaFolderPH(len(meta)))
    meta += put_be32(0)

    meta += put_be16(len(node.name))
    meta += node.name.encode('utf-8', errors='ignore')
    while len(meta) % 4 != 0:
        meta += b'\x00'

    if not node.children:
        meta += put_be32(0)
        meta += put_be32(len(node.elements))
        for el in node.elements:
            elemPH.append(MetaElemPH(len(meta), el))
            meta += put_be32(0)
            meta += put_be32(el.size)
            meta += put_be32(0)
            meta += put_be32(0)
            meta += put_be16(len(el.name))
            meta += el.name.encode('utf-8', errors='ignore')
            while len(meta) % 4 != 0:
                meta += b'\x00'
    else:
        meta += put_be32(len(node.children))
        for c in node.children:
            write_folder_metadata(c, meta, folderPH, elemPH)
        if node.elements:
            meta += put_be32(len(node.elements))
            for el in node.elements:
                elemPH.append(MetaElemPH(len(meta), el))
                meta += put_be32(0)
                meta += put_be32(el.size)
                meta += put_be32(0)
                meta += put_be32(0)
                meta += put_be16(len(el.name))
                meta += el.name.encode('utf-8', errors='ignore')
                while len(meta) % 4 != 0:
                    meta += b'\x00'

def pack_kzb(extracted_dir: Path, output_file: Path, log_callback) -> int:
    if not extracted_dir.exists() or not extracted_dir.is_dir():
        log_callback(f"ERROR: Input directory not found: {extracted_dir}")
        return 2

    root = FolderNode(extracted_dir.name)
    tops = sorted(list(extracted_dir.iterdir()), key=lambda x: x.name)
    for de in tops:
        if de.is_dir():
            root.children.append(build_node_from_fs(de))
        elif de.is_file():
            root.elements.append(ElementInfo(de.name, de, de.stat().st_size))

    meta = bytearray()
    top_count = len(root.children) + (0 if not root.elements else 1)
    write_root_header(root.name, top_count, meta)

    folderPH: List[MetaFolderPH] = []
    elemPH: List[MetaElemPH] = []

    for child in root.children:
        write_folder_metadata(child, meta, folderPH, elemPH)

    if root.elements:
        synth = FolderNode(root.name + "_rootfiles")
        synth.elements = list(root.elements)
        write_folder_metadata(synth, meta, folderPH, elemPH)

    folder_sizes = []
    for child in root.children:
        folder_sizes.append(compute_total_data_size(child))
    if root.elements:
        folder_sizes.append(compute_total_data_size(synth))

    for ph, sz in zip(folderPH, folder_sizes):
        meta[ph.size_pos:ph.size_pos+4] = put_be32(sz)

    out = bytearray(b'\x00' * HEADER_SIZE)
    out[0:4] = b'kzbf'  # NOT "KZBF" so we go KZB path

    out.extend(meta)
    while len(out) % 4 != 0:
        out.append(0)

    log_callback(f"Writing {len(elemPH)} resources...")
    for i, ph in enumerate(elemPH):
        if i % 100 == 0:
            log_callback(f"  Progress: {i}/{len(elemPH)}")
        addr_abs = len(out)
        out[HEADER_SIZE + ph.addr_pos : HEADER_SIZE + ph.addr_pos + 4] = put_be32(addr_abs)
        out.extend(b'\x00\x00\x00\x00')
        with open(ph.element.disk_path, 'rb') as f:
            data = f.read()
        out.extend(data)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'wb') as f:
        f.write(out)
    log_callback(f"SUCCESS: Packed KZB written: {output_file} ({len(out)} bytes)")
    return 0


class KZBToolsGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("KZB Tools - Pack & Unpack")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)

        # Queue for thread-safe logging
        self.log_queue = queue.Queue()
        self.check_log_queue()

        # Accent style fallback (won't crash if theme lacks Accent)
        try:
            style = ttk.Style()
            if "Azure" in style.theme_names():
                style.theme_use("Azure")
            style.configure('Accent.TButton')
        except Exception:
            pass

        self.create_widgets()

    def dispatch_ui(self, fn, *args, **kwargs):
        """Run a callable on the Tk thread."""
        self.root.after(0, lambda: fn(*args, **kwargs))

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        title = ttk.Label(main_frame, text="KZB Tools", font=('Arial', 16, 'bold'))
        title.grid(row=0, column=0, columnspan=3, pady=(0, 10))

        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        unpack_frame = ttk.Frame(notebook, padding="10")
        notebook.add(unpack_frame, text="Unpack KZB/KZBF")
        self.create_unpack_tab(unpack_frame)

        pack_frame = ttk.Frame(notebook, padding="10")
        notebook.add(pack_frame, text="Pack KZB")
        self.create_pack_tab(pack_frame)

    def create_unpack_tab(self, parent):
        ttk.Label(parent, text="Input KZB/KZBF File:").grid(row=0, column=0, sticky=tk.W, pady=5)

        self.unpack_input = tk.StringVar()
        input_entry = ttk.Entry(parent, textvariable=self.unpack_input, width=60)
        input_entry.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))

        browse_btn = ttk.Button(parent, text="Browse...", command=self.browse_unpack_input)
        browse_btn.grid(row=0, column=2, padx=5, pady=5)

        unpack_btn = ttk.Button(parent, text="Unpack File", command=self.unpack_file, style='Accent.TButton')
        unpack_btn.grid(row=1, column=0, columnspan=3, pady=10)

        ttk.Label(parent, text="Log:").grid(row=2, column=0, sticky=tk.W, pady=(10, 5))

        self.unpack_log = scrolledtext.ScrolledText(parent, height=20, width=70, state='disabled')
        self.unpack_log.grid(row=3, column=0, columnspan=3, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))

        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(3, weight=1)

    def create_pack_tab(self, parent):
        ttk.Label(parent, text="Input Directory:").grid(row=0, column=0, sticky=tk.W, pady=5)

        self.pack_input = tk.StringVar()
        input_entry = ttk.Entry(parent, textvariable=self.pack_input, width=60)
        input_entry.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))

        browse_btn = ttk.Button(parent, text="Browse...", command=self.browse_pack_input)
        browse_btn.grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(parent, text="Output KZB File:").grid(row=1, column=0, sticky=tk.W, pady=5)

        self.pack_output = tk.StringVar()
        output_entry = ttk.Entry(parent, textvariable=self.pack_output, width=60)
        output_entry.grid(row=1, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))

        browse_btn = ttk.Button(parent, text="Browse...", command=self.browse_pack_output)
        browse_btn.grid(row=1, column=2, padx=5, pady=5)

        pack_btn = ttk.Button(parent, text="Pack to KZB", command=self.pack_file, style='Accent.TButton')
        pack_btn.grid(row=2, column=0, columnspan=3, pady=10)

        ttk.Label(parent, text="Log:").grid(row=3, column=0, sticky=tk.W, pady=(10, 5))

        self.pack_log = scrolledtext.ScrolledText(parent, height=20, width=70, state='disabled')
        self.pack_log.grid(row=4, column=0, columnspan=3, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))

        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(4, weight=1)

    def browse_unpack_input(self):
        filename = filedialog.askopenfilename(
            title="Select KZB/KZBF file",
            filetypes=[("KZB files", "*.kzb"), ("KZBF files", "*.kzbf"), ("All files", "*.*")]
        )
        if filename:
            self.unpack_input.set(filename)

    def browse_pack_input(self):
        dirname = filedialog.askdirectory(title="Select extracted directory")
        if dirname:
            self.pack_input.set(dirname)

    def browse_pack_output(self):
        filename = filedialog.asksaveasfilename(
            title="Save KZB file as",
            defaultextension=".kzb",
            filetypes=[("KZB files", "*.kzb"), ("All files", "*.*")]
        )
        if filename:
            self.pack_output.set(filename)

    def log_to_widget(self, widget, message):
        self.log_queue.put((widget, message))

    def check_log_queue(self):
        try:
            while True:
                widget, message = self.log_queue.get_nowait()
                widget.configure(state='normal')
                widget.insert(tk.END, message + '\n')
                widget.see(tk.END)
                widget.configure(state='disabled')
        except queue.Empty:
            pass
        self.root.after(100, self.check_log_queue)

    def unpack_file(self):
        input_file = self.unpack_input.get()
        if not input_file:
            messagebox.showerror("Error", "Please select an input file")
            return
        if not Path(input_file).exists():
            messagebox.showerror("Error", "Input file does not exist")
            return

        self.unpack_log.configure(state='normal')
        self.unpack_log.delete(1.0, tk.END)
        self.unpack_log.configure(state='disabled')

        def run_unpack():
            try:
                processor = KZBProcessor(lambda msg: self.log_to_widget(self.unpack_log, msg))
                output_dir = processor.unpack(Path(input_file))
                self.log_to_widget(self.unpack_log, f"\n✓ Extraction complete!")
                self.log_to_widget(self.unpack_log, f"Output directory: {output_dir}")
                # UI thread messagebox
                self.dispatch_ui(messagebox.showinfo, "Success", f"File unpacked successfully!\n\nOutput: {output_dir}")
            except Exception as e:
                self.log_to_widget(self.unpack_log, f"\n✗ ERROR: {str(e)}")
                self.dispatch_ui(messagebox.showerror, "Error", f"Unpacking failed:\n{str(e)}")

        threading.Thread(target=run_unpack, daemon=True).start()

    def pack_file(self):
        input_dir = self.pack_input.get()
        output_file = self.pack_output.get()

        if not input_dir:
            messagebox.showerror("Error", "Please select an input directory")
            return
        if not output_file:
            messagebox.showerror("Error", "Please select an output file")
            return
        if not Path(input_dir).exists():
            messagebox.showerror("Error", "Input directory does not exist")
            return

        self.pack_log.configure(state='normal')
        self.pack_log.delete(1.0, tk.END)
        self.pack_log.configure(state='disabled')

        def run_pack():
            try:
                result = pack_kzb(
                    Path(input_dir),
                    Path(output_file),
                    lambda msg: self.log_to_widget(self.pack_log, msg)
                )
                if result == 0:
                    self.dispatch_ui(messagebox.showinfo, "Success", f"File packed successfully!\n\nOutput: {output_file}")
                else:
                    self.dispatch_ui(messagebox.showerror, "Error", "Packing failed. Check the log for details.")
            except Exception as e:
                self.log_to_widget(self.pack_log, f"\n✗ ERROR: {str(e)}")
                self.dispatch_ui(messagebox.showerror, "Error", f"Packing failed:\n{str(e)}")

        threading.Thread(target=run_pack, daemon=True).start()

def main():
    root = tk.Tk()
    app = KZBToolsGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()
kzb_backup.py
