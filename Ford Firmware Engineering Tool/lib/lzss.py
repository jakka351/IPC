# lzss_port.py
# Faithful Python port of the C++/IDA-style LZSS variant you posted.
# Window = 1024 (10-bit offset), lookahead up to 17 (emit len-2 in 4 bits).
# Bitstream: [flag bit][(if 0) 10-bit pos + 4-bit (len-2)] | [if 1: 8-bit literal]
# Terminator: flag 0, pos=0, then a trailing 0x00 byte (matches your code).

from dataclasses import dataclass

# ---- Helpers to mimic the IDA/hexrays BYTEn/WORDn macros --------------------

def BYTEn(x: int, n: int) -> int:
    return (x >> (n * 8)) & 0xFF

def set_BYTEn(x: int, n: int, val: int) -> int:
    mask = ~(0xFF << (n * 8)) & 0xFFFFFFFF
    return (x & mask) | ((val & 0xFF) << (n * 8))

def LOWORD(x: int) -> int:
    return x & 0xFFFF

def set_LOWORD(x: int, val: int) -> int:
    return (x & 0xFFFF0000) | (val & 0xFFFF)

# BYTE2 == byte index 2, BYTE3 == byte index 3 (0-based)
def BYTE2(x: int) -> int:
    return BYTEn(x, 2)

def set_BYTE2(x: int, val: int) -> int:
    return set_BYTEn(x, 2, val)

def BYTE3(x: int) -> int:
    return BYTEn(x, 3)

def set_BYTE3(x: int, val: int) -> int:
    return set_BYTEn(x, 3, val)

# ---- LZSS data structures ----------------------------------------------------

@dataclass
class TreeNode:
    parent: int = 0
    small_child: int = 0
    large_child: int = 0

class LzssContext:
    __slots__ = (
        "bCompressedData", "out_bit", "out_len", "in_bit",
        "lzss_window", "out_ptr_index", "match_len", "tree"
    )
    def __init__(self):
        # Buffer size mirrors your static 0x500000
        self.bCompressedData = bytearray(0x500000)
        self.out_bit = 0x80     # unsigned 0x80 instead of signed -128
        self.out_len = 0
        self.in_bit = 0x80
        self.lzss_window = bytearray(1024)
        self.out_ptr_index = 0  # index into bCompressedData
        self.match_len = 0
        self.tree = [TreeNode() for _ in range(1025)]  # 0..1024

# ---- Core tree ops (ported 1:1 from your C++ logic) -------------------------

def lzss_init_tree(root_child: int, ctx: LzssContext) -> LzssContext:
    ctx.tree[1024].parent = 0
    ctx.tree[1024].small_child = 0
    ctx.tree[1024].large_child = root_child
    ctx.tree[root_child].parent = 1024
    ctx.tree[root_child].large_child = 0
    ctx.tree[root_child].small_child = 0
    return ctx

def lzss_contract_node(old_node: int, new_node: int, ctx: LzssContext) -> LzssContext:
    ctx.tree[new_node].parent = ctx.tree[old_node].parent
    if ctx.tree[ctx.tree[old_node].parent].large_child == old_node:
        ctx.tree[ctx.tree[old_node].parent].large_child = new_node
    else:
        ctx.tree[ctx.tree[old_node].parent].small_child = new_node
    ctx.tree[old_node].parent = 0
    ctx.tree[old_node].small_child = 0
    ctx.tree[old_node].large_child = 0
    return ctx

def lzss_replace_node(old_node: int, new_node: int, ctx: LzssContext) -> LzssContext:
    parent = ctx.tree[old_node].parent
    if ctx.tree[parent].small_child == old_node:
        ctx.tree[parent].small_child = new_node
    else:
        ctx.tree[parent].large_child = new_node

    # Copy parent/small/large fields from old -> new
    ctx.tree[new_node].parent = ctx.tree[old_node].parent
    ctx.tree[new_node].small_child = ctx.tree[old_node].small_child
    ctx.tree[new_node].large_child = ctx.tree[old_node].large_child

    # Fix children's parent pointers
    sc = ctx.tree[new_node].small_child
    lc = ctx.tree[new_node].large_child
    if sc:
        ctx.tree[sc].parent = new_node
    if lc:
        ctx.tree[lc].parent = new_node

    # Clear old
    ctx.tree[old_node].parent = 0
    ctx.tree[old_node].small_child = 0
    ctx.tree[old_node].large_child = 0
    return ctx

def lzss_find_next_node(node: int, ctx: LzssContext) -> int:
    nxt = ctx.tree[node].small_child
    while ctx.tree[nxt].large_child:
        nxt = ctx.tree[nxt].large_child
    return nxt

def lzss_delete_node(node: int, ctx: LzssContext) -> LzssContext:
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

def lzss_add_node(new_node: int, match_pos_out: list, lzss_window: bytearray, ctx: LzssContext) -> LzssContext:
    """
    new_node: ring index (0..1023)
    match_pos_out: single-element list to emulate pass-by-ref; set to best match position
    Side effect: ctx.match_len updated with best match length (0..17)
    """
    match_done = 0
    if new_node:
        test_node = ctx.tree[1024].large_child
        match_len = 0
        while not match_done:
            test_node_3 = 0
            delta = 0
            # Compare up to 0x10 (16), then special-case > 0x10 (i.e., 17)
            while test_node_3 <= 0x10 and delta == 0:
                a = lzss_window[(new_node + test_node_3) & 0x3FF]
                b = lzss_window[(test_node + test_node_3) & 0x3FF]
                delta = (a - b)
                test_node_3 += 1
            if delta != 0:
                test_node_3 -= 1  # went one past the mismatch

            if test_node_3 >= match_len:
                match_len = test_node_3
                match_pos_out[0] = test_node
                if test_node_3 > 0x10:
                    ctx = lzss_replace_node(test_node, new_node, ctx)
                    ctx.match_len = test_node_3
                    match_done = 1

            if not match_done:
                # choose child based on delta sign
                child_is_small = (delta < 0)
                if child_is_small:
                    child_ref = "small_child"
                else:
                    child_ref = "large_child"

                curr = getattr(ctx.tree[test_node], child_ref)
                if curr == 0:
                    # attach here
                    setattr(ctx.tree[test_node], child_ref, new_node)
                    ctx.tree[new_node].parent = test_node
                    ctx.tree[new_node].large_child = 0
                    ctx.tree[new_node].small_child = 0
                    ctx.match_len = match_len
                    match_done = 1
                test_node = getattr(ctx.tree[test_node], child_ref)
    else:
        ctx.match_len = 0
    return ctx

# ---- Bit output -------------------------------------------------------------

def output_bits(bits: int, num_bits: int, ctx: LzssContext) -> LzssContext:
    bit_value = 1 << (num_bits - 1) if num_bits > 0 else 0
    nb = num_bits
    while nb:
        if ctx.out_bit == 0x80:  # starting a new byte; reset target byte
            ctx.bCompressedData[ctx.out_ptr_index] = 0
        if bits & bit_value:
            ctx.bCompressedData[ctx.out_ptr_index] |= ctx.out_bit

        if ctx.out_bit == 0x01:
            ctx.out_bit = 0x80
            ctx.out_ptr_index += 1
            ctx.out_len += 1
        else:
            ctx.out_bit >>= 1

        bit_value >>= 1
        nb -= 1
    return ctx

# ---- Public entry points ----------------------------------------------------

def _init_ctx() -> LzssContext:
    ctx = LzssContext()
    # mirror your InitLzssContext defaults
    ctx.out_bit = 0x80
    ctx.in_bit = 0x80
    ctx.match_len = 0
    return ctx

def SecurityOK() -> bool:
    # Your code calls this; just return True here.
    return True

def compress_block(uncompressed: bytes) -> tuple[bytes, int]:
    """
    Equivalent to your C export:
      unsigned char* CompressBlock(unsigned char* data, int len, int* out_len)
    Returns (compressed_bytes, out_len)
    """
    ctx = lzss_compress_data(uncompressed)
    # Slice out the used portion; the C code "returns pointer" + size
    return (bytes(ctx.bCompressedData[:ctx.out_len]), ctx.out_len)

def lzss_compress_data(input_buffer: bytes) -> LzssContext:
    input_length = len(input_buffer)
    ctx = _init_ctx()
    if not SecurityOK():
        return ctx

    # Local ring buffer (the C had both ctx.lzss_window and a local one; the algorithm uses the local one)
    lzss_window = bytearray(1024)
    # win_pos is a 32-bit integer abused as:
    #  - LOWORD(win_pos) = current ring index
    #  - BYTE2(win_pos)  = preload/remaining counter
    #  - BYTE3(win_pos)  = inner loop counter
    win_pos = 1  # low word = 1, the rest zero
    repl_cnt = 0
    match_pos = 0  # used as a temp; BYTE2(match_pos) is abused as temp byte in the original
    eos_reached = 0
    in_ptr = 0

    ctx.out_bit = 0x80
    ctx.out_len = 0

    # Clear window and tree
    for i in range(1024):
        lzss_window[i] = 0
    for n in ctx.tree:
        n.parent = 0
        n.small_child = 0
        n.large_child = 0

    # Preload up to 0x10 bytes ahead of win_pos into the ring
    while BYTE2(win_pos) <= 0x10 and not eos_reached:
        if in_ptr < input_length:
            b = input_buffer[in_ptr]
            in_ptr += 1
            idx = (LOWORD(win_pos) + BYTE2(win_pos)) & 0x3FF
            lzss_window[idx] = b
            win_pos = set_BYTE2(win_pos, (BYTE2(win_pos) + 1) & 0xFF)
        else:
            eos_reached = 1

    ctx = lzss_init_tree(LOWORD(win_pos), ctx)

    # Main encode loop — runs while there is preload remaining (BYTE2(win_pos) > 0)
    while BYTE2(win_pos):
        if ctx.match_len > BYTE2(win_pos):
            ctx.match_len = BYTE2(win_pos)

        if ctx.match_len > 1:
            # Encode match: flag 0, 10-bit position, 4-bit (len-2)
            ctx = output_bits(0, 1, ctx)
            ctx = output_bits(LOWORD(match_pos) & 0x3FF, 10, ctx)
            ctx = output_bits((ctx.match_len - 2) & 0xF, 4, ctx)
            repl_cnt = ctx.match_len
        else:
            # Encode literal: flag 1, then byte
            repl_cnt = 1
            literal = lzss_window[LOWORD(win_pos) & 0x3FF]
            ctx = output_bits(1, 1, ctx)
            ctx = output_bits(literal, 8, ctx)

        # Slide window repl_cnt times
        win_pos = set_BYTE3(win_pos, 0)
        while BYTE3(win_pos) < repl_cnt:
            # delete_node((win_pos + 17) & 0x3FF)
            del_idx = (LOWORD(win_pos) + 17) & 0x3FF
            ctx = lzss_delete_node(del_idx, ctx)

            # Load next input byte into the ring at (win_pos + 17)
            if in_ptr < input_length:
                b = input_buffer[in_ptr]
                in_ptr += 1
                lzss_window[del_idx] = b
            else:
                # decrement the preload/remaining counter
                win_pos = set_BYTE2(win_pos, (BYTE2(win_pos) - 1) & 0xFF)

            # advance LOWORD(win_pos)
            win_pos = set_LOWORD(win_pos, (LOWORD(win_pos) + 1) & 0x3FF)

            # Add node if preload still nonzero
            if BYTE2(win_pos):
                # match_pos is "out" param; emulate with 1-element list
                mp = [0]
                ctx = lzss_add_node(LOWORD(win_pos), mp, lzss_window, ctx)
                match_pos = set_LOWORD(match_pos, mp[0] & 0x3FF)  # store 10-bit idx

            # increment BYTE3(win_pos)
            win_pos = set_BYTE3(win_pos, (BYTE3(win_pos) + 1) & 0xFF)

    # Terminator: flag 0 + 10 zero bits, then a zero byte appended
    ctx = output_bits(0, 1, ctx)
    ctx = output_bits(0, 10, ctx)
    # append 0x00 as in your code:
    if ctx.out_ptr_index >= len(ctx.bCompressedData):
        ctx.bCompressedData.extend(b"\x00")
    ctx.bCompressedData[ctx.out_ptr_index] = 0
    ctx.out_ptr_index += 1
    ctx.out_len += 1
    return ctx

# ---- Quick self-test (optional) ---------------------------------------------
if __name__ == "__main__":
    data = b"HELLO HELLO HELLO HELLO!!!\x00\x01\x02" * 8
    comp, n = compress_block(data)
    print("compressed bytes:", n)
