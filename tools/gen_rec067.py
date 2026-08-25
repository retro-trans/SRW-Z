# -*- coding: utf-8 -*-
"""Record 67 - Chiram scene (shared w/ rec096, Rand route) + Minerva Freedom talk."""
import importlib.util
import json
WORK = r'E:\Projects\SRW Z\_work'


def bl(x):
    return len(x.encode('cp932'))


# Reuse rows 15-38 from rec096 (identical Chiram President/Asakim scene).
spec = importlib.util.spec_from_file_location("r96", "rec096_en.py")
m96 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m96)
T = {k: v for k, v in m96.T.items() if 15 <= k <= 38}

T.update({
39: 'Rand\n"Damn! Were we a\nstep too late!?"',
40: 'Rand\n"This is bad, $n.. We\'re\nbeing made to dance to\nthat guy\'s scenario."',
41: 'Athena\n"What\'s going on, repairman!\nWho is that man!?"',
42: 'Rand\n"The details\'ll have to\nwait! I\'m going after him!"',
43: 'Athena\n"H-hey!"',
44: 'Rand\n"So long! Take care!"',
45: 'Athena\n"Ngh..! Who the hell\nis that man!"',
46: 'Olson\n"Athena.. I\'m going too."',
47: 'Athena\n"Huh.."',
48: 'Olson\n"With the spacetime\ndevice destroyed, Plan D\nhas all but failed."',
49: 'Olson\n"If so, the brass will\nagain plan spacetime\nrepair via the Singularity\nand use me and Kei."',
50: 'Athena\n"Then take Kei\nKatsuragi and secure\nChiram\'s survival.."',
51: 'Olson\n"..I no longer know\nif that is right."',
52: 'Athena\n"Uncle.."',
53: 'Olson\n"So I\'ll go to see Kei.\nAnd think once more\nabout what I ought\nto do."',
54: 'Athena\n"Please wait, Uncle!\nThen I\'ll come with\nyou too!"',
55: 'Olson\n"No. You stay in Chiram\nand gather information."',
56: 'Olson\n"Asakim Dowin, whom that\nman Rand pursues.. And\nthe New Fed\'s turmoil.."',
57: 'Olson\n"Things will keep moving.\nI\'m counting on you,\nAthena."',
58: 'Athena\n"Uncle.. I pray for\nyour safety.."',
60: '\u3000\n\u3000\u3000\u3000\u3000\u301cMinerva, Shin & Rey\'s Room\u301c',
61: 'Athrun\n"Coming in, Shin."',
62: 'Shin\n"......."',
63: 'Athrun\n"Holed up in your room\nall this time - what\nare you doing?"',
64: 'Kamille\n"A simulation for\nbeating the Freedom."',
65: 'Athrun\n"What..?"',
66: 'Shin\n"Damn! No matter how\noften I try, it evades\nbefore my attack\neven lands!"',
67: '$n\n"That\'s not all. It\ncounters the instant it\nevades, leaving us no\ntime to recover.."',
68: 'Kamille\n"And its attacks are\nflawlessly precise,\nsurely stripping away\nour combat power."',
69: '$n\n"In a long-range shooting\nmatch, you could say\nthere\'s no opening at all."',
70: 'Rey\n"Its thruster control is\nsuperb too. It throws\nthe unit around at will."',
71: 'Shin\n"The Freedom outpowers\nthe Impulse. And to\nhandle it this well.."',
72: 'Athrun\n"A combat sim against the\nFreedom.. Just what\non earth for?"',
73: 'Shin\n"Because it\'s strong."',
74: 'Athrun\n"!"',
75: 'Shin\n"The Freedom\'s pilot may\nwell be the strongest of\nfoes. He even brought\ndown that Destroy."',
76: 'Shin\n"So I think training\nagainst it is a\ngood thing."',
77: 'Athrun\n"..!"',
78: 'Shin\n"If something happens, we\nneed someone who can take\nit down, right? The guy\'s\na total unknown."',
79: 'Athrun\n"Shin!"',
80: 'Kamille\n"I think what Shin\nsays is sound."',
81: '$n\n"As long as the Freedom\nstands in our way, the\nday we fight it head-on\nwill come."',
82: 'Athrun\n"Kamille.. $n.."',
83: 'Rey\n"The Freedom is strong.\nAnd whatever its aims,\nit is not of our army."',
84: 'Rey\n"What $n describes\nis exactly what we\nshould anticipate."',
85: 'Athrun\n"......."',
86: 'Rey\n"Even if it is someone\nyou once fought\nalongside.."',
87: 'Athrun\n"But Kira is not\nan enemy!"',
88: 'Rey\n"How can you say\nthat so surely?"',
89: 'Rey\n"Heine was slain because\nof it, and you yourself\nwere shot down by it,\nweren\'t you?"',
90: 'Rey\n"Combat calls are for the\nbrass, but I can\'t say\nfor sure it\'s not\nan enemy."',
91: 'Rey\n"So I believe we should\nprepare for it all\nthe same."',
92: '$n\n"Captain Athrun.. if you\nwould, might we have\nsome advice?"',
93: 'Shin\n"Never mind, $n. A record\nof losses is no help\nas reference."',
94: 'Athrun\n"What!?"',
95: 'Rey\n"Sorry, Athrun. I\'ll\nhave a word with Shin\nmyself."',
96: 'Athrun\n"Ngh..!"',
97: 'Shin\n"..He left, huh.."',
98: '$n\n"..Shin.. it may be none\nof my business, but let\nme say just this.."',
99: '$n\n"Just don\'t fight that\nFreedom out of hatred."',
100: 'Shin\n"$n.."',
101: 'Kamille\n"What we must do isn\'t\navenge Stella.."',
102: 'Kamille\n"It\'s to strike those who\nspread the fighting,\nand end this war."',
103: 'Shin\n"..I know, Kamille..\nI know that, so.. I.."',
104: 'Kamille\n"I believe in you, Shin.\nSo next time the Freedom\nappears, I\'ll entrust\nit all to you."',
105: 'Kamille\n"I\'m starting to see, if\nfaintly, a way to bring\nit down too."',
106: 'Shin\n"Really, Kamille!?"',
107: 'Kamille\n"Yeah.. For it, you\'ll\nneed to draw out 120%\nof the Impulse\'s power."',
108: 'Shin\n"120% of the Impulse\'s\npower.."',
})

T.update({
63: 'Athrun\n"Holed up in here all\nthis time - what\nare you doing?"',
68: 'Kamille\n"And its attacks are\nperfectly precise,\nsteadily draining\nour power."',
81: '$n\n"While the Freedom\nblocks our way, the day\nwe fight it head-on\nwill come."',
90: 'Rey\n"Combat calls are the\nbrass\'s, but I can\'t\nsay it\'s no enemy."',
93: 'Shin\n"Never mind, $n. A\nrecord of losses is\nno reference."',
})

rows = json.load(open(WORK + r'\analysis\rec067_work.json', encoding='utf-8'))
bud = {r['i']: r['budget'] for r in rows}
need = set(bud)
miss = need - set(T)
extra = set(T) - need
over = [(i, bl(T[i]), bud[i]) for i in T if i in bud and bl(T[i]) > bud[i]]
print("rec067: %d/%d rows | missing %s | extra %s | over %s" % (
    len(T), len(need), sorted(miss), sorted(extra), over))
if not miss and not extra and not over:
    lines = ["# -*- coding: utf-8 -*-", '"""Stage record 67 dialogue."""', "", "T = {"]
    for k in sorted(T):
        lines.append("    %d: %r," % (k, T[k]))
    lines.append("}")
    open("rec067_en.py", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("  WRITTEN")
