from .imports import *

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
