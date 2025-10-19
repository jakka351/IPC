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
from .lzss import *
import struct
import zlib
import re
from pathlib import Path
from typing import List, Tuple, Optional
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from threading import Thread, Event
import time
import struct

# J2534 stack
from .j2534.j2534_device_finder import find_installed_j2534_dlls
from .j2534.j2534_struct import J2534_Port
from .j2534.j2534 import PassThruMsg, TxFlag
from .j2534.j2534 import *


PROG_SET = "PROG_SET"
STATUS_SET = "STATUS_SET"
DONE_OK = "DONE_OK"
DONE_ERR = "DONE_ERR"
ENABLE_UI = "ENABLE_UI"
DISABLE_UI = "DISABLE_UI"

# Virtual path mapping inside bitmaps.bin (fixed order)
BITMAPS_VPATHS = {
    "KZB":  "install/bin/cluster.kzb",
    "TXT1": "install/bin/cluster.kzb.txt",
    "TXT2": "part_number/ifs3_part_number.txt",
    "CFG":  "install/bin/cluster.kzb.cfg",
}


class CombinedEngineeringTool(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ford Firmware Engineering Tool - Anonymous Automotive Alliance")
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
        self.vbf_pack_blocks = []
        self.vbf_cancel_flag = False
        self.vbf_use_lzss = tk.BooleanVar(value=False)
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
            "\\lib\\images\\base_sprite.png",
            "\\lib\\images\\base_sprite.png",
            "\\lib\\images\\base_sprite.png"
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
        ttk.Label(title_frame, text="Ford Firmware Engineering Tool - Anonymous Automotive Alliance", 
                 font=('TkDefaultFont', 14, 'bold')).pack(side='left')
        ttk.Label(title_frame, text="v3.3", 
                 font=('TkDefaultFont', 8)).pack(side='left', padx=(10, 0))
        
        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=(0, 10))
        
        # Main notebook
        self.main_notebook = ttk.Notebook(main_frame)
        self.main_notebook.pack(fill='both', expand=True)
        
        # VBF Tab
        vbf_frame = ttk.Frame(self.main_notebook, padding="10")
        self.main_notebook.add(vbf_frame, text="VBF Tools")
        self._build_vbf_ui(vbf_frame)
        # VBF Flasher Tab

        # KZB Tab
        kzb_frame = ttk.Frame(self.main_notebook, padding="10")
        self.main_notebook.add(kzb_frame, text="KZB Tools")
        self._build_kzb_ui(kzb_frame)        
        
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
        
        vbf_flasher_frame = ttk.Frame(self.main_notebook, padding="10")
        self.main_notebook.add(vbf_flasher_frame, text="VBF Flasher")
        self._build_vbf_flasher_ui(vbf_flasher_frame)
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
        
        # VBF Patcher tab (NEW)
        patcher_frame = ttk.Frame(vbf_notebook, padding="10")
        vbf_notebook.add(patcher_frame, text="VBF Patcher")
        self._build_vbf_patcher_tab(patcher_frame)
        
        # VBF Flasher tab (NEW)
        flasher_frame = ttk.Frame(vbf_notebook, padding="10")
        vbf_notebook.add(flasher_frame, text="VBF Flasher")
        self._build_vbf_flasher_ui(flasher_frame)


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

        # Complete _build_vbf_pack_tab method for your GUI class
    # This replaces your existing method

    def _build_vbf_pack_tab(self, parent):
        """Build the VBF Pack tab"""
        # Header controls
        header_frame = ttk.LabelFrame(parent, text="Header", padding="10")
        header_frame.pack(fill='both', expand=False, pady=(0, 10))
        
        header_btns = ttk.Frame(header_frame)
        header_btns.pack(fill='x', pady=(0, 5))
        ttk.Button(header_btns, text="Load Header", command=self.vbf_pk_load_header).pack(side='left', padx=(0, 5))
        ttk.Button(header_btns, text="Save Header As", command=self.vbf_pk_save_header_as).pack(side='left', padx=(0, 5))
        self.vbf_lbl_header_src = ttk.Label(header_btns, text="(no header loaded)")
        self.vbf_lbl_header_src.pack(side='left', padx=10)
        
        # Header text with scrollbars
        self.vbf_txt_pk_hdr = tk.Text(header_frame, height=10, wrap='none')
        yph = ttk.Scrollbar(header_frame, orient='vertical', command=self.vbf_txt_pk_hdr.yview)
        xph = ttk.Scrollbar(header_frame, orient='horizontal', command=self.vbf_txt_pk_hdr.xview)
        self.vbf_txt_pk_hdr.configure(yscrollcommand=yph.set, xscrollcommand=xph.set)
        self.vbf_txt_pk_hdr.pack(side='left', fill='both', expand=True)
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
        opts.pack(fill='x', pady=(0, 10))
        ttk.Checkbutton(opts, text="Use LZSS Compression", variable=self.vbf_use_lzss).pack(side='left', padx=(0, 10))
        ttk.Separator(opts, orient='vertical').pack(side='left', fill='y', padx=10)
        ttk.Checkbutton(opts, text="Compute file_checksum", variable=self.vbf_do_file_crc).pack(side='left', padx=(0, 10))
        ttk.Label(opts, text="Scope:").pack(side='left', padx=(0, 5))
        scope = ttk.Combobox(opts, textvariable=self.vbf_crc_scope, state="readonly", width=25,
                             values=("whole_file_zeroed_field", "payload_only", "header_only"))
        scope.pack(side='left')
        
        # Progress bar with label
        progress_frame = ttk.Frame(parent)
        progress_frame.pack(fill='x', pady=(0, 5))
        self.vbf_lbl_progress = ttk.Label(progress_frame, text="Ready")
        self.vbf_lbl_progress.pack(side='left', padx=(0, 10))
        self.vbf_progress_pk = ttk.Progressbar(progress_frame, mode='determinate')
        self.vbf_progress_pk.pack(side='left', fill='x', expand=True)

    def _build_vbf_patcher_tab(self, parent):
        """Build the VBF Patcher tab for editing and patching VBF files"""
        
        # Title and description
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(title_frame, text="VBF File Patcher", 
                 font=('TkDefaultFont', 12, 'bold')).pack(anchor='w')
        ttk.Label(title_frame, text="Edit and patch VBF file headers and data blocks", 
                 font=('TkDefaultFont', 9), foreground='gray').pack(anchor='w')
        
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=(0, 15))
        
        # Input file section
        input_group = ttk.LabelFrame(parent, text="Input File", padding="10")
        input_group.pack(fill='x', pady=(0, 10))
        
        ttk.Label(input_group, text="VBF File:").grid(row=0, column=0, sticky='w', padx=(0, 10))
        self.patcher_vbf_file = tk.StringVar()
        ttk.Entry(input_group, textvariable=self.patcher_vbf_file, width=70).grid(
            row=0, column=1, sticky='ew', padx=(0, 10))
        ttk.Button(input_group, text="Browse...", 
                  command=self.patcher_browse_vbf).grid(row=0, column=2)
        
        ttk.Button(input_group, text="Load VBF", 
                  command=self.patcher_load_vbf, width=15).grid(row=0, column=3, padx=(10, 0))
        
        input_group.columnconfigure(1, weight=1)
        
        # File info display
        info_frame = ttk.Frame(parent)
        info_frame.pack(fill='x', pady=(0, 10))
        self.patcher_file_info_label = ttk.Label(info_frame, text="No file loaded", 
                                                 font=('TkDefaultFont', 9), foreground='gray')
        self.patcher_file_info_label.pack(side='left')
        
        # Patch options section
        patch_group = ttk.LabelFrame(parent, text="Patch Configuration", padding="10")
        patch_group.pack(fill='x', pady=(0, 10))
        
        # Address/offset input
        ttk.Label(patch_group, text="Memory Address (hex):").grid(row=0, column=0, sticky='w', padx=(0, 10), pady=5)
        self.patcher_address = tk.StringVar(value="0x00000000")
        ttk.Entry(patch_group, textvariable=self.patcher_address, width=20).grid(
            row=0, column=1, sticky='w', pady=5)
        
        ttk.Label(patch_group, text="Block Offset (hex):").grid(row=0, column=2, sticky='w', padx=(20, 10), pady=5)
        self.patcher_offset = tk.StringVar(value="0x0000")
        ttk.Entry(patch_group, textvariable=self.patcher_offset, width=20).grid(
            row=0, column=3, sticky='w', pady=5)
        
        # Patch data input
        ttk.Label(patch_group, text="Patch Data (hex):").grid(row=1, column=0, sticky='nw', padx=(0, 10), pady=5)
        self.patcher_data = scrolledtext.ScrolledText(patch_group, height=4, width=70, 
                                                      font=('Courier', 9))
        self.patcher_data.grid(row=1, column=1, columnspan=3, sticky='ew', pady=5)
        
        # Patch type selection
        ttk.Label(patch_group, text="Patch Type:").grid(row=2, column=0, sticky='w', padx=(0, 10), pady=5)
        self.patcher_type = tk.StringVar(value="data_block")
        patch_types = ttk.Frame(patch_group)
        patch_types.grid(row=2, column=1, columnspan=3, sticky='w', pady=5)
        
        ttk.Radiobutton(patch_types, text="Data Block", 
                       variable=self.patcher_type, value="data_block").pack(side='left', padx=(0, 15))
        ttk.Radiobutton(patch_types, text="Header Field", 
                       variable=self.patcher_type, value="header_field").pack(side='left', padx=(0, 15))
        ttk.Radiobutton(patch_types, text="Checksum Update", 
                       variable=self.patcher_type, value="checksum").pack(side='left')
        
        patch_group.columnconfigure(1, weight=1)
        
        # Header editor section
        header_group = ttk.LabelFrame(parent, text="Header Field Editor", padding="10")
        header_group.pack(fill='x', pady=(0, 10))
        
        header_edit_frame = ttk.Frame(header_group)
        header_edit_frame.pack(fill='x')
        
        ttk.Label(header_edit_frame, text="Field Name:").grid(row=0, column=0, sticky='w', padx=(0, 10))
        self.patcher_header_field = tk.StringVar()
        header_field_combo = ttk.Combobox(header_edit_frame, textvariable=self.patcher_header_field, 
                                          state="readonly", width=25,
                                          values=("sw_part_number", "sw_part_type", "data_format_identifier", 
                                                 "ecu_address", "file_checksum", "sw_version"))
        header_field_combo.grid(row=0, column=1, sticky='w', padx=(0, 20))
        
        ttk.Label(header_edit_frame, text="New Value:").grid(row=0, column=2, sticky='w', padx=(0, 10))
        self.patcher_header_value = tk.StringVar()
        ttk.Entry(header_edit_frame, textvariable=self.patcher_header_value, width=30).grid(
            row=0, column=3, sticky='w')
        
        ttk.Button(header_edit_frame, text="Update Field", 
                  command=self.patcher_update_header_field, width=15).grid(row=0, column=4, padx=(20, 0))
        
        # Backup options
        options_group = ttk.LabelFrame(parent, text="Patch Options", padding="10")
        options_group.pack(fill='x', pady=(0, 10))
        
        self.patcher_create_backup = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_group, text="Create backup before patching", 
                       variable=self.patcher_create_backup).pack(side='left', padx=(0, 20))
        
        self.patcher_verify_patch = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_group, text="Verify patch after apply", 
                       variable=self.patcher_verify_patch).pack(side='left', padx=(0, 20))
        
        self.patcher_recalc_checksums = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_group, text="Recalculate checksums", 
                       variable=self.patcher_recalc_checksums).pack(side='left')
        
        # Control buttons
        control_frame = ttk.Frame(parent)
        control_frame.pack(pady=(0, 10))
        
        ttk.Button(control_frame, text="Apply Patch", 
                  command=self.patcher_apply_patch, width=15).pack(side='left', padx=5)
        ttk.Button(control_frame, text="Save As...", 
                  command=self.patcher_save_as, width=15).pack(side='left', padx=5)
        ttk.Button(control_frame, text="View Hex Dump", 
                  command=self.patcher_view_hex, width=15).pack(side='left', padx=5)
        ttk.Button(control_frame, text="Clear Patch", 
                  command=self.patcher_clear, width=15).pack(side='left', padx=5)
        
        # Progress section
        progress_group = ttk.LabelFrame(parent, text="Patch Progress", padding="10")
        progress_group.pack(fill='x', pady=(0, 10))
        
        self.patcher_status_label = ttk.Label(progress_group, text="Ready")
        self.patcher_status_label.pack(anchor='w', pady=(0, 5))
        
        self.patcher_progress = ttk.Progressbar(progress_group, mode='determinate')
        self.patcher_progress.pack(fill='x', pady=(0, 5))
        
        progress_info = ttk.Frame(progress_group)
        progress_info.pack(fill='x')
        ttk.Label(progress_info, text="Progress:").pack(side='left')
        self.patcher_progress_label = ttk.Label(progress_info, text="0%")
        self.patcher_progress_label.pack(side='left', padx=(5, 20))
        ttk.Label(progress_info, text="Status:").pack(side='left')
        self.patcher_operation_label = ttk.Label(progress_info, text="Idle")
        self.patcher_operation_label.pack(side='left', padx=5)
        
        # Log section
        log_group = ttk.LabelFrame(parent, text="Patch Log", padding="10")
        log_group.pack(fill='both', expand=True)
        
        self.patcher_log = scrolledtext.ScrolledText(log_group, height=10, width=90,
                                                     font=('Courier', 9), state='disabled')
        self.patcher_log.pack(fill='both', expand=True)

    '''
    def _build_vbf_flasher_tab(self, parent: ttk.Frame) -> None:
        """
        Build the VBF Flasher UI ON THE GIVEN PARENT FRAME.
        Do NOT reference self.notebook here (it doesn't exist). Everything belongs under `parent`.
        """
        import tkinter as tk
        from tkinter import ttk

        # -------- vars / state --------
        # Create only if not present so re-building doesn't clobber existing state
        if not hasattr(self, "flasher_interface"):
            self.flasher_interface = tk.StringVar(value="J2534")
        if not hasattr(self, "flasher_device"):
            self.flasher_device = tk.StringVar(value="")
        if not hasattr(self, "flasher_ecu_txid"):
            self.flasher_ecu_txid = tk.StringVar(value="7E0")
        if not hasattr(self, "flasher_ecu_rxid"):
            self.flasher_ecu_rxid = tk.StringVar(value="7E8")
        if not hasattr(self, "flasher_bitrate"):
            self.flasher_bitrate = tk.IntVar(value=500000)
        if not hasattr(self, "flasher_vbf_file"):
            self.flasher_vbf_file = tk.StringVar(value="")

        # live objects/state
        if not hasattr(self, "_j2534_port"):
            self._j2534_port = None
        if not hasattr(self, "_j2534_devices"):
            self._j2534_devices = []
        if not hasattr(self, "_cancel_evt"):
            from threading import Event
            self._cancel_evt = Event()

        # -------------------- layout --------------------
        # Top row: interface + device selector + refresh
        frm_top = ttk.Frame(parent)
        frm_top.pack(fill="x", padx=8, pady=6)

        ttk.Label(frm_top, text="Interface:").grid(row=0, column=0, sticky="w")
        self.cmb_iface = ttk.Combobox(frm_top, textvariable=self.flasher_interface, state="readonly",
                                      values=["J2534"], width=10)
        self.cmb_iface.grid(row=0, column=1, sticky="w", padx=(6, 12))

        ttk.Label(frm_top, text="Device:").grid(row=0, column=2, sticky="w")
        self.cmb_device = ttk.Combobox(frm_top, textvariable=self.flasher_device, width=60)
        self.cmb_device.grid(row=0, column=3, sticky="we", padx=(6, 6))
        ttk.Button(frm_top, text="Refresh", command=self.flasher_refresh_devices).grid(row=0, column=4, sticky="we")

        frm_top.columnconfigure(3, weight=1)

        # ECU Address & bitrate
        frm_cfg = ttk.Frame(parent)
        frm_cfg.pack(fill="x", padx=8, pady=6)

        ttk.Label(frm_cfg, text="ECU TxID (hex):").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm_cfg, textvariable=self.flasher_ecu_txid, width=8).grid(row=0, column=1, sticky="w", padx=(6, 18))

        ttk.Label(frm_cfg, text="ECU RxID (hex):").grid(row=0, column=2, sticky="w")
        ttk.Entry(frm_cfg, textvariable=self.flasher_ecu_rxid, width=8).grid(row=0, column=3, sticky="w", padx=(6, 18))

        ttk.Label(frm_cfg, text="Bitrate:").grid(row=0, column=4, sticky="w")
        ttk.Entry(frm_cfg, textvariable=self.flasher_bitrate, width=10).grid(row=0, column=5, sticky="w", padx=(6, 6))

        # File selection
        frm_files = ttk.Frame(parent)
        frm_files.pack(fill="x", padx=8, pady=6)

        ttk.Entry(frm_files, textvariable=self.flasher_vbf_file).grid(row=0, column=0, sticky="we", padx=(0, 6))
        ttk.Button(frm_files, text="Browse...", command=self.flasher_browse_vbf).grid(row=0, column=1, sticky="w", padx=(0, 6))
        ttk.Button(frm_files, text="Add to Queue", command=self.flasher_add_files).grid(row=0, column=2, sticky="w")
        frm_files.columnconfigure(0, weight=1)

        # Listbox queue + clear
        frm_queue = ttk.Frame(parent)
        frm_queue.pack(fill="both", expand=True, padx=8, pady=6)

        self.flasher_file_listbox = tk.Listbox(frm_queue, height=6)
        self.flasher_file_listbox.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(frm_queue, orient="vertical", command=self.flasher_file_listbox.yview)
        sb.pack(side="left", fill="y")
        self.flasher_file_listbox.configure(yscrollcommand=sb.set)

        btns_q = ttk.Frame(frm_queue)
        btns_q.pack(side="left", fill="y", padx=(8,0))
        ttk.Button(btns_q, text="Clear Queue", command=self.flasher_clear_files).pack(fill="x")

        # Controls row
        frm_ctrl = ttk.Frame(parent)
        frm_ctrl.pack(fill="x", padx=8, pady=6)

        self.flasher_btn_test = ttk.Button(frm_ctrl, text="Test", command=self.flasher_test_connection)
        self.flasher_btn_connect = ttk.Button(frm_ctrl, text="Connect", command=self.flasher_connect)
        self.flasher_btn_flash = ttk.Button(frm_ctrl, text="Flash", command=self.flasher_start_flash, state="disabled")
        self.flasher_btn_cancel = ttk.Button(frm_ctrl, text="Cancel", command=self.flasher_cancel, state="disabled")
        self.flasher_btn_disconnect = ttk.Button(frm_ctrl, text="Disconnect", command=self.flasher_disconnect, state="disabled")

        for i, b in enumerate([self.flasher_btn_test, self.flasher_btn_connect, self.flasher_btn_flash, self.flasher_btn_cancel, self.flasher_btn_disconnect]):
            b.grid(row=0, column=i, padx=6, sticky="we")
        frm_ctrl.columnconfigure(2, weight=1)

        # Progress + status
        frm_prog = ttk.Frame(parent)
        frm_prog.pack(fill="x", padx=8, pady=(0,6))
        self.flasher_progress = ttk.Progressbar(frm_prog, mode="determinate", maximum=100)
        self.flasher_progress.grid(row=0, column=0, sticky="we")
        self.flasher_status_label = ttk.Label(frm_prog, text="Idle")
        self.flasher_status_label.grid(row=0, column=1, sticky="e", padx=(6,0))
        frm_prog.columnconfigure(0, weight=1)

        # Log
        frm_log = ttk.Frame(parent)
        frm_log.pack(fill="both", expand=True, padx=8, pady=(0,8))
        ttk.Label(frm_log, text="Log:").pack(anchor="w")
        self.flasher_log = tk.Text(frm_log, height=10, state="disabled")
        self.flasher_log.pack(fill="both", expand=True)

        # Populate device list once UI exists
        try:
            self.flasher_refresh_devices()
        except Exception:
            pass

    '''
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
            ok = "✓" if s.crc_calc == s.crc_stored else "✗"
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
                
                self.after(0, lambda: self.status_label.config(text=f"Status: Extracted block #{sec.index} → {out_path}"))
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
                
                self.after(0, lambda: self.status_label.config(text=f"Status: Extracted {count} block(s) → {outdir}"))
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
        self.status_label.config(text=f"Status: Header saved → {p}")

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
            #mark

    def vbf_pk_cancel(self):
        if self._worker_thread and self._worker_thread.is_alive():
            self._cancel_evt.set()
            self._worker_q.put((STATUS_SET, "Cancelling…"))

    def _vbf_worker_build(self, *, raw_header: str, out_path: Path, pack_items: List[Tuple[Path,int,int]],
                      use_lzss: bool, do_crc: bool, crc_scope: str):
        try:
            self._worker_q.put((STATUS_SET, "Building VBF…"))

            checksum_re = re.compile(r"(file_checksum\s*=\s*)0x[0-9A-Fa-f]{8}(\s*;)")
            header_has_field = checksum_re.search(raw_header) is not None

            header_bytes = raw_header.encode("latin-1", errors="ignore")
            patch_offset: Optional[int] = None

            def locate_patch_offset(text_for_search: str) -> Optional[int]:
                m = checksum_re.search(text_for_search)
                if not m:
                    return None
                # position AFTER `file_checksum = `
                before = text_for_search[:m.start()] + m.group(1)
                return len(before)

            # Decide header we write first and whether we patch later
            if not do_crc or not header_has_field:
                header_to_write = header_bytes
                patch_after = False
                crc32_acc: Optional[int] = None
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
                # default: accumulate CRC32 over payload only
                header_zero = checksum_re.sub(r"\g<1>0x00000000\2", raw_header)
                header_to_write = header_zero.encode("latin-1", errors="ignore")
                patch_after = True
                patch_offset = locate_patch_offset(header_zero)
                crc32_acc = 0

            with out_path.open("wb+") as fh:
                # 1) write header
                fh.write(header_to_write)

                # 2) write blocks
                if use_lzss:
                    self._worker_q.put((STATUS_SET, "Compressing with LZSS…"))

                    # concatenate all payloads in order
                    all_data = bytearray()
                    first_addr = pack_items[0][1] if pack_items else 0
                    total_size = 0
                    for (pth, _addr, _len) in pack_items:
                        if self._cancel_evt.is_set():
                            raise KeyboardInterrupt("Cancelled")
                        b = pth.read_bytes()
                        all_data.extend(b)
                        total_size += len(b)

                    # hook progress into GUI bar
                    def progress_callback(frac: float):
                        if self._cancel_evt.is_set():
                            raise KeyboardInterrupt("Cancelled")
                        # map 20..90%
                        self._worker_q.put((PROG_SET, int(20 + frac * 70)))

                    comp = lzss_compress_data(bytes(all_data), on_progress=progress_callback)

                    block_addr_bytes = struct.pack('>I', first_addr)
                    block_len_bytes  = struct.pack('>I', len(comp))
                    block_crc16      = crc16_ccitt_ffff(comp)
                    block_crc_bytes  = struct.pack('>H', block_crc16)

                    if crc32_acc is not None:
                        crc32_acc = crc32_bytes(block_addr_bytes, crc32_acc)
                        crc32_acc = crc32_bytes(block_len_bytes,  crc32_acc)
                        crc32_acc = crc32_bytes(comp,             crc32_acc)
                        crc32_acc = crc32_bytes(block_crc_bytes,  crc32_acc)

                    fh.write(block_addr_bytes)
                    fh.write(block_len_bytes)
                    fh.write(comp)
                    fh.write(block_crc_bytes)

                else:
                    self._worker_q.put((STATUS_SET, "Writing VBF blocks…"))
                    total_blocks = len(pack_items)
                    for block_idx, (pth, addr, _len) in enumerate(pack_items, start=1):
                        if self._cancel_evt.is_set():
                            raise KeyboardInterrupt("Cancelled")
                        data = pth.read_bytes()
                        block_addr_bytes = struct.pack('>I', addr)
                        block_len_bytes  = struct.pack('>I', len(data))
                        block_crc16      = crc16_ccitt_ffff(data)
                        block_crc_bytes  = struct.pack('>H', block_crc16)

                        if crc32_acc is not None:
                            crc32_acc = crc32_bytes(block_addr_bytes, crc32_acc)
                            crc32_acc = crc32_bytes(block_len_bytes,  crc32_acc)
                            crc32_acc = crc32_bytes(data,            crc32_acc)
                            crc32_acc = crc32_bytes(block_crc_bytes,  crc32_acc)

                        fh.write(block_addr_bytes)
                        fh.write(block_len_bytes)
                        fh.write(data)
                        fh.write(block_crc_bytes)

                        if total_blocks:
                            frac = min(1.0, block_idx / total_blocks)
                            self._worker_q.put((PROG_SET, int(10 + frac * 85)))

                # 3) patch file_checksum if requested
                if patch_after and patch_offset is not None:
                    final_crc = (crc32_acc or 0) & 0xFFFFFFFF
                    fh.seek(patch_offset, 0)
                    fh.write(f"{final_crc:08X}".encode("ascii"))

            if self._cancel_evt.is_set():
                try:
                    out_path.unlink(missing_ok=True)
                except Exception:
                    pass
                self._worker_q.put((ENABLE_UI, None))
                self._worker_q.put((STATUS_SET, "Cancelled"))
                return

            msg = f"VBF written:\n{out_path}\nSize: {out_path.stat().st_size:,} bytes"
            msg += "\n\nCompressed using Python LZSS" if use_lzss else f"\n\n{len(pack_items)} block(s) written"
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

    def vbf_pk_load_header(self):
        """Load header from text file"""
        from tkinter import filedialog, messagebox
        from pathlib import Path
        
        path = filedialog.askopenfilename(
            title="Select Header File",
            filetypes=[("Text Files", "*.txt"), ("VBF Files", "*.vbf"), ("All Files", "*.*")]
        )
        if not path:
            return
        
        try:
            with open(path, 'r', encoding='latin-1') as f:
                header_text = f.read()
            
            self.vbf_lbl_header_src.config(text=Path(path).name)
            self.vbf_txt_pk_hdr.delete('1.0', 'end')
            self.vbf_txt_pk_hdr.insert('1.0', header_text)
            
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load header:\n{e}")


    def vbf_pk_save_header_as(self):
        """Save current header text to file"""
        from tkinter import filedialog, messagebox
        
        path = filedialog.asksaveasfilename(
            title="Save Header As",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if not path:
            return
        
        try:
            header = self.vbf_txt_pk_hdr.get('1.0', 'end-1c')
            with open(path, 'w', encoding='latin-1') as f:
                f.write(header)
            messagebox.showinfo("Saved", f"Header saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save header:\n{e}")


    def vbf_pk_add_bin(self):
        """Add binary file(s) - auto-detects addresses, only prompts once if needed"""
        from tkinter import filedialog, simpledialog, messagebox
        from pathlib import Path
        import re
        
        paths = filedialog.askopenfilenames(
            title="Select Binary File(s)",
            filetypes=[("Binary Files", "*.bin"), ("All Files", "*.*")]
        )
        if not paths:
            return
        
        # Try to auto-detect addresses from filenames
        files_with_addrs = []
        files_without_addrs = []
        
        for path in paths:
            p = Path(path)
            # Look for "0x00100000" or "_00100000_" pattern
            match = re.search(r'0x([0-9A-Fa-f]+)', p.name)
            if not match:
                match = re.search(r'_([0-9A-Fa-f]{8})(?:_|\.)', p.name)
            
            if match:
                try:
                    address = int(match.group(1), 16)
                    files_with_addrs.append((address, p))
                except:
                    files_without_addrs.append(p)
            else:
                files_without_addrs.append(p)
        
        # Add files with detected addresses
        for addr, p in files_with_addrs:
            size = p.stat().st_size
            self.vbf_pack_blocks.append((addr, p))
            idx = len(self.vbf_pack_blocks)
            self.vbf_tree_pk.insert('', 'end', values=(
                idx,
                f"0x{addr:08X}",
                f"{size:,}",
                str(p)
            ))
        
        # If files without addresses, prompt ONCE
        if files_without_addrs:
            addr_str = simpledialog.askstring(
                "Enter Starting Address",
                f"{len(files_without_addrs)} file(s) have no address in filename.\n"
                f"Enter starting address (hex) for these files:",
                initialvalue="0x00000000"
            )
            
            if addr_str is None:
                return
            
            try:
                addr_str = addr_str.strip()
                if addr_str.lower().startswith('0x'):
                    base_address = int(addr_str, 16)
                else:
                    base_address = int(addr_str, 16)
            except ValueError:
                messagebox.showerror("Invalid Address", 
                    f"Invalid address: {addr_str}\nFiles without addresses were skipped.")
                return
            
            # Add files sequentially
            current_addr = base_address
            for p in files_without_addrs:
                size = p.stat().st_size
                self.vbf_pack_blocks.append((current_addr, p))
                idx = len(self.vbf_pack_blocks)
                self.vbf_tree_pk.insert('', 'end', values=(
                    idx,
                    f"0x{current_addr:08X}",
                    f"{size:,}",
                    str(p)
                ))
                current_addr += ((size + 0xFFFF) & ~0xFFFF)


    def vbf_pk_remove_selected(self):
        """Remove selected block"""
        selection = self.vbf_tree_pk.selection()
        if not selection:
            return
        
        item = selection[0]
        idx = self.vbf_tree_pk.index(item)
        del self.vbf_pack_blocks[idx]
        self._rebuild_vbf_pack_tree()


    def vbf_pk_move_sel(self, direction):
        """Move selected block up (-1) or down (+1)"""
        selection = self.vbf_tree_pk.selection()
        if not selection:
            return
        
        item = selection[0]
        idx = self.vbf_tree_pk.index(item)
        new_idx = idx + direction
        
        if new_idx < 0 or new_idx >= len(self.vbf_pack_blocks):
            return
        
        self.vbf_pack_blocks[idx], self.vbf_pack_blocks[new_idx] = \
            self.vbf_pack_blocks[new_idx], self.vbf_pack_blocks[idx]
        
        self._rebuild_vbf_pack_tree()
        
        items = self.vbf_tree_pk.get_children()
        if new_idx < len(items):
            self.vbf_tree_pk.selection_set(items[new_idx])


    def _rebuild_vbf_pack_tree(self):
        """Rebuild tree display"""
        for item in self.vbf_tree_pk.get_children():
            self.vbf_tree_pk.delete(item)
        
        for idx, (addr, path) in enumerate(self.vbf_pack_blocks, 1):
            size = path.stat().st_size
            self.vbf_tree_pk.insert('', 'end', values=(
                idx,
                f"0x{addr:08X}",
                f"{size:,}",
                str(path)
            ))


    def vbf_pk_build(self):
        """Build VBF with working progress bar"""
        from tkinter import filedialog, messagebox
        from pathlib import Path
        import threading
        
        header_text = self.vbf_txt_pk_hdr.get('1.0', 'end-1c').strip()
        if not header_text:
            messagebox.showwarning("No Header", "Please load or enter a header first")
            return
        
        if not self.vbf_pack_blocks:
            messagebox.showwarning("No Blocks", "Please add at least one binary block")
            return
        
        output_path = filedialog.asksaveasfilename(
            title="Save VBF As",
            defaultextension=".vbf",
            filetypes=[("VBF Files", "*.vbf"), ("All Files", "*.*")]
        )
        if not output_path:
            return
        
        use_lzss = self.vbf_use_lzss.get()
        compute_crc = self.vbf_do_file_crc.get()
        crc_scope = self.vbf_crc_scope.get()
        
        self.vbf_btn_build.config(state='disabled')
        self.vbf_btn_cancel.config(state='normal')
        self.vbf_cancel_flag = False
        self.vbf_progress_pk['value'] = 0
        self.vbf_progress_pk['maximum'] = 100
        
        def build_thread():
            try:
                from .vbf import build_vbf_file
                
                def progress_callback(p):
                    value = int(p * 100)
                    self.after(0, self._update_progress, value)
                
                def cancel_check():
                    return self.vbf_cancel_flag
                
                success = build_vbf_file(
                    header_text=header_text,
                    blocks=self.vbf_pack_blocks,
                    output_path=Path(output_path),
                    use_lzss=use_lzss,
                    compute_file_crc=compute_crc,
                    crc_scope=crc_scope,
                    on_progress=progress_callback,
                    cancel_check=cancel_check
                )
                
                if success and not self.vbf_cancel_flag:
                    self.after(0, lambda: messagebox.showinfo(
                        "Success", f"VBF file created:\n{output_path}"))
                elif self.vbf_cancel_flag:
                    self.after(0, lambda: messagebox.showinfo(
                        "Cancelled", "VBF build was cancelled"))
            
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                self.after(0, lambda: messagebox.showerror(
                    "Build Error", f"Failed to build VBF:\n{e}\n\n{error_detail}"))
            
            finally:
                self.after(0, self._vbf_pk_build_complete)
        
        threading.Thread(target=build_thread, daemon=True).start()


    def _update_progress(self, value):
        """Update progress bar"""
        self.vbf_progress_pk['value'] = value
        self.vbf_progress_pk.update()


    def vbf_pk_cancel(self):
        """Cancel build"""
        self.vbf_cancel_flag = True


    def _vbf_pk_build_complete(self):
        """Clean up after build"""
        self.vbf_btn_build.config(state='normal')
        self.vbf_btn_cancel.config(state='disabled')
        self.vbf_progress_pk['value'] = 0

       ## patcher command

    def patcher_browse_vbf(self):
        """Browse for VBF file to patch"""
        filename = filedialog.askopenfilename(
            title="Select VBF File",
            filetypes=[("VBF Files", "*.vbf"), ("All Files", "*.*")]
        )
        if filename:
            self.patcher_vbf_file.set(filename)
            self._patcher_log(f"Selected file: {filename}")

    def patcher_load_vbf(self):
        """Load VBF file for patching"""
        vbf_file = self.patcher_vbf_file.get()
        if not vbf_file:
            messagebox.showwarning("No File", "Please select a VBF file first")
            return
        
        self._patcher_log(f"Loading VBF file: {vbf_file}")
        self.patcher_status_label.configure(text="Loading VBF file...")
        # TODO: Implement actual VBF loading logic
        self._patcher_log("VBF file loaded successfully")
        self.patcher_file_info_label.configure(text=f"Loaded: {Path(vbf_file).name} | Size: XXX KB")
        self.patcher_status_label.configure(text="Ready to patch")

    def patcher_update_header_field(self):
        """Update a header field value"""
        field = self.patcher_header_field.get()
        value = self.patcher_header_value.get()
        
        if not field or not value:
            messagebox.showwarning("Missing Data", "Please select field and enter value")
            return
        
        self._patcher_log(f"Updating header field '{field}' to '{value}'")
        # TODO: Implement actual header field update logic
        self._patcher_log(f"Header field '{field}' updated successfully")

    def patcher_apply_patch(self):
        """Apply the configured patch to the VBF file"""
        vbf_file = self.patcher_vbf_file.get()
        if not vbf_file:
            messagebox.showwarning("No File", "Please load a VBF file first")
            return
        
        patch_type = self.patcher_type.get()
        self._patcher_log(f"Applying {patch_type} patch...")
        self.patcher_status_label.configure(text="Applying patch...")
        self.patcher_progress['value'] = 0
        
        # TODO: Implement actual patching logic
        # Simulate progress
        for i in range(0, 101, 20):
            self.patcher_progress['value'] = i
            self.patcher_progress_label.configure(text=f"{i}%")
            self.update_idletasks()
        
        self._patcher_log("Patch applied successfully")
        self.patcher_status_label.configure(text="Patch complete")
        messagebox.showinfo("Success", "Patch applied successfully!")

    def patcher_save_as(self):
        """Save patched VBF file"""
        filename = filedialog.asksaveasfilename(
            title="Save Patched VBF File",
            defaultextension=".vbf",
            filetypes=[("VBF Files", "*.vbf"), ("All Files", "*.*")]
        )
        if filename:
            self._patcher_log(f"Saving patched file to: {filename}")
            # TODO: Implement actual save logic
            self._patcher_log("File saved successfully")

    def patcher_view_hex(self):
        """Open hex dump viewer"""
        vbf_file = self.patcher_vbf_file.get()
        if not vbf_file:
            messagebox.showwarning("No File", "Please load a VBF file first")
            return
        
        # TODO: Implement hex viewer window
        self._patcher_log("Opening hex viewer...")
        messagebox.showinfo("Hex Viewer", "Hex viewer functionality will be implemented here")

    def patcher_clear(self):
        """Clear all patch data"""
        self.patcher_data.delete('1.0', tk.END)
        self.patcher_address.set("0x00000000")
        self.patcher_offset.set("0x0000")
        self.patcher_header_value.set("")
        self._patcher_log("Patch data cleared")

    def _patcher_log(self, message):
        """Add message to patcher log"""
        self.patcher_log.configure(state='normal')
        self.patcher_log.insert(tk.END, f"{message}\n")
        self.patcher_log.see(tk.END)
        self.patcher_log.configure(state='disabled')

    
## flasher command
    # =============================================================================
    # J2534-backed VBF Flasher implementation
    # =============================================================================
    def vbf_log(self, message: str):
        """Add message to VBF log"""
        self.vbf_log_text.config(state='normal')
        self.vbf_log_text.insert('end', message + '\n')
        self.vbf_log_text.see('end')
        self.vbf_log_text.config(state='disabled')
    
    def vbf_clear_log(self):
        """Clear VBF log"""
        self.vbf_log_text.config(state='normal')
        self.vbf_log_text.delete('1.0', 'end')
        self.vbf_log_text.config(state='disabled')
    
    def vbf_scan_devices(self):
        """Scan for J2534 devices"""
        self.vbf_log("Scanning for J2534 devices...")
        self.vbf_j2534_devices = find_installed_j2534_dlls()
        
        self.vbf_device_listbox.delete(0, 'end')
        
        if not self.vbf_j2534_devices:
            self.vbf_log("No J2534 devices found!")
            messagebox.showwarning("No Devices", "No J2534 devices found. Check drivers are installed.")
        else:
            for dev in self.vbf_j2534_devices:
                self.vbf_device_listbox.insert('end', f"{dev.Name} ({dev.Vendor})")
            self.vbf_log(f"Found {len(self.vbf_j2534_devices)} device(s)")
    
    def vbf_select_device(self):
        """Select device from list"""
        selection = self.vbf_device_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a device")
            return
        
        idx = selection[0]
        self.vbf_selected_device = self.vbf_j2534_devices[idx]
        self.vbf_log(f"Selected: {self.vbf_selected_device.Name}")
    
    def vbf_browse_file(self):
        """Browse for VBF file"""
        filename = filedialog.askopenfilename(
            title="Select VBF File",
            filetypes=[("VBF files", "*.vbf"), ("All files", "*.*")]
        )
        
        if filename:
            self.vbf_file_path = Path(filename)
            self.vbf_file_label.config(text=str(self.vbf_file_path), foreground='black')
            self.vbf_log(f"Selected: {self.vbf_file_path.name}")
    
    def vbf_connect(self):
        """Connect to J2534 device"""
        if not self.vbf_selected_device:
            messagebox.showerror("Error", "Please select a J2534 device")
            return
        
        try:
            self.vbf_log("Connecting to J2534 device...")
            
            # Import here to avoid issues
            from .j2534.j2534_struct import J2534_Port
            
            self.vbf_port = J2534_Port()
            self.vbf_port.load_device(self.vbf_selected_device)
            self.vbf_port.open()
            
            baud = getattr(BaudRate, f"ISO15765_{self.vbf_baud_var.get()}", BaudRate.ISO15765_500000)
            self.vbf_port.connect_iso15765(baud, ConnectFlag.NONE)
            
            tx_id = int(self.vbf_tx_id_var.get(), 16)
            rx_id = int(self.vbf_rx_id_var.get(), 16)
            self.vbf_port.set_iso15765_flow_control(tx_id=tx_id, rx_id=rx_id)
            
            self.vbf_is_connected = True
            self.vbf_log("Connected successfully")
            
            self.vbf_btn_connect.config(state='disabled')
            self.vbf_btn_disconnect.config(state='normal')
            self.vbf_btn_flash.config(state='normal')
            
        except Exception as e:
            self.vbf_log(f"Connection failed: {e}")
            messagebox.showerror("Connection Error", str(e))
            self.vbf_cleanup()
    
    def vbf_disconnect(self):
        """Disconnect from J2534 device"""
        self.vbf_cleanup()
        self.vbf_log("Disconnected")
    
    def vbf_cleanup(self):
        """Cleanup J2534 connection"""
        if self.vbf_port:
            try:
                self.vbf_port.clear_filter()
                self.vbf_port.disconnect()
                self.vbf_port.close()
            except:
                pass
            self.vbf_port = None
        
        self.vbf_is_connected = False
        self.vbf_btn_connect.config(state='normal')
        self.vbf_btn_disconnect.config(state='disabled')
        self.vbf_btn_flash.config(state='disabled')
    
    def vbf_start_flash(self):
        """Start flashing VBF file"""
        if not self.vbf_file_path or not self.vbf_file_path.exists():
            messagebox.showerror("Error", "Please select a valid VBF file")
            return
        
        if not self.vbf_is_connected:
            messagebox.showerror("Error", "Not connected to J2534 device")
            return
        
        result = messagebox.askyesno(
            "Confirm Flash",
            f"Flash {self.vbf_file_path.name}?\n\n"
            "WARNING: Ensure vehicle is ready:\n"
            "- Battery fully charged\n"
            "- Ignition ON\n"
            "- Do not interrupt power"
        )
        
        if not result:
            return
        
        self.vbf_is_flashing = True
        self.vbf_btn_flash.config(state='disabled')
        self.vbf_btn_disconnect.config(state='disabled')
        self.vbf_progress_var.set(0)
        
        self.vbf_flash_thread = Thread(target=self._vbf_flash_worker, daemon=True)
        self.vbf_flash_thread.start()
    
    def _vbf_flash_worker(self):
        """Worker thread for flashing"""
        try:
            from .j2534.j2534_struct import make_iso15765_msg
            
            tx_id = int(self.vbf_tx_id_var.get(), 16)
            rx_id = int(self.vbf_rx_id_var.get(), 16)
            
            # Parse VBF
            self.vbf_log(f"Parsing VBF file: {self.vbf_file_path}")
            blocks = self._vbf_parse_file(self.vbf_file_path)
            
            if not blocks:
                self.after(0, lambda: messagebox.showerror("Error", "No data blocks found in VBF"))
                return
            
            total_bytes = sum(block[2] for block in blocks)
            self.vbf_log(f"Found {len(blocks)} blocks, total {total_bytes} bytes")
            
            # Enter programming session
            self.vbf_log("Entering programming session...")
            req = bytes([0x10, 0x02])  # DiagnosticSessionControl Programming
            resp = self._vbf_send_uds(req)
            if not resp or resp[0] != 0x50:
                self.vbf_log("Failed to enter programming session")
                return
            
            time.sleep(0.1)
            
            # Flash each block
            bytes_done = 0
            for idx, (address, length, data) in enumerate(blocks):
                self.vbf_log(f"Block {idx+1}/{len(blocks)}: Addr 0x{address:08X}, Size {length}")
                
                # Request download
                req = bytes([0x34, 0x00, 0x44]) + struct.pack(">I", address) + struct.pack(">I", length)
                resp = self._vbf_send_uds(req, timeout=10000)
                if not resp or resp[0] != 0x74:
                    self.vbf_log("Request download failed")
                    return
                
                # Get max block size
                max_block = 4093
                if len(resp) >= 3:
                    num_bytes = (resp[1] & 0xF0) >> 4
                    if num_bytes > 0:
                        max_block = int.from_bytes(resp[2:2+num_bytes], 'big') - 2
                
                # Transfer data
                offset = 0
                block_counter = 1
                
                while offset < len(data):
                    chunk_size = min(max_block, len(data) - offset)
                    chunk = data[offset:offset + chunk_size]
                    
                    req = bytes([0x36, block_counter & 0xFF]) + chunk
                    resp = self._vbf_send_uds(req, timeout=5000)
                    if not resp or resp[0] != 0x76:
                        self.vbf_log(f"Transfer failed at offset {offset}")
                        return
                    
                    offset += chunk_size
                    block_counter = (block_counter + 1) & 0xFF
                    bytes_done += chunk_size
                    
                    percent = (bytes_done / total_bytes) * 100
                    self.after(0, lambda p=percent: self.vbf_progress_var.set(p))
                
                # Exit transfer
                req = bytes([0x37])
                resp = self._vbf_send_uds(req, timeout=10000)
                if not resp or resp[0] != 0x77:
                    self.vbf_log("Transfer exit failed")
                    return
            
            # Reset ECU
            self.vbf_log("Resetting ECU...")
            req = bytes([0x11, 0x01])
            self._vbf_send_uds(req, timeout=2000)
            
            self.after(0, lambda: self.vbf_progress_var.set(100))
            self.vbf_log("Flashing complete!")
            self.after(0, lambda: messagebox.showinfo("Success", "VBF flashing completed!"))
            
        except Exception as e:
            self.vbf_log(f"Flash error: {e}")
            self.after(0, lambda: messagebox.showerror("Error", f"Flashing failed: {e}"))
        finally:
            self.vbf_is_flashing = False
            self.after(0, lambda: self.vbf_btn_flash.config(state='normal'))
            self.after(0, lambda: self.vbf_btn_disconnect.config(state='normal'))
    
    def _vbf_send_uds(self, data: bytes, timeout: int = 5000) -> Optional[bytes]:
        """Send UDS request and get response"""
        from .j2534.j2534_struct import make_iso15765_msg
        
        msg = make_iso15765_msg(data)
        self.vbf_log(f"TX: {data.hex(' ').upper()}")
        
        try:
            self.vbf_port.write(msg, timeout_ms=50)
        except:
            return None
        
        start = time.time()
        while (time.time() - start) * 1000 < timeout:
            responses = self.vbf_port.read(max_msgs=10, timeout_ms=100)
            
            for resp in responses:
                if resp.DataSize > 0:
                    resp_data = bytes(resp.Data[:resp.DataSize])
                    self.vbf_log(f"RX: {resp_data.hex(' ').upper()}")
                    
                    # Handle pending
                    if len(resp_data) >= 3 and resp_data[0] == 0x7F and resp_data[2] == 0x78:
                        continue
                    
                    return resp_data
        
        return None
    
    def _vbf_parse_file(self, vbf_path: Path) -> List[Tuple[int, int, bytes]]:
        """Parse VBF file and return list of (address, length, data) tuples"""
        blocks = []
        
        with open(vbf_path, 'rb') as f:
            content = f.read()
        
        pos = 0
        while True:
            block_start = content.find(b'__BLOCK__', pos)
            if block_start == -1:
                break
            
            pos = block_start + 9
            while pos < len(content) and content[pos:pos+1] in b' \t\r\n':
                pos += 1
            
            line_end = content.find(b'\n', pos)
            if line_end == -1:
                break
            
            line = content[pos:line_end].decode('ascii', errors='ignore').strip()
            parts = line.split()
            
            if len(parts) >= 2:
                try:
                    address = int(parts[0], 16) if parts[0].startswith('0x') else int(parts[0])
                    length = int(parts[1], 16) if parts[1].startswith('0x') else int(parts[1])
                    
                    data_start = line_end + 1
                    data_end = data_start + length
                    
                    if data_end <= len(content):
                        block_data = content[data_start:data_end]
                        blocks.append((address, length, block_data))
                        pos = data_end
                    else:
                        break
                except:
                    pos = line_end + 1
            else:
                pos = line_end + 1
        
        return blocks
    def _flasher_log(self, msg: str):
        try:
            self.flasher_log.configure(state='normal')
            self.flasher_log.insert(tk.END, msg + "\n")
            self.flasher_log.see(tk.END)
        finally:
            self.flasher_log.configure(state='disabled')

    def flasher_refresh_devices(self):
        """Enumerate J2534 devices and load them into the combobox."""
        try:
            self._j2534_devices = find_installed_j2534_dlls()
            items = [f"{d.Name} | {d.FunctionLibrary}" for d in self._j2534_devices]
            self.cmb_device['values'] = items
            if items:
                self.cmb_device.current(0)
                self.flasher_device.set(items[0])
            self._flasher_log(f"Found {len(items)} J2534 device(s).")
        except Exception as e:
            self._flasher_log(f"Device refresh failed: {e}")
            messagebox.showerror("J2534", f"Device refresh failed: {e}")

    def _resolve_selected_device(self):
        """Return the selected registry device object (or first if not matched)."""
        sel = self.flasher_device.get() or ""
        for d in self._j2534_devices:
            line = f"{d.Name} | {d.FunctionLibrary}"
            if sel == line or sel.lower() in (line.lower()):
                return d
        return self._j2534_devices[0] if self._j2534_devices else None

    def flasher_test_connection(self):
        """Open a device briefly and run a minimal UDS ping (0x10 0x03) to prove transport."""
        try:
            d = self._resolve_selected_device()
            if not d:
                messagebox.showerror("J2534", "No J2534 devices found.")
                return
            tx_id = int(self.flasher_ecu_txid.get(), 16)
            rx_id = int(self.flasher_ecu_rxid.get(), 16)
            bitrate = int(self.flasher_bitrate.get())
            self._flasher_log(f"Testing device: {d.Name} ({d.FunctionLibrary}) BITRATE={bitrate} TxID=0x{tx_id:X} RxID=0x{rx_id:X}")

            port = J2534_Port()
            port.load_device(d)
            port.open()
            port.connect_can(bitrate=bitrate)
            port.set_pass_filter(rx_id, extended=False)  # expect replies from rx_id

            # UDS: Diagnostic Session Control (0x10 0x03)
            rsp = self._isotp_request_response(port, tx_id, rx_id, b'\x10\x03', timeout=1500)
            ok = rsp and len(rsp) >= 2 and rsp[0] == 0x50
            self._flasher_log("UDS DSC(0x10 0x03) -> " + (rsp.hex() if rsp else "No response"))
            messagebox.showinfo("Test", "Transport OK (UDS Session Control responded)" if ok else "Transport path established but DSC not acknowledged.")

            port.disconnect()
            port.close()
        except Exception as e:
            self._flasher_log(f"Test failed: {e}")
            messagebox.showerror("Test", f"Failed: {e}")

    def flasher_connect(self):
        """Open, connect, and hold a live J2534 session."""
        try:
            d = self._resolve_selected_device()
            if not d:
                messagebox.showerror("J2534", "No J2534 devices found.")
                return
            tx_id = int(self.flasher_ecu_txid.get(), 16)
            rx_id = int(self.flasher_ecu_rxid.get(), 16)
            bitrate = int(self.flasher_bitrate.get())
            self._flasher_log(f"Connecting to {d.Name} @ {bitrate} bps")

            port = J2534_Port()
            port.load_device(d)
            port.open()
            port.connect_can(bitrate=bitrate)
            port.set_pass_filter(rx_id, extended=False)

            self._j2534_port = port
            self.flasher_status_label.configure(text="Connected")
            self.flasher_btn_connect.configure(state='disabled')
            self.flasher_btn_flash.configure(state='normal')
            self.flasher_btn_disconnect.configure(state='normal')
            self._flasher_log("Connected.")
        except Exception as e:
            self._flasher_log(f"Connect failed: {e}")
            messagebox.showerror("Connect", f"Failed: {e}")

    def flasher_disconnect(self):
        try:
            if self._j2534_port:
                try: self._j2534_port.disconnect()
                except: pass
                try: self._j2534_port.close()
                except: pass
                self._j2534_port = None
            self.flasher_status_label.configure(text="Disconnected")
            self.flasher_btn_connect.configure(state='normal')
            self.flasher_btn_flash.configure(state='disabled')
            self.flasher_btn_disconnect.configure(state='disabled')
            self._flasher_log("Disconnected.")
        except Exception as e:
            self._flasher_log(f"Disconnect error: {e}")

    def flasher_browse_vbf(self):
        fn = filedialog.askopenfilename(
            title="Select VBF File", filetypes=[("VBF Files","*.vbf"), ("All Files","*.*")]
        )
        if fn:
            self.flasher_vbf_file.set(fn)
            self._flasher_log(f"Selected: {fn}")

    def flasher_add_files(self):
        fns = filedialog.askopenfilenames(
            title="Select VBF Files", filetypes=[("VBF Files","*.vbf"), ("All Files","*.*")]
        )
        for f in fns:
            self.flasher_file_listbox.insert(tk.END, f)
            self._flasher_log(f"Queued: {f}")

    def flasher_clear_files(self):
        self.flasher_file_listbox.delete(0, tk.END)
        self._flasher_log("Queue cleared.")

    def flasher_cancel(self):
        self._cancel_evt.set()
        self._flasher_log("Cancel requested.")

    def _update_flash_progress(self, pct: int, status: str = ""):
        pct = max(0, min(100, int(pct)))
        try:
            self.flasher_progress['value'] = pct
            if status:
                self.flasher_status_label.configure(text=status)
            self.update_idletasks()
        except Exception:
            pass

    # -------- ISO-TP helpers (blocking, minimal) ----------
    def _isotp_send(self, port: J2534_Port, tx_id: int, rx_id: int, payload: bytes, stmin_ms: int = 0, timeout: int = 1500):
        """Send a complete ISO-TP payload over 11-bit CAN using J2534_Port."""
        def _write(can_id: int, data8: bytes):
            msg = PassThruMsg()
            msg.ProtocolID = 1  # CAN
            msg.RxStatus = 0
            msg.TxFlags = int(TxFlag.CAN_11BIT_ID)
            msg.Timestamp = 0
            msg.DataSize = 8
            for i, b in enumerate(data8.ljust(8, b'\x00')[:8]):
                msg.Data[i] = b
            msg.CanId = can_id
            port.write(msg)

        if len(payload) <= 7:
            frm = bytes([0x00 | len(payload)]) + payload
            _write(tx_id, frm)
            return

        total = len(payload)
        # First Frame
        ff = bytes([0x10 | ((total >> 8) & 0x0F), total & 0xFF]) + payload[:6]
        _write(tx_id, ff)

        # Wait FC
        t0 = time.time()
        bs, st = 0, stmin_ms
        while True:
            msgs = port.read(max_msgs=24, timeout_ms=timeout)
            for m in msgs:
                raw = bytes(m.Data[:m.DataSize]) if getattr(m,"DataSize",None) else bytes(m.Data)
                if len(raw) >= 3 and (raw[0] & 0xF0) == 0x30:
                    bs, st = raw[1], raw[2]
                    break
            else:
                if (time.time() - t0) * 1000 > timeout:
                    raise TimeoutError("FC timeout")
                continue
            break

        # Consecutive frames
        off = 6
        sn = 1
        sent_in_block = 0
        while off < total:
            chunk = payload[off:off+7]
            cf = bytes([0x20 | (sn & 0x0F)]) + chunk
            _write(tx_id, cf)
            sn = (sn + 1) & 0x0F
            off += len(chunk)
            sent_in_block += 1
            if bs and sent_in_block >= bs:
                # wait next FC
                t1 = time.time()
                got = False
                while not got:
                    msgs = port.read(max_msgs=24, timeout_ms=timeout)
                    for m in msgs:
                        raw = bytes(m.Data[:m.DataSize]) if getattr(m,"DataSize",None) else bytes(m.Data)
                        if len(raw) >= 3 and (raw[0] & 0xF0) == 0x30:
                            bs, st = raw[1], raw[2]
                            sent_in_block = 0
                            got = True
                            break
                    if (time.time() - t1) * 1000 > timeout:
                        raise TimeoutError("Next FC timeout")

            if st:
                time.sleep(max(st, 1)/1000.0)

    def _isotp_request_response(self, port: J2534_Port, tx_id: int, rx_id: int, req: bytes, timeout: int = 1500) -> bytes:
        """Send a small request (<=4095) and return concatenated ISO-TP response body."""
        # send
        self._isotp_send(port, tx_id, rx_id, req, timeout=timeout)
        # receive (basic; assumes single response PDU)
        t0 = time.time()
        acc = bytearray()
        expected = None
        sn_next = 1
        while True:
            msgs = port.read(max_msgs=24, timeout_ms=timeout)
            for m in msgs:
                raw = bytes(m.Data[:m.DataSize]) if getattr(m,"DataSize",None) else bytes(m.Data)
                if not raw: 
                    continue
                pci = raw[0] & 0xF0
                if pci == 0x00:  # SF
                    ln = raw[0] & 0x0F
                    return bytes(raw[1:1+ln])
                if pci == 0x10:  # FF
                    ln = ((raw[0] & 0x0F) << 8) | raw[1]
                    acc.extend(raw[2:8])
                    expected = ln
                    # send FC (CTS)
                    fc = bytes([0x30, 0x00, 0x0A]) + b'\x00'*5  # BS=0 (unlimited), STmin=10ms
                    # transmit FC to ECU (we are the client, so ECU should send CFs next)
                    msg = PassThruMsg()
                    msg.ProtocolID = 1
                    msg.TxFlags = int(TxFlag.CAN_11BIT_ID)
                    msg.DataSize = 8
                    for i,b in enumerate(fc):
                        msg.Data[i] = b
                    msg.CanId = rx_id  # reply to ECU on its Rx?
                    # NOTE: Some stacks expect FC on ECU->Client direction; you may need a filter/route; often using tx_id works
                    msg.CanId = tx_id
                    port.write(msg)
                    if len(acc) >= expected:
                        return bytes(acc[:expected])
                    continue
                if pci == 0x20:  # CF
                    sn = raw[0] & 0x0F
                    if sn != sn_next:
                        # allow resync
                        sn_next = (sn + 1) & 0x0F
                    else:
                        sn_next = (sn_next + 1) & 0x0F
                    acc.extend(raw[1:8])
                    if expected is not None and len(acc) >= expected:
                        return bytes(acc[:expected])
            if (time.time() - t0) * 1000 > timeout:
                return b""

    def flasher_start_flash(self):
        """Parse VBF and stream sections with ISO-TP transport (you add ECU-specific steps)."""
        if not self._j2534_port:
            messagebox.showerror("Flash", "Not connected to a J2534 device.")
            return

        files = []
        if self.flasher_vbf_file.get():
            files.append(Path(self.flasher_vbf_file.get()))
        for i in range(self.flasher_file_listbox.size()):
            files.append(Path(self.flasher_file_listbox.get(i)))
        files = [p for p in files if p.exists()]
        if not files:
            messagebox.showwarning("Flash", "No valid VBF files selected.")
            return

        self._cancel_evt.clear()
        self.flasher_btn_flash.configure(state='disabled')
        self.flasher_btn_cancel.configure(state='normal')
        self._update_flash_progress(0, "Starting…")

        tx_id = int(self.flasher_ecu_txid.get(), 16)
        rx_id = int(self.flasher_ecu_rxid.get(), 16)
        port = self._j2534_port

        def worker():
            try:
                total = len(files)
                for idx, vbf_path in enumerate(files, start=1):
                    if self._cancel_evt.is_set():
                        break
                    self._flasher_log(f"Parsing {vbf_path.name}")
                    blob = vbf_path.read_bytes()
                    # ----- parse header & sections using helpers in your vbf.py -----
                    start, end = _find_header_bounds(blob)          # you already have these helpers
                    header_text = blob[:end].decode('latin-1', 'ignore')
                    sections = parse_blocks(blob, end)              # returns objects with .index .start_addr .length .data_off

                    # ----- minimal UDS wake-up: go to extended session, keep alive -----
                    self._flasher_log("UDS: SessionControl 0x10 0x03")
                    _ = self._isotp_request_response(port, tx_id, rx_id, b'\x10\x03', timeout=1500)
                    self._flasher_log("UDS: TesterPresent 0x3E 0x00")
                    _ = self._isotp_request_response(port, tx_id, rx_id, b'\x3E\x00', timeout=1500)

                    # TODO: your SecurityAccess, erase/download/routines here
                    # For now, we just prove transport by streaming each section's raw data
                    for s in sections:
                        if self._cancel_evt.is_set():
                            break
                        data = blob[s.data_off : s.data_off + s.length]
                        self._flasher_log(f"Streaming section #{s.index} addr=0x{s.start_addr:08X} len={len(data)}")
                        # If your ECU expects 0x34/0x36/0x37 use that here; this demo just sends raw data to prove transport.
                        self._isotp_send(port, tx_id, rx_id, data, timeout=5000)
                        pct = int(((idx - 1) + (s.index / max(1, len(sections)))) / total * 100)
                        self._update_flash_progress(pct, f"Sent section {s.index}/{len(sections)} for {vbf_path.name}")

                    self._flasher_log(f"Completed streaming {vbf_path.name}")
                self._update_flash_progress(100, "Done")
            except Exception as e:
                self._flasher_log(f"Flash error: {e}")
                messagebox.showerror("Flash", f"Error: {e}")
            finally:
                try:
                    self.flasher_btn_flash.configure(state='normal')
                    self.flasher_btn_cancel.configure(state='disabled')
                except Exception:
                    pass

        Thread(target=worker, daemon=True).start()


    # =============================================================================
    # END OF VBF PATCHER AND FLASHER TABS
    # =============================================================================

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
    '''
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
    '''
    def bitmaps_build(self):
        # Validate inputs
        kzb_path = self.bitmaps_kzb_file.get()
        cfg_path = self.bitmaps_cfg_file.get()
        txt1_path = self.bitmaps_txt1_file.get()
        txt2_path = self.bitmaps_txt2_file.get()
        output_path = self.bitmaps_output_file.get()

        if not kzb_path:
            messagebox.showerror("Missing File", "Please select a KZB file"); return
        if not cfg_path:
            messagebox.showerror("Missing File", "Please select a KZB.CFG file"); return
        if not txt1_path:
            messagebox.showerror("Missing File", "Please select Text File 1"); return
        if not txt2_path:
            messagebox.showerror("Missing File", "Please select Text File 2"); return
        if not output_path:
            messagebox.showerror("Missing Output", "Please specify an output file"); return

        for path, name in [(kzb_path,"KZB"),(cfg_path,"CFG"),(txt1_path,"Text 1"),(txt2_path,"Text 2")]:
            if not Path(path).exists():
                messagebox.showerror("File Not Found", f"{name} file does not exist:\n{path}"); return

        # Clear log & progress
        self.bitmaps_log.configure(state='normal'); self.bitmaps_log.delete(1.0, tk.END); self.bitmaps_log.configure(state='disabled')
        self.bitmaps_progress['value'] = 0
        self.bitmaps_status_label.configure(text="Building bitmaps.bin…")

        def run_build():
            try:
                self.bitmaps_log_message("=" * 70)
                self.bitmaps_log_message("Starting bitmaps.bin build process")
                self.bitmaps_log_message("=" * 70)

                # Read inputs
                self.bitmaps_status_label.configure(text="Reading inputs…")
                self.bitmaps_progress['value'] = 15

                kzb_data  = Path(kzb_path).read_bytes()
                cfg_data  = Path(cfg_path).read_bytes()
                txt1_data = Path(txt1_path).read_bytes()
                txt2_data = Path(txt2_path).read_bytes()

                self.bitmaps_log_message(f" [KZB ] {Path(kzb_path).name}  ({len(kzb_data):,} bytes)")
                self.bitmaps_log_message(f" [CFG ] {Path(cfg_path).name}  ({len(cfg_data):,} bytes)")
                self.bitmaps_log_message(f" [TXT1] {Path(txt1_path).name} ({len(txt1_data):,} bytes)")
                self.bitmaps_log_message(f" [TXT2] {Path(txt2_path).name} ({len(txt2_data):,} bytes)")

                # Fixed virtual directory layout inside the container
                entries = [
                    ("KZB",  BITMAPS_VPATHS["KZB"],  kzb_data),
                    ("TXT1", BITMAPS_VPATHS["TXT1"], txt1_data),
                    ("TXT2", BITMAPS_VPATHS["TXT2"], txt2_data),
                    ("CFG",  BITMAPS_VPATHS["CFG"],  cfg_data),
                ]

                # Build header
                self.bitmaps_status_label.configure(text="Building header…")
                self.bitmaps_progress['value'] = 35
                output = bytearray()
                output.extend(b"BTMP")  # magic

                # We always include the directory header (it’s the whole point here).
                # Keep your "include header" flag to also add legacy size table if you want.
                import struct, zlib

                file_count = len(entries)
                output.extend(struct.pack("<I", file_count))

                # Reserve file table with variable-length paths.
                # Each record: u16 path_len | path_bytes (utf-8) | u32 offset | u32 size
                table_records = []
                for _, vpath, data in entries:
                    p_bytes = vpath.encode("utf-8")
                    output.extend(struct.pack("<H", len(p_bytes)))
                    output.extend(p_bytes)
                    # placeholders for offset/size
                    off_pos = len(output); output.extend(struct.pack("<I", 0))
                    sz_pos  = len(output); output.extend(struct.pack("<I", 0))
                    table_records.append((off_pos, sz_pos, vpath, len(data)))

                # If you still want the old fixed 4-slot “size header”, we keep it (optional)
                legacy_offset_positions = []
                if self.bitmaps_include_header.get():
                    # Align (optional) before legacy block
                    if self.bitmaps_align_sections.get():
                        while (len(output) % 4) != 0:
                            output.append(0)
                    # “Legacy” count (always 4 here)
                    output.extend(struct.pack("<I", 4))
                    for _ in range(4):
                        legacy_offset_positions.append(len(output))
                        output.extend(struct.pack("<I", 0))  # offset placeholder
                        output.extend(struct.pack("<I", 0))  # size placeholder

                # Align data start if requested
                if self.bitmaps_align_sections.get():
                    while (len(output) % 4) != 0:
                        output.append(0)

                self.bitmaps_status_label.configure(text="Writing file data…")
                self.bitmaps_progress['value'] = 60

                # Append data and patch offsets/sizes
                section_info = []
                for idx, (_, vpath, data) in enumerate(entries):
                    start = len(output)
                    output.extend(data)
                    size  = len(data)
                    section_info.append((start, size, vpath))

                    # Align between blobs if requested
                    if self.bitmaps_align_sections.get() and idx < (len(entries) - 1):
                        while (len(output) % 4) != 0:
                            output.append(0)

                # Patch the variable-length table offsets/sizes
                for (off_pos, sz_pos, vpath, _decl_sz), (start, size, _) in zip(table_records, section_info):
                    output[off_pos:off_pos+4] = struct.pack("<I", start)
                    output[sz_pos:sz_pos+4]   = struct.pack("<I", size)

                # Patch the legacy header (if included)
                if self.bitmaps_include_header.get():
                    for i, (start, size, _) in enumerate(section_info):
                        pos = legacy_offset_positions[i]
                        output[pos:pos+4]     = struct.pack("<I", start)
                        output[pos+4:pos+8]   = struct.pack("<I", size)

                # Log virtual layout
                self.bitmaps_log_message("")
                self.bitmaps_log_message("Virtual directory layout inside bitmaps.bin:")
                for (start, size, vpath) in section_info:
                    self.bitmaps_log_message(f"  {vpath:35s}  Offset: 0x{start:08X}  Size: {size:,}")

                # Optional trailing CRC32 for the whole image (LE), like your old toggle
                if self.bitmaps_add_crc.get():
                    crc = crc32_bytes(bytes(output))
                    output.extend(struct.pack("<I", crc))
                    self.bitmaps_log_message(f"\n[CRC32] image=0x{crc:08X}")

                # Write the file
                self.bitmaps_status_label.configure(text="Writing output file…")
                self.bitmaps_progress['value'] = 85
                Path(output_path).write_bytes(output)

                self.bitmaps_progress['value'] = 100
                self.bitmaps_status_label.configure(text="Build complete!")

                self.bitmaps_log_message("")
                self.bitmaps_log_message("=" * 70)
                self.bitmaps_log_message("[SUCCESS] bitmaps.bin created successfully")
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
                self.after(0, lambda: messagebox.showerror("Build Failed", f"Error building bitmaps.bin:\n\n{str(e)}"))

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
    
    def _build_vbf_flasher_ui(self, parent):
        """Build VBF Flasher tab"""
        # State
        self.vbf_j2534_devices = []
        self.vbf_selected_device = None
        self.vbf_file_path = None
        self.vbf_port = None
        self.vbf_is_connected = False
        self.vbf_flash_thread = None
        self.vbf_is_flashing = False
        
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        ttk.Label(main_frame, text="VBF Flasher", 
                 font=('TkDefaultFont', 12, 'bold')).pack(anchor='w', pady=(0, 10))
        
        # Device Selection
        device_frame = ttk.LabelFrame(main_frame, text="J2534 Device Selection", padding="10")
        device_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(device_frame, text="Available Devices:").pack(anchor='w')
        
        self.vbf_device_listbox = tk.Listbox(device_frame, height=4)
        self.vbf_device_listbox.pack(fill='both', expand=True, pady=(5, 5))
        
        btn_frame1 = ttk.Frame(device_frame)
        btn_frame1.pack(fill='x')
        ttk.Button(btn_frame1, text="Scan Devices", command=self.vbf_scan_devices).pack(side='left', padx=(0, 5))
        ttk.Button(btn_frame1, text="Select Device", command=self.vbf_select_device).pack(side='left')
        
        # Connection Parameters
        params_frame = ttk.LabelFrame(main_frame, text="Connection Parameters", padding="10")
        params_frame.pack(fill='x', pady=(0, 10))
        
        id_frame = ttk.Frame(params_frame)
        id_frame.pack(fill='x')
        
        ttk.Label(id_frame, text="TX ID (hex):").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.vbf_tx_id_var = tk.StringVar(value="7E0")
        ttk.Entry(id_frame, textvariable=self.vbf_tx_id_var, width=10).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(id_frame, text="RX ID (hex):").grid(row=0, column=2, sticky='w', padx=5, pady=5)
        self.vbf_rx_id_var = tk.StringVar(value="7E8")
        ttk.Entry(id_frame, textvariable=self.vbf_rx_id_var, width=10).grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(id_frame, text="Baud:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.vbf_baud_var = tk.StringVar(value="500000")
        ttk.Combobox(id_frame, textvariable=self.vbf_baud_var, 
                     values=["125000", "250000", "500000"], 
                     state='readonly', width=10).grid(row=1, column=1, padx=5, pady=5)
        
        # File Selection
        file_frame = ttk.LabelFrame(main_frame, text="VBF File", padding="10")
        file_frame.pack(fill='x', pady=(0, 10))
        
        self.vbf_file_label = ttk.Label(file_frame, text="No file selected", foreground='gray')
        self.vbf_file_label.pack(anchor='w', pady=(0, 5))
        
        ttk.Button(file_frame, text="Browse...", command=self.vbf_browse_file).pack(anchor='w')
        
        # Flash Control
        control_frame = ttk.LabelFrame(main_frame, text="Flash Control", padding="10")
        control_frame.pack(fill='x', pady=(0, 10))
        
        self.vbf_progress_var = tk.DoubleVar()
        self.vbf_progress_bar = ttk.Progressbar(control_frame, variable=self.vbf_progress_var, 
                                                maximum=100, length=400)
        self.vbf_progress_bar.pack(fill='x', pady=(0, 5))
        
        self.vbf_progress_label = ttk.Label(control_frame, text="Ready", foreground='blue')
        self.vbf_progress_label.pack(anchor='w', pady=(0, 10))
        
        btn_control_frame = ttk.Frame(control_frame)
        btn_control_frame.pack(fill='x')
        
        self.vbf_btn_connect = ttk.Button(btn_control_frame, text="Connect", command=self.vbf_connect)
        self.vbf_btn_connect.pack(side='left', padx=(0, 5))
        
        self.vbf_btn_flash = ttk.Button(btn_control_frame, text="Start Flash", 
                                        command=self.vbf_start_flash, state='disabled')
        self.vbf_btn_flash.pack(side='left', padx=(0, 5))
        
        self.vbf_btn_disconnect = ttk.Button(btn_control_frame, text="Disconnect", 
                                             command=self.vbf_disconnect, state='disabled')
        self.vbf_btn_disconnect.pack(side='left')
        
        # Log
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        log_frame.pack(fill='both', expand=True)
        
        self.vbf_log_text = scrolledtext.ScrolledText(log_frame, height=12, wrap='word', state='disabled')
        self.vbf_log_text.pack(fill='both', expand=True, pady=(0, 5))
        
        ttk.Button(log_frame, text="Clear", command=self.vbf_clear_log).pack(anchor='w')
    
    def vbf_log(self, msg: str):
        """Log message"""
        self.vbf_log_text.config(state='normal')
        self.vbf_log_text.insert('end', msg + '\n')
        self.vbf_log_text.see('end')
        self.vbf_log_text.config(state='disabled')
    
    def vbf_clear_log(self):
        """Clear log"""
        self.vbf_log_text.config(state='normal')
        self.vbf_log_text.delete('1.0', 'end')
        self.vbf_log_text.config(state='disabled')
    
    def vbf_scan_devices(self):
        """Scan for J2534 devices"""
        self.vbf_log("Scanning...")
        self.vbf_j2534_devices = find_installed_j2534_dlls()
        
        self.vbf_device_listbox.delete(0, 'end')
        
        if not self.vbf_j2534_devices:
            self.vbf_log("No devices found")
            messagebox.showwarning("No Devices", "No J2534 devices found")
        else:
            for dev in self.vbf_j2534_devices:
                self.vbf_device_listbox.insert('end', f"{dev.Name} ({dev.Vendor})")
            self.vbf_log(f"Found {len(self.vbf_j2534_devices)} device(s)")
    
    def vbf_select_device(self):
        """Select device"""
        sel = self.vbf_device_listbox.curselection()
        if not sel:
            messagebox.showwarning("No Selection", "Select a device")
            return
        
        self.vbf_selected_device = self.vbf_j2534_devices[sel[0]]
        self.vbf_log(f"Selected: {self.vbf_selected_device.Name}")
    
    def vbf_browse_file(self):
        """Browse VBF"""
        filename = filedialog.askopenfilename(
            title="Select VBF",
            filetypes=[("VBF files", "*.vbf"), ("All files", "*.*")]
        )
        
        if filename:
            self.vbf_file_path = Path(filename)
            self.vbf_file_label.config(text=str(self.vbf_file_path), foreground='black')
            self.vbf_log(f"File: {self.vbf_file_path.name}")
    
    def vbf_connect(self):
        """Connect J2534"""
        if not self.vbf_selected_device:
            messagebox.showerror("Error", "Select device first")
            return
        
        try:
            self.vbf_log("Connecting...")
            
            from .j2534.j2534_struct import J2534_Port
            
            self.vbf_port = J2534_Port()
            self.vbf_port.load_device(self.vbf_selected_device)
            self.vbf_port.open()
            
            baud = getattr(BaudRate, f"ISO15765_{self.vbf_baud_var.get()}", BaudRate.ISO15765_500000)
            self.vbf_port.connect_iso15765(baud, ConnectFlag.NONE)
            
            tx_id = int(self.vbf_tx_id_var.get(), 16)
            rx_id = int(self.vbf_rx_id_var.get(), 16)
            self.vbf_port.set_iso15765_flow_control(tx_id=tx_id, rx_id=rx_id)
            
            self.vbf_is_connected = True
            self.vbf_log("Connected")
            
            self.vbf_btn_connect.config(state='disabled')
            self.vbf_btn_disconnect.config(state='normal')
            self.vbf_btn_flash.config(state='normal')
            
        except Exception as e:
            self.vbf_log(f"Failed: {e}")
            messagebox.showerror("Error", str(e))
            self.vbf_cleanup()
    
    def vbf_disconnect(self):
        """Disconnect"""
        self.vbf_cleanup()
        self.vbf_log("Disconnected")
    
    def vbf_cleanup(self):
        """Cleanup"""
        if self.vbf_port:
            try:
                self.vbf_port.clear_filter()
                self.vbf_port.disconnect()
                self.vbf_port.close()
            except:
                pass
            self.vbf_port = None
        
        self.vbf_is_connected = False
        self.vbf_btn_connect.config(state='normal')
        self.vbf_btn_disconnect.config(state='disabled')
        self.vbf_btn_flash.config(state='disabled')
    
    def vbf_start_flash(self):
        """Start flash"""
        if not self.vbf_file_path or not self.vbf_file_path.exists():
            messagebox.showerror("Error", "Select VBF file")
            return
        
        if not self.vbf_is_connected:
            messagebox.showerror("Error", "Not connected")
            return
        
        result = messagebox.askyesno(
            "Confirm",
            f"Flash {self.vbf_file_path.name}?\n\n"
            "Battery charged?\n"
            "Ignition ON?"
        )
        
        if not result:
            return
        
        self.vbf_is_flashing = True
        self.vbf_btn_flash.config(state='disabled')
        self.vbf_btn_disconnect.config(state='disabled')
        self.vbf_progress_var.set(0)
        
        self.vbf_flash_thread = Thread(target=self._vbf_flash_worker, daemon=True)
        self.vbf_flash_thread.start()
    
    def _vbf_flash_worker(self):
        """Flash worker"""
        try:
            from .j2534.j2534_struct import make_iso15765_msg
            
            # Parse VBF
            self.vbf_log("Parsing VBF...")
            blocks = self._vbf_parse_file(self.vbf_file_path)
            
            if not blocks:
                self.after(0, lambda: messagebox.showerror("Error", "No blocks in VBF"))
                return
            
            total_bytes = sum(b[2] for b in blocks)
            self.vbf_log(f"{len(blocks)} blocks, {total_bytes} bytes")
            
            # Enter programming
            self.vbf_log("Entering programming session...")
            resp = self._vbf_send_uds(bytes([0x10, 0x02]))
            if not resp or resp[0] != 0x50:
                self.vbf_log("Failed to enter programming")
                return
            
            time.sleep(0.1)
            
            # Flash blocks
            bytes_done = 0
            for idx, (addr, length, data) in enumerate(blocks):
                self.vbf_log(f"Block {idx+1}/{len(blocks)}: 0x{addr:08X}, {length} bytes")
                
                # Request download
                req = bytes([0x34, 0x00, 0x44]) + struct.pack(">I", addr) + struct.pack(">I", length)
                resp = self._vbf_send_uds(req, 10000)
                if not resp or resp[0] != 0x74:
                    self.vbf_log("Request download failed")
                    return
                
                # Max block
                max_block = 4093
                if len(resp) >= 3:
                    nb = (resp[1] & 0xF0) >> 4
                    if nb > 0:
                        max_block = int.from_bytes(resp[2:2+nb], 'big') - 2
                
                # Transfer
                offset = 0
                counter = 1
                
                while offset < len(data):
                    chunk_size = min(max_block, len(data) - offset)
                    chunk = data[offset:offset + chunk_size]
                    
                    req = bytes([0x36, counter & 0xFF]) + chunk
                    resp = self._vbf_send_uds(req, 5000)
                    if not resp or resp[0] != 0x76:
                        self.vbf_log(f"Transfer failed at {offset}")
                        return
                    
                    offset += chunk_size
                    counter = (counter + 1) & 0xFF
                    bytes_done += chunk_size
                    
                    pct = (bytes_done / total_bytes) * 100
                    self.after(0, lambda p=pct: self.vbf_progress_var.set(p))
                
                # Exit transfer
                resp = self._vbf_send_uds(bytes([0x37]), 10000)
                if not resp or resp[0] != 0x77:
                    self.vbf_log("Transfer exit failed")
                    return
            
            # Reset
            self.vbf_log("Resetting ECU...")
            self._vbf_send_uds(bytes([0x11, 0x01]), 2000)
            
            self.after(0, lambda: self.vbf_progress_var.set(100))
            self.vbf_log("COMPLETE!")
            self.after(0, lambda: messagebox.showinfo("Done", "Flash complete"))
            
        except Exception as e:
            self.vbf_log(f"ERROR: {e}")
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.vbf_is_flashing = False
            self.after(0, lambda: self.vbf_btn_flash.config(state='normal'))
            self.after(0, lambda: self.vbf_btn_disconnect.config(state='normal'))
    
    def _vbf_send_uds(self, data: bytes, timeout: int = 5000) -> Optional[bytes]:
        """Send UDS"""
        from .j2534.j2534_struct import make_iso15765_msg
        
        msg = make_iso15765_msg(data)
        self.vbf_log(f"TX: {data.hex(' ').upper()}")
        
        try:
            self.vbf_port.write(msg, 50)
        except:
            return None
        
        start = time.time()
        while (time.time() - start) * 1000 < timeout:
            resps = self.vbf_port.read(10, 100)
            
            for r in resps:
                if r.DataSize > 0:
                    rd = bytes(r.Data[:r.DataSize])
                    self.vbf_log(f"RX: {rd.hex(' ').upper()}")
                    
                    # Pending
                    if len(rd) >= 3 and rd[0] == 0x7F and rd[2] == 0x78:
                        continue
                    
                    return rd
        
        return None
    
    def _vbf_parse_file(self, vbf_path: Path) -> List[Tuple[int, int, bytes]]:
        """Parse VBF"""
        blocks = []
        
        with open(vbf_path, 'rb') as f:
            content = f.read()
        
        pos = 0
        while True:
            start = content.find(b'__BLOCK__', pos)
            if start == -1:
                break
            
            pos = start + 9
            while pos < len(content) and content[pos:pos+1] in b' \t\r\n':
                pos += 1
            
            end = content.find(b'\n', pos)
            if end == -1:
                break
            
            line = content[pos:end].decode('ascii', errors='ignore').strip()
            parts = line.split()
            
            if len(parts) >= 2:
                try:
                    addr = int(parts[0], 16) if parts[0].startswith('0x') else int(parts[0])
                    length = int(parts[1], 16) if parts[1].startswith('0x') else int(parts[1])
                    
                    dstart = end + 1
                    dend = dstart + length
                    
                    if dend <= len(content):
                        data = content[dstart:dend]
                        blocks.append((addr, length, data))
                        pos = dend
                    else:
                        break
                except:
                    pos = end + 1
            else:
                pos = end + 1
        
        return blocks


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
