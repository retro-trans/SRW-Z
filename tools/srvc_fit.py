# -*- coding: utf-8 -*-
"""Fit a battle-caption translation into its ORIGINAL byte budget.

WHY THIS EXISTS (2026-08-21, found from a Tannhauser screenshot)
    Scripted attack sequences - the multi-line exchanges a weapon plays, e.g.
    Talia "This ship now begins attack!" / Arthur "Roger! All, battle
    stations!" - are fetched from SRVC.BIN **by byte offset**, not by index.
    So if ANY string in a block is longer than the Japanese one it replaced,
    every offset after it inside that block slides, and the sequence renders
    the wrong line, the same line twice, "..." , or a line missing its opening
    quote (a mid-string read). All four were visible in the Minerva/Tannhauser
    sequence.

    srvc_apply already pads SHORT translations back up to the original length;
    what was missing is the other half of the invariant:

        every string must be EXACTLY its original byte length - never longer.

    276,001 of 277,545 slots already satisfied it; 1,544 did not (714 distinct
    lines, 15,294 bytes of overflow), and those 1,544 were corrupting every
    sequence that followed them in their block.

The tiers below shorten text without changing meaning where possible, and only
clip as a last resort. Anything that reaches the clip tier is reported so it
can be rewritten by hand later - see analysis/srvc_fitted.json.
"""
import re

NL = chr(92) + "n"                       # the literal backslash-n line break


def ellipsis(u):
    """"..." costs SIX bytes; the Japanese ellipsis costs two.

    In menu mode the reader treats 0x2E-0x3D as control codes, so every '.'
    must ship as its fullwidth form (2 bytes) - three of them is 6 bytes for
    one pause. U+2026 is one cp932 character (0x8163), is what the Japanese
    script itself uses, and renders better than three wide dots.
    """
    return re.sub(r"(?:\.|．|…){2,}", "…", u)


def tidy(u):
    """Whitespace and punctuation that costs bytes but carries no meaning."""
    u = re.sub(r"[ \t]{2,}", " ", u)
    u = re.sub(r" +([,.!?;:])", r"\1", u)
    u = re.sub(r"\.{4,}", "...", u)
    u = re.sub(r" +" + re.escape(NL), NL, u)
    u = re.sub(re.escape(NL) + r" +", NL, u)
    return u.strip()


CONTRACTIONS = [
    (r"\bcannot\b", "can't"), (r"\bdo not\b", "don't"),
    (r"\bdoes not\b", "doesn't"), (r"\bdid not\b", "didn't"),
    (r"\bwill not\b", "won't"), (r"\bis not\b", "isn't"),
    (r"\bare not\b", "aren't"), (r"\bwas not\b", "wasn't"),
    (r"\bhave not\b", "haven't"), (r"\bhas not\b", "hasn't"),
    (r"\bcould not\b", "couldn't"), (r"\bwould not\b", "wouldn't"),
    (r"\bshould not\b", "shouldn't"), (r"\bI am\b", "I'm"),
    (r"\bI will\b", "I'll"), (r"\bI have\b", "I've"),
    (r"\byou are\b", "you're"), (r"\byou will\b", "you'll"),
    (r"\bwe are\b", "we're"), (r"\bwe will\b", "we'll"),
    (r"\bthey are\b", "they're"), (r"\bit is\b", "it's"),
    (r"\bthat is\b", "that's"), (r"\bthere is\b", "there's"),
    (r"\blet us\b", "let's"),
]


def contract(u):
    for pat, rep in CONTRACTIONS:
        u = re.sub(pat, rep, u)
        u = re.sub(pat.replace(r"\b", "", 1).capitalize(), rep.capitalize(), u)
    return u


def clip(u, budget, enc):
    """Last resort: drop whole words from the end until it fits.

    Never cuts inside the NL marker and never leaves a dangling separator.
    """
    while u and len(enc(u)) > budget:
        cut = max(u.rfind(" "), u.rfind(NL))
        if cut <= 0:
            u = u[:-1]
        else:
            u = u[:cut]
        u = u.rstrip(" ,;:-")
        if u.endswith(NL):
            u = u[:-len(NL)].rstrip()
    return u


def fit(text, budget, encode_fn):
    """Return (fitted_text, tier) with len(encode_fn(fitted_text)) <= budget.

    tier: 0 already fit | 1 ellipsis | 2 tidy | 3 contractions | 4 CLIPPED
    """
    for tier, step in enumerate((lambda u: u, ellipsis, tidy, contract)):
        text = step(text)
        if len(encode_fn(text)) <= budget:
            return text, tier
    return clip(text, budget, encode_fn), 4
