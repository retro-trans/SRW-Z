# -*- coding: utf-8 -*-
"""Re-wrap the recovered in-battle/event dialogue (missing_dlg_en*.py) to the
message-box width, same rules as reflow_dialogue.py (37 chars, 3 lines).

These 255 lines were hand-wrapped at ~30 chars, so they read fine but waste half
the box. Re-wrapping only removes newlines, so no line can outgrow its slot -
still asserted per row against the byte count it already had.

Usage: reflow_missing.py [--apply]
"""
import io, os, sys
import importlib.util as u

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import reflow_dialogue as R


def bl(s):
    return len(s.encode("cp932", "replace"))


def load(name, var):
    spec = u.spec_from_file_location(name, os.path.join(TOOLS, name + ".py"))
    m = u.module_from_spec(spec); spec.loader.exec_module(m)
    return getattr(m, var)


def write(name, var, doc, d):
    lines = ["# -*- coding: utf-8 -*-", '"""%s"""' % doc, "", "%s = {" % var]
    for k in sorted(d):
        lines.append("%r: %r," % (k, d[k]))
    lines.append("}")
    io.open(os.path.join(TOOLS, name + ".py"), "w", encoding="utf-8").write(
        "\n".join(lines) + "\n")


def main():
    apply = "--apply" in sys.argv
    total = changed = 0
    for name, var, doc in (
        ("missing_dlg_en", "MISSING_EN",
         "English for in-battle/event dialogue the original extraction missed, "
         "keyed \"recNNN:offset\" (re-wrapped to box width)."),
        ("missing_dlg_en_b", "MISSING_EN_B",
         "Second half of the missing in-battle/event dialogue (re-wrapped)."),
    ):
        d = dict(load(name, var))
        for k, t in list(d.items()):
            total += 1
            new = R.reflow(t)
            if new is None or new == t:
                continue
            if bl(new) > bl(t):          # can only shrink; never risk the slot
                continue
            d[k] = new
            changed += 1
        if apply:
            write(name, var, doc, d)
    print("lines: %d | re-wrapped: %d" % (total, changed))
    print("APPLIED" if apply else "(dry run - pass --apply to write)")


if __name__ == "__main__":
    main()
