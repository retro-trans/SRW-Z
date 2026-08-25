# -*- coding: utf-8 -*-
"""Fix pass: forecast/char-select overlaps + control-code mode-select strings.

The mode/scenario-select strings carry engine CONTROL BYTES (ops 0x31-0x35
with params: color/position) before and inside the text. Entries here are
pre-encoded bytes: original control prefix preserved verbatim, Japanese tail
replaced with menu-encoded English. apply_elf writes bytes values raw.
"""
from patch import encode


def raw(prefix_hex, text):
    return bytes.fromhex(prefix_hex) + encode(text, "menu")


BATCH = {
    # --- character select: fixed layout, JP-width fields (overlap fix) ---
    0x347A60: "Pick a hero.",
    0x347A88: "：Male",
    0x347A98: "：Female",
    # --- battle forecast: fixed layout (overlap fix) ---
    0x342580: "ATK",
    0x342818: "Begin",
    0x342828: "Orders",
    0x342838: "Support",
    # --- scenario / new-game-plus select (control-code strings) ---
    0x33BAC8: raw("3102", "：Back"),
    0x33BAE2: raw("3211341133093509", "・Normal replay"),
    0x33BB00: raw("310E", "・No upgrades/training/part buys"),
    0x33BB50: "・Enemies upgraded/always HARD",
    0x33BB90: raw("310D3212341233093509", "Choose a mode to play."),
    0x33BBC0: raw("3210341033093509", "・Carries over all pilots'\n kill counts."),
    0x33BC10: "・Carries over funds, BS\n and PP.",
    0x33BC50: "＜2nd: 50%  3rd: 75%\n 4th+: 100%＞",
    0x33BCA0: raw("310E", "＜Clear both heroes to unlock＞"),
    0x33BCD0: raw("310E", "・Upgrades go to level 15"),
    0x33BD00: raw("310E", "・Start with every upgrade part"),
    0x33BD40: raw("31023210341033083508", "：OK"),
    0x33BD58: "：Back",
    0x33BD62: raw("3212341233093509", "Play the main game."),
    0x33BD90: raw("310E3212341233093509", "Learn the basics. One stage."),
    0x33BDC0: raw("310C3210341033083508", "Choose a scenario to play."),
}
