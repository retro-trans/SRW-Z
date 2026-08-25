"""Minimal PINE client to read PCSX2 EE memory, and dump the glyph log buffer.

PINE request:  [u32 total_len][ cmd... ]   cmd = [u8 op][u32 addr]  (read32 op=2)
PINE reply:    [u32 total_len][u8 result][ per-cmd little-endian values ]
Tries TCP 127.0.0.1:<slot> then Windows named pipe \\.\pipe\pcsx2-pine-<slot>.
"""
import sys, socket, struct, time

SLOT = 28011
LOGBUF = 0x00188980          # CAVE+0x510
NENT = 32


class Pine:
    def __init__(self, slot=SLOT):
        self.sock = None; self.pipe = None
        try:
            s = socket.create_connection(("127.0.0.1", slot), timeout=3)
            self.sock = s; self.kind = "tcp:%d" % slot; return
        except OSError:
            pass
        import os
        for name in (r"\\.\pipe\pcsx2-pine-%d" % slot, r"\\.\pipe\pcsx2-pine"):
            try:
                self.pipe = open(name, "r+b", buffering=0)
                self.kind = name; return
            except OSError:
                continue
        raise RuntimeError("could not connect to PINE (tcp or pipe)")

    def _xfer(self, payload):
        msg = struct.pack("<I", 4 + len(payload)) + payload
        if self.sock:
            self.sock.sendall(msg)
            hdr = self._recvn(4); ln = struct.unpack("<I", hdr)[0]
            return hdr + self._recvn(ln - 4)
        else:
            self.pipe.write(msg); self.pipe.flush()
            hdr = self.pipe.read(4); ln = struct.unpack("<I", hdr)[0]
            return hdr + self.pipe.read(ln - 4)

    def _recvn(self, k):
        b = b""
        while len(b) < k:
            c = self.sock.recv(k - len(b))
            if not c: raise RuntimeError("socket closed")
            b += c
        return b

    def read32_batch(self, addrs):
        payload = b"".join(struct.pack("<BI", 2, a) for a in addrs)
        rep = self._xfer(payload)
        res = rep[4]
        if res != 0:
            raise RuntimeError("PINE result code %d" % res)
        body = rep[5:]
        return [struct.unpack("<I", body[i * 4:i * 4 + 4])[0] for i in range(len(addrs))]

    def write32(self, addr, val):
        # PINE MsgWrite32 = opcode 6: [u8 op][u32 addr][u32 val]
        payload = struct.pack("<BII", 6, addr, val)
        rep = self._xfer(payload)
        if rep[4] != 0:
            raise RuntimeError("PINE write result %d" % rep[4])


def main():
    p = Pine()
    print("connected via", p.kind)
    if len(sys.argv) > 1 and sys.argv[1] == "reset":
        p.write32(LOGBUF, 0)
        print("counter reset to 0")
        return
    if len(sys.argv) > 2 and sys.argv[1] == "poke":
        import json
        for va, hx in json.load(open(sys.argv[2])):
            p.write32(va, struct.unpack("<I", bytes.fromhex(hx))[0])
        print("poked", sys.argv[2])
        return
    words = p.read32_batch([LOGBUF] + [LOGBUF + 4 + i * 4 for i in range(NENT * 2)])
    count = words[0]
    print("glyph count (total drawn):", count)
    ents = words[1:]
    print("\nslot  code   destX  srcU   X2    char")
    seen = []
    for i in range(NENT):
        w0 = ents[i * 2]; w1 = ents[i * 2 + 1]
        destx = w0 & 0xFFFF
        s4 = (w0 >> 16) & 0xFFFF
        s6 = w1 & 0xFFFF
        code = (w1 >> 16) & 0xFFFF
        if code == 0 and destx == 0:
            continue
        try:
            ch = struct.pack(">H", code).decode("cp932") if code >= 0x8100 else chr(code & 0x7F)
        except Exception:
            ch = "?"
        seen.append((i, code, destx, s4, s6, ch))
    # order by draw order approx (slot), show
    for i, code, destx, s4, s6, ch in seen:
        print("%3d  0x%04X %5d  %5d  %5d   %s" % (i, code, destx, s4, s6, ch))
    # analysis: consecutive dest-x deltas and s4/s6 deltas
    if len(seen) >= 3:
        print("\nconsecutive deltas (destX, s+4, s+6):")
        srt = sorted(seen, key=lambda e: e[2])   # by destX
        for a, b in zip(srt, srt[1:]):
            print("  '%s'->'%s'  dDestX=%d  dS4=%d  dS6=%d"
                  % (a[5], b[5], b[2] - a[2], b[3] - a[3], b[4] - a[4]))


if __name__ == "__main__":
    main()
