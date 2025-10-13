#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###################################################################
#
#         ____.       __    __           ________  .____________ 
#        |    |____  |  | _|  | _______  \_____  \ |   ____/_   |
#        |    \__  \ |  |/ /  |/ /\__  \   _(__  < |____  \ |   |
#    /\__|    |/ __ \|    <|    <  / __ \_/       \/       \|   |
#    \________(____  /__|_ \__|_ \(____  /______  /______  /|___|
#                  \/     \/    \/     \/       \/       \/      
#
###################################################################
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
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox, simpledialog
#
#                                                                                                                                                                                                 
#                                                   .  ..   ....   ...   ..  ...  ....    ........   .........      .  .    ..      ...........    ....                                               
#                                              ..                                                                                                         .                                              
#                                             :                            ...                                             ....                   ....     ..                                            
#                                            :      ?YY!    :YY7   :Y!  .?J!~!J?.  !YY^   ?J  :JJ.  .JJ. .JJY^    ~YJ?   ~J?~~7J!   ?Y.   .Y?  .7J~^~??.    :                                            
#                                           .      ~5~7Y.   :5JJ?  :5!  ?5:   :5J  7Y?Y^  JY   .YJ .YJ.  .YJ75:  ^57YJ  :5?    75~  ?5:   .YJ  ~5?          :                                            
#                                          ..     .Y? .Y?   :5!.JJ :5!  JY.   .YJ  75:^5^ JY    .J?J7    .YJ 7Y.:5~.YJ  :57    !5!  ?Y:   .YJ   :!??7~.     :                                            
#                                          .      ?57^^J5~  :5! .JJ~Y!  JY.   .YJ  75: ^Y~JJ     :YJ     .YJ  ?YY!  YJ  :57    !5~  ?5:   .YJ       .757    :                                            
#                            ...          .      !5!.:.:J5. :5!   ?557  ^Y?^::?Y^  75^  ^YYY     .5J     .YJ   ~^  .YJ   7Y!::~Y?.  :Y?^::?Y~  ^J7:.:7Y^     .    .   .         ...                      
#                  ..                            ::     .:.  :.    ::.    .:::.    .:.   .:.      :.      :.        :.    .::^:.      .:::.     .::::.                                   ..              
#                 :                                                                                                                                                                       ..             
#                .       !?7    77   !7 .!!77!!^ .!7!7!.  !77    !77. .~7!!7: .!!77!!^ !7  !7   .7~ :7!!!!.        !7!    :?^     :?^     :?^    ~??:    ^?7:   7!   ^7!!77^   77!!!!.     :             
#                :      ~Y!Y~   JJ   ?Y    ?Y.  .Y?   ?Y  JJJ7  ~Y?Y. ?Y.  !5.   ?Y.   7Y. :Y^  !Y. ^Y~           ~J~J^   ^Y~     ^5~     ^5~   :5!7Y.   !5?Y:  YJ  ~5~   ^~.  YY.         :             
#               .      .Y! !Y.  JJ   ?Y    ?Y   .57   !5. J?.Y~:5:!Y. JJ   ^5^   ?Y    7Y.  7J .J~  :J7~~~       .J~ !J.  ^Y~     ^Y~     ^Y~   JJ .Y7   ~5:^5^ J?  75.        JJ!~~:     ..             
#               :      7Y7^!Y?  JJ   ?Y    ?Y   .57   ?5. J? :Y5~ 7Y. JY   ~5:   ?Y    7J.  .Y~~J   :Y^          ?J!^!J7  ^Y~     ^Y~     ^Y~  ~Y?~~JY:  ~5: ^Y!J?  75:   .:   JJ          .             
#              .      ^Y^   ~Y: ^J7~!J^    7J    ~J!~!J^  ??  .:  !Y. :?7~~?!    ?J    7J.   !JJ^   :J7~~~:     ~J: . ^J^ :J7~~~^ :J?~!!^ :Y~ .J7   .JJ  ~Y:  :YY?  .7J!~!J7.  JJ!~~!.     :             
#              :                  ...              ..                   ...                                                                                            ...          .      :             
#               .                                                                                                                                                                         .              
#                :                          .             ..:^^~~!!!!!!!!!!!~~^:..        ..........................................................................................     .               
#                :                                  .:^!!!!~^:...           ..:^~!!!!^:.                                                                                                 :               
#               ..      ..................      .:!7!~:.                            ..^~!!^.      ..................................................................................     :               
#               :                            :!7!^.                 .:^^..                :~7!^.             ...............................................                             :               
#               :                         .!?!:                  .!?YYYYYJ?~.                .:!7^.                                                                                      :               
#               :      .............    ^?7:                   ^?YYYYYYYYYYYY?^                  :!7:   .:....::::::::::::::::::::::::::::..........................................     :               
#               :                     ~J!.     :!!.          :JYYYYYYYYYYYYYYYY?:          ^!:     .~7^                                                                                  :               
#               :      ..........   ~J~.     !YY~           ~YYJYYYYYYYYYYYYYYJYY^          .?Y7.     ^7^  ..::::::::::::....        ...............................................     :               
#               :                 :J7.  .!:.JJ~            ^YYYYJ?!~^::::^~7?YYYYY:           ^?Y~ !.   ~?:    .............:::::.                                                       .               
#                :               !J:   :Y~.7^::           .YYJ!:             .:7YYJ           ..:7^.Y!   .7!                   ....:..                                                 ..                
#                 ..           .J7    :Y? .^77.           7Y7.                  .?5^           ~7:. ^Y~    ^?:                       ....                                             .                  
#                     ..      :Y~  .^ ?J.^JJ~            .Y!  :~!!!^      ^!!!~.  ??            :?J~.?J .~  .?^                         ...                                        ..                    
#                     .      :Y^   J: Y?77:              !?        ::    ^.       .J.             :!??Y. J:  .?^                           .:.                                    ..                     
#                    ..     :Y^   !5..J^.::              J:   .:~~:       .^!~:    !~             ^:.^J: ??   .J:                             ..                                  :                      
#                    :     .Y~    JY: .:J!              :?   ^^^~~^.      .^^^::   .J              7?:. .JJ.   :J.                              .::..!.                ...       ..                      
#                   :      7?    .YY..?Y^               ?:            ^.            J:              ~J?..JJ.    !?   ................................^::...                      :                       
#                   .     :5.  .: 7J~Y!.                J.   :      . ?^ .     ..   ~!               .7J^?7 .   .J:                                       ...::...              ..                       
#                  .      7?   ^? .YJ..7.               J:   :?~.   :!7!^.  .^7!    ?^              .~ :JJ. 7:   !7    ......                                    ...:...          ..                     
#                  :      Y^   ~Y~ ~.:Y7                .J.   :^~!~~!7.~!~~~!^~    ^?                7?..! ^Y^   :J         ......                                     ......        .                   
#                  .     :5.   :YY: :YJ.                 :?.   .  .:^^.:~^.. :.   ^7                 .JJ. .JJ.   .J.              ....                                       ...       .                 
#                 ..     :Y.    !Y? JY:                   .!^   .    .Y!    .    ~^                   :Y? ~Y~     J:  .::::::....      ..        ............                    ..     .                
#                 ..     ^Y    . ~Y7Y^ ~              .:^!7??7       :Y7       .7??7!^:.             ~ ~Y~J~ :    J:   ............:.......   :..... .........................   .::.    :               
#                 ..     :Y.   !! .J? :Y:        :~!?JYYYYYYYYJ.     :5!      .JYYYYYYYYJ?!^.       .Y. J?. ~7   .Y.       .^^............  :.                                ...   :.   .               
#                 ..     .Y:   .5?..: 7Y:       ~YYYYYYYYYYYYYY?      :      .JYJJJJJJJJYYYYJ.      ^Y! ^ .7Y:   :J   :....             .^ .:          ..............           ...  ^    :              
#                  :      J7    ~YY~  JY.      .YYYYYYYYYYYYYYYY^    ~??.    7YJJJJJJJJJJJJJY!      :Y?  ^YY~    77    ....::::::::::....   ^                                    : ..~:   .              
#                  :      ~Y     :J5?.!Y..~    ~YYYYYYYYYYYYYYYYY.   .Y?    ~YYYYYYJJJJJJJJJYJ    ~..Y!.?Y?:    .Y.          ...........    ..                                  :.    :    .             
#                  ..      Y~    . :?J7Y. Y~   JYYYYYYYYYYYYYYYYY7   .Y?   .YYYYYJJYJJJJJJJJJY:  !J :J7J7: .    77                           ^     ...................          :     ^    :             
#                   :      ^Y.   ^7: .^?^ ?Y:  !YYYYYYYYYJYYYYYYYY^  7YY:  JYJYJJYYYJJYJYJJYY7. ^Y7 !?^..^7.   ^J.   .:..........             ^                                ^    ..!.   :             
#                    .      7J    :JJ!:.. :YJ   .!YYYYYYYYYYYYYYYYY..YYY7 7YJJJJJJJYYJYJYYJ!.   JY. ..:7J7    .Y:    :::::::::::::::.....     .:                              :.   :: ^    :             
#                    .       ?7     ~JYJ!: ~Y: !^ .!JYYYYYYYYYYJJYY7!YYYJ!YYYYYYJJJJJJYYJ~  ^! ~Y: :7JY7:    .J^   .~                          :.                            .^       ^   ..             
#                     :       ?7      .^7J?^!J  J?.  ^?YYYYYJJYYJJJYYJYYYYYYYYYJYYYYYY?^  :J? :J^^?J7^.     .J^    ^       ..                   ^                           .^       .:   .              
#                      .       7?     .:...::~~  !Y!.  .~7JYYYYYYYYYYYYYYYYYYYYYYYJ?~.  .7J^ .~^::...:.    :?:    ^                 .            :..........................:        ^.   .              
#                     .         ~J:    .~77!^:::. :!J7:    .:~!7?JJJYYYYYJJJJ?7!^:.  .^77^. .:.:^~77~.    !7.     ..............     .:..............................................::   ..             
#                  ..            .?!      .^!?JJJJ7!7?7!:.    ..:::::::::::::.    .:!??777JJJJJ?7~.     :?^                              ..............................................   .              
#                 .                ~J^       ..       ..:~7?JJ7~:^^~!^:~~~^:~7J?7!^:..  .......       .7!.   .................  ...  ....:::::::::::::::::::::::::::.:.........:....     ..              
#                :      .........    !?^      :~!!77?JYYYJ?~.  :!~:      .^!^..:~?JYYYJ?7!!~~^.     .7!.                                                                      .        ..                
#               ..                    .~?~.      ..:^^:..   .!J~.           :77:   .:^^~^^..      ^7!.         ..                                               ...       ...     .                      
#               .                        :!7^.             .?~                :7~              :!7^        ...                                                                 ..                        
#               .      ..............       ^!7~.                                          .:!!^.     .......      .         .............................                    ..    . .                  
#               .                              :~!!~:.                                 .^~!~:                                                                                             ..             
#                :                                 .:~!!~^:.                    ..:^~!~^.                                                                                                   :            
#                 .        .~7?J?J????????????????7~:.  ..:^~~~~~~~^^^^^^~~~~!~~~^:.   .:~!7!~:     .^   ::.  :.  .^   .:.  .^   ::.  .:   ::   ^   .::   ^   .:.  .^   ::.  .^   :.  .::    :           
#                  :      ~YYYYYYYYYYYYYYYYYYYYYYYYY5YY?7~^:......................:~7?JYYYYYYYY?     ?  ^: !  ^^   ?  :~ !.  ?  ^: 7  .7  ! .7  !.  7 ^^  7. .! !.  ?  .~ !. .7   :~  ! ^^   :           
#                  :      JYJJJYYYJJJJYJ?7!!!!!!!!!!!!!777777?JJ??77777777???JJYYYYYYYJJJJJJJJJY^   .7  .^.^  ^~   7.  ~.~   7. .:.~  .7  ::::  !:  ~.^.  !:  ~.~   7.  ~.~  .7   :~  ~.^.   :           
#                  :      JJJJJJJJYJYY!.                      .!YYYYYYYYYYYYYYYYYJJYYJJJJJJJJJJY^                                                                                            :           
#                  :      JYJJJJYYYYY^  ^JJJJJJJJJJJJJJJJJJJ?:  ~YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY^                                                                                            :           
#                  :      JYJJJYYYYY^  !YYYYYYYYYYYYYYYYYYYYYY^  ^YYYYYYYYJJJJJJJJJJJJJJJJJJYYJY^   .7   ^~   !:  .7   .7  .^.~  :!  :::^ ^.::  7.  ~.~. .7  .~.~  .7  .^.^  ^^  ~.^. ~.~.   :           
#                  :      JYJJJYYYJ:  75YYYYYYYYYYYYYYYYYYYYYYY~  ^YYYYYYYY~               .JYJY^    ?   .!   ~^   ?    7  ^: 7  .7  !. ! ! .~  !:  7 ^:  7  .~ !   7  ~. !  :~  ! ^: ! ~:   :           
#                  :      JYJJY7:.    ..........................   ..:!YYYY^                ?YJY^   .:.  .:   ::  .:.   :.  ...  .:   ..   ..   :.  ...   :.  ...  .:.  ..   .:  ...  ...    :           
#                  :      JJJYJ                                        JYYY^      :!        JYYY^                                                                                            :           
#                  :      JYJYJ   ~??7?7~                    ~7????^   ?YYY^  ^..^..... :^  JYYY^   ^:^  .~   ^:  ::^  .~  .^:. .::.  ^:   ^:  ::^  ^:^  .~  .^:: .::: .::. ::^.  ~.  ::^    ^           
#                  :      JJJYJ   !JJYYJ?     :::::::::^.    ?JJJYY~   ?YYY^  ^.  ^.  . .:  ?YJY^  .~ !. .?   ^~  7 :^  7  ~. 7 7  !  :~   :~  7 ^:.! ~.  7  ~. 7 !. 7 7 .! 7 .~  !.  ! ~.   ^           
#                  :      JJJJJ                                        ?YJY^       ..:7^    ?YJY^   ^.^  .!   ^^  :.:  .!. .::. .::.  ^^   :^  :.^  ^.^  .!  .::: .::: .::. :.^.  ~:  :.^    :           
#                  :      JJJYJ                                        ?YJY^                ?YJY^                                                                                            :           
#                  :      JYJYJ       ^^^^^^^^^^^^^^^^^^^^^^^^^^.      ?YYY!...............:JYJY^   ...  .:   ..  .:.   :   ..   ..   ..   ..  ...  .:   ..   ..   :.  .:.   :   ...  ...    :           
#                  :      JJJYJ      .YYYYYYYYYYYYYYYYYYYYYYYYY5^      JYJJYYYYYYYYYYYYYYYYYJJJY^  .! !. .7  7 .~ 7 ^:  7  ^: !  ^^   ^~  ! :^ ! ^:  ?   :!   ^~   ~^  7 :^  ?  .! ! .! !.   :           
#                  :      JJJJY?~^::^?YJJJJJJJJJYJJYJJJYJJJYJJJY?^^^^^7YJJYYYJYYJYJJYJJJYJJJJJJY^   ~.~  .7  ^.:: ~.^.  7. .^.~  ^~   ^~  ~.^. ~.^.  7.  :!   :!   ~^  ~.^.  7.  ~.~  ~.~    :           
#                  :      JYJJJYYYYYYYJJJJJJJJJJYJJJYYJJJJJJJJJJYYYYYYYJJJJYJYYYYJJJJJJJYJJJJJJY:                                                                                            .           
#                  :      :JYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYJ^                                                                                             .           
#                  ..       :~!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!~:      :!  :::^  7.  ~.~  ~.~ .^.^  ^~  ~.^. .7.  ~.~  :!  :^.^ ::.^  ~:  ^.^. .7   .7  .^.^    .           
#                   ..                                                                              .7  !. !  !: .! ~.:~ ! ~. 7  :~  7 :^  7. .~ !.  7  ~. ! ~. 7  ^^  7 .^  ?    7  ~. 7   ..           
#                     .                                                                             .^   ..   :.  ...  ...  :.   ::  .:.   ^.  ...  .^.  :..  .:.  ::  .::  .^.   ^.  :..   :            
#                       ...                                                                                                                                                               ..             
#                                                                                                                             .  ...   .              .................................         #

#                                                                                                                             
FZBF_SIGN = b'KZBF'
HEADER_SIZE = 0x4C

def file_to_bytes(p: Path) -> bytearray:
    with open(p, 'rb') as f:
        return bytearray(f.read())

def buffer_to_file(out_path: Path, buf: bytes):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(buf)

_WIN_RESERVED = {
    "CON","PRN","AUX","NUL",
    *(f"COM{i}" for i in range(1,10)),
    *(f"LPT{i}" for i in range(1,10)),
}

def _strip_controls(s: str) -> str:
    return ''.join(ch for ch in s if ch != '\x00' and ord(ch) >= 32)

def _fix_reserved(seg: str) -> str:
    seg = seg.rstrip(" .")
    if not seg or seg.upper() in _WIN_RESERVED:
        return f"_{seg or 'unnamed'}_"
    return seg

def sanitize_name(raw: str, fallback: str) -> str:
    s = _strip_controls(raw)
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
        keep = max(1, limit - len(h) - 1 - len(ext) - 1)
        return f"{base[:keep]}_{h}.{ext}"
    keep = max(1, limit - 1 - len(h))
    return f"{seg[:keep]}_{h}"

def fit_path_under(base_dir: Path, rel_path: Path, max_total: int = 240) -> Path:
    parts = [shorten_segment(p, 80) for p in rel_path.parts]
    rel2 = Path(*parts)
    full = base_dir / rel2
    if len(str(full)) <= max_total:
        return rel2

    original_last = parts[-1]
    for limit in (80, 64, 48, 32, 24):
        parts[-1] = shorten_segment(original_last, limit)
        rel2 = Path(*parts)
        if len(str(base_dir / rel2)) <= max_total:
            return rel2

    h = hashlib.md5(original_last.encode('utf-8', 'ignore')).hexdigest()[:16]
    parts[-1] = h
    return Path(*parts)

def escape_path(p: str) -> Path:
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
    def __init__(self, log_callback, progress_callback=None):
        self.log = log_callback
        self.progress_callback = progress_callback
        self.G_extract = True
        self.G_extract_path = Path()
        self.G_idx = 0
        self.G_bin = bytearray()
        self.total_files = 0
        self.processed_files = 0

    def update_progress(self, current: int, total: int, message: str = ""):
        if self.progress_callback:
            self.progress_callback(current, total, message)

    def count_files_in_folder(self, prefix: Path, count: int, depth: int) -> int:
        file_count = 0
        saved_idx = self.G_idx
        
        for i in range(count):
            if self.G_idx + 16 > len(self.G_bin):
                break
            addr = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4
            size = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4
            self.G_idx += 8
            raw_name, self.G_idx, _ = read_be_string(self.G_bin, self.G_idx)
            file_count += 1
        
        self.G_idx = saved_idx
        return file_count

    def count_total_files(self) -> int:
        saved_idx = self.G_idx
        saved_extract = self.G_extract
        self.G_extract = False
        
        try:
            str_sz = be16(self.G_bin[self.G_idx:self.G_idx+2]); self.G_idx += 2
            self.G_idx += str_sz
            self.G_idx = align4_idx(self.G_idx)
            
            self.G_idx += 4 * 4
            count = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4
            
            total = 0
            for _ in range(count):
                total += self.count_folder_files(Path(), 1)
                
        except Exception as e:
            self.log(f"[WARNING] Could not count files: {e}")
            total = 100
        finally:
            self.G_idx = saved_idx
            self.G_extract = saved_extract
            
        return total

    def count_folder_files(self, prefix: Path, depth: int) -> int:
        file_count = 0
        
        if self.G_idx + 4 > len(self.G_bin):
            return 0
            
        size = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4
        raw_name, self.G_idx, _ = read_be_string(self.G_bin, self.G_idx)
        
        if self.G_idx + 4 > len(self.G_bin):
            return 0
            
        count = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4
        last_folder = (count == 0)
        
        if last_folder:
            if self.G_idx + 4 > len(self.G_bin):
                return 0
            elem_count = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4
            file_count += elem_count
            for _ in range(elem_count):
                if self.G_idx + 16 > len(self.G_bin):
                    break
                self.G_idx += 16
                _, self.G_idx, _ = read_be_string(self.G_bin, self.G_idx)
        else:
            for _ in range(count):
                child_files = self.count_folder_files(prefix, depth+1)
                file_count += child_files
            
            if self.G_idx + 4 <= len(self.G_bin):
                next_val = be32(self.G_bin[self.G_idx:self.G_idx+4])
                if next_val < 1000:
                    elem_count2 = next_val; self.G_idx += 4
                    file_count += elem_count2
                    for _ in range(elem_count2):
                        if self.G_idx + 16 > len(self.G_bin):
                            break
                        self.G_idx += 16
                        _, self.G_idx, _ = read_be_string(self.G_bin, self.G_idx)
                        
        return file_count

    def extract_resource(self, resource_path: Path, address: int, size: int):
        start = address + 4
        end = start + size
        
        if end > len(self.G_bin):
            raise RuntimeError(f"Resource bounds exceed file size: {end} > {len(self.G_bin)}")
            
        safe_rel = fit_path_under(self.G_extract_path, resource_path, 240)
        buffer_to_file(self.G_extract_path / safe_rel, self.G_bin[start:end])
        
        self.processed_files += 1
        if self.total_files > 0:
            self.update_progress(self.processed_files, self.total_files, 
                               f"Extracting: {resource_path.name}")

    def parse_elements(self, prefix: Path, count: int, depth: int) -> int:
        for i in range(count):
            if self.G_idx + 16 > len(self.G_bin):
                raise RuntimeError("Unexpected EOF reading element")
                
            addr = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4
            size = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4
            unk1 = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4
            unk2 = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4

            raw_name, self.G_idx, _ = read_be_string(self.G_bin, self.G_idx)
            safe_name = sanitize_name(raw_name, f"elem_{addr:08x}")

            file_path = prefix / escape_path(safe_name)
            self.log("  "*depth + f"[FILE] {safe_name} | addr=0x{addr:08x} size={size}")

            if self.G_extract:
                self.extract_resource(file_path, addr, size)
        return 0

    def parse_folder(self, prefix: Path, depth: int) -> int:
        if self.G_idx + 4 > len(self.G_bin):
            raise RuntimeError("Unexpected EOF reading folder size")
            
        size = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4
        raw_name, self.G_idx, _ = read_be_string(self.G_bin, self.G_idx)
        safe_name = sanitize_name(raw_name, f"folder_{self.G_idx:08x}")

        if self.G_idx + 4 > len(self.G_bin):
            raise RuntimeError("Unexpected EOF reading folder count")
            
        count = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4
        last_folder = (count == 0)
        
        if last_folder:
            if self.G_idx + 4 > len(self.G_bin):
                raise RuntimeError("Unexpected EOF reading element count")
            elem_count = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4
        else:
            elem_count = None

        folder_path = prefix / f"Folder_{safe_name}"
        self.log("  "*depth + f"[DIR ] {safe_name} | children={count}")

        if self.G_extract:
            (self.G_extract_path / escape_path(str(folder_path))).mkdir(parents=True, exist_ok=True)

        if last_folder:
            self.parse_elements(folder_path, elem_count, depth+1)
        else:
            processed_size = 0
            for _ in range(count):
                processed_size += self.parse_folder(folder_path, depth+1)
            if processed_size != size:
                if self.G_idx + 4 > len(self.G_bin):
                    self.log("  "*depth + "[WARN] EOF before mixed folder elements")
                    return size
                elem_count2 = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4
                self.log("  "*depth + f"[MIX ] {elem_count2} additional files")
                self.parse_elements(folder_path, elem_count2, depth+1)

        return size

    def parse_kzb(self, in_file: Path):
        self.G_idx = HEADER_SIZE

        self.total_files = self.count_total_files()
        self.processed_files = 0
        self.log(f"[INFO] Estimated files: {self.total_files}")
        
        self.G_idx = HEADER_SIZE

        str_sz = be16(self.G_bin[self.G_idx:self.G_idx+2]); self.G_idx += 2
        root_name = self.G_bin[self.G_idx:self.G_idx+str_sz].decode('utf-8', errors='ignore')
        self.G_idx += str_sz
        self.G_idx = align4_idx(self.G_idx)

        self.G_idx += 4 * 4
        count = be32(self.G_bin[self.G_idx:self.G_idx+4]); self.G_idx += 4

        self.log(f"[ROOT] {root_name} | top_folders={count}")
        for _ in range(count):
            self.parse_folder(Path(), 1)

        self.log(f"[DONE] Extraction completed at offset 0x{self.G_idx:x}")

    def extract_resource_kzbf(self, resource_path: Path, address: int, size: int):
        if address + size > len(self.G_bin):
            raise RuntimeError(f"KZBF resource bounds exceed file size")
            
        safe_rel = fit_path_under(self.G_extract_path, resource_path, 240)
        path = (self.G_extract_path / safe_rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path = path.with_name('r_' + path.name)
        buffer_to_file(path, self.G_bin[address:address+size])
        
        self.processed_files += 1
        if self.total_files > 0:
            self.update_progress(self.processed_files, self.total_files,
                               f"Extracting: {resource_path.name}")

    def parse_kzbf(self, in_file: Path):
        def need(n: int):
            if self.G_idx + n > len(self.G_bin):
                raise RuntimeError("KZBF: unexpected EOF while parsing")

        need(4)
        _unk = int.from_bytes(self.G_bin[self.G_idx:self.G_idx+4], 'little'); self.G_idx += 4
        need(4)
        str_sz = int.from_bytes(self.G_bin[self.G_idx:self.G_idx+4], 'little'); self.G_idx += 4
        need(str_sz)
        root_name = self.G_bin[self.G_idx:self.G_idx+str_sz].decode('utf-8', errors='ignore')
        self.G_idx += str_sz
        need(4)
        count = int.from_bytes(self.G_bin[self.G_idx:self.G_idx+4], 'little'); self.G_idx += 4

        nodes = []
        for _ in range(count):
            sbytes = []
            while self.G_idx < len(self.G_bin) and self.G_bin[self.G_idx] != 0:
                sbytes.append(self.G_bin[self.G_idx])
                self.G_idx += 1
            if self.G_idx >= len(self.G_bin):
                raise RuntimeError("KZBF: unterminated node string")
            self.G_idx += 1
            node_raw = bytes(sbytes).decode('utf-8', errors='ignore')
            node = sanitize_name(node_raw, f"node_{len(nodes):04d}")
            nodes.append(node)

        self.log(f"[KZBF] Node count: {len(nodes)}")
        self.total_files = len(nodes)
        self.processed_files = 0

        need(4)
        elem_count = int.from_bytes(self.G_bin[self.G_idx:self.G_idx+4], 'little'); self.G_idx += 4
        elems = []
        for _ in range(elem_count):
            need(24)
            idx, unk1, addr, size, unk4, unk5 = struct.unpack('<6I', self.G_bin[self.G_idx:self.G_idx+24])
            self.G_idx += 24
            elems.append((idx, unk1, addr, size))

        for i, node in enumerate(nodes):
            idx, _unk1, addr, size = elems[i]
            self.log(f"[{idx:04d}] 0x{addr:08x} | {size:8d} bytes | {node}")

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

def pack_kzb(extracted_dir: Path, output_file: Path, log_callback, progress_callback=None) -> int:
    if not extracted_dir.exists() or not extracted_dir.is_dir():
        log_callback(f"[ERROR] Input directory not found: {extracted_dir}")
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
    out[0:4] = b'kzbf'

    out.extend(meta)
    while len(out) % 4 != 0:
        out.append(0)

    log_callback(f"[INFO] Writing {len(elemPH)} resources...")
    total_files = len(elemPH)
    
    for i, ph in enumerate(elemPH):
        if progress_callback:
            progress_callback(i + 1, total_files, f"Packing: {ph.element.name}")
        if i % 100 == 0:
            log_callback(f"[PROG] {i}/{total_files}")
        addr_abs = len(out)
        out[HEADER_SIZE + ph.addr_pos : HEADER_SIZE + ph.addr_pos + 4] = put_be32(addr_abs)
        out.extend(b'\x00\x00\x00\x00')
        with open(ph.element.disk_path, 'rb') as f:
            data = f.read()
        out.extend(data)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'wb') as f:
        f.write(out)
    log_callback(f"[DONE] KZB written: {output_file} ({len(out)} bytes)")
    return 0

# ==================== VBF IMPLEMENTATION ====================

class TreeNode:
    def __init__(self):
        self.parent: int = 0
        self.small_child: int = 0
        self.large_child: int = 0

class LZSSContext:
    def __init__(self):
        self.compressed_data = bytearray()
        self.out_bit: int = 128
        self.out_len: int = 0
        self.in_bit: int = 128
        self.lzss_window = bytearray(1024)
        self.match_len: int = 0
        self.tree: List[TreeNode] = [TreeNode() for _ in range(1025)]
        self.current_byte: int = 0

def lzss_init_tree(root_child: int, ctx: LZSSContext) -> LZSSContext:
    ctx.tree[1024].parent = 0
    ctx.tree[1024].small_child = 0
    ctx.tree[1024].large_child = root_child
    ctx.tree[root_child].parent = 1024
    ctx.tree[root_child].large_child = 0
    ctx.tree[root_child].small_child = 0
    return ctx

def lzss_contract_node(old_node: int, new_node: int, ctx: LZSSContext) -> LZSSContext:
    ctx.tree[new_node].parent = ctx.tree[old_node].parent
    if ctx.tree[ctx.tree[old_node].parent].large_child == old_node:
        ctx.tree[ctx.tree[old_node].parent].large_child = new_node
    else:
        ctx.tree[ctx.tree[old_node].parent].small_child = new_node
    ctx.tree[old_node].parent = 0
    ctx.tree[old_node].small_child = 0
    ctx.tree[old_node].large_child = 0
    return ctx

def lzss_replace_node(old_node: int, new_node: int, ctx: LZSSContext) -> LZSSContext:
    if ctx.tree[ctx.tree[old_node].parent].small_child == old_node:
        ctx.tree[ctx.tree[old_node].parent].small_child = new_node
    else:
        ctx.tree[ctx.tree[old_node].parent].large_child = new_node
    
    ctx.tree[new_node].parent = ctx.tree[old_node].parent
    ctx.tree[new_node].small_child = ctx.tree[old_node].small_child
    ctx.tree[new_node].large_child = ctx.tree[old_node].large_child
    
    ctx.tree[ctx.tree[new_node].small_child].parent = new_node
    ctx.tree[ctx.tree[new_node].large_child].parent = new_node
    
    ctx.tree[old_node].parent = 0
    ctx.tree[old_node].small_child = 0
    ctx.tree[old_node].large_child = 0
    return ctx

def lzss_find_next_node(node: int, ctx: LZSSContext) -> int:
    next_node = ctx.tree[node].small_child
    while ctx.tree[next_node].large_child:
        next_node = ctx.tree[next_node].large_child
    return next_node

def lzss_delete_node(node: int, ctx: LZSSContext) -> LZSSContext:
    if ctx.tree[node].large_child:
        if ctx.tree[node].small_child:
            repl_node = lzss_find_next_node(node, ctx)
            ctx = lzss_contract_node(repl_node, ctx.tree[repl_node].small_child, ctx)
            ctx = lzss_replace_node(node, repl_node, ctx)
        else:
            ctx = lzss_contract_node(node, ctx.tree[node].large_child, ctx)
    else:
        ctx = lzss_contract_node(node, ctx.tree[node].small_child, ctx)
    return ctx

def lzss_add_node(new_node: int, lzss_window: bytearray, ctx: LZSSContext) -> Tuple[LZSSContext, int]:
    match_pos = 0
    match_done = False
    
    if new_node == 0:
        ctx.match_len = 0
        return ctx, match_pos
    
    test_node = ctx.tree[1024].large_child
    match_len = 0
    
    while not match_done:
        test_node_3 = 0
        delta = 0
        
        while test_node_3 <= 0x10 and delta == 0:
            idx1 = (new_node + test_node_3) & 0x3FF
            idx2 = (test_node + test_node_3) & 0x3FF
            delta = lzss_window[idx1] - lzss_window[idx2]
            test_node_3 += 1
        
        if delta:
            test_node_3 -= 1
        
        if test_node_3 >= match_len:
            match_len = test_node_3
            match_pos = test_node
            if test_node_3 > 0x10:
                ctx = lzss_replace_node(test_node, new_node, ctx)
                ctx.match_len = test_node_3
                match_done = True
        
        if not match_done:
            if delta < 0:
                child_ptr = ctx.tree[test_node].small_child
                if child_ptr == 0:
                    ctx.tree[test_node].small_child = new_node
                    ctx.tree[new_node].parent = test_node
                    ctx.tree[new_node].large_child = 0
                    ctx.tree[new_node].small_child = 0
                    ctx.match_len = match_len
                    match_done = True
                else:
                    test_node = child_ptr
            else:
                child_ptr = ctx.tree[test_node].large_child
                if child_ptr == 0:
                    ctx.tree[test_node].large_child = new_node
                    ctx.tree[new_node].parent = test_node
                    ctx.tree[new_node].large_child = 0
                    ctx.tree[new_node].small_child = 0
                    ctx.match_len = match_len
                    match_done = True
                else:
                    test_node = child_ptr
    
    return ctx, match_pos

def output_bits(bits: int, num_bits: int, ctx: LZSSContext) -> LZSSContext:
    bit_value = 1 << (num_bits - 1)
    
    for _ in range(num_bits):
        if ctx.out_bit == 128:
            ctx.compressed_data.append(0)
            ctx.current_byte = len(ctx.compressed_data) - 1
            ctx.out_len += 1
        
        if bits & bit_value:
            ctx.compressed_data[ctx.current_byte] |= ctx.out_bit
        
        if ctx.out_bit == 1:
            ctx.out_bit = 128
        else:
            ctx.out_bit >>= 1
        
        bit_value >>= 1
    
    return ctx

def lzss_compress_data(input_buffer: bytes, on_progress: Optional[Callable[[float], None]] = None) -> bytes:
    ctx = LZSSContext()
    input_length = len(input_buffer)
    
    if input_length == 0:
        return bytes()
    
    win_pos = 1
    repl_cnt = 0
    match_pos = 0
    eos_reached = False
    in_ptr = 0
    
    ctx.out_bit = 128
    ctx.out_len = 0
    
    for i in range(1024):
        ctx.lzss_window[i] = 0
    for i in range(1025):
        ctx.tree[i] = TreeNode()
    
    byte2_win = (win_pos >> 16) & 0xFF
    while byte2_win <= 0x10 and not eos_reached:
        if in_ptr < input_length:
            match_pos_hi = input_buffer[in_ptr]
            in_ptr += 1
            
            idx = byte2_win + (win_pos & 0xFFFF)
            if idx < 1024:
                ctx.lzss_window[idx] = match_pos_hi
            byte2_win += 1
        else:
            eos_reached = True
        
        win_pos = (win_pos & 0xFFFF) | (byte2_win << 16)
    
    ctx = lzss_init_tree(win_pos & 0xFFFF, ctx)
    
    byte2_win = (win_pos >> 16) & 0xFF
    total_iterations = 0
    max_iterations = input_length * 2
    
    while byte2_win > 0 and total_iterations < max_iterations:
        total_iterations += 1
        
        if on_progress and total_iterations % 1000 == 0:
            progress = min(0.95, in_ptr / max(1, input_length))
            on_progress(progress)
        
        if ctx.match_len > byte2_win:
            ctx.match_len = byte2_win
        
        if ctx.match_len > 1:
            ctx = output_bits(0, 1, ctx)
            ctx = output_bits(match_pos & 0xFFFF, 0x0A, ctx)
            ctx = output_bits(ctx.match_len - 2, 4, ctx)
            repl_cnt = ctx.match_len
        else:
            repl_cnt = 1
            ctx = output_bits(1, 1, ctx)
            literal_val = ctx.lzss_window[(win_pos & 0xFFFF) & 0x3FF]
            ctx = output_bits(literal_val, 8, ctx)
        
        byte3_win = 0
        while byte3_win < repl_cnt:
            delete_pos = ((win_pos & 0xFFFF) + 17) & 0x3FF
            ctx = lzss_delete_node(delete_pos, ctx)
            
            if in_ptr < input_length:
                match_pos_hi = input_buffer[in_ptr]
                in_ptr += 1
                store_pos = ((win_pos & 0xFFFF) + 17) & 0x3FF
                ctx.lzss_window[store_pos] = match_pos_hi
            else:
                byte2_win -= 1
                win_pos = (win_pos & 0xFFFF) | (byte2_win << 16)
            
            win_pos_lo = ((win_pos & 0xFFFF) + 1) & 0x3FF
            win_pos = win_pos_lo | (win_pos & 0xFFFF0000)
            
            byte2_check = (win_pos >> 16) & 0xFF
            if byte2_check > 0:
                ctx, match_pos = lzss_add_node(win_pos & 0xFFFF, ctx.lzss_window, ctx)
            
            byte3_win += 1
        
        byte2_win = (win_pos >> 16) & 0xFF
    
    ctx = output_bits(0, 1, ctx)
    ctx = output_bits(0, 0x0A, ctx)
    ctx.compressed_data.append(0)
    ctx.out_len += 1
    
    if on_progress:
        on_progress(1.0)
    
    return bytes(ctx.compressed_data[:ctx.out_len])

def crc16_ccitt_ffff(data: memoryview | bytes) -> int:
    CRC16_POLY = 0x1021
    CRC16_INIT = 0xFFFF
    crc = CRC16_INIT
    mv = memoryview(data) if not isinstance(data, memoryview) else data
    for b in mv:
        crc ^= (b << 8) & 0xFFFF
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ CRC16_POLY) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc & 0xFFFF

def crc32_bytes(buf: bytes, init: int = 0) -> int:
    return zlib.crc32(buf, init) & 0xFFFFFFFF

def crc32_file(mm: mmap.mmap) -> int:
    pos = 0
    crc = 0
    blksz = 1 << 20
    size = len(mm)
    while pos < size:
        end = min(size, pos + blksz)
        crc = zlib.crc32(mm[pos:end], crc)
        pos = end
    return crc & 0xFFFFFFFF

@dataclass
class VBFSection:
    index: int
    start_addr: int
    length: int
    data_off: int
    crc_stored: int
    crc_calc: int

@dataclass
class VBFFile:
    path: Path
    header_text: str
    header_end_off: int
    header_fields: dict
    file_crc_from_header: Optional[int]
    sections: List[VBFSection]

def _find_header_bounds(mm: mmap.mmap) -> Tuple[int, int]:
    lower = mm.read().lower()
    mm.seek(0)
    hidx = lower.find(b'header')
    if hidx < 0:
        head = lower[:min(2_000_000, len(mm))]
        if b'vbf_version' in head:
            vpos = head.find(b'vbf_version')
            obr = head.find(b'{', vpos)
            cpos = _match_brace(mm, obr)
            if obr < 0 or cpos < 0:
                raise ValueError("Could not locate 'header { ... }' block.")
            return (vpos, cpos + 1)
        raise ValueError("No 'header' keyword found; not a VBF or header corrupted.")
    obr = lower.find(b'{', hidx)
    if obr < 0:
        raise ValueError("Found 'header' but no opening '{'.")
    cpos = _match_brace(mm, obr)
    if cpos < 0:
        raise ValueError("Header brace matching failed.")
    return (hidx, cpos + 1)

def _match_brace(mm: mmap.mmap, obr: int) -> int:
    i = obr
    depth = 0
    size = len(mm)
    in_str = False
    esc = False
    while i < size:
        c = mm[i]
        i += 1
        if in_str:
            if esc:
                esc = False
                continue
            if c == 0x5C:
                esc = True
                continue
            if c == 0x22:
                in_str = False
            continue
        if c == 0x22:
            in_str = True
            continue
        if c == 0x7B:
            depth += 1
            continue
        if c == 0x7D:
            depth -= 1
            if depth == 0:
                return i - 1
    return -1

def parse_header_fields(header_text: str) -> Tuple[dict, Optional[int]]:
    lines = []
    for line in header_text.splitlines():
        if '//' in line:
            line = line.split('//', 1)[0]
        lines.append(line)
    txt = '\n'.join(lines)
    kv_re = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?);', re.DOTALL)
    fields = {}
    file_crc = None
    for m in kv_re.finditer(txt):
        k = m.group(1)
        v = m.group(2).strip()
        if v.startswith('{') and v.endswith('}'):
            fields[k] = v[1:-1].strip()
            continue
        if v.startswith('"') and v.endswith('"'):
            fields[k] = v[1:-1]
            continue
        vlow = v.lower()
        if vlow.startswith('0x'):
            try:
                num = int(vlow, 16)
                fields[k] = num
                if k.lower() == 'file_checksum':
                    file_crc = num & 0xFFFFFFFF
                continue
            except Exception:
                pass
        try:
            if '.' in v:
                fields[k] = float(v)
            else:
                fields[k] = int(v)
        except Exception:
            fields[k] = v
    return fields, file_crc

def parse_blocks(mm: mmap.mmap, start_off: int, on_progress=None) -> List[VBFSection]:
    total = len(mm)
    p = start_off
    idx = 1
    sections: List[VBFSection] = []
    min_hdr = 4 + 4 + 2
    while p + min_hdr <= total:
        addr = struct.unpack_from('>I', mm, p)[0]
        p += 4
        length = struct.unpack_from('>I', mm, p)[0]
        p += 4
        if length < 0 or p + length + 2 > total:
            break
        data_off = p
        data_mv = memoryview(mm)[data_off:data_off+length]
        p += length
        crc_stored = struct.unpack_from('>H', mm, p)[0]
        p += 2
        crc_calc = crc16_ccitt_ffff(data_mv)
        sections.append(VBFSection(idx, addr, length, data_off, crc_stored, crc_calc))
        idx += 1
        if on_progress and (idx % 64 == 0):
            on_progress(p / total)
    return sections

# ==================== GUI ====================

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
        
        # Worker machinery
        self._worker_thread: Optional[threading.Thread] = None
        self._worker_q: "queue.Queue[tuple]" = queue.Queue()
        self._cancel_evt: threading.Event = threading.Event()
        
        self._build_ui()
        self._tick_ui()

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
        ttk.Label(title_frame, text="v3.2", 
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
        
        # Status bar
        status_frame = ttk.Frame(main_frame, relief=tk.SUNKEN, borderwidth=1)
        status_frame.pack(fill='x', pady=(10, 0))
        self.status_label = ttk.Label(status_frame, text="Status: Ready", anchor='w')
        self.status_label.pack(side='left', fill='x', expand=True, padx=5, pady=2)

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
        
        # Progress section (NEW)
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

    # ==================== KZB COMMANDS ====================
    
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
                
                self.after(0, lambda: messagebox.showinfo(
                    "Extraction Complete", 
                    f"Archive unpacked successfully\n\nOutput: {output_dir}\nFiles: {processor.processed_files}"
                ))
            except Exception as e:
                self.kzb_log_to_widget(self.kzb_unpack_log, "=" * 70)
                self.kzb_log_to_widget(self.kzb_unpack_log, f"[ERROR] {str(e)}")
                self.kzb_log_to_widget(self.kzb_unpack_log, "=" * 70)
                self.kzb_update_progress_ui(
                    self.kzb_unpack_progress,
                    self.kzb_unpack_status_label,
                    self.kzb_unpack_progress_label,
                    self.kzb_unpack_files_label,
                    0, 100, "Error occurred"
                )
                self.after(0, lambda: messagebox.showerror(
                    "Extraction Failed", 
                    f"Error during unpacking:\n\n{str(e)}"
                ))

        threading.Thread(target=run_unpack, daemon=True).start()

    def kzb_pack_file(self):
        input_dir = self.kzb_pack_input.get()
        output_file = self.kzb_pack_output.get()

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
                    
                    self.after(0, lambda: messagebox.showinfo(
                        "Packing Complete", 
                        f"Archive created successfully\n\nOutput: {output_file}"
                    ))
                else:
                    self.after(0, lambda: messagebox.showerror(
                        "Packing Failed", 
                        "Error during packing. Check log for details."
                    ))
            except Exception as e:
                self.kzb_log_to_widget(self.kzb_pack_log, "=" * 70)
                self.kzb_log_to_widget(self.kzb_pack_log, f"[ERROR] {str(e)}")
                self.kzb_log_to_widget(self.kzb_pack_log, "=" * 70)
                self.kzb_update_progress_ui(
                    self.kzb_pack_progress,
                    self.kzb_pack_status_label,
                    self.kzb_pack_progress_label,
                    self.kzb_pack_files_label,
                    0, 100, "Error occurred"
                )
                self.after(0, lambda: messagebox.showerror(
                    "Packing Failed", 
                    f"Error during packing:\n\n{str(e)}"
                ))

        threading.Thread(target=run_pack, daemon=True).start()

    # ==================== VBF COMMANDS ====================
    
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
            ok = "✔" if s.crc_calc == s.crc_stored else "✖"
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
            self._worker_q.put((STATUS_SET, "Cancelling…"))

    def _vbf_worker_build(self, *, raw_header: str, out_path: Path, pack_items: List[Tuple[Path,int,int]],
                      use_lzss: bool, do_crc: bool, crc_scope: str):
        try:
            self._worker_q.put((STATUS_SET, "Building VBF…"))
            
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
                    self._worker_q.put((STATUS_SET, "Compressing with LZSS…"))
                    
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
                    self._worker_q.put((STATUS_SET, "Writing payload (no compression)…"))
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

    # ==================== UI UPDATE MACHINERY ====================
    
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
                    pass  # Handle progress for VBF build if needed
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
            "Ford Firmware Engineering Tool v3.2\n\n"
            "VBF Tools: VBF unpacker/packer with Python LZSS\n"
            "KZB Tools: Archive extraction and packing\n"
            "TAR Archive Builder: Create TAR archives\n\n"
            "Bitmaps Builder: Custom binary file builder\n"
            "By Jakka351\n"
            "github.com/jakka351"
        )


# ==================== MAIN ====================

def main():
    app = CombinedEngineeringTool()
    app.mainloop()

if __name__ == '__main__':
    main()
