from __future__ import annotations
import re
import zlib
import mmap
import json
import struct
import threading
import queue
import hashlib
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional, Callable
from io import BytesIO
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox, simpledialog
from PIL import Image, ImageTk, ImageDraw, ImageFilter
from .imports import *
from .kzb import *
from .vbf import *
from .vbf import _find_header_bounds
from .commands import *


PROG_SET = "PROG_SET"
STATUS_SET = "STATUS_SET"
DONE_OK = "DONE_OK"
DONE_ERR = "DONE_ERR"
ENABLE_UI = "ENABLE_UI"
DISABLE_UI = "DISABLE_UI"

class CombinedEngineeringTool(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ford Firmware Engineering Tool - Jakka351")
        self.geometry("1280x850")
        self.minsize(1100, 750)
        
        # Queue system
        self.log_queue = queue.Queue()
        self.progress_queue = queue.Queue()
        
        # VBF state
        self.vbf_mm: Optional[mmap.mmap] = None
        self.vbf_path: Optional[Path] = None
        self.vbf_header_text: str = ""
        self.vbf_header_end: int = 0
        self.vbf_header_fields: dict = {}
        self.vbf_header_crc32: Optional[int] = None
        self.vbf_sections: List[VBFSection] = []
        self.vbf_outdir: Optional[Path] = None
        self.vbf_pack_items: List[Tuple[Path,int,int]] = []
        self.vbf_use_lzss = tk.BooleanVar(value=True)
        self.vbf_do_file_crc = tk.BooleanVar(value=True)
        self.vbf_crc_scope = tk.StringVar(value="whole_file_zeroed_field")
        
        # TAR state
        self.tar_files: List[Path] = []
        self.tar_compression = tk.StringVar(value="none")
        
        # TAR to Binary state
        self.tar2bin_format = tk.StringVar(value="sequential")
        
        # Image Utility state - MODIFIED TO SUPPORT 6 IMAGES
        self.img_original: List[Optional[Image.Image]] = [None] * 6
        self.img_current: List[Optional[Image.Image]] = [None] * 6
        self.img_path: List[Optional[Path]] = [None] * 6
        self.img_display: List[Optional[ImageTk.PhotoImage]] = [None] * 6
        self.img_canvas: List[Optional[tk.Canvas]] = [None] * 6
        self.img_info: List[Optional[ttk.Label]] = [None] * 6
        
        # Worker machinery
        self._worker_thread: Optional[threading.Thread] = None
        self._worker_q: "queue.Queue[tuple]" = queue.Queue()
        self._cancel_evt: threading.Event = threading.Event()
        
        self._build_ui()
        self._tick_ui()
        
        # Auto-load startup images
        self.after(100, self._load_startup_images)


    def _load_startup_images(self):
        """Load the three uploaded images into slots 0, 1, and 2"""
        startup_images = [
            "/mnt/user-data/uploads/1760647562196_S550_Sprite_01.png",
            "/mnt/user-data/uploads/1760647562197_S550_Sprite_02.png",
            "/mnt/user-data/uploads/1760647562197_S550_Sprite_03.png"
        ]
        
        for idx, img_path in enumerate(startup_images):
            if Path(img_path).exists():
                try:
                    img = Image.open(img_path)
                    self.img_original[idx] = img.copy()
                    self.img_current[idx] = img.copy()
                    self.img_path[idx] = Path(img_path)
                    self._update_image_display(idx)
                except Exception as e:
                    print(f"Failed to load startup image {idx + 1}: {e}")
        
        self.status_label.configure(text="Status: Loaded 3 startup images into slots 1-3")

    def _build_ui(self):
        # Menu
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_menu)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.cmd_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menubar)
        
        # Main container
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Title
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(title_frame, text="Ford Firmware Engineering Tool", 
                 font=('TkDefaultFont', 14, 'bold')).pack(side='left')
        ttk.Label(title_frame, text="v3.3", 
                 font=('TkDefaultFont', 8)).pack(side='left', padx=(10, 0))
        
        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=(0, 10))
        
        # Main notebook
        self.main_notebook = ttk.Notebook(main_frame)
        self.main_notebook.pack(fill='both', expand=True)
        
        # KZB Tab
        kzb_frame = ttk.Frame(self.main_notebook, padding="10")
        self.main_notebook.add(kzb_frame, text="KZB Tools")
        self._build_kzb_ui(kzb_frame)
        
        # VBF Tab
        vbf_frame = ttk.Frame(self.main_notebook, padding="10")
        self.main_notebook.add(vbf_frame, text="VBF Tools")
        self._build_vbf_ui(vbf_frame)
        
        # Bitmaps Builder Tab
        bitmaps_frame = ttk.Frame(self.main_notebook, padding="10")
        self.main_notebook.add(bitmaps_frame, text="Bitmaps Builder")
        self._build_bitmaps_ui(bitmaps_frame)
        
        # TAR Archive Builder Tab
        tar_frame = ttk.Frame(self.main_notebook, padding="10")
        self.main_notebook.add(tar_frame, text="TAR Archive Builder")
        self._build_tar_ui(tar_frame)
        
        # TAR to Binary Tab (NEW)
        tar2bin_frame = ttk.Frame(self.main_notebook, padding="10")
        self.main_notebook.add(tar2bin_frame, text="TAR to Binary")
        self._build_tar2bin_ui(tar2bin_frame)
        
        # Image Utility Tab (NEW)
        img_frame = ttk.Frame(self.main_notebook, padding="10")
        self.main_notebook.add(img_frame, text="Image Utility")
        self._build_image_utility_ui(img_frame)
        
        # Status bar
        status_frame = ttk.Frame(main_frame, relief=tk.SUNKEN, borderwidth=1)
        status_frame.pack(fill='x', pady=(10, 0))
        self.status_label = ttk.Label(status_frame, text="Status: Ready", anchor='w')
        self.status_label.pack(side='left', fill='x', expand=True, padx=5, pady=2)

    # ... [Previous tab build methods remain the same] ...
    
    def _build_kzb_ui(self, parent):
        # Sub-notebook for Unpack/Pack
        kzb_notebook = ttk.Notebook(parent)
        kzb_notebook.pack(fill='both', expand=True)
        
        # Unpack tab
        unpack_frame = ttk.Frame(kzb_notebook, padding="10")
        kzb_notebook.add(unpack_frame, text="Unpack KZB")
        self._build_kzb_unpack_tab(unpack_frame)
        
        # Pack tab
        pack_frame = ttk.Frame(kzb_notebook, padding="10")
        kzb_notebook.add(pack_frame, text="Pack KZB")
        self._build_kzb_pack_tab(pack_frame)

    def _build_kzb_unpack_tab(self, parent):
        input_group = ttk.LabelFrame(parent, text="Input Configuration", padding="10")
        input_group.pack(fill='x', pady=(0, 10))
        
        ttk.Label(input_group, text="Archive File:").grid(row=0, column=0, sticky='w', padx=(0, 10))
        self.kzb_unpack_input = tk.StringVar()
        ttk.Entry(input_group, textvariable=self.kzb_unpack_input, width=70).grid(
            row=0, column=1, sticky='ew', padx=(0, 10))
        ttk.Button(input_group, text="Browse...", 
                  command=self.kzb_browse_unpack_input).grid(row=0, column=2)
        input_group.columnconfigure(1, weight=1)
        
        control_frame = ttk.Frame(parent)
        control_frame.pack(pady=(0, 10))
        ttk.Button(control_frame, text="Extract Archive", 
                  command=self.kzb_unpack_file, width=20).pack()
        
        progress_group = ttk.LabelFrame(parent, text="Extraction Progress", padding="10")
        progress_group.pack(fill='x', pady=(0, 10))
        
        self.kzb_unpack_status_label = ttk.Label(progress_group, text="Idle")
        self.kzb_unpack_status_label.pack(anchor='w', pady=(0, 5))
        
        self.kzb_unpack_progress = ttk.Progressbar(progress_group, mode='determinate')
        self.kzb_unpack_progress.pack(fill='x', pady=(0, 5))
        
        progress_info = ttk.Frame(progress_group)
        progress_info.pack(fill='x')
        ttk.Label(progress_info, text="Progress:").pack(side='left')
        self.kzb_unpack_progress_label = ttk.Label(progress_info, text="0%")
        self.kzb_unpack_progress_label.pack(side='left', padx=(5, 20))
        ttk.Label(progress_info, text="Files:").pack(side='left')
        self.kzb_unpack_files_label = ttk.Label(progress_info, text="0/0")
        self.kzb_unpack_files_label.pack(side='left', padx=5)
        
        log_group = ttk.LabelFrame(parent, text="Operation Log", padding="10")
        log_group.pack(fill='both', expand=True)
        
        self.kzb_unpack_log = scrolledtext.ScrolledText(log_group, height=15, width=90,
                                                        font=('Courier', 9), state='disabled')
        self.kzb_unpack_log.pack(fill='both', expand=True)

    def _build_kzb_pack_tab(self, parent):
        input_group = ttk.LabelFrame(parent, text="Input Configuration", padding="10")
        input_group.pack(fill='x', pady=(0, 10))
        
        ttk.Label(input_group, text="Directory:").grid(row=0, column=0, sticky='w', padx=(0, 10))
        self.kzb_pack_input = tk.StringVar()
        ttk.Entry(input_group, textvariable=self.kzb_pack_input, width=70).grid(
            row=0, column=1, sticky='ew', padx=(0, 10))
        ttk.Button(input_group, text="Browse...", 
                  command=self.kzb_browse_pack_input).grid(row=0, column=2)
        input_group.columnconfigure(1, weight=1)
        
        output_group = ttk.LabelFrame(parent, text="Output Configuration", padding="10")
        output_group.pack(fill='x', pady=(0, 10))
        
        ttk.Label(output_group, text="Output File:").grid(row=0, column=0, sticky='w', padx=(0, 10))
        self.kzb_pack_output = tk.StringVar()
        ttk.Entry(output_group, textvariable=self.kzb_pack_output, width=70).grid(
            row=0, column=1, sticky='ew', padx=(0, 10))
        ttk.Button(output_group, text="Browse...", 
                  command=self.kzb_browse_pack_output).grid(row=0, column=2)
        output_group.columnconfigure(1, weight=1)
        
        control_frame = ttk.Frame(parent)
        control_frame.pack(pady=(0, 10))
        ttk.Button(control_frame, text="Create Archive", 
                  command=self.kzb_pack_file, width=20).pack()
        
        progress_group = ttk.LabelFrame(parent, text="Packing Progress", padding="10")
        progress_group.pack(fill='x', pady=(0, 10))
        
        self.kzb_pack_status_label = ttk.Label(progress_group, text="Idle")
        self.kzb_pack_status_label.pack(anchor='w', pady=(0, 5))
        
        self.kzb_pack_progress = ttk.Progressbar(progress_group, mode='determinate')
        self.kzb_pack_progress.pack(fill='x', pady=(0, 5))
        
        progress_info = ttk.Frame(progress_group)
        progress_info.pack(fill='x')
        ttk.Label(progress_info, text="Progress:").pack(side='left')
        self.kzb_pack_progress_label = ttk.Label(progress_info, text="0%")
        self.kzb_pack_progress_label.pack(side='left', padx=(5, 20))
        ttk.Label(progress_info, text="Files:").pack(side='left')
        self.kzb_pack_files_label = ttk.Label(progress_info, text="0/0")
        self.kzb_pack_files_label.pack(side='left', padx=5)
        
        log_group = ttk.LabelFrame(parent, text="Operation Log", padding="10")
        log_group.pack(fill='both', expand=True)
        
        self.kzb_pack_log = scrolledtext.ScrolledText(log_group, height=15, width=90,
                                                      font=('Courier', 9), state='disabled')
        self.kzb_pack_log.pack(fill='both', expand=True)

    def _build_vbf_ui(self, parent):
        vbf_notebook = ttk.Notebook(parent)
        vbf_notebook.pack(fill='both', expand=True)
        
        # Unpack tab
        unpack_frame = ttk.Frame(vbf_notebook, padding="10")
        vbf_notebook.add(unpack_frame, text="Unpack VBF")
        self._build_vbf_unpack_tab(unpack_frame)
        
        # Pack tab
        pack_frame = ttk.Frame(vbf_notebook, padding="10")
        vbf_notebook.add(pack_frame, text="Pack VBF")
        self._build_vbf_pack_tab(pack_frame)

    def _build_vbf_unpack_tab(self, parent):
        # Top controls
        top = ttk.Frame(parent)
        top.pack(fill='x', pady=(0, 10))
        
        ttk.Button(top, text="Open VBF File", command=self.vbf_cmd_open).pack(side='left', padx=(0, 10))
        ttk.Button(top, text="Choose Output Folder", command=self.vbf_cmd_choose_out).pack(side='left', padx=(0, 10))
        ttk.Button(top, text="Extract Selected Block", command=self.vbf_cmd_extract_selected).pack(side='left', padx=(0, 10))
        ttk.Button(top, text="Extract All Blocks", command=self.vbf_cmd_extract_all).pack(side='left')
        
        # File info
        info_frame = ttk.Frame(parent)
        info_frame.pack(fill='x', pady=(0, 10))
        self.vbf_lbl_file = ttk.Label(info_frame, text="No file loaded")
        self.vbf_lbl_file.pack(side='left')
        self.vbf_lbl_out = ttk.Label(info_frame, text="Output: (not set)")
        self.vbf_lbl_out.pack(side='right')
        
        # Progress section
        progress_group = ttk.LabelFrame(parent, text="Extraction Progress", padding="10")
        progress_group.pack(fill='x', pady=(0, 10))
        
        self.vbf_unpack_status_label = ttk.Label(progress_group, text="Idle")
        self.vbf_unpack_status_label.pack(anchor='w', pady=(0, 5))
        
        self.vbf_unpack_progress = ttk.Progressbar(progress_group, mode='determinate')
        self.vbf_unpack_progress.pack(fill='x', pady=(0, 5))
        
        progress_info = ttk.Frame(progress_group)
        progress_info.pack(fill='x')
        ttk.Label(progress_info, text="Progress:").pack(side='left')
        self.vbf_unpack_progress_label = ttk.Label(progress_info, text="0%")
        self.vbf_unpack_progress_label.pack(side='left', padx=(5, 20))
        ttk.Label(progress_info, text="Blocks:").pack(side='left')
        self.vbf_unpack_blocks_label = ttk.Label(progress_info, text="0/0")
        self.vbf_unpack_blocks_label.pack(side='left', padx=5)
        
        # Paned window
        paned = ttk.PanedWindow(parent, orient='horizontal')
        paned.pack(fill='both', expand=True)
        
        # Left: sections list
        left = ttk.Frame(paned)
        paned.add(left, weight=1)
        
        cols = ("#", "start", "len", "crc", "ok")
        self.vbf_tree = ttk.Treeview(left, columns=cols, show='headings', selectmode='browse', height=20)
        self.vbf_tree.heading("#", text="#")
        self.vbf_tree.column("#", width=40, anchor='e')
        self.vbf_tree.heading("start", text="Start Addr")
        self.vbf_tree.column("start", width=120)
        self.vbf_tree.heading("len", text="Length")
        self.vbf_tree.column("len", width=100, anchor='e')
        self.vbf_tree.heading("crc", text="CRC16")
        self.vbf_tree.column("crc", width=180)
        self.vbf_tree.heading("ok", text="OK")
        self.vbf_tree.column("ok", width=40, anchor='center')
        self.vbf_tree.pack(fill='both', expand=True)
        
        # Right: tabs for header/json
        right = ttk.Notebook(paned)
        paned.add(right, weight=2)
        
        # Header tab
        tab_hdr = ttk.Frame(right)
        right.add(tab_hdr, text="Header")
        self.vbf_txt_hdr = tk.Text(tab_hdr, wrap='none')
        y1 = ttk.Scrollbar(tab_hdr, orient='vertical', command=self.vbf_txt_hdr.yview)
        x1 = ttk.Scrollbar(tab_hdr, orient='horizontal', command=self.vbf_txt_hdr.xview)
        self.vbf_txt_hdr.configure(yscrollcommand=y1.set, xscrollcommand=x1.set)
        self.vbf_txt_hdr.pack(side='top', fill='both', expand=True)
        y1.pack(side='right', fill='y')
        x1.pack(side='bottom', fill='x')
        
        # JSON tab
        tab_json = ttk.Frame(right)
        right.add(tab_json, text="Header (JSON)")
        self.vbf_txt_json = tk.Text(tab_json, wrap='none')
        y2 = ttk.Scrollbar(tab_json, orient='vertical', command=self.vbf_txt_json.yview)
        x2 = ttk.Scrollbar(tab_json, orient='horizontal', command=self.vbf_txt_json.xview)
        self.vbf_txt_json.configure(yscrollcommand=y2.set, xscrollcommand=x2.set)
        self.vbf_txt_json.pack(side='top', fill='both', expand=True)
        y2.pack(side='right', fill='y')
        x2.pack(side='bottom', fill='x')

    def _build_vbf_pack_tab(self, parent):
        # Header controls
        header_frame = ttk.LabelFrame(parent, text="Header", padding="10")
        header_frame.pack(fill='both', expand=False, pady=(0, 10))
        
        header_btns = ttk.Frame(header_frame)
        header_btns.pack(fill='x', pady=(0, 5))
        ttk.Button(header_btns, text="Load Header", command=self.vbf_pk_load_header).pack(side='left', padx=(0, 5))
        ttk.Button(header_btns, text="Save Header As", command=self.vbf_pk_save_header_as).pack(side='left', padx=(0, 5))
        self.vbf_lbl_header_src = ttk.Label(header_btns, text="(no header loaded)")
        self.vbf_lbl_header_src.pack(side='left', padx=10)
        
        self.vbf_txt_pk_hdr = tk.Text(header_frame, height=10, wrap='none')
        yph = ttk.Scrollbar(header_frame, orient='vertical', command=self.vbf_txt_pk_hdr.yview)
        xph = ttk.Scrollbar(header_frame, orient='horizontal', command=self.vbf_txt_pk_hdr.xview)
        self.vbf_txt_pk_hdr.configure(yscrollcommand=yph.set, xscrollcommand=xph.set)
        self.vbf_txt_pk_hdr.pack(side='top', fill='both', expand=True)
        yph.pack(side='right', fill='y')
        xph.pack(side='bottom', fill='x')
        
        # BIN list
        bins_frame = ttk.LabelFrame(parent, text="Blocks (addr + file)", padding="10")
        bins_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        cols_pk = ("#", "addr", "len", "path")
        self.vbf_tree_pk = ttk.Treeview(bins_frame, columns=cols_pk, show='headings', selectmode='browse', height=12)
        self.vbf_tree_pk.heading("#", text="#")
        self.vbf_tree_pk.column("#", width=40, anchor='e')
        self.vbf_tree_pk.heading("addr", text="Start Addr")
        self.vbf_tree_pk.column("addr", width=120)
        self.vbf_tree_pk.heading("len", text="Length")
        self.vbf_tree_pk.column("len", width=100, anchor='e')
        self.vbf_tree_pk.heading("path", text="File")
        self.vbf_tree_pk.column("path", width=400)
        self.vbf_tree_pk.pack(fill='both', expand=True, pady=(0, 5))
        
        pk_btns = ttk.Frame(bins_frame)
        pk_btns.pack(fill='x')
        ttk.Button(pk_btns, text="Add BIN(s)", command=self.vbf_pk_add_bin).pack(side='left', padx=(0, 5))
        ttk.Button(pk_btns, text="Remove", command=self.vbf_pk_remove_selected).pack(side='left', padx=(0, 5))
        ttk.Button(pk_btns, text="Move Up", command=lambda: self.vbf_pk_move_sel(-1)).pack(side='left', padx=(0, 5))
        ttk.Button(pk_btns, text="Move Down", command=lambda: self.vbf_pk_move_sel(+1)).pack(side='left', padx=(0, 5))
        self.vbf_btn_build = ttk.Button(pk_btns, text="Build VBF", command=self.vbf_pk_build)
        self.vbf_btn_build.pack(side='right', padx=(5, 0))
        self.vbf_btn_cancel = ttk.Button(pk_btns, text="Cancel", command=self.vbf_pk_cancel, state="disabled")
        self.vbf_btn_cancel.pack(side='right')
        
        # Options
        opts = ttk.LabelFrame(parent, text="Compression & Checksum Options", padding="10")
        opts.pack(fill='x')
        ttk.Checkbutton(opts, text="Use LZSS Compression", variable=self.vbf_use_lzss).pack(side='left', padx=(0, 10))
        ttk.Separator(opts, orient='vertical').pack(side='left', fill='y', padx=10)
        ttk.Checkbutton(opts, text="Compute file_checksum", variable=self.vbf_do_file_crc).pack(side='left', padx=(0, 10))
        ttk.Label(opts, text="Scope:").pack(side='left', padx=(0, 5))
        scope = ttk.Combobox(opts, textvariable=self.vbf_crc_scope, state="readonly", width=25,
                             values=("whole_file_zeroed_field", "payload_only", "header_only"))
        scope.pack(side='left')

    def _build_bitmaps_ui(self, parent):
        # Title and description
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(title_frame, text="Bitmaps Binary Builder", 
                 font=('TkDefaultFont', 12, 'bold')).pack(anchor='w')
        ttk.Label(title_frame, text="Combine KZB, CFG, and text files into bitmaps.bin", 
                 font=('TkDefaultFont', 9), foreground='gray').pack(anchor='w')
        
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=(0, 15))
        
        # Input files section
        input_group = ttk.LabelFrame(parent, text="Input Files", padding="15")
        input_group.pack(fill='both', expand=False, pady=(0, 10))
        
        # KZB file
        ttk.Label(input_group, text="KZB File:").grid(row=0, column=0, sticky='w', padx=(0, 10), pady=5)
        self.bitmaps_kzb_file = tk.StringVar()
        ttk.Entry(input_group, textvariable=self.bitmaps_kzb_file, width=60).grid(
            row=0, column=1, sticky='ew', padx=(0, 10), pady=5)
        ttk.Button(input_group, text="Browse...", 
                  command=lambda: self._browse_bitmaps_file(self.bitmaps_kzb_file, "KZB", "*.kzb")).grid(
            row=0, column=2, pady=5)
        
        # CFG file
        ttk.Label(input_group, text="KZB.CFG File:").grid(row=1, column=0, sticky='w', padx=(0, 10), pady=5)
        self.bitmaps_cfg_file = tk.StringVar()
        ttk.Entry(input_group, textvariable=self.bitmaps_cfg_file, width=60).grid(
            row=1, column=1, sticky='ew', padx=(0, 10), pady=5)
        ttk.Button(input_group, text="Browse...", 
                  command=lambda: self._browse_bitmaps_file(self.bitmaps_cfg_file, "CFG", "*.cfg")).grid(
            row=1, column=2, pady=5)
        
        # Text file 1
        ttk.Label(input_group, text="Text File 1:").grid(row=2, column=0, sticky='w', padx=(0, 10), pady=5)
        self.bitmaps_txt1_file = tk.StringVar()
        ttk.Entry(input_group, textvariable=self.bitmaps_txt1_file, width=60).grid(
            row=2, column=1, sticky='ew', padx=(0, 10), pady=5)
        ttk.Button(input_group, text="Browse...", 
                  command=lambda: self._browse_bitmaps_file(self.bitmaps_txt1_file, "Text", "*.txt")).grid(
            row=2, column=2, pady=5)
        
        # Text file 2
        ttk.Label(input_group, text="Text File 2:").grid(row=3, column=0, sticky='w', padx=(0, 10), pady=5)
        self.bitmaps_txt2_file = tk.StringVar()
        ttk.Entry(input_group, textvariable=self.bitmaps_txt2_file, width=60).grid(
            row=3, column=1, sticky='ew', padx=(0, 10), pady=5)
        ttk.Button(input_group, text="Browse...", 
                  command=lambda: self._browse_bitmaps_file(self.bitmaps_txt2_file, "Text", "*.txt")).grid(
            row=3, column=2, pady=5)
        
        input_group.columnconfigure(1, weight=1)
        
        # Output section
        output_group = ttk.LabelFrame(parent, text="Output Configuration", padding="15")
        output_group.pack(fill='x', pady=(0, 10))
        
        ttk.Label(output_group, text="Output File:").grid(row=0, column=0, sticky='w', padx=(0, 10))
        self.bitmaps_output_file = tk.StringVar(value="bitmaps.bin")
        ttk.Entry(output_group, textvariable=self.bitmaps_output_file, width=60).grid(
            row=0, column=1, sticky='ew', padx=(0, 10))
        ttk.Button(output_group, text="Browse...", 
                  command=self._browse_bitmaps_output).grid(row=0, column=2)
        
        output_group.columnconfigure(1, weight=1)
        
        # Build options
        options_group = ttk.LabelFrame(parent, text="Build Options", padding="15")
        options_group.pack(fill='x', pady=(0, 10))
        
        self.bitmaps_include_header = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_group, text="Include file size header", 
                       variable=self.bitmaps_include_header).pack(anchor='w', pady=2)
        
        self.bitmaps_align_sections = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_group, text="Align sections to 4-byte boundaries", 
                       variable=self.bitmaps_align_sections).pack(anchor='w', pady=2)
        
        self.bitmaps_add_crc = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_group, text="Add CRC32 checksum at end", 
                       variable=self.bitmaps_add_crc).pack(anchor='w', pady=2)
        
        # Control buttons
        control_frame = ttk.Frame(parent)
        control_frame.pack(pady=(0, 10))
        
        ttk.Button(control_frame, text="Build bitmaps.bin", 
                  command=self.bitmaps_build, width=20).pack(side='left', padx=5)
        ttk.Button(control_frame, text="Clear All Fields", 
                  command=self.bitmaps_clear_fields, width=20).pack(side='left', padx=5)
        
        # Progress section
        progress_group = ttk.LabelFrame(parent, text="Build Progress", padding="10")
        progress_group.pack(fill='x', pady=(0, 10))
        
        self.bitmaps_status_label = ttk.Label(progress_group, text="Ready to build")
        self.bitmaps_status_label.pack(anchor='w', pady=(0, 5))
        
        self.bitmaps_progress = ttk.Progressbar(progress_group, mode='determinate')
        self.bitmaps_progress.pack(fill='x', pady=(0, 5))
        
        # Log section
        log_group = ttk.LabelFrame(parent, text="Build Log", padding="10")
        log_group.pack(fill='both', expand=True)
        
        self.bitmaps_log = scrolledtext.ScrolledText(log_group, height=12, width=90,
                                                     font=('Courier', 9), state='disabled')
        self.bitmaps_log.pack(fill='both', expand=True)

    def _build_tar_ui(self, parent):
        # Title and description
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(title_frame, text="TAR Archive Builder", 
                 font=('TkDefaultFont', 12, 'bold')).pack(anchor='w')
        ttk.Label(title_frame, text="Create TAR archives from binary files with optional compression", 
                 font=('TkDefaultFont', 9), foreground='gray').pack(anchor='w')
        
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=(0, 15))
        
        # File list section
        files_group = ttk.LabelFrame(parent, text="Files to Archive", padding="15")
        files_group.pack(fill='both', expand=True, pady=(0, 10))
        
        # Treeview for file list
        cols = ("#", "filename", "size", "path")
        self.tar_tree = ttk.Treeview(files_group, columns=cols, show='headings', selectmode='browse', height=12)
        self.tar_tree.heading("#", text="#")
        self.tar_tree.column("#", width=40, anchor='e')
        self.tar_tree.heading("filename", text="Filename")
        self.tar_tree.column("filename", width=200)
        self.tar_tree.heading("size", text="Size")
        self.tar_tree.column("size", width=100, anchor='e')
        self.tar_tree.heading("path", text="Full Path")
        self.tar_tree.column("path", width=400)
        
        scrollbar = ttk.Scrollbar(files_group, orient='vertical', command=self.tar_tree.yview)
        self.tar_tree.configure(yscrollcommand=scrollbar.set)
        
        self.tar_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Buttons for file management
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Button(btn_frame, text="Add Files...", command=self.tar_add_files).pack(side='left', padx=(0, 5))
        ttk.Button(btn_frame, text="Add Folder...", command=self.tar_add_folder).pack(side='left', padx=(0, 5))
        ttk.Button(btn_frame, text="Remove Selected", command=self.tar_remove_selected).pack(side='left', padx=(0, 5))
        ttk.Button(btn_frame, text="Clear All", command=self.tar_clear_all).pack(side='left', padx=(0, 5))
        
        # Output configuration
        output_group = ttk.LabelFrame(parent, text="Output Configuration", padding="15")
        output_group.pack(fill='x', pady=(0, 10))
        
        ttk.Label(output_group, text="Output File:").grid(row=0, column=0, sticky='w', padx=(0, 10), pady=5)
        self.tar_output_file = tk.StringVar(value="archive.tar")
        ttk.Entry(output_group, textvariable=self.tar_output_file, width=60).grid(
            row=0, column=1, sticky='ew', padx=(0, 10), pady=5)
        ttk.Button(output_group, text="Browse...", command=self.tar_browse_output).grid(row=0, column=2, pady=5)
        
        ttk.Label(output_group, text="Compression:").grid(row=1, column=0, sticky='w', padx=(0, 10), pady=5)
        compression_frame = ttk.Frame(output_group)
        compression_frame.grid(row=1, column=1, sticky='w', pady=5)
        
        ttk.Radiobutton(compression_frame, text="None (.tar)", 
                       variable=self.tar_compression, value="none").pack(side='left', padx=(0, 15))
        ttk.Radiobutton(compression_frame, text="gzip (.tar.gz)", 
                       variable=self.tar_compression, value="gz").pack(side='left', padx=(0, 15))
        ttk.Radiobutton(compression_frame, text="bzip2 (.tar.bz2)", 
                       variable=self.tar_compression, value="bz2").pack(side='left', padx=(0, 15))
        ttk.Radiobutton(compression_frame, text="xz (.tar.xz)", 
                       variable=self.tar_compression, value="xz").pack(side='left')
        
        output_group.columnconfigure(1, weight=1)
        
        # Archive options
        options_group = ttk.LabelFrame(parent, text="Archive Options", padding="15")
        options_group.pack(fill='x', pady=(0, 10))
        
        self.tar_preserve_paths = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_group, text="Preserve directory structure", 
                       variable=self.tar_preserve_paths).pack(anchor='w', pady=2)
        
        self.tar_add_timestamp = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_group, text="Add timestamp to filename", 
                       variable=self.tar_add_timestamp).pack(anchor='w', pady=2)
        
        # Build button
        control_frame = ttk.Frame(parent)
        control_frame.pack(pady=(0, 10))
        
        ttk.Button(control_frame, text="Create Archive", 
                  command=self.tar_build, width=20).pack()
        
        # Progress section
        progress_group = ttk.LabelFrame(parent, text="Archive Progress", padding="10")
        progress_group.pack(fill='x', pady=(0, 10))
        
        self.tar_status_label = ttk.Label(progress_group, text="Ready to create archive")
        self.tar_status_label.pack(anchor='w', pady=(0, 5))
        
        self.tar_progress = ttk.Progressbar(progress_group, mode='determinate')
        self.tar_progress.pack(fill='x', pady=(0, 5))
        
        # Log section
        log_group = ttk.LabelFrame(parent, text="Archive Log", padding="10")
        log_group.pack(fill='both', expand=True)
        
        self.tar_log = scrolledtext.ScrolledText(log_group, height=8, width=90,
                                                 font=('Courier', 9), state='disabled')
        self.tar_log.pack(fill='both', expand=True)

   

    # ==================== NEW: TAR TO BINARY TAB ====================
    
    def _build_tar2bin_ui(self, parent):
        # Title and description
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(title_frame, text="TAR to Binary Converter", 
                 font=('TkDefaultFont', 12, 'bold')).pack(anchor='w')
        ttk.Label(title_frame, text="Convert TAR archives into structured binary format", 
                 font=('TkDefaultFont', 9), foreground='gray').pack(anchor='w')
        
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=(0, 15))
        
        # Input section
        input_group = ttk.LabelFrame(parent, text="Input Configuration", padding="15")
        input_group.pack(fill='x', pady=(0, 10))
        
        ttk.Label(input_group, text="TAR Archive:").grid(row=0, column=0, sticky='w', padx=(0, 10), pady=5)
        self.tar2bin_input = tk.StringVar()
        ttk.Entry(input_group, textvariable=self.tar2bin_input, width=60).grid(
            row=0, column=1, sticky='ew', padx=(0, 10), pady=5)
        ttk.Button(input_group, text="Browse...", command=self.tar2bin_browse_input).grid(row=0, column=2, pady=5)
        
        input_group.columnconfigure(1, weight=1)
        
        # Output section
        output_group = ttk.LabelFrame(parent, text="Output Configuration", padding="15")
        output_group.pack(fill='x', pady=(0, 10))
        
        ttk.Label(output_group, text="Output File:").grid(row=0, column=0, sticky='w', padx=(0, 10), pady=5)
        self.tar2bin_output = tk.StringVar(value="archive.bin")
        ttk.Entry(output_group, textvariable=self.tar2bin_output, width=60).grid(
            row=0, column=1, sticky='ew', padx=(0, 10), pady=5)
        ttk.Button(output_group, text="Browse...", command=self.tar2bin_browse_output).grid(row=0, column=2, pady=5)
        
        output_group.columnconfigure(1, weight=1)
        
        # Format options
        format_group = ttk.LabelFrame(parent, text="Binary Format Options", padding="15")
        format_group.pack(fill='x', pady=(0, 10))
        
        ttk.Label(format_group, text="Format Type:").grid(row=0, column=0, sticky='w', padx=(0, 10))
        format_frame = ttk.Frame(format_group)
        format_frame.grid(row=0, column=1, sticky='w')
        
        ttk.Radiobutton(format_frame, text="Sequential (files appended)", 
                       variable=self.tar2bin_format, value="sequential").pack(anchor='w', pady=2)
        ttk.Radiobutton(format_frame, text="Index Table (with file offsets)", 
                       variable=self.tar2bin_format, value="indexed").pack(anchor='w', pady=2)
        ttk.Radiobutton(format_frame, text="Custom Header (metadata + data)", 
                       variable=self.tar2bin_format, value="header").pack(anchor='w', pady=2)
        
        self.tar2bin_add_magic = tk.BooleanVar(value=True)
        ttk.Checkbutton(format_group, text="Add magic signature (TARB)", 
                       variable=self.tar2bin_add_magic).grid(row=1, column=0, columnspan=2, sticky='w', pady=5)
        
        self.tar2bin_add_crc = tk.BooleanVar(value=False)
        ttk.Checkbutton(format_group, text="Add CRC32 checksum", 
                       variable=self.tar2bin_add_crc).grid(row=2, column=0, columnspan=2, sticky='w', pady=2)
        
        format_group.columnconfigure(1, weight=1)
        
        # Control buttons
        control_frame = ttk.Frame(parent)
        control_frame.pack(pady=(0, 10))
        
        ttk.Button(control_frame, text="Convert to Binary", 
                  command=self.tar2bin_convert, width=20).pack()
        
        # Progress section
        progress_group = ttk.LabelFrame(parent, text="Conversion Progress", padding="10")
        progress_group.pack(fill='x', pady=(0, 10))
        
        self.tar2bin_status_label = ttk.Label(progress_group, text="Ready to convert")
        self.tar2bin_status_label.pack(anchor='w', pady=(0, 5))
        
        self.tar2bin_progress = ttk.Progressbar(progress_group, mode='determinate')
        self.tar2bin_progress.pack(fill='x', pady=(0, 5))
        
        # Log section
        log_group = ttk.LabelFrame(parent, text="Conversion Log", padding="10")
        log_group.pack(fill='both', expand=True)
        
        self.tar2bin_log = scrolledtext.ScrolledText(log_group, height=12, width=90,
                                                     font=('Courier', 9), state='disabled')
        self.tar2bin_log.pack(fill='both', expand=True)
    
    # ==================== NEW: IMAGE UTILITY TAB ====================
    '''
    def _build_image_utility_ui(self, parent):
        """Build the Image Utility UI with 6 image slots in a 2x3 grid"""
        # Title
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(title_frame, text="Image Utility - 6 Image Editor", 
                 font=('TkDefaultFont', 12, 'bold')).pack(anchor='w')
        ttk.Label(title_frame, text="Display and edit up to 6 PNG images simultaneously", 
                 font=('TkDefaultFont', 9), foreground='gray').pack(anchor='w')
        
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=(0, 15))
        
        # Create 2 rows of 3 images each
        for row in range(2):
            row_frame = ttk.Frame(parent)
            row_frame.pack(fill='both', expand=True, pady=5)
            
            for col in range(3):
                img_num = row * 3 + col
                self._create_image_panel(row_frame, img_num)

    def _create_image_panel(self, parent, img_num: int):
        """Create a single image panel for the specified slot"""
        panel = ttk.LabelFrame(parent, text=f"Image {img_num + 1}", padding="5")
        panel.pack(side='left', fill='both', expand=True, padx=5)
        
        # Control buttons
        ctrl_frame = ttk.Frame(panel)
        ctrl_frame.pack(fill='x', pady=(0, 5))
        
        ttk.Button(ctrl_frame, text="Load", 
                  command=lambda: self.img_load(img_num), width=8).pack(side='left', padx=2)
        ttk.Button(ctrl_frame, text="Save", 
                  command=lambda: self.img_save(img_num), width=8).pack(side='left', padx=2)
        ttk.Button(ctrl_frame, text="Clear", 
                  command=lambda: self.img_clear(img_num), width=8).pack(side='left', padx=2)
        
        # Image display canvas
        canvas_frame = ttk.Frame(panel, relief='sunken', borderwidth=1)
        canvas_frame.pack(fill='both', expand=True, pady=(0, 5))
        
        canvas = tk.Canvas(canvas_frame, bg='gray90', width=300, height=250)
        canvas.pack(fill='both', expand=True)
        self.img_canvas[img_num] = canvas
        
        # Image info label
        info = ttk.Label(panel, text="No image loaded", relief='sunken')
        info.pack(fill='x', pady=(0, 5))
        self.img_info[img_num] = info
        
        # Edit controls in a compact layout
        edit_frame = ttk.LabelFrame(panel, text="Edit", padding="3")
        edit_frame.pack(fill='x')
        
        # Row 1: Rotate, Flip
        row1 = ttk.Frame(edit_frame)
        row1.pack(fill='x', pady=1)
        ttk.Button(row1, text="Rotate 90°", 
                  command=lambda: self.img_rotate(img_num, 90), width=9).pack(side='left', padx=1)
        ttk.Button(row1, text="Flip H", 
                  command=lambda: self.img_flip(img_num, 'h'), width=9).pack(side='left', padx=1)
        ttk.Button(row1, text="Flip V", 
                  command=lambda: self.img_flip(img_num, 'v'), width=9).pack(side='left', padx=1)
        
        # Row 2: Effects
        row2 = ttk.Frame(edit_frame)
        row2.pack(fill='x', pady=1)
        ttk.Button(row2, text="Resize...", 
                  command=lambda: self.img_resize_dialog(img_num), width=9).pack(side='left', padx=1)
        ttk.Button(row2, text="Grayscale", 
                  command=lambda: self.img_grayscale(img_num), width=9).pack(side='left', padx=1)
        ttk.Button(row2, text="Blur", 
                  command=lambda: self.img_blur(img_num), width=9).pack(side='left', padx=1)
    '''
    def _build_image_utility_ui(self, parent):
        """Build the Image Utility UI with 3 spritesheet slots on top, 1 logo slot on bottom"""
        # Title
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(title_frame, text="Spritesheet Logo Stamper", 
                 font=('TkDefaultFont', 12, 'bold')).pack(anchor='w')
        ttk.Label(title_frame, text="Load 3 spritesheets (4x4 grid) and 1 logo. Transform applies logo to all spritesheets.", 
                 font=('TkDefaultFont', 9), foreground='gray').pack(anchor='w')
        
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=(0, 15))
        
        # Top row: 3 spritesheet slots
        top_frame = ttk.Frame(parent)
        top_frame.pack(fill='both', expand=True, pady=5)
        
        for col in range(3):
            self._create_image_panel(top_frame, col, f"Spritesheet {col + 1}")
        
        # Transform button (centered)
        transform_frame = ttk.Frame(parent)
        transform_frame.pack(fill='x', pady=15)
        
        ttk.Button(transform_frame, text="⬇ TRANSFORM ALL SPRITESHEETS ⬇", 
                  command=self.transform_all_spritesheets,
                  width=40).pack()
        
        ttk.Label(transform_frame, 
                 text="Applies the logo below to the center of each sub-image (4x4 grid) in all 3 spritesheets above",
                 font=('TkDefaultFont', 8), foreground='gray').pack(pady=5)
        
        # Bottom row: 1 logo slot (centered)
        bottom_frame = ttk.Frame(parent)
        bottom_frame.pack(fill='both', expand=True, pady=5)
        
        # Add spacers for centering
        ttk.Frame(bottom_frame).pack(side='left', fill='both', expand=True)
        self._create_image_panel(bottom_frame, 3, "Logo (Transparent PNG)")
        ttk.Frame(bottom_frame).pack(side='left', fill='both', expand=True)


    def _create_image_panel(self, parent, img_num: int, title: str):
        """Create a single image panel for the specified slot"""
        panel = ttk.LabelFrame(parent, text=title, padding="5")
        panel.pack(side='left', fill='both', expand=True, padx=5)
        
        # Control buttons
        ctrl_frame = ttk.Frame(panel)
        ctrl_frame.pack(fill='x', pady=(0, 5))
        
        ttk.Button(ctrl_frame, text="Load", 
                  command=lambda: self.img_load(img_num), width=8).pack(side='left', padx=2)
        ttk.Button(ctrl_frame, text="Save", 
                  command=lambda: self.img_save(img_num), width=8).pack(side='left', padx=2)
        ttk.Button(ctrl_frame, text="Clear", 
                  command=lambda: self.img_clear(img_num), width=8).pack(side='left', padx=2)
        
        # Image display canvas
        canvas_frame = ttk.Frame(panel, relief='sunken', borderwidth=1)
        canvas_frame.pack(fill='both', expand=True, pady=(0, 5))
        
        canvas = tk.Canvas(canvas_frame, bg='gray90', width=300, height=250)
        canvas.pack(fill='both', expand=True)
        self.img_canvas[img_num] = canvas
        
        # Image info label
        info = ttk.Label(panel, text="No image loaded", relief='sunken')
        info.pack(fill='x', pady=(0, 5))
        self.img_info[img_num] = info
        
        # Edit controls in a compact layout
        edit_frame = ttk.LabelFrame(panel, text="Edit", padding="3")
        edit_frame.pack(fill='x')
        
        # Row 1: Rotate, Flip
        row1 = ttk.Frame(edit_frame)
        row1.pack(fill='x', pady=1)
        ttk.Button(row1, text="Rotate 90°", 
                  command=lambda: self.img_rotate(img_num, 90), width=9).pack(side='left', padx=1)
        ttk.Button(row1, text="Flip H", 
                  command=lambda: self.img_flip(img_num, 'h'), width=9).pack(side='left', padx=1)
        ttk.Button(row1, text="Flip V", 
                  command=lambda: self.img_flip(img_num, 'v'), width=9).pack(side='left', padx=1)
        
        # Row 2: Effects
        row2 = ttk.Frame(edit_frame)
        row2.pack(fill='x', pady=1)
        ttk.Button(row2, text="Resize...", 
                  command=lambda: self.img_resize_dialog(img_num), width=9).pack(side='left', padx=1)
        ttk.Button(row2, text="Grayscale", 
                  command=lambda: self.img_grayscale(img_num), width=9).pack(side='left', padx=1)
        ttk.Button(row2, text="Blur", 
                  command=lambda: self.img_blur(img_num), width=9).pack(side='left', padx=1)


    def transform_all_spritesheets(self):
        """Apply the logo (slot 3) to all 3 spritesheets (slots 0, 1, 2) with progress bar"""
        print("DEBUG: transform_all_spritesheets() called")  # Debug
        
        try:
            # Import the function from spritesheet_logo_apply.py
            from spritesheet_logo_apply import apply_logo_to_spritesheet
            print("DEBUG: Successfully imported apply_logo_to_spritesheet")  # Debug
        except ImportError as e:
            messagebox.showerror("Import Error", 
                               f"Could not import spritesheet_logo_apply.py\n\n{str(e)}\n\n"
                               "Make sure spritesheet_logo_apply.py is in the same directory as this script.")
            return
        
        logo_img = self.img_current[3]
        print(f"DEBUG: Logo image: {logo_img}")  # Debug
        
        # Validation
        if logo_img is None:
            messagebox.showwarning("No Logo", "Please load a logo image in the bottom slot first!")
            return
        
        # Check if at least one spritesheet is loaded
        spritesheets_loaded = [(i, self.img_current[i]) for i in range(3) if self.img_current[i] is not None]
        print(f"DEBUG: Spritesheets loaded: {len(spritesheets_loaded)}")  # Debug
        
        if not spritesheets_loaded:
            messagebox.showwarning("No Spritesheets", 
                                 "Please load at least one spritesheet in the top slots!")
            return
        
        # Ask for confirmation
        loaded_count = len(spritesheets_loaded)
        confirm = messagebox.askyesno(
            "Confirm Transform",
            f"Apply logo to {loaded_count} spritesheet(s)?\n\n"
            f"This will stamp the logo at the center of each sub-image (4x4 grid).\n"
            f"Original images will be preserved.",
            icon='question'
        )
        
        if not confirm:
            print("DEBUG: User cancelled")  # Debug
            return
        
        # Create progress dialog
        progress_dialog = tk.Toplevel(self)
        progress_dialog.title("Transforming Spritesheets")
        progress_dialog.geometry("400x150")
        progress_dialog.transient(self)
        progress_dialog.grab_set()
        
        ttk.Label(progress_dialog, text="Applying logo to spritesheets...", 
                 font=('TkDefaultFont', 10)).pack(pady=20)
        
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_dialog, variable=progress_var, 
                                       maximum=100, length=350, mode='determinate')
        progress_bar.pack(pady=10)
        
        status_label = ttk.Label(progress_dialog, text="Starting...", foreground='blue')
        status_label.pack(pady=10)
        
        progress_dialog.update()
        
        # Apply transformation to each loaded spritesheet
        success_count = 0
        errors = []
        
        for idx, (i, sheet_img) in enumerate(spritesheets_loaded):
            try:
                status_label.configure(text=f"Processing Spritesheet {i + 1}...")
                progress_var.set((idx / loaded_count) * 100)
                progress_dialog.update()
                
                print(f"DEBUG: Processing spritesheet {i + 1}, size: {sheet_img.size}")  # Debug
                
                # Apply the logo using the spritesheet script function
                result = apply_logo_to_spritesheet(
                    sheet_img=sheet_img,
                    logo_img=logo_img,
                    rows=4,
                    cols=4,
                    max_ratio=0.45,
                    padding_px=0
                )
                
                print(f"DEBUG: Successfully transformed spritesheet {i + 1}")  # Debug
                
                # Update the current image
                self.img_current[i] = result
                self._update_image_display(i)
                success_count += 1
                
            except Exception as e:
                print(f"DEBUG: Error on spritesheet {i + 1}: {str(e)}")  # Debug
                import traceback
                traceback.print_exc()
                errors.append(f"Spritesheet {i + 1}: {str(e)}")
        
        # Complete progress
        progress_var.set(100)
        status_label.configure(text="Complete!", foreground='green')
        progress_dialog.update()
        
        # Close progress dialog after brief delay
        progress_dialog.after(500, progress_dialog.destroy)
        
        # Report results
        if success_count > 0:
            msg = f"Successfully transformed {success_count} spritesheet(s)!"
            if errors:
                msg += f"\n\nErrors:\n" + "\n".join(errors)
            messagebox.showinfo("Transform Complete", msg)
            self.status_label.configure(
                text=f"Status: Transformed {success_count} spritesheet(s) with logo"
            )
        else:
            messagebox.showerror("Transform Failed", 
                               "Failed to transform any spritesheets:\n\n" + "\n".join(errors))
        
        print("DEBUG: transform_all_spritesheets() completed")  # Debug

    def kzb_browse_unpack_input(self):
        filename = filedialog.askopenfilename(
            title="Select KZB/KZBF Archive",
            filetypes=[("KZB files", "*.kzb"), ("KZBF files", "*.kzbf"), ("All files", "*.*")]
        )
        if filename:
            self.kzb_unpack_input.set(filename)

    def kzb_browse_pack_input(self):
        dirname = filedialog.askdirectory(title="Select Directory to Pack")
        if dirname:
            self.kzb_pack_input.set(dirname)

    def kzb_browse_pack_output(self):
        filename = filedialog.asksaveasfilename(
            title="Save Archive As",
            defaultextension=".kzb",
            filetypes=[("KZB files", "*.kzb"), ("All files", "*.*")]
        )
        if filename:
            self.kzb_pack_output.set(filename)

    def kzb_log_to_widget(self, widget, message):
        self.log_queue.put((widget, message))

    def kzb_update_progress_ui(self, progressbar, status_label, progress_label, files_label, 
                          current, total, message):
        self.progress_queue.put((progressbar, status_label, progress_label, files_label, 
                                current, total, message))

    def kzb_unpack_file(self):
        input_file = self.kzb_unpack_input.get()
        if not input_file:
            messagebox.showerror("Error", "Please select an input file")
            return
        if not Path(input_file).exists():
            messagebox.showerror("Error", "Input file does not exist")
            return

        self.kzb_unpack_log.configure(state='normal')
        self.kzb_unpack_log.delete(1.0, tk.END)
        self.kzb_unpack_log.configure(state='disabled')
        self.kzb_unpack_progress['value'] = 0
        self.kzb_unpack_progress_label.configure(text="0%")
        self.kzb_unpack_files_label.configure(text="0/0")
        self.kzb_unpack_status_label.configure(text="Initializing extraction...")

    def kzb_unpack_file(self):
        input_file = self.kzb_unpack_input.get()
        if not input_file:
            messagebox.showerror("Error", "Please select an input file")
            return
        if not Path(input_file).exists():
            messagebox.showerror("Error", "Input file does not exist")
            return

        self.kzb_unpack_log.configure(state='normal')
        self.kzb_unpack_log.delete(1.0, tk.END)
        self.kzb_unpack_log.configure(state='disabled')
        self.kzb_unpack_progress['value'] = 0
        self.kzb_unpack_progress_label.configure(text="0%")
        self.kzb_unpack_files_label.configure(text="0/0")
        self.kzb_unpack_status_label.configure(text="Initializing extraction...")

        def run_unpack():
            try:
                def progress_callback(current, total, message):
                    self.kzb_update_progress_ui(
                        self.kzb_unpack_progress,
                        self.kzb_unpack_status_label,
                        self.kzb_unpack_progress_label,
                        self.kzb_unpack_files_label,
                        current, total, message
                    )

                processor = KZBProcessor(
                    lambda msg: self.kzb_log_to_widget(self.kzb_unpack_log, msg),
                    progress_callback
                )
                output_dir = processor.unpack(Path(input_file))
                
                self.kzb_log_to_widget(self.kzb_unpack_log, "=" * 70)
                self.kzb_log_to_widget(self.kzb_unpack_log, "[SUCCESS] Extraction completed")
                self.kzb_log_to_widget(self.kzb_unpack_log, f"[OUTPUT] {output_dir}")
                self.kzb_log_to_widget(self.kzb_unpack_log, f"[STATS ] {processor.processed_files} files extracted")
                self.kzb_log_to_widget(self.kzb_unpack_log, "=" * 70)
                
                self.kzb_update_progress_ui(
                    self.kzb_unpack_progress,
                    self.kzb_unpack_status_label,
                    self.kzb_unpack_progress_label,
                    self.kzb_unpack_files_label,
                    100, 100, "Extraction complete"
                )
                
                self.root.after(0, lambda: messagebox.showinfo(
                    "Extraction Complete", 
                    f"Archive unpacked successfully\n\nOutput: {output_dir}\nFiles: {processor.processed_files}"
                ))
            except Exception as e:
                self.kzb_log_to_widget(self.kzb_unpack_log, "=" * 70)
                self.kzb_log_to_widget(self.kzb_unpack_log, f"[ERROR] {str(e)}")
                self.kzb_log_to_widget(self.kzb_unpack_log, "=" * 70)
                self.kzb_update_progress_ui(
                    self.unpack_progress,
                    self.unpack_status_label,
                    self.unpack_progress_label,
                    self.unpack_files_label,
                    0, 100, "Error occurred"
                )
                self.root.after(0, lambda: messagebox.showerror(
                    "Extraction Failed", 
                    f"Error during unpacking:\n\n{str(e)}"
                ))

        threading.Thread(target=run_unpack, daemon=True).start()

    def kzb_pack_file(self):
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

        self.kzb_pack_log.configure(state='normal')
        self.kzb_pack_log.delete(1.0, tk.END)
        self.kzb_pack_log.configure(state='disabled')
        self.kzb_pack_progress['value'] = 0
        self.kzb_pack_progress_label.configure(text="0%")
        self.kzb_pack_files_label.configure(text="0/0")
        self.kzb_pack_status_label.configure(text="Initializing packing...")

        def run_pack():
            try:
                def progress_callback(current, total, message):
                    self.kzb_update_progress_ui(
                        self.kzb_pack_progress,
                        self.kzb_pack_status_label,
                        self.kzb_pack_progress_label,
                        self.kzb_pack_files_label,
                        current, total, message
                    )

                result = pack_kzb(
                    Path(input_dir),
                    Path(output_file),
                    lambda msg: self.kzb_log_to_widget(self.kzb_pack_log, msg),
                    progress_callback
                )
                
                if result == 0:
                    self.kzb_log_to_widget(self.kzb_pack_log, "=" * 70)
                    self.kzb_log_to_widget(self.kzb_pack_log, "[SUCCESS] Packing completed")
                    self.kzb_log_to_widget(self.kzb_pack_log, f"[OUTPUT] {output_file}")
                    self.kzb_log_to_widget(self.kzb_pack_log, "=" * 70)
                    
                    self.kzb_update_progress_ui(
                        self.kzb_pack_progress,
                        self.kzb_pack_status_label,
                        self.kzb_pack_progress_label,
                        self.kzb_pack_files_label,
                        100, 100, "Packing complete"
                    )
                    
                    self.root.after(0, lambda: messagebox.showinfo(
                        "Packing Complete", 
                        f"Archive created successfully\n\nOutput: {output_file}"
                    ))
                else:
                    self.root.after(0, lambda: messagebox.showerror(
                        "Packing Failed", 
                        "Error during packing. Check log for details."
                    ))
            except Exception as e:
                self.kzb_log_to_widget(self.pack_log, "=" * 70)
                self.kzb_log_to_widget(self.pack_log, f"[ERROR] {str(e)}")
                self.kzb_log_to_widget(self.pack_log, "=" * 70)
                self.kzb_update_progress_ui(
                    self.pack_progress,
                    self.pack_status_label,
                    self.pack_progress_label,
                    self.pack_files_label,
                    0, 100, "Error occurred"
                )
                self.root.after(0, lambda: messagebox.showerror(
                    "Packing Failed", 
                    f"Error during packing:\n\n{str(e)}"
                ))

        threading.Thread(target=run_pack, daemon=True).start()

    # VBF GUI COMMANDS

    def vbf_cmd_open(self):
        path = filedialog.askopenfilename(title="Open VBF", filetypes=[("VBF files", "*.vbf"), ("All files", "*.*")])
        if not path:
            return
        self._vbf_load_file(Path(path))

    def _vbf_load_file(self, path: Path):
        try:
            if self.vbf_mm is not None:
                self.vbf_mm.close()
        except Exception:
            pass

        fh = path.open('rb')
        mm = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
        self.vbf_mm = mm
        self.vbf_path = path
        self.vbf_lbl_file.config(text=f"File: {path.name}")

        start, end = _find_header_bounds(mm)
        header_bytes = mm[:end]
        self.vbf_header_text = header_bytes.decode('latin-1', errors='ignore')
        self.vbf_header_end = end

        self.vbf_header_fields, self.vbf_header_crc32 = parse_header_fields(self.vbf_header_text)

        sections = parse_blocks(mm, self.vbf_header_end)
        self.vbf_sections = sections

        self.vbf_txt_hdr.delete("1.0", "end")
        self.vbf_txt_hdr.insert("1.0", self.vbf_header_text)
        self.vbf_txt_json.delete("1.0", "end")
        self.vbf_txt_json.insert("1.0", json.dumps(self.vbf_header_fields, indent=2, ensure_ascii=False))

        for iid in self.vbf_tree.get_children():
            self.vbf_tree.delete(iid)
        for s in sections:
            ok = "âœ”" if s.crc_calc == s.crc_stored else "âœ–"
            self.vbf_tree.insert("", "end", iid=str(s.index), values=(
                s.index, f"0x{s.start_addr:08X}", f"{s.length:,}",
                f"0x{s.crc_stored:04X} / 0x{s.crc_calc:04X}", ok
            ))

        checksum_note = ""
        if self.vbf_header_crc32 is not None:
            calc = crc32_file(mm)
            match = "OK" if calc == self.vbf_header_crc32 else "MISMATCH"
            checksum_note = f" | file_checksum header=0x{self.vbf_header_crc32:08X} calc=0x{calc:08X} ({match})"
        self.status_label.config(text=f"Status: Loaded {path.name}: {len(sections)} block(s){checksum_note}")

    def vbf_cmd_choose_out(self):
        d = filedialog.askdirectory(title="Choose Output Folder")
        if not d:
            return
        self.vbf_outdir = Path(d)
        self.vbf_lbl_out.config(text=f"Output: {self.vbf_outdir}")

    def _vbf_ensure_outdir(self) -> Path:
        if self.vbf_outdir is None and self.vbf_path:
            self.vbf_outdir = self.vbf_path.with_suffix("")
            self.vbf_outdir = Path(str(self.vbf_outdir) + "_unpacked")
            self.vbf_lbl_out.config(text=f"Output: {self.vbf_outdir}")
        if self.vbf_outdir:
            self.vbf_outdir.mkdir(parents=True, exist_ok=True)
        return self.vbf_outdir

    def _vbf_write_header_sidecars(self, outdir: Path):
        (outdir / f"{self.vbf_path.name}_ascii_head.txt").write_text(self.vbf_header_text, encoding="utf-8", errors="ignore")
        (outdir / f"{self.vbf_path.name}_config.json").write_text(json.dumps(self.vbf_header_fields, indent=2, ensure_ascii=False), encoding="utf-8")

    def vbf_update_progress_ui(self, current, total, message):
        """Helper to update VBF unpack progress UI"""
        self.progress_queue.put((
            self.vbf_unpack_progress,
            self.vbf_unpack_status_label,
            self.vbf_unpack_progress_label,
            self.vbf_unpack_blocks_label,
            current, total, message
        ))

    def vbf_cmd_extract_selected(self):
        if not self.vbf_sections:
            return
        sel = self.vbf_tree.selection()
        if not sel:
            messagebox.showinfo("Nothing selected", "Pick a block in the list.")
            return
        idx = int(sel[0])
        sec = next((s for s in self.vbf_sections if s.index == idx), None)
        if not sec:
            return
        
        # Reset progress
        self.vbf_unpack_progress['value'] = 0
        self.vbf_unpack_progress_label.configure(text="0%")
        self.vbf_unpack_blocks_label.configure(text="0/1")
        self.vbf_unpack_status_label.configure(text="Extracting selected block...")
        
        def run_extract():
            try:
                outdir = self._vbf_ensure_outdir()
                if not outdir:
                    return
                self._vbf_write_header_sidecars(outdir)
                
                # Update progress to 50%
                self.vbf_update_progress_ui(1, 2, "Writing block data...")
                
                out_name = f"{self.vbf_path.name}_section_{sec.index:03d}_{sec.start_addr:08X}_len_{sec.length:06X}.bin"
                out_path = outdir / out_name
                with out_path.open('wb') as fh:
                    fh.write(self.vbf_mm[sec.data_off:sec.data_off+sec.length])
                
                # Complete
                self.vbf_update_progress_ui(1, 1, "Extraction complete")
                
                self.after(0, lambda: self.status_label.config(text=f"Status: Extracted block #{sec.index} â†’ {out_path}"))
                self.after(0, lambda: messagebox.showinfo("Extracted", str(out_path)))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Extraction Failed", f"Error: {str(e)}"))
        
        threading.Thread(target=run_extract, daemon=True).start()

    def vbf_cmd_extract_all(self):
        if not self.vbf_sections:
            return
        
        # Reset progress
        self.vbf_unpack_progress['value'] = 0
        self.vbf_unpack_progress_label.configure(text="0%")
        self.vbf_unpack_blocks_label.configure(text="0/0")
        self.vbf_unpack_status_label.configure(text="Initializing extraction...")
        
        def run_extract_all():
            try:
                outdir = self._vbf_ensure_outdir()
                if not outdir:
                    return
                
                total = len(self.vbf_sections)
                self.vbf_update_progress_ui(0, total, "Writing header files...")
                self._vbf_write_header_sidecars(outdir)
                
                count = 0
                for sec in self.vbf_sections:
                    if count % 5 == 0:  # Update every 5 blocks
                        self.vbf_update_progress_ui(
                            count, total, 
                            f"Extracting block {sec.index}/{total}..."
                        )
                    
                    out_name = f"{self.vbf_path.name}_section_{sec.index:03d}_{sec.start_addr:08X}_len_{sec.length:06X}.bin"
                    out_path = outdir / out_name
                    with out_path.open('wb') as fh:
                        fh.write(self.vbf_mm[sec.data_off:sec.data_off+sec.length])
                    count += 1
                
                # Complete
                self.vbf_update_progress_ui(total, total, "Extraction complete")
                
                self.after(0, lambda: self.status_label.config(text=f"Status: Extracted {count} block(s) â†’ {outdir}"))
                self.after(0, lambda: messagebox.showinfo("Done", f"Extracted {count} block(s) to:\n{outdir}"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Extraction Failed", f"Error: {str(e)}"))
        
        threading.Thread(target=run_extract_all, daemon=True).start()

    def vbf_pk_load_header(self):
        p = filedialog.askopenfilename(title="Load Header Text",
                                       filetypes=[("Text/Headers", "*.txt *.h *.hdr *.vbf"), ("All files","*.*")])
        if not p:
            return
        pth = Path(p)
        data = pth.read_bytes()
        if pth.suffix.lower() == ".vbf":
            try:
                with pth.open("rb") as fh:
                    mm = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
                    _, end = _find_header_bounds(mm)
                    text = mm[:end].decode("latin-1", errors="ignore")
                    mm.close()
            except Exception:
                text = data.decode("latin-1", errors="ignore")
        else:
            text = data.decode("latin-1", errors="ignore")
        self.vbf_txt_pk_hdr.delete("1.0", "end")
        self.vbf_txt_pk_hdr.insert("1.0", text)
        self.vbf_lbl_header_src.config(text=f"Header source: {pth.name}")
        self.status_label.config(text="Status: Header loaded into editor")

    def vbf_pk_save_header_as(self):
        text = self.vbf_txt_pk_hdr.get("1.0","end").encode("latin-1", errors="ignore")
        p = filedialog.asksaveasfilename(defaultextension=".txt", title="Save Header As")
        if not p:
            return
        Path(p).write_bytes(text)
        self.status_label.config(text=f"Status: Header saved â†’ {p}")

    def vbf_pk_add_bin(self):
        fps = filedialog.askopenfilenames(
            title="Select Binary Files",
            filetypes=[("Binary files","*.bin *.img *.bin2 *.dat *.hex"), ("All files","*.*")]
        )
        if not fps:
            return
        s = simpledialog.askstring("Start Address",
                                   "Enter start address for the first file (hex like 0x7E000 or decimal):")
        if s is None:
            return
        s = s.strip()
        try:
            base_addr = int(s, 16) if s.lower().startswith("0x") else int(s)
        except Exception:
            messagebox.showerror("Bad address", f"Could not parse address: {s}")
            return

        addr = base_addr
        for fp in fps:
            pth = Path(fp)
            length = pth.stat().st_size
            self.vbf_pack_items.append((pth, addr, length))
            addr += length
        self._vbf_pk_refresh_tree()

    def vbf_pk_remove_selected(self):
        sel = self.vbf_tree_pk.selection()
        if not sel:
            return
        idx = int(sel[0]) - 1
        if 0 <= idx < len(self.vbf_pack_items):
            del self.vbf_pack_items[idx]
            self._vbf_pk_refresh_tree()

    def vbf_pk_move_sel(self, delta: int):
        sel = self.vbf_tree_pk.selection()
        if not sel:
            return
        idx = int(sel[0]) - 1
        j = idx + delta
        if 0 <= idx < len(self.vbf_pack_items) and 0 <= j < len(self.vbf_pack_items):
            self.vbf_pack_items[idx], self.vbf_pack_items[j] = self.vbf_pack_items[j], self.vbf_pack_items[idx]
            self._vbf_pk_refresh_tree()
            self.vbf_tree_pk.selection_set(str(j+1))

    def _vbf_pk_refresh_tree(self):
        for iid in self.vbf_tree_pk.get_children():
            self.vbf_tree_pk.delete(iid)
        for i, (pth, addr, length) in enumerate(self.vbf_pack_items, start=1):
            self.vbf_tree_pk.insert("", "end", iid=str(i), values=(i, f"0x{addr:08X}", f"{length:,}", str(pth)))

    def vbf_pk_build(self):
        raw_header = self.vbf_txt_pk_hdr.get("1.0","end").rstrip("\n")
        if not raw_header.strip():
            messagebox.showerror("No header", "Load or paste a header first.")
            return
        if not self.vbf_pack_items:
            messagebox.showerror("No blocks", "Add at least one BIN + address.")
            return

        hb = raw_header.encode("latin-1", errors="ignore")
        o = hb.find(b'{')
        c = hb.rfind(b'}')
        if o < 0 or c < 0 or c < o:
            messagebox.showerror("Header error", "Header lacks a proper { ... } block.")
            return

        outp = filedialog.asksaveasfilename(title="Save VBF As", defaultextension=".vbf",
                                            filetypes=[("VBF files","*.vbf"), ("All files","*.*")])
        if not outp:
            return
        out_path = Path(outp)

        if self._worker_thread and self._worker_thread.is_alive():
            messagebox.showwarning("Busy", "A build is already running.")
            return

        self._cancel_evt.clear()
        self._worker_q.put((DISABLE_UI, None))
        args = dict(
            raw_header=raw_header,
            out_path=out_path,
            pack_items=self.vbf_pack_items.copy(),
            use_lzss=self.vbf_use_lzss.get(),
            do_crc=self.vbf_do_file_crc.get(),
            crc_scope=self.vbf_crc_scope.get(),
        )
        self._worker_thread = threading.Thread(target=self._vbf_worker_build, kwargs=args, daemon=True)
        self._worker_thread.start()

    def vbf_pk_cancel(self):
        if self._worker_thread and self._worker_thread.is_alive():
            self._cancel_evt.set()
            self._worker_q.put((STATUS_SET, "Cancellingâ€¦"))

    def _vbf_worker_build(self, *, raw_header: str, out_path: Path, pack_items: List[Tuple[Path,int,int]],
                      use_lzss: bool, do_crc: bool, crc_scope: str):
        try:
            self._worker_q.put((STATUS_SET, "Building VBFâ€¦"))
            
            checksum_re = re.compile(r"(file_checksum\s*=\s*)0x[0-9A-Fa-f]{8}(\s*;)")
            header_has_field = checksum_re.search(raw_header) is not None

            header_bytes = raw_header.encode("latin-1", errors="ignore")
            patch_offset = None

            def locate_patch_offset(text_for_search: str) -> Optional[int]:
                m = checksum_re.search(text_for_search)
                if not m:
                    return None
                prefix = m.group(1)
                before = text_for_search[:m.start()] + prefix
                return len(before)

            if not do_crc or not header_has_field:
                header_to_write = header_bytes
                patch_after = False
                crc32_acc = None
            elif crc_scope == "header_only":
                header_zero = checksum_re.sub(r"\g<1>0x00000000\2", raw_header)
                crc = crc32_bytes(header_zero.encode("latin-1", errors="ignore"))
                header_final = checksum_re.sub(lambda m: f"{m.group(1)}0x{crc:08X}{m.group(2)}", raw_header)
                header_to_write = header_final.encode("latin-1", errors="ignore")
                patch_after = False
                crc32_acc = None
            elif crc_scope == "payload_only":
                header_zero = checksum_re.sub(r"\g<1>0x00000000\2", raw_header)
                header_to_write = header_zero.encode("latin-1", errors="ignore")
                patch_after = True
                patch_offset = locate_patch_offset(header_zero)
                crc32_acc = 0
            elif crc_scope == "whole_file_zeroed_field":
                header_zero = checksum_re.sub(r"\g<1>0x00000000\2", raw_header)
                header_to_write = header_zero.encode("latin-1", errors="ignore")
                patch_after = True
                patch_offset = locate_patch_offset(header_zero)
                crc32_acc = crc32_bytes(header_to_write)
            else:
                header_zero = checksum_re.sub(r"\g<1>0x00000000\2", raw_header)
                header_to_write = header_zero.encode("latin-1", errors="ignore")
                patch_after = True
                patch_offset = locate_patch_offset(header_zero)
                crc32_acc = 0

            with out_path.open("wb+") as fh:
                fh.write(header_to_write)

                if use_lzss:
                    self._worker_q.put((STATUS_SET, "Compressing with LZSSâ€¦"))
                    
                    all_data = bytearray()
                    for (pth, _addr, _len) in pack_items:
                        if self._cancel_evt.is_set():
                            raise KeyboardInterrupt("Cancelled")
                        all_data.extend(pth.read_bytes())
                    
                    def progress_callback(frac: float):
                        if self._cancel_evt.is_set():
                            raise KeyboardInterrupt("Cancelled")
                        self._worker_q.put((PROG_SET, int(20 + frac * 70)))
                    
                    compressed = lzss_compress_data(bytes(all_data), on_progress=progress_callback)
                    
                    if crc32_acc is not None:
                        crc32_acc = crc32_bytes(compressed, crc32_acc)
                    fh.write(compressed)
                    
                else:
                    self._worker_q.put((STATUS_SET, "Writing payload (no compression)â€¦"))
                    written = 0
                    total_len = sum(pth.stat().st_size for (pth, _a, _l) in pack_items)
                    
                    for (pth, _addr, _len) in pack_items:
                        if self._cancel_evt.is_set():
                            raise KeyboardInterrupt("Cancelled")
                        chunk = pth.read_bytes()
                        if crc32_acc is not None:
                            crc32_acc = crc32_bytes(chunk, crc32_acc)
                        fh.write(chunk)
                        written += len(chunk)
                        if total_len:
                            frac = min(1.0, written / max(1, total_len))
                            self._worker_q.put((PROG_SET, int(10 + frac * 85)))

                if patch_after and patch_offset is not None:
                    final_crc = crc32_acc & 0xFFFFFFFF if crc32_acc is not None else 0
                    hex8 = f"{final_crc:08X}".encode("ascii")
                    fh.seek(patch_offset, 0)
                    fh.write(hex8)

            if self._cancel_evt.is_set():
                try:
                    out_path.unlink(missing_ok=True)
                except Exception:
                    pass
                self._worker_q.put((ENABLE_UI, None))
                self._worker_q.put((STATUS_SET, "Cancelled"))
                return

            msg = f"VBF written:\n{out_path}\nSize: {out_path.stat().st_size:,} bytes"
            if use_lzss:
                msg += f"\n\nCompressed using Python LZSS"
            self._worker_q.put((DONE_OK, msg))
            self._worker_q.put((ENABLE_UI, None))

        except KeyboardInterrupt:
            try:
                out_path.unlink(missing_ok=True)
            except Exception:
                pass
            self._worker_q.put((ENABLE_UI, None))
            self._worker_q.put((STATUS_SET, "Cancelled"))
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self._worker_q.put((ENABLE_UI, None))
            self._worker_q.put((DONE_ERR, f"{type(e).__name__}: {e}\n\n{tb}"))

    # ==================== BITMAPS BUILDER COMMANDS ====================

    def _browse_bitmaps_file(self, var: tk.StringVar, file_type: str, pattern: str):
        filename = filedialog.askopenfilename(
            title=f"Select {file_type} File",
            filetypes=[(f"{file_type} files", pattern), ("All files", "*.*")]
        )
        if filename:
            var.set(filename)

    def _browse_bitmaps_output(self):
        filename = filedialog.asksaveasfilename(
            title="Save Bitmaps Binary As",
            defaultextension=".bin",
            initialfile="bitmaps.bin",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")]
        )
        if filename:
            self.bitmaps_output_file.set(filename)

    def bitmaps_clear_fields(self):
        self.bitmaps_kzb_file.set("")
        self.bitmaps_cfg_file.set("")
        self.bitmaps_txt1_file.set("")
        self.bitmaps_txt2_file.set("")
        self.bitmaps_output_file.set("bitmaps.bin")
        self.bitmaps_log.configure(state='normal')
        self.bitmaps_log.delete(1.0, tk.END)
        self.bitmaps_log.configure(state='disabled')
        self.bitmaps_progress['value'] = 0
        self.bitmaps_status_label.configure(text="Ready to build")

    def bitmaps_log_message(self, message):
        self.bitmaps_log.configure(state='normal')
        self.bitmaps_log.insert(tk.END, message + '\n')
        self.bitmaps_log.see(tk.END)
        self.bitmaps_log.configure(state='disabled')

    def bitmaps_build(self):
        # Validate inputs
        kzb_path = self.bitmaps_kzb_file.get()
        cfg_path = self.bitmaps_cfg_file.get()
        txt1_path = self.bitmaps_txt1_file.get()
        txt2_path = self.bitmaps_txt2_file.get()
        output_path = self.bitmaps_output_file.get()
        
        if not kzb_path:
            messagebox.showerror("Missing File", "Please select a KZB file")
            return
        if not cfg_path:
            messagebox.showerror("Missing File", "Please select a KZB.CFG file")
            return
        if not txt1_path:
            messagebox.showerror("Missing File", "Please select Text File 1")
            return
        if not txt2_path:
            messagebox.showerror("Missing File", "Please select Text File 2")
            return
        if not output_path:
            messagebox.showerror("Missing Output", "Please specify an output file")
            return
        
        # Check if files exist
        for path, name in [(kzb_path, "KZB"), (cfg_path, "CFG"), 
                           (txt1_path, "Text 1"), (txt2_path, "Text 2")]:
            if not Path(path).exists():
                messagebox.showerror("File Not Found", f"{name} file does not exist:\n{path}")
                return
        
        # Clear log
        self.bitmaps_log.configure(state='normal')
        self.bitmaps_log.delete(1.0, tk.END)
        self.bitmaps_log.configure(state='disabled')
        self.bitmaps_progress['value'] = 0
        self.bitmaps_status_label.configure(text="Building bitmaps.bin...")
        
        def run_build():
            try:
                self.bitmaps_log_message("=" * 70)
                self.bitmaps_log_message("Starting bitmaps.bin build process")
                self.bitmaps_log_message("=" * 70)
                
                # Read input files
                self.bitmaps_status_label.configure(text="Reading KZB file...")
                self.bitmaps_progress['value'] = 10
                self.bitmaps_log_message(f"[1/4] Reading KZB file: {Path(kzb_path).name}")
                kzb_data = Path(kzb_path).read_bytes()
                self.bitmaps_log_message(f"      Size: {len(kzb_data):,} bytes")
                
                self.bitmaps_status_label.configure(text="Reading CFG file...")
                self.bitmaps_progress['value'] = 30
                self.bitmaps_log_message(f"[2/4] Reading CFG file: {Path(cfg_path).name}")
                cfg_data = Path(cfg_path).read_bytes()
                self.bitmaps_log_message(f"      Size: {len(cfg_data):,} bytes")
                
                self.bitmaps_status_label.configure(text="Reading Text file 1...")
                self.bitmaps_progress['value'] = 50
                self.bitmaps_log_message(f"[3/4] Reading Text file 1: {Path(txt1_path).name}")
                txt1_data = Path(txt1_path).read_bytes()
                self.bitmaps_log_message(f"      Size: {len(txt1_data):,} bytes")
                
                self.bitmaps_status_label.configure(text="Reading Text file 2...")
                self.bitmaps_progress['value'] = 70
                self.bitmaps_log_message(f"[4/4] Reading Text file 2: {Path(txt2_path).name}")
                txt2_data = Path(txt2_path).read_bytes()
                self.bitmaps_log_message(f"      Size: {len(txt2_data):,} bytes")
                
                # Build binary
                self.bitmaps_status_label.configure(text="Building binary structure...")
                self.bitmaps_progress['value'] = 80
                self.bitmaps_log_message("")
                self.bitmaps_log_message("Building binary structure...")
                
                output = bytearray()
                
                # Add magic header
                output.extend(b'BTMP')  # Magic signature
                
                if self.bitmaps_include_header.get():
                    self.bitmaps_log_message("  Adding file size headers")
                    # Add file count
                    output.extend(struct.pack('<I', 4))  # 4 files
                    
                    # Add offsets and sizes for each section (will be patched later)
                    offset_positions = []
                    for i in range(4):
                        offset_positions.append(len(output))
                        output.extend(struct.pack('<I', 0))  # offset placeholder
                        output.extend(struct.pack('<I', 0))  # size placeholder
                
                # Add alignment if needed
                if self.bitmaps_align_sections.get():
                    while len(output) % 4 != 0:
                        output.append(0)
                
                # Add data sections
                sections = [
                    (kzb_data, "KZB", Path(kzb_path).name),
                    (cfg_data, "CFG", Path(cfg_path).name),
                    (txt1_data, "TXT1", Path(txt1_path).name),
                    (txt2_data, "TXT2", Path(txt2_path).name)
                ]
                
                section_info = []
                for idx, (data, label, filename) in enumerate(sections):
                    section_start = len(output)
                    output.extend(data)
                    section_info.append((section_start, len(data)))
                    self.bitmaps_log_message(f"  [{label}] Offset: 0x{section_start:08X}, Size: {len(data):,} bytes ({filename})")
                    
                    # Add alignment if needed
                    if self.bitmaps_align_sections.get() and idx < len(sections) - 1:
                        while len(output) % 4 != 0:
                            output.append(0)
                
                # Patch offsets and sizes
                if self.bitmaps_include_header.get():
                    for idx, (offset, size) in enumerate(section_info):
                        pos = offset_positions[idx]
                        output[pos:pos+4] = struct.pack('<I', offset)
                        output[pos+4:pos+8] = struct.pack('<I', size)
                
                # Add CRC if requested
                if self.bitmaps_add_crc.get():
                    crc = crc32_bytes(bytes(output))
                    output.extend(struct.pack('<I', crc))
                    self.bitmaps_log_message(f"  [CRC32] 0x{crc:08X}")
                
                # Write output file
                self.bitmaps_status_label.configure(text="Writing output file...")
                self.bitmaps_progress['value'] = 90
                self.bitmaps_log_message("")
                self.bitmaps_log_message(f"Writing to: {output_path}")
                
                Path(output_path).write_bytes(output)
                
                self.bitmaps_progress['value'] = 100
                self.bitmaps_status_label.configure(text="Build complete!")
                
                self.bitmaps_log_message("")
                self.bitmaps_log_message("=" * 70)
                self.bitmaps_log_message(f"[SUCCESS] bitmaps.bin created successfully")
                self.bitmaps_log_message(f"[OUTPUT] {output_path}")
                self.bitmaps_log_message(f"[SIZE  ] {len(output):,} bytes ({len(output)/1024:.2f} KB)")
                self.bitmaps_log_message("=" * 70)
                
                self.after(0, lambda: messagebox.showinfo(
                    "Build Complete",
                    f"bitmaps.bin created successfully!\n\n"
                    f"Output: {output_path}\n"
                    f"Size: {len(output):,} bytes ({len(output)/1024:.2f} KB)"
                ))
                
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                self.bitmaps_log_message("")
                self.bitmaps_log_message("=" * 70)
                self.bitmaps_log_message(f"[ERROR] Build failed: {str(e)}")
                self.bitmaps_log_message("=" * 70)
                self.bitmaps_log_message(tb)
                self.bitmaps_progress['value'] = 0
                self.bitmaps_status_label.configure(text="Build failed")
                
                self.after(0, lambda: messagebox.showerror(
                    "Build Failed",
                    f"Error building bitmaps.bin:\n\n{str(e)}"
                ))
        
        threading.Thread(target=run_build, daemon=True).start()

    # ==================== TAR ARCHIVE BUILDER COMMANDS ====================

    def tar_add_files(self):
        files = filedialog.askopenfilenames(
            title="Select Binary Files",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")]
        )
        if not files:
            return
        
        for filepath in files:
            path = Path(filepath)
            if path not in self.tar_files:
                self.tar_files.append(path)
        
        self._tar_refresh_tree()

    def tar_add_folder(self):
        folder = filedialog.askdirectory(title="Select Folder")
        if not folder:
            return
        
        folder_path = Path(folder)
        for file_path in folder_path.rglob('*'):
            if file_path.is_file() and file_path not in self.tar_files:
                self.tar_files.append(file_path)
        
        self._tar_refresh_tree()

    def tar_remove_selected(self):
        sel = self.tar_tree.selection()
        if not sel:
            return
        idx = int(sel[0]) - 1
        if 0 <= idx < len(self.tar_files):
            del self.tar_files[idx]
            self._tar_refresh_tree()

    def tar_clear_all(self):
        self.tar_files.clear()
        self._tar_refresh_tree()

    def _tar_refresh_tree(self):
        for iid in self.tar_tree.get_children():
            self.tar_tree.delete(iid)
        
        for i, path in enumerate(self.tar_files, start=1):
            size = path.stat().st_size
            self.tar_tree.insert("", "end", iid=str(i), values=(
                i, path.name, f"{size:,} bytes", str(path)
            ))

    def tar_browse_output(self):
        compression = self.tar_compression.get()
        ext_map = {
            "none": ".tar",
            "gz": ".tar.gz",
            "bz2": ".tar.bz2",
            "xz": ".tar.xz"
        }
        default_ext = ext_map.get(compression, ".tar")
        
        filename = filedialog.asksaveasfilename(
            title="Save TAR Archive As",
            defaultextension=default_ext,
            initialfile=f"archive{default_ext}",
            filetypes=[
                ("TAR archives", "*.tar"),
                ("GZIP compressed TAR", "*.tar.gz"),
                ("BZIP2 compressed TAR", "*.tar.bz2"),
                ("XZ compressed TAR", "*.tar.xz"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.tar_output_file.set(filename)

    def tar_log_message(self, message):
        self.tar_log.configure(state='normal')
        self.tar_log.insert(tk.END, message + '\n')
        self.tar_log.see(tk.END)
        self.tar_log.configure(state='disabled')

    def tar_build(self):
        if not self.tar_files:
            messagebox.showerror("No Files", "Please add files to archive")
            return
        
        output_path = self.tar_output_file.get()
        if not output_path:
            messagebox.showerror("No Output", "Please specify output file")
            return
        
        # Clear log
        self.tar_log.configure(state='normal')
        self.tar_log.delete(1.0, tk.END)
        self.tar_log.configure(state='disabled')
        self.tar_progress['value'] = 0
        self.tar_status_label.configure(text="Creating archive...")
        
        def run_tar_build():
            try:
                self.tar_log_message("=" * 70)
                self.tar_log_message("Starting TAR archive creation")
                self.tar_log_message("=" * 70)
                
                compression = self.tar_compression.get()
                mode_map = {
                    "none": "w",
                    "gz": "w:gz",
                    "bz2": "w:bz2",
                    "xz": "w:xz"
                }
                mode = mode_map.get(compression, "w")
                
                comp_name = {
                    "none": "No compression",
                    "gz": "GZIP compression",
                    "bz2": "BZIP2 compression",
                    "xz": "XZ compression"
                }.get(compression, "No compression")
                
                self.tar_log_message(f"Compression: {comp_name}")
                self.tar_log_message(f"Output: {output_path}")
                self.tar_log_message(f"Files to archive: {len(self.tar_files)}")
                self.tar_log_message("")
                
                # Add timestamp if requested
                output_final = Path(output_path)
                if self.tar_add_timestamp.get():
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    stem = output_final.stem
                    # Remove existing tar extensions
                    if stem.endswith('.tar'):
                        stem = stem[:-4]
                    suffix = ''.join(output_final.suffixes)
                    output_final = output_final.parent / f"{stem}_{timestamp}{suffix}"
                    self.tar_log_message(f"Added timestamp to filename: {output_final.name}")
                    self.tar_log_message("")
                
                with tarfile.open(output_final, mode) as tar:
                    total = len(self.tar_files)
                    for i, file_path in enumerate(self.tar_files, start=1):
                        # Update progress
                        progress = int((i / total) * 100)
                        self.tar_progress['value'] = progress
                        self.tar_status_label.configure(text=f"Adding: {file_path.name}")
                        
                        # Determine arcname
                        if self.tar_preserve_paths.get():
                            arcname = str(file_path)
                        else:
                            arcname = file_path.name
                        
                        # Add file to archive
                        tar.add(file_path, arcname=arcname)
                        
                        size = file_path.stat().st_size
                        self.tar_log_message(f"[{i}/{total}] Added: {arcname} ({size:,} bytes)")
                
                final_size = output_final.stat().st_size
                
                self.tar_progress['value'] = 100
                self.tar_status_label.configure(text="Archive created successfully!")
                
                self.tar_log_message("")
                self.tar_log_message("=" * 70)
                self.tar_log_message("[SUCCESS] TAR archive created successfully")
                self.tar_log_message(f"[OUTPUT] {output_final}")
                self.tar_log_message(f"[SIZE  ] {final_size:,} bytes ({final_size/1024:.2f} KB)")
                self.tar_log_message(f"[FILES ] {len(self.tar_files)} files archived")
                self.tar_log_message("=" * 70)
                
                self.after(0, lambda: messagebox.showinfo(
                    "Archive Complete",
                    f"TAR archive created successfully!\n\n"
                    f"Output: {output_final}\n"
                    f"Size: {final_size:,} bytes ({final_size/1024:.2f} KB)\n"
                    f"Files: {len(self.tar_files)}"
                ))
                
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                self.tar_log_message("")
                self.tar_log_message("=" * 70)
                self.tar_log_message(f"[ERROR] Archive creation failed: {str(e)}")
                self.tar_log_message("=" * 70)
                self.tar_log_message(tb)
                self.tar_progress['value'] = 0
                self.tar_status_label.configure(text="Archive creation failed")
                
                self.after(0, lambda: messagebox.showerror(
                    "Archive Failed",
                    f"Error creating TAR archive:\n\n{str(e)}"
                ))
        
        threading.Thread(target=run_tar_build, daemon=True).start()

 # ==================== TAR TO BINARY COMMANDS ====================
    
    def tar2bin_browse_input(self):
        filename = filedialog.askopenfilename(
            title="Select TAR Archive",
            filetypes=[
                ("TAR archives", "*.tar"),
                ("Compressed TAR", "*.tar.gz *.tar.bz2 *.tar.xz"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.tar2bin_input.set(filename)
    
    def tar2bin_browse_output(self):
        filename = filedialog.asksaveasfilename(
            title="Save Binary File As",
            defaultextension=".bin",
            initialfile="archive.bin",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")]
        )
        if filename:
            self.tar2bin_output.set(filename)
    
    def tar2bin_log_message(self, message):
        self.tar2bin_log.configure(state='normal')
        self.tar2bin_log.insert(tk.END, message + '\n')
        self.tar2bin_log.see(tk.END)
        self.tar2bin_log.configure(state='disabled')
    
    def tar2bin_convert(self):
        input_file = self.tar2bin_input.get()
        output_file = self.tar2bin_output.get()
        
        if not input_file:
            messagebox.showerror("No Input", "Please select a TAR archive")
            return
        if not output_file:
            messagebox.showerror("No Output", "Please specify an output file")
            return
        if not Path(input_file).exists():
            messagebox.showerror("File Not Found", "Input TAR archive does not exist")
            return
        
        # Clear log
        self.tar2bin_log.configure(state='normal')
        self.tar2bin_log.delete(1.0, tk.END)
        self.tar2bin_log.configure(state='disabled')
        self.tar2bin_progress['value'] = 0
        self.tar2bin_status_label.configure(text="Converting...")
        
        def run_convert():
            try:
                self.tar2bin_log_message("=" * 70)
                self.tar2bin_log_message("Starting TAR to Binary conversion")
                self.tar2bin_log_message("=" * 70)
                
                format_type = self.tar2bin_format.get()
                add_magic = self.tar2bin_add_magic.get()
                add_crc = self.tar2bin_add_crc.get()
                
                self.tar2bin_log_message(f"Format: {format_type}")
                self.tar2bin_log_message(f"Magic signature: {add_magic}")
                self.tar2bin_log_message(f"CRC32: {add_crc}")
                self.tar2bin_log_message("")
                
                # Read TAR archive
                self.tar2bin_status_label.configure(text="Reading TAR archive...")
                self.tar2bin_progress['value'] = 10
                self.tar2bin_log_message(f"Opening: {Path(input_file).name}")
                
                with tarfile.open(input_file, 'r:*') as tar:
                    members = tar.getmembers()
                    file_members = [m for m in members if m.isfile()]
                    
                    self.tar2bin_log_message(f"Found {len(file_members)} files in archive")
                    self.tar2bin_log_message("")
                    
                    # Build binary format
                    output = bytearray()
                    
                    if add_magic:
                        output.extend(b'TARB')  # Magic signature
                        self.tar2bin_log_message("Added magic signature: TARB")
                    
                    if format_type == "sequential":
                        # Simple sequential format
                        self.tar2bin_log_message("Using sequential format (files appended)")
                        
                        # File count
                        output.extend(struct.pack('<I', len(file_members)))
                        
                        for i, member in enumerate(file_members):
                            progress = 10 + int((i / len(file_members)) * 80)
                            self.tar2bin_progress['value'] = progress
                            self.tar2bin_status_label.configure(text=f"Processing: {member.name}")
                            
                            # Extract file data
                            f = tar.extractfile(member)
                            if f:
                                data = f.read()
                                
                                # Write filename length and name
                                name_bytes = member.name.encode('utf-8')
                                output.extend(struct.pack('<H', len(name_bytes)))
                                output.extend(name_bytes)
                                
                                # Write file size
                                output.extend(struct.pack('<I', len(data)))
                                
                                # Write file data
                                output.extend(data)
                                
                                self.tar2bin_log_message(
                                    f"  [{i+1}/{len(file_members)}] {member.name} ({len(data):,} bytes)"
                                )
                    
                    elif format_type == "indexed":
                        # Index table format
                        self.tar2bin_log_message("Using indexed format (with file offset table)")
                        
                        # Reserve space for file count and index table
                        file_count = len(file_members)
                        output.extend(struct.pack('<I', file_count))
                        
                        # Calculate header size (count + index entries)
                        # Each index entry: name_len(2) + name + offset(4) + size(4)
                        index_start = len(output)
                        
                        # Build index and data
                        index_entries = []
                        data_section = bytearray()
                        
                        for i, member in enumerate(file_members):
                            progress = 10 + int((i / len(file_members)) * 80)
                            self.tar2bin_progress['value'] = progress
                            
                            f = tar.extractfile(member)
                            if f:
                                data = f.read()
                                
                                name_bytes = member.name.encode('utf-8')
                                offset = len(data_section)
                                
                                index_entries.append((name_bytes, offset, len(data)))
                                data_section.extend(data)
                        
                        # Calculate data start position
                        index_size = sum(2 + len(name) + 4 + 4 for name, _, _ in index_entries)
                        data_start = len(output) + index_size
                        
                        # Write index table
                        for name_bytes, offset, size in index_entries:
                            output.extend(struct.pack('<H', len(name_bytes)))
                            output.extend(name_bytes)
                            output.extend(struct.pack('<I', data_start + offset))
                            output.extend(struct.pack('<I', size))
                            
                            self.tar2bin_log_message(
                                f"  Index: {name_bytes.decode('utf-8')} @ 0x{data_start + offset:08X} ({size:,} bytes)"
                            )
                        
                        # Write data section
                        output.extend(data_section)
                    
                    elif format_type == "header":
                        # Custom header format
                        self.tar2bin_log_message("Using custom header format (metadata + data)")
                        
                        # Header: version, file count, total size
                        output.extend(struct.pack('<I', 1))  # Version
                        output.extend(struct.pack('<I', len(file_members)))  # File count
                        
                        # Reserve space for total size (will fill later)
                        size_pos = len(output)
                        output.extend(struct.pack('<I', 0))
                        
                        # Metadata section
                        metadata = bytearray()
                        data_section = bytearray()
                        
                        for i, member in enumerate(file_members):
                            progress = 10 + int((i / len(file_members)) * 80)
                            self.tar2bin_progress['value'] = progress
                            
                            f = tar.extractfile(member)
                            if f:
                                data = f.read()
                                
                                # Metadata: name, offset, size, timestamp
                                name_bytes = member.name.encode('utf-8')
                                metadata.extend(struct.pack('<H', len(name_bytes)))
                                metadata.extend(name_bytes)
                                metadata.extend(struct.pack('<Q', len(data_section)))  # Offset (8 bytes)
                                metadata.extend(struct.pack('<Q', len(data)))  # Size (8 bytes)
                                metadata.extend(struct.pack('<Q', int(member.mtime)))  # Timestamp (8 bytes)
                                
                                data_section.extend(data)
                                
                                self.tar2bin_log_message(
                                    f"  [{i+1}/{len(file_members)}] {member.name} ({len(data):,} bytes)"
                                )
                        
                        # Write metadata size and metadata
                        output.extend(struct.pack('<I', len(metadata)))
                        output.extend(metadata)
                        
                        # Write data
                        output.extend(data_section)
                        
                        # Update total size
                        total_size = len(output) - size_pos - 4
                        output[size_pos:size_pos+4] = struct.pack('<I', total_size)
                    
                    # Add CRC32 if requested
                    if add_crc:
                        crc = crc32_bytes(bytes(output))
                        output.extend(struct.pack('<I', crc))
                        self.tar2bin_log_message("")
                        self.tar2bin_log_message(f"Added CRC32: 0x{crc:08X}")
                
                # Write output file
                self.tar2bin_status_label.configure(text="Writing output file...")
                self.tar2bin_progress['value'] = 95
                self.tar2bin_log_message("")
                self.tar2bin_log_message(f"Writing to: {output_file}")
                
                Path(output_file).write_bytes(output)
                
                self.tar2bin_progress['value'] = 100
                self.tar2bin_status_label.configure(text="Conversion complete!")
                
                self.tar2bin_log_message("")
                self.tar2bin_log_message("=" * 70)
                self.tar2bin_log_message("[SUCCESS] Conversion completed")
                self.tar2bin_log_message(f"[OUTPUT] {output_file}")
                self.tar2bin_log_message(f"[SIZE  ] {len(output):,} bytes ({len(output)/1024:.2f} KB)")
                self.tar2bin_log_message("=" * 70)
                
                self.after(0, lambda: messagebox.showinfo(
                    "Conversion Complete",
                    f"TAR archive converted successfully!\n\n"
                    f"Output: {output_file}\n"
                    f"Size: {len(output):,} bytes ({len(output)/1024:.2f} KB)"
                ))
                
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                self.tar2bin_log_message("")
                self.tar2bin_log_message("=" * 70)
                self.tar2bin_log_message(f"[ERROR] Conversion failed: {str(e)}")
                self.tar2bin_log_message("=" * 70)
                self.tar2bin_log_message(tb)
                self.tar2bin_progress['value'] = 0
                self.tar2bin_status_label.configure(text="Conversion failed")
                
                self.after(0, lambda: messagebox.showerror(
                    "Conversion Failed",
                    f"Error converting TAR archive:\n\n{str(e)}"
                ))
        
        threading.Thread(target=run_convert, daemon=True).start()

# ==================== IMAGE UTILITY COMMANDS ====================
    
    def img_load(self, img_num: int):
        """Load an image into the specified slot"""
        filename = filedialog.askopenfilename(
            title=f"Load Image {img_num + 1}",
            filetypes=[
                ("PNG images", "*.png"),
                ("All image files", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("All files", "*.*")
            ]
        )
        if not filename:
            return
        
        try:
            img = Image.open(filename)
            self.img_original[img_num] = img.copy()
            self.img_current[img_num] = img.copy()
            self.img_path[img_num] = Path(filename)
            self._update_image_display(img_num)
            
            self.status_label.configure(text=f"Status: Loaded image {img_num + 1} - {Path(filename).name}")
            
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load image:\n\n{str(e)}")


    def img_save(self, img_num: int):
        """Save the image from the specified slot"""
        img = self.img_current[img_num]
        
        if img is None:
            messagebox.showwarning("No Image", f"No image loaded in slot {img_num + 1}")
            return
        
        filename = filedialog.asksaveasfilename(
            title=f"Save Image {img_num + 1}",
            defaultextension=".png",
            filetypes=[
                ("PNG images", "*.png"),
                ("JPEG images", "*.jpg"),
                ("All files", "*.*")
            ]
        )
        if not filename:
            return
        
        try:
            img.save(filename)
            self.status_label.configure(text=f"Status: Saved image {img_num + 1} - {Path(filename).name}")
            messagebox.showinfo("Success", f"Image saved successfully!\n\n{filename}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save image:\n\n{str(e)}")


    def img_clear(self, img_num: int):
        """Clear the image from the specified slot"""
        self.img_original[img_num] = None
        self.img_current[img_num] = None
        self.img_path[img_num] = None
        self.img_display[img_num] = None
        
        if self.img_canvas[img_num]:
            self.img_canvas[img_num].delete("all")
        if self.img_info[img_num]:
            self.img_info[img_num].configure(text="No image loaded")
        
        self.status_label.configure(text=f"Status: Cleared image {img_num + 1}")


    def img_rotate(self, img_num: int, angle: int):
        """Rotate the image in the specified slot"""
        img = self.img_current[img_num]
        
        if img is None:
            messagebox.showwarning("No Image", f"No image loaded in slot {img_num + 1}")
            return
        
        rotated = img.rotate(angle, expand=True)
        self.img_current[img_num] = rotated
        self._update_image_display(img_num)
        self.status_label.configure(text=f"Status: Rotated image {img_num + 1} by {angle}°")


    def img_flip(self, img_num: int, direction: str):
        """Flip the image in the specified slot"""
        img = self.img_current[img_num]
        
        if img is None:
            messagebox.showwarning("No Image", f"No image loaded in slot {img_num + 1}")
            return
        
        if direction == 'h':
            flipped = img.transpose(Image.FLIP_LEFT_RIGHT)
            desc = "horizontally"
        else:
            flipped = img.transpose(Image.FLIP_TOP_BOTTOM)
            desc = "vertically"
        
        self.img_current[img_num] = flipped
        self._update_image_display(img_num)
        self.status_label.configure(text=f"Status: Flipped image {img_num + 1} {desc}")


    def img_resize_dialog(self, img_num: int):
        img = self.img1_current if img_num == 1 else self.img2_current
        
        if img is None:
            messagebox.showwarning("No Image", f"No image loaded in slot {img_num}")
            return
        
        # Create dialog
        dialog = tk.Toplevel(self)
        dialog.title(f"Resize Image {img_num}")
        dialog.geometry("300x150")
        dialog.transient(self)
        dialog.grab_set()
        
        ttk.Label(dialog, text=f"Current size: {img.width} x {img.height}").pack(pady=10)
        
        frame = ttk.Frame(dialog, padding="10")
        frame.pack()
        
        ttk.Label(frame, text="New width:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        width_var = tk.StringVar(value=str(img.width))
        ttk.Entry(frame, textvariable=width_var, width=10).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(frame, text="New height:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        height_var = tk.StringVar(value=str(img.height))
        ttk.Entry(frame, textvariable=height_var, width=10).grid(row=1, column=1, padx=5, pady=5)
        
        def do_resize():
            try:
                new_width = int(width_var.get())
                new_height = int(height_var.get())
                
                if new_width <= 0 or new_height <= 0:
                    messagebox.showerror("Invalid Size", "Width and height must be positive")
                    return
                
                resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                if img_num == 1:
                    self.img1_current = resized
                else:
                    self.img2_current = resized
                
                self._update_image_display(img_num)
                self.status_label.configure(text=f"Status: Resized image {img_num} to {new_width}x{new_height}")
                dialog.destroy()
                
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter valid numbers")
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Resize", command=do_resize).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side='left', padx=5)
    
    def img_grayscale(self, img_num: int):
        img = self.img1_current if img_num == 1 else self.img2_current
        
        if img is None:
            messagebox.showwarning("No Image", f"No image loaded in slot {img_num}")
            return
        
        gray = img.convert('L').convert('RGB')
        
        if img_num == 1:
            self.img1_current = gray
        else:
            self.img2_current = gray
        
        self._update_image_display(img_num)
        self.status_label.configure(text=f"Status: Converted image {img_num} to grayscale")
    
    def img_blur(self, img_num: int):
        img = self.img1_current if img_num == 1 else self.img2_current
        
        if img is None:
            messagebox.showwarning("No Image", f"No image loaded in slot {img_num}")
            return
        
        blurred = img.filter(ImageFilter.BLUR)
        
        if img_num == 1:
            self.img1_current = blurred
        else:
            self.img2_current = blurred
        
        self._update_image_display(img_num)
        self.status_label.configure(text=f"Status: Applied blur to image {img_num}")
    
    def _update_image_display(self, img_num: int):
        """Update the display for the specified image slot"""
        img = self.img_current[img_num]
        canvas = self.img_canvas[img_num]
        info_label = self.img_info[img_num]
        
        if img is None or canvas is None:
            return
        
        # Get canvas size
        canvas.update_idletasks()
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        
        if canvas_width <= 1:
            canvas_width = 300
        if canvas_height <= 1:
            canvas_height = 250
        
        # Calculate scaling to fit canvas
        img_width, img_height = img.size
        scale = min(canvas_width / img_width, canvas_height / img_height, 1.0)
        
        display_width = int(img_width * scale)
        display_height = int(img_height * scale)
        
        # Resize for display
        display_img = img.resize((display_width, display_height), Image.Resampling.LANCZOS)
        
        # Convert to PhotoImage
        photo = ImageTk.PhotoImage(display_img)
        
        # Store reference to prevent garbage collection
        self.img_display[img_num] = photo
        
        # Display on canvas
        canvas.delete("all")
        x = (canvas_width - display_width) // 2
        y = (canvas_height - display_height) // 2
        canvas.create_image(x, y, anchor='nw', image=photo)
        
        # Update info label
        if info_label:
            info_label.configure(text=f"{img.width}x{img.height} | {img.mode}")


    def _tick_ui(self):
        # Process log queue
        try:
            while True:
                widget, message = self.log_queue.get_nowait()
                widget.configure(state='normal')
                widget.insert(tk.END, message + '\n')
                widget.see(tk.END)
                widget.configure(state='disabled')
        except queue.Empty:
            pass

        # Process progress queue
        try:
            while True:
                progressbar, status_label, progress_label, files_label, current, total, message = self.progress_queue.get_nowait()
                if total > 0:
                    percent = (current / total) * 100
                    progressbar['value'] = percent
                    progress_label.configure(text=f"{percent:.1f}%")
                    files_label.configure(text=f"{current}/{total}")
                    status_label.configure(text=message)
                    self.status_label.configure(text=f"Status: {message}")
        except queue.Empty:
            pass

        # Process worker queue
        try:
            while True:
                kind, payload = self._worker_q.get_nowait()
                if kind == PROG_SET:
                    pass
                elif kind == STATUS_SET:
                    self.status_label.config(text=f"Status: {payload}")
                elif kind == DISABLE_UI:
                    self.vbf_btn_build.config(state="disabled")
                    self.vbf_btn_cancel.config(state="normal")
                elif kind == ENABLE_UI:
                    self.vbf_btn_build.config(state="normal")
                    self.vbf_btn_cancel.config(state="disabled")
                elif kind == DONE_OK:
                    self.status_label.config(text=f"Status: Build complete")
                    messagebox.showinfo("Done", payload)
                elif kind == DONE_ERR:
                    self.status_label.config(text="Status: Build failed")
                    messagebox.showerror("Pack error", payload)
        except queue.Empty:
            pass

        self.after(100, self._tick_ui)

    def cmd_about(self):
        messagebox.showinfo(
            "About",
            "Ford Firmware Engineering Tool v3.3\n\n"
            "VBF Tools: VBF unpacker/packer with Python LZSS\n"
            "KZB Tools: Archive extraction and packing\n"
            "TAR Archive Builder: Create TAR archives\n"
            "TAR to Binary: Convert TAR to binary format\n"
            "Image Utility: Display and edit PNG images\n\n"
            "Bitmaps Builder: Custom binary file builder\n"
            "By Jakka351\n"
            "github.com/jakka351"
        )
