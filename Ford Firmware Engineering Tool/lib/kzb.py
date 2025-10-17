from .imports import *

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
