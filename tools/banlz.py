"""Banpresto LZ codec for SRW Z (PS2), ported from the boot ELF.

Decompressor reverse engineered from SLPS_258.87:
    0x1C6C40  header parser (varint fields) -> calls core
    0x1C6D70  core decompressor

Format:
    varint:  v = 0; do { v = (v<<7) | byte } while ((v&1)==0); value = v>>1
             (7 payload bits per byte, bit0 of each byte is the stop flag)

    header:  varint total          decompressed size
             varint flags          bit0..: window = 1 << (((flags>>1)&0xF)+8)
             [varint skipped]      present iff NOT(window>=total AND flags&0x21==1)
                                   AND (flags & 0x40)
             varint (reserved)     always present
    stream:  repeat until out == total:
             token T:   lit  = T & 0xF   (0 -> varint)
                        nref = T >> 4    (0 -> varint)
             lit literal bytes            (must be >= 1; do-while in hardware)
             if out < total:
               nref references:
                 token R: d = R & 0xF
                          if (d&1)==0: do { d = (d<<7)|byte } while ((d&1)==0)
                          dist = d >> 1
                          len  = R >> 4   (0 -> varint), then len += 1
                 copy len bytes from out[-dist-1:], overlapping allowed,
                 clamped to total
"""


class CorruptStream(Exception):
    pass


def _varint(src, i):
    v = 0
    while True:
        v = (v << 7) | src[i]
        i += 1
        if v & 1:
            return v >> 1, i


def parse_header(src, i=0):
    total, i = _varint(src, i)
    if total <= 0:
        return None, None, i
    flags, i = _varint(src, i)
    window = 1 << (((flags >> 1) & 0xF) + 8)
    if not (window >= total and (flags & 0x21) == 1):
        if flags & 0x40:
            _, i = _varint(src, i)          # skipped field
    _, i = _varint(src, i)                  # reserved field
    return total, flags, i


def decompress_stream(src, i, total):
    out = bytearray()
    n = len(src)
    while len(out) < total:
        if i >= n:
            raise CorruptStream("input exhausted at out=%d/%d" % (len(out), total))
        T = src[i]; i += 1
        lit = T & 0xF
        if lit == 0:
            lit, i = _varint(src, i)
        nref = T >> 4
        if nref == 0:
            nref, i = _varint(src, i)
        if lit == 0:
            raise CorruptStream("literal count 0 at 0x%X" % (i - 1))
        out += src[i:i + lit]
        i += lit
        if len(out) >= total:
            break
        for _ in range(nref):
            R = src[i]; i += 1
            d = R & 0xF
            if (d & 1) == 0:
                while True:
                    d = (d << 7) | src[i]
                    i += 1
                    if d & 1:
                        break
            dist = d >> 1
            ln = R >> 4
            if ln == 0:
                ln, i = _varint(src, i)
            ln += 1
            pos = len(out) - dist - 1
            if pos < 0:
                raise CorruptStream("distance %d exceeds output at %d" % (dist, len(out)))
            if len(out) + ln > total:
                ln = total - len(out)
            for k in range(ln):
                out.append(out[pos + k])
            if len(out) >= total:
                break
    return bytes(out), i


def decompress_record(src, i=0):
    """-> (data or None, next_input_offset)"""
    total, flags, i = parse_header(src, i)
    if total is None:
        return None, i
    return decompress_stream(src, i, total)


def _emit_varint(value):
    """Inverse of _varint: 7-bit chunks, each <<1, final chunk |1."""
    chunks = [value & 0x7F]
    value >>= 7
    while value:
        chunks.append(value & 0x7F)
        value >>= 7
    chunks.reverse()
    out = bytearray((c << 1) for c in chunks)
    out[-1] |= 1
    return bytes(out)


def _emit_dist_nibble(dist):
    """Distance = nibble seed + optional continuation bytes.
    Returns (nibble, extra_bytes). Nibble carries the TOP 3 bits (<<1),
    continuation bytes carry 7 bits each."""
    chunks = [dist & 0x7F]
    dist >>= 7
    while dist:
        chunks.append(dist & 0x7F)
        dist >>= 7
    chunks.reverse()
    if len(chunks) == 1 and chunks[0] <= 7:
        return (chunks[0] << 1) | 1, b""
    if chunks[0] > 7:                      # nibble only holds 3 payload bits
        chunks.insert(0, 0)
    nib = chunks[0] << 1                    # continuation: bit0 = 0
    rest = bytearray((c << 1) for c in chunks[1:])
    rest[-1] |= 1
    return nib, bytes(rest)


def compress_stream(data, window):
    """Greedy LZ producing a stream the game's decoder accepts.

    Grammar constraint from the hardware do-while loops: every group is
    >=1 literal then >=1 ref, except the final group which may be
    literals-only (decoder exits once the output is full).
    """
    n = len(data)
    # hash chains on 3-byte seeds
    heads = {}
    tokens = []          # ("lit", bytes) / ("ref", dist, length)
    lit_start = 0
    i = 0
    MIN3 = 3             # refs shorter than 3 cost >= their savings unless dist<=7

    def find_match(pos):
        if pos + 3 > n:
            return None
        best_len = 0
        best_dist = 0
        seed = data[pos:pos + 3]
        cands = heads.get(seed)
        if cands:
            lo = max(0, pos - window)
            for cand in reversed(cands[-768:]):
                if cand < lo:
                    break
                length = 3
                maxl = n - pos
                while length < maxl and data[cand + length] == data[pos + length]:
                    length += 1
                if length > best_len:
                    best_len, best_dist = length, pos - cand - 1
                    if length >= 96:
                        break
        # cheap adjacent-run match (dist<=7 encodes in one byte, len>=2 pays)
        if best_len < 2 and pos >= 1:
            for d in range(0, min(8, pos)):
                cand = pos - d - 1
                length = 0
                maxl = n - pos
                while length < maxl and data[cand + length] == data[pos + length]:
                    length += 1
                if length >= 2 and length > best_len:
                    best_len, best_dist = length, d
        if best_len >= MIN3 or (best_len >= 2 and best_dist <= 7):
            return best_dist, best_len
        return None

    def index_pos(pos):
        if pos + 3 <= n:
            heads.setdefault(data[pos:pos + 3], []).append(pos)

    while i < n:
        m = find_match(i)
        if m:
            # lazy: if skipping one byte yields a longer match, defer
            if i + 1 < n:
                index_pos(i)
                m2 = find_match(i + 1)
                if m2 and m2[1] > m[1] + 1:
                    i += 1
                    m = m2
                else:
                    heads[data[i:i + 3]].pop()   # undo probe index
            if i > lit_start:
                tokens.append(("lit", data[lit_start:i]))
            dist, length = m
            tokens.append(("ref", dist, length))
            for p in range(i, i + length):
                index_pos(p)
            i += length
            lit_start = i
        else:
            index_pos(i)
            i += 1
    if i > lit_start:
        tokens.append(("lit", data[lit_start:i]))

    # pack tokens into (literals, refs) groups
    out = bytearray()
    k = 0
    while k < len(tokens):
        if tokens[k][0] == "lit":
            lits = tokens[k][1]
            k += 1
        else:
            # decoder demands >=1 literal per group: steal one byte back
            # from the previous ref by shortening it -- cannot happen with
            # this tokenizer (refs are always preceded by literals except
            # consecutively), so emit a 1-byte literal from the ref source.
            raise CorruptStream("tokenizer emitted ref at group start")
        refs = []
        while k < len(tokens) and tokens[k][0] == "ref":
            refs.append(tokens[k])
            k += 1
        if not refs and k < len(tokens):
            raise CorruptStream("adjacent literal tokens")
        lit_n = len(lits)
        ref_n = len(refs)
        if ref_n == 0:
            if k < len(tokens):
                raise CorruptStream("literal-only group before end of stream")
            # final group: decoder reads the ref nibble BEFORE the literals
            # but exits on output-full before using it -- any nonzero value
            # avoids a spurious varint read
            ref_field = 1
        else:
            ref_field = 0 if ref_n > 15 else ref_n
        head = bytearray([ref_field << 4 | (0 if lit_n > 15 else lit_n)])
        if lit_n > 15:
            head += _emit_varint(lit_n)
        if ref_n > 15:
            head += _emit_varint(ref_n)
        out += head
        out += lits
        for _, dist, length in refs:
            nib, extra = _emit_dist_nibble(dist)
            ln = length - 1
            if 1 <= ln <= 15:
                out.append((ln << 4) | nib)
                out += extra
            else:
                out.append(nib)
                out += extra
                out += _emit_varint(ln)
    return bytes(out)


def compress_record(data, flags=None):
    """Emit header + stream. flags defaults to a 256KB window profile."""
    if flags is None:
        flags = 0x15
    window = 1 << (((flags >> 1) & 0xF) + 8)
    head = bytearray()
    head += _emit_varint(len(data))
    head += _emit_varint(flags)
    total = len(data)
    if not (window >= total and (flags & 0x21) == 1):
        if flags & 0x40:
            head += _emit_varint(0)
    head += _emit_varint(0)
    return bytes(head) + compress_stream(data, window)


def decompress_all(src):
    """Decompress consecutive records until input is exhausted or invalid."""
    out, i = [], 0
    while i < len(src):
        # skip zero padding between records
        j = i
        while j < len(src) and src[j] == 0:
            j += 1
        if j >= len(src):
            break
        try:
            data, nxt = decompress_record(src, j)
        except (CorruptStream, IndexError) as e:
            out.append(("ERROR@0x%X: %s" % (j, e), None))
            break
        if data is None:
            break
        out.append((j, data))
        i = nxt
    return out


def _ref_cost(dist, length):
    """Encoded byte cost of one ref token."""
    nib, extra = _emit_dist_nibble(dist)
    ln = length - 1
    cost = 1 + len(extra)
    if not (1 <= ln <= 15):
        cost += len(_emit_varint(ln))
    return cost


def compress_stream_optimal(data, window):
    """Cost-based optimal parse (DP right-to-left). Literal cost is 1 byte
    plus a small amortized group overhead; ref cost is exact. The token
    stream is then grouped exactly like the greedy encoder."""
    n = len(data)
    heads = {}
    # index all positions first (matches may reference any earlier pos)
    occ = {}
    for i in range(n - 2):
        occ.setdefault(data[i:i + 3], []).append(i)

    INF = 1 << 60
    dp = [0] * (n + 1)
    choice = [None] * (n + 1)
    LIT = 1.02          # amortized group overhead per literal byte

    for i in range(n - 1, -1, -1):
        best = dp[i + 1] + LIT
        pick = None
        seed = data[i:i + 3]
        cands = occ.get(seed)
        if cands is not None and len(seed) == 3:
            lo = max(0, i - window)
            # candidates strictly before i, newest first, capped
            k = len(cands) - 1
            tried = 0
            while k >= 0 and tried < 320:
                c = cands[k]
                k -= 1
                if c >= i:
                    continue
                if c < lo:
                    break
                tried += 1
                maxl = n - i
                length = 3
                while length < maxl and data[c + length] == data[i + length]:
                    length += 1
                dist = i - c - 1
                # evaluate a few lengths: full and the 16-boundary
                for L in {length, min(length, 16), min(length, 8)}:
                    if L < 3:
                        continue
                    cost = _ref_cost(dist, L) + dp[i + L]
                    if cost < best:
                        best = cost
                        pick = (dist, L)
        # short-range 2-byte refs (dist<=7)
        for dcand in range(0, min(8, i)):
            c = i - dcand - 1
            if data[c] == data[i] and i + 1 < n and data[c + 1] == data[i + 1]:
                L = 2
                maxl = n - i
                while L < maxl and data[c + L] == data[i + L]:
                    L += 1
                for LL in {L, min(L, 16)}:
                    if LL < 2:
                        continue
                    cost = _ref_cost(dcand, LL) + dp[i + LL]
                    if cost < best:
                        best = cost
                        pick = (dcand, LL)
        dp[i] = best
        choice[i] = pick

    # emit tokens by walking choices
    tokens = []
    lit_start = 0
    i = 0
    while i < n:
        pick = choice[i]
        if pick is None:
            i += 1
            continue
        if i > lit_start:
            tokens.append(("lit", data[lit_start:i]))
        dist, L = pick
        tokens.append(("ref", dist, L))
        i += L
        lit_start = i
    if i > lit_start:
        tokens.append(("lit", data[lit_start:i]))

    # grammar fix: stream must START with a literal group
    if tokens and tokens[0][0] == "ref":
        d0, L0 = tokens[0][1], tokens[0][2]
        tokens[0] = ("lit", data[0:1])
        if L0 > 1:
            tokens.insert(1, ("ref", d0, L0 - 1))
        # note: shortened ref keeps validity (copies same source run)
    return _pack_tokens(tokens)


def _pack_tokens(tokens):
    out = bytearray()
    k = 0
    while k < len(tokens):
        if tokens[k][0] != "lit":
            raise CorruptStream("ref at group start")
        lits = tokens[k][1]
        k += 1
        refs = []
        while k < len(tokens) and tokens[k][0] == "ref":
            refs.append(tokens[k])
            k += 1
        lit_n = len(lits)
        ref_n = len(refs)
        if ref_n == 0:
            if k < len(tokens):
                raise CorruptStream("literal-only group mid-stream")
            ref_field = 1
        else:
            ref_field = 0 if ref_n > 15 else ref_n
        head = bytearray([ref_field << 4 | (0 if lit_n > 15 else lit_n)])
        if lit_n > 15:
            head += _emit_varint(lit_n)
        if ref_n > 15:
            head += _emit_varint(ref_n)
        out += head
        out += lits
        for _, dist, length in refs:
            nib, extra = _emit_dist_nibble(dist)
            ln = length - 1
            if 1 <= ln <= 15:
                out.append((ln << 4) | nib)
                out += extra
            else:
                out.append(nib)
                out += extra
                out += _emit_varint(ln)
    return bytes(out)


def compress_record_optimal(data, flags=None):
    if flags is None:
        flags = 0x15
    window = 1 << (((flags >> 1) & 0xF) + 8)
    head = bytearray()
    head += _emit_varint(len(data))
    head += _emit_varint(flags)
    total = len(data)
    if not (window >= total and (flags & 0x21) == 1):
        if flags & 0x40:
            head += _emit_varint(0)
    head += _emit_varint(0)
    body = compress_stream_optimal(data, window)
    greedy = compress_stream(data, window)
    if len(greedy) < len(body):
        body = greedy
    return bytes(head) + body
