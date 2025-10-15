
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
##################################################################
#
#         ____.       __    __           ________  .____________ 
#        |    |____  |  | _|  | _______  \_____  \ |   ____/_   |
#        |    \__  \ |  |/ /  |/ /\__  \   _(__  < |____  \ |   |
#    /\__|    |/ __ \|    <|    <  / __ \_/       \/       \|   |
#    \________(____  /__|_ \__|_ \(____  /______  /______  /|___|
#                  \/     \/    \/     \/       \/       \/      
#
##################################################################
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
