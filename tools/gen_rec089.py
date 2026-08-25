# -*- coding: utf-8 -*-
"""Record 89 - Overdevil scene (shared with rec094) + Gainer/Renton Wheel gift."""
import importlib.util
import json
WORK = r'E:\Projects\SRW Z\_work'


def bl(x):
    return len(x.encode('cp932'))


# Reuse rows 6-52 from rec094 (identical Overdevil-awakening scene).
spec = importlib.util.spec_from_file_location("r94", "rec094_en.py")
m94 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m94)

T = {k: v for k, v in m94.T.items() if 6 <= k <= 52}

# Second half: Eureka Seven / King Gainer bazaar-gift scene (rec089-only).
T.update({
54: '"Eureka Seven"',
55: 'A balance-control part fitted to the underside of a lift board. '
    'The larger it is, the slower the speed, but the easier it is to land tricks.\n'
    'Besides the wheel, many things define a lift board\'s character - '
    'its length and form, the shape of the trapar intake that catches '
    'trapar waves, and more.',
57: 'Witz\n"What are you doing, Gainer!\nGet back to the Iron\nGear, quick!"',
58: 'Gainer\n"Hold on! This market..\nthey\'re selling tons of\nlift boards here!"',
59: 'Bello\n"You.. The world\'s in\ncrisis and you\'re off\nshopping carefree?"',
60: 'Gainer\n"But.. Renton just came\nback, so I thought I\'d\nget him some kind\nof gift.."',
61: 'Roabie\n"Even so, you\'d sell that\nautographed Lacus Clyne\ndisc for it? What\na waste.."',
62: 'Gainer\n"I don\'t need it anymore.\n..And Renton.. seems he\'s\nbeen through something\npainful.."',
63: 'Garrod\n"That guy.. seems he lived\nwith that Charles and Ray\nfor a little while.."',
64: 'Roabie\n"Rough.. Even if set up\nfor it, to end up\nfighting them.."',
65: 'Bello\n"Got it, big bro Gainer.\nIf it\'s to comfort your\nlittle bro, that\'s\nanother story."',
66: 'Gainer\n"Bello.."',
67: 'Garrod\n"But hurry! We don\'t\nhave much time!"',
68: 'Gainer\n"Yeah..!"',
69: 'Gainer\n"..Renton, if you like,\nuse these."',
70: 'Renton\n"So many <Wheels>..\nWhere did you get\nall these!?"',
71: 'Moondoggie\n"Amazing, these.. Some\nrare ones in here too."',
72: 'Gainer\n"I came into some cash,\nso I bought them at\nrandom. I don\'t really\nget lift boards.."',
73: 'Renton\n"..So a real border\nfinds it stylish to fit\nno wheels at all, huh.."',
74: 'Gainer\n"Huh.."',
75: 'Renton\n"Words from someone I\nknew. The one who\ntaught me all kinds\nof things.."',
76: 'Renton\n"That person also\nsaid this."',
77: 'Renton\n"Trends and others\' eyes\ndon\'t matter.. If it\'s\nfun, that\'s enough..\nThat\'s what lifting is.."',
78: 'Garrod\n"I see.. Sounds just\nlike that old man.."',
79: 'Gainer\n"Sorry, Renton.. For..\nmaking you remember.."',
80: 'Renton\n"It\'s fine, big bro Gainer.\nI have no intention of\never forgetting\nthose people.."',
81: 'Gainer\n"Renton.."',
82: 'Renton\n"Thank you, big bro.. I\'ll\ntreasure these Wheels."',
83: 'Renton\n(Charles, Ray.. Once things\nsettle, I\'ll try a big\nwheel too, like\nCharles did..)',
84: 'Renton\n(Papa, Mama.. The way of\nliving you taught me..\nI\'ll never forget it..)',
})

T.update({
55: 'A balance part on a lift board\'s underside. '
    'The bigger it is, the slower the speed, but the easier tricks are to land.\n'
    'Many things beyond the wheel define a board\'s character - '
    'its length and form, and the trapar-intake shape that catches trapar waves.',
59: 'Bello\n"You.. World\'s in crisis\nand you shop\ncarefree?"',
65: 'Bello\n"Got it, bro Gainer.\nTo comfort your little\nbro, that\'s another\nstory."',
})

rows = json.load(open(WORK + r'\analysis\rec089_work.json', encoding='utf-8'))
bud = {r['i']: r['budget'] for r in rows}
need = set(bud)
miss = need - set(T)
extra = set(T) - need
over = [(i, bl(T[i]), bud[i]) for i in T if i in bud and bl(T[i]) > bud[i]]
print("rec089: %d/%d rows | missing %s | extra %s | over %s" % (
    len(T), len(need), sorted(miss), sorted(extra), over))
if not miss and not extra and not over:
    lines = ["# -*- coding: utf-8 -*-", '"""Stage record 89 dialogue."""', "", "T = {"]
    for k in sorted(T):
        lines.append("    %d: %r," % (k, T[k]))
    lines.append("}")
    open("rec089_en.py", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("  WRITTEN")
