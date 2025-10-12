#!/usr/bin/env python3
"""
KZB Tools GUI - Graphical interface for packing and unpacking KZB/KZBF files
"""

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import sys
import struct
from pathlib import Path
from typing import List
import queue

# Import the backend functions
FZBF_SIGN = b'KZBF'
HEADER_SIZE = 0x4C

# Backend utility functions
def file_to_bytes(p: Path) -> bytearray:
    with open(p, 'rb') as f:
        return bytearray(f.read())

def buffer_to_file(out_path: Path, buf: bytes):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(buf)

def escape_path(p: str) -> Path:
    safe = p.replace('\\', '/')
    parts = []
    for seg in safe.split('/'):
        if seg in ('', '.', '..'):
            continue
        seg = seg.replace(':', '_').replace('*', '_').replace('?', '_').replace('"', "'").replace('<', '(').replace('>', ')').replace('|', '_')
        parts.append(seg)
    return Path(*parts)

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

# Backend extraction functions
class KZBProcessor:
    def __init__(self, log_callback):
        self.log = log_callback
        self.G_extract = True
        self.G_extract_path = Path()
        self.G_idx = 0
        self.G_bin = bytearray()

    def extract_resource(self, resource_path: Path, address: int, size: int):
        start = address + 4
        end = start + size
        buffer_to_file(self.G_extract_path / resource_path, self.G_bin[start:end])

    def parse_elements(self, prefix: Path, count: int, depth: int) -> int:
        for _ in range(count):
            addr = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4
            size = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4
            unk1 = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4
            unk2 = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4

            str_sz = be16(self.G_bin[self.G_idx:self.G_idx+2]); self.G_idx += 2
            name = self.G_bin[self.G_idx:self.G_idx+str_sz].decode('utf-8', errors='ignore'); self.G_idx += str_sz
            self.G_idx = align4_idx(self.G_idx)

            file_path = prefix / escape_path(name)
            self.log("\t"*depth + f"File: {name} Size: 0x{size:x}({size})")

            if self.G_extract:
                self.extract_resource(escape_path(str(file_path)), addr, size)
        return 0

    def parse_folder(self, prefix: Path, depth: int) -> int:
        size = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4

        str_sz = be16(self.G_bin[self.G_idx:self.G_idx+2]); self.G_idx += 2
        name = self.G_bin[self.G_idx:self.G_idx+str_sz].decode('utf-8', errors='ignore'); self.G_idx += str_sz
        self.G_idx = align4_idx(self.G_idx)

        count = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4
        last_folder = (count == 0)
        if last_folder:
            count = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4

        folder_path = prefix / f"Folder_{name}"
        self.log("\t"*depth + f"Folder: {name} Count: {count}")

        if self.G_extract:
            (self.G_extract_path / escape_path(str(folder_path))).mkdir(parents=True, exist_ok=True)

        if last_folder:
            self.parse_elements(folder_path, count, depth+1)
        else:
            for _ in range(count):
                self.parse_folder(folder_path, depth+1)
            if self.G_idx + 4 <= len(self.G_bin):
                elem_count = be32(self.G_bin[self.G_idx:self.G_idx+4])
                if elem_count:
                    self.G_idx += 4
                    self.parse_elements(folder_path, elem_count, depth+1)
        return size

    def parse_kzb(self, in_file: Path):
        self.G_idx = HEADER_SIZE

        str_sz = be16(self.G_bin[self.G_idx:self.G_idx+2]); self.G_idx += 2
        root_name = self.G_bin[self.G_idx:self.G_idx+str_sz].decode('utf-8', errors='ignore'); self.G_idx += str_sz
        self.G_idx = align4_idx(self.G_idx)

        self.G_idx += 16  # skip unk1-4
        count = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4

        self.log(f"Root: {root_name} (Folders: {count})")
        for _ in range(count):
            self.parse_folder(Path(), 1)

        self.log(f"Extraction completed at offset 0x{self.G_idx:x}")

    def extract_resource_kzbf(self, resource_path: Path, address: int, size: int):
        path = (self.G_extract_path / resource_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path = path.with_name('r_' + path.name)
        buffer_to_file(path, self.G_bin[address:address+size])

    def parse_kzbf(self, in_file: Path):
        unk = int.from_bytes(self.G_bin[self.G_idx:self.G_idx+4], 'little'); self.G_idx += 4

        str_sz = int.from_bytes(self.G_bin[self.G_idx:self.G_idx+4], 'little'); self.G_idx += 4
        root_name = self.G_bin[self.G_idx:self.G_idx+str_sz].decode('utf-8', errors='ignore'); self.G_idx += str_sz

        count = int.from_bytes(self.G_bin[self.G_idx:self.G_idx+4], 'little'); self.G_idx += 4

        nodes = []
        for _ in range(count):
            s = []
            while self.G_bin[self.G_idx] != 0:
                s.append(self.G_bin[self.G_idx])
                self.G_idx += 1
            self.G_idx += 1
            nodes.append(bytes(s).decode('utf-8', errors='ignore'))

        self.log(f"KZBF Nodes count: {len(nodes)}")

        count = int.from_bytes(self.G_bin[self.G_idx:self.G_idx+4], 'little'); self.G_idx += 4

        elems = []
        for _ in range(count):
            idx, unk1, addr, size, unk4, unk5 = struct.unpack('<6I', self.G_bin[self.G_idx:self.G_idx+24])
            self.G_idx += 24
            elems.append((idx, unk1, addr, size))

        for i, n in enumerate(nodes):
            idx, unk1, addr, size = elems[i]
            self.log(f"{idx:04d} 0x{addr:08x} 0x{size:08x} {n}")

        for i, n in enumerate(nodes):
            _, _, addr, size = elems[i]
            local = addr
            if '.png' in n.lower():
                local += 5 * 4
                if self.G_extract:
                    self.extract_resource_kzbf(escape_path(n), local, size - (5*4))
            else:
                if self.G_extract:
                    self.extract_resource_kzbf(escape_path(n), local, size)

    def unpack(self, in_file: Path):
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


# Packing classes
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
    meta += put_be32(0) * 4
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
            meta += put_be32(0) * 2
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
                meta += put_be32(0) * 2
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

    folderPH = []
    elemPH = []

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
    out[0:4] = b'kzbf'

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


# GUI Application
class KZBToolsGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("KZB Tools - Pack & Unpack")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)
        
        # Queue for thread-safe logging
        self.log_queue = queue.Queue()
        self.check_log_queue()
        
        self.create_widgets()
        
    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Title
        title = ttk.Label(main_frame, text="KZB Tools", font=('Arial', 16, 'bold'))
        title.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # Notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Unpack Tab
        unpack_frame = ttk.Frame(notebook, padding="10")
        notebook.add(unpack_frame, text="Unpack KZB/KZBF")
        self.create_unpack_tab(unpack_frame)
        
        # Pack Tab
        pack_frame = ttk.Frame(notebook, padding="10")
        notebook.add(pack_frame, text="Pack KZB")
        self.create_pack_tab(pack_frame)
        
    def create_unpack_tab(self, parent):
        # Input file
        ttk.Label(parent, text="Input KZB/KZBF File:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.unpack_input = tk.StringVar()
        input_entry = ttk.Entry(parent, textvariable=self.unpack_input, width=60)
        input_entry.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        browse_btn = ttk.Button(parent, text="Browse...", command=self.browse_unpack_input)
        browse_btn.grid(row=0, column=2, padx=5, pady=5)
        
        # Unpack button
        unpack_btn = ttk.Button(parent, text="Unpack File", command=self.unpack_file, style='Accent.TButton')
        unpack_btn.grid(row=1, column=0, columnspan=3, pady=10)
        
        # Log area
        ttk.Label(parent, text="Log:").grid(row=2, column=0, sticky=tk.W, pady=(10, 5))
        
        self.unpack_log = scrolledtext.ScrolledText(parent, height=20, width=70, state='disabled')
        self.unpack_log.grid(row=3, column=0, columnspan=3, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(3, weight=1)
        
    def create_pack_tab(self, parent):
        # Input directory
        ttk.Label(parent, text="Input Directory:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.pack_input = tk.StringVar()
        input_entry = ttk.Entry(parent, textvariable=self.pack_input, width=60)
        input_entry.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        browse_btn = ttk.Button(parent, text="Browse...", command=self.browse_pack_input)
        browse_btn.grid(row=0, column=2, padx=5, pady=5)
        
        # Output file
        ttk.Label(parent, text="Output KZB File:").grid(row=1, column=0, sticky=tk.W, pady=5)
        
        self.pack_output = tk.StringVar()
        output_entry = ttk.Entry(parent, textvariable=self.pack_output, width=60)
        output_entry.grid(row=1, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        browse_btn = ttk.Button(parent, text="Browse...", command=self.browse_pack_output)
        browse_btn.grid(row=1, column=2, padx=5, pady=5)
        
        # Pack button
        pack_btn = ttk.Button(parent, text="Pack to KZB", command=self.pack_file, style='Accent.TButton')
        pack_btn.grid(row=2, column=0, columnspan=3, pady=10)
        
        # Log area
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
        """Thread-safe logging to text widget"""
        self.log_queue.put((widget, message))
        
    def check_log_queue(self):
        """Process log queue"""
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
                messagebox.showinfo("Success", f"File unpacked successfully!\n\nOutput: {output_dir}")
            except Exception as e:
                self.log_to_widget(self.unpack_log, f"\n✗ ERROR: {str(e)}")
                messagebox.showerror("Error", f"Unpacking failed:\n{str(e)}")
                
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
                    messagebox.showinfo("Success", f"File packed successfully!\n\nOutput: {output_file}")
                else:
                    messagebox.showerror("Error", "Packing failed. Check the log for details.")
            except Exception as e:
                self.log_to_widget(self.pack_log, f"\n✗ ERROR: {str(e)}")
                messagebox.showerror("Error", f"Packing failed:\n{str(e)}")
                
        threading.Thread(target=run_pack, daemon=True).start()


def main():
    root = tk.Tk()
    app = KZBToolsGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
