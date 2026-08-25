"""Extract the opening scenario text of STAGE.BIN as cleanly as possible.

Marks every non-Shift-JIS byte as <XX> so the boundary between real prose and
surrounding bytecode is visible, instead of being silently glued together.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sjisscan import is_lead, is_trail

data = open(sys.argv[1], "rb").read()
start = int(sys.argv[2], 16)
length = int(sys.argv[3], 16)

chunk = data[start:start + length]
out = []
i = 0
run_jp = 0
while i < len(chunk):
    if i + 1 < len(chunk) and is_lead(chunk[i]) and is_trail(chunk[i + 1]):
        try:
            out.append(chunk[i:i + 2].decode("shift_jis"))
            run_jp += 1
        except UnicodeDecodeError:
            out.append("<%02X%02X>" % (chunk[i], chunk[i + 1]))
        i += 2
    elif chunk[i] == 0x0A:
        out.append("\n")
        i += 1
    elif 0x20 <= chunk[i] < 0x7F:
        out.append(chr(chunk[i]))
        i += 1
    else:
        out.append("<%02X>" % chunk[i])
        i += 1

text = "".join(out)
print("region 0x%X .. 0x%X   (%d Japanese chars)" % (start, start + length, run_jp))
print("=" * 72)
print(text)
