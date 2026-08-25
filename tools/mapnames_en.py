# -*- coding: utf-8 -*-
"""English map names for MAP/MAPNAME.BIN.

Records sit on a fixed 256-byte stride, so there is no pointer table and each
name has a ~255 byte budget. Names are keyed by record index.

Terminology follows the source series where the location comes from one:
Gundam SEED/Destiny, Eureka Seven, Big O, Getter, Mazinger, GaoGaiGar,
Aquarion, Zambot, plus the Z original setting.
"""

MAP_NAMES = {
    0:  "DummyMap by. Construction Team",
    1:  "Lunar Surface - Military Base",
    2:  "Lunar Surface - Wasteland",
    3:  "Space (1)",
    4:  "Space (2)",
    5:  "DummyMap by. Construction Team",
    6:  "Space (4)",
    7:  "Generic City (1)",
    8:  "Generic City (2)",
    9:  "Generic City (3)",
    10: "Half-Ruined City",
    11: "Chiram City",
    12: "Federation Assembly City",
    13: "Ruined City",
    14: "Wasteland (1)",
    15: "Wasteland (2)",
    16: "Wasteland (3)",
    17: "Forest",
    18: "Plains (1)",
    19: "Plains (2)",
    20: "Canyon",
    21: "Coastline",
    22: "Snowy Mountains",
    23: "Siberian Plains (1)",
    24: "Siberian Plains (2)",
    25: "Siberian Plains (3)",
    26: "Siberian Plains (4)",
    27: "Open Sea (1)",
    28: "Open Sea (2)",
    29: "Open Sea (3)",
    30: "Military Base",
    31: "Another Dimension",
    32: "Armory One Exterior",
    33: "Falling Junius Seven (1)",
    34: "Falling Junius Seven (2)",
    35: "Gibraltar Base",
    36: "Lohengrin Gun Battery",
    37: "Heaven's Base",
    38: "Orb Coastline",
    39: "Orb",
    40: "Requiem Relay Station",
    41: "Lunar Requiem",
    42: "Messiah",
    43: "Suruga Bay (1)",
    44: "Suruga Bay (2)",
    45: "Trinity City",
    46: "Orbital Elevator (1)",
    47: "Orbital Elevator (2)",
    48: "Ulugusk",
    49: "Dome Polis",
    50: "Agato Crystal",
    51: "Liman Megalopolis",
    52: "Knox",
    53: "Paradigm City",
    54: "New Saotome Research Institute",
    55: "Photon Power Laboratory (1)",
    56: "Hong Kong City",
    57: "Colony Laser",
    58: "Zonder Epta",
    59: "Bellforest",
    60: "Coralian Cloud",
    61: "Inside the Scub Cave",
    62: "Eureka's Street",
    63: "Antarctica",
    64: "Saint-Germain Castle",
    65: "Goma (1)",
    66: "Goma (2)",
    67: "Skull Moon Base",
    68: "Atlandia",
    69: "Oratorio No.8",
    70: "Vodarl Palace",
    71: "Above the Orbital Elevator",
    72: "Photon Power Laboratory (2)",
    73: "Night Sea",
    74: "Another Dimension (2)",
    75: "DummyMap by. Construction Team",
    76: "DummyMap by. Construction Team",
    77: "DummyMap by. Construction Team",
    78: "DummyMap by. Construction Team",
    79: "DummyMap by. Construction Team",
}

# Records 80..194 are developer placeholder slots: ■NNN-<era>.
ERA = {"現代": "Present", "未来（１）": "Future(1)",
       "未来（２）": "Future(2)", "未来（３）": "Future(3)"}


def build_all(originals):
    """originals: list of the Japanese strings, indexed by record.
    Returns {index: english}."""
    out = dict(MAP_NAMES)
    for i, jp in enumerate(originals):
        if i in out:
            continue
        if jp.startswith("■"):
            # ■０１３−未来（１）  ->  #013-Future(1)
            body = jp[1:]
            num, _, era = body.partition("−")
            digits = "".join(
                chr(ord(c) - 0xFEE0) if "０" <= c <= "９" else c for c in num)
            out[i] = "#%s-%s" % (digits, ERA.get(era, era))
        else:
            out[i] = None   # untranslated -> leave original bytes alone
    return out
